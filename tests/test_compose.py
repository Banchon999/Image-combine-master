# -*- coding: utf-8 -*-
"""เทสต์งานพิกเซล: ปรับขนาด, ต่อภาพ, เปิดไฟล์"""

import pytest
from PIL import Image

from conftest import BLUE, RED, WHITE
from imbine import fit_uniform, load_rgb, stitch_group


class TestFitUniform:

    def test_แนวตั้งทำให้กว้างเท่ากันหมด(self, img):
        out = fit_uniform([img(100, 50), img(200, 100), img(150, 30)],
                          vertical=True)
        assert {im.width for im in out} == {200}

    def test_แนวนอนทำให้สูงเท่ากันหมด(self, img):
        out = fit_uniform([img(50, 100), img(100, 200)], vertical=False)
        assert {im.height for im in out} == {200}

    def test_ยึดขนาดใหญ่สุดเพื่อไม่ให้เสียรายละเอียด(self, img):
        out = fit_uniform([img(100, 50), img(400, 200)], vertical=True)
        assert out[0].width == 400

    def test_คงอัตราส่วนเดิม(self, img):
        # 100x50 ขยายกว้างเป็น 200 -> สูงต้องเป็น 100
        out = fit_uniform([img(100, 50), img(200, 999)], vertical=True)
        assert out[0].size == (200, 100)

    def test_ภาพที่ขนาดตรงอยู่แล้วไม่ถูกสร้างใหม่(self, img):
        big = img(200, 100)
        out = fit_uniform([img(100, 50), big], vertical=True)
        assert out[1] is big

    def test_ภาพเตี้ยมากยังสูงอย่างน้อยหนึ่งพิกเซล(self, img):
        # 1000x1 ย่อ/ขยายแล้วปัดเศษอาจได้ 0 ซึ่ง PIL จะโยน error
        out = fit_uniform([img(1000, 1), img(50, 50)], vertical=True)
        assert all(im.height >= 1 for im in out)

    def test_ลิสต์ว่าง(self):
        assert fit_uniform([], vertical=True) == []


class TestStitchGroup:

    def test_แนวตั้งความสูงคือผลรวม(self, img):
        out = stitch_group([img(100, 50), img(100, 30)], vertical=True)
        assert out.size == (100, 80)

    def test_แนวนอนความกว้างคือผลรวม(self, img):
        out = stitch_group([img(50, 100), img(30, 100)], vertical=False)
        assert out.size == (80, 100)

    def test_เรียงตามลำดับที่ส่งเข้ามา(self, img):
        out = stitch_group([img(10, 10, RED), img(10, 10, BLUE)],
                           vertical=True)
        assert out.getpixel((5, 5)) == RED
        assert out.getpixel((5, 15)) == BLUE

    def test_ภาพแคบกว่าถูกจัดกึ่งกลาง(self, img):
        out = stitch_group([img(100, 50, RED), img(60, 50, BLUE)],
                           vertical=True)
        assert out.size == (100, 100)
        assert out.getpixel((0, 50)) == WHITE   # ขอบซ้ายเป็นพื้นหลัง
        assert out.getpixel((50, 50)) == BLUE   # ตรงกลางเป็นภาพ

    def test_เปลี่ยนสีพื้นหลังได้(self, img):
        out = stitch_group([img(100, 50), img(60, 50)], vertical=True,
                           bg_color=(0, 0, 0))
        assert out.getpixel((0, 50)) == (0, 0, 0)

    def test_ผลลัพธ์เป็นโหมด_RGB(self, img):
        assert stitch_group([img(10, 10)]).mode == "RGB"

    def test_กลุ่มว่างโยน_error(self):
        with pytest.raises(ValueError, match="ไม่มีรูปภาพ"):
            stitch_group([])


class TestLoadRgb:

    def test_คืนโหมด_RGB(self, write_image):
        assert load_rgb(write_image("a.jpg")).mode == "RGB"

    def test_แปลงภาพโปร่งใสเป็น_RGB(self, tmp_path):
        path = tmp_path / "a.png"
        Image.new("RGBA", (10, 10), (255, 0, 0, 128)).save(path)
        assert load_rgb(str(path)).mode == "RGB"

    def test_ไม่ค้างตัวจัดการไฟล์ไว้(self, write_image, tmp_path):
        # ถ้ายังเปิดไฟล์ค้าง บน Windows จะลบไฟล์ต้นทางไม่ได้
        path = write_image("a.jpg")
        loaded = load_rgb(path)
        import os
        os.remove(path)
        assert loaded.size == (10, 10)  # ภาพยังใช้ได้หลังไฟล์ถูกลบ

    def test_ไฟล์เสียโยน_error(self, tmp_path):
        bad = tmp_path / "bad.jpg"
        bad.write_text("นี่ไม่ใช่ไฟล์ภาพ")
        with pytest.raises(Exception):
            load_rgb(str(bad))
