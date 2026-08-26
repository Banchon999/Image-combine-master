# -*- coding: utf-8 -*-
"""ขั้นตอนมาตรฐานของการต่อภาพ"""

from ..pipeline import Pipeline
from .load import LoadImagesStep
from .save import SaveStep
from .split import SplitStep
from .stitch import StitchStep
from .uniform import UniformSizeStep

__all__ = [
    "LoadImagesStep", "UniformSizeStep", "SplitStep", "StitchStep", "SaveStep",
    "build_default_pipeline",
]


def build_default_pipeline(save=True):
    """
    ประกอบสายมาตรฐาน: load -> uniform -> split -> stitch -> save

    save=False ใช้เมื่ออยากได้แค่ภาพผลลัพธ์ในหน่วยความจำ ไม่ต้องเขียนดิสก์
    (เช่นตอนทำ preview) — เป็นเหตุผลหลักที่แยกการบันทึกออกมาเป็นขั้นของตัวเอง
    """
    steps = [LoadImagesStep(), UniformSizeStep(), SplitStep(), StitchStep()]
    if save:
        steps.append(SaveStep())
    return Pipeline(steps, name="ต่อภาพ")
