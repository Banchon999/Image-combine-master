"""Zoomable, viewport-rendered image workspace and overlay controls."""

from PySide6.QtCore import QLineF, Signal
from PySide6.QtGui import QColor, QImageReader, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class WorkspaceView(QGraphicsView):
    zoomChanged = Signal(int)
    selectionChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self._items = []
        self._grid = True
        self._zoom = 1.0
        self._grid_color = QColor(255, 255, 255, 22)
        self.set_colors("#17191f")

    def set_colors(self, canvas, grid=None):
        """
        ตั้งสีพื้นหลังและเส้นกริดจากธีม

        เดิมสีสองค่านี้ฝังอยู่ในไฟล์นี้ ทำให้เปลี่ยนธีมแล้วแคนวาสยังมืดอยู่
        ตัวเดียว — ตอนนี้ imbine.ui.qt.theme เป็นเจ้าของสีทั้งหมด
        """
        self.setBackgroundBrush(QColor(canvas))
        if grid is not None:
            self._grid_color = QColor(grid)
        else:
            # เส้นกริดต้องตัดกับพื้นหลัง: พื้นมืดใช้เส้นสว่าง พื้นสว่างใช้เส้นมืด
            base = QColor(canvas)
            light = base.lightness() > 127
            self._grid_color = (QColor(0, 0, 0, 26) if light
                                else QColor(255, 255, 255, 22))
        self.viewport().update()

    def set_layers(self, layers, orientation="vertical"):
        self.scene().clear()
        self._items = []
        cursor = 0.0
        for index, layer in enumerate(layers):
            reader = QImageReader(layer.path)
            image = reader.read()
            if image.isNull():
                continue
            item = QGraphicsPixmapItem(QPixmap.fromImage(image))
            item.setData(0, index)
            item.setFlag(QGraphicsPixmapItem.ItemIsSelectable)
            item.setOpacity(layer.opacity)
            item.setRotation(layer.rotation)
            item.setScale(layer.scale)
            if orientation == "vertical":
                item.setPos(layer.offset_x, cursor + layer.offset_y)
                cursor += image.height() * layer.scale
            else:
                item.setPos(cursor + layer.offset_x, layer.offset_y)
                cursor += image.width() * layer.scale
            self.scene().addItem(item)
            self._items.append(item)
        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-200, -200, 200, 200))
        self.scene().selectionChanged.connect(self._emit_selection)

    def set_grid_visible(self, visible):
        self._grid = visible
        self.viewport().update()

    def set_zoom_percent(self, percent):
        self._zoom = max(0.1, min(8.0, percent / 100.0))
        transform = self.transform()
        transform.reset()
        transform.scale(self._zoom, self._zoom)
        self.setTransform(transform)
        self.zoomChanged.emit(round(self._zoom * 100))

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.set_zoom_percent(round(self._zoom * factor * 100))

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self._grid:
            return
        step = 50
        painter.setPen(QPen(self._grid_color, 0))
        left = int(rect.left()) - int(rect.left()) % step
        top = int(rect.top()) - int(rect.top()) % step
        for x in range(left, int(rect.right()) + step, step):
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()) + step, step):
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))

    def _emit_selection(self):
        selected = self.scene().selectedItems()
        if selected:
            self.selectionChanged.emit(selected[0].data(0))
