"""Multi-folder batch queue for the Qt application."""

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFileDialog,
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget)

from ...images import image_paths_in


class BatchPanel(QWidget):
    runRequested = Signal(list, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("MULTI-FOLDER BATCH QUEUE"))
        self.folders = QListWidget()
        self.folders.setDragDropMode(QAbstractItemView.InternalMove)
        layout.addWidget(self.folders)
        row = QHBoxLayout()
        add = QPushButton("＋ Folder")
        children = QPushButton("＋ Subfolders")
        remove = QPushButton("Remove")
        row.addWidget(add); row.addWidget(children); row.addWidget(remove)
        layout.addLayout(row)
        self.separate = QCheckBox("สร้างโฟลเดอร์ผลลัพธ์แยกตามชื่อโฟลเดอร์ต้นทาง")
        self.separate.setChecked(True)
        layout.addWidget(self.separate)
        output_row = QHBoxLayout()
        self.output_label = QLabel("ยังไม่ได้เลือกปลายทาง")
        output = QPushButton("Output…")
        output_row.addWidget(self.output_label, 1); output_row.addWidget(output)
        layout.addLayout(output_row)
        self.run_button = QPushButton("▶ Run all folders")
        layout.addWidget(self.run_button)
        self.output_folder = ""
        add.clicked.connect(self.add_folder)
        children.clicked.connect(self.add_subfolders)
        remove.clicked.connect(lambda: self.folders.takeItem(self.folders.currentRow()))
        output.clicked.connect(self.choose_output)
        self.run_button.clicked.connect(self._request_run)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add image folder")
        existing = {self.folders.item(i).text() for i in range(self.folders.count())}
        if folder and folder not in existing:
            self.folders.addItem(folder)

    def add_subfolders(self):
        parent = QFileDialog.getExistingDirectory(self, "Add all subfolders")
        if not parent:
            return
        for name in sorted(os.listdir(parent)):
            path = os.path.join(parent, name)
            existing = {self.folders.item(i).text() for i in range(self.folders.count())}
            if os.path.isdir(path) and path not in existing and image_paths_in(path):
                self.folders.addItem(path)

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Batch output folder")
        if folder:
            self.output_folder = folder
            self.output_label.setText(folder)

    def _request_run(self):
        folders = [self.folders.item(i).text() for i in range(self.folders.count())]
        if folders and self.output_folder:
            self.runRequested.emit(folders, self.output_folder, self.separate.isChecked())
