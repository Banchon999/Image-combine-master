# -*- coding: utf-8 -*-
"""เทสต์การสร้างชื่อไฟล์ผลลัพธ์"""

import pytest

from imbine import build_output_name, ext_for


class TestExtFor:

    @pytest.mark.parametrize("fmt,expected", [
        ("JPG", ".jpg"), ("jpg", ".jpg"),
        ("PNG", ".png"), ("png", ".png"),
        ("WEBP", ".webp"), ("webp", ".webp"),
        ("TIFF", ".tiff"), ("tiff", ".tiff"),
    ])
    def test_นามสกุลตามชนิด(self, fmt, expected):
        assert ext_for(fmt) == expected

    def test_ชนิดที่ไม่รู้จักตกเป็น_jpg(self):
        assert ext_for("") == ".jpg"


class TestBuildOutputName:

    @pytest.mark.parametrize("pattern,expected", [
        ("{n}", "7"),
        ("{n2}", "07"),
        ("{n3}", "007"),
        ("{total}", "20"),
        ("{folder}", "ตอนที่ 3"),
    ])
    def test_ตัวแปรแต่ละตัว(self, pattern, expected):
        assert build_output_name(pattern, 7, 20, "ตอนที่ 3") == expected

    def test_เติมศูนย์นำหน้าตามจำนวนหลัก(self):
        assert build_output_name("{n3}", 1, 5) == "001"
        assert build_output_name("{n2}", 1, 5) == "01"
        assert build_output_name("{n}", 1, 5) == "1"

    def test_แทนที่รอบเดียวไม่อ่านซ้ำ(self):
        # โฟลเดอร์ที่ชื่อพ้องกับตัวแปรต้องอยู่เฉย ๆ ไม่ถูกขยายต่อ
        assert build_output_name("{folder}", 7, 20, "{total}") == "{total}"
        assert build_output_name("{folder}", 7, 20, "{n}") == "{n}"

    def test_ตัวแปรที่ไม่รู้จักถูกปล่อยไว้ตามเดิม(self):
        assert build_output_name("{ไม่มีตัวนี้}_{n}", 4, 9) == "{ไม่มีตัวนี้}_4"

    def test_ผสมหลายตัวแปร(self):
        assert build_output_name("{folder}_{n2}_of_{total}", 3, 12,
                                 "ch01") == "ch01_03_of_12"

    def test_เลขเกินจำนวนหลักไม่ถูกตัด(self):
        assert build_output_name("{n2}", 100, 100) == "100"

    @pytest.mark.parametrize("bad", list('<>:"/\\|?*'))
    def test_อักขระต้องห้ามถูกแทนด้วยขีดล่าง(self, bad):
        assert build_output_name(f"a{bad}b", 1, 1) == "a_b"

    def test_pattern_ว่างได้ชื่อสำรอง(self):
        assert build_output_name("", 3, 5) == "output_3"
        assert build_output_name("   ", 3, 5) == "output_3"

    def test_ข้อความล้วนไม่มีตัวแปรก็ใช้ได้(self):
        assert build_output_name("รวมเล่ม", 1, 1) == "รวมเล่ม"

    def test_ตัดช่องว่างหัวท้าย(self):
        assert build_output_name("  {n}  ", 5, 9) == "5"

    def test_folder_ว่างไม่ทิ้งคำว่า_folder_ไว้(self):
        assert build_output_name("{folder}{n}", 2, 3, "") == "2"
