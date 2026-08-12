# -*- coding: utf-8 -*-
"""เทสต์ StitchConfig"""

import pytest

from imbine import StitchConfig


class TestValidation:

    def test_ค่าเริ่มต้นคือต่อแนวตั้งไฟล์เดียว(self):
        cfg = StitchConfig()
        assert cfg.orientation == "vertical"
        assert cfg.vertical is True
        assert cfg.parts_count == 1
        assert cfg.max_size == 0

    def test_แนวนอนทำให้_vertical_เป็นเท็จ(self):
        assert StitchConfig(orientation="horizontal").vertical is False

    def test_ทิศทางผิดต้องโยน_error(self):
        # สะกดผิดคือบั๊ก ไม่ควรเงียบแล้วต่อแนวตั้งให้เฉย ๆ
        with pytest.raises(ValueError, match="orientation"):
            StitchConfig(orientation="vertical ")

    def test_ชนิดไฟล์ผิดต้องโยน_error(self):
        with pytest.raises(ValueError, match="fmt"):
            StitchConfig(fmt="TIFF")

    def test_ชนิดไฟล์ตัวเล็กถูกปรับเป็นตัวใหญ่(self):
        assert StitchConfig(fmt="webp").fmt == "WEBP"

    @pytest.mark.parametrize("given,expected", [(0, 1), (-5, 1), (150, 100),
                                                (92, 92)])
    def test_คุณภาพถูกบีบให้อยู่ในช่วง(self, given, expected):
        # ค่ามาจาก Spinbox ที่ผู้ใช้พิมพ์เองได้ จึงบีบแทนการโยน error
        assert StitchConfig(quality=given).quality == expected

    def test_จำนวนไฟล์ต่ำสุดคือหนึ่ง(self):
        assert StitchConfig(parts_count=0).parts_count == 1
        assert StitchConfig(parts_count=-3).parts_count == 1

    def test_ขนาดสูงสุดติดลบกลายเป็นศูนย์(self):
        assert StitchConfig(max_size=-100).max_size == 0

    def test_ค่าตัวเลขที่เป็นสตริงถูกแปลงให้(self):
        cfg = StitchConfig(quality="80", parts_count="3", max_size="5000")
        assert (cfg.quality, cfg.parts_count, cfg.max_size) == (80, 3, 5000)


class TestSerialisation:

    def test_ไปกลับแล้วได้ค่าเดิม(self):
        cfg = StitchConfig(orientation="horizontal", fmt="PNG", quality=70,
                           parts_count=4, uniform=False, overwrite=True)
        assert StitchConfig.from_dict(cfg.to_dict()) == cfg

    def test_to_dict_แปลงสีเป็น_list_เพื่อให้เป็น_JSON_ได้(self):
        import json
        data = StitchConfig().to_dict()
        assert data["bg_color"] == [255, 255, 255]
        json.dumps(data)  # ต้องไม่โยน TypeError

    def test_from_dict_ข้ามคีย์ที่ไม่รู้จัก(self):
        # ไฟล์ preset เก่าที่มีคีย์ซึ่งถูกถอดออกไปแล้วต้องไม่ทำให้โหลดพัง
        cfg = StitchConfig.from_dict({"fmt": "PNG", "ฟีเจอร์เก่า": 123})
        assert cfg.fmt == "PNG"

    def test_from_dict_รับ_None_ได้(self):
        assert StitchConfig.from_dict(None) == StitchConfig()


class TestReplace:

    def test_คืนตัวใหม่และไม่แตะตัวเดิม(self):
        original = StitchConfig(fmt="JPG", quality=92)
        changed = original.replace(fmt="PNG")
        assert changed.fmt == "PNG"
        assert original.fmt == "JPG"
        assert changed.quality == 92

    def test_ค่าที่แก้ยังถูกตรวจอยู่(self):
        with pytest.raises(ValueError):
            StitchConfig().replace(fmt="GIF")
