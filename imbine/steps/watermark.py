# -*- coding: utf-8 -*-
"""ขั้นตอน: ใส่ลายน้ำลงภาพผลลัพธ์"""

from ..i18n import M
from ..pipeline import Step
from ..watermark import apply_watermark


class WatermarkStep(Step):
    """
    อ่าน/เขียน ctx.results

    อยู่ *หลัง* stitch เพราะลายน้ำควรมีอันเดียวต่อไฟล์ผลลัพธ์ ไม่ใช่อันหนึ่ง
    ต่อหน้าต้นฉบับ — ถ้าใส่ก่อนต่อ ภาพยาว ๆ หนึ่งไฟล์จะเต็มไปด้วยลายน้ำซ้ำ ๆ
    ทุกช่วงความสูงของหน้าเดิม
    """

    name = "watermark"
    label_key = "step.watermark"

    def is_enabled(self, ctx):
        spec = getattr(ctx.config, "watermark", None)
        return bool(spec and spec.get("enabled"))

    def run(self, ctx):
        spec = ctx.config.watermark
        total = len(ctx.results)
        marked = []
        for i, img in enumerate(ctx.results, start=1):
            ctx.cancel.check()
            marked.append(apply_watermark(img, spec))
            ctx.progress.report(i, total,
                                M("progress.watermarked", done=i, total=total))
        ctx.results = marked
