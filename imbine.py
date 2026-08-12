# -*- coding: utf-8 -*-
"""
ImageStitcher - แอพต่อภาพเว็บตูน
================================
โปรแกรมต่อภาพ (เว็บตูน/มันฮวา) มี UI ครบครัน รันด้วย Python + Tkinter

โครงสร้าง 2 หน้า (แท็บ):
  1. ต่อภาพ 1 โฟลเดอร์   - ต่อภาพในโฟลเดอร์เดียว
  2. ต่อภาพหลายโฟลเดอร์   - ต่อภาพทีละหลายโฟลเดอร์ในรอบเดียว

ฟีเจอร์หลัก:
  - ต่อได้ทั้งแนวตั้ง (เว็บตูน) และแนวนอน
  - เรียงภาพอัตโนมัติแบบ natural sort รองรับชื่อหลายรูปแบบ
  - ตั้งชื่อไฟล์ออกด้วย pattern
  - กำหนดจำนวนไฟล์ผลลัพธ์ หรือจำกัดขนาดต่อไฟล์
  - ออกได้ JPG / PNG / WebP
  - ปรับขนาดให้เท่ากันทุกภาพ
  - ระบบ smart กัน human error (ตรวจสอบก่อนทำงาน + เตือนล่วงหน้า)

วิธีรัน:
  pip install Pillow
  python image_stitcher.py
"""

import os
import re
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "ไม่พบไลบรารี Pillow\n"
        "กรุณาติดตั้งก่อนด้วยคำสั่ง:  pip install Pillow"
    )

# ======================================================================
# ส่วนตรรกะ (logic) - แยกออกจาก UI เพื่อให้แก้ไข/ทดสอบง่าย
# ======================================================================

# นามสกุลไฟล์ภาพที่รองรับเป็น "ขาเข้า"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")


def is_image_file(filename):
    """เช็คว่าไฟล์เป็นรูปภาพหรือไม่ (ดูจากนามสกุล)"""
    return filename.lower().endswith(IMAGE_EXTS)


def natural_sort_key(filename):
    """
    สร้าง 'กุญแจ' สำหรับเรียงชื่อไฟล์แบบธรรมชาติ (natural sort)

    ปัญหา: ถ้าเรียงแบบปกติ ชื่อไฟล์จะกลายเป็น 1, 10, 11, 2, 3 ...
    วิธีแก้: แยกตัวเลขออกมาแล้วเทียบเป็นตัวเลขจริง ๆ ทำให้ได้ 1, 2, 3, ... 10, 11

    รองรับชื่อหลายแบบ เช่น:
      01.jpg, 02.jpg          -> เลขล้วน
      page_1.jpg, page_10.jpg -> มีคำนำหน้า
      001-002.jpg             -> มีหลายเลข
      ตอนที่ 1.jpg            -> มีตัวอักษรไทยปน
    """
    name = os.path.splitext(filename)[0]  # ตัดนามสกุลออก
    parts = re.split(r"(\d+)", name)      # แยกเป็นชิ้น สลับเลข/ตัวอักษร
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part)))      # เป็นตัวเลข -> เทียบค่าตัวเลข
        else:
            key.append((0, part.lower()))   # เป็นตัวอักษร -> เทียบตัวอักษร
    return key


def list_images_sorted(folder):
    """คืนรายชื่อไฟล์ภาพในโฟลเดอร์ เรียงตามชื่อแบบธรรมชาติแล้ว"""
    if not os.path.isdir(folder):
        return []
    files = [f for f in os.listdir(folder) if is_image_file(f)]
    files.sort(key=natural_sort_key)
    return files


# ----------------------------------------------------------------------
# ระบบ smart กัน human error: ตรวจสอบล่วงหน้าก่อนต่อภาพจริง
# ----------------------------------------------------------------------

