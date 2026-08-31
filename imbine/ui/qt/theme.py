# -*- coding: utf-8 -*-
"""
ธีมและสีของหน้าตาโปรแกรม

เดิม stylesheet เป็นสตริงก้อนเดียวฝังอยู่ใน main() และยังมีสีอีกหลายค่ากระจาย
อยู่ตามไฟล์ (พื้นหลังแคนวาส เส้นกริด) จะเปลี่ยนสีทีต้องไล่แก้หลายที่ และทำ
ธีมสว่างไม่ได้เลย ที่นี่รวมสีทั้งหมดเป็น "โทเคน" แล้วประกอบ stylesheet จาก
โทเคนอีกที เพิ่มธีมใหม่ = เพิ่ม dict หนึ่งตัว
"""

import os

from ...resources import asset_path

DARK = {
    "bg": "#22252d",
    "surface": "#292d37",
    "surface_alt": "#303541",
    "sunken": "#1d2027",
    "canvas": "#17191f",
    "border": "#454b59",
    "text": "#edf0f7",
    "text_dim": "#9aa3b8",
    "accent": "#3f68d9",
    "accent_hover": "#4d76e6",
    "hover": "#3d4352",
    "warning": "#e8b339",
    "danger": "#e5544b",
    "grid": "rgba(255, 255, 255, 22)",
}

LIGHT = {
    "bg": "#f4f5f8",
    "surface": "#e8eaf0",
    "surface_alt": "#ffffff",
    "sunken": "#dfe2ea",
    "canvas": "#cfd3dd",
    "border": "#c2c7d4",
    "text": "#1c1f27",
    "text_dim": "#5d6474",
    "accent": "#3059cc",
    "accent_hover": "#2749ad",
    "hover": "#d3d8e4",
    "warning": "#9a6b00",
    "danger": "#c0392b",
    "grid": "rgba(0, 0, 0, 26)",
}

THEMES = {"dark": DARK, "light": LIGHT}
DEFAULT_THEME = "dark"

# ลำดับฟอนต์ที่ครอบคลุมภาษาไทยบนทุกระบบ ถ้าตัวแรกไม่มีจะไล่ไปตัวถัดไปเอง
# Leelawadee UI มากับ Windows 8+ ส่วน Tahoma มีมาตั้งแต่ Windows รุ่นเก่ามาก
FONT_STACK = ('"Noto Sans Thai", "Leelawadee UI", "Sarabun", Tahoma, '
              '"Segoe UI", "Helvetica Neue", sans-serif')


def load_icon(name, color=None):
    """
    โหลดไอคอน SVG จาก assets/icons แล้วย้อมสีให้เข้ากับธีม

    ไฟล์ SVG ใช้ ``stroke="currentColor"`` ซึ่ง QtSvg ไม่รู้จัก (ไม่มี CSS
    cascade) จึงต้องแทนที่ด้วยสีจริงก่อนเรนเดอร์ ไม่งั้นได้ไอคอนสีดำบนพื้นมืด

    ไฟล์หายก็คืน QIcon ว่าง — ปุ่มยังมีข้อความกำกับอยู่แล้ว
    """
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QIcon, QPixmap

    path = asset_path("icons", f"{name}.svg")
    if not os.path.isfile(path):
        return QIcon()
    color = color or tokens()["text"]
    with open(path, encoding="utf-8") as handle:
        markup = handle.read().replace("currentColor", color)
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(markup.encode("utf-8")), "SVG")
    return QIcon(pixmap)


def app_icon():
    """ไอคอนของหน้าต่างและของไฟล์ .exe"""
    from PySide6.QtGui import QIcon

    path = asset_path("icon.ico")
    return QIcon(path) if os.path.isfile(path) else QIcon()


def tokens(name=DEFAULT_THEME):
    """คืนชุดสีของธีม — ชื่อที่ไม่รู้จักถอยไปใช้ธีมเริ่มต้น"""
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def build_stylesheet(name=DEFAULT_THEME):
    """ประกอบ Qt stylesheet จากโทเคนสีของธีมที่เลือก"""
    c = tokens(name)
    return f"""
        * {{ font-family: {FONT_STACK}; font-size: 10.5pt; }}

        QMainWindow, QDockWidget, QWidget {{
            background: {c['bg']}; color: {c['text']};
        }}
        QToolBar {{
            background: {c['surface']}; border: 0; padding: 6px; spacing: 6px;
        }}
        QToolButton {{
            padding: 6px 10px; border-radius: 5px; color: {c['text']};
        }}
        QToolButton:hover {{ background: {c['hover']}; }}
        QToolButton:disabled {{ color: {c['text_dim']}; }}

        QMenuBar {{ background: {c['surface']}; color: {c['text']}; }}
        QMenuBar::item:selected {{ background: {c['hover']}; }}
        QMenu {{
            background: {c['surface_alt']}; color: {c['text']};
            border: 1px solid {c['border']};
        }}
        QMenu::item:selected {{ background: {c['accent']}; }}

        QDockWidget::title {{
            background: {c['surface']}; padding: 8px; font-weight: 600;
        }}

        QTabWidget::pane {{ border: 1px solid {c['border']}; }}
        QTabBar::tab {{
            background: {c['surface']}; color: {c['text_dim']};
            padding: 8px 16px; border-top-left-radius: 5px;
            border-top-right-radius: 5px; margin-right: 2px;
        }}
        QTabBar::tab:selected {{ background: {c['bg']}; color: {c['text']}; }}

        QGroupBox {{
            border: 1px solid {c['border']}; border-radius: 6px;
            margin-top: 22px; padding: 10px 8px 8px 8px; font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 10px; padding: 2px 6px; color: {c['text']};
        }}

        QListWidget {{
            background: {c['sunken']}; border: 0; padding: 8px;
        }}
        QListWidget::item {{ color: {c['text']}; padding: 3px; }}
        QListWidget::item:selected {{
            background: {c['accent']}; border-radius: 5px;
        }}

        QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
            background: {c['surface_alt']}; color: {c['text']}; padding: 5px;
            border: 1px solid {c['border']}; border-radius: 4px;
            selection-background-color: {c['accent']};
        }}
        QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
            color: {c['text_dim']};
        }}
        QComboBox QAbstractItemView {{
            background: {c['surface_alt']}; color: {c['text']};
            selection-background-color: {c['accent']};
        }}

        QPushButton {{
            background: {c['surface_alt']}; color: {c['text']};
            border: 1px solid {c['border']}; border-radius: 5px;
            padding: 6px 14px;
        }}
        QPushButton:hover {{ background: {c['hover']}; }}
        QPushButton:disabled {{ color: {c['text_dim']}; }}
        QPushButton[accent="true"] {{
            background: {c['accent']}; border-color: {c['accent']};
            color: #ffffff; font-weight: 600;
        }}
        QPushButton[accent="true"]:hover {{ background: {c['accent_hover']}; }}

        QCheckBox, QRadioButton, QLabel {{ color: {c['text']}; }}
        QLabel[hint="true"] {{ color: {c['text_dim']}; font-size: 9pt; }}
        QLabel[warning="true"] {{ color: {c['warning']}; }}

        QProgressBar {{
            background: {c['sunken']}; border: 0; border-radius: 4px;
            text-align: center; color: {c['text']};
        }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 4px; }}

        QStatusBar {{ background: {c['surface']}; color: {c['text']}; }}
        QScrollArea {{ border: 0; }}
        QTextBrowser {{
            background: {c['sunken']}; color: {c['text']};
            border: 1px solid {c['border']}; border-radius: 4px;
        }}
    """
