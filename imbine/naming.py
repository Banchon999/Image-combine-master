# -*- coding: utf-8 -*-
"""สร้างชื่อไฟล์ผลลัพธ์"""

import re

# อักขระที่ตั้งเป็นชื่อไฟล์ไม่ได้บน Windows (Linux/macOS ใจกว้างกว่า
# แต่เรากันไว้ให้หมดเพื่อให้ไฟล์ย้ายข้ามเครื่องได้)
_FORBIDDEN = re.compile(r'[<>:"/\\|?*]')

_TOKEN = re.compile(r"\{(n3|n2|n|folder|total)\}")

_EXT_BY_FORMAT = {"PNG": ".png", "WEBP": ".webp", "JPG": ".jpg",
                  "JPEG": ".jpg", "TIFF": ".tiff"}


def ext_for(fmt):
    """คืนนามสกุลไฟล์ตามชนิดที่เลือก (ไม่รู้จัก -> .jpg)"""
    return _EXT_BY_FORMAT.get(str(fmt).upper(), ".jpg")


def build_output_name(pattern, index, total, folder_name=""):
    """
    สร้างชื่อไฟล์ผลลัพธ์จาก pattern ที่ผู้ใช้กำหนด (ยังไม่รวมนามสกุล)

    ตัวแปรที่ใช้ใน pattern ได้:
      {n}      -> เลขลำดับ เช่น 1, 2, 3
      {n2}     -> เลขลำดับ 2 หลัก เช่น 01, 02
      {n3}     -> เลขลำดับ 3 หลัก เช่น 001
      {folder} -> ชื่อโฟลเดอร์ต้นทาง
      {total}  -> จำนวนไฟล์ผลลัพธ์ทั้งหมด

    แทนที่ทุกตัวใน "รอบเดียว" ตั้งใจให้ข้อความที่ถูกแทนเข้ามาไม่ถูกอ่านซ้ำ
    ไม่งั้นโฟลเดอร์ที่ชื่อ "{total}" จะถูกขยายต่อกลายเป็นตัวเลข
    """
    values = {
        "n": str(index),
        "n2": f"{index:02d}",
        "n3": f"{index:03d}",
        "folder": str(folder_name),
        "total": str(total),
    }
    name = _TOKEN.sub(lambda m: values[m.group(1)], str(pattern))
    name = _FORBIDDEN.sub("_", name)
    # pattern ว่างหรือมีแต่อักขระต้องห้าม -> ต้องมีชื่อสำรอง ไม่งั้นได้ไฟล์ ".jpg"
    return name.strip() or f"output_{index}"