def inspect_images(image_paths):
    """
    ตรวจสอบรูปภาพล่วงหน้า เพื่อหา 'จุดเสี่ยง' ก่อนเริ่มทำงานจริง

    คืนค่า dict:
      ok          : list path รูปที่เปิดได้ปกติ
      broken      : list (path, เหตุผล) รูปที่เปิดไม่ได้/เสีย
      sizes       : dict {path: (w, h)} ขนาดของรูปที่เปิดได้
      warnings    : list ข้อความเตือน (ภาษาไทย) ที่ควรแจ้งผู้ใช้ก่อนทำงาน

    ฟังก์ชันนี้ไม่ตัดสินใจแทนผู้ใช้ แค่รายงานให้ผู้ใช้ตัดสินใจเอง
    """
    ok, broken, sizes = [], [], {}
    for path in image_paths:
        try:
            with Image.open(path) as img:
                img.verify()  # ตรวจว่าไฟล์ไม่เสีย
            # verify() ทำให้ object ใช้ต่อไม่ได้ ต้องเปิดใหม่เพื่ออ่านขนาด
            with Image.open(path) as img2:
                sizes[path] = img2.size
            ok.append(path)
        except Exception as e:
            broken.append((path, str(e)))

    warnings = []

    if broken:
        names = ", ".join(os.path.basename(p) for p, _ in broken[:5])
        more = f" และอีก {len(broken) - 5} ไฟล์" if len(broken) > 5 else ""
        warnings.append(
            f"⚠ มีไฟล์เปิดไม่ได้/เสีย {len(broken)} ไฟล์ "
            f"({names}{more}) — ระบบจะข้ามไฟล์เหล่านี้ให้")

    # ตรวจความกว้างที่ต่างกันมาก
    widths = [w for (w, h) in sizes.values()]
    if widths:
        wmin, wmax = min(widths), max(widths)
        if wmax > 0 and wmin / wmax < 0.5:
            warnings.append(
                f"⚠ ความกว้างของภาพต่างกันมาก ({wmin}px ถึง {wmax}px) — "
                f"ระบบจะปรับให้เท่ากันก่อนต่อ แต่ควรตรวจว่าภาพถูกชุดหรือไม่")

    # ตรวจรูปที่ขนาดผิดปกติ (เล็ก/ใหญ่กว่าค่ามัธยฐานมาก) — มักเป็นภาพไม่ใช่เนื้อหา
    areas = sorted(w * h for (w, h) in sizes.values())
    if len(areas) >= 4:
        median = areas[len(areas) // 2]
        odd = []
        for path, (w, h) in sizes.items():
            area = w * h
            if median > 0 and (area < median * 0.15 or area > median * 6):
                odd.append(os.path.basename(path))
        if odd:
            shown = ", ".join(odd[:5])
            more = f" และอีก {len(odd) - 5} ไฟล์" if len(odd) > 5 else ""
            warnings.append(
                f"⚠ มี {len(odd)} ภาพที่ขนาดต่างจากภาพอื่นมาก "
                f"({shown}{more}) — อาจเป็นปก/โฆษณา/ภาพแทรก ควรตรวจดู")

    return {"ok": ok, "broken": broken, "sizes": sizes, "warnings": warnings}


def check_output_path(folders_in, folder_out):
    """
    ตรวจว่าโฟลเดอร์ปลายทางปลอดภัยหรือไม่

    คืน list ข้อความเตือน เช่น ปลายทางอยู่ในโฟลเดอร์ต้นทาง
    (ซึ่งจะทำให้รอบหน้าระบบเก็บภาพที่ต่อแล้วมาต่อซ้ำ)
    """
    warnings = []
    if not folder_out:
        return warnings
    out_abs = os.path.abspath(folder_out)
    for fin in folders_in:
        in_abs = os.path.abspath(fin)
        # ปลายทางอยู่ข้างใน หรือเป็นตัวเดียวกับต้นทาง
        if out_abs == in_abs or out_abs.startswith(in_abs + os.sep):
            warnings.append(
                f"⚠ โฟลเดอร์ปลายทางอยู่ในโฟลเดอร์ต้นทาง "
                f"({os.path.basename(fin)}) — ไฟล์ที่ต่อแล้วอาจถูกนำมาต่อซ้ำ "
                f"ในรอบถัดไป แนะนำให้แยกโฟลเดอร์ปลายทางออกมา")
    return warnings


def find_existing_outputs(output_folder, name_pattern, count, fmt,
                          folder_name=""):
    """หาว่าจะมีไฟล์ผลลัพธ์ตัวไหนทับไฟล์เดิมที่มีอยู่แล้วบ้าง"""
    if not os.path.isdir(output_folder):
        return []
    ext = _ext_for(fmt)
    existing = []
    for i in range(1, count + 1):
        fname = build_output_name(name_pattern, i, count, folder_name) + ext
        if os.path.exists(os.path.join(output_folder, fname)):
            existing.append(fname)
    return existing


# ----------------------------------------------------------------------
# การต่อภาพ
# ----------------------------------------------------------------------

def stitch_images(image_paths, orientation="vertical", parts_count=1,
                  max_size=0, uniform=True, bg_color=(255, 255, 255),
                  progress_cb=None):
    """
    ต่อภาพจากรายการ image_paths

    พารามิเตอร์:
      image_paths : list ของ path รูปภาพ (เรียงลำดับมาแล้ว)
      orientation : "vertical" ต่อแนวตั้ง / "horizontal" ต่อแนวนอน
      parts_count : อยากได้ผลลัพธ์กี่ไฟล์ (แบ่งภาพให้เท่า ๆ กัน)
      max_size    : ขนาดสูงสุดต่อ 1 ไฟล์ (px) — แนวตั้งคือความสูง
                    แนวนอนคือความกว้าง  0 = ไม่จำกัด
      uniform     : True = ปรับให้ภาพมีขนาดด้านตัดเท่ากัน
                    (แนวตั้ง=กว้างเท่ากัน / แนวนอน=สูงเท่ากัน)
      bg_color    : สีพื้นหลัง
      progress_cb : ฟังก์ชันรายงานความคืบหน้า รับ (ทำไปแล้ว, ทั้งหมด)

    คืนค่า: list ของ PIL.Image (แต่ละตัวคือ 1 ไฟล์ผลลัพธ์)
    """
    if not image_paths:
        raise ValueError("ไม่มีรูปภาพให้ต่อ")

    vertical = (orientation == "vertical")

    # --- เปิดรูปทั้งหมด ---
    loaded = []
    total = len(image_paths)
    for i, path in enumerate(image_paths):
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        loaded.append(img)
        if progress_cb:
            progress_cb(i + 1, total)

    # --- ปรับขนาดด้านตัดให้เท่ากัน ---
    if uniform:
        if vertical:
            # ต่อแนวตั้ง -> ความกว้างต้องเท่ากัน (ใช้กว้างสุดเป็นมาตรฐาน)
            target = max(img.width for img in loaded)
            fixed = []
            for img in loaded:
                if img.width != target:
                    new_h = round(img.height * target / img.width)
                    img = img.resize((target, new_h), Image.LANCZOS)
                fixed.append(img)
            loaded = fixed
        else:
            # ต่อแนวนอน -> ความสูงต้องเท่ากัน
            target = max(img.height for img in loaded)
            fixed = []
            for img in loaded:
                if img.height != target:
                    new_w = round(img.width * target / img.height)
                    img = img.resize((new_w, target), Image.LANCZOS)
                fixed.append(img)
            loaded = fixed

    # --- แบ่งรูปออกเป็นกลุ่ม ---
    groups = _split_into_groups(loaded, parts_count, max_size, vertical)

    # --- ต่อรูปในแต่ละกลุ่ม ---
    results = []
    for group in groups:
        if vertical:
            w = max(img.width for img in group)
            h = sum(img.height for img in group)
            canvas = Image.new("RGB", (w, h), bg_color)
            y = 0
            for img in group:
                # จัดให้อยู่กลางถ้ากว้างไม่เท่ากัน
                x = (w - img.width) // 2
                canvas.paste(img, (x, y))
                y += img.height
        else:
            w = sum(img.width for img in group)
            h = max(img.height for img in group)
            canvas = Image.new("RGB", (w, h), bg_color)
            x = 0
            for img in group:
                y = (h - img.height) // 2
                canvas.paste(img, (x, y))
                x += img.width
        results.append(canvas)

    return results


def _split_into_groups(images, parts_count, max_size, vertical):
    """
    แบ่งรายการรูปออกเป็นกลุ่ม

    ลำดับการตัดสินใจ:
      1. ถ้ากำหนด max_size -> แบ่งกลุ่มใหม่ทันทีที่ขนาดรวมจะเกิน
      2. ไม่งั้นใช้ parts_count -> แบ่งให้ได้จำนวนกลุ่มเท่าที่ขอ
    """
    def dim(img):
        # ขนาดที่นำมาบวกกัน: แนวตั้ง=ความสูง / แนวนอน=ความกว้าง
        return img.height if vertical else img.width

    # กรณีจำกัดขนาด
    if max_size and max_size > 0:
        groups, current, current_size = [], [], 0
        for img in images:
            d = dim(img)
            if current and current_size + d > max_size:
                groups.append(current)
                current, current_size = [], 0
            current.append(img)
            current_size += d
        if current:
            groups.append(current)
        return groups

    # กรณีแบ่งตามจำนวนไฟล์
    parts_count = max(1, int(parts_count))
    parts_count = min(parts_count, len(images))
    groups, n = [], len(images)
    base = n // parts_count          # จำนวนรูปต่อกลุ่ม (ขั้นต่ำ)
    remainder = n % parts_count      # เศษ -> เกลี่ยใส่กลุ่มแรก ๆ
    idx = 0
    for i in range(parts_count):
        size = base + (1 if i < remainder else 0)
        groups.append(images[idx:idx + size])
        idx += size
    return groups


# ----------------------------------------------------------------------
# ชื่อไฟล์ & การบันทึก
# ----------------------------------------------------------------------

def build_output_name(pattern, index, total, folder_name=""):
    """
    สร้างชื่อไฟล์ผลลัพธ์จาก pattern ที่ผู้ใช้กำหนด

    ตัวแปรที่ใช้ใน pattern ได้:
      {n}      -> เลขลำดับ เช่น 1, 2, 3
      {n2}     -> เลขลำดับ 2 หลัก เช่น 01, 02
      {n3}     -> เลขลำดับ 3 หลัก เช่น 001
      {folder} -> ชื่อโฟลเดอร์ต้นทาง
      {total}  -> จำนวนไฟล์ผลลัพธ์ทั้งหมด
    """
    name = pattern
    name = name.replace("{n3}", f"{index:03d}")
    name = name.replace("{n2}", f"{index:02d}")
    name = name.replace("{n}", str(index))
    name = name.replace("{folder}", folder_name)
    name = name.replace("{total}", str(total))
    name = re.sub(r'[<>:"/\\|?*]', "_", name)  # ลบอักขระต้องห้าม
    return name.strip() or f"output_{index}"


def _ext_for(fmt):
    """คืนนามสกุลไฟล์ตามชนิดที่เลือก"""
    fmt = fmt.upper()
    return {"PNG": ".png", "WEBP": ".webp"}.get(fmt, ".jpg")


def save_results(results, output_folder, name_pattern, fmt="JPG",
                quality=92, folder_name="", overwrite=True):
    """
    บันทึกภาพผลลัพธ์ลงโฟลเดอร์

    overwrite=False -> ถ้าชื่อซ้ำจะเติม _1, _2 ต่อท้ายแทนการเขียนทับ
    คืนค่า: list ของ path ไฟล์ที่บันทึกแล้ว
    """
    os.makedirs(output_folder, exist_ok=True)
    fmt = fmt.upper()
    ext = _ext_for(fmt)
    saved = []
    total = len(results)
    for i, img in enumerate(results, start=1):
        base = build_output_name(name_pattern, i, total, folder_name)
        path = os.path.join(output_folder, base + ext)
        if not overwrite:
            # หาเลขท้ายที่ยังว่าง
            dup = 1
            while os.path.exists(path):
                path = os.path.join(output_folder, f"{base}_{dup}{ext}")
                dup += 1
        if fmt == "PNG":
            img.save(path, "PNG")
        elif fmt == "WEBP":
            img.save(path, "WEBP", quality=quality)
        else:
            img.save(path, "JPEG", quality=quality)
        saved.append(path)
    return saved


# ======================================================================
# ส่วน UI - หน้าตาโปรแกรม
# ======================================================================

FORMATS = ["JPG", "PNG", "WEBP"]


class SettingsPanel(ttk.LabelFrame):
    """
    แผงตั้งค่าการต่อภาพ ใช้ร่วมกันได้ทั้งสองแท็บ
    เก็บค่าทั้งหมดไว้ในตัวเอง ดึงออกด้วย .get_config()
    """

    def __init__(self, master, title="ตั้งค่าการต่อภาพ"):
        super().__init__(master, text=title, padding=8)
        self.orientation = tk.StringVar(value="vertical")
        self.name_pattern = tk.StringVar(value="{n3}")
        self.fmt = tk.StringVar(value="JPG")
        self.quality = tk.IntVar(value=92)
        self.split_mode = tk.StringVar(value="parts")
        self.parts_count = tk.IntVar(value=1)
        self.max_size = tk.IntVar(value=20000)
        self.uniform = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        # ทิศทางการต่อ
        orow = ttk.Frame(self)
        orow.pack(fill="x", pady=2)
        ttk.Label(orow, text="ทิศทาง:").pack(side="left")
        ttk.Radiobutton(orow, text="แนวตั้ง (เว็บตูน)",
                        variable=self.orientation,
                        value="vertical").pack(side="left", padx=4)
        ttk.Radiobutton(orow, text="แนวนอน",
                        variable=self.orientation,
                        value="horizontal").pack(side="left", padx=4)

        # โหมดการแบ่งไฟล์
        mrow = ttk.Frame(self)
        mrow.pack(fill="x", pady=2)
        ttk.Radiobutton(mrow, text="แบ่งเป็นจำนวนไฟล์:",
                        variable=self.split_mode,
                        value="parts").pack(side="left")
        ttk.Spinbox(mrow, from_=1, to=999, width=6,
                    textvariable=self.parts_count).pack(side="left",
                                                        padx=(4, 14))
        ttk.Radiobutton(mrow, text="จำกัดขนาดต่อไฟล์ (px):",
                        variable=self.split_mode,
                        value="size").pack(side="left")
        ttk.Spinbox(mrow, from_=500, to=200000, increment=1000, width=9,
                    textvariable=self.max_size).pack(side="left", padx=4)

        # รูปแบบชื่อไฟล์
        nrow = ttk.Frame(self)
        nrow.pack(fill="x", pady=2)
        ttk.Label(nrow, text="ชื่อไฟล์ออก:").pack(side="left")
        ttk.Entry(nrow, textvariable=self.name_pattern,
                  width=22).pack(side="left", padx=4)
        ttk.Label(nrow, text="( {n} {n2} {n3} {folder} {total} )",
                  foreground="gray").pack(side="left")

        # นามสกุล + คุณภาพ
        frow = ttk.Frame(self)
        frow.pack(fill="x", pady=2)
        ttk.Label(frow, text="ชนิดไฟล์:").pack(side="left")
        ttk.Combobox(frow, textvariable=self.fmt, values=FORMATS,
                     width=7, state="readonly").pack(side="left", padx=4)
        ttk.Label(frow, text="คุณภาพ:").pack(side="left", padx=(12, 0))
        ttk.Spinbox(frow, from_=50, to=100, width=5,
                    textvariable=self.quality).pack(side="left", padx=4)
        ttk.Label(frow, text="(สำหรับ JPG/WebP)",
                  foreground="gray").pack(side="left")

        # ตัวเลือกอื่น
        crow = ttk.Frame(self)
        crow.pack(fill="x", pady=2)
        ttk.Checkbutton(crow, text="ปรับขนาดให้เท่ากันทุกภาพ",
                        variable=self.uniform).pack(side="left")
        ttk.Checkbutton(crow, text="เขียนทับไฟล์ชื่อซ้ำ",
                        variable=self.overwrite).pack(side="left", padx=(14, 0))

    def get_config(self):
        """ดึงค่าตั้งทั้งหมดออกมาเป็น dict"""
        return {
            "orientation": self.orientation.get(),
            "name_pattern": self.name_pattern.get(),
            "fmt": self.fmt.get(),
            "quality": self.quality.get(),
            "parts_count": (self.parts_count.get()
                            if self.split_mode.get() == "parts" else 1),
            "max_size": (self.max_size.get()
                         if self.split_mode.get() == "size" else 0),
            "uniform": self.uniform.get(),
            "overwrite": self.overwrite.get(),
        }


def show_precheck_dialog(parent, warnings):
    """
    แสดงกล่องเตือนรวมก่อนเริ่มทำงาน
    คืน True ถ้าผู้ใช้กดยืนยันให้ทำต่อ, False ถ้ายกเลิก
    ถ้าไม่มี warning เลย คืน True ทันที
    """
    if not warnings:
        return True
    msg = ("ระบบตรวจพบจุดที่ควรระวังก่อนเริ่มทำงาน:\n\n"
           + "\n\n".join(warnings)
           + "\n\nต้องการดำเนินการต่อหรือไม่?")
    return messagebox.askyesno("ตรวจสอบก่อนทำงาน", msg, parent=parent)


class SingleFolderTab(ttk.Frame):
    """แท็บที่ 1: ต่อภาพในโฟลเดอร์เดียว"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.image_list = []
        self._build()

    def _build(self):
        # เลือกโฟลเดอร์ต้นทาง
        box1 = ttk.LabelFrame(self, text="1. โฟลเดอร์ต้นทาง", padding=8)
        box1.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(box1)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.folder).pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="เลือกโฟลเดอร์...",
                   command=self._choose_folder).pack(side="left", padx=(6, 0))
        self.count_label = ttk.Label(box1, text="ยังไม่ได้เลือกโฟลเดอร์",
                                     foreground="gray")
        self.count_label.pack(anchor="w", pady=(6, 0))

        # รายชื่อไฟล์
        box2 = ttk.LabelFrame(self, text="2. ลำดับภาพ (เรียงตามชื่ออัตโนมัติ)",
                              padding=8)
        box2.pack(fill="both", expand=True, pady=(0, 8))
        lf = ttk.Frame(box2)
        lf.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(lf, yscrollcommand=sb.set, height=7)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.config(command=self.listbox.yview)

        # แผงตั้งค่า
        self.settings = SettingsPanel(self, "3. ตั้งค่าการต่อภาพ")
        self.settings.pack(fill="x", pady=(0, 8))

        # ปลายทาง
        box4 = ttk.LabelFrame(self, text="4. โฟลเดอร์ปลายทาง", padding=8)
        box4.pack(fill="x", pady=(0, 8))
        r4 = ttk.Frame(box4)
        r4.pack(fill="x")
        ttk.Entry(r4, textvariable=self.output_folder).pack(
            side="left", fill="x", expand=True)
        ttk.Button(r4, text="เลือก...",
                   command=self._choose_output).pack(side="left", padx=(6, 0))

        # progress + ปุ่ม
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 4))
        self.status = ttk.Label(self, text="พร้อมทำงาน", foreground="gray")
        self.status.pack(anchor="w")
        self.run_btn = ttk.Button(self, text="▶  เริ่มต่อภาพ",
                                  command=self._run)
        self.run_btn.pack(fill="x", pady=(6, 0))

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่มีภาพ")
        if not folder:
            return
        self.folder.set(folder)
        self.image_list = list_images_sorted(folder)
        self.listbox.delete(0, tk.END)
        for i, name in enumerate(self.image_list, 1):
            self.listbox.insert(tk.END, f"{i:>3}.  {name}")
        self.count_label.config(
            text=f"พบรูปภาพ {len(self.image_list)} ไฟล์",
            foreground="green" if self.image_list else "red")
        if not self.output_folder.get():
            self.output_folder.set(os.path.join(folder, "_stitched"))

    def _choose_output(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if folder:
            self.output_folder.set(folder)

    def _run(self):
        # ----- ระบบกัน human error: ตรวจก่อนเริ่ม -----
        if not self.image_list:
            messagebox.showwarning("ยังไม่พร้อม",
                                   "กรุณาเลือกโฟลเดอร์ที่มีรูปภาพก่อน")
            return
        if not self.output_folder.get():
            messagebox.showwarning("ยังไม่พร้อม", "กรุณาเลือกโฟลเดอร์ปลายทาง")
            return

        folder = self.folder.get()
        paths = [os.path.join(folder, f) for f in self.image_list]
        cfg = self.settings.get_config()

        self.status.config(text="กำลังตรวจสอบรูปภาพ...", foreground="gray")
        self.update_idletasks()

        # รวบรวม warning ทั้งหมด
        report = inspect_images(paths)
        warnings = list(report["warnings"])
        warnings += check_output_path([folder], self.output_folder.get())

        if not report["ok"]:
            messagebox.showerror("ทำงานไม่ได้",
                                 "ไม่มีไฟล์ภาพที่เปิดได้เลยในโฟลเดอร์นี้")
            self.status.config(text="พร้อมทำงาน")
            return

        # เตือนเรื่องเขียนทับ
        if not cfg["overwrite"]:
            count = (cfg["parts_count"] if cfg["max_size"] == 0 else 1)
            existing = find_existing_outputs(
                self.output_folder.get(), cfg["name_pattern"], count,
                cfg["fmt"], os.path.basename(folder))
            if existing:
                warnings.append(
                    f"⚠ มีไฟล์ชื่อซ้ำในปลายทาง {len(existing)} ไฟล์ — "
                    f"ระบบจะเติมเลขท้าย (_1, _2) ให้ ไม่เขียนทับ")

        if not show_precheck_dialog(self, warnings):
            self.status.config(text="ยกเลิกแล้ว")
            return

        self.run_btn.config(state="disabled")
        threading.Thread(
            target=self._worker,
            args=(report["ok"], cfg, folder),
            daemon=True).start()

    def _worker(self, ok_paths, cfg, folder):
        try:
            def progress(done, tot):
                self.progress.config(maximum=tot, value=done)
                self.status.config(text=f"กำลังโหลดรูป {done}/{tot}")

            self.status.config(text="กำลังประมวลผล...")
            results = stitch_images(
                ok_paths, orientation=cfg["orientation"],
                parts_count=cfg["parts_count"], max_size=cfg["max_size"],
                uniform=cfg["uniform"], progress_cb=progress)

            self.status.config(text="กำลังบันทึกไฟล์...")
            saved = save_results(
                results, self.output_folder.get(), cfg["name_pattern"],
                cfg["fmt"], cfg["quality"],
                folder_name=os.path.basename(folder),
                overwrite=cfg["overwrite"])

            self.status.config(
                text=f"เสร็จแล้ว! บันทึก {len(saved)} ไฟล์",
                foreground="green")
            messagebox.showinfo(
                "สำเร็จ",
                f"ต่อภาพเสร็จแล้ว\nบันทึก {len(saved)} ไฟล์ไปที่:\n"
                f"{self.output_folder.get()}")
        except Exception as e:
            traceback.print_exc()
            self.status.config(text=f"เกิดข้อผิดพลาด: {e}", foreground="red")
            messagebox.showerror("ข้อผิดพลาด", str(e))
        finally:
            self.run_btn.config(state="normal")


class MultiFolderTab(ttk.Frame):
    """แท็บที่ 2: ต่อภาพหลายโฟลเดอร์ในรอบเดียว"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folders = []
        self.output_folder = tk.StringVar()
        self.subfolder = tk.BooleanVar(value=True)
        self._build()

    def _build(self):
        # รายการโฟลเดอร์
        box1 = ttk.LabelFrame(self, text="1. โฟลเดอร์ที่จะประมวลผล",
                              padding=8)
        box1.pack(fill="both", expand=True, pady=(0, 8))
        lf = ttk.Frame(box1)
        lf.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(lf, yscrollcommand=sb.set, height=6,
                                  selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.config(command=self.listbox.yview)

        br = ttk.Frame(box1)
        br.pack(fill="x", pady=(6, 0))
        ttk.Button(br, text="+ เพิ่มโฟลเดอร์",
                   command=self._add_folder).pack(side="left")
        ttk.Button(br, text="+ เพิ่มโฟลเดอร์ย่อยทั้งหมด",
                   command=self._add_parent).pack(side="left", padx=4)
        ttk.Button(br, text="ลบที่เลือก",
                   command=self._remove_selected).pack(side="left", padx=4)
        ttk.Button(br, text="ล้างทั้งหมด",
                   command=self._clear).pack(side="left")

        # แผงตั้งค่า
        self.settings = SettingsPanel(self, "2. ตั้งค่า (ใช้กับทุกโฟลเดอร์)")
        self.settings.pack(fill="x", pady=(0, 8))

        # ปลายทาง
        box3 = ttk.LabelFrame(self, text="3. โฟลเดอร์ปลายทาง", padding=8)
        box3.pack(fill="x", pady=(0, 8))
        r3 = ttk.Frame(box3)
        r3.pack(fill="x")
        ttk.Entry(r3, textvariable=self.output_folder).pack(
            side="left", fill="x", expand=True)
        ttk.Button(r3, text="เลือก...",
                   command=self._choose_output).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(box3,
                        text="แยกผลลัพธ์เป็นโฟลเดอร์ย่อยตามชื่อต้นทาง",
                        variable=self.subfolder).pack(anchor="w",
                                                      pady=(6, 0))

        # progress + ปุ่ม
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 4))
        self.status = ttk.Label(self, text="พร้อมทำงาน", foreground="gray")
        self.status.pack(anchor="w")
        self.run_btn = ttk.Button(self, text="▶  เริ่มต่อภาพทุกโฟลเดอร์",
                                  command=self._run)
        self.run_btn.pack(fill="x", pady=(6, 0))

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for folder in self.folders:
            n = len(list_images_sorted(folder))
            self.listbox.insert(
                tk.END,
                f"{os.path.basename(folder)}  ({n} รูป)  -  {folder}")

    def _add_folder(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์")
        if folder and folder not in self.folders:
            self.folders.append(folder)
            self._refresh_list()

    def _add_parent(self):
        """เลือกโฟลเดอร์แม่ แล้วเพิ่มโฟลเดอร์ย่อยทุกตัวที่มีรูปภาพ"""
        parent = filedialog.askdirectory(
            title="เลือกโฟลเดอร์แม่ (จะดึงโฟลเดอร์ย่อยทั้งหมด)")
        if not parent:
            return
        added = 0
        for name in sorted(os.listdir(parent), key=natural_sort_key):
            sub = os.path.join(parent, name)
            if (os.path.isdir(sub) and sub not in self.folders
                    and list_images_sorted(sub)):
                self.folders.append(sub)
                added += 1
        self._refresh_list()
        messagebox.showinfo("เพิ่มแล้ว",
                            f"เพิ่ม {added} โฟลเดอร์ย่อยที่มีรูปภาพ")

    def _remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            del self.folders[i]
        self._refresh_list()

    def _clear(self):
        self.folders = []
        self._refresh_list()

    def _choose_output(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if folder:
            self.output_folder.set(folder)

    def _run(self):
        # ----- ระบบกัน human error -----
        if not self.folders:
            messagebox.showwarning("ยังไม่พร้อม",
                                   "กรุณาเพิ่มโฟลเดอร์อย่างน้อย 1 โฟลเดอร์")
            return
        if not self.output_folder.get():
            messagebox.showwarning("ยังไม่พร้อม", "กรุณาเลือกโฟลเดอร์ปลายทาง")
            return

        warnings = []
        # โฟลเดอร์ที่ไม่มีรูปเลย
        empty = [os.path.basename(f) for f in self.folders
                 if not list_images_sorted(f)]
        if empty:
            warnings.append(
                f"⚠ มี {len(empty)} โฟลเดอร์ที่ไม่มีรูปภาพ "
                f"({', '.join(empty[:5])}) — ระบบจะข้ามให้")
        # ปลายทางอยู่ในต้นทาง
        warnings += check_output_path(self.folders, self.output_folder.get())

        if not show_precheck_dialog(self, warnings):
            self.status.config(text="ยกเลิกแล้ว")
            return

        self.run_btn.config(state="disabled")
        cfg = self.settings.get_config()
        threading.Thread(target=self._worker, args=(cfg,),
                         daemon=True).start()

    def _worker(self, cfg):
        try:
            total_folders = len(self.folders)
            self.progress.config(maximum=total_folders, value=0)
            ok, fail, errors = 0, 0, []

            for idx, folder in enumerate(self.folders, 1):
                fname = os.path.basename(folder)
                self.status.config(
                    text=f"[{idx}/{total_folders}] กำลังทำ: {fname}")
                try:
                    images = list_images_sorted(folder)
                    if not images:
                        raise ValueError("ไม่พบรูปภาพในโฟลเดอร์นี้")
                    paths = [os.path.join(folder, f) for f in images]
                    # ข้ามไฟล์เสีย แต่ยังทำต่อ
                    report = inspect_images(paths)
                    if not report["ok"]:
                        raise ValueError("ไม่มีไฟล์ภาพที่เปิดได้")

                    results = stitch_images(
                        report["ok"], orientation=cfg["orientation"],
                        parts_count=cfg["parts_count"],
                        max_size=cfg["max_size"], uniform=cfg["uniform"])

                    if self.subfolder.get():
                        out = os.path.join(self.output_folder.get(), fname)
                    else:
                        out = self.output_folder.get()
                    save_results(results, out, cfg["name_pattern"],
                                 cfg["fmt"], cfg["quality"],
                                 folder_name=fname,
                                 overwrite=cfg["overwrite"])
                    ok += 1
                except Exception as e:
                    fail += 1
                    errors.append(f"{fname}: {e}")
                self.progress.config(value=idx)

            msg = f"เสร็จแล้ว!  สำเร็จ {ok} โฟลเดอร์"
            if fail:
                msg += f", ล้มเหลว {fail} โฟลเดอร์"
            self.status.config(
                text=msg, foreground="green" if not fail else "orange")
            detail = msg
            if errors:
                detail += "\n\nรายการที่ล้มเหลว:\n" + "\n".join(errors)
            messagebox.showinfo("ผลลัพธ์", detail)
        except Exception as e:
            traceback.print_exc()
            self.status.config(text=f"เกิดข้อผิดพลาด: {e}", foreground="red")
            messagebox.showerror("ข้อผิดพลาด", str(e))
        finally:
            self.run_btn.config(state="normal")


class App(tk.Tk):
    """หน้าต่างหลักของโปรแกรม"""

    def __init__(self):
        super().__init__()
        self.title("ImageStitcher - แอพต่อภาพเว็บตูน")
        self.geometry("740x820")
        self.minsize(660, 700)

        header = ttk.Frame(self, padding=(12, 10, 12, 4))
        header.pack(fill="x")
        ttk.Label(header, text="🧩  แอพต่อภาพเว็บตูน",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(header,
                  text="ต่อภาพแนวตั้ง/แนวนอน เรียงลำดับอัตโนมัติ "
                       "มีระบบตรวจสอบกันพลาด",
                  foreground="gray").pack(anchor="w")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        nb.add(SingleFolderTab(nb), text="  ต่อภาพ 1 โฟลเดอร์  ")
        nb.add(MultiFolderTab(nb), text="  ต่อภาพหลายโฟลเดอร์  ")


if __name__ == "__main__":
    App().mainloop()
