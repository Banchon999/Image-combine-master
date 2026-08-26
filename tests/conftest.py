# -*- coding: utf-8 -*-
"""เครื่องมือร่วมสำหรับเทสต์"""

import pytest
from PIL import Image

RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


@pytest.fixture
def img():
    """สร้างภาพในหน่วยความจำ ไม่แตะดิสก์"""
    def _img(w, h, color=RED):
        return Image.new("RGB", (w, h), color)
    return _img


@pytest.fixture
def write_image(tmp_path):
    """เขียนไฟล์ภาพจริงลง tmp_path แล้วคืน path"""
    def _write(name, w=10, h=10, color=RED):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (w, h), color).save(path)
        return str(path)
    return _write


@pytest.fixture
def folder_of_images(tmp_path):
    """สร้างโฟลเดอร์ที่มีภาพ n ใบ ชื่อ 01.jpg, 02.jpg, ... คืน path โฟลเดอร์"""
    def _make(name="pages", count=5, w=100, h=50):
        folder = tmp_path / name
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(1, count + 1):
            Image.new("RGB", (w, h), RED).save(folder / f"{i:02d}.jpg")
        return str(folder)
    return _make
