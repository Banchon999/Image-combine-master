# -*- coding: utf-8 -*-
"""เทสต์การบันทึกไฟล์"""

import os

from PIL import Image

from imbine import save_image, save_results, unique_path


class TestUniquePath:

    def test_ไม่มีไฟล์เดิมก็คืนทางเดิม(self, tmp_path):
        path = str(tmp_path / "a.jpg")
        assert unique_path(path) == path

    def test_มีไฟล์เดิมแล้วเติมเลขหนึ่ง(self, write_image):
        path = write_image("a.jpg")
        assert unique_path(path).endswith("a_1.jpg")

    def test_เลี่ยงเลขที่ถูกใช้ไปแล้ว(self, write_image):
        path = write_image("a.jpg")
        write_image("a_1.jpg")
        assert unique_path(path).endswith("a_2.jpg")

    def test_เติมเลขก่อนนามสกุลไม่ใช่ต่อท้าย(self, write_image):
        assert unique_path(write_image("a.png")).endswith(".png")


class TestSaveImage:

    def test_บันทึก_jpg(self, tmp_path):
        path = str(tmp_path / "a.jpg")
        save_image(Image.new("RGB", (8, 8)), path, "JPG")
        with Image.open(path) as im:
            assert im.format == "JPEG"

    def test_บันทึก_png(self, tmp_path):
        path = str(tmp_path / "a.png")
        save_image(Image.new("RGB", (8, 8)), path, "PNG")
        with Image.open(path) as im:
            assert im.format == "PNG"

    def test_บันทึก_webp(self, tmp_path):
        path = str(tmp_path / "a.webp")
        save_image(Image.new("RGB", (8, 8)), path, "WEBP")
        with Image.open(path) as im:
            assert im.format == "WEBP"

    def test_คุณภาพต่ำได้ไฟล์เล็กกว่า(self, tmp_path):
        img = Image.new("RGB", (200, 200))
        for x in range(200):          # ใส่รายละเอียดให้บีบอัดเห็นผล
            for y in range(0, 200, 3):
                img.putpixel((x, y), (x % 256, y % 256, (x * y) % 256))
        low = str(tmp_path / "low.jpg")
        high = str(tmp_path / "high.jpg")
        save_image(img, low, "JPG", quality=20)
        save_image(img, high, "JPG", quality=95)
        assert os.path.getsize(low) < os.path.getsize(high)


class TestSaveResults:

    def _images(self, n):
        return [Image.new("RGB", (10, 10)) for _ in range(n)]

    def test_บันทึกครบและคืน_path(self, tmp_path):
        out = str(tmp_path / "out")
        saved = save_results(self._images(3), out, "{n3}")
        assert len(saved) == 3
        assert all(os.path.exists(p) for p in saved)
        assert sorted(os.listdir(out)) == ["001.jpg", "002.jpg", "003.jpg"]

    def test_สร้างโฟลเดอร์ให้ถ้ายังไม่มี(self, tmp_path):
        out = tmp_path / "ก" / "ข"
        save_results(self._images(1), str(out), "{n}")
        assert out.is_dir()

    def test_total_ในชื่อไฟล์คือจำนวนไฟล์ผลลัพธ์(self, tmp_path):
        out = str(tmp_path / "out")
        save_results(self._images(3), out, "{n}_of_{total}")
        assert sorted(os.listdir(out)) == ["1_of_3.jpg", "2_of_3.jpg",
                                           "3_of_3.jpg"]

    def test_เขียนทับเมื่อ_overwrite_จริง(self, tmp_path):
        out = str(tmp_path / "out")
        save_results(self._images(2), out, "{n}", overwrite=True)
        save_results(self._images(2), out, "{n}", overwrite=True)
        assert len(os.listdir(out)) == 2

    def test_เติมเลขท้ายเมื่อ_overwrite_เท็จ(self, tmp_path):
        out = str(tmp_path / "out")
        save_results(self._images(1), out, "{n}", overwrite=False)
        save_results(self._images(1), out, "{n}", overwrite=False)
        assert sorted(os.listdir(out)) == ["1.jpg", "1_1.jpg"]

    def test_รายงานความคืบหน้า(self, tmp_path):
        calls = []
        save_results(self._images(3), str(tmp_path / "out"), "{n}",
                     progress_cb=lambda d, t: calls.append((d, t)))
        assert calls == [(1, 3), (2, 3), (3, 3)]

    def test_ลิสต์ว่างไม่สร้างไฟล์แต่ยังสร้างโฟลเดอร์(self, tmp_path):
        out = tmp_path / "out"
        assert save_results([], str(out), "{n}") == []
        assert out.is_dir()
