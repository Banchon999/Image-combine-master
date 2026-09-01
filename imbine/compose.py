# -*- coding: utf-8 -*-
"""ปรับขนาดและวางภาพลงผืนผ้าใบ — งานพิกเซลล้วน ไม่รู้จัก pipeline"""

from PIL import Image

from .i18n import M
from .images import load_image

# Pillow ย้าย constant การ resample ไปอยู่ใต้ Image.Resampling ตั้งแต่ 9.1
# แต่ยังคง alias เดิมไว้ — เผื่อไว้ทั้งสองทางจะได้ไม่ผูกกับเวอร์ชัน
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - Pillow เก่ากว่า 9.1
    RESAMPLE = Image.LANCZOS


def uniform_target(sizes, vertical=True):
    """
    ขนาดของ 'ด้านตัด' ที่ทุกภาพจะถูกปรับให้เท่ากัน

    ยึด "ค่ามากสุด" เพื่อไม่ให้ภาพถูกย่อจนเสียรายละเอียด — ภาพเล็กจะถูกขยายขึ้น
    แทนที่จะย่อภาพใหญ่ลง
    """
    sizes = list(sizes)
    if not sizes:
        return 0
    return max(w if vertical else h for (w, h) in sizes)


def uniform_size(size, target, vertical=True):
    """ขนาดใหม่ของภาพหนึ่งใบหลังปรับด้านตัดให้เท่ากับ target"""
    w, h = size
    if vertical:
        if w == target:
            return (w, h)
        # max(1, ...) กันภาพที่กว้างมากแต่สูงนิดเดียวถูกย่อจนสูง 0 px
        return (target, max(1, round(h * target / w)))
    if h == target:
        return (w, h)
    return (max(1, round(w * target / h)), target)


def uniform_sizes(sizes, vertical=True):
    """
    ขนาดของทุกภาพหลังผ่าน fit_uniform — คำนวณจากตัวเลขล้วน ไม่เปิดไฟล์

    imbine.estimate ใช้ตัวนี้เพื่อบอกผู้ใช้ล่วงหน้าว่าจะได้ไฟล์ขนาดเท่าไหร่
    ต้องให้ผลตรงกับ fit_uniform เสมอ — ทั้งคู่จึงใช้ uniform_size ตัวเดียวกัน
    """
    sizes = list(sizes)
    target = uniform_target(sizes, vertical)
    return [uniform_size(size, target, vertical) for size in sizes]


def fit_uniform(images, vertical=True, resample=RESAMPLE):
    """
    ปรับ 'ด้านตัด' ของทุกภาพให้เท่ากัน โดยคงอัตราส่วนเดิม

      ต่อแนวตั้ง  -> ความกว้างต้องเท่ากัน (ยึดกว้างสุดเป็นมาตรฐาน)
      ต่อแนวนอน  -> ความสูงต้องเท่ากัน  (ยึดสูงสุดเป็นมาตรฐาน)

    คืน list ใหม่ ภาพที่ขนาดตรงอยู่แล้วจะถูกส่งต่อเป็นตัวเดิม (ไม่คัดลอกซ้ำ)
    """
    images = list(images)
    if not images:
        return []

    target = uniform_target([im.size for im in images], vertical)

    out = []
    for im in images:
        new_size = uniform_size(im.size, target, vertical)
        if new_size != im.size:
            im = im.resize(new_size, resample)
        out.append(im)
    return out


def stitch_group(images, vertical=True, bg_color=(255, 255, 255)):
    """
    ต่อภาพในกลุ่มเดียวให้เป็นภาพเดียว

    ถ้าขนาดด้านตัดไม่เท่ากัน (ไม่ได้ผ่าน fit_uniform มา) จะจัดให้อยู่กึ่งกลาง
    แล้วเหลือพื้นหลังสี bg_color ที่ขอบ
    """
    images = list(images)
    if not images:
        raise ValueError(M("core.error.no_images"))

    has_alpha = any("A" in im.getbands() or im.mode in ("P", "PA") and
                    "transparency" in im.info for im in images)
    grayscale = all(im.mode in ("1", "L", "I", "F") for im in images)
    mode = "RGBA" if has_alpha else ("L" if grayscale else "RGB")
    if mode == "RGBA":
        fill = tuple(bg_color[:3]) + (0,)
    elif mode == "L":
        fill = bg_color if isinstance(bg_color, int) else bg_color[0]
    else:
        fill = tuple(bg_color[:3])

    if vertical:
        w = max(im.width for im in images)
        h = sum(im.height for im in images)
        canvas = Image.new(mode, (w, h), fill)
        y = 0
        for im in images:
            converted = im if im.mode == mode else im.convert(mode)
            canvas.paste(converted, ((w - im.width) // 2, y))
            y += im.height
    else:
        w = sum(im.width for im in images)
        h = max(im.height for im in images)
        canvas = Image.new(mode, (w, h), fill)
        x = 0
        for im in images:
            converted = im if im.mode == mode else im.convert(mode)
            canvas.paste(converted, (x, (h - im.height) // 2))
            x += im.width
    for key in ("icc_profile", "exif", "dpi"):
        if key in images[0].info:
            canvas.info[key] = images[0].info[key]
    return canvas


def load_rgb(path):
    """
    เปิดไฟล์ภาพแล้วคืนภาพโหมด RGB ที่ 'ไม่ผูกกับไฟล์ต้นทาง' แล้ว

    ใช้ with + convert() เสมอ เพื่อให้ไฟล์ถูกปิดทันที
    ถ้าปล่อย Image.open() ค้างไว้ ตัวจัดการไฟล์จะรั่วสะสม และบน Windows
    ไฟล์ต้นทางจะถูกล็อกจนลบ/ย้ายไม่ได้ระหว่างที่โปรแกรมยังเปิดอยู่
    """
    return load_image(path, "first")[0].convert("RGB")
