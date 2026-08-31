# -*- coding: utf-8 -*-
"""ขั้นตอน: บันทึกผลลัพธ์ลงดิสก์"""

import os

from ..naming import build_output_name, ext_for
from ..output import save_image, unique_path
from ..pipeline import Step


class SaveStep(Step):
    """
    อ่าน ctx.results -> เขียนไฟล์ + เก็บ path ลง ctx.saved_paths

    ไม่เรียก output.save_results() ทั้งก้อน เพราะต้องรายงานความคืบหน้าและ
    เช็คการยกเลิกเป็นราย ๆ ไฟล์ (การเขียน JPEG สูงสองหมื่น px ใช้เวลาหลายวินาที
    ต่อไฟล์ ถ้ารายงานทีเดียวตอนจบ ผู้ใช้จะนึกว่าแอพค้าง)
    """

    name = "save"
    label_key = "step.save"

    def is_enabled(self, ctx):
        return bool(ctx.output_folder)

    def run(self, ctx):
        cfg = ctx.config
        os.makedirs(ctx.output_folder, exist_ok=True)
        ext = ext_for(cfg.fmt)
        total = len(ctx.results)
        saved = []

        for i, img in enumerate(ctx.results, start=1):
            ctx.cancel.check()
            base = build_output_name(cfg.name_pattern, i, total,
                                     ctx.folder_name)
            path = os.path.join(ctx.output_folder, base + ext)
            if not cfg.overwrite:
                path = unique_path(path)
            options = cfg.export_options.get(cfg.fmt, cfg.export_options)
            saved.append(save_image(
                img, path, cfg.fmt, cfg.quality, cfg.alpha_background, options,
                ctx.warnings.append))
            ctx.progress.report(i, total, os.path.basename(path))

        ctx.saved_paths = saved
