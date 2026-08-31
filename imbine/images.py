# -*- coding: utf-8 -*-
"""ค้นหาและเรียงลำดับไฟล์ภาพ"""

import os
import re

from PIL import Image, ImageOps

from .formats import (canonical_format, decoder_available,
                      extensions_for_decoders)
from .i18n import M

# นามสกุลไฟล์ภาพที่รองรับเป็น "ขาเข้า"
IMAGE_EXTS = extensions_for_decoders()


class ImageValidationError(ValueError):
    """The file name or decoded image does not satisfy input requirements."""


def inspect_image(path):
    """Decode enough of *path* to validate it and report its real format."""
    try:
        with Image.open(path) as image:
            actual = canonical_format(image.format)
            if not decoder_available(actual):
                raise ImageValidationError(M("core.error.no_decoder", fmt=actual))
            image.verify()
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(
            M("core.error.not_an_image", path=path)) from exc
    return actual


def is_image_file(filename, validate=False):
    """Check a supported suffix, optionally validating decoded content too."""
    supported = str(filename).lower().endswith(IMAGE_EXTS)
    if not supported or not validate:
        return supported
    try:
        inspect_image(filename)
        return True
    except (ImageValidationError, OSError):
        return False


def load_image(path, multi_frame="first"):
    """Load detached, oriented images without prematurely converting colour.

    ``multi_frame`` may be ``first``, ``all`` or ``error``.  The return value is
    always a list so callers cannot accidentally ignore extra frames.
    """
    if multi_frame not in ("first", "all", "error"):
        raise ValueError(M("core.error.bad_multi_frame"))
    actual = inspect_image(path)
    with Image.open(path) as source:
        frames = getattr(source, "n_frames", 1)
        if frames > 1 and multi_frame == "error":
            raise ImageValidationError(
                M("core.error.multi_frame_rejected", path=path, frames=frames))
        indexes = range(frames) if multi_frame == "all" else range(1)
        loaded = []
        for index in indexes:
            source.seek(index)
            frame = ImageOps.exif_transpose(source)
            frame.load()
            frame = frame.copy()
            frame.info["source_format"] = actual
            # exif_transpose has consumed orientation; retain all other EXIF.
            exif = frame.getexif()
            if 274 in exif:
                del exif[274]
            if exif:
                frame.info["exif"] = exif.tobytes()
            loaded.append(frame)
        return loaded


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
    files = [f for f in os.listdir(folder)
             if is_image_file(os.path.join(folder, f), validate=True)]
    files.sort(key=natural_sort_key)
    return files


def image_paths_in(folder):
    """เหมือน list_images_sorted แต่คืน path เต็ม"""
    return [os.path.join(folder, f) for f in list_images_sorted(folder)]
