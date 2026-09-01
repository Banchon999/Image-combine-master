# -*- coding: utf-8 -*-
"""
ระบบหลายภาษา

ปัญหาที่ต้องแก้: ข้อความที่ผู้ใช้เห็นจำนวนมากถูกสร้างใน "ชั้นตรรกะ" (คำเตือน
Smart Check, ข้อความ error, ความคืบหน้าของแต่ละขั้น) ซึ่งห้าม import Qt
ดังนั้นจะใช้ QTranslator/tr() ไม่ได้ และชั้นตรรกะก็ไม่ควรรู้ด้วยซ้ำว่าตอนนี้
ผู้ใช้เลือกภาษาอะไร

ทางออกคือ ``Message`` — วัตถุที่เก็บ *คีย์* กับ *พารามิเตอร์* ไว้เฉย ๆ แล้ว
แปลตอนถูกแปลงเป็นสตริง (``__str__``) เท่านั้น ผลที่ได้คือ:

  - ชั้นตรรกะสร้างข้อความได้โดยไม่ต้องรู้ภาษา
  - ผู้ใช้สลับภาษาได้ทีหลัง ข้อความที่ยังไม่ถูกแสดงก็เปลี่ยนตาม
  - โค้ดเดิมที่ทำ ``str(warning)`` หรือ f-string ยังทำงานเหมือนเดิมทุกประการ

เพิ่มภาษาใหม่ = วางไฟล์ ``imbine/locales/<code>.json`` เพิ่ม 1 ไฟล์ ไม่ต้องแตะโค้ด
"""

import json
import os

from .resources import locales_dir

# ภาษาเริ่มต้น — เป็นภาษาที่ข้อความต้นฉบับถูกเขียนไว้ ใช้เป็น fallback ด้วย
DEFAULT_LOCALE = "th"

_catalogs = {}      # code -> dict ของคำแปล (โหลดแบบ lazy)
_current = DEFAULT_LOCALE


# ----------------------------------------------------------------------
# ข้อความที่ยังไม่ถูกแปล
# ----------------------------------------------------------------------

class Message(str):
    """
    ข้อความที่แปลแล้ว แต่ยังจำได้ว่าตัวเองมาจากคีย์ไหน

    **สืบทอดจาก ``str`` โดยตั้งใจ** — ข้อความเหล่านี้ถูกส่งต่อไปยังโค้ดที่
    ต้องการสตริงจริง ๆ อยู่ตลอด (``"\\n".join(warnings)``, ``warnings.warn()``,
    ``str(exception)``, ``label.setText()``) การใช้วัตถุที่ "เหมือนสตริง"
    แต่ไม่ใช่สตริงจริงจะพังทันทีที่เจอ ``str.join`` ซึ่งไม่ยอมรับอะไรนอกจาก str

    การแปลจึงเกิด *ตอนสร้าง* ไม่ใช่ตอนแสดงผล ซึ่งใช้ได้จริงเพราะข้อความจากชั้น
    ตรรกะทุกตัวมีอายุสั้น (คำเตือนถูกโชว์ทันทีในกล่องยืนยัน, ความคืบหน้าเปลี่ยน
    ทุกวินาที, error ถูกโยนแล้วแสดงเลย) ส่วนข้อความที่ต้องอยู่ยาวข้ามการสลับ
    ภาษา — ป้ายบนปุ่มและชื่อขั้นตอน — ใช้ ``t()`` ตอนวาดใหม่แทน

    ใครที่ถือ Message ไว้นานแล้วอยากได้ภาษาใหม่ เรียก ``.retranslate()``
    """

    __slots__ = ("key", "params")

    def __new__(cls, key, params=None):
        params = dict(params or {})
        text = super().__new__(cls, translate(key, **params))
        text.key = key
        text.params = params
        return text

    def retranslate(self):
        """คืน Message ตัวใหม่ที่แปลด้วยภาษาปัจจุบัน"""
        return Message(self.key, self.params)

    def __repr__(self):
        return f"Message({self.key!r}, {self.params!r})"


def M(key, **params):
    """ทางลัดสร้าง Message — ใช้ในชั้นตรรกะ"""
    return Message(key, params)


# ----------------------------------------------------------------------
# แค็ตตาล็อก
# ----------------------------------------------------------------------

def _load_catalog(code):
    """อ่านไฟล์คำแปลของภาษาหนึ่ง — ไฟล์หายหรือพังให้ถือว่าว่าง ไม่ใช่ crash"""
    path = os.path.join(locales_dir(), f"{code}.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def catalog(code=None):
    """คืน dict คำแปลของภาษาที่ขอ (โหลดครั้งแรกครั้งเดียวแล้วจำไว้)"""
    code = code or _current
    if code not in _catalogs:
        _catalogs[code] = _load_catalog(code)
    return _catalogs[code]


def available_locales():
    """
    คืน [(code, ชื่อภาษาในภาษานั้นเอง), ...] เรียงตามตัวอักษร

    สแกนจากไฟล์จริงในโฟลเดอร์ locales — เมนูเลือกภาษาจึงขึ้นเองเมื่อมีไฟล์ใหม่
    """
    found = []
    try:
        names = sorted(os.listdir(locales_dir()))
    except OSError:
        return [(DEFAULT_LOCALE, DEFAULT_LOCALE)]
    for name in names:
        if not name.endswith(".json"):
            continue
        code = name[:-5]
        meta = catalog(code).get("_meta") or {}
        found.append((code, meta.get("name", code)))
    return found or [(DEFAULT_LOCALE, DEFAULT_LOCALE)]


def has_locale(code):
    return any(code == existing for existing, _ in available_locales())


# ----------------------------------------------------------------------
# ภาษาปัจจุบัน
# ----------------------------------------------------------------------

def get_locale():
    return _current


def set_locale(code):
    """
    เปลี่ยนภาษาที่ใช้แปล — คืนโค้ดภาษาที่ใช้จริง

    ขอภาษาที่ไม่มีไฟล์ จะถอยไปใช้ DEFAULT_LOCALE แทนที่จะโยน error
    เพราะค่านี้มาจากไฟล์ตั้งค่าของผู้ใช้ซึ่งแก้มือได้
    """
    global _current
    _current = code if has_locale(code) else DEFAULT_LOCALE
    return _current


# ----------------------------------------------------------------------
# แปล
# ----------------------------------------------------------------------

def translate(key, **params):
    """
    แปลคีย์เป็นข้อความในภาษาปัจจุบัน

    ลำดับการถอย: ภาษาปัจจุบัน -> ภาษาเริ่มต้น -> ตัวคีย์เอง
    คีย์ที่ยังไม่ได้แปลจึงโผล่มาให้เห็นแทนที่จะกลายเป็นช่องว่าง

    พารามิเตอร์ที่ขาดหายก็ไม่ทำให้พัง — คืนเทมเพลตดิบแทน เพราะข้อความ
    ที่อ่านแปลก ๆ ยังดีกว่าแอพที่ปิดตัวเองกลางงานของผู้ใช้
    """
    template = catalog().get(key)
    if template is None and _current != DEFAULT_LOCALE:
        template = catalog(DEFAULT_LOCALE).get(key)
    if template is None:
        template = key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template


def has_key(key):
    """มีคำแปลของคีย์นี้จริงไหม (ภาษาปัจจุบันหรือภาษาเริ่มต้น)"""
    return key in catalog() or key in catalog(DEFAULT_LOCALE)


def t(key, **params):
    """ทางลัดสำหรับชั้น UI — แปลทันที คืน str"""
    return translate(key, **params)
