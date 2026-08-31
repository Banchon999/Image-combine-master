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
from .compose import (fit_uniform, load_rgb, stitch_group, uniform_size,
                      uniform_sizes, uniform_target)
from .config import FORMATS, ORIENTATIONS, StitchConfig
from .estimate import (OutputPlan, estimate_bytes, human_bytes, limit_warnings,
                       plan_for_paths, plan_output, probe_sizes, stitched_size)
from .formats import (FORMAT_REGISTRY, FormatCapabilities,
                      available_export_formats, capabilities,
                      decoder_available, encoder_available)
from .grouping import group_boundaries, split_into_groups
from .i18n import (DEFAULT_LOCALE, Message, available_locales, get_locale,
                   set_locale, t, translate)
from .images import (IMAGE_EXTS, ImageValidationError, image_paths_in,
                     inspect_image, is_image_file, list_images_sorted,
                     load_image, natural_sort_key)
from .inspection import (InspectionReport, check_output_path,
                         find_existing_outputs, inspect_images)
from .naming import build_output_name, ext_for
from .output import export_warnings, save_image, save_results, unique_path
from .pipeline import (Cancelled, CancelToken, Pipeline, PipelineContext,
                       Progress, ProgressEvent, Step)
from .steps import (DownscaleStep, LoadImagesStep, SaveStep, SplitStep,
                    StitchStep, TrimStep, UniformSizeStep, WatermarkStep,
                    build_default_pipeline, build_preview_pipeline)
from .trim import dedupe_sequence, drop_overlap, find_overlap, trim_border
from .userdata import (delete_preset, list_presets, load_preset, load_settings,
                       save_preset, save_settings)
from .watermark import ANCHORS, apply_watermark

__all__ = [
    "__version__",
    # ภาษา
    "Message", "translate", "t", "set_locale", "get_locale",
    "available_locales", "DEFAULT_LOCALE",
    # ค่าตั้ง
    "StitchConfig", "FORMATS", "ORIENTATIONS", "FORMAT_REGISTRY",
    "FormatCapabilities", "capabilities", "available_export_formats",
    "decoder_available", "encoder_available",
    # ไฟล์และการเรียงลำดับ
    "IMAGE_EXTS", "is_image_file", "natural_sort_key", "list_images_sorted",
    "image_paths_in", "inspect_image", "load_image", "ImageValidationError",
    # ตรวจสอบก่อนทำงาน
    "InspectionReport", "inspect_images", "check_output_path",
    "find_existing_outputs",
    # งานพิกเซล
    "fit_uniform", "stitch_group", "load_rgb", "split_into_groups",
    "group_boundaries", "uniform_target", "uniform_size", "uniform_sizes",
    "trim_border", "find_overlap", "drop_overlap", "dedupe_sequence",
    "apply_watermark", "ANCHORS",
    # ประมาณผลล่วงหน้า
    "OutputPlan", "plan_output", "plan_for_paths", "probe_sizes",
    "stitched_size", "estimate_bytes", "limit_warnings", "human_bytes",
    # ค่าตั้งของผู้ใช้และพรีเซ็ต
    "load_settings", "save_settings", "list_presets", "save_preset",
    "load_preset", "delete_preset",
    # ชื่อไฟล์และการบันทึก
    "build_output_name", "ext_for", "save_results", "save_image",
    "unique_path", "export_warnings",
    # pipeline
    "Pipeline", "PipelineContext", "Step", "Progress", "ProgressEvent",
    "CancelToken", "Cancelled", "build_default_pipeline",
    "build_preview_pipeline",
    "LoadImagesStep", "TrimStep", "DownscaleStep", "UniformSizeStep",
    "SplitStep", "StitchStep", "WatermarkStep", "SaveStep",
    # หน้าบ้าน
    "run_stitch", "stitch_images",
]
