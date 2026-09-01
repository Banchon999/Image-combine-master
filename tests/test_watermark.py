# -*- coding: utf-8 -*-
"""เทสต์ลายน้ำ"""

import pytest
from PIL import Image

from imbine.config import StitchConfig
from imbine.pipeline import PipelineContext
from imbine.steps.watermark import WatermarkStep
from imbine.watermark import (ANCHORS, apply_watermark, find_font_file,
                              load_font)

BLACK = (0, 0, 0)


def พื้นดำ(w=200, h=120):
    return Image.new("RGB", (w, h), BLACK)


def จุดที่ไม่ดำ(img):
    """คืน bounding box ของสิ่งที่ถูกวาดทับพื้นดำ"""
    return img.convert("RGB").getbbox()


class Testเปิดปิด:
    def test_ไม่เปิดใช้คืนภาพเดิม(self):
        img = พื้นดำ()
        assert apply_watermark(img, {"enabled": False, "text": "x"}) is img

    def test_spec_ว่างคืนภาพเดิม(self):
        img = พื้นดำ()
        assert apply_watermark(img, {}) is img
        assert apply_watermark(img, None) is img

    def test_เปิดแต่ไม่มีข้อความคืนภาพเดิม(self):
        img = พื้นดำ()
        assert apply_watermark(img, {"enabled": True, "text": ""}) is img

    def test_ไฟล์ภาพลายน้ำหายไม่ทำให้งานล้ม(self):
        """งานต่อภาพของผู้ใช้ไม่ควรพังเพราะลายน้ำ"""
        img = พื้นดำ()
        spec = {"enabled": True, "image": "/ไม่มี/ไฟล์.png"}
        assert apply_watermark(img, spec) is img


class Testลายน้ำข้อความ:
    def test_วาดอะไรบางอย่างลงบนภาพ(self):
        ผล = apply_watermark(พื้นดำ(), {"enabled": True, "text": "TEST",
                                        "opacity": 1.0})
        assert จุดที่ไม่ดำ(ผล) is not None

    def test_ภาพเดิมไม่ถูกแก้(self):
        img = พื้นดำ()
        apply_watermark(img, {"enabled": True, "text": "TEST", "opacity": 1.0})
        assert จุดที่ไม่ดำ(img) is None

    def test_คงโหมดสีเดิมไว้(self):
        """ถ้าปล่อยเป็น RGBA ไฟล์ JPEG จะต้องถูก flatten อีกรอบตอนบันทึก"""
        ผล = apply_watermark(พื้นดำ(), {"enabled": True, "text": "x",
                                        "opacity": 1.0})
        assert ผล.mode == "RGB"

    @pytest.mark.parametrize("anchor", sorted(ANCHORS))
    def test_วางได้ครบทุกตำแหน่งและอยู่ในกรอบภาพ(self, anchor):
        ผล = apply_watermark(พื้นดำ(400, 400),
                             {"enabled": True, "text": "AB", "opacity": 1.0,
                              "position": anchor, "margin": 10})
        box = จุดที่ไม่ดำ(ผล)
        assert box is not None
        assert box[0] >= 0 and box[1] >= 0
        assert box[2] <= 400 and box[3] <= 400

    def test_ตำแหน่งบนกับล่างให้ผลต่างกัน(self):
        บน = จุดที่ไม่ดำ(apply_watermark(พื้นดำ(400, 400),
                        {"enabled": True, "text": "A", "opacity": 1.0,
                         "position": "top-left", "margin": 10}))
        ล่าง = จุดที่ไม่ดำ(apply_watermark(พื้นดำ(400, 400),
                        {"enabled": True, "text": "A", "opacity": 1.0,
                         "position": "bottom-left", "margin": 10}))
        assert บน[1] < ล่าง[1]

    def test_ตำแหน่งที่ไม่รู้จักถอยไปใช้ค่าเริ่มต้นแทนที่จะพัง(self):
        ผล = apply_watermark(พื้นดำ(), {"enabled": True, "text": "x",
                                        "opacity": 1.0, "position": "ไม่มีจริง"})
        assert จุดที่ไม่ดำ(ผล) is not None

    def test_ข้อความภาษาไทยไม่ทำให้พัง(self):
        """ฟอนต์อาจไม่มีสระไทย แต่ต้องไม่โยน exception"""
        ผล = apply_watermark(พื้นดำ(), {"enabled": True, "text": "แปลไทย",
                                        "opacity": 1.0})
        assert ผล.size == (200, 120)


class Testลายน้ำรูปภาพ:
    def test_วางรูปลายน้ำลงบนภาพได้(self, tmp_path):
        mark = tmp_path / "mark.png"
        Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(mark)
        ผล = apply_watermark(พื้นดำ(400, 400),
                             {"enabled": True, "image": str(mark),
                              "opacity": 1.0, "scale": 0.25})
        box = จุดที่ไม่ดำ(ผล)
        assert box is not None and (box[2] - box[0]) == 100  # 400 * 0.25

    def test_ความโปร่งใสมีผลจริง(self, tmp_path):
        mark = tmp_path / "mark.png"
        Image.new("RGBA", (40, 40), (255, 255, 255, 255)).save(mark)
        spec = {"enabled": True, "image": str(mark), "scale": 0.5,
                "position": "center"}
        ทึบ = apply_watermark(พื้นดำ(200, 200), dict(spec, opacity=1.0))
        จาง = apply_watermark(พื้นดำ(200, 200), dict(spec, opacity=0.2))
        assert ทึบ.getpixel((100, 100)) > จาง.getpixel((100, 100))


class Testฟอนต์:
    def test_หาไฟล์ฟอนต์ที่ระบุเองได้ก่อนเสมอ(self, tmp_path):
        ปลอม = tmp_path / "custom.ttf"
        ปลอม.write_bytes(b"not really a font")
        assert find_font_file(str(ปลอม)) == str(ปลอม)

    def test_ฟอนต์ที่เสียถอยไปใช้ฟอนต์เริ่มต้นแทนที่จะพัง(self, tmp_path):
        ปลอม = tmp_path / "broken.ttf"
        ปลอม.write_bytes(b"not really a font")
        assert load_font(20, str(ปลอม)) is not None


class TestWatermarkStep:
    def make_ctx(self, results, **watermark):
        ctx = PipelineContext(config=StitchConfig(watermark=watermark))
        ctx.results = list(results)
        return ctx

    def test_ปิดอยู่เป็นค่าเริ่มต้น(self):
        assert WatermarkStep().is_enabled(self.make_ctx([])) is False

    def test_เปิดเมื่อ_enabled(self):
        ctx = self.make_ctx([], enabled=True, text="x")
        assert WatermarkStep().is_enabled(ctx) is True

    def test_ใส่ลายน้ำครบทุกไฟล์ผลลัพธ์(self):
        ctx = self.make_ctx([พื้นดำ(), พื้นดำ()], enabled=True, text="A",
                            opacity=1.0)
        WatermarkStep().run(ctx)
        assert all(จุดที่ไม่ดำ(im) is not None for im in ctx.results)

    def test_อยู่หลัง_stitch_เพื่อให้ได้ลายน้ำอันเดียวต่อไฟล์(self):
        from imbine.steps import build_default_pipeline
        names = build_default_pipeline().step_names()
        assert names.index("watermark") > names.index("stitch")
        assert names.index("watermark") < names.index("save")
