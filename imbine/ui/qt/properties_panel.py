"""Dockable image transformation properties."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
                               QGroupBox, QPushButton, QSpinBox, QVBoxLayout,
                               QWidget)


class PropertiesPanel(QWidget):
    properties_changed = Signal(dict)
    auto_align_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout()
        self.crop = QCheckBox("เปิดใช้ Crop")
        self.blend_mode = QComboBox()
        self.blend_mode.addItems(["Normal", "Multiply", "Screen", "Overlay"])
        self.auto_align = QPushButton("Auto-Align")
        self.rotate = QDoubleSpinBox()
        self.rotate.setRange(-360, 360)
        self.rotate.setSuffix("°")
        self.scale = QDoubleSpinBox()
        self.scale.setRange(1, 800)
        self.scale.setValue(100)
        self.scale.setSuffix("%")
        self.offset_x = QSpinBox()
        self.offset_y = QSpinBox()
        for control in (self.offset_x, self.offset_y):
            control.setRange(-100000, 100000)
            control.setSuffix(" px")
        form.addRow("Crop", self.crop)
        form.addRow("Blend Mode", self.blend_mode)
        form.addRow("Auto-Align", self.auto_align)
        form.addRow("Rotate", self.rotate)
        form.addRow("Scale", self.scale)
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        group = QGroupBox("คุณสมบัติ")
        group.setLayout(form)
        layout = QVBoxLayout(self)
        layout.addWidget(group)
        layout.addStretch()

        self.auto_align.clicked.connect(self.auto_align_requested)
        for signal in (self.crop.toggled, self.blend_mode.currentTextChanged,
                       self.rotate.valueChanged, self.scale.valueChanged,
                       self.offset_x.valueChanged, self.offset_y.valueChanged):
            signal.connect(self._emit_values)

    def values(self):
        return {"crop": self.crop.isChecked(), "blend_mode": self.blend_mode.currentText(),
                "rotate": self.rotate.value(), "scale": self.scale.value(),
                "offset_x": self.offset_x.value(), "offset_y": self.offset_y.value()}

    def _emit_values(self, *unused):
        self.properties_changed.emit(self.values())
