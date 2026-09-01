# -*- coding: utf-8 -*-
"""
หา path ของไฟล์ประกอบ (locale, ไอคอน, ฟอนต์) ให้เจอทั้งตอนรันจาก source
และตอนถูกแพ็กเป็น .exe ด้วย PyInstaller

PyInstaller แตกไฟล์ประกอบลงโฟลเดอร์ชั่วคราวแล้วบอก path ไว้ที่ ``sys._MEIPASS``
ส่วนตอนรันจาก source ไฟล์เหล่านั้นอยู่ข้าง ๆ โค้ดตามปกติ — โมดูลนี้ปิดความต่าง
ตรงนั้นให้จบในที่เดียว โค้ดที่เหลือจะได้ไม่ต้องรู้ว่าตัวเองถูก freeze อยู่หรือเปล่า
"""

import os
import sys

# รากของแพ็กเกจ imbine (โฟลเดอร์ที่ไฟล์นี้อยู่)
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    """True เมื่อกำลังรันจากไฟล์ที่ PyInstaller แพ็กไว้"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def base_dir():
    """
    โฟลเดอร์รากที่ใช้อ้าง path ของไฟล์ประกอบ

    ตอน frozen = โฟลเดอร์ชั่วคราวที่ PyInstaller แตกไฟล์ไว้
    ตอนรันจาก source = โฟลเดอร์แม่ของแพ็กเกจ (รากของ repo)
    """
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(_PACKAGE_DIR)


def package_path(*parts):
    """path ของไฟล์ที่อยู่ *ในแพ็กเกจ* เช่น locales/th.json"""
    if is_frozen():
        return os.path.join(sys._MEIPASS, "imbine", *parts)
    return os.path.join(_PACKAGE_DIR, *parts)


def asset_path(*parts):
    """path ของไฟล์ใน assets/ เช่น ไอคอนและฟอนต์"""
    return os.path.join(base_dir(), "assets", *parts)


def locales_dir():
    """โฟลเดอร์ที่เก็บไฟล์คำแปล"""
    return package_path("locales")
