"""Main Qt editing window for Imbine."""

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QUndoStack
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox,
    QDockWidget, QFileDialog, QFormLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressBar, QSlider, QSpinBox, QDoubleSpinBox,
    QToolBar, QVBoxLayout, QWidget)

from ...api import run_stitch
from ...config import StitchConfig
from ..document import StitchDocument
from ..qt_export import populate_export_formats
from .workspace import WorkspaceView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = StitchDocument()
        self.undo_stack = QUndoStack(self)
        self.setWindowTitle("Imbine — Interactive Image Workspace")
        self.resize(1400, 900)
        self.canvas = WorkspaceView()
        self.setCentralWidget(self.canvas)
        self._build_toolbar()
        self._build_properties()
        self._build_assets()
        self.status_label = QLabel("พร้อมใช้งาน")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.progress)
        self.canvas.selectionChanged.connect(self._select_asset)

    def _build_toolbar(self):
        bar = QToolBar("Action bar")
        bar.setMovable(False)
        bar.setIconSize(QSize(20, 20))
        self.addToolBar(bar)
        self.import_action = bar.addAction("＋ Import")
        self.export_action = bar.addAction("⇩ Export")
        bar.addSeparator()
        bar.addAction(self.undo_stack.createUndoAction(self, "Undo"))
        bar.addAction(self.undo_stack.createRedoAction(self, "Redo"))
        bar.addSeparator()
        bar.addWidget(QLabel("  Zoom "))
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(10, 400)
        self.zoom.setValue(100)
        self.zoom.setFixedWidth(150)
        bar.addWidget(self.zoom)
        self.zoom_value = QLabel("100%")
        bar.addWidget(self.zoom_value)
        self.import_action.triggered.connect(self.import_images)
        self.export_action.triggered.connect(self.export_image)
        self.zoom.valueChanged.connect(self.canvas.set_zoom_percent)
        self.canvas.zoomChanged.connect(lambda value: self.zoom_value.setText(f"{value}%"))

    def _build_properties(self):
        dock = QDockWidget("TOOLS & PROPERTIES", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        panel = QWidget()
        form = QFormLayout(panel)
        self.orientation = QComboBox(); self.orientation.addItems(["Vertical", "Horizontal"])
        self.blend = QComboBox(); self.blend.addItems(["Normal", "Multiply", "Screen", "Overlay"])
        self.rotation = QDoubleSpinBox(); self.rotation.setRange(-180, 180); self.rotation.setSuffix("°")
        self.scale = QDoubleSpinBox(); self.scale.setRange(.05, 8); self.scale.setValue(1); self.scale.setSingleStep(.05)
        self.offset_x = QSpinBox(); self.offset_x.setRange(-100000, 100000)
        self.offset_y = QSpinBox(); self.offset_y.setRange(-100000, 100000)
        self.formats = QComboBox(); populate_export_formats(self.formats)
        form.addRow("Direction", self.orientation)
        form.addRow("Blend mode", self.blend)
        form.addRow("Rotate", self.rotation)
        form.addRow("Scale", self.scale)
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        form.addRow("Export format", self.formats)
        dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.orientation.currentIndexChanged.connect(self._refresh_canvas)
        for widget in (self.rotation, self.scale, self.offset_x, self.offset_y):
            widget.valueChanged.connect(self._apply_properties)

    def _build_assets(self):
        dock = QDockWidget("ASSETS", self)
        self.assets = QListWidget()
        self.assets.setViewMode(QListWidget.IconMode)
        self.assets.setIconSize(QSize(112, 112))
        self.assets.setResizeMode(QListWidget.Adjust)
        self.assets.setDragDropMode(QAbstractItemView.InternalMove)
        self.assets.setDefaultDropAction(Qt.MoveAction)
        self.assets.setContextMenuPolicy(Qt.ActionsContextMenu)
        remove = QAction("Remove selected", self.assets)
        remove.setShortcut(QKeySequence.Delete)
        remove.triggered.connect(self.remove_selected)
        self.assets.addAction(remove)
        self.assets.model().rowsMoved.connect(self._sync_order)
        self.assets.currentRowChanged.connect(self._load_properties)
        dock.setWidget(self.assets)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def import_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import images", "", "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff)")
        if not paths:
            return
        self.document.add_paths(paths)
        self._rebuild_assets()
        self._refresh_canvas()
        self.status_label.setText(f"นำเข้าแล้ว {len(paths)} ภาพ")

    def _rebuild_assets(self):
        self.assets.clear()
        for layer in self.document.layers:
            pixmap = QPixmap(layer.path).scaled(112, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(QIcon(pixmap), layer.name)
            item.setToolTip(layer.path)
            self.assets.addItem(item)

    def _refresh_canvas(self):
        self.document.orientation = "vertical" if self.orientation.currentIndex() == 0 else "horizontal"
        self.canvas.set_layers(self.document.layers, self.document.orientation)

    def _select_asset(self, index): self.assets.setCurrentRow(index)
    def _load_properties(self, index):
        if index < 0 or index >= len(self.document.layers): return
        layer = self.document.layers[index]
        for widget in (self.rotation, self.scale, self.offset_x, self.offset_y): widget.blockSignals(True)
        self.rotation.setValue(layer.rotation); self.scale.setValue(layer.scale)
        self.offset_x.setValue(round(layer.offset_x)); self.offset_y.setValue(round(layer.offset_y))
        for widget in (self.rotation, self.scale, self.offset_x, self.offset_y): widget.blockSignals(False)

    def _apply_properties(self):
        row = self.assets.currentRow()
        if row < 0: return
        layer = self.document.layers[row]
        layer.rotation = self.rotation.value(); layer.scale = self.scale.value()
        layer.offset_x = self.offset_x.value(); layer.offset_y = self.offset_y.value()
        self._refresh_canvas()

    def _sync_order(self, *args):
        paths = [self.assets.item(i).toolTip() for i in range(self.assets.count())]
        lookup = {layer.path: layer for layer in self.document.layers}
        self.document.layers = [lookup[path] for path in paths]
        self._refresh_canvas()

    def remove_selected(self):
        row = self.assets.currentRow()
        if row >= 0:
            self.document.remove(row); self._rebuild_assets(); self._refresh_canvas()

    def export_image(self):
        if not self.document.paths:
            QMessageBox.information(self, "Export", "กรุณานำเข้าภาพก่อน")
            return
        folder = QFileDialog.getExistingDirectory(self, "Export folder")
        if not folder: return
        self.status_label.setText("กำลังประมวลผล…"); self.progress.show(); self.progress.setRange(0, 0)
        QApplication.processEvents()
        try:
            config = StitchConfig(orientation=self.document.orientation, fmt=self.formats.currentText())
            context = run_stitch(self.document.paths, folder, config, os.path.basename(folder))
        except Exception as error:
            QMessageBox.critical(self, "Export failed", str(error)); self.status_label.setText("เกิดข้อผิดพลาด")
        else:
            self.status_label.setText(f"เสร็จสิ้น — {len(context.saved_paths)} ไฟล์")
        finally:
            self.progress.hide()


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QDockWidget, QWidget { background: #22252d; color: #edf0f7; }
        QToolBar { background: #292d37; border: 0; padding: 7px; spacing: 7px; }
        QToolButton { padding: 7px 11px; border-radius: 5px; }
        QToolButton:hover { background: #3d4352; }
        QDockWidget::title { background: #292d37; padding: 9px; font-weight: 600; }
        QListWidget { background: #1d2027; border: 0; padding: 8px; }
        QListWidget::item:selected { background: #3f68d9; border-radius: 5px; }
        QComboBox, QSpinBox, QDoubleSpinBox { background: #303541; padding: 5px; border: 1px solid #454b59; border-radius: 4px; }
        QStatusBar { background: #292d37; }
    """)
    window = MainWindow()
    window.show()
    return app.exec()
