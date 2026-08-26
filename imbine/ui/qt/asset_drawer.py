"""Filmstrip แสดง asset ที่ import แล้ว."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class AssetDrawer(QListWidget):
    asset_activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("assetDrawer")
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(False)
        self.setIconSize(QSize(96, 72))
        self.setMinimumHeight(120)
        self.itemDoubleClicked.connect(
            lambda item: self.asset_activated.emit(item.data(Qt.UserRole)))

    def add_assets(self, paths):
        for path in paths:
            path = str(path)
            pixmap = QPixmap(path)
            if pixmap.isNull():
                continue
            thumb = pixmap.scaled(self.iconSize(), Qt.KeepAspectRatio,
                                  Qt.SmoothTransformation)
            item = QListWidgetItem(QIcon(thumb), Path(path).name)
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)
