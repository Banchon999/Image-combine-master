# -*- coding: utf-8 -*-
"""ขั้นตอนมาตรฐานของการต่อภาพ"""

from ..i18n import translate
from ..pipeline import Pipeline
from .downscale import DownscaleStep
from .load import LoadImagesStep
from .save import SaveStep
from .split import SplitStep
from .stitch import StitchStep
from .trim import TrimStep
from .uniform import UniformSizeStep
from .watermark import WatermarkStep

__all__ = [
    "LoadImagesStep", "TrimStep", "DownscaleStep", "UniformSizeStep",
    "SplitStep", "StitchStep", "WatermarkStep", "SaveStep",
    "build_default_pipeline", "build_preview_pipeline",
]


def build_default_pipeline(save=True):
    """
    ประกอบสายมาตรฐาน:

        load -> trim -> downscale -> uniform -> split -> stitch -> watermark -> save

    trim / downscale / watermark ปิดอยู่เป็นค่าเริ่มต้น (is_enabled คืน False)
    Pipeline.run จะคัดออกก่อนนับขั้น สายที่รันจริงจึงเหลือเท่าเดิมทุกประการ
    จนกว่าผู้ใช้จะเปิดใช้เอง

    save=False ใช้เมื่ออยากได้แค่ภาพผลลัพธ์ในหน่วยความจำ ไม่ต้องเขียนดิสก์
    (เช่นตอนทำ preview) — เป็นเหตุผลหลักที่แยกการบันทึกออกมาเป็นขั้นของตัวเอง
    """
    steps = [LoadImagesStep(), TrimStep(), DownscaleStep(), UniformSizeStep(),
             SplitStep(), StitchStep(), WatermarkStep()]
    if save:
        steps.append(SaveStep())
    return Pipeline(steps, name=translate("pipeline.name"))


def build_preview_pipeline():
    """
    สายสำหรับพรีวิว — เหมือนสายมาตรฐานแต่ไม่บันทึกไฟล์

    ตัวที่ทำให้พรีวิวเร็วคือ DownscaleStep ซึ่งเปิดทำงานเมื่อ config มี
    preview_max_dimension > 0 ผู้เรียกจึงควรใช้ config.replace() ตั้งค่านั้น
    ก่อนส่งเข้ามา ไม่ใช่แก้ config ที่ผู้ใช้ตั้งไว้
    """
    return build_default_pipeline(save=False)
