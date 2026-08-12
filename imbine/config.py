# -*- coding: utf-8 -*-
"""
ค่าตั้งของการต่อภาพ

เก็บเป็น dataclass ตัวเดียวเพื่อให้:
  - ส่งผ่าน pipeline ได้โดยไม่ต้องโยนพารามิเตอร์เป็นสิบตัว
  - แปลงเป็น dict เพื่อเซฟเป็นไฟล์ preset ได้ทันที
  - ตรวจค่าผิดตั้งแต่ต้นทาง ไม่ใช่ไประเบิดกลางทาง
"""

from dataclasses import asdict, dataclass, field, fields

# ชนิดไฟล์ขาออกที่รองรับ
FORMATS = ("JPG", "PNG", "WEBP")

ORIENTATIONS = ("vertical", "horizontal")


@dataclass
class StitchConfig:
    """ค่าตั้งทั้งหมดของงานต่อภาพ 1 งาน"""

    orientation: str = "vertical"
    """"vertical" = ต่อแนวตั้ง (เว็บตูน) / "horizontal" = ต่อแนวนอน"""

    name_pattern: str = "{n3}"
    """รูปแบบชื่อไฟล์ออก ดู naming.build_output_name"""

    fmt: str = "JPG"
    """ชนิดไฟล์ขาออก: JPG / PNG / WEBP"""

    quality: int = 92
    """คุณภาพ 1-100 (ใช้กับ JPG และ WebP เท่านั้น)"""

    parts_count: int = 1
    """อยากได้ผลลัพธ์กี่ไฟล์ (ใช้เมื่อ max_size == 0)"""

    max_size: int = 0
    """ขนาดสูงสุดต่อไฟล์ (px) แนวตั้ง=สูง แนวนอน=กว้าง / 0 = ไม่จำกัด"""

    uniform: bool = True
    """ปรับด้านตัดให้เท่ากันก่อนต่อหรือไม่"""

    overwrite: bool = False
    """True = เขียนทับไฟล์ชื่อซ้ำ / False = เติม _1, _2 ต่อท้าย"""

    bg_color: tuple = (255, 255, 255)
    """สีพื้นหลังของผืนผ้าใบ"""

    def __post_init__(self):
        if self.orientation not in ORIENTATIONS:
            raise ValueError(
                f"orientation ต้องเป็น {ORIENTATIONS} ไม่ใช่ {self.orientation!r}")

        self.fmt = str(self.fmt).upper()
        if self.fmt not in FORMATS:
            raise ValueError(f"fmt ต้องเป็น {FORMATS} ไม่ใช่ {self.fmt!r}")

        # ค่าตัวเลขใช้วิธี "บีบให้อยู่ในช่วง" ไม่ใช่โยน error
        # เพราะมันมาจาก Spinbox ที่ผู้ใช้พิมพ์มั่วได้
        self.quality = max(1, min(100, int(self.quality)))
        self.parts_count = max(1, int(self.parts_count))
        self.max_size = max(0, int(self.max_size))
        self.uniform = bool(self.uniform)
        self.overwrite = bool(self.overwrite)
        self.bg_color = tuple(self.bg_color)

    @property
    def vertical(self):
        """ต่อแนวตั้งหรือไม่ — ใช้บ่อยจนควรมีทางลัด"""
        return self.orientation == "vertical"

    def to_dict(self):
        """แปลงเป็น dict สำหรับเซฟลงไฟล์ preset"""
        data = asdict(self)
        data["bg_color"] = list(self.bg_color)  # JSON ไม่มี tuple
        return data

    @classmethod
    def from_dict(cls, data):
        """สร้างจาก dict โดยข้ามคีย์แปลกปลอมที่ไม่รู้จัก

        เผื่อไฟล์ preset เก่าที่มีคีย์ซึ่งถูกถอดออกไปแล้ว จะได้ไม่พัง
        """
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})

    def replace(self, **changes):
        """คืน config ตัวใหม่ที่แก้บางค่า (ตัวเดิมไม่ถูกแตะ)"""
        data = asdict(self)
        data.update(changes)
        return StitchConfig(**data)
