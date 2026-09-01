# -*- coding: utf-8 -*-
"""เทสต์ระบบประมาณผลลัพธ์"""

import pytest

from imbine.api import run_stitch
from imbine.config import StitchConfig
from imbine.estimate import (BYTES_PER_PIXEL, OutputPlan, estimate_bytes,
                             human_bytes, limit_warnings, plan_for_paths,
                             plan_output, probe_sizes, stitched_size)


class Testอ่านขนาดไฟล์:
    def test_อ่านขนาดได้โดยไม่ต้อง_decode(self, write_image, tmp_path):
        paths = [write_image("a.jpg", 100, 50),
                 write_image("b.jpg", 80, 40)]
        assert probe_sizes(paths) == [(100, 50), (80, 40)]

    def test_ข้ามไฟล์เสียเงียบ_ๆ(self, write_image, tmp_path):
        """การรายงานไฟล์เสียเป็นหน้าที่ของ inspection ไม่ใช่ของตัวประมาณผล"""
        good = write_image("good.jpg", 10, 10)
        bad = tmp_path / "bad.jpg"
        bad.write_bytes(b"not an image")
        assert probe_sizes([good, str(bad)]) == [(10, 10)]

    def test_ไฟล์ไม่มีจริงก็ไม่พัง(self):
        assert probe_sizes(["/ไม่มี/ไฟล์นี้.jpg"]) == []


class Testขนาดหลังต่อภาพ:
    def test_แนวตั้งบวกความสูงเอาความกว้างมากสุด(self):
        assert stitched_size([(100, 50), (80, 30)], vertical=True) == (100, 80)

    def test_แนวนอนบวกความกว้างเอาความสูงมากสุด(self):
        assert stitched_size([(100, 50), (80, 30)], vertical=False) == (180, 50)

    def test_ไม่มีภาพคืนศูนย์(self):
        assert stitched_size([]) == (0, 0)


class Testแผนผลลัพธ์ตรงกับของจริง:
    """หัวใจของไฟล์นี้ — ตัวเลขที่พรีวิวต้องตรงกับไฟล์ที่ได้จริง"""

    @pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
    @pytest.mark.parametrize("parts,max_size", [(1, 0), (2, 0), (3, 0), (1, 120)])
    @pytest.mark.parametrize("uniform", [True, False])
    def test_ขนาดที่ทำนายตรงกับผลลัพธ์จริงทุกกรณี(
            self, write_image, tmp_path, orientation, parts, max_size, uniform):
        paths = [write_image(f"{i}.png", 40 + i * 20, 30 + i * 10)
                 for i in range(5)]
        config = StitchConfig(orientation=orientation, parts_count=parts,
                              max_size=max_size, uniform=uniform, fmt="PNG")

        plan = plan_output(probe_sizes(paths), config)
        จริง = run_stitch(paths, config=config).results

        assert plan.part_count == len(จริง)
        assert list(plan.parts) == [im.size for im in จริง]

    def test_นับจำนวนภาพต้นทางไว้ด้วย(self, write_image, tmp_path):
        paths = [write_image(f"{i}.png", 30, 30) for i in range(4)]
        plan = plan_for_paths(paths, StitchConfig(parts_count=2))
        assert plan.source_count == 4 and plan.part_count == 2

    def test_ไม่มีภาพได้แผนว่าง(self):
        plan = plan_output([], StitchConfig())
        assert not plan and plan.part_count == 0 and plan.total_bytes == 0
        assert isinstance(plan, OutputPlan)


class Testประมาณขนาดไฟล์:
    def test_ภาพใหญ่กว่าได้ตัวเลขใหญ่กว่า(self):
        assert estimate_bytes(1000, 1000) > estimate_bytes(500, 500)

    def test_คุณภาพสูงกว่าได้ไฟล์ใหญ่กว่าสำหรับ_format_ที่มีคุณภาพ(self):
        assert estimate_bytes(500, 500, "JPG", 95) > estimate_bytes(500, 500, "JPG", 50)

    def test_คุณภาพไม่มีผลกับ_format_ไร้สูญเสีย(self):
        """PNG ไม่มี quality — เลื่อนสไลเดอร์แล้วตัวเลขต้องไม่ขยับ"""
        assert estimate_bytes(500, 500, "PNG", 95) == estimate_bytes(500, 500, "PNG", 10)

    def test_png_ใหญ่กว่า_jpg_ที่ขนาดเท่ากัน(self):
        assert estimate_bytes(800, 800, "PNG") > estimate_bytes(800, 800, "JPG", 92)

    def test_format_ที่ไม่รู้จักก็ยังได้ตัวเลข(self):
        assert estimate_bytes(100, 100, "ไม่รู้จัก") > 0

    def test_jpg_กับ_jpeg_ให้ผลเท่ากัน(self):
        assert estimate_bytes(300, 300, "JPG", 80) == estimate_bytes(300, 300, "JPEG", 80)
        assert "JPG" not in BYTES_PER_PIXEL  # ใช้ชื่อ canonical เท่านั้น


class Testเตือนเกินลิมิตของ_format:
    def test_เตือนเมื่อสูงเกินลิมิตของ_webp(self):
        warnings = limit_warnings([(1000, 20000)], "WEBP")
        assert len(warnings) == 1
        assert "16383" in warnings[0]

    def test_ไม่เตือนเมื่ออยู่ในลิมิต(self):
        assert limit_warnings([(1000, 8000)], "WEBP") == []

    def test_บอกว่าไฟล์ที่เท่าไหร่มีปัญหา(self):
        warnings = limit_warnings([(100, 100), (100, 99999)], "JPG")
        assert len(warnings) == 1 and warnings[0].params["index"] == 2

    def test_แผนผลลัพธ์พกคำเตือนมาด้วย(self, write_image, tmp_path):
        paths = [write_image(f"{i}.png", 100, 9000) for i in range(2)]
        plan = plan_for_paths(paths, StitchConfig(fmt="WEBP", parts_count=1))
        assert plan.parts == ((100, 18000),)
        assert len(plan.warnings) == 1

    def test_format_ที่ไม่มีลิมิตไม่เตือน(self):
        assert limit_warnings([(999999, 999999)], "TIFF") == []


class Testแปลงไบต์เป็นข้อความ:
    @pytest.mark.parametrize("value,expected", [
        (512, "512 B"), (2048, "2.0 KB"), (5 * 1024 ** 2, "5.0 MB"),
        (3 * 1024 ** 3, "3.0 GB"),
    ])
    def test_เลือกหน่วยที่อ่านง่าย(self, value, expected):
        assert human_bytes(value) == expected
