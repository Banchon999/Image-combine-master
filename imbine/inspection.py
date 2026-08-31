# -*- coding: utf-8 -*-
"""
ระบบ smart กัน human error: ตรวจสอบล่วงหน้าก่อนต่อภาพจริง

หลักการของโมดูลนี้: **รายงาน ไม่ตัดสินใจแทนผู้ใช้**
ทุกอย่างที่คืนออกไปเป็นได้แค่ "คำเตือน" ให้ UI เอาไปถามผู้ใช้ว่าจะไปต่อไหม
"""

import os
from dataclasses import dataclass, field

from PIL import Image

from .i18n import M, translate
from .naming import build_output_name, ext_for


@dataclass
class InspectionReport:
    """ผลการตรวจภาพล่วงหน้า"""

    ok: list = field(default_factory=list)
    """path รูปที่เปิดได้ปกติ (เรียงตามลำดับเดิม)"""

    broken: list = field(default_factory=list)
    """(path, เหตุผล) ของรูปที่เปิดไม่ได้"""

    sizes: dict = field(default_factory=dict)
    """{path: (w, h)} ของรูปที่เปิดได้"""

    warnings: list = field(default_factory=list)
    """คำเตือนที่ควรแจ้งผู้ใช้ก่อนทำงาน — เป็น Message แปลตอนแสดงผล"""

    def __bool__(self):
        """report เป็น True เมื่อมีรูปที่ใช้งานได้อย่างน้อย 1 รูป"""
        return bool(self.ok)


def _join_names(paths, limit=5):
    """
    รวมชื่อไฟล์เป็นข้อความสั้น ๆ ไม่ให้ยาวจนล้นกล่องข้อความ

    คืน str ไม่ใช่ Message เพราะผลลัพธ์ถูกใช้เป็น *พารามิเตอร์* ของ Message
    ตัวนอกอีกที — แปลตรงนี้เลยจึงถูกต้องกว่าซ้อน Message เข้าไปอีกชั้น
    """
    names = ", ".join(os.path.basename(p) for p in paths[:limit])
    more = (translate("core.inspect.more_files", count=len(paths) - limit)
            if len(paths) > limit else "")
    return names + more


def inspect_images(image_paths):
    """
    ตรวจสอบรูปภาพล่วงหน้า เพื่อหา 'จุดเสี่ยง' ก่อนเริ่มทำงานจริง

    ตรวจ 3 อย่าง:
      1. ไฟล์เสีย / เปิดไม่ได้
      2. ความกว้างต่างกันมากผิดปกติ (อาจเป็นภาพคนละชุด)
      3. ภาพที่ขนาดต่างจากค่ามัธยฐานมาก (มักเป็นปก/โฆษณา/ภาพแทรก)
    """
    ok, broken, sizes = [], [], {}
    for path in image_paths:
        try:
            with Image.open(path) as img:
                img.verify()  # ตรวจว่าไฟล์ไม่เสีย
            # verify() ทำให้ object ใช้ต่อไม่ได้ ต้องเปิดใหม่เพื่ออ่านขนาด
            with Image.open(path) as img2:
                sizes[path] = img2.size
            ok.append(path)
        except Exception as e:
            broken.append((path, str(e)))

    warnings = []

    if broken:
        warnings.append(M("core.inspect.broken", count=len(broken),
                          names=_join_names([p for p, _ in broken])))

    # --- ความกว้างต่างกันมาก ---
    widths = [w for (w, h) in sizes.values()]
    if widths:
        wmin, wmax = min(widths), max(widths)
        if wmax > 0 and wmin / wmax < 0.5:
            warnings.append(M("core.inspect.width_spread",
                              minimum=wmin, maximum=wmax))

    # --- ภาพที่ขนาดผิดปกติเทียบกับค่ามัธยฐาน ---
    # ต้องมีอย่างน้อย 4 ภาพ ค่ามัธยฐานถึงจะมีความหมายพอจะใช้เทียบ
    areas = sorted(w * h for (w, h) in sizes.values())
    if len(areas) >= 4:
        median = areas[len(areas) // 2]
        odd = [p for p, (w, h) in sizes.items()
               if median > 0 and (w * h < median * 0.15 or w * h > median * 6)]
        if odd:
            warnings.append(M("core.inspect.odd_size", count=len(odd),
                              names=_join_names(odd)))

    return InspectionReport(ok=ok, broken=broken, sizes=sizes,
                            warnings=warnings)


def check_output_path(folders_in, folder_out):
    """
    ตรวจว่าโฟลเดอร์ปลายทางปลอดภัยหรือไม่

    เคสที่อันตรายจริง: ปลายทางอยู่ *ข้างใน* ต้นทาง — รอบถัดไปที่สั่งต่อภาพ
    โฟลเดอร์เดิม ระบบจะเก็บไฟล์ที่ต่อไปแล้วมาต่อซ้ำเข้าไปอีก
    """
    warnings = []
    if not folder_out:
        return warnings
    out_abs = os.path.abspath(folder_out)
    for fin in folders_in:
        in_abs = os.path.abspath(fin)
        if out_abs == in_abs or out_abs.startswith(in_abs + os.sep):
            warnings.append(M("core.inspect.output_inside_input",
                              folder=os.path.basename(fin)))
    return warnings


def find_existing_outputs(output_folder, name_pattern, count, fmt,
                          folder_name=""):
    """หาว่าจะมีไฟล์ผลลัพธ์ตัวไหนทับไฟล์เดิมที่มีอยู่แล้วบ้าง"""
    if not os.path.isdir(output_folder):
        return []
    ext = ext_for(fmt)
    existing = []
    for i in range(1, int(count) + 1):
        fname = build_output_name(name_pattern, i, count, folder_name) + ext
        if os.path.exists(os.path.join(output_folder, fname)):
            existing.append(fname)
    return existing
