# -*- coding: utf-8 -*-
"""แบ่งรายการภาพออกเป็นกลุ่ม — 1 กลุ่ม = 1 ไฟล์ผลลัพธ์"""


def group_boundaries(dims, parts_count=1, max_size=0):
    """
    ตัดสินใจว่าจะแบ่งตรงไหน โดยดูแค่ "ขนาดตามแกนที่ต่อ" ของแต่ละภาพ

    คืน [(start, stop), ...] เป็นช่วง index แบบเดียวกับการ slice

    แยกออกมาจาก split_into_groups เพราะระบบประมาณผล (imbine.estimate) ต้อง
    ตอบให้ได้ว่า "จะได้กี่ไฟล์ ไฟล์ละเท่าไหร่" โดยยังไม่เปิดภาพจริงสักใบ
    ถ้าปล่อยให้มันคำนวณเอง เลขที่พรีวิวกับไฟล์ที่ได้จริงจะเริ่มเพี้ยนกันทันที
    ที่มีใครมาแก้ตรรกะการแบ่งข้างล่างนี้

    ลำดับการตัดสินใจ:
      1. ถ้ากำหนด max_size -> แบ่งกลุ่มใหม่ทันทีที่ขนาดรวมจะเกิน
      2. ไม่งั้นใช้ parts_count -> แบ่งให้ได้จำนวนกลุ่มเท่าที่ขอ

    หมายเหตุ: โหมด max_size ตัดได้เฉพาะ "ตรงรอยต่อระหว่างรูป" เท่านั้น
    ถ้ารูปเดียวสูงเกิน max_size อยู่แล้ว มันจะได้อยู่กลุ่มตัวเองและยังเกินอยู่ดี
    (การตัดกลางรูปโดยเลี่ยงบอลลูนคำพูดคือระบบ smart split ที่ยังไม่ได้ทำ)
    """
    dims = list(dims)
    if not dims:
        return []

    # ---- กรณีจำกัดขนาดต่อไฟล์ ----
    if max_size and max_size > 0:
        bounds, start, current_size = [], 0, 0
        for index, d in enumerate(dims):
            if index > start and current_size + d > max_size:
                bounds.append((start, index))
                start, current_size = index, 0
            current_size += d
        bounds.append((start, len(dims)))
        return bounds

    # ---- กรณีแบ่งตามจำนวนไฟล์ ----
    parts_count = max(1, int(parts_count))
    parts_count = min(parts_count, len(dims))  # ขอ 10 ไฟล์จาก 3 รูปไม่ได้
    bounds, n = [], len(dims)
    base = n // parts_count          # จำนวนรูปต่อกลุ่ม (ขั้นต่ำ)
    remainder = n % parts_count      # เศษ -> เกลี่ยใส่กลุ่มแรก ๆ
    idx = 0
    for i in range(parts_count):
        size = base + (1 if i < remainder else 0)
        bounds.append((idx, idx + size))
        idx += size
    return bounds


def split_into_groups(images, parts_count=1, max_size=0, vertical=True):
    """
    แบ่งรายการรูปออกเป็นกลุ่ม — 1 กลุ่ม = 1 ไฟล์ผลลัพธ์

    ตรรกะการตัดสินใจอยู่ใน group_boundaries ทั้งหมด ฟังก์ชันนี้แค่เอา
    ช่วง index ที่ได้ไปหั่นรายการจริง
    """
    images = list(images)
    # ขนาดที่นำมาบวกกัน: แนวตั้ง=ความสูง / แนวนอน=ความกว้าง
    dims = [img.height if vertical else img.width for img in images]
    return [images[start:stop] for start, stop in
            group_boundaries(dims, parts_count, max_size)]
