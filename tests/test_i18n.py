# -*- coding: utf-8 -*-
"""เทสต์ระบบหลายภาษา"""

import json
import os

import pytest

from imbine.i18n import (DEFAULT_LOCALE, M, Message, available_locales,
                         catalog, get_locale, has_key, set_locale, translate)
from imbine.resources import locales_dir


@pytest.fixture(autouse=True)
def คืนภาษาเดิมหลังเทสต์():
    """เทสต์ที่สลับภาษาต้องไม่ทำให้เทสต์ตัวถัดไปเพี้ยน"""
    เดิม = get_locale()
    yield
    set_locale(เดิม)


def อ่านไฟล์ภาษา(code):
    path = os.path.join(locales_dir(), f"{code}.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class Testคลังคำแปลครบถ้วน:
    """กันคำแปลตกหล่นตอนเพิ่มภาษาใหม่ — เป็นเหตุผลหลักที่มีไฟล์เทสต์นี้"""

    def test_ทุกภาษามีคีย์ชุดเดียวกับภาษาเริ่มต้น(self):
        ฐาน = set(อ่านไฟล์ภาษา(DEFAULT_LOCALE))
        for code, _ in available_locales():
            keys = set(อ่านไฟล์ภาษา(code))
            ขาด = ฐาน - keys
            เกิน = keys - ฐาน
            assert not ขาด, f"{code}.json ขาดคีย์: {sorted(ขาด)}"
            assert not เกิน, f"{code}.json มีคีย์ที่ {DEFAULT_LOCALE} ไม่มี: {sorted(เกิน)}"

    def test_ทุกภาษามี_meta_ที่บอกชื่อตัวเอง(self):
        for code, name in available_locales():
            meta = อ่านไฟล์ภาษา(code)["_meta"]
            assert meta["code"] == code
            assert meta["name"] == name and name.strip()

    def test_พารามิเตอร์ในแต่ละภาษาตรงกัน(self):
        """{count} ที่หายไปในภาษาหนึ่ง = ข้อมูลหายไปจากข้อความจริง"""
        import re
        ช่อง = lambda s: set(re.findall(r"\{(\w+)\}", s))
        ฐาน = อ่านไฟล์ภาษา(DEFAULT_LOCALE)
        for code, _ in available_locales():
            if code == DEFAULT_LOCALE:
                continue
            อื่น = อ่านไฟล์ภาษา(code)
            for key, template in ฐาน.items():
                if key == "_meta":
                    continue
                assert ช่อง(template) == ช่อง(อื่น[key]), f"{code}.json คีย์ {key}"


class TestMessage:
    def test_เป็น_str_จริงเพื่อให้ใช้กับ_join_ได้(self):
        """เหตุผลที่ Message สืบทอด str — โค้ดเดิมทำ '\\n'.join(warnings)"""
        ข้อความ = M("core.error.no_images")
        assert isinstance(ข้อความ, str)
        assert "\n".join([ข้อความ, ข้อความ]).count("\n") == 1

    def test_จำคีย์กับพารามิเตอร์ไว้ได้(self):
        ข้อความ = M("core.error.no_decoder", fmt="AVIF")
        assert ข้อความ.key == "core.error.no_decoder"
        assert ข้อความ.params == {"fmt": "AVIF"}

    def test_retranslate_เปลี่ยนภาษาได้(self):
        set_locale("th")
        ไทย = M("core.error.no_images")
        set_locale("en")
        assert ไทย.retranslate() == "No images to stitch"
        assert ไทย == "ไม่มีรูปภาพให้ต่อ"  # ตัวเดิมไม่ถูกแตะ

    def test_ใช้เป็นข้อความของ_exception_ได้(self):
        with pytest.raises(ValueError, match="ไม่มีรูปภาพ"):
            raise ValueError(M("core.error.no_images"))


class Testการแปล:
    def test_คีย์ที่ไม่มีคืนตัวคีย์เองไม่ใช่ค่าว่าง(self):
        assert translate("ไม่.มี.คีย์.นี้") == "ไม่.มี.คีย์.นี้"

    def test_พารามิเตอร์ขาดไม่ทำให้พัง(self):
        """ข้อความอ่านแปลก ๆ ยังดีกว่าแอพดับกลางงานของผู้ใช้"""
        assert translate("core.error.no_decoder") == catalog()["core.error.no_decoder"]

    def test_ภาษาที่ไม่มีถอยไปใช้ภาษาเริ่มต้น(self):
        assert set_locale("ไม่มีภาษานี้") == DEFAULT_LOCALE

    def test_คีย์ที่ภาษาปลายทางไม่มีถอยไปภาษาเริ่มต้น(self, monkeypatch):
        from imbine import i18n
        monkeypatch.setitem(i18n._catalogs, "en", {"_meta": {"name": "English"}})
        set_locale("en")
        assert translate("core.error.no_images") == "ไม่มีรูปภาพให้ต่อ"

    def test_has_key(self):
        assert has_key("core.error.no_images")
        assert not has_key("core.error.ไม่มีจริง")


class Testชื่อขั้นตอน:
    def test_ขั้นตอนมาตรฐานมีชื่อที่แปลแล้ว(self):
        from imbine.steps import build_default_pipeline
        set_locale("en")
        labels = [s.label() for s in build_default_pipeline().steps]
        assert "Stitch" in labels and "Save" in labels

    def test_ขั้นตอนที่คนอื่นเขียนเองได้ชื่อดิบของตัวเอง(self):
        """label_key ว่าง = ใช้ name ซึ่งอ่านรู้เรื่องกว่าคำแปลกลาง"""
        from imbine.pipeline import Step

        class ขั้นแปลก(Step):
            name = "upscale-x4"

        assert ขั้นแปลก().label() == "upscale-x4"

    def test_name_ยังเป็นอังกฤษเพื่อให้ค้นหาได้หลังสลับภาษา(self):
        from imbine.steps import build_default_pipeline
        set_locale("en")
        pipe = build_default_pipeline()
        assert pipe.index_of("save") == len(pipe.steps) - 1
