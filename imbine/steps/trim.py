# -*- coding: utf-8 -*-
"""ขั้นตอน: ตัดขอบว่างและตัดส่วนที่ซ้ำระหว่างหน้า"""

from ..i18n import M
from ..pipeline import Step
from ..trim import dedupe_sequence, trim_border


class TrimStep(Step):
    """
    อ่าน/เขียน ctx.images

    ต้องอยู่ *ก่อน* uniform เพราะการปรับความกว้างให้เท่ากันคิดจากภาพหลังตัดขอบ
    ถ้าตัดทีหลัง ภาพที่มีขอบหนาจะดึงความกว้างมาตรฐานให้ใหญ่เกินจริง

    ปิดอยู่เป็นค่าเริ่มต้น — ผู้ใช้ต้องเปิดเอง เพราะการตัดขอบเป็นการตัดสินใจ
    แทนผู้ใช้ว่าอะไรคือ "ขอบ" ซึ่งบางเรื่องขอบขาวคือส่วนหนึ่งของงานออกแบบ
    """

    name = "trim"
    label_key = "step.trim"

    def is_enabled(self, ctx):
        cfg = ctx.config
        return bool(cfg.trim_borders or cfg.dedupe_overlap)

    def run(self, ctx):
        cfg = ctx.config
        total = len(ctx.images)

        if cfg.trim_borders:
            trimmed = []
            for i, img in enumerate(ctx.images, start=1):
                ctx.cancel.check()
                trimmed.append(trim_border(img, cfg.trim_tolerance))
                ctx.progress.report(i, total)
            ctx.images = trimmed
            ctx.progress.report(total, total,
                                M("progress.trimmed", count=total))

        if cfg.dedupe_overlap:
            ctx.cancel.check()
            ctx.images, removed = dedupe_sequence(
                ctx.images, max_search=cfg.overlap_max_px,
                tolerance=cfg.trim_tolerance, vertical=ctx.vertical)
            ctx.notes["overlaps_removed"] = removed
            ctx.progress.report(total, total,
                                M("progress.overlap_removed", count=removed))
