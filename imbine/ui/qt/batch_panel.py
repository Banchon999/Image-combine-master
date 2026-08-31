# -*- coding: utf-8 -*-
"""คิวต่อภาพหลายโฟลเดอร์รวดเดียว"""

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFileDialog,
                               QHBoxLayout, QLabel, QListWidget, QPushButton,
                               QVBoxLayout, QWidget)

from ...i18n import t
from ...images import image_paths_in


class BatchPanel(QWidget):
    runRequested = Signal(list, str, bool)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.title = QLabel()
        layout.addWidget(self.title)

        self.folders = QListWidget()
        self.folders.setDragDropMode(QAbstractItemView.InternalMove)
        self.folders.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.folders, 1)

        row = QHBoxLayout()
        self.add_button = QPushButton()
        self.children_button = QPushButton()
        self.remove_button = QPushButton()
        for button in (self.add_button, self.children_button, self.remove_button):
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

        self.separate = QCheckBox()
        self.separate.setChecked(True)
        layout.addWidget(self.separate)

        output_row = QHBoxLayout()
        self.output_label = QLabel()
        self.output_button = QPushButton()
        output_row.addWidget(self.output_label, 1)
        output_row.addWidget(self.output_button)
        layout.addLayout(output_row)

        self.run_button = QPushButton()
        self.run_button.setProperty("accent", True)
        layout.addWidget(self.run_button)

        self.hint = QLabel()
        self.hint.setProperty("hint", True)
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.output_folder = ""
        self.add_button.clicked.connect(self.add_folder)
        self.children_button.clicked.connect(self.add_subfolders)
        self.remove_button.clicked.connect(self.remove_selected)
        self.output_button.clicked.connect(self.choose_output)
        self.run_button.clicked.connect(self._request_run)

        self.retranslate()

    def _existing(self):
        return {self.folders.item(i).text() for i in range(self.folders.count())}

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, t("ui.dialog.add_folder"))
        if folder and folder not in self._existing():
            self.folders.addItem(folder)

    def add_subfolders(self):
        parent = QFileDialog.getExistingDirectory(
            self, t("ui.dialog.add_subfolders"))
        if not parent:
            return
        for name in sorted(os.listdir(parent)):
            path = os.path.join(parent, name)
            if (os.path.isdir(path) and path not in self._existing()
                    and image_paths_in(path)):
                self.folders.addItem(path)

    def remove_selected(self):
        for item in self.folders.selectedItems():
            self.folders.takeItem(self.folders.row(item))

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, t("ui.dialog.batch_output"))
        if folder:
            self.output_folder = folder
            self.output_label.setText(folder)

    def _request_run(self):
        folders = [self.folders.item(i).text()
                   for i in range(self.folders.count())]
        if not folders:
            self.message.emit(t("ui.batch.empty"))
            return
        if not self.output_folder:
            # เดิมกดปุ่มแล้วเงียบไปเฉย ๆ ถ้ายังไม่ได้เลือกปลายทาง
            self.message.emit(t("ui.batch.need_output"))
            return
        self.runRequested.emit(folders, self.output_folder,
                               self.separate.isChecked())

    def retranslate(self):
        self.title.setText(t("ui.batch.title"))
        self.add_button.setText(t("ui.batch.add"))
        self.children_button.setText(t("ui.batch.add_subfolders"))
        self.remove_button.setText(t("ui.batch.remove"))
        self.separate.setText(t("ui.batch.separate"))
        self.output_button.setText(t("ui.batch.output"))
        self.run_button.setText(t("ui.batch.run"))
        self.hint.setText(t("ui.batch.hint"))
        if not self.output_folder:
            self.output_label.setText(t("ui.batch.no_output"))
