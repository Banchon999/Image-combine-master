# -*- coding: utf-8 -*-
"""
หน้าบ้านที่ UI และสคริปต์ภายนอกเรียกใช้

จุดประสงค์คือให้ UI ไม่ต้องรู้จัก Step หรือ PipelineContext เลย — เรียก
run_stitch() ทีเดียวจบ ส่วนใครที่อยากแทรกขั้นตอนเองค่อยประกอบ pipeline มาส่ง
"""

from .config import StitchConfig
from .pipeline import CancelToken, PipelineContext, Progress
from .steps import build_default_pipeline


def run_stitch(image_paths, output_folder="", config=None, folder_name="",
               progress_cb=None, cancel=None, pipeline=None):
    """
    ต่อภาพหนึ่งชุดตั้งแต่เปิดไฟล์จนบันทึกเสร็จ

    พารามิเตอร์:
      image_paths  : list ของ path รูปภาพ (ต้องเรียงลำดับมาแล้ว)
      output_folder: โฟลเดอร์ปลายทาง — ปล่อยว่าง = ไม่บันทึก (ใช้ทำ preview)
      config       : StitchConfig หรือ dict — None = ใช้ค่าเริ่มต้น
      folder_name  : ชื่อที่จะไปแทน {folder} ในชื่อไฟล์
      progress_cb  : ฟังก์ชันรับ ProgressEvent ตัวเดียว
      cancel       : CancelToken สำหรับสั่งหยุดกลางคัน
      pipeline     : สายที่ประกอบเอง — None = ใช้สายมาตรฐาน

    คืนค่า: PipelineContext ที่มี .results (ภาพ) และ .saved_paths (ไฟล์)
    โยน Cancelled ถ้าผู้ใช้สั่งยกเลิก
    """
    if config is None:
        config = StitchConfig()
    elif isinstance(config, dict):
        config = StitchConfig.from_dict(config)

    ctx = PipelineContext(
        config=config,
        source_paths=list(image_paths),
        output_folder=output_folder,
        folder_name=folder_name,
        progress=Progress(progress_cb),
        cancel=cancel or CancelToken(),
    )

    if pipeline is None:
        pipeline = build_default_pipeline(save=bool(output_folder))
    return pipeline.run(ctx)


# ----------------------------------------------------------------------
# ฟังก์ชันหน้าตาเดิม — เก็บไว้ให้สคริปต์เก่าและตัวอย่างใน README ยังรันได้
# ----------------------------------------------------------------------

def stitch_images(image_paths, orientation="vertical", parts_count=1,
                  max_size=0, uniform=True, bg_color=(255, 255, 255),
                  progress_cb=None):
    """
    ต่อภาพแล้วคืน list ของ PIL.Image โดยไม่บันทึกลงดิสก์

    progress_cb ยังเป็นแบบเดิมคือรับ (ทำไปแล้ว, ทั้งหมด) ของ *ขั้นที่กำลังทำ*
    ไม่ใช่ ProgressEvent — ใครอยากได้ข้อมูลเต็มให้ไปใช้ run_stitch()
    """
    config = StitchConfig(
        orientation=orientation, parts_count=parts_count, max_size=max_size,
        uniform=uniform, bg_color=bg_color)

    adapter = None
    if progress_cb:
        def adapter(event):
            progress_cb(event.done, event.total)

    return run_stitch(image_paths, config=config, progress_cb=adapter).results
