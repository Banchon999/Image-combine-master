# -*- coding: utf-8 -*-
"""ขั้นตอน: ต่อภาพในแต่ละกลุ่มให้เป็นภาพเดียว"""

from ..compose import stitch_group
from ..pipeline import Step


class StitchStep(Step):
    """
    อ่าน ctx.groups -> เขียน ctx.results

    พอต่อเสร็จจะปล่อย ctx.images / ctx.groups ทิ้ง เพราะภาพต้นทางทั้งชุด
    ไม่ถูกใช้อีกแล้ว แต่ยังกินแรมอยู่เท่าเดิม — สำคัญมากเมื่อมีขั้น upscale
    มาต่อท้าย load ในอนาคต (ภาพ 4x กินแรม 16 เท่าของเดิม)
    """

    name = "stitch"

    def run(self, ctx):
        total = len(ctx.groups)
        results = []
        for i, group in enumerate(ctx.groups, start=1):
            ctx.cancel.check()
            results.append(stitch_group(
                group, vertical=ctx.vertical, bg_color=ctx.config.bg_color))
            ctx.progress.report(i, total, f"ไฟล์ที่ {i}/{total}")
        ctx.results = results

        # คืนแรมของภาพต้นทาง — results เป็นผืนผ้าใบใหม่ ไม่ได้อ้างถึงภาพเดิม
        ctx.images = []
        ctx.groups = []
