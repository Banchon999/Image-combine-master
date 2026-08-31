# -*- coding: utf-8 -*-
"""ขั้นตอน: ย่อภาพก่อนต่อ — มีไว้สำหรับโหมดพรีวิวโดยเฉพาะ"""

import math

from ..compose import RESAMPLE
from ..pipeline import Step


class DownscaleStep(Step):
    """
    อ่าน/เขียน ctx.images — ย่อทุกภาพให้ผลลัพธ์ที่ต่อแล้วมีพิกเซลรวมไม่เกิน
    ``config.preview_max_pixels``

    **ต้องคิดจากขนาดรวม ไม่ใช่ขนาดของภาพแต่ละใบ** เพราะการต่อภาพคือการบวก
    ความสูงกันไปเรื่อย ๆ การจำกัดว่า "ภาพแต่ละใบสูงไม่เกิน 1400" ไม่ได้ช่วย
    อะไรเลยเมื่อมี 50 ใบ — ยังได้ภาพสูง 70,000 px เหมือนเดิม

    **และต้องคิดเป็นจำนวนพิกเซล ไม่ใช่กรอบสี่เหลี่ยม** ถ้าบังคับว่าทั้งกว้าง
    และสูงต้องไม่เกิน N ภาพเว็บตูนที่สูง 48,000 px จะถูกย่อจนกว้างเหลือ 40 px
    ซึ่งบอกอะไรไม่ได้เลย งบแบบ "พิกเซลรวม" ให้ผลตามสัดส่วนจริง: ตอนสั้นได้
    ความละเอียดเต็ม ตอนยาวถูกย่อลงเท่าที่จำเป็นเท่านั้น

    ปิดอยู่เสมอในสายมาตรฐาน (preview_max_pixels = 0) — งานส่งออกจริงต้องได้
    ความละเอียดเต็ม
    """

    name = "downscale"
    label_key = "step.downscale"

    def is_enabled(self, ctx):
        # ดูได้แค่ config เท่านั้น ห้ามดู ctx.images — Pipeline.run เรียก
        # is_enabled ของทุกขั้น *ก่อน* เริ่มรัน ตอนนั้น ctx.images ยังว่างอยู่
        # เสมอเพราะ load ยังไม่ทำงาน เช็ค ctx.images ตรงนี้จะทำให้ขั้นนี้ถูก
        # ปิดเงียบ ๆ ตลอดกาล
        return bool(getattr(ctx.config, "preview_max_pixels", 0) > 0)

    def _scale_factor(self, ctx):
        """ตัวคูณย่อที่ทำให้ภาพผลลัพธ์มีพิกเซลรวมพอดีงบ (ไม่เกิน 1.0)"""
        budget = int(ctx.config.preview_max_pixels)
        if ctx.vertical:
            along = sum(im.height for im in ctx.images)
            across = max(im.width for im in ctx.images)
        else:
            along = sum(im.width for im in ctx.images)
            across = max(im.height for im in ctx.images)

        total = along * across
        if total <= budget or total <= 0:
            return 1.0
        # พื้นที่โตตามกำลังสองของตัวคูณ จึงต้องใช้รากที่สอง
        return math.sqrt(budget / total)

    def run(self, ctx):
        if not ctx.images:
            return
        factor = self._scale_factor(ctx)
        total = len(ctx.images)
        ctx.notes["preview_scale"] = factor

        if factor >= 1.0:
            ctx.progress.report(total, total)
            return

        out = []
        for i, img in enumerate(ctx.images, start=1):
            ctx.cancel.check()
            out.append(img.resize((max(1, round(img.width * factor)),
                                   max(1, round(img.height * factor))),
                                  RESAMPLE))
            ctx.progress.report(i, total)
        ctx.images = out
