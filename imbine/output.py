# -*- coding: utf-8 -*-
"""บันทึกภาพผลลัพธ์ลงดิสก์"""

import os

from .naming import build_output_name, ext_for


def unique_path(path):
    """หา path ที่ยังไม่มีไฟล์อยู่ โดยเติม _1, _2, ... ก่อนนามสกุล"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    dup = 1
    while os.path.exists(f"{base}_{dup}{ext}"):
        dup += 1
    return f"{base}_{dup}{ext}"


def save_image(img, path, fmt="JPG", quality=92):
    """บันทึกภาพ 1 ใบตามชนิดที่เลือก แล้วคืน path ที่เขียนจริง"""
    fmt = str(fmt).upper()
    if fmt == "PNG":
        img.save(path, "PNG")           # PNG ไม่มี lossy quality
    elif fmt == "WEBP":
        img.save(path, "WEBP", quality=quality)
    else:
        img.save(path, "JPEG", quality=quality)
    return path


def save_results(results, output_folder, name_pattern, fmt="JPG",
                 quality=92, folder_name="", overwrite=True,
                 progress_cb=None):
    """
    บันทึกภาพผลลัพธ์ทั้งชุดลงโฟลเดอร์

    overwrite=False -> ถ้าชื่อซ้ำจะเติม _1, _2 ต่อท้ายแทนการเขียนทับ
    progress_cb     -> ฟังก์ชันรับ (บันทึกไปแล้ว, ทั้งหมด)

    คืนค่า: list ของ path ไฟล์ที่บันทึกแล้ว
    """
    os.makedirs(output_folder, exist_ok=True)
    ext = ext_for(fmt)
    saved = []
    total = len(results)
    for i, img in enumerate(results, start=1):
        base = build_output_name(name_pattern, i, total, folder_name)
        path = os.path.join(output_folder, base + ext)
        if not overwrite:
            path = unique_path(path)
        saved.append(save_image(img, path, fmt, quality))
        if progress_cb:
            progress_cb(i, total)
    return saved
