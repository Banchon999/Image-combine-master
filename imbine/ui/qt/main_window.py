"""หน้าต่างหลักของ Qt frontend."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QUndoStack
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QMainWindow,
                               QProgressBar)

from .asset_drawer import AssetDrawer
from .canvas import Canvas
from .properties_panel import PropertiesPanel
from .toolbar import MainToolBar

IMAGE_FILTER = "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif)"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainWindow")
        self.setWindowTitle("Imbine — Image Combiner")
        self.resize(1200, 800)
        self.undo_stack = QUndoStack(self)
        self.canvas = Canvas(self)
        self.setCentralWidget(self.canvas)

        self.toolbar = MainToolBar(self.undo_stack, self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.properties_panel = PropertiesPanel(self)
        self.properties_dock = QDockWidget("Crop & Transform", self)
        self.properties_dock.setObjectName("propertiesDock")
        self.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)

        self.asset_drawer = AssetDrawer(self)
        self.asset_dock = QDockWidget("Assets", self)
        self.asset_dock.setObjectName("assetDock")
        self.asset_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.asset_dock.setWidget(self.asset_drawer)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.asset_dock)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMaximumWidth(220)
        self.statusBar().showMessage("เสร็จสิ้น")
        self.statusBar().addPermanentWidget(self.progress)
        self._connect_actions()

    def _connect_actions(self):
        self.toolbar.import_requested.connect(self.import_assets)
        self.toolbar.export_requested.connect(self.export_image)
        self.toolbar.zoom_in_requested.connect(self.canvas.zoom_in)
        self.toolbar.zoom_out_requested.connect(self.canvas.zoom_out)
        self.toolbar.fit_requested.connect(self.canvas.fit_content)
        self.toolbar.import_action.setShortcut(QKeySequence.Open)
        self.toolbar.export_action.setShortcut(QKeySequence.Save)
        self.asset_drawer.asset_activated.connect(self.canvas.show_image)
        self.canvas.files_dropped.connect(self.add_assets)
        self.properties_panel.auto_align_requested.connect(
            lambda: self.set_job_status("เสร็จสิ้น", 100))

    def import_assets(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import images", "", IMAGE_FILTER)
        if paths:
            self.add_assets(paths)

    def add_assets(self, paths):
        paths = [p for p in paths if Path(p).is_file()]
        if not paths:
            return
        self.set_job_status("กำลังประมวลผล", 25)
        self.asset_drawer.add_assets(paths)
        self.canvas.show_image(paths[0])
        self.set_job_status("เสร็จสิ้น", 100)

    def export_image(self):
        if not self.canvas.scene().items():
            self.statusBar().showMessage("ยังไม่มีภาพสำหรับ Export", 4000)
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export image", "combined.png",
                                               "PNG (*.png);;JPEG (*.jpg *.jpeg)")
        if not path:
            return
        self.set_job_status("กำลังประมวลผล", 50)
        pixmap = self.canvas.scene().items()[0].pixmap()
        if pixmap.save(path):
            self.set_job_status("เสร็จสิ้น", 100)
        else:
            self.statusBar().showMessage("Export ไม่สำเร็จ", 5000)
            self.toolbar.set_job_status("เกิดข้อผิดพลาด")

    def set_job_status(self, text, progress=None):
        self.toolbar.set_job_status(text)
        self.statusBar().showMessage(text)
        if progress is not None:
            self.progress.setValue(progress)
