# -*- coding: utf-8 -*-
"""
ประมาณผลลัพธ์ล่วงหน้า — จะได้กี่ไฟล์ ไฟล์ละกี่พิกเซล ราว ๆ กี่ MB

ทั้งโมดูลนี้ทำงานจาก "ขนาดภาพ" อย่างเดียว ไม่แตะพิกเซลเลย การอ่านขนาดใช้
Image.open() ซึ่งอ่านแค่ส่วนหัวไฟล์ จึงเร็วพอจะคำนวณใหม่ทุกครั้งที่ผู้ใช้
ขยับสไลเดอร์ ไม่ต้องรอ ไม่ต้องขึ้นเธรด

ค่าที่สำคัญที่สุดที่โมดูลนี้ให้คือ **คำเตือนเรื่องลิมิตของ format** — WebP
เก็บได้สูงสุด 16383 px และ JPEG 65535 px ซึ่งเว็บตูนที่ต่อยาว ๆ ชนประจำ
เดิมผู้ใช้จะรู้ก็ต่อเมื่อกด Export ไปแล้วรอจนพัง
"""

from dataclasses import dataclass, field

from PIL import Image

from .compose import uniform_sizes
from .formats import canonical_format, capabilities
from .grouping import group_boundaries
from .i18n import M

# ไบต์ต่อพิกเซลโดยประมาณของภาพลายเส้น/ระบายสีแบบการ์ตูน ที่คุณภาพ 100
#
# ตัวเลขพวกนี้เป็นการ "ประมาณ" ไม่ใช่การคำนวณ ภาพจริงเบี่ยงได้หลายสิบเปอร์เซ็นต์
# ตามความซับซ้อนของเนื้อภาพ (หน้าที่มีแต่พื้นขาวเล็กกว่านี้มาก ฉากที่ลงสีทั้งหน้า
# ใหญ่กว่านี้) จุดประสงค์คือให้ผู้ใช้กะได้ว่า "หลักสิบ MB หรือหลักร้อย MB"
# ไม่ใช่ทำนายขนาดไฟล์ให้ตรงเป๊ะ
BYTES_PER_PIXEL = {
    "JPEG": 0.30,
    "WEBP": 0.22,
    "PNG": 1.20,
    "TIFF": 3.00,
    "BMP": 3.00,
    "GIF": 0.60,
}

_DEFAULT_BPP = 0.5


@dataclass(frozen=True)
class OutputPlan:
    """คำตอบของคำถาม 'ถ้ากด Export ตอนนี้จะได้อะไร'"""

    parts: tuple = ()
    """((w, h), ...) ขนาดของแต่ละไฟล์ผลลัพธ์"""

    total_bytes: int = 0
    """ประมาณการขนาดรวมของทุกไฟล์ (ไบต์)"""

    warnings: tuple = ()
    """Message ที่ต้องเตือนผู้ใช้ — ตอนนี้มีแค่เรื่องเกินลิมิตของ format"""

    source_count: int = 0
    """จำนวนภาพต้นทางที่นับได้"""

    @property
    def part_count(self):
        return len(self.parts)

    def __bool__(self):
        return bool(self.parts)


def probe_sizes(paths):
    """
    อ่านขนาดของไฟล์ภาพโดยไม่ decode เนื้อภาพ

    ไฟล์ที่เปิดไม่ได้จะถูกข้ามเงียบ ๆ — การรายงานไฟล์เสียเป็นหน้าที่ของ
    imbine.inspection ไม่ใช่ของตัวประมาณผล
    """
    sizes = []
    for path in paths:
        try:
            with Image.open(path) as img:
                sizes.append(img.size)
        except Exception:
            continue
    return sizes


def estimate_bytes(width, height, fmt="JPG", quality=92):
    """
    ประมาณขนาดไฟล์เป็นไบต์

    คุณภาพมีผลกับ format ที่บีบอัดแบบสูญเสียเท่านั้น ใช้เส้นโค้งยกกำลัง
    เพราะขนาดไฟล์ JPEG/WebP ไม่ได้โตเป็นเส้นตรงตามเลขคุณภาพ — ช่วง 90-100
    ขนาดพุ่งเร็วกว่าช่วง 50-60 มาก
    """
    name = canonical_format(fmt)
    bpp = BYTES_PER_PIXEL.get(name, _DEFAULT_BPP)
    caps = capabilities(name)
    if caps is not None and caps.quality:
        bpp *= max(0.01, min(1.0, quality / 100.0)) ** 2.5
    return int(width * height * bpp)


def limit_warnings(parts, fmt="JPG"):
    """เตือนไฟล์ที่จะเกินขนาดสูงสุดที่ format นั้นเก็บได้"""
    caps = capabilities(fmt)
    if caps is None or not caps.maximum_dimensions:
        return []
    limit_w, limit_h = caps.maximum_dimensions
    name = canonical_format(fmt)
    return [M("core.export.over_limit", fmt=name, limit_w=limit_w,
              limit_h=limit_h, index=index, width=w, height=h)
            for index, (w, h) in enumerate(parts, start=1)
            if w > limit_w or h > limit_h]


def stitched_size(sizes, vertical=True):
    """
    ขนาดของภาพที่ได้จากการต่อภาพชุดหนึ่ง

    ต้องให้ผลตรงกับ compose.stitch_group: แกนที่ต่อคือผลบวก อีกแกนคือค่ามากสุด
    """
    sizes = list(sizes)
    if not sizes:
        return (0, 0)
    if vertical:
        return (max(w for w, _ in sizes), sum(h for _, h in sizes))
    return (sum(w for w, _ in sizes), max(h for _, h in sizes))


def plan_output(sizes, config):
    """
    บอกว่าจะได้ไฟล์กี่ไฟล์ ไฟล์ละเท่าไหร่ รวมกี่ไบต์

    เดินตามเส้นทางเดียวกับ pipeline จริงเป๊ะ ๆ โดยใช้ฟังก์ชันตัวเดียวกัน:
    uniform -> group_boundaries -> stitched_size  ถ้าใครแก้ตรรกะการแบ่งหรือ
    การปรับขนาด ตัวเลขตรงนี้จะขยับตามเอง ไม่ต้องมาไล่แก้สองที่
    """
    sizes = list(sizes)
    if not sizes:
        return OutputPlan()

    vertical = config.vertical
    if config.uniform:
        sizes = uniform_sizes(sizes, vertical)

    dims = [h if vertical else w for (w, h) in sizes]
    bounds = group_boundaries(dims, config.parts_count, config.max_size)
    parts = tuple(stitched_size(sizes[start:stop], vertical)
                  for start, stop in bounds)

    total = sum(estimate_bytes(w, h, config.fmt, config.quality)
                for w, h in parts)
    return OutputPlan(parts=parts, total_bytes=total,
                      warnings=tuple(limit_warnings(parts, config.fmt)),
                      source_count=len(sizes))


def plan_for_paths(paths, config):
    """ทางลัด: อ่านขนาดจากไฟล์แล้วประมาณผลในขั้นตอนเดียว"""
    return plan_output(probe_sizes(paths), config)


def human_bytes(count):
    """แปลงไบต์เป็นข้อความสั้น ๆ ที่คนอ่านรู้เรื่อง"""
    value = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
