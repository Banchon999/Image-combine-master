# -*- coding: utf-8 -*-
"""ตัวทำงานเบื้องหลัง — กันงานหนักไม่ให้ไปค้างอยู่บนเธรดของ UI"""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot

from ...api import run_stitch
from ...pipeline import CancelToken, Cancelled
from ...steps import build_preview_pipeline


@dataclass(frozen=True)
class StitchJob:
    paths: tuple
    output_folder: str
    config: object
    folder_name: str = ""


class StitchWorker(QObject):
    progress = Signal(object)
    jobFinished = Signal(int, object)
    failed = Signal(int, object)
    finished = Signal(bool)

    def __init__(self, jobs):
        super().__init__()
        self.jobs = list(jobs)
        self.cancel_token = CancelToken()

    @Slot()
    def run(self):
        cancelled = False
        for index, job in enumerate(self.jobs):
            if self.cancel_token.cancelled:
                cancelled = True
                break
            try:
                context = run_stitch(
                    job.paths, job.output_folder, job.config, job.folder_name,
                    progress_cb=lambda event, i=index: self.progress.emit((i, event)),
                    cancel=self.cancel_token)
            except Cancelled:
                cancelled = True
                break
            except Exception as error:
                self.failed.emit(index, error)
            else:
                self.jobFinished.emit(index, context)
        self.finished.emit(cancelled)

    def cancel(self):
        self.cancel_token.cancel()


class PreviewWorker(QObject):
    """
    ต่อภาพเพื่อดูผลอย่างเดียว ไม่เขียนไฟล์

    แยกคลาสจาก StitchWorker เพราะสัญญาต่างกันชัดเจน: อันนี้คืน *ภาพ* กลับมา
    ให้ UI วาด ไม่ใช่คืน path ของไฟล์ที่เขียนไปแล้ว การยัดสองอย่างนี้ไว้ใน
    คลาสเดียวจะทำให้ผู้รับสัญญาณต้องเดาเองว่าได้อะไรมา
    """

    progress = Signal(object)
    ready = Signal(object)
    failed = Signal(object)
    finished = Signal(bool)

    def __init__(self, paths, config):
        super().__init__()
        self.paths = list(paths)
        self.config = config
        self.cancel_token = CancelToken()

    @Slot()
    def run(self):
        cancelled = False
        try:
            context = run_stitch(
                self.paths, "", self.config,
                progress_cb=self.progress.emit,
                cancel=self.cancel_token,
                pipeline=build_preview_pipeline())
        except Cancelled:
            cancelled = True
        except Exception as error:
            self.failed.emit(error)
        else:
            self.ready.emit(context.results)
        self.finished.emit(cancelled)

    def cancel(self):
        self.cancel_token.cancel()
