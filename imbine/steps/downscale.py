# -*- coding: utf-8 -*-
"""ขั้นตอน: ย่อภาพก่อนต่อ — มีไว้สำหรับโหมดพรีวิวโดยเฉพาะ"""

from ..compose import RESAMPLE
from ..pipeline import Step


class DownscaleStep(Step):
    """
    อ่าน/เขียน ctx.images — ย่อทุกภาพให้ด้านยาวสุดไม่เกิน preview_max_dimension

    เหตุผลที่ต้องมี: พรีวิวเว็บตูนหนึ่งตอนคือการต่อภาพสูง 20,000 px ขึ้นไป
    ซึ่งกินแรมหลายร้อยเมกะไบต์และใช้เวลาหลายวินาที ทั้งที่ผลลัพธ์จะถูกย่อลง
    เหลือความกว้างไม่กี่ร้อยพิกเซลบนจออยู่ดี การย่อตั้งแต่ก่อนต่อทำให้พรีวิว
    เร็วขึ้นเป็นสิบเท่าและไม่มีทางทำให้แรมเต็ม

    ปิดอยู่เสมอในสายมาตรฐาน (preview_max_dimension = 0) — งานส่งออกจริง
    ต้องได้ความละเอียดเต็ม
    """

    name = "downscale"
    label_key = "step.downscale"

    def is_enabled(self, ctx):
        return bool(getattr(ctx.config, "preview_max_dimension", 0) > 0)

    def run(self, ctx):
        limit = int(ctx.config.preview_max_dimension)
        total = len(ctx.images)
        out = []
        for i, img in enumerate(ctx.images, start=1):
            ctx.cancel.check()
            longest = max(img.width, img.height)
            if longest > limit:
                ratio = limit / longest
                img = img.resize((max(1, round(img.width * ratio)),
                                  max(1, round(img.height * ratio))), RESAMPLE)
            out.append(img)
            ctx.progress.report(i, total)
        ctx.images = out
