# -*- coding: utf-8 -*-
"""เทสต์การตัดขอบและตัดส่วนซ้ำ"""

import pytest
from PIL import Image

from imbine.config import StitchConfig
from imbine.pipeline import PipelineContext
from imbine.steps.trim import TrimStep
from imbine.trim import (dedupe_sequence, drop_overlap, find_overlap,
                         trim_border)

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)


def กรอบขาว(inner_w, inner_h, pad, color=BLUE):
    """ภาพสี่เหลี่ยมสีเดียวที่มีขอบขาวหนา pad รอบด้าน"""
    img = Image.new("RGB", (inner_w + pad * 2, inner_h + pad * 2), WHITE)
    img.paste(Image.new("RGB", (inner_w, inner_h), color), (pad, pad))
    return img


def ภาพสุ่ม(w, h, seed=0):
    """ภาพที่แต่ละแถวต่างกันจริง — ใช้ทดสอบการหาส่วนซ้อน"""
    img = Image.new("RGB", (w, h))
    img.putdata([((x * 7 + y * 13 + seed) % 256,
                  (y * 31 + seed) % 256,
                  (x * 3 + seed) % 256)
                 for y in range(h) for x in range(w)])
    return img


class Testตัดขอบ:
    def test_ตัดขอบสีเดียวออกได้(self):
        assert trim_border(กรอบขาว(40, 20, pad=10)).size == (40, 20)

    def test_ภาพที่ไม่มีขอบไม่ถูกแตะ(self):
        img = Image.new("RGB", (30, 30), BLUE)
        assert trim_border(img) is img

    def test_ภาพสีเดียวทั้งใบคืนภาพเดิมไม่ใช่ภาพขนาดศูนย์(self):
        """getbbox() คืน None เมื่อไม่มีอะไรต่างจากพื้นหลัง — ต้องไม่ crop ด้วยค่านั้น"""
        img = Image.new("RGB", (25, 25), WHITE)
        assert trim_border(img).size == (25, 25)

    def test_tolerance_ช่วยตัดขอบที่มี_noise(self):
        """ขอบขาวใน JPEG จริงไม่เคยเป็น 255 เป๊ะทุกจุด"""
        img = กรอบขาว(20, 20, pad=8)
        img.putpixel((2, 2), (250, 252, 251))     # noise บนขอบ
        assert trim_border(img, tolerance=0).size != (20, 20)
        assert trim_border(img, tolerance=16).size == (20, 20)

    def test_ระบุสีพื้นหลังเองได้(self):
        img = Image.new("RGB", (40, 40), BLUE)
        img.paste(Image.new("RGB", (10, 10), WHITE), (15, 15))
        assert trim_border(img, background=BLUE).size == (10, 10)

    def test_ภาพเดิมไม่ถูกแก้(self):
        img = กรอบขาว(20, 20, pad=5)
        trim_border(img)
        assert img.size == (30, 30)


