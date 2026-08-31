# -*- coding: utf-8 -*-
"""
ท่อประมวลผล (pipeline)

เดิม stitch_images() ทำทุกอย่างในฟังก์ชันเดียว พอจะเพิ่ม upscale / denoise /
watermark / auto-trim เข้าไป โค้ดจะพันกันจนแก้ไม่ไหว โมดูลนี้แยกงานออกเป็น
"ขั้นตอน" (Step) ที่ต่อกันเป็นสาย เปิด/ปิด/แทรก/สลับลำดับได้ทีละตัว

สายมาตรฐานตอนนี้:

    load -> trim -> downscale -> uniform -> split -> stitch -> watermark -> save

โดย trim / downscale / watermark ปิดอยู่เป็นค่าเริ่มต้น (is_enabled คืน False)
สายจึงเหลือ load -> uniform -> split -> stitch -> save เหมือนเดิมทุกประการ
จนกว่าผู้ใช้จะเปิดใช้เอง

ตำแหน่งที่ระบบในอนาคตจะเสียบเข้ามา:

    load -> [denoise] -> [upscale] -> trim -> uniform -> split -> ...

สามหลักที่ทุก Step ต้องเคารพ:
  1. รายงานความคืบหน้าผ่าน ctx.progress — UI จะได้ไม่ต้องเดา
  2. เช็คการยกเลิกผ่าน ctx.cancel ในลูปที่กินเวลา
  3. ห้าม import อะไรที่เกี่ยวกับ UI — โมดูลนี้ต้องเทสต์ได้โดยไม่มีหน้าจอ
"""

import threading
from dataclasses import dataclass, field

from .i18n import M, has_key, translate


# ----------------------------------------------------------------------
# การยกเลิกงาน
# ----------------------------------------------------------------------

class Cancelled(Exception):
    """ผู้ใช้กดยกเลิกระหว่างทาง — ไม่ใช่ข้อผิดพลาด UI ไม่ควรแสดงเป็น error"""


