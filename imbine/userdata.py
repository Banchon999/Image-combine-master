# -*- coding: utf-8 -*-
"""
ค่าตั้งของผู้ใช้และพรีเซ็ต — เก็บเป็น JSON ในโฟลเดอร์ config ของระบบ

เลือก JSON แทน QSettings ด้วยเหตุผลสองข้อ: เทสต์ได้โดยไม่ต้องมี Qt (ตามกติกา
ของโปรเจกต์ที่ห้ามชั้นตรรกะรู้จัก UI) และผู้ใช้ก๊อปไฟล์พรีเซ็ตส่งให้เพื่อนได้

StitchConfig มี to_dict/from_dict อยู่แล้วและถูกออกแบบมาเพื่อการนี้โดยเฉพาะ
โมดูลนี้จึงไม่เขียน serializer ใหม่ แค่เอาไปเขียนลงไฟล์
"""

import json
import os
import re

from .config import StitchConfig
from .i18n import M

APP_DIR_NAME = "imbine"
SETTINGS_FILE = "settings.json"
PRESETS_DIR_NAME = "presets"

# ชื่อพรีเซ็ตกลายเป็นชื่อไฟล์ จึงต้องกันอักขระที่ระบบไฟล์ไม่รับ
_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# override ได้เพื่อการเทสต์ และเผื่อโหมด portable ที่เก็บค่าไว้ข้างตัว .exe
_override_dir = None


def set_config_dir(path):
    """บังคับโฟลเดอร์ที่ใช้เก็บค่า — None = กลับไปใช้ค่าปกติของระบบ"""
    global _override_dir
    _override_dir = str(path) if path else None


def config_dir():
    """โฟลเดอร์เก็บค่าตั้งตามธรรมเนียมของแต่ละระบบปฏิบัติการ"""
    if _override_dir:
        return _override_dir
    base = os.environ.get("APPDATA")            # Windows
    if not base:
        base = os.environ.get("XDG_CONFIG_HOME")  # Linux ตามสเปก freedesktop
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_DIR_NAME)


def presets_dir():
    return os.path.join(config_dir(), PRESETS_DIR_NAME)


def _read_json(path, fallback):
    """
    อ่าน JSON แบบไม่ยอมพัง

    ไฟล์ตั้งค่าที่เสีย (ดิสก์เต็มระหว่างเขียน, ผู้ใช้แก้มือแล้วพิมพ์ผิด) ต้องไม่
    ทำให้แอพเปิดไม่ขึ้น — ถอยไปใช้ค่าเริ่มต้นแล้วทำงานต่อดีกว่า
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return fallback
    return data if isinstance(data, type(fallback)) else fallback


def _write_json(path, data):
    """
    เขียนแบบ atomic — เขียนลงไฟล์ชั่วคราวก่อนแล้วค่อย replace

    กันกรณีโปรแกรมถูกปิดกลางคัน แล้วเหลือไฟล์ตั้งค่าที่เขียนไม่จบ ซึ่งจะทำให้
    ค่าที่ผู้ใช้ตั้งไว้หายทั้งหมดในรอบถัดไป
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(temp, path)
    return path


# ----------------------------------------------------------------------
# ค่าตั้งทั่วไปของแอพ
# ----------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "locale": "",              # ว่าง = ใช้ภาษาเริ่มต้น
    "theme": "dark",
    "recent_folders": [],
    "last_config": None,
    "window_geometry": "",
}

RECENT_LIMIT = 10


def load_settings():
    """อ่านค่าตั้ง เติมคีย์ที่ขาดด้วยค่าเริ่มต้น (เผื่อไฟล์จากเวอร์ชันเก่า)"""
    data = _read_json(os.path.join(config_dir(), SETTINGS_FILE), {})
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    return merged


def save_settings(settings):
    return _write_json(os.path.join(config_dir(), SETTINGS_FILE), dict(settings))


def remember_folder(path, settings=None):
    """
    เลื่อนโฟลเดอร์ขึ้นหัวรายการที่เพิ่งใช้ คืนค่าตั้งชุดใหม่

    ไม่บันทึกลงดิสก์ให้ — ผู้เรียกตัดสินใจเองว่าจะเขียนเมื่อไหร่
    """
    settings = dict(settings or load_settings())
    recent = [p for p in settings.get("recent_folders", []) if p != path]
    recent.insert(0, path)
    settings["recent_folders"] = recent[:RECENT_LIMIT]
    return settings


# ----------------------------------------------------------------------
# พรีเซ็ตค่าตั้งการต่อภาพ
# ----------------------------------------------------------------------

def valid_preset_name(name):
    name = str(name or "").strip()
    return bool(name) and not _BAD_NAME.search(name)


def preset_path(name):
    if not valid_preset_name(name):
        raise ValueError(M("core.error.bad_preset_name"))
    return os.path.join(presets_dir(), f"{str(name).strip()}.json")


def list_presets():
    """ชื่อพรีเซ็ตทั้งหมด เรียงตามตัวอักษร"""
    try:
        names = os.listdir(presets_dir())
    except OSError:
        return []
    return sorted(n[:-5] for n in names if n.endswith(".json"))


def save_preset(name, config):
    """บันทึกพรีเซ็ต — รับได้ทั้ง StitchConfig และ dict"""
    data = config.to_dict() if isinstance(config, StitchConfig) else dict(config)
    return _write_json(preset_path(name), data)


def load_preset(name):
    """อ่านพรีเซ็ตเป็น StitchConfig — ไม่มีไฟล์ให้โยน KeyError"""
    path = preset_path(name)
    if not os.path.isfile(path):
        raise KeyError(M("core.error.preset_not_found", name=name))
    # from_dict ทิ้งคีย์ที่ไม่รู้จักอยู่แล้ว พรีเซ็ตจากเวอร์ชันเก่า/ใหม่กว่า
    # จึงเปิดได้เสมอ แค่ค่าที่หายไปกลับไปเป็นค่าเริ่มต้น
    return StitchConfig.from_dict(_read_json(path, {}))


def delete_preset(name):
    """ลบพรีเซ็ต — คืน True ถ้ามีไฟล์ให้ลบจริง"""
    path = preset_path(name)
    try:
        os.remove(path)
    except OSError:
        return False
    return True
