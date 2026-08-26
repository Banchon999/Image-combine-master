"""Background workers that keep long-running stitching away from Qt's UI thread."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot

from ...api import run_stitch
from ...pipeline import CancelToken, Cancelled


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
