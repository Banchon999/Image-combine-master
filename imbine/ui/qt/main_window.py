"""Main Qt editing window for Imbine."""

import os

from PySide6.QtCore import QThread, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QUndoStack
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox,
    QDockWidget, QFileDialog, QFormLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QLineEdit, QCheckBox,
    QSlider, QSpinBox, QDoubleSpinBox, QTabWidget, QToolBar, QWidget)

from ...config import StitchConfig
from ...images import image_paths_in, natural_sort_key
from ...inspection import check_output_path, inspect_images
from ...naming import build_output_name, ext_for
from ..document import StitchDocument
from ..qt_export import populate_export_formats
from .batch_panel import BatchPanel
from .inspection_dialog import InspectionDialog
from .workspace import WorkspaceView
from .workers import StitchJob, StitchWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = StitchDocument()
        self.undo_stack = QUndoStack(self)
        self.setWindowTitle("Imbine — Interactive Image Workspace")
        self.resize(1400, 900)
        self.canvas = WorkspaceView()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.canvas, "Interactive Workspace")
        self.batch = BatchPanel()
        self.tabs.addTab(self.batch, "Multi-folder Batch")
        self.setCentralWidget(self.tabs)
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
        self.batch.runRequested.connect(self.run_batch)
        self._thread = self._worker = None

    def _build_toolbar(self):
        bar = QToolBar("Action bar")
        bar.setMovable(False)
        bar.setIconSize(QSize(20, 20))
        self.addToolBar(bar)
        self.import_action = bar.addAction("＋ Import")
        self.export_action = bar.addAction("⇩ Export")
        self.folder_action = bar.addAction("▣ Import Folder")
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
        self.folder_action.triggered.connect(self.import_folder)
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
        self.pattern = QLineEdit("{folder}_{n3}")
        self.name_preview = QLabel()
        self.quality = QSpinBox(); self.quality.setRange(1, 100); self.quality.setValue(92)
        self.parts = QSpinBox(); self.parts.setRange(1, 999); self.parts.setValue(1)
        self.max_size = QSpinBox(); self.max_size.setRange(0, 1000000); self.max_size.setSuffix(" px")
        self.uniform = QCheckBox(); self.uniform.setChecked(True)
        self.overwrite = QCheckBox()
        form.addRow("Direction", self.orientation)
        form.addRow("Blend mode", self.blend)
        form.addRow("Rotate", self.rotation)
        form.addRow("Scale", self.scale)
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        form.addRow("Export format", self.formats)
        form.addRow("Smart name", self.pattern)
        form.addRow("Preview", self.name_preview)
        form.addRow("Quality", self.quality)
        form.addRow("Output parts", self.parts)
        form.addRow("Max part size", self.max_size)
        form.addRow("Uniform size", self.uniform)
        form.addRow("Overwrite", self.overwrite)
        dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.orientation.currentIndexChanged.connect(self._refresh_canvas)
        self.pattern.textChanged.connect(self._update_name_preview)
        self.formats.currentTextChanged.connect(self._update_name_preview)
        self.parts.valueChanged.connect(self._update_name_preview)
        self._update_name_preview()
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
        paths.sort(key=lambda path: natural_sort_key(os.path.basename(path)))
        self.document.add_paths(paths)
        self._rebuild_assets()
        self._refresh_canvas()
        self.status_label.setText(f"นำเข้าแล้ว {len(paths)} ภาพ")

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import image folder")
        if not folder:
            return
        paths = image_paths_in(folder)
        self.document.add_paths(paths)
        self._rebuild_assets(); self._refresh_canvas()
        self.status_label.setText(f"Smart Order: {len(paths)} ภาพ")

    def _update_name_preview(self):
        names = [build_output_name(self.pattern.text(), i, self.parts.value(), "chapter")
                 + ext_for(self.formats.currentText()) for i in range(1, min(3, self.parts.value()) + 1)]
        self.name_preview.setText(", ".join(names))

    def _config(self):
        return StitchConfig(
            orientation=self.document.orientation, fmt=self.formats.currentText(),
            name_pattern=self.pattern.text(), quality=self.quality.value(),
            parts_count=self.parts.value(), max_size=self.max_size.value(),
            uniform=self.uniform.isChecked(), overwrite=self.overwrite.isChecked())

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
        report = inspect_images(self.document.paths)
        warnings = check_output_path(
            list({os.path.dirname(path) for path in self.document.paths}), folder)
        if InspectionDialog(report, warnings, self).exec() != InspectionDialog.Accepted:
            return
        job = StitchJob(tuple(report.ok), folder, self._config(), os.path.basename(folder))
        self._start_jobs([job])

    def run_batch(self, folders, output_folder, separate):
        jobs, warnings = [], []
        config = self._config()
        for folder in folders:
            report = inspect_images(image_paths_in(folder))
            warnings.extend(f"{os.path.basename(folder)}: {text}" for text in report.warnings)
            target = os.path.join(output_folder, os.path.basename(folder)) if separate else output_folder
            warnings.extend(check_output_path([folder], target))
            if report.ok:
                jobs.append(StitchJob(tuple(report.ok), target, config, os.path.basename(folder)))
        if not jobs:
            QMessageBox.warning(self, "Batch", "ไม่พบภาพที่ประมวลผลได้")
            return
        combined = inspect_images([path for job in jobs for path in job.paths])
        if InspectionDialog(combined, warnings, self).exec() != InspectionDialog.Accepted:
            return
        self._start_jobs(jobs)

    def _start_jobs(self, jobs):
        self._thread = QThread(self)
        self._worker = StitchWorker(jobs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.failed.connect(self._on_failed)
        self._worker.jobFinished.connect(
            lambda index, context: self.status_label.setText(
                f"งาน {index + 1} เสร็จสิ้น — {len(context.saved_paths)} ไฟล์"))
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self.progress.setRange(0, 100); self.progress.setValue(0); self.progress.show()
        self.status_label.setText("กำลังประมวลผล…")
        self.export_action.setEnabled(False); self.batch.run_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._worker.cancel)
        self.statusBar().addPermanentWidget(self.cancel_button)
        self._thread.start()

    def _on_progress(self, payload):
        index, event = payload
        self.progress.setValue(round(event.overall * 100))
        self.status_label.setText(f"งาน {index + 1}: {event.step} {event.done}/{event.total}")

    def _on_failed(self, index, error):
        self.status_label.setText(f"งาน {index + 1} ล้มเหลว")
        QMessageBox.critical(self, "Processing failed", str(error))

    def _on_finished(self, cancelled):
        self.progress.hide(); self.cancel_button.deleteLater()
        self.export_action.setEnabled(True); self.batch.run_button.setEnabled(True)
        self.status_label.setText("ยกเลิกแล้ว" if cancelled else "ประมวลผล Batch เสร็จสิ้น")
        self._worker = self._thread = None

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            if not self._thread.wait(5000):
                self.status_label.setText("กำลังยกเลิกงาน กรุณารอสักครู่…")
                event.ignore()
                return
        super().closeEvent(event)


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
