# -*- coding: utf-8 -*-
"""แบ่งรายการภาพออกเป็นกลุ่ม — 1 กลุ่ม = 1 ไฟล์ผลลัพธ์"""


def split_into_groups(images, parts_count=1, max_size=0, vertical=True):
    """
    แบ่งรายการรูปออกเป็นกลุ่ม

    ลำดับการตัดสินใจ:
      1. ถ้ากำหนด max_size -> แบ่งกลุ่มใหม่ทันทีที่ขนาดรวมจะเกิน
      2. ไม่งั้นใช้ parts_count -> แบ่งให้ได้จำนวนกลุ่มเท่าที่ขอ

    หมายเหตุ: โหมด max_size ตัดได้เฉพาะ "ตรงรอยต่อระหว่างรูป" เท่านั้น
    ถ้ารูปเดียวสูงเกิน max_size อยู่แล้ว มันจะได้อยู่กลุ่มตัวเองและยังเกินอยู่ดี
    (การตัดกลางรูปโดยเลี่ยงบอลลูนคำพูดคือระบบ smart split ที่ยังไม่ได้ทำ)
    """
    images = list(images)
    if not images:
        return []

    def dim(img):
        # ขนาดที่นำมาบวกกัน: แนวตั้ง=ความสูง / แนวนอน=ความกว้าง
        return img.height if vertical else img.width

    # ---- กรณีจำกัดขนาดต่อไฟล์ ----
    if max_size and max_size > 0:
        groups, current, current_size = [], [], 0
        for img in images:
            d = dim(img)
            if current and current_size + d > max_size:
                groups.append(current)
                current, current_size = [], 0
            current.append(img)
            current_size += d
        if current:
            groups.append(current)
        return groups

    # ---- กรณีแบ่งตามจำนวนไฟล์ ----
    parts_count = max(1, int(parts_count))
    parts_count = min(parts_count, len(images))  # ขอ 10 ไฟล์จาก 3 รูปไม่ได้
    groups, n = [], len(images)
    base = n // parts_count          # จำนวนรูปต่อกลุ่ม (ขั้นต่ำ)
    remainder = n % parts_count      # เศษ -> เกลี่ยใส่กลุ่มแรก ๆ
    idx = 0
    for i in range(parts_count):
        size = base + (1 if i < remainder else 0)
        groups.append(images[idx:idx + size])
        idx += size
    return groups
