# -*- coding: utf-8 -*-
"""
แผงตั้งค่าการต่อภาพ

เดิมคอนโทรลทั้งหมดถูกยัดใน QFormLayout แถวเดียวกัน 14 แถว ไม่มีหัวข้อ ไม่มี
คำอธิบาย และมีคอนโทรลที่ไม่มีผลกับไฟล์ผลลัพธ์ (Blend mode / Rotate / Scale /
Offset) ปนอยู่กับคอนโทรลจริง — คนใช้แยกไม่ออกว่าอันไหนทำอะไร

ที่นี่จัดใหม่เป็นกลุ่มตามลำดับที่คนคิดจริง ๆ เวลาต่อภาพ: ต่อไปทางไหน ->
แบ่งกี่ไฟล์ -> เอาไฟล์แบบไหน -> ตั้งชื่อว่าอะไร -> จะแต่งอะไรเพิ่มไหม
และคอนโทรลที่ไม่มีผลถูกถอดออกทั้งหมด
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFormLayout,
                               QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QRadioButton,
                               QScrollArea, QSlider, QSpinBox, QVBoxLayout,
                               QWidget)

from ...config import StitchConfig
from ...formats import capabilities
from ...i18n import t
from ...naming import build_output_name, ext_for
from ...watermark import ANCHORS, DEFAULT_ANCHOR
from ..qt_export import populate_export_formats

# โทเคนที่ใส่ในชื่อไฟล์ได้ — ปุ่มกดแทรกสร้างจากรายการนี้
NAME_TOKENS = ("{n}", "{n2}", "{n3}", "{folder}", "{total}")

# ตำแหน่งลายน้ำ เรียงแบบเดียวกับที่ตาเห็นบนภาพ (บน -> ล่าง, ซ้าย -> ขวา)
WATERMARK_POSITIONS = (
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
)


def hint(text=""):
    """ป้ายคำอธิบายตัวเล็กสีจาง ใต้คอนโทรลที่ต้องอธิบายเพิ่ม"""
    label = QLabel(text)
    label.setProperty("hint", True)
    label.setWordWrap(True)
    return label


class SettingsPanel(QWidget):
    """แผงตั้งค่าทั้งหมด — คุยกับข้างนอกด้วย StitchConfig เท่านั้น"""

    configChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False       # กัน signal ตีกลับตอนโหลดค่าเข้าคอนโทรล

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        body = QWidget()
        self._layout = QVBoxLayout(body)
        self._layout.setSpacing(12)
        scroll.setWidget(body)

        self._build_direction()
        self._build_split()
        self._build_output()
        self._build_naming()
        self._build_extras()
        self._build_presets()
        self._layout.addStretch(1)

        self._connect()
        self.retranslate()
        self._sync_enabled()

    # -- กลุ่มคอนโทรล ------------------------------------------------

    def _group(self, attr):
        box = QGroupBox()
        setattr(self, attr, box)
        self._layout.addWidget(box)
        return box

    def _build_direction(self):
        box = self._group("box_direction")
        layout = QVBoxLayout(box)
        self.vertical = QRadioButton()
        self.horizontal = QRadioButton()
        self.vertical.setChecked(True)
        self.direction_group = QButtonGroup(self)
        self.direction_group.addButton(self.vertical, 0)
        self.direction_group.addButton(self.horizontal, 1)
        layout.addWidget(self.vertical)
        layout.addWidget(self.horizontal)
        self.direction_hint = hint()
        layout.addWidget(self.direction_hint)

    def _build_split(self):
        """
        แยกโหมดแบ่งไฟล์เป็น radio เพราะเดิมทั้งสองช่องกรอกได้พร้อมกัน
        แต่ max_size ชนะ parts_count เงียบ ๆ (grouping.py) ผู้ใช้ที่กรอกทั้งคู่
        จะไม่มีทางรู้เลยว่าทำไมได้จำนวนไฟล์ไม่ตรงที่ขอ
        """
        box = self._group("box_split")
        layout = QVBoxLayout(box)

        self.by_parts = QRadioButton()
        self.by_parts.setChecked(True)
        self.by_size = QRadioButton()
        self.split_group = QButtonGroup(self)
        self.split_group.addButton(self.by_parts, 0)
        self.split_group.addButton(self.by_size, 1)

        self.parts = QSpinBox()
        self.parts.setRange(1, 999)
        self.parts.setValue(1)

        self.max_size = QSpinBox()
        self.max_size.setRange(1, 1000000)
        self.max_size.setValue(20000)
        self.max_size.setSingleStep(1000)
        self.max_size.setSuffix(" px")

        grid = QGridLayout()
        grid.addWidget(self.by_parts, 0, 0)
        grid.addWidget(self.parts, 0, 1)
        grid.addWidget(self.by_size, 1, 0)
        grid.addWidget(self.max_size, 1, 1)
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)
        self.split_hint = hint()
        layout.addWidget(self.split_hint)

    def _build_output(self):
        box = self._group("box_output")
        form = QFormLayout(box)

        self.formats = QComboBox()
        populate_export_formats(self.formats)

        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(92)

        self.uniform = QCheckBox()
        self.uniform.setChecked(True)
        self.overwrite = QCheckBox()

        self.label_format = QLabel()
        self.label_quality = QLabel()
        form.addRow(self.label_format, self.formats)
        form.addRow(self.label_quality, self.quality)
        form.addRow("", self.uniform)
        form.addRow("", self.overwrite)
        self.output_hint = hint()
        form.addRow(self.output_hint)

    def _build_naming(self):
        box = self._group("box_naming")
        layout = QVBoxLayout(box)

        self.pattern = QLineEdit("{folder}_{n3}")
        layout.addWidget(self.pattern)

        # ปุ่มกดแทรกโทเคน — เดิมผู้ใช้ต้องจำเองว่าพิมพ์อะไรได้บ้าง
        self.token_row = QHBoxLayout()
        self.token_buttons = []
        for token in NAME_TOKENS:
            button = QPushButton(token)
            button.setFlat(True)
            button.clicked.connect(
                lambda _=False, value=token: self._insert_token(value))
            self.token_row.addWidget(button)
            self.token_buttons.append(button)
        self.token_row.addStretch(1)
        layout.addLayout(self.token_row)

        self.name_preview = QLabel()
        self.name_preview.setProperty("hint", True)
        self.name_preview.setWordWrap(True)
        layout.addWidget(self.name_preview)

    def _build_extras(self):
        box = self._group("box_extras")
        layout = QVBoxLayout(box)

        self.trim_borders = QCheckBox()
        self.dedupe_overlap = QCheckBox()
        layout.addWidget(self.trim_borders)
        layout.addWidget(self.dedupe_overlap)
        self.trim_hint = hint()
        layout.addWidget(self.trim_hint)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        self.watermark_on = QCheckBox()
        layout.addWidget(self.watermark_on)

        self.watermark_text = QLineEdit()
        self.watermark_position = QComboBox()
        for key in WATERMARK_POSITIONS:
            self.watermark_position.addItem("", key)
        self.watermark_position.setCurrentIndex(
            WATERMARK_POSITIONS.index(DEFAULT_ANCHOR))
        self.watermark_opacity = QSlider(Qt.Horizontal)
        self.watermark_opacity.setRange(5, 100)
        self.watermark_opacity.setValue(50)
        self.watermark_opacity_value = QLabel("50%")

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.watermark_opacity, 1)
        opacity_row.addWidget(self.watermark_opacity_value)

        self.watermark_form = QFormLayout()
        self.label_wm_text = QLabel()
        self.label_wm_position = QLabel()
        self.label_wm_opacity = QLabel()
        self.watermark_form.addRow(self.label_wm_text, self.watermark_text)
        self.watermark_form.addRow(self.label_wm_position, self.watermark_position)
        self.watermark_form.addRow(self.label_wm_opacity, opacity_row)
        layout.addLayout(self.watermark_form)

    def _build_presets(self):
        box = self._group("box_presets")
        layout = QVBoxLayout(box)
        self.presets = QComboBox()
        self.presets.setEditable(True)
        layout.addWidget(self.presets)
        row = QHBoxLayout()
        self.preset_save = QPushButton()
        self.preset_delete = QPushButton()
        row.addWidget(self.preset_save)
        row.addWidget(self.preset_delete)
        layout.addLayout(row)
        self.preset_hint = hint()
        layout.addWidget(self.preset_hint)

    # -- การเชื่อมสัญญาณ ----------------------------------------------

    def _connect(self):
        for widget in (self.vertical, self.horizontal, self.by_parts,
                       self.by_size, self.uniform, self.overwrite,
                       self.trim_borders, self.dedupe_overlap,
                       self.watermark_on):
            widget.toggled.connect(self._changed)
        for widget in (self.parts, self.max_size, self.quality):
            widget.valueChanged.connect(self._changed)
        self.formats.currentTextChanged.connect(self._changed)
        self.pattern.textChanged.connect(self._changed)
        self.watermark_text.textChanged.connect(self._changed)
        self.watermark_position.currentIndexChanged.connect(self._changed)
        self.watermark_opacity.valueChanged.connect(self._changed)

    def _changed(self, *args):
        if self._loading:
            return
        self._sync_enabled()
        self.configChanged.emit()

    def _sync_enabled(self):
        """เปิด/ปิดคอนโทรลตามโหมดที่เลือก — คอนโทรลที่ไม่มีผลต้องดูไม่มีผลด้วย"""
        self.parts.setEnabled(self.by_parts.isChecked())
        self.max_size.setEnabled(self.by_size.isChecked())

        caps = capabilities(self.formats.currentText())
        supports_quality = bool(caps and caps.quality)
        self.quality.setVisible(supports_quality)
        self.label_quality.setVisible(supports_quality)

        on = self.watermark_on.isChecked()
        for widget in (self.watermark_text, self.watermark_position,
                       self.watermark_opacity, self.watermark_opacity_value,
                       self.label_wm_text, self.label_wm_position,
                       self.label_wm_opacity):
            widget.setEnabled(on)

        self.watermark_opacity_value.setText(f"{self.watermark_opacity.value()}%")
        self._update_name_preview()

    def _insert_token(self, token):
        self.pattern.insert(token)
        self.pattern.setFocus()

    def _update_name_preview(self):
        count = self.parts.value() if self.by_parts.isChecked() else 3
        names = [build_output_name(self.pattern.text(), i, count,
                                   t("ui.naming.sample_folder"))
                 + ext_for(self.formats.currentText())
                 for i in range(1, min(3, max(1, count)) + 1)]
        more = " …" if count > 3 else ""
        self.name_preview.setText(t("ui.naming.preview",
                                    names=", ".join(names) + more))

    # -- แปลงเป็น/จาก StitchConfig -------------------------------------

    def to_config(self, **overrides):
        """อ่านค่าจากคอนโทรลทั้งหมดออกมาเป็น StitchConfig"""
        values = dict(
            orientation="vertical" if self.vertical.isChecked() else "horizontal",
            fmt=self.formats.currentText(),
            quality=self.quality.value(),
            parts_count=self.parts.value() if self.by_parts.isChecked() else 1,
            max_size=self.max_size.value() if self.by_size.isChecked() else 0,
            uniform=self.uniform.isChecked(),
            overwrite=self.overwrite.isChecked(),
            name_pattern=self.pattern.text(),
            trim_borders=self.trim_borders.isChecked(),
            dedupe_overlap=self.dedupe_overlap.isChecked(),
            watermark=self._watermark_spec(),
        )
        values.update(overrides)
        return StitchConfig(**values)

    def _watermark_spec(self):
        if not self.watermark_on.isChecked():
            return {}
        return {
            "enabled": True,
            "text": self.watermark_text.text(),
            "position": self.watermark_position.currentData() or DEFAULT_ANCHOR,
            "opacity": self.watermark_opacity.value() / 100.0,
        }

    def apply_config(self, config):
        """ตั้งคอนโทรลทั้งหมดตาม StitchConfig (ใช้ตอนโหลดพรีเซ็ต)"""
        self._loading = True
        try:
            self.vertical.setChecked(config.vertical)
            self.horizontal.setChecked(not config.vertical)

            index = self.formats.findText(config.fmt)
            if index < 0 and config.fmt == "JPG":
                index = self.formats.findText("JPEG")
            if index >= 0:
                self.formats.setCurrentIndex(index)

            self.quality.setValue(config.quality)
            self.uniform.setChecked(config.uniform)
            self.overwrite.setChecked(config.overwrite)
            self.pattern.setText(config.name_pattern)

            if config.max_size > 0:
                self.by_size.setChecked(True)
                self.max_size.setValue(config.max_size)
            else:
                self.by_parts.setChecked(True)
                self.parts.setValue(config.parts_count)

            self.trim_borders.setChecked(config.trim_borders)
            self.dedupe_overlap.setChecked(config.dedupe_overlap)

            spec = config.watermark or {}
            self.watermark_on.setChecked(bool(spec.get("enabled")))
            self.watermark_text.setText(str(spec.get("text", "")))
            position = self.watermark_position.findData(
                spec.get("position", DEFAULT_ANCHOR))
            if position >= 0:
                self.watermark_position.setCurrentIndex(position)
            self.watermark_opacity.setValue(
                round(float(spec.get("opacity", 0.5)) * 100))
        finally:
            self._loading = False
        self._sync_enabled()
        self.configChanged.emit()

    def set_preset_names(self, names, current=""):
        self._loading = True
        try:
            self.presets.clear()
            self.presets.addItems(list(names))
            self.presets.setCurrentText(current)
        finally:
            self._loading = False

    # -- ภาษา ---------------------------------------------------------

    def retranslate(self):
        """ตั้งข้อความใหม่ทั้งแผง — เรียกซ้ำได้ทุกครั้งที่ผู้ใช้สลับภาษา"""
        self.box_direction.setTitle(t("ui.group.direction"))
        self.vertical.setText(t("ui.direction.vertical"))
        self.horizontal.setText(t("ui.direction.horizontal"))
        self.direction_hint.setText(t("ui.direction.hint"))

        self.box_split.setTitle(t("ui.group.split"))
        self.by_parts.setText(t("ui.split.by_parts"))
        self.by_size.setText(t("ui.split.by_size"))
        self.split_hint.setText(t("ui.split.hint"))

        self.box_output.setTitle(t("ui.group.output"))
        self.label_format.setText(t("ui.output.format"))
        self.label_quality.setText(t("ui.output.quality"))
        self.uniform.setText(t("ui.output.uniform"))
        self.overwrite.setText(t("ui.output.overwrite"))
        self.output_hint.setText(t("ui.output.hint"))

        self.box_naming.setTitle(t("ui.group.naming"))
        self.pattern.setPlaceholderText(t("ui.naming.placeholder"))

        self.box_extras.setTitle(t("ui.group.extras"))
        self.trim_borders.setText(t("ui.extras.trim_borders"))
        self.dedupe_overlap.setText(t("ui.extras.dedupe"))
        self.trim_hint.setText(t("ui.extras.trim_hint"))
        self.watermark_on.setText(t("ui.extras.watermark"))
        self.label_wm_text.setText(t("ui.extras.watermark_text"))
        self.label_wm_position.setText(t("ui.extras.watermark_position"))
        self.label_wm_opacity.setText(t("ui.extras.watermark_opacity"))
        for index, key in enumerate(WATERMARK_POSITIONS):
            self.watermark_position.setItemText(index, t(f"ui.anchor.{key}"))

        self.box_presets.setTitle(t("ui.group.presets"))
        self.preset_save.setText(t("ui.presets.save"))
        self.preset_delete.setText(t("ui.presets.delete"))
        self.preset_hint.setText(t("ui.presets.hint"))
        self.presets.lineEdit().setPlaceholderText(t("ui.presets.placeholder"))

        self._retranslate_tooltips()
        self._update_name_preview()

    def _retranslate_tooltips(self):
        tips = {
            self.uniform: "ui.tip.uniform",
            self.overwrite: "ui.tip.overwrite",
            self.quality: "ui.tip.quality",
            self.parts: "ui.tip.parts",
            self.max_size: "ui.tip.max_size",
            self.pattern: "ui.tip.pattern",
            self.trim_borders: "ui.tip.trim_borders",
            self.dedupe_overlap: "ui.tip.dedupe",
            self.watermark_on: "ui.tip.watermark",
            self.presets: "ui.tip.presets",
        }
        for widget, key in tips.items():
            widget.setToolTip(t(key))
        for button in self.token_buttons:
            button.setToolTip(t(f"ui.token.{button.text().strip('{}')}"))
