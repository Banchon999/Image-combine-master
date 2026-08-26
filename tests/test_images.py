# -*- coding: utf-8 -*-
"""เทสต์การค้นหาและเรียงลำดับไฟล์ภาพ"""

from PIL import Image

from imbine import (image_paths_in, is_image_file, list_images_sorted,
                    natural_sort_key)


class TestIsImageFile:

    def test_รู้จักนามสกุลที่รองรับ(self):
        for name in ["a.jpg", "a.jpeg", "a.png", "a.webp", "a.bmp", "a.gif"]:
            assert is_image_file(name), name

    def test_ไม่สนตัวพิมพ์ใหญ่เล็ก(self):
        assert is_image_file("PAGE.JPG")
        assert is_image_file("Page.PnG")

    def test_ปฏิเสธไฟล์อื่น(self):
        for name in ["a.txt", "a.psd", "a.jpg.txt", "noext", ""]:
            assert not is_image_file(name), name


class TestNaturalSortKey:

    def _sorted(self, names):
        return sorted(names, key=natural_sort_key)

    def test_เลขสองหลักต้องมาหลังเลขหลักเดียว(self):
        # นี่คือปัญหาหลักที่ natural sort มีไว้แก้
        assert self._sorted(["10.jpg", "2.jpg", "1.jpg"]) == [
            "1.jpg", "2.jpg", "10.jpg"]

    def test_ชื่อที่มีคำนำหน้า(self):
        assert self._sorted(["page_10.jpg", "page_2.jpg", "page_1.jpg"]) == [
            "page_1.jpg", "page_2.jpg", "page_10.jpg"]

    def test_เลขนำศูนย์ให้ผลเหมือนกัน(self):
        assert self._sorted(["003.jpg", "001.jpg", "002.jpg"]) == [
            "001.jpg", "002.jpg", "003.jpg"]

    def test_ชื่อที่มีหลายเลข(self):
        assert self._sorted(["001-010.jpg", "001-002.jpg", "001-001.jpg"]) == [
            "001-001.jpg", "001-002.jpg", "001-010.jpg"]

    def test_ชื่อภาษาไทย(self):
        assert self._sorted(["ตอนที่ 10.jpg", "ตอนที่ 2.jpg"]) == [
            "ตอนที่ 2.jpg", "ตอนที่ 10.jpg"]

    def test_ปนตัวอักษรกับตัวเลขแล้วไม่ระเบิด(self):
        # ถ้าคีย์ไม่ได้ใส่ 'ชนิด' นำหน้า การเทียบ str กับ int จะโยน TypeError
        self._sorted(["1.jpg", "a.jpg", "1a.jpg", "a1.jpg", ".jpg"])

    def test_ตัวพิมพ์ใหญ่เล็กไม่ทำให้ลำดับเพี้ยน(self):
        assert self._sorted(["B.jpg", "a.jpg"]) == ["a.jpg", "B.jpg"]

    def test_นามสกุลไม่ถูกนำมาคิด(self):
        # 2.png ต้องมาก่อน 10.jpg แม้ตัวอักษร j < p
        assert self._sorted(["10.jpg", "2.png"]) == ["2.png", "10.jpg"]


class TestListImagesSorted:

    def test_คืนเฉพาะไฟล์ภาพและเรียงถูก(self, tmp_path):
        for name in ["10.jpg", "2.jpg", "1.jpg"]:
            Image.new("RGB", (1, 1)).save(tmp_path / name)
        (tmp_path / "note.txt").write_bytes(b"x")
        assert list_images_sorted(str(tmp_path)) == [
            "1.jpg", "2.jpg", "10.jpg"]

    def test_ไม่นับไฟล์เสียแม้นามสกุลเป็นภาพ(self, tmp_path):
        (tmp_path / "broken.jpg").write_bytes(b"not an image")
        assert list_images_sorted(str(tmp_path)) == []

    def test_โฟลเดอร์ไม่มีอยู่คืนลิสต์ว่าง(self, tmp_path):
        assert list_images_sorted(str(tmp_path / "ไม่มีจริง")) == []

    def test_ส่งไฟล์แทนโฟลเดอร์ก็ไม่พัง(self, write_image):
        assert list_images_sorted(write_image("a.jpg")) == []

    def test_โฟลเดอร์ว่างคืนลิสต์ว่าง(self, tmp_path):
        assert list_images_sorted(str(tmp_path)) == []

    def test_image_paths_in_คืน_path_เต็ม(self, folder_of_images):
        folder = folder_of_images(count=3)
        paths = image_paths_in(folder)
        assert len(paths) == 3
        assert all(p.startswith(folder) for p in paths)
        # ต้องเปิดได้จริง ไม่ใช่แค่สตริงถูก
        for p in paths:
            with Image.open(p) as im:
                assert im.size == (100, 50)
