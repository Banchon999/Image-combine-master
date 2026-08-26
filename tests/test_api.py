# -*- coding: utf-8 -*-
"""เทสต์ end-to-end ผ่านหน้าบ้าน — ตั้งแต่ path ไฟล์จนถึงไฟล์ผลลัพธ์"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from imbine import (Cancelled, CancelToken, StitchConfig, Step,
                    build_default_pipeline, image_paths_in, run_stitch,
                    save_results, stitch_images)


class TestRunStitch:

    def test_ต่อและบันทึกครบวงจร(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=6, w=100, h=50)
        out = tmp_path / "out"
        ctx = run_stitch(image_paths_in(folder), str(out),
                         StitchConfig(parts_count=2), folder_name="ch01")

        assert len(ctx.saved_paths) == 2
        assert sorted(os.listdir(out)) == ["001.jpg", "002.jpg"]
        with Image.open(ctx.saved_paths[0]) as im:
            assert im.size == (100, 150)  # 3 ใบ x สูง 50

    def test_ปลายทางว่างคือไม่เขียนไฟล์(self, folder_of_images):
        # โหมดนี้คือฐานของระบบ preview ที่จะทำต่อ
        folder = folder_of_images(count=4)
        ctx = run_stitch(image_paths_in(folder))
        assert len(ctx.results) == 1
        assert ctx.saved_paths == []

    def test_รับ_config_เป็น_dict_ได้(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=4)
        ctx = run_stitch(image_paths_in(folder), str(tmp_path / "o"),
                         {"parts_count": 2, "fmt": "PNG"})
        assert all(p.endswith(".png") for p in ctx.saved_paths)

    def test_ค่าเริ่มต้นคือรวมเป็นไฟล์เดียว(self, folder_of_images):
        ctx = run_stitch(image_paths_in(folder_of_images(count=5)))
        assert len(ctx.results) == 1

    def test_แนวนอนต่อออกด้านกว้าง(self, folder_of_images):
        folder = folder_of_images(count=3, w=100, h=50)
        ctx = run_stitch(image_paths_in(folder),
                         config=StitchConfig(orientation="horizontal"))
        assert ctx.results[0].size == (300, 50)

    def test_จำกัดขนาดต่อไฟล์(self, folder_of_images):
        folder = folder_of_images(count=6, w=100, h=100)
        ctx = run_stitch(image_paths_in(folder),
                         config=StitchConfig(max_size=250))
        assert len(ctx.results) == 3  # 2+2+2

    def test_uniform_ปรับความกว้างให้เท่ากัน(self, write_image):
        paths = [write_image("a.jpg", 100, 50), write_image("b.jpg", 200, 50)]
        ctx = run_stitch(paths, config=StitchConfig(uniform=True))
        assert ctx.results[0].width == 200

    def test_ปิด_uniform_แล้วภาพเล็กถูกจัดกึ่งกลาง(self, write_image):
        paths = [write_image("a.jpg", 200, 50), write_image("b.jpg", 100, 50)]
        ctx = run_stitch(paths, config=StitchConfig(uniform=False))
        assert ctx.results[0].size == (200, 100)

    def test_ไม่มีภาพเลยต้องโยน_error(self, tmp_path):
        with pytest.raises(ValueError, match="ไม่มีรูปภาพ"):
            run_stitch([], str(tmp_path / "out"))

    def test_folder_name_ไปโผล่ในชื่อไฟล์(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=2)
        out = tmp_path / "out"
        run_stitch(image_paths_in(folder), str(out),
                   StitchConfig(name_pattern="{folder}_{n2}"),
                   folder_name="ตอนที่ 5")
        assert os.listdir(out) == ["ตอนที่ 5_01.jpg"]

    def test_ไม่เขียนทับแต่เติมเลขท้าย(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=2)
        out = tmp_path / "out"
        cfg = StitchConfig(overwrite=False)
        run_stitch(image_paths_in(folder), str(out), cfg)
        run_stitch(image_paths_in(folder), str(out), cfg)
        assert sorted(os.listdir(out)) == ["001.jpg", "001_1.jpg"]

    def test_เขียนทับเมื่อสั่ง(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=2)
        out = tmp_path / "out"
        cfg = StitchConfig(overwrite=True)
        run_stitch(image_paths_in(folder), str(out), cfg)
        run_stitch(image_paths_in(folder), str(out), cfg)
        assert os.listdir(out) == ["001.jpg"]

    def test_สร้างโฟลเดอร์ปลายทางที่ยังไม่มีให้(self, folder_of_images,
                                                  tmp_path):
        out = tmp_path / "ยัง" / "ไม่มี"
        run_stitch(image_paths_in(folder_of_images(count=2)), str(out))
        assert out.is_dir()


class TestReadmeExample:
    """ตัวอย่างใน README ต้องรันได้จริง ไม่ใช่โค้ดที่เขียนไว้สวย ๆ เฉย ๆ"""

    def test_ตัวอย่างใน_README(self, folder_of_images, tmp_path):
        folder = folder_of_images(name="chapter_01", count=6)
        events = []
        ctx = run_stitch(
            image_paths_in(folder),
            output_folder=str(tmp_path / "output"),
            config=StitchConfig(orientation="vertical", parts_count=3,
                                name_pattern="{folder}_{n2}", fmt="JPG"),
            folder_name="chapter_01",
            progress_cb=events.append,
        )
        assert len(ctx.saved_paths) == 3
        assert os.path.basename(ctx.saved_paths[0]) == "chapter_01_01.jpg"
        assert events


class TestProgressReporting:

    def test_รายงานครบทุกขั้น(self, folder_of_images, tmp_path):
        events = []
        run_stitch(image_paths_in(folder_of_images(count=4)),
                   str(tmp_path / "out"), progress_cb=events.append)
        assert {e.step for e in events} == {"load", "uniform", "split",
                                            "stitch", "save"}

    def test_ความคืบหน้ารวมเดินหน้าอย่างเดียว(self, folder_of_images,
                                                 tmp_path):
        events = []
        run_stitch(image_paths_in(folder_of_images(count=6)),
                   str(tmp_path / "out"), progress_cb=events.append)
        overall = [e.overall for e in events]
        assert overall == sorted(overall)
        assert 0.0 <= overall[0] and overall[-1] <= 1.0

    def test_บอกชื่อไฟล์ที่กำลังทำ(self, folder_of_images, tmp_path):
        events = []
        run_stitch(image_paths_in(folder_of_images(count=3)),
                   str(tmp_path / "out"), progress_cb=events.append)
        load_msgs = [e.message for e in events if e.step == "load"]
        assert "01.jpg" in load_msgs


class TestCancellation:

    def test_ยกเลิกกลางการโหลดภาพ(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=20)
        token = CancelToken()

        def on_progress(event):
            if event.step == "load" and event.done == 3:
                token.cancel()

        with pytest.raises(Cancelled):
            run_stitch(image_paths_in(folder), str(tmp_path / "out"),
                       progress_cb=on_progress, cancel=token)

        # ยกเลิกแล้วต้องไม่มีไฟล์ค้างในปลายทาง
        assert not (tmp_path / "out").exists()

    def test_ยกเลิกมีผลทันทีไม่รอให้ขั้นนั้นจบ(self, folder_of_images,
                                                   tmp_path):
        """
        ขั้นที่กินเวลานาน (upscale ที่จะมาในอนาคต) ต้องหยุดกลางคันได้
        ถ้าเช็คแค่ 'ระหว่างขั้น' ผู้ใช้กดยกเลิกแล้วยังต้องรออีกหลายนาที
        """
        folder = folder_of_images(count=20)
        token = CancelToken()
        loaded = []

        def on_progress(event):
            if event.step == "load":
                loaded.append(event.done)
                if event.done == 3:
                    token.cancel()

        with pytest.raises(Cancelled):
            run_stitch(image_paths_in(folder), str(tmp_path / "out"),
                       progress_cb=on_progress, cancel=token)

        assert max(loaded) <= 4  # ต้องไม่โหลดต่อจนครบ 20 ใบ

    def test_ยกเลิกระหว่างต่อภาพก็หยุดทันที(self, folder_of_images, tmp_path):
        folder = folder_of_images(count=16)
        token = CancelToken()
        stitched = []

        def on_progress(event):
            if event.step == "stitch":
                stitched.append(event.done)
                if event.done == 1:
                    token.cancel()

        with pytest.raises(Cancelled):
            run_stitch(image_paths_in(folder), str(tmp_path / "out"),
                       StitchConfig(parts_count=8), progress_cb=on_progress,
                       cancel=token)

        assert max(stitched) <= 2

    def test_ยกเลิกก่อนเริ่ม(self, folder_of_images, tmp_path):
        token = CancelToken()
        token.cancel()
        with pytest.raises(Cancelled):
            run_stitch(image_paths_in(folder_of_images(count=3)),
                       str(tmp_path / "out"), cancel=token)


class TestCustomPipeline:
    """ประกอบสายเองได้ — นี่คือทางที่ upscale/watermark จะเข้ามาในอนาคต"""

    def test_แทรกขั้นของตัวเองเข้าไปได้(self, folder_of_images, tmp_path):
        class TintStep(Step):
            name = "ย้อมสี"

            def run(self, ctx):
                ctx.images = [im.point(lambda v: 0) for im in ctx.images]

        pipe = build_default_pipeline(save=False)
        pipe.insert_after("load", TintStep())
        ctx = run_stitch(image_paths_in(folder_of_images(count=2)),
                         pipeline=pipe)
        assert ctx.results[0].getpixel((0, 0)) == (0, 0, 0)

    def test_ขั้นที่แทรกเห็นความคืบหน้าเป็นส่วนหนึ่งของงาน(self,
                                                              folder_of_images):
        class NoopStep(Step):
            name = "ขั้นใหม่"

            def run(self, ctx):
                pass

        events = []
        pipe = build_default_pipeline(save=False)
        pipe.insert_after("load", NoopStep())
        run_stitch(image_paths_in(folder_of_images(count=2)), pipeline=pipe,
                   progress_cb=events.append)
        assert "ขั้นใหม่" in {e.step for e in events}
        assert {e.step_total for e in events} == {5}


class TestLegacyApi:
    """ฟังก์ชันหน้าตาเดิมที่ README และสคริปต์เก่าเรียกใช้"""

    def test_stitch_images_คืนลิสต์ของภาพ(self, folder_of_images):
        results = stitch_images(image_paths_in(folder_of_images(count=6)),
                                parts_count=3)
        assert len(results) == 3
        assert results[0].size == (100, 100)

    def test_stitch_images_progress_cb_ยังเป็นแบบสองอาร์กิวเมนต์(
            self, folder_of_images):
        calls = []
        stitch_images(image_paths_in(folder_of_images(count=3)),
                      progress_cb=lambda done, total: calls.append(
                          (done, total)))
        assert (3, 3) in calls

    def test_stitch_images_ลิสต์ว่างโยน_error(self):
        with pytest.raises(ValueError, match="ไม่มีรูปภาพ"):
            stitch_images([])

    def test_save_results_ยังใช้ได้(self, folder_of_images, tmp_path):
        results = stitch_images(image_paths_in(folder_of_images(count=4)),
                                parts_count=2)
        saved = save_results(results, str(tmp_path / "out"), "{n2}",
                             fmt="PNG", quality=90)
        assert len(saved) == 2
        assert all(p.endswith(".png") and os.path.exists(p) for p in saved)

    def test_ตัวอย่างแบบเดิมยังรันได้(self, folder_of_images, tmp_path):
        folder = folder_of_images(name="chapter_01", count=5)
        paths = image_paths_in(folder)
        results = stitch_images(paths, orientation="vertical", parts_count=3)
        saved = save_results(results, str(tmp_path / "output"),
                             "{folder}_{n2}", fmt="JPG", quality=92,
                             folder_name="chapter_01")
        assert len(saved) == 3


class TestNoUiDependency:

    def test_import_imbine_ไม่ลาก_tkinter_เข้ามา(self):
        """
        ส่วนตรรกะต้องเทสต์ได้บนเครื่องที่ไม่มีจอ/ไม่มี tkinter
        รันในโปรเซสแยกเพื่อไม่ให้ผลถูกรบกวนจากสิ่งที่เทสต์อื่นเผลอ import ไว้
        """
        root = Path(__file__).resolve().parents[1]
        code = ("import sys, imbine; "
                "sys.exit(1 if 'tkinter' in sys.modules else 0)")
        result = subprocess.run([sys.executable, "-c", code], cwd=root)
        assert result.returncode == 0
