# -*- coding: utf-8 -*-
"""บันทึกภาพผลลัพธ์ลงดิสก์"""

import os
import warnings

from PIL import Image

from .formats import capabilities, canonical_format, encoder_available
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


def export_warnings(img, fmt):
    """Describe source data that the target encoder cannot represent."""
    fmt = canonical_format(fmt)
    caps = capabilities(fmt)
    notices = []
    if caps is None:
        return [f"ไม่ทราบความสามารถของ format {fmt}"]
    if ("A" in img.getbands() or "transparency" in img.info) and not caps.alpha:
        notices.append(f"{fmt} ไม่รองรับ alpha; จะ flatten บนสีพื้นหลังที่กำหนด")
    if img.info.get("icc_profile") and not caps.icc_profile:
        notices.append(f"{fmt} ไม่รองรับ ICC profile; profile จะถูกละทิ้ง")
    if img.info.get("exif") and not caps.exif:
        notices.append(f"{fmt} ไม่รองรับ EXIF; metadata จะถูกละทิ้ง")
    return notices


def _flatten_alpha(img, background):
    rgba = img.convert("RGBA")
    base = Image.new("RGBA", rgba.size, tuple(background[:3]) + (255,))
    return Image.alpha_composite(base, rgba).convert("RGB")


def save_image(img, path, fmt="JPG", quality=92, alpha_background=(255, 255, 255),
               options=None, warning_cb=None):
    """บันทึกภาพ 1 ใบตามชนิดที่เลือก แล้วคืน path ที่เขียนจริง"""
    fmt = canonical_format(fmt)
    if not encoder_available(fmt):
        raise ValueError(f"ไม่มี encoder {fmt} ใน Pillow ที่กำลังใช้งาน")
    for notice in export_warnings(img, fmt):
        (warning_cb or (lambda message: warnings.warn(message, UserWarning)))(notice)
    caps = capabilities(fmt)
    if caps and not caps.alpha and ("A" in img.getbands() or
                                    "transparency" in img.info):
        img = _flatten_alpha(img, alpha_background)
    kwargs = dict(options or {})
    if caps and caps.quality:
        kwargs.setdefault("quality", quality)
    for key in ("icc_profile", "exif", "dpi"):
        if key in img.info and (key not in ("icc_profile", "exif") or
                                getattr(caps, key, False)):
            kwargs.setdefault(key, img.info[key])
    img.save(path, fmt, **kwargs)
    return path


def save_results(results, output_folder, name_pattern, fmt="JPG",
                 quality=92, folder_name="", overwrite=True,
                 progress_cb=None, alpha_background=(255, 255, 255),
                 options=None, warning_cb=None):
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
        saved.append(save_image(img, path, fmt, quality, alpha_background,
                                options, warning_cb))
        if progress_cb:
            progress_cb(i, total)
    return saved