class CancelToken:
    """
    ป้ายบอก "หยุดเถอะ" ที่ส่งข้ามเธรดได้

    UI ถือไว้แล้วเรียก .cancel() เมื่อผู้ใช้กดปุ่ม ส่วน worker เรียก .check()
    เป็นระยะ ใช้ threading.Event เพื่อให้อ่าน/เขียนข้ามเธรดได้อย่างปลอดภัย
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    @property
    def cancelled(self):
        return self._event.is_set()

    def check(self):
        """โยน Cancelled ถ้าถูกสั่งยกเลิกแล้ว"""
        if self._event.is_set():
            raise Cancelled(M("core.error.cancelled"))

    def reset(self):
        self._event.clear()


# ----------------------------------------------------------------------
# ความคืบหน้า
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ProgressEvent:
    """สถานะ ณ ขณะหนึ่งของงาน — ส่งให้ UI เอาไปวาด"""

    step: str            # ตัวระบุขั้นตอนที่กำลังทำ (อังกฤษ ใช้ในโค้ด)
    step_index: int      # ขั้นที่เท่าไหร่ (เริ่มที่ 1)
    step_total: int      # ทั้งหมดกี่ขั้น
    done: int            # ทำไปแล้วกี่หน่วยในขั้นนี้
    total: int           # ขั้นนี้มีกี่หน่วย
    message: object = ""  # ข้อความเสริม เช่นชื่อไฟล์ที่กำลังทำ (str หรือ Message)
    step_label: str = ""  # ชื่อขั้นตอนที่แปลแล้ว สำหรับโชว์ผู้ใช้

    @property
    def fraction(self):
        """ความคืบหน้าของ *ขั้นนี้* 0.0-1.0"""
        return self.done / self.total if self.total else 0.0

    @property
    def overall(self):
        """ความคืบหน้าของ *ทั้งงาน* 0.0-1.0 (ถือว่าทุกขั้นหนักเท่ากัน)"""
        if not self.step_total:
            return 0.0
        return (self.step_index - 1 + self.fraction) / self.step_total


class Progress:
    """
    ตัวรายงานความคืบหน้า

    รับ callback ตัวเดียวที่รับ ProgressEvent — UI ฝั่ง Tk เอาไปห่อด้วย
    widget.after(0, ...) ส่วนฝั่ง Qt เอาไป emit เป็น signal ได้ตรง ๆ

    callback = None ก็ใช้งานได้ปกติ (เงียบ) จะได้ไม่ต้องเช็ค None ทุกจุดที่เรียก
    """

    def __init__(self, callback=None):
        self._cb = callback
        self._step = ""
        self._label = ""
        self._index = 0
        self._total = 0

    def begin_step(self, name, index, total, label=""):
        self._step, self._index, self._total = name, index, total
        self._label = label or name
        self.report(0, 1)

    def report(self, done, total, message=""):
        if self._cb is None:
            return
        self._cb(ProgressEvent(
            step=self._step, step_index=self._index, step_total=self._total,
            done=done, total=total, message=message, step_label=self._label))


# ----------------------------------------------------------------------
# สิ่งที่ไหลผ่านท่อ
# ----------------------------------------------------------------------

@dataclass
class PipelineContext:
    """
    กล่องข้อมูลที่ส่งต่อกันระหว่าง Step

    แต่ละ Step อ่านช่องที่ตัวเองต้องใช้ แล้วเขียนช่องถัดไป:

        source_paths --load--> images --split--> groups
                     --stitch--> results --save--> saved_paths
    """

    config: object                                   # StitchConfig
    source_paths: list = field(default_factory=list)  # path ภาพขาเข้า
    output_folder: str = ""
    folder_name: str = ""                             # ใช้กับ {folder} ในชื่อไฟล์

    images: list = field(default_factory=list)        # ภาพระหว่างทาง
    groups: list = field(default_factory=list)        # หลังแบ่งกลุ่ม
    results: list = field(default_factory=list)       # หลังต่อเสร็จ
    saved_paths: list = field(default_factory=list)   # ไฟล์ที่เขียนลงดิสก์แล้ว

    warnings: list = field(default_factory=list)      # เก็บสะสมระหว่างทาง
    notes: dict = field(default_factory=dict)         # ที่ว่างให้ Step จดอะไรก็ได้

    progress: Progress = field(default_factory=Progress)
    cancel: CancelToken = field(default_factory=CancelToken)

    @property
    def vertical(self):
        return self.config.vertical


# ----------------------------------------------------------------------
# ขั้นตอน
# ----------------------------------------------------------------------

class Step:
    """
    ฐานของทุกขั้นตอน

    ขั้นตอนใหม่ (upscale, watermark, trim ...) แค่สืบทอดคลาสนี้แล้วเขียน run()
    ถ้าขั้นนั้นควรทำงานเฉพาะบางเงื่อนไข ให้ override is_enabled()
    """

    name = "step"
    """ตัวระบุขั้นตอน — เป็นภาษาอังกฤษเสมอ ใช้ค้นหาใน insert_before/after"""

    label_key = ""
    """คีย์คำแปลของชื่อที่ผู้ใช้เห็น — ว่างไว้แปลว่า "ใช้ name ไปเลย"

    แยกจาก name เพราะ name เป็น *ตัวระบุ* ที่โค้ดใช้ค้นหา ถ้าเอาไปแปลด้วย
    pipe.insert_before("save", ...) จะพังทันทีที่ผู้ใช้สลับภาษา
    """

    def is_enabled(self, ctx):
        """คืน False เพื่อให้ pipeline ข้ามขั้นนี้ไปเลย (ไม่นับในตัวนับขั้นด้วย)

        **ตัดสินใจจาก ctx.config เท่านั้น** อย่าดู ctx.images / ctx.groups /
        ctx.results เพราะ Pipeline.run เรียกเมธอดนี้ของทุกขั้น *ก่อน* เริ่มรัน
        (เพื่อให้ตัวนับ "ขั้นที่ 2 จาก 5" ตรงกับที่ผู้ใช้เห็น) ตอนนั้นช่อง
        ข้อมูลทุกช่องยังว่างอยู่ ขั้นที่เช็คช่องพวกนี้จะถูกปิดเงียบ ๆ ตลอดกาล
        """
        return True

    def label(self):
        """
        ชื่อขั้นตอนที่ผู้ใช้เห็น (แปลแล้ว)

        ขั้นตอนที่คนอื่นเขียนเองแล้วไม่ได้ตั้ง label_key จะได้ชื่อดิบของตัวเอง
        กลับไป ซึ่งอ่านรู้เรื่องกว่าคำว่า "ขั้นตอน" ที่แปลจากคีย์กลาง
        """
        if self.label_key and has_key(self.label_key):
            return translate(self.label_key)
        return self.name

    def run(self, ctx):
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.name!r}>"


class Pipeline:
    """
    สายของ Step ที่รันต่อกันตามลำดับ

    เมธอด insert_before / insert_after / replace / remove มีไว้เพื่อให้
    ระบบในอนาคตเสียบตัวเองเข้ามาได้โดยไม่ต้องแก้โค้ดที่ประกอบสายมาตรฐาน เช่น

        pipe = build_default_pipeline()
        pipe.insert_after("load", UpscaleStep(model="realesrgan-x4plus-anime"))
        pipe.insert_before("save", WatermarkStep(text="@myscan"))
    """

    def __init__(self, steps=(), name="pipeline"):
        self.steps = list(steps)
        self.name = name

    # -- ตรวจดูสาย --------------------------------------------------

    def step_names(self):
        return [s.name for s in self.steps]

    def index_of(self, name):
        for i, step in enumerate(self.steps):
            if step.name == name:
                return i
        raise KeyError(M("core.error.step_not_found", name=repr(name),
                         existing=self.step_names()))

    # -- แก้สาย -----------------------------------------------------

    def append(self, step):
        self.steps.append(step)
        return self

    def insert_before(self, name, step):
        self.steps.insert(self.index_of(name), step)
        return self

    def insert_after(self, name, step):
        self.steps.insert(self.index_of(name) + 1, step)
        return self

    def replace(self, name, step):
        self.steps[self.index_of(name)] = step
        return self

    def remove(self, name):
        del self.steps[self.index_of(name)]
        return self

    # -- รัน --------------------------------------------------------

    def run(self, ctx):
        """
        รันทุกขั้นที่เปิดใช้งานตามลำดับ แล้วคืน ctx ตัวเดิมที่ถูกเติมข้อมูลแล้ว

        โยน Cancelled ถ้าถูกสั่งยกเลิก — ผู้เรียกควรดักแยกจาก Exception อื่น
        เพราะมันคือการกระทำของผู้ใช้ ไม่ใช่ความผิดพลาด
        """
        # คัดขั้นที่ปิดอยู่ออกก่อน เพื่อให้ตัวนับ "ขั้นที่ 2 จาก 5" ตรงกับ
        # สิ่งที่ผู้ใช้เห็นจริง ไม่ใช่รวมขั้นที่ถูกข้ามไปด้วย
        active = [s for s in self.steps if s.is_enabled(ctx)]
        total = len(active)

        for i, step in enumerate(active, start=1):
            ctx.cancel.check()
            ctx.progress.begin_step(step.name, i, total, step.label())
            step.run(ctx)

        ctx.cancel.check()
        return ctx

    def __repr__(self):
        return f"<Pipeline {self.name!r} {' -> '.join(self.step_names())}>"
