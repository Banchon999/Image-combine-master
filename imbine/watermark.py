# -*- coding: utf-8 -*-
"""
ใส่ลายน้ำลงบนภาพที่ต่อเสร็จแล้ว

รองรับทั้งลายน้ำแบบข้อความและแบบรูปภาพ วางได้ 9 ตำแหน่ง ปรับความโปร่งใสได้

เรื่องฟอนต์: ``ImageFont.load_default()`` ของ Pillow วาดภาษาไทยไม่ได้ (ได้
สี่เหลี่ยมเปล่า) ต่างจาก Qt ที่หาฟอนต์สำรองในเครื่องให้เอง โมดูลนี้จึงต้อง
ไล่หาไฟล์ฟอนต์จริงเอง ตามลำดับ: ฟอนต์ที่ผู้ใช้ระบุ -> ฟอนต์ที่แถมมากับแอพ
-> ฟอนต์ไทยที่มีในระบบ -> ฟอนต์เริ่มต้นของ Pillow (ซึ่งจะได้สี่เหลี่ยม
ถ้าข้อความเป็นภาษาไทย แต่ยังดีกว่าโปรแกรมดับ)
"""

import os

from PIL import Image, ImageDraw, ImageFont

from .resources import asset_path

# ตำแหน่งที่วางได้ -> (สัดส่วนแนวนอน, สัดส่วนแนวตั้ง)
ANCHORS = {
    "top-left": (0.0, 0.0),
    "top-center": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "middle-left": (0.0, 0.5),
    "center": (0.5, 0.5),
    "middle-right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom-center": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}

DEFAULT_ANCHOR = "bottom-right"

# ฟอนต์ไทยที่มักมีติดเครื่องอยู่แล้ว เรียงตามความน่าจะเจอ
_SYSTEM_FONTS = (
    r"C:\Windows\Fonts\leelawui.ttf",      # Leelawadee UI — Windows 8 ขึ้นไป
    r"C:\Windows\Fonts\tahoma.ttf",        # Tahoma — Windows ทุกรุ่น
    "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",           # macOS
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",   # Linux
    "/usr/share/fonts/truetype/tlwg/Loma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",           # ไม่มีไทย แต่ดีกว่าไม่มีอะไร
)

BUNDLED_FONT = "NotoSansThai-Regular.ttf"


def find_font_file(preferred=None):
    """หาไฟล์ฟอนต์ที่ใช้ได้จริง — คืน None ถ้าไม่เจอเลย"""
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.append(asset_path("fonts", BUNDLED_FONT))
    candidates.extend(_SYSTEM_FONTS)
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def load_font(size, preferred=None):
    """โหลดฟอนต์ตามขนาดที่ขอ ถอยไปใช้ฟอนต์เริ่มต้นถ้าหาไม่เจอ"""
    path = find_font_file(preferred)
    if path:
        try:
            return ImageFont.truetype(path, max(1, int(size)))
        except OSError:
            pass
    return ImageFont.load_default()


def _anchor_position(canvas_size, item_size, anchor, margin):
    """คำนวณมุมซ้ายบนที่จะวางลายน้ำ"""
    fx, fy = ANCHORS.get(anchor, ANCHORS[DEFAULT_ANCHOR])
    cw, ch = canvas_size
    iw, ih = item_size
    free_w = max(0, cw - iw - margin * 2)
    free_h = max(0, ch - ih - margin * 2)
    return (round(margin + free_w * fx), round(margin + free_h * fy))


def _text_layer(size, spec):
    """วาดข้อความลงเลเยอร์โปร่งใสขนาดเท่าภาพหลัก"""
    text = str(spec.get("text") or "")
    if not text:
        return None

    width, height = size
    # ขนาดฟอนต์คิดเป็นสัดส่วนของด้านสั้น เพื่อให้ลายน้ำดูเท่ากันทุกขนาดภาพ
    scale = float(spec.get("scale", 0.04))
    font_size = spec.get("font_size") or max(8, round(min(width, height) * scale))
    font = load_font(font_size, spec.get("font"))

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    box = draw.textbbox((0, 0), text, font=font)
    text_size = (box[2] - box[0], box[3] - box[1])
    margin = int(spec.get("margin", 24))
    x, y = _anchor_position(size, text_size, spec.get("position", DEFAULT_ANCHOR),
                            margin)

    color = tuple(spec.get("color", (255, 255, 255)))[:3]
    opacity = round(255 * max(0.0, min(1.0, float(spec.get("opacity", 0.5)))))

    if spec.get("outline", True):
        # ขอบดำบาง ๆ ทำให้ลายน้ำอ่านออกทั้งบนพื้นสว่างและพื้นมืด
        draw.text((x - box[0], y - box[1]), text, font=font,
                  fill=(0, 0, 0, opacity), stroke_width=max(1, font_size // 16),
                  stroke_fill=(0, 0, 0, opacity))
    draw.text((x - box[0], y - box[1]), text, font=font, fill=color + (opacity,))
    return layer


def _image_layer(size, spec):
    """วางไฟล์ภาพเป็นลายน้ำลงเลเยอร์โปร่งใสขนาดเท่าภาพหลัก"""
    source = spec.get("image")
    if not source or not os.path.isfile(source):
        return None

    with Image.open(source) as handle:
        mark = handle.convert("RGBA")

    width, height = size
    target_w = max(1, round(width * float(spec.get("scale", 0.15))))
    if mark.width != target_w:
        ratio = target_w / mark.width
        mark = mark.resize((target_w, max(1, round(mark.height * ratio))),
                           Image.LANCZOS)

    opacity = max(0.0, min(1.0, float(spec.get("opacity", 0.5))))
    if opacity < 1.0:
        alpha = mark.getchannel("A").point(lambda value: round(value * opacity))
        mark.putalpha(alpha)

    margin = int(spec.get("margin", 24))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.paste(mark, _anchor_position(size, mark.size,
                                       spec.get("position", DEFAULT_ANCHOR),
                                       margin), mark)
    return layer


def apply_watermark(img, spec):
    """
    คืนภาพใหม่ที่มีลายน้ำ — ภาพเดิมไม่ถูกแก้

    ``spec`` เป็น dict เพื่อให้เพิ่มตัวเลือกทีหลังได้โดยไม่ต้องแก้ StitchConfig:
      enabled   เปิด/ปิด
      text      ข้อความ (ใช้เมื่อไม่ได้ระบุ image)
      image     path ของไฟล์ภาพลายน้ำ
      position  หนึ่งใน ANCHORS
      opacity   0.0-1.0
      margin    ระยะห่างจากขอบ (px)
      scale     ขนาดเทียบกับภาพหลัก
      color     สีข้อความ (r, g, b)
      font      path ฟอนต์ที่อยากใช้เอง

    ระบุอะไรไม่ครบ หรือไฟล์ลายน้ำหาย จะคืนภาพเดิมกลับไปเฉย ๆ — งานต่อภาพ
    ของผู้ใช้ไม่ควรล้มเพราะลายน้ำ
    """
    if not spec or not spec.get("enabled"):
        return img

    layer = (_image_layer(img.size, spec) if spec.get("image")
             else _text_layer(img.size, spec))
    if layer is None:
        return img

    base = img.convert("RGBA")
    merged = Image.alpha_composite(base, layer)
    # คืนโหมดเดิม เพื่อไม่ให้ภาพ RGB กลายเป็น RGBA แล้วไปบังคับให้ต้อง
    # flatten อีกรอบตอนบันทึกเป็น JPEG
    result = merged if img.mode == "RGBA" else merged.convert(img.mode)
    result.info.update(img.info)
    return result
