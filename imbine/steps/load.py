# -*- coding: utf-8 -*-
"""ขั้นตอน: เปิดไฟล์ภาพเข้าหน่วยความจำ"""

import os

from ..i18n import M
from ..images import load_image
from ..pipeline import Step


class LoadImagesStep(Step):
    """
    อ่าน ctx.source_paths -> เขียน ctx.images

    แปลงเป็น RGB ทุกใบตั้งแต่ตรงนี้ เพราะขั้นตอนหลังจากนี้ (resize, paste,
    save เป็น JPEG) ล้วนคาดหวังโหมดเดียวกัน การแปลงกระจัดกระจายทีหลัง
    จะทำให้ภาพ RGBA/P หลุดไปโผล่เป็นสีเพี้ยนตอนบันทึก

    ผลข้างเคียงที่ต้องรู้: ภาพโปร่งใสจะถูกทับด้วยพื้นดำตามพฤติกรรมของ
    convert("RGB") — ยังไม่ได้จัดการเรื่องนี้ ถือเป็นพฤติกรรมเดิมของโปรแกรม
    """

    name = "load"
    label_key = "step.load"

    def run(self, ctx):
        paths = list(ctx.source_paths)
        if not paths:
            raise ValueError(M("core.error.no_images"))

        total = len(paths)
        images = []
        for i, path in enumerate(paths, start=1):
            ctx.cancel.check()
            images.extend(load_image(path, ctx.config.multi_frame))
            ctx.progress.report(i, total, os.path.basename(path))
        ctx.images = images
