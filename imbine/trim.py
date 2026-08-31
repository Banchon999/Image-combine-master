# -*- coding: utf-8 -*-
"""
ตัดขอบว่างและตัดส่วนที่ซ้ำกันระหว่างหน้า

ปัญหาจริงสองข้อของไฟล์เว็บตูนที่โหลดมาจากเว็บ:

  1. **ขอบขาว/ดำติดมา** — บางเว็บใส่ padding ให้ทุกหน้า พอต่อกันแล้วเกิดเป็น
     แถบคั่นกลางเรื่อง
  2. **หน้าซ้อนกัน** — ตัวตัดภาพหลายตัวจงใจให้หน้าถัดไปคาบเกี่ยวกับหน้าก่อน
     ไม่กี่ร้อยพิกเซล พอเอามาต่อตรง ๆ จะเห็นภาพเดิมซ้ำสองรอบ

ทั้งสองอย่างแก้ได้ด้วยการดูพิกเซลล้วน ๆ ไม่ต้องรู้จัก pipeline
"""

from PIL import Image, ImageChops

# จำนวนจุดที่สุ่มอ่านต่อหนึ่งแถว เวลาเทียบว่าสองแถวเหมือนกันไหม
# 32 จุดพอแยกแถวที่ต่างกันจริงออกจากกันได้ โดยไม่ต้องอ่านทั้งแถว
_ROW_SAMPLES = 32


def _background_color(img):
    """เดาสีพื้นหลังจากมุมซ้ายบน — ตรงกับที่ตาคนใช้ตัดสิน"""
    return img.convert("RGB").getpixel((0, 0))


def trim_border(img, tolerance=8, background=None):
    """
    ตัดขอบสีเดียวรอบภาพออก คืนภาพใหม่ (ภาพเดิมไม่ถูกแตะ)

    ``tolerance`` คือความต่างของสีที่ยังนับว่า "เป็นพื้นหลัง" — ภาพ JPEG
    มี noise จากการบีบอัดเสมอ ขอบขาวจริง ๆ จึงไม่เคยเป็น 255 เป๊ะทุกจุด
    ถ้าตั้งเป็น 0 จะแทบไม่มีอะไรถูกตัดเลย

    ภาพที่เป็นสีเดียวทั้งใบจะถูกคืนกลับไปเหมือนเดิม ไม่ใช่คืนภาพขนาด 0
    """
    rgb = img.convert("RGB")
    background = background if background is not None else _background_color(img)

    canvas = Image.new("RGB", rgb.size, tuple(background[:3]))
    diff = ImageChops.difference(rgb, canvas)
    if tolerance:
        # ยกระดับความต่างขึ้นแล้วหักค่า tolerance ออก จุดที่ต่างน้อยกว่า
        # tolerance จะกลายเป็น 0 แล้ว getbbox() จะไม่นับว่าเป็นเนื้อภาพ
        diff = ImageChops.add(diff, diff, 2.0, -tolerance)

    box = diff.getbbox()
    if box is None or box == (0, 0, img.width, img.height):
        return img
    return img.crop(box)


def _line_signatures(img, vertical=True, tolerance=8):
    """
    ย่อแต่ละแถว (หรือคอลัมน์) ให้เหลือลายเซ็นสั้น ๆ ที่เทียบกันได้เร็ว

    ย่อความกว้างลงเหลือ _ROW_SAMPLES จุดในครั้งเดียวด้วย resize แล้วค่อยหาร
    ด้วย tolerance เพื่อให้ noise จากการบีบอัดตกลงมาอยู่ช่องเดียวกัน
    การเทียบภายหลังจึงเป็นการเทียบ tuple ของ int ซึ่งเร็วกว่าไล่เทียบพิกเซลมาก
    """
    rgb = img.convert("RGB")
    if not vertical:
        # TRANSPOSE ไม่ใช่ ROTATE_90 — การหมุนจะกลับลำดับคอลัมน์ ทำให้
        # "ท้ายภาพ" กับ "หัวภาพ" สลับข้างกัน แล้วหาส่วนซ้อนไม่เจอเลย
        rgb = rgb.transpose(Image.TRANSPOSE)

    lines = rgb.height
    if lines == 0:
        return []
    small = rgb.resize((_ROW_SAMPLES, lines), Image.NEAREST)
    raw = small.tobytes()                    # RGB เรียงทีละแถว
    stride = _ROW_SAMPLES * 3
    step = max(1, int(tolerance))
    return [tuple(value // step for value in raw[y * stride:(y + 1) * stride])
            for y in range(lines)]


def find_overlap(previous, following, max_search=400, tolerance=8,
                 vertical=True, minimum=8):
    """
    หาว่าท้ายภาพแรกกับหัวภาพที่สองซ้ำกันกี่พิกเซล — ไม่ซ้ำคืน 0

    ``minimum`` กันการตัดพลาด: แถวว่าง ๆ ไม่กี่แถวที่บังเอิญเหมือนกัน
    (ขอบขาวด้านล่างกับขอบขาวด้านบน) ไม่ควรถือเป็นการซ้อนกันจริง
    ตั้งไว้สูงพอที่จะต้องเป็นเนื้อภาพจริงถึงจะเข้าเงื่อนไข

    ภาพที่ด้านตัดไม่เท่ากันจะถูกข้าม เพราะเทียบแถวต่อแถวไม่ได้อย่างมีความหมาย
    """
    if vertical and previous.width != following.width:
        return 0
    if not vertical and previous.height != following.height:
        return 0

    limit = max(0, int(max_search))
    if limit < minimum:
        return 0

    before = _line_signatures(previous, vertical, tolerance)[-limit:]
    after = _line_signatures(following, vertical, tolerance)[:limit]

    # ไล่จากยาวสุดลงมา เพื่อให้ได้ส่วนซ้อนที่ยาวที่สุดเสมอ
    for size in range(min(len(before), len(after)), minimum - 1, -1):
        if before[-size:] == after[:size]:
            return size
    return 0


def drop_overlap(img, amount, vertical=True):
    """ตัดส่วนหัวของภาพออก ``amount`` พิกเซล (ใช้กับภาพที่ซ้อนกับภาพก่อนหน้า)"""
    if amount <= 0:
        return img
    if vertical:
        if amount >= img.height:
            return img
        return img.crop((0, amount, img.width, img.height))
    if amount >= img.width:
        return img
    return img.crop((amount, 0, img.width, img.height))


def dedupe_sequence(images, max_search=400, tolerance=8, vertical=True):
    """
    ตัดส่วนซ้ำออกจากภาพทั้งชุด คืน (รายการภาพใหม่, จำนวนจุดที่ตัด)

    เทียบกับ "ภาพก่อนหน้าหลังตัดแล้ว" เสมอ ไม่ใช่ภาพต้นฉบับ เพราะส่วนที่ถูก
    ตัดออกไปแล้วไม่ควรถูกนำมาเทียบซ้ำ
    """
    images = list(images)
    if len(images) < 2:
        return images, 0

    result = [images[0]]
    removed = 0
    for nxt in images[1:]:
        amount = find_overlap(result[-1], nxt, max_search, tolerance, vertical)
        if amount:
            nxt = drop_overlap(nxt, amount, vertical)
            removed += 1
        result.append(nxt)
    return result, removed
