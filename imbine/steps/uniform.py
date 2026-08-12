# -*- coding: utf-8 -*-
"""ขั้นตอน: ปรับด้านตัดของทุกภาพให้เท่ากัน"""

from ..compose import fit_uniform
from ..pipeline import Step


class UniformSizeStep(Step):
    """
    อ่าน/เขียน ctx.images

    ปิดได้ด้วย config.uniform=False — เมื่อปิด ภาพขนาดไม่เท่ากันจะถูกจัด
    กึ่งกลางตอนต่อแทน (StitchStep จัดการให้) ไม่ใช่ว่าจะพัง
    """

    name = "uniform"

    def is_enabled(self, ctx):
        return bool(ctx.config.uniform)

    def run(self, ctx):
        total = len(ctx.images)
        ctx.progress.report(0, total)
        ctx.images = fit_uniform(ctx.images, vertical=ctx.vertical)
        ctx.progress.report(total, total)
