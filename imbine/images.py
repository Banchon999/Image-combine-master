# -*- coding: utf-8 -*-
"""ค้นหาและเรียงลำดับไฟล์ภาพ"""

import os
import re

# นามสกุลไฟล์ภาพที่รองรับเป็น "ขาเข้า"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")


def is_image_file(filename):
    """เช็คว่าไฟล์เป็นรูปภาพหรือไม่ (ดูจากนามสกุล)"""
    return str(filename).lower().endswith(IMAGE_EXTS)


def natural_sort_key(filename):
    """
    สร้าง 'กุญแจ' สำหรับเรียงชื่อไฟล์แบบธรรมชาติ (natural sort)

    ปัญหา: ถ้าเรียงแบบปกติ ชื่อไฟล์จะกลายเป็น 1, 10, 11, 2, 3 ...
    วิธีแก้: แยกตัวเลขออกมาแล้วเทียบเป็นตัวเลขจริง ๆ ทำให้ได้ 1, 2, 3, ... 10, 11

    รองรับชื่อหลายแบบ เช่น:
      01.jpg, 02.jpg          -> เลขล้วน
      page_1.jpg, page_10.jpg -> มีคำนำหน้า
      001-002.jpg             -> มีหลายเลข
      ตอนที่ 1.jpg            -> มีตัวอักษรไทยปน

    คีย์ที่คืนเป็น list ของ tuple (ชนิด, ค่า) โดยชนิด 0=ตัวอักษร 1=ตัวเลข
    การใส่ชนิดนำหน้าทำให้เทียบ str กับ int ข้ามกันแล้วไม่ TypeError
    """
    name = os.path.splitext(str(filename))[0]  # ตัดนามสกุลออก
    parts = re.split(r"(\d+)", name)           # แยกเป็นชิ้น สลับเลข/ตัวอักษร
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part)))          # เป็นตัวเลข -> เทียบค่าตัวเลข
        else:
            key.append((0, part.lower()))       # เป็นตัวอักษร -> เทียบตัวอักษร
    return key


def list_images_sorted(folder):
    """คืนรายชื่อไฟล์ภาพในโฟลเดอร์ เรียงตามชื่อแบบธรรมชาติแล้ว

    คืน list ว่างถ้าโฟลเดอร์ไม่มีอยู่ — ตั้งใจให้เรียกได้โดยไม่ต้องเช็คก่อน
    """
    if not os.path.isdir(folder):
        return []
    files = [f for f in os.listdir(folder) if is_image_file(f)]
    files.sort(key=natural_sort_key)
    return files


def image_paths_in(folder):
    """เหมือน list_images_sorted แต่คืน path เต็ม"""
    return [os.path.join(folder, f) for f in list_images_sorted(folder)]
