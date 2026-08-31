# -*- coding: utf-8 -*-
"""เทสต์ค่าตั้งของผู้ใช้และพรีเซ็ต"""

import json
import os

import pytest

from imbine.config import StitchConfig
from imbine.userdata import (DEFAULT_SETTINGS, RECENT_LIMIT, config_dir,
                             delete_preset, list_presets, load_preset,
                             load_settings, preset_path, presets_dir,
                             remember_folder, save_preset, save_settings,
                             set_config_dir, valid_preset_name)


@pytest.fixture(autouse=True)
def โฟลเดอร์ชั่วคราว(tmp_path):
    """ทุกเทสต์ต้องไม่ไปแตะค่าตั้งจริงของคนรันเทสต์"""
    set_config_dir(tmp_path / "imbine")
    yield tmp_path / "imbine"
    set_config_dir(None)


class Testโฟลเดอร์เก็บค่า:
    def test_ใช้โฟลเดอร์ที่บังคับไว้(self, โฟลเดอร์ชั่วคราว):
        assert config_dir() == str(โฟลเดอร์ชั่วคราว)
        assert presets_dir().startswith(str(โฟลเดอร์ชั่วคราว))

    def test_ยกเลิก_override_แล้วกลับไปใช้ของระบบ(self):
        set_config_dir(None)
        assert config_dir().endswith("imbine")


class Testค่าตั้งทั่วไป:
    def test_ยังไม่มีไฟล์ก็ได้ค่าเริ่มต้น(self):
        assert load_settings() == DEFAULT_SETTINGS

    def test_บันทึกแล้วอ่านกลับได้(self):
        save_settings(dict(DEFAULT_SETTINGS, locale="en", theme="light"))
        อ่าน = load_settings()
        assert อ่าน["locale"] == "en" and อ่าน["theme"] == "light"

    def test_ไฟล์เสียไม่ทำให้แอพเปิดไม่ขึ้น(self):
        """ผู้ใช้แก้ไฟล์มือแล้วพิมพ์ผิด ต้องถอยไปใช้ค่าเริ่มต้น ไม่ใช่ crash"""
        path = os.path.join(config_dir(), "settings.json")
        os.makedirs(config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{ พังแน่นอน")
        assert load_settings() == DEFAULT_SETTINGS

    def test_คีย์ที่ไม่รู้จักถูกทิ้ง_คีย์ที่ขาดถูกเติม(self):
        path = os.path.join(config_dir(), "settings.json")
        os.makedirs(config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"locale": "en", "ของแปลกจากเวอร์ชันอื่น": 1}, handle)
        อ่าน = load_settings()
        assert อ่าน["locale"] == "en"
        assert "ของแปลกจากเวอร์ชันอื่น" not in อ่าน
        assert อ่าน["theme"] == DEFAULT_SETTINGS["theme"]

    def test_เขียนแบบ_atomic_ไม่ทิ้งไฟล์ชั่วคราวไว้(self):
        save_settings(DEFAULT_SETTINGS)
        assert not any(n.endswith(".tmp") for n in os.listdir(config_dir()))


class Testโฟลเดอร์ที่เพิ่งใช้:
    def test_เลื่อนขึ้นหัวรายการ(self):
        s = remember_folder("/a", DEFAULT_SETTINGS)
        s = remember_folder("/b", s)
        assert s["recent_folders"] == ["/b", "/a"]

    def test_ใช้ซ้ำไม่เกิดรายการซ้ำ(self):
        s = remember_folder("/a", DEFAULT_SETTINGS)
        s = remember_folder("/b", s)
        s = remember_folder("/a", s)
        assert s["recent_folders"] == ["/a", "/b"]

    def test_จำกัดจำนวนไม่ให้ยาวไม่รู้จบ(self):
        s = DEFAULT_SETTINGS
        for i in range(RECENT_LIMIT + 5):
            s = remember_folder(f"/f{i}", s)
        assert len(s["recent_folders"]) == RECENT_LIMIT


class Testชื่อพรีเซ็ต:
    @pytest.mark.parametrize("name", ["ปกติ", "my preset", "a-b_c"])
    def test_ชื่อที่ใช้ได้(self, name):
        assert valid_preset_name(name)

    @pytest.mark.parametrize("name", ["", "   ", None, "a/b", "a:b", "a?b"])
    def test_ชื่อที่ใช้ไม่ได้(self, name):
        assert not valid_preset_name(name)

    def test_ชื่อผิดโยน_ValueError(self):
        with pytest.raises(ValueError):
            preset_path("ก/ข")


class Testพรีเซ็ต:
    def test_บันทึกแล้วโหลดกลับได้ค่าเดิม(self):
        cfg = StitchConfig(orientation="horizontal", fmt="PNG", parts_count=4,
                           trim_borders=True, watermark={"enabled": True,
                                                         "text": "@me"})
        save_preset("งานประจำ", cfg)
        กลับมา = load_preset("งานประจำ")
        assert กลับมา.orientation == "horizontal"
        assert กลับมา.parts_count == 4
        assert กลับมา.trim_borders is True
        assert กลับมา.watermark["text"] == "@me"

    def test_รับ_dict_ได้ด้วย(self):
        save_preset("จาก dict", {"orientation": "horizontal"})
        assert load_preset("จาก dict").orientation == "horizontal"

    def test_รายชื่อเรียงตามตัวอักษร(self):
        for name in ("ข", "ก", "ค"):
            save_preset(name, StitchConfig())
        assert list_presets() == ["ก", "ข", "ค"]

    def test_ยังไม่มีโฟลเดอร์ก็คืนรายการว่าง(self):
        assert list_presets() == []

    def test_โหลดพรีเซ็ตที่ไม่มีโยน_KeyError(self):
        with pytest.raises(KeyError):
            load_preset("ไม่เคยมี")

    def test_ลบได้และบอกว่าลบจริงไหม(self):
        save_preset("ชั่วคราว", StitchConfig())
        assert delete_preset("ชั่วคราว") is True
        assert delete_preset("ชั่วคราว") is False
        assert list_presets() == []

    def test_พรีเซ็ตจากเวอร์ชันอื่นเปิดได้_คีย์แปลกถูกทิ้ง(self):
        """from_dict ทิ้งคีย์ที่ไม่รู้จักอยู่แล้ว — พรีเซ็ตเก่าต้องไม่พัง"""
        os.makedirs(presets_dir(), exist_ok=True)
        with open(preset_path("เก่า"), "w", encoding="utf-8") as handle:
            json.dump({"orientation": "horizontal", "ฟีเจอร์ที่ถอดไปแล้ว": 1},
                      handle)
        assert load_preset("เก่า").orientation == "horizontal"

    def test_ไฟล์พรีเซ็ตเป็น_json_ที่คนอ่านออกและส่งต่อได้(self):
        save_preset("แชร์", StitchConfig(fmt="PNG"))
        with open(preset_path("แชร์"), encoding="utf-8") as handle:
            assert json.load(handle)["fmt"] == "PNG"
