# -*- coding: utf-8 -*-
"""หน้าต่างหลักของ Imbine"""

import os

from PySide6.QtCore import QSize, Qt, QThread
from PySide6.QtGui import (QAction, QActionGroup, QIcon, QKeySequence, QPixmap,
                           QUndoStack)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDockWidget,
                               QFileDialog, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox,
                               QProgressBar, QPushButton, QSlider, QTabWidget,
                               QToolBar, QWidget, QVBoxLayout)

from ... import __version__
from ...i18n import available_locales, get_locale, set_locale, t
from ...images import IMAGE_EXTS, image_paths_in, is_image_file, natural_sort_key
from ...inspection import check_output_path, inspect_images
from ...userdata import (delete_preset, list_presets, load_preset,
                         load_settings, remember_folder, save_preset,
                         save_settings, valid_preset_name)
from ..document import StitchDocument
from .batch_panel import BatchPanel
from .inspection_dialog import InspectionDialog
from .preview_panel import PREVIEW_MAX_PIXELS, PreviewPanel
from .settings_panel import SettingsPanel
from .summary_bar import SummaryBar
from .theme import DEFAULT_THEME, THEMES, build_stylesheet, tokens
from .workers import PreviewWorker, StitchJob, StitchWorker
from .workspace import WorkspaceView

