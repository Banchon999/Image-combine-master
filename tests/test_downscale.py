# -*- coding: utf-8 -*-
"""เทสต์ขั้นตอนย่อภาพสำหรับพรีวิว"""

import pytest
from PIL import Image

from imbine.config import StitchConfig
from imbine.pipeline import PipelineContext
from imbine.steps import build_default_pipeline
from imbine.steps.downscale import DownscaleStep


def ctx_with(pages, w=800, h=1200, **config):
    ctx = PipelineContext(config=StitchConfig(**config))
    ctx.images = [Image.new("RGB", (w, h)) for _ in range(pages)]
    return ctx


class Testเปิดปิด:
    def test_ปิดอยู่เป็นค่าเริ่มต้น(self):
        assert DownscaleStep().is_enabled(ctx_with(3)) is False

    def test_เปิดเมื่อมีงบพิกเซล(self):
        assert DownscaleStep().is_enabled(
            ctx_with(3, preview_max_pixels=1000)) is True

    def test_is_enabled_ต้องไม่ดู_ctx_images(self):
        """
        กันบั๊กที่เคยเกิดจริง: Pipeline.run เรียก is_enabled ของทุกขั้น *ก่อน*
        เริ่มรัน ตอนนั้น ctx.images ยังว่างเพราะ load ยังไม่ทำงาน ขั้นที่เช็ค
        ctx.images จะถูกปิดเงียบ ๆ ตลอดกาลและพรีวิวจะไม่เคยถูกย่อเลย
        """
        ctx = PipelineContext(config=StitchConfig(preview_max_pixels=1000))
        assert ctx.images == []
        assert DownscaleStep().is_enabled(ctx) is True

    def test_อยู่ในสายมาตรฐานแต่ถูกข้ามเมื่อไม่ได้ตั้งงบ(self):
        pipe = build_default_pipeline()
        assert "downscale" in pipe.step_names()
        assert DownscaleStep().is_enabled(ctx_with(3)) is False


class Testตัวคูณย่อ:
    def test_เล็กกว่างบแล้วไม่ย่อเลย(self):
        ctx = ctx_with(3, preview_max_pixels=12_000_000)
        DownscaleStep().run(ctx)
        assert [im.size for im in ctx.images] == [(800, 1200)] * 3
        assert ctx.notes["preview_scale"] == 1.0

    def test_ใหญ่กว่างบแล้วย่อจนพอดีงบ(self):
        budget = 12_000_000
        ctx = ctx_with(40, preview_max_pixels=budget)
        DownscaleStep().run(ctx)
        w = max(im.width for im in ctx.images)
        h = sum(im.height for im in ctx.images)
        assert w * h <= budget * 1.02      # เผื่อการปัดเศษ
        assert w * h > budget * 0.95       # ต้องไม่ย่อเกินจำเป็น

    def test_คิดจากขนาดรวมไม่ใช่ขนาดของภาพแต่ละใบ(self):
        """
        หัวใจของขั้นนี้ — 40 ใบที่แต่ละใบเล็กกว่างบ แต่รวมกันแล้วเกิน
        ต้องถูกย่อ ไม่ใช่ปล่อยผ่านเพราะดูทีละใบแล้วไม่เกิน
        """
        ctx = ctx_with(40, preview_max_pixels=12_000_000)
        assert 800 * 1200 < 12_000_000     # ทีละใบไม่เกินงบ
        DownscaleStep().run(ctx)
        assert ctx.images[0].size != (800, 1200)

    def test_ความกว้างไม่ถูกย่อจนดูอะไรไม่ออก(self):
        """
        เหตุผลที่งบเป็น "จำนวนพิกเซล" ไม่ใช่ "กรอบสี่เหลี่ยม" — ถ้าบังคับให้
        ทั้งกว้างและสูงไม่เกิน 2400 ภาพนี้จะเหลือกว้าง 40 px
        """
        ctx = ctx_with(40, preview_max_pixels=12_000_000)
        DownscaleStep().run(ctx)
        assert ctx.images[0].width > 300

    def test_แนวนอนคิดจากความกว้างรวม(self):
        ctx = ctx_with(40, w=1200, h=800, orientation="horizontal",
                       preview_max_pixels=12_000_000)
        DownscaleStep().run(ctx)
        total_w = sum(im.width for im in ctx.images)
        max_h = max(im.height for im in ctx.images)
        assert total_w * max_h <= 12_000_000 * 1.02

    def test_ไม่มีภาพก็ไม่พัง(self):
        ctx = PipelineContext(config=StitchConfig(preview_max_pixels=1000))
        DownscaleStep().run(ctx)
        assert ctx.images == []


class Testสายพรีวิว:
    def test_สายพรีวิวไม่บันทึกไฟล์(self):
        from imbine.steps import build_preview_pipeline
        assert "save" not in build_preview_pipeline().step_names()

    def test_ย่อจริงเมื่อรันทั้งสาย(self, write_image, tmp_path):
        from imbine.api import run_stitch
        from imbine.steps import build_preview_pipeline
        paths = [write_image(f"{i:02d}.png", 400, 600) for i in range(10)]
        config = StitchConfig(preview_max_pixels=200_000, fmt="PNG")
        results = run_stitch(paths, config=config,
                             pipeline=build_preview_pipeline()).results
        w, h = results[0].size
        assert w * h <= 200_000 * 1.05
        assert (w, h) != (400, 6000)   # ต้องถูกย่อจริง ไม่ใช่ผ่านมาเฉย ๆ
