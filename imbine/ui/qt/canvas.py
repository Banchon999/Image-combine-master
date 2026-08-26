"""Interactive graphics canvas สำหรับ preview และจัดวางภาพ."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class Canvas(QGraphicsView):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        scene = QGraphicsScene(parent)
        super().__init__(scene, parent)
        self.setObjectName("canvas")
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)

    def show_image(self, path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False
        self.scene().clear()
        item = QGraphicsPixmapItem(pixmap)
        item.setFlag(QGraphicsPixmapItem.ItemIsMovable)
        item.setFlag(QGraphicsPixmapItem.ItemIsSelectable)
        self.scene().addItem(item)
        self.scene().setSceneRect(item.boundingRect())
        self.fit_content()
        return True

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1 / 1.2, 1 / 1.2)

    def fit_content(self):
        if not self.scene().items():
            return
        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            (self.zoom_in if event.angleDelta().y() > 0 else self.zoom_out)()
            event.accept()
        else:
            super().wheelEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