class Testหาส่วนซ้อน:
    def test_เจอส่วนที่ซ้ำกันตรงรอยต่อ(self):
        เต็ม = ภาพสุ่ม(40, 200)
        ก่อน = เต็ม.crop((0, 0, 40, 120))
        หลัง = เต็ม.crop((0, 90, 40, 200))     # ซ้อนกัน 30 px
        assert find_overlap(ก่อน, หลัง, max_search=80) == 30

    def test_ภาพที่ไม่เกี่ยวกันคืนศูนย์(self):
        assert find_overlap(ภาพสุ่ม(40, 100, seed=1),
                            ภาพสุ่ม(40, 100, seed=99)) == 0

    def test_ความกว้างไม่เท่ากันไม่เทียบ(self):
        """เทียบแถวต่อแถวข้ามภาพคนละความกว้างไม่มีความหมาย"""
        assert find_overlap(ภาพสุ่ม(40, 100), ภาพสุ่ม(60, 100)) == 0

    def test_ไม่นับส่วนซ้อนสั้นเกินไป(self):
        """ขอบขาวไม่กี่แถวที่บังเอิญเหมือนกันไม่ใช่การซ้อนกันจริง"""
        เต็ม = ภาพสุ่ม(40, 200)
        ก่อน, หลัง = เต็ม.crop((0, 0, 40, 100)), เต็ม.crop((0, 97, 40, 200))
        assert find_overlap(ก่อน, หลัง, max_search=80, minimum=20) == 0

    def test_max_search_จำกัดความลึกที่ค้นหา(self):
        เต็ม = ภาพสุ่ม(40, 300)
        ก่อน, หลัง = เต็ม.crop((0, 0, 40, 200)), เต็ม.crop((0, 100, 40, 300))
        assert find_overlap(ก่อน, หลัง, max_search=50) == 0     # ซ้อน 100 แต่ค้นแค่ 50
        assert find_overlap(ก่อน, หลัง, max_search=150) == 100

    def test_แนวนอนเทียบเป็นคอลัมน์(self):
        เต็ม = ภาพสุ่ม(200, 40)
        ก่อน, หลัง = เต็ม.crop((0, 0, 120, 40)), เต็ม.crop((90, 0, 200, 40))
        assert find_overlap(ก่อน, หลัง, max_search=80, vertical=False) == 30


class Testตัดส่วนซ้อนออก:
    def test_ตัดหัวภาพออกตามจำนวนที่บอก(self):
        assert drop_overlap(ภาพสุ่ม(40, 100), 30).size == (40, 70)

    def test_ตัดศูนย์คืนภาพเดิม(self):
        img = ภาพสุ่ม(40, 100)
        assert drop_overlap(img, 0) is img

    def test_ตัดเกินความสูงคืนภาพเดิมแทนที่จะได้ภาพเปล่า(self):
        img = ภาพสุ่ม(40, 50)
        assert drop_overlap(img, 999) is img

    def test_ตัดทั้งชุดแล้วต่อกันได้ความสูงเท่าต้นฉบับ(self):
        เต็ม = ภาพสุ่ม(40, 300)
        ชิ้น = [เต็ม.crop((0, 0, 40, 120)),
                เต็ม.crop((0, 100, 40, 220)),
                เต็ม.crop((0, 200, 40, 300))]
        ผล, ตัดไป = dedupe_sequence(ชิ้น, max_search=60)
        assert ตัดไป == 2
        assert sum(im.height for im in ผล) == 300

    def test_ภาพเดียวไม่ต้องทำอะไร(self):
        img = ภาพสุ่ม(40, 50)
        ผล, ตัดไป = dedupe_sequence([img])
        assert ผล == [img] and ตัดไป == 0


class TestTrimStep:
    def make_ctx(self, images, **config):
        ctx = PipelineContext(config=StitchConfig(**config))
        ctx.images = list(images)
        return ctx

    def test_ปิดอยู่เป็นค่าเริ่มต้น(self):
        assert TrimStep().is_enabled(self.make_ctx([])) is False

    @pytest.mark.parametrize("field", ["trim_borders", "dedupe_overlap"])
    def test_เปิดเมื่อตั้งค่าอย่างใดอย่างหนึ่ง(self, field):
        assert TrimStep().is_enabled(self.make_ctx([], **{field: True})) is True

    def test_ตัดขอบทุกภาพในชุด(self):
        ctx = self.make_ctx([กรอบขาว(20, 20, pad=6)] * 3, trim_borders=True)
        TrimStep().run(ctx)
        assert [im.size for im in ctx.images] == [(20, 20)] * 3

    def test_ตัดส่วนซ้อนแล้วจดจำนวนไว้ใน_notes(self):
        เต็ม = ภาพสุ่ม(40, 200)
        ctx = self.make_ctx([เต็ม.crop((0, 0, 40, 120)),
                             เต็ม.crop((0, 90, 40, 200))],
                            dedupe_overlap=True, overlap_max_px=80)
        TrimStep().run(ctx)
        assert ctx.notes["overlaps_removed"] == 1
        assert sum(im.height for im in ctx.images) == 200
