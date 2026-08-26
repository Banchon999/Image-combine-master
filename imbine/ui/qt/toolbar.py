"""Top toolbar ของ Qt frontend."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QToolBar


class MainToolBar(QToolBar):
    import_requested = Signal()
    export_requested = Signal()
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    fit_requested = Signal()

    def __init__(self, undo_stack, parent=None):
        super().__init__("เครื่องมือหลัก", parent)
        self.setObjectName("mainToolbar")
        self.setMovable(False)
        self.import_action = self.addAction("Import")
        self.export_action = self.addAction("Export")
        self.addSeparator()
        self.undo_action = undo_stack.createUndoAction(self, "Undo")
        self.redo_action = undo_stack.createRedoAction(self, "Redo")
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        self.addSeparator()
        self.zoom_in_action = self.addAction("Zoom In")
        self.zoom_out_action = self.addAction("Zoom Out")
        self.fit_action = self.addAction("Fit")
        self.addSeparator()
        self.job_status = QLabel("พร้อมทำงาน")
        self.job_status.setObjectName("jobStatus")
        self.addWidget(self.job_status)

        self.import_action.triggered.connect(self.import_requested)
        self.export_action.triggered.connect(self.export_requested)
        self.zoom_in_action.triggered.connect(self.zoom_in_requested)
        self.zoom_out_action.triggered.connect(self.zoom_out_requested)
        self.fit_action.triggered.connect(self.fit_requested)

    def set_job_status(self, text):
        self.job_status.setText(text)
