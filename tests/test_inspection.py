# -*- coding: utf-8 -*-
"""เทสต์ระบบตรวจสอบก่อนทำงาน (ระบบกัน human error)"""

import os

from PIL import Image

from imbine import (check_output_path, find_existing_outputs, inspect_images)


def warn_text(report):
    return "\n".join(report.warnings)


class TestInspectImages:

    def test_ภาพปกติไม่มีคำเตือน(self, folder_of_images):
        folder = folder_of_images(count=5)
        paths = [os.path.join(folder, f) for f in sorted(os.listdir(folder))]
        report = inspect_images(paths)
        assert len(report.ok) == 5
        assert report.broken == []
        assert report.warnings == []

    def test_เก็บขนาดของทุกภาพที่เปิดได้(self, write_image):
        path = write_image("a.jpg", 120, 80)
        assert inspect_images([path]).sizes[path] == (120, 80)

    def test_จับไฟล์เสียและยังคืนภาพที่ดีไว้(self, write_image, tmp_path):
        good = write_image("good.jpg")
        bad = tmp_path / "bad.jpg"
        bad.write_text("ไม่ใช่ภาพ")
        report = inspect_images([good, str(bad)])
        assert report.ok == [good]
        assert len(report.broken) == 1
        assert report.broken[0][0] == str(bad)
        assert "เปิดไม่ได้" in warn_text(report)

    def test_ไฟล์ไม่มีอยู่จริงนับเป็นไฟล์เสีย(self):
        report = inspect_images(["/ไม่มี/ทาง/นี้.jpg"])
        assert report.ok == []
        assert len(report.broken) == 1

    def test_เตือนเมื่อความกว้างต่างกันเกินครึ่ง(self, write_image):
        paths = [write_image("a.jpg", 1000, 100),
                 write_image("b.jpg", 400, 100)]
        assert "ความกว้างของภาพต่างกันมาก" in warn_text(inspect_images(paths))

    def test_ไม่เตือนเมื่อความกว้างใกล้เคียงกัน(self, write_image):
        paths = [write_image("a.jpg", 1000, 100),
                 write_image("b.jpg", 900, 100)]
        assert "ความกว้าง" not in warn_text(inspect_images(paths))

    def test_เตือนภาพที่ขนาดผิดปกติเทียบกับค่ามัธยฐาน(self, write_image):
        paths = [write_image(f"p{i}.jpg", 800, 800) for i in range(5)]
        paths.append(write_image("ads.jpg", 800, 30))  # แบนเนอร์โฆษณา
        assert "ขนาดต่างจากภาพอื่นมาก" in warn_text(inspect_images(paths))

    def test_ภาพน้อยกว่าสี่ใบไม่ตรวจค่ามัธยฐาน(self, write_image):
        # ตัวอย่างน้อยเกินไป ค่ามัธยฐานไม่มีความหมายพอจะเชื่อ
        paths = [write_image("a.jpg", 800, 800), write_image("b.jpg", 800, 20)]
        assert "ขนาดต่างจากภาพอื่นมาก" not in warn_text(inspect_images(paths))

    def test_รายงานเป็นเท็จเมื่อไม่มีภาพใช้ได้(self, tmp_path):
        bad = tmp_path / "bad.jpg"
        bad.write_text("x")
        assert not inspect_images([str(bad)])

    def test_รายงานเป็นจริงเมื่อมีภาพใช้ได้(self, write_image):
        assert inspect_images([write_image("a.jpg")])

    def test_ลิสต์ว่างไม่มีคำเตือน(self):
        report = inspect_images([])
        assert report.ok == [] and report.warnings == []

    def test_ข้อความเตือนไม่ยาวเกินไปเมื่อไฟล์เสียเยอะ(self, tmp_path):
        paths = []
        for i in range(12):
            p = tmp_path / f"bad{i}.jpg"
            p.write_text("x")
            paths.append(str(p))
        text = warn_text(inspect_images(paths))
        assert "และอีก 7 ไฟล์" in text  # โชว์ 5 ชื่อแรก ที่เหลือย่อ


class TestCheckOutputPath:

    def test_ปลายทางอยู่ในต้นทางต้องเตือน(self, tmp_path):
        src = tmp_path / "ch01"
        src.mkdir()
        warnings = check_output_path([str(src)], str(src / "_stitched"))
        assert len(warnings) == 1
        assert "อยู่ในโฟลเดอร์ต้นทาง" in warnings[0]

    def test_ปลายทางเป็นตัวเดียวกับต้นทางต้องเตือน(self, tmp_path):
        src = tmp_path / "ch01"
        src.mkdir()
        assert check_output_path([str(src)], str(src))

    def test_ปลายทางแยกออกมาไม่เตือน(self, tmp_path):
        src = tmp_path / "ch01"
        out = tmp_path / "out"
        src.mkdir()
        assert check_output_path([str(src)], str(out)) == []

    def test_ชื่อที่ขึ้นต้นเหมือนกันแต่คนละโฟลเดอร์ไม่เตือน(self, tmp_path):
        # "ch01_out" ไม่ได้อยู่ใน "ch01" แม้สตริงจะขึ้นต้นเหมือนกัน
        src = tmp_path / "ch01"
        src.mkdir()
        assert check_output_path([str(src)], str(tmp_path / "ch01_out")) == []

    def test_เตือนทีละโฟลเดอร์ต้นทาง(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir(), b.mkdir()
        assert len(check_output_path([str(a), str(b)], str(a / "out"))) == 1

    def test_ปลายทางว่างไม่เตือน(self, tmp_path):
        assert check_output_path([str(tmp_path)], "") == []


class TestFindExistingOutputs:

    def test_เจอไฟล์ที่จะถูกทับ(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        Image.new("RGB", (5, 5)).save(out / "001.jpg")
        Image.new("RGB", (5, 5)).save(out / "003.jpg")
        found = find_existing_outputs(str(out), "{n3}", 3, "JPG")
        assert found == ["001.jpg", "003.jpg"]

    def test_นามสกุลต้องตรงกับชนิดที่เลือก(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        Image.new("RGB", (5, 5)).save(out / "001.jpg")
        assert find_existing_outputs(str(out), "{n3}", 3, "PNG") == []

    def test_โฟลเดอร์ปลายทางยังไม่มีคืนลิสต์ว่าง(self, tmp_path):
        assert find_existing_outputs(str(tmp_path / "ยังไม่มี"), "{n3}", 3,
                                     "JPG") == []

    def test_คิด_folder_ในรูปแบบชื่อด้วย(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        Image.new("RGB", (5, 5)).save(out / "ch01_01.jpg")
        assert find_existing_outputs(str(out), "{folder}_{n2}", 2, "JPG",
                                     "ch01") == ["ch01_01.jpg"]
