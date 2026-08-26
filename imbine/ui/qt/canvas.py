"""Control-point editing state and an optional Qt alignment canvas.

The model is deliberately usable without Qt, which keeps transform interaction
testable and prevents the application core from acquiring a GUI dependency.
"""

from ...alignment.manual import estimate_transform
from ...alignment.models import ControlPointPair


class AlignmentCanvasModel:
    COLORS = ("#ef5350", "#42a5f5", "#66bb6a", "#ffa726",
              "#ab47bc", "#26c6da")

    def __init__(self):
        self.source_layer = None
        self.reference_layer = None
        self.control_points = []
        self.preview_transform = None

    def select_layers(self, source, reference):
        if source is reference:
            raise ValueError("source and reference layers must be different")
        self.source_layer, self.reference_layer = source, reference
        self.clear_preview()

    def add_pair(self, source, reference):
        pair = ControlPointPair(tuple(map(float, source)), tuple(map(float, reference)))
        self.control_points.append(pair)
        self.clear_preview()
        return len(self.control_points) - 1

    def move_point(self, index, side, position):
        pair = self.control_points[index]
        position = tuple(map(float, position))
        if side == "source":
            pair = ControlPointPair(position, pair.reference)
        elif side == "reference":
            pair = ControlPointPair(pair.source, position)
        else:
            raise ValueError("side must be source or reference")
        self.control_points[index] = pair
        self.clear_preview()

    def remove_pair(self, index):
        del self.control_points[index]
        self.clear_preview()

    def marker(self, index):
        """Return the matching, one-based label and color for both point views."""
        return str(index + 1), self.COLORS[index % len(self.COLORS)]

    def preview(self, kind="affine"):
        self.preview_transform = estimate_transform(self.control_points, kind)
        return self.preview_transform

    def confirm_preview(self):
        if self.preview_transform is None or self.source_layer is None:
            raise ValueError("there is no transform preview to confirm")
        self.source_layer.transform = self.preview_transform
        result = self.preview_transform
        self.preview_transform = None
        return result

    def clear_preview(self):
        self.preview_transform = None


try:  # Qt stays optional; imports are never hidden behind a broad exception.
    from PySide6.QtCore import QPointF, Qt, Signal
    from PySide6.QtGui import QColor, QPen
    from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsView
except ImportError:
    AlignmentCanvas = None
else:
    class AlignmentCanvas(QGraphicsView):
        """Qt view supporting numbered draggable control-point markers."""

        pointsChanged = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setScene(QGraphicsScene(self))
            self.model = AlignmentCanvasModel()
            self.setDragMode(QGraphicsView.ScrollHandDrag)

        def redraw_points(self):
            self.scene().clear()
            for index, pair in enumerate(self.model.control_points):
                label, color = self.model.marker(index)
                for point in (pair.source, pair.reference):
                    item = QGraphicsEllipseItem(-6, -6, 12, 12)
                    item.setPos(QPointF(*point))
                    item.setPen(QPen(QColor(color), 3))
                    item.setToolTip("Control point %s" % label)
                    item.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
                    item.setData(0, index)
                    self.scene().addItem(item)

        def mousePressEvent(self, event):
            if event.button() == Qt.RightButton:
                item = self.itemAt(event.position().toPoint())
                if item is not None and item.data(0) is not None:
                    self.model.remove_pair(item.data(0))
                    self.redraw_points()
                    self.pointsChanged.emit()
                    return
            super().mousePressEvent(event)