THUMBNAIL = QSize(112, 112)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = StitchDocument()
        self.undo_stack = QUndoStack(self)
        self.settings = load_settings()
        self.theme = self.settings.get("theme") or DEFAULT_THEME
        self._thread = self._worker = None
        self._cancel_button = None

        self.resize(1400, 900)
        self.setAcceptDrops(True)

        self._build_central()
        self._build_toolbar()
        self._build_menus()
        self._build_settings_dock()
        self._build_assets_dock()
        self._build_status_bar()
        self._connect()

        self.settings_panel.set_preset_names(list_presets())
        last = self.settings.get("last_config")
        if last:
            from ...config import StitchConfig
            self.settings_panel.apply_config(StitchConfig.from_dict(last))

        self.retranslate()
        self.apply_theme(self.theme)

    # ------------------------------------------------------------------
    # การประกอบหน้าต่าง
    # ------------------------------------------------------------------

    def _build_central(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.summary_bar = SummaryBar()
        layout.addWidget(self.summary_bar)

        self.tabs = QTabWidget()
        self.canvas = WorkspaceView()
        self.preview = PreviewPanel()
        self.batch = BatchPanel()
        self.tabs.addTab(self.canvas, "")
        self.tabs.addTab(self.preview, "")
        self.tabs.addTab(self.batch, "")
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)

    def _build_toolbar(self):
        bar = QToolBar()
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        bar.setIconSize(QSize(18, 18))
        self.addToolBar(bar)
        self.toolbar = bar

        self.import_action = bar.addAction("")
        self.import_action.setShortcut(QKeySequence.Open)
        self.folder_action = bar.addAction("")
        self.folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        bar.addSeparator()
        self.preview_action = bar.addAction("")
        self.preview_action.setShortcut(QKeySequence("Ctrl+P"))
        self.export_action = bar.addAction("")
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        bar.addSeparator()

        self.undo_action = self.undo_stack.createUndoAction(self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.redo_action = self.undo_stack.createRedoAction(self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        bar.addAction(self.undo_action)
        bar.addAction(self.redo_action)
        bar.addSeparator()

        self.zoom_label = QLabel()
        bar.addWidget(self.zoom_label)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(10, 400)
        self.zoom.setValue(100)
        self.zoom.setFixedWidth(140)
        bar.addWidget(self.zoom)
        self.zoom_value = QLabel("100%")
        bar.addWidget(self.zoom_value)

    def _build_menus(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addAction(self.folder_action)
        self.recent_menu = self.file_menu.addMenu("")
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.preview_action)
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()
        self.quit_action = self.file_menu.addAction("")
        self.quit_action.setShortcut(QKeySequence.Quit)
        self.quit_action.triggered.connect(self.close)

        self.edit_menu = menubar.addMenu("")
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.remove_action = self.edit_menu.addAction("")
        self.remove_action.setShortcut(QKeySequence.Delete)
        self.remove_action.triggered.connect(self.remove_selected)
        self.clear_action = self.edit_menu.addAction("")
        self.clear_action.triggered.connect(self.clear_images)

        self.view_menu = menubar.addMenu("")
        self.theme_actions = {}
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        for name in THEMES:
            action = self.view_menu.addAction("")
            action.setCheckable(True)
            action.setChecked(name == self.theme)
            action.triggered.connect(lambda _=False, n=name: self.apply_theme(n))
            theme_group.addAction(action)
            self.theme_actions[name] = action

        self.language_menu = menubar.addMenu("")
        self.language_actions = {}
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        for code, name in available_locales():
            action = self.language_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == get_locale())
            action.triggered.connect(lambda _=False, c=code: self.change_language(c))
            language_group.addAction(action)
            self.language_actions[code] = action

        self.help_menu = menubar.addMenu("")
        self.about_action = self.help_menu.addAction("")
        self.about_action.triggered.connect(self.show_about)

    def _build_settings_dock(self):
        self.settings_dock = QDockWidget(self)
        self.settings_dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.settings_panel = SettingsPanel()
        self.settings_dock.setWidget(self.settings_panel)
        self.settings_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.RightDockWidgetArea, self.settings_dock)

    def _build_assets_dock(self):
        self.assets_dock = QDockWidget(self)
        self.assets = QListWidget()
        self.assets.setViewMode(QListWidget.IconMode)
        self.assets.setIconSize(THUMBNAIL)
        self.assets.setResizeMode(QListWidget.Adjust)
        self.assets.setDragDropMode(QAbstractItemView.InternalMove)
        self.assets.setDefaultDropAction(Qt.MoveAction)
        self.assets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.assets.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.assets_dock.setWidget(self.assets)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.assets_dock)

    def _build_status_bar(self):
        self.status_label = QLabel()
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.progress)

    def _connect(self):
        self.import_action.triggered.connect(self.import_images)
        self.folder_action.triggered.connect(self.import_folder)
        self.export_action.triggered.connect(self.export_images)
        self.preview_action.triggered.connect(self.build_preview)
        self.preview.build_button.clicked.connect(self.build_preview)

        self.zoom.valueChanged.connect(self.canvas.set_zoom_percent)
        self.canvas.zoomChanged.connect(
            lambda value: self.zoom_value.setText(f"{value}%"))
        self.canvas.selectionChanged.connect(self.assets.setCurrentRow)

        self.assets.model().rowsMoved.connect(self._sync_order)
        self.assets.addAction(self._make_remove_action())

        self.settings_panel.configChanged.connect(self._on_config_changed)
        self.settings_panel.preset_save.clicked.connect(self.save_current_preset)
        self.settings_panel.preset_delete.clicked.connect(self.delete_current_preset)
        self.settings_panel.presets.activated.connect(self.load_selected_preset)

        self.batch.runRequested.connect(self.run_batch)
        self.batch.message.connect(self.status_label.setText)

        self.summary_bar.set_config_source(self.settings_panel.to_config)

    def _make_remove_action(self):
        action = QAction(self.assets)
        action.setShortcut(QKeySequence.Delete)
        action.triggered.connect(self.remove_selected)
        self._assets_remove_action = action
        return action

    # ------------------------------------------------------------------
    # ธีมและภาษา
    # ------------------------------------------------------------------

    def apply_theme(self, name):
        self.theme = name if name in THEMES else DEFAULT_THEME
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(self.theme))
        self.canvas.set_colors(tokens(self.theme)["canvas"])
        action = self.theme_actions.get(self.theme)
        if action is not None:
            action.setChecked(True)
        self._store_settings()

    def change_language(self, code):
        set_locale(code)
        self.retranslate()
        self._store_settings()

    def retranslate(self):
        """ตั้งข้อความใหม่ทั้งหน้าต่าง — เรียกซ้ำได้ทุกครั้งที่สลับภาษา"""
        self.setWindowTitle(t("ui.app.title"))

        self.tabs.setTabText(0, t("ui.tab.workspace"))
        self.tabs.setTabText(1, t("ui.tab.preview"))
        self.tabs.setTabText(2, t("ui.tab.batch"))

        self.toolbar.setWindowTitle(t("ui.toolbar.title"))
        self.import_action.setText(t("ui.toolbar.import"))
        self.folder_action.setText(t("ui.toolbar.import_folder"))
        self.preview_action.setText(t("ui.toolbar.preview"))
        self.export_action.setText(t("ui.toolbar.export"))
        self.undo_action.setText(t("ui.toolbar.undo"))
        self.redo_action.setText(t("ui.toolbar.redo"))
        self.zoom_label.setText("  " + t("ui.toolbar.zoom") + " ")

        self.file_menu.setTitle(t("ui.menu.file"))
        self.edit_menu.setTitle(t("ui.menu.edit"))
        self.view_menu.setTitle(t("ui.menu.view"))
        self.language_menu.setTitle(t("ui.menu.language"))
        self.help_menu.setTitle(t("ui.menu.help"))
        self.recent_menu.setTitle(t("ui.menu.recent"))
        self.quit_action.setText(t("ui.menu.quit"))
        self.remove_action.setText(t("ui.menu.remove_selected"))
        self._assets_remove_action.setText(t("ui.menu.remove_selected"))
        self.clear_action.setText(t("ui.menu.clear"))
        self.about_action.setText(t("ui.menu.about"))
        for name, action in self.theme_actions.items():
            action.setText(t(f"ui.menu.theme_{name}"))
        for code, action in self.language_actions.items():
            action.setChecked(code == get_locale())

        self.settings_dock.setWindowTitle(t("ui.dock.settings"))
        self.assets_dock.setWindowTitle(t("ui.dock.assets"))

        self.settings_panel.retranslate()
        self.summary_bar.retranslate()
        self.preview.retranslate()
        self.batch.retranslate()
        self._refresh_recent_menu()

        if not self.document.layers:
            self.status_label.setText(t("ui.app.ready"))

    # ------------------------------------------------------------------
    # นำเข้าภาพ
    # ------------------------------------------------------------------

    def import_images(self):
        patterns = " ".join(f"*{ext}" for ext in IMAGE_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, t("ui.dialog.import"), "",
            t("ui.dialog.image_filter", patterns=patterns))
        if not paths:
            return
        paths.sort(key=lambda path: natural_sort_key(os.path.basename(path)))
        self._add_paths(paths, t("ui.status.imported", count=len(paths)))

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, t("ui.dialog.import_folder"))
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        paths = image_paths_in(folder)
        if not paths:
            self.status_label.setText(t("ui.batch.empty"))
            return
        self.settings = remember_folder(folder, self.settings)
        self._store_settings()
        self._refresh_recent_menu()
        self._add_paths(paths, t("ui.status.imported_sorted", count=len(paths)))

    def _add_paths(self, paths, message):
        self.document.add_paths(paths)
        self._rebuild_assets()
        self._refresh_canvas()
        self.status_label.setText(message)

    def clear_images(self):
        self.document.layers = []
        self._rebuild_assets()
        self._refresh_canvas()
        self.preview.clear()
        self.status_label.setText(t("ui.app.ready"))

    def remove_selected(self):
        rows = sorted((self.assets.row(item) for item in
                       self.assets.selectedItems()), reverse=True)
        if not rows:
            return
        for row in rows:
            self.document.remove(row)
        self._rebuild_assets()
        self._refresh_canvas()

    # -- ลากไฟล์มาวาง --------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """รับได้ทั้งไฟล์ภาพและโฟลเดอร์ ปนกันก็ได้"""
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if os.path.isdir(local):
                paths.extend(image_paths_in(local))
            elif is_image_file(local):
                paths.append(local)
        if not paths:
            return
        paths.sort(key=lambda path: natural_sort_key(os.path.basename(path)))
        self._add_paths(paths, t("ui.status.imported", count=len(paths)))
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # รายการภาพและแคนวาส
    # ------------------------------------------------------------------

    def _rebuild_assets(self):
        self.assets.blockSignals(True)
        try:
            self.assets.clear()
            for layer in self.document.layers:
                pixmap = QPixmap(layer.path).scaled(
                    THUMBNAIL, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(QIcon(pixmap), layer.name)
                item.setToolTip(layer.path)
                self.assets.addItem(item)
        finally:
            self.assets.blockSignals(False)

    def _refresh_canvas(self):
        config = self.settings_panel.to_config()
        self.document.orientation = config.orientation
        self.canvas.set_layers(self.document.layers, self.document.orientation)
        self.summary_bar.set_paths(self.document.paths)

    def _sync_order(self, *args):
        paths = [self.assets.item(i).toolTip() for i in range(self.assets.count())]
        lookup = {layer.path: layer for layer in self.document.layers}
        self.document.layers = [lookup[path] for path in paths if path in lookup]
        self._refresh_canvas()

    def _on_config_changed(self):
        self.document.orientation = self.settings_panel.to_config().orientation
        self.canvas.set_layers(self.document.layers, self.document.orientation)
        self.summary_bar.schedule()

    # ------------------------------------------------------------------
    # พรีเซ็ต
    # ------------------------------------------------------------------

    def save_current_preset(self):
        name = self.settings_panel.presets.currentText().strip()
        if not valid_preset_name(name):
            self.status_label.setText(t("ui.presets.bad_name"))
            return
        save_preset(name, self.settings_panel.to_config())
        self.settings_panel.set_preset_names(list_presets(), name)
        self.status_label.setText(t("ui.presets.saved", name=name))

    def delete_current_preset(self):
        name = self.settings_panel.presets.currentText().strip()
        if valid_preset_name(name) and delete_preset(name):
            self.settings_panel.set_preset_names(list_presets())
            self.status_label.setText(t("ui.presets.deleted", name=name))

    def load_selected_preset(self, *args):
        name = self.settings_panel.presets.currentText().strip()
        if not valid_preset_name(name):
            return
        try:
            config = load_preset(name)
        except KeyError:
            return
        self.settings_panel.apply_config(config)

    # ------------------------------------------------------------------
    # พรีวิวและส่งออก
    # ------------------------------------------------------------------

    def build_preview(self):
        if self._busy():
            return
        if not self.document.paths:
            self.status_label.setText(t("ui.status.no_images"))
            return

        self.tabs.setCurrentWidget(self.preview)
        self.preview.set_working()
        config = self.settings_panel.to_config(
            preview_max_pixels=PREVIEW_MAX_PIXELS)

        worker = PreviewWorker(self.document.paths, config)
        worker.ready.connect(self.preview.set_results)
        worker.failed.connect(self._on_failed_single)
        worker.progress.connect(self._on_preview_progress)
        self._run_worker(worker, t("ui.preview.working"))

    def export_images(self):
        if self._busy():
            return
        if not self.document.paths:
            self.status_label.setText(t("ui.status.no_images"))
            return

        folder = QFileDialog.getExistingDirectory(
            self, t("ui.dialog.export_folder"))
        if not folder:
            return

        report = inspect_images(self.document.paths)
        warnings = check_output_path(
            sorted({os.path.dirname(path) for path in self.document.paths}),
            folder)
        # คำเตือนเรื่องลิมิตของ format คำนวณไว้แล้วในแถบสรุป เอามารวมในกล่อง
        # ยืนยันด้วย เพราะตรงนี้คือจุดสุดท้ายก่อนเสียเวลาทำงานจริง
        plan = self.summary_bar.plan_now(self.settings_panel.to_config())
        if plan is not None:
            warnings.extend(str(w) for w in plan.warnings)

        if InspectionDialog(report, warnings, self).exec() != InspectionDialog.Accepted:
            return

        job = StitchJob(tuple(report.ok), folder, self.settings_panel.to_config(),
                        os.path.basename(folder))
        self._start_jobs([job])

    def run_batch(self, folders, output_folder, separate):
        if self._busy():
            return
        jobs, warnings = [], []
        config = self.settings_panel.to_config()
        for folder in folders:
            report = inspect_images(image_paths_in(folder))
            name = os.path.basename(folder)
            warnings.extend(f"{name}: {text}" for text in report.warnings)
            target = os.path.join(output_folder, name) if separate else output_folder
            warnings.extend(check_output_path([folder], target))
            if report.ok:
                jobs.append(StitchJob(tuple(report.ok), target, config, name))

        if not jobs:
            self.status_label.setText(t("ui.batch.empty"))
            return

        combined = inspect_images([path for job in jobs for path in job.paths])
        if InspectionDialog(combined, warnings, self).exec() != InspectionDialog.Accepted:
            return
        self._start_jobs(jobs)

    # ------------------------------------------------------------------
    # การรันงานเบื้องหลัง
    # ------------------------------------------------------------------

    def _busy(self):
        if self._worker is not None:
            self.status_label.setText(t("ui.status.busy"))
            return True
        return False

    def _start_jobs(self, jobs):
        worker = StitchWorker(jobs)
        worker.progress.connect(self._on_progress)
        worker.failed.connect(self._on_failed)
        worker.jobFinished.connect(self._on_job_finished)
        self._saved_total = 0
        self._run_worker(worker, t("ui.status.working"))

    def _run_worker(self, worker, message):
        """
        ย้าย worker ไปเธรดของตัวเองแล้วเริ่มรัน

        ใช้ร่วมกันทั้งงานส่งออกและงานพรีวิว เพราะการจัดการเธรด ปุ่มยกเลิก และ
        การเปิด/ปิดปุ่มระหว่างทำงานเหมือนกันหมด ต่างกันแค่สัญญาณที่ worker ส่ง
        """
        self._thread = QThread(self)
        self._worker = worker
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.show()
        self.status_label.setText(message)
        self._set_actions_enabled(False)

        self._cancel_button = QPushButton(t("ui.toolbar.cancel"))
        self._cancel_button.clicked.connect(worker.cancel)
        self.statusBar().addPermanentWidget(self._cancel_button)

        self._thread.start()

    def _set_actions_enabled(self, enabled):
        for action in (self.export_action, self.preview_action,
                       self.import_action, self.folder_action):
            action.setEnabled(enabled)
        self.batch.run_button.setEnabled(enabled)
        self.preview.build_button.setEnabled(enabled)

    def _on_progress(self, payload):
        index, event = payload
        self.progress.setValue(round(event.overall * 100))
        self.status_label.setText(t(
            "ui.status.job_progress", index=index + 1,
            step=event.step_label or event.step, done=event.done,
            total=event.total))

    def _on_preview_progress(self, event):
        self.progress.setValue(round(event.overall * 100))

    def _on_job_finished(self, index, context):
        self._saved_total += len(context.saved_paths)
        self.status_label.setText(t("ui.status.job_done", index=index + 1,
                                    count=len(context.saved_paths)))

    def _on_failed(self, index, error):
        self.status_label.setText(t("ui.status.job_failed", index=index + 1))
        QMessageBox.critical(self, t("ui.error.title"), str(error))

    def _on_failed_single(self, error):
        QMessageBox.critical(self, t("ui.error.title"), str(error))

    def _on_finished(self, cancelled):
        self.progress.hide()
        if self._cancel_button is not None:
            self.statusBar().removeWidget(self._cancel_button)
            self._cancel_button.deleteLater()
            self._cancel_button = None
        self._set_actions_enabled(True)
        if cancelled:
            self.status_label.setText(t("ui.status.cancelled"))
        elif getattr(self, "_saved_total", 0):
            self.status_label.setText(t("ui.status.all_done",
                                        count=self._saved_total))
        self._saved_total = 0
        self._worker = self._thread = None

    # ------------------------------------------------------------------
    # อื่น ๆ
    # ------------------------------------------------------------------

    def _refresh_recent_menu(self):
        self.recent_menu.clear()
        recent = self.settings.get("recent_folders") or []
        if not recent:
            action = self.recent_menu.addAction(t("ui.menu.recent_empty"))
            action.setEnabled(False)
            return
        for folder in recent:
            action = self.recent_menu.addAction(folder)
            action.triggered.connect(
                lambda _=False, path=folder: self.load_folder(path))

    def _store_settings(self):
        self.settings["theme"] = self.theme
        self.settings["locale"] = get_locale()
        try:
            self.settings["last_config"] = self.settings_panel.to_config().to_dict()
        except (AttributeError, ValueError):
            pass
        save_settings(self.settings)

    def show_about(self):
        QMessageBox.about(self, t("ui.about.title"),
                          t("ui.about.body", version=__version__))

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            if not self._thread.wait(5000):
                self.status_label.setText(t("ui.status.cancelling"))
                event.ignore()
                return
        self._store_settings()
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("Imbine")
    app.setApplicationVersion(__version__)

    # ตั้งภาษาตามที่ผู้ใช้เคยเลือกไว้ ก่อนสร้าง widget ใด ๆ เพราะข้อความ
    # ถูกอ่านตอน __init__ ของแต่ละตัว
    saved = load_settings()
    if saved.get("locale"):
        set_locale(saved["locale"])

    window = MainWindow()
    window.show()
    return app.exec()
