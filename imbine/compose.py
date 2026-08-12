# -*- coding: utf-8 -*-
"""ปรับขนาดและวางภาพลงผืนผ้าใบ — งานพิกเซลล้วน ไม่รู้จัก pipeline"""

from PIL import Image

# Pillow ย้าย constant การ resample ไปอยู่ใต้ Image.Resampling ตั้งแต่ 9.1
# แต่ยังคง alias เดิมไว้ — เผื่อไว้ทั้งสองทางจะได้ไม่ผูกกับเวอร์ชัน
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - Pillow เก่ากว่า 9.1
    RESAMPLE = Image.LANCZOS


def fit_uniform(images, vertical=True, resample=RESAMPLE):
    """
    ปรับ 'ด้านตัด' ของทุกภาพให้เท่ากัน โดยคงอัตราส่วนเดิม

      ต่อแนวตั้ง  -> ความกว้างต้องเท่ากัน (ยึดกว้างสุดเป็นมาตรฐาน)
      ต่อแนวนอน  -> ความสูงต้องเท่ากัน  (ยึดสูงสุดเป็นมาตรฐาน)

    ยึด "ค่ามากสุด" เพื่อไม่ให้ภาพถูกย่อจนเสียรายละเอียด — ภาพเล็กจะถูกขยายขึ้น
    แทนที่จะย่อภาพใหญ่ลง

    คืน list ใหม่ ภาพที่ขนาดตรงอยู่แล้วจะถูกส่งต่อเป็นตัวเดิม (ไม่คัดลอกซ้ำ)
    """
    images = list(images)
    if not images:
        return []

    if vertical:
        target = max(im.width for im in images)
    else:
        target = max(im.height for im in images)

    out = []
    for im in images:
        if vertical and im.width != target:
            # max(1, ...) กันภาพที่กว้างมากแต่สูงนิดเดียวถูกย่อจนสูง 0 px
            new_h = max(1, round(im.height * target / im.width))
            im = im.resize((target, new_h), resample)
        elif not vertical and im.height != target:
            new_w = max(1, round(im.width * target / im.height))
            im = im.resize((new_w, target), resample)
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
        raise ValueError("ไม่มีรูปภาพให้ต่อ")

    if vertical:
        w = max(im.width for im in images)
        h = sum(im.height for im in images)
        canvas = Image.new("RGB", (w, h), bg_color)
        y = 0
        for im in images:
            canvas.paste(im, ((w - im.width) // 2, y))
            y += im.height
    else:
        w = sum(im.width for im in images)
        h = max(im.height for im in images)
        canvas = Image.new("RGB", (w, h), bg_color)
        x = 0
        for im in images:
            canvas.paste(im, (x, (h - im.height) // 2))
            x += im.width
    return canvas


def load_rgb(path):
    """
    เปิดไฟล์ภาพแล้วคืนภาพโหมด RGB ที่ 'ไม่ผูกกับไฟล์ต้นทาง' แล้ว

    ใช้ with + convert() เสมอ เพื่อให้ไฟล์ถูกปิดทันที
    ถ้าปล่อย Image.open() ค้างไว้ ตัวจัดการไฟล์จะรั่วสะสม และบน Windows
    ไฟล์ต้นทางจะถูกล็อกจนลบ/ย้ายไม่ได้ระหว่างที่โปรแกรมยังเปิดอยู่
    """
    with Image.open(path) as img:
        return img.convert("RGB")
