# -*- coding: utf-8 -*-
"""
หน้าตาโปรแกรม (Tkinter)

ไฟล์นี้ทำหน้าที่เดียวคือ "รับค่าจากผู้ใช้แล้วเรียก imbine.run_stitch()"
ตรรกะการต่อภาพทั้งหมดอยู่ในแพ็กเกจ imbine ไม่มีอยู่ในไฟล์นี้เลย

โครงสร้าง 2 หน้า (แท็บ):
  1. ต่อภาพ 1 โฟลเดอร์   - ต่อภาพในโฟลเดอร์เดียว
  2. ต่อภาพหลายโฟลเดอร์   - ต่อภาพทีละหลายโฟลเดอร์ในรอบเดียว
"""

import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .. import (Cancelled, CancelToken, FORMATS, StitchConfig,
                check_output_path, find_existing_outputs, inspect_images,
                list_images_sorted, natural_sort_key, run_stitch)


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
        ttk.Combobox(frow, textvariable=self.fmt, values=list(FORMATS),
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
        """ดึงค่าตั้งทั้งหมดออกมาเป็น StitchConfig"""
        by_parts = (self.split_mode.get() == "parts")
        return StitchConfig(
            orientation=self.orientation.get(),
            name_pattern=self.name_pattern.get(),
            fmt=self.fmt.get(),
            quality=self.quality.get(),
            parts_count=self.parts_count.get() if by_parts else 1,
            max_size=0 if by_parts else self.max_size.get(),
            uniform=self.uniform.get(),
            overwrite=self.overwrite.get(),
        )


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


class WorkerMixin:
    """
    ตัวช่วยให้ background thread คุย widget ได้อย่างปลอดภัย

    Tkinter ไม่ thread-safe — การเรียก widget.config() จากเธรดอื่นตรง ๆ
    ทำให้แครชแบบสุ่มได้ ทางที่ถูกคือฝากงานกลับไปให้เธรดหลักผ่าน after()
    """

    def post(self, fn, *args, **kwargs):
        """สั่งให้ฟังก์ชันไปทำงานบนเธรดหลักของ Tk"""
        self.after(0, lambda: fn(*args, **kwargs))

    def set_status(self, text, color="gray"):
        self.post(self.status.config, text=text, foreground=color)

    def set_progress(self, done, total):
        self.post(self.progress.config, maximum=max(1, total), value=done)


class SingleFolderTab(ttk.Frame, WorkerMixin):
    """แท็บที่ 1: ต่อภาพในโฟลเดอร์เดียว"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.image_list = []
        self.cancel_token = None
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
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(6, 0))
        self.run_btn = ttk.Button(btns, text="▶  เริ่มต่อภาพ",
                                  command=self._run)
        self.run_btn.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ttk.Button(btns, text="■ ยกเลิก", state="disabled",
                                     command=self._cancel)
        self.cancel_btn.pack(side="left", padx=(6, 0))

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

    def _cancel(self):
        if self.cancel_token:
            self.cancel_token.cancel()
            self.set_status("กำลังยกเลิก...", "orange")

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
        warnings = list(report.warnings)
        warnings += check_output_path([folder], self.output_folder.get())

        if not report.ok:
            messagebox.showerror("ทำงานไม่ได้",
                                 "ไม่มีไฟล์ภาพที่เปิดได้เลยในโฟลเดอร์นี้")
            self.status.config(text="พร้อมทำงาน")
            return

        # เตือนเรื่องเขียนทับ
        if not cfg.overwrite:
            count = cfg.parts_count if cfg.max_size == 0 else 1
            existing = find_existing_outputs(
                self.output_folder.get(), cfg.name_pattern, count,
                cfg.fmt, os.path.basename(folder))
            if existing:
                warnings.append(
                    f"⚠ มีไฟล์ชื่อซ้ำในปลายทาง {len(existing)} ไฟล์ — "
                    f"ระบบจะเติมเลขท้าย (_1, _2) ให้ ไม่เขียนทับ")

        if not show_precheck_dialog(self, warnings):
            self.status.config(text="ยกเลิกแล้ว")
            return

        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.cancel_token = CancelToken()
        threading.Thread(
            target=self._worker,
            args=(report.ok, cfg, folder),
            daemon=True).start()

    def _worker(self, ok_paths, cfg, folder):
        try:
            def on_progress(event):
                self.set_progress(event.done, event.total)
                self.set_status(
                    f"[{event.step}] {event.done}/{event.total}  "
                    f"{event.message}")

            ctx = run_stitch(
                ok_paths,
                output_folder=self.output_folder.get(),
                config=cfg,
                folder_name=os.path.basename(folder),
                progress_cb=on_progress,
                cancel=self.cancel_token)

            n = len(ctx.saved_paths)
            self.set_status(f"เสร็จแล้ว! บันทึก {n} ไฟล์", "green")
            self.post(messagebox.showinfo, "สำเร็จ",
                      f"ต่อภาพเสร็จแล้ว\nบันทึก {n} ไฟล์ไปที่:\n"
                      f"{self.output_folder.get()}")
        except Cancelled:
            self.set_status("ยกเลิกแล้ว", "orange")
        except Exception as e:
            traceback.print_exc()
            self.set_status(f"เกิดข้อผิดพลาด: {e}", "red")
            self.post(messagebox.showerror, "ข้อผิดพลาด", str(e))
        finally:
            self.post(self.run_btn.config, state="normal")
            self.post(self.cancel_btn.config, state="disabled")


class MultiFolderTab(ttk.Frame, WorkerMixin):
    """แท็บที่ 2: ต่อภาพหลายโฟลเดอร์ในรอบเดียว"""

    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folders = []
        self.output_folder = tk.StringVar()
        self.subfolder = tk.BooleanVar(value=True)
        self.cancel_token = None
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
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(6, 0))
        self.run_btn = ttk.Button(btns, text="▶  เริ่มต่อภาพทุกโฟลเดอร์",
                                  command=self._run)
        self.run_btn.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ttk.Button(btns, text="■ ยกเลิก", state="disabled",
                                     command=self._cancel)
        self.cancel_btn.pack(side="left", padx=(6, 0))

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

    def _cancel(self):
        if self.cancel_token:
            self.cancel_token.cancel()
            self.set_status("กำลังยกเลิก...", "orange")

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
        self.cancel_btn.config(state="normal")
        self.cancel_token = CancelToken()
        cfg = self.settings.get_config()
        threading.Thread(target=self._worker, args=(cfg,),
                         daemon=True).start()

    def _worker(self, cfg):
        try:
            total_folders = len(self.folders)
            ok, fail, errors = 0, 0, []

            for idx, folder in enumerate(self.folders, 1):
                if self.cancel_token.cancelled:
                    break
                fname = os.path.basename(folder)
                self.set_status(f"[{idx}/{total_folders}] กำลังทำ: {fname}")
                try:
                    images = list_images_sorted(folder)
                    if not images:
                        raise ValueError("ไม่พบรูปภาพในโฟลเดอร์นี้")
                    paths = [os.path.join(folder, f) for f in images]
                    # ข้ามไฟล์เสีย แต่ยังทำต่อ
                    report = inspect_images(paths)
                    if not report.ok:
                        raise ValueError("ไม่มีไฟล์ภาพที่เปิดได้")

                    out = self.output_folder.get()
                    if self.subfolder.get():
                        out = os.path.join(out, fname)
                    run_stitch(report.ok, output_folder=out, config=cfg,
                               folder_name=fname, cancel=self.cancel_token)
                    ok += 1
                except Cancelled:
                    raise
                except Exception as e:
                    fail += 1
                    errors.append(f"{fname}: {e}")
                self.set_progress(idx, total_folders)

            msg = f"เสร็จแล้ว!  สำเร็จ {ok} โฟลเดอร์"
            if fail:
                msg += f", ล้มเหลว {fail} โฟลเดอร์"
            self.set_status(msg, "green" if not fail else "orange")
            detail = msg
            if errors:
                detail += "\n\nรายการที่ล้มเหลว:\n" + "\n".join(errors)
            self.post(messagebox.showinfo, "ผลลัพธ์", detail)
        except Cancelled:
            self.set_status("ยกเลิกแล้ว", "orange")
        except Exception as e:
            traceback.print_exc()
            self.set_status(f"เกิดข้อผิดพลาด: {e}", "red")
            self.post(messagebox.showerror, "ข้อผิดพลาด", str(e))
        finally:
            self.post(self.run_btn.config, state="normal")
            self.post(self.cancel_btn.config, state="disabled")


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


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
