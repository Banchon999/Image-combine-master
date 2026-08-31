# -*- coding: utf-8 -*-
"""ขั้นตอน: แบ่งภาพออกเป็นกลุ่ม (1 กลุ่ม = 1 ไฟล์ผลลัพธ์)"""

from ..grouping import split_into_groups
from ..i18n import M
from ..pipeline import Step


class SplitStep(Step):
    """
    อ่าน ctx.images -> เขียน ctx.groups

    ต้องอยู่ *หลัง* uniform เสมอ เพราะการแบ่งตาม max_size คิดจากความสูง/กว้าง
    หลังปรับขนาดแล้ว ถ้าสลับลำดับกัน ไฟล์ผลลัพธ์จะเกินขนาดที่ผู้ใช้กำหนด
    """

    name = "split"
    label_key = "step.split"

    def run(self, ctx):
        cfg = ctx.config
        ctx.groups = split_into_groups(
            ctx.images,
            parts_count=cfg.parts_count,
            max_size=cfg.max_size,
            vertical=ctx.vertical,
        )
        ctx.progress.report(1, 1, M("progress.split_result",
                                    count=len(ctx.groups)))
