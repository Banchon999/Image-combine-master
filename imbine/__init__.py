# -*- coding: utf-8 -*-
"""
ImageStitcher — เครื่องมือต่อภาพเว็บตูน

โมดูลนี้เปิดเฉพาะ "ส่วนตรรกะ" ซึ่งไม่ import UI ใด ๆ ทั้งสิ้น
เปิด `import imbine` ได้บนเครื่องที่ไม่มี tkinter หรือไม่มีจอ (เช่นใน CI)
ส่วน UI อยู่ใน imbine.ui และต้องเรียกแยกเอง

รันแอพ:  python -m imbine
"""

__version__ = "0.2.0"

from .api import run_stitch, stitch_images
from .compose import fit_uniform, load_rgb, stitch_group
from .config import FORMATS, ORIENTATIONS, StitchConfig
from .grouping import split_into_groups
from .images import (IMAGE_EXTS, image_paths_in, is_image_file,
                     list_images_sorted, natural_sort_key)
from .inspection import (InspectionReport, check_output_path,
                         find_existing_outputs, inspect_images)
from .naming import build_output_name, ext_for
from .output import save_image, save_results, unique_path
from .pipeline import (Cancelled, CancelToken, Pipeline, PipelineContext,
                       Progress, ProgressEvent, Step)
from .steps import (LoadImagesStep, SaveStep, SplitStep, StitchStep,
                    UniformSizeStep, build_default_pipeline)

__all__ = [
    "__version__",
    # ค่าตั้ง
    "StitchConfig", "FORMATS", "ORIENTATIONS",
    # ไฟล์และการเรียงลำดับ
    "IMAGE_EXTS", "is_image_file", "natural_sort_key", "list_images_sorted",
    "image_paths_in",
    # ตรวจสอบก่อนทำงาน
    "InspectionReport", "inspect_images", "check_output_path",
    "find_existing_outputs",
    # งานพิกเซล
    "fit_uniform", "stitch_group", "load_rgb", "split_into_groups",
    # ชื่อไฟล์และการบันทึก
    "build_output_name", "ext_for", "save_results", "save_image",
    "unique_path",
    # pipeline
    "Pipeline", "PipelineContext", "Step", "Progress", "ProgressEvent",
    "CancelToken", "Cancelled", "build_default_pipeline",
    "LoadImagesStep", "UniformSizeStep", "SplitStep", "StitchStep",
    "SaveStep",
    # หน้าบ้าน
    "run_stitch", "stitch_images",
]
