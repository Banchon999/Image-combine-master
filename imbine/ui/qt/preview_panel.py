# -*- coding: utf-8 -*-
"""
แท็บพรีวิวผลลัพธ์จริง

`build_default_pipeline(save=False)` มีอยู่แล้วและถูกออกแบบมาเพื่อการนี้พอดี
(คืนภาพในหน่วยความจำโดยไม่เขียนดิสก์) สิ่งที่ต้องเพิ่มคือทำให้มันไม่กินแรม
จนเครื่องอืด — เว็บตูนหนึ่งตอนต่อกันแล้วสูงสองหมื่นพิกเซลขึ้นไป ซึ่งจะถูก
ย่อลงเหลือไม่กี่ร้อยพิกเซลบนจออยู่ดี DownscaleStep จึงย่อตั้งแต่ก่อนต่อ
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from ...i18n import t

# งบพิกเซลของภาพพรีวิว — 12 ล้านพิกเซลคือราว 36 MB ในหน่วยความจำ ซึ่ง
# สร้างเสร็จในไม่กี่วินาทีและยังเห็นรายละเอียดพอตรวจว่าต่อถูกลำดับไหม
# ตอนสั้น ๆ ที่เล็กกว่างบนี้จะได้ความละเอียดเต็มไปเลย
PREVIEW_MAX_PIXELS = 12_000_000

# ด้านที่ยาวที่สุดที่ QPixmap รับไหว — Qt เก็บภาพที่ด้านเกิน 32767 px ไม่ได้
# ภาพที่ยาวกว่านี้ต้องย่อลงอีกก่อนวาด ไม่งั้นได้ภาพเปล่า
MAX_PIXMAP_AXIS = 30000


def pixmap_from_pil(image):
    """แปลง PIL.Image เป็น QPixmap โดยไม่ต้องเขียนไฟล์ชั่วคราว"""
    longest = max(image.width, image.height)
    if longest > MAX_PIXMAP_AXIS:
        ratio = MAX_PIXMAP_AXIS / longest
        image = image.resize((max(1, round(image.width * ratio)),
                              max(1, round(image.height * ratio))))
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimage = QImage(data, rgb.width, rgb.height, rgb.width * 3,
                    QImage.Format_RGB888)
    # copy() เพราะ QImage ไม่ได้ถือ buffer ไว้เอง ถ้าไม่ก๊อป data จะถูกเก็บกวาด
    # แล้วภาพกลายเป็นขยะ
    return QPixmap.fromImage(qimage.copy())


class PreviewPanel(QWidget):
    """แสดงผลลัพธ์ที่ต่อแล้วจริง ๆ ทีละไฟล์"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = []
        self._index = 0

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.build_button = QPushButton()
        self.build_button.setProperty("accent", True)
        self.previous = QPushButton("‹")
        self.next = QPushButton("›")
        self.position = QLabel()
        controls.addWidget(self.build_button)
        controls.addStretch(1)
        controls.addWidget(self.previous)
        controls.addWidget(self.position)
        controls.addWidget(self.next)
        layout.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.image)
        layout.addWidget(self.scroll, 1)

        self.note = QLabel()
        self.note.setProperty("hint", True)
        self.note.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.note)

        self.previous.clicked.connect(lambda: self.show_part(self._index - 1))
        self.next.clicked.connect(lambda: self.show_part(self._index + 1))

        self.retranslate()
        self.clear()

    def clear(self):
        self._results = []
        self._index = 0
        self.image.setPixmap(QPixmap())
        self.image.setText(t("ui.preview.empty"))
        self._sync_controls()

    def set_working(self):
        self.image.setPixmap(QPixmap())
        self.image.setText(t("ui.preview.working"))

    def set_results(self, results):
        self._results = list(results)
        self._index = 0
        if not self._results:
            self.clear()
            return
        self.show_part(0)

    def show_part(self, index):
        if not self._results:
            return
        self._index = max(0, min(len(self._results) - 1, index))
        self.image.setText("")
        self.image.setPixmap(pixmap_from_pil(self._results[self._index]))
        self._sync_controls()

    def _sync_controls(self):
        has = bool(self._results)
        many = len(self._results) > 1
        self.previous.setVisible(many)
        self.next.setVisible(many)
        self.position.setVisible(has)
        self.previous.setEnabled(self._index > 0)
        self.next.setEnabled(self._index < len(self._results) - 1)
        self.note.setVisible(has)
        if has:
            self.position.setText(t("ui.preview.part", index=self._index + 1,
                                    total=len(self._results)))

    def retranslate(self):
        self.build_button.setText(t("ui.preview.build"))
        self.note.setText(t("ui.preview.scaled"))
        if not self._results:
            self.image.setText(t("ui.preview.empty"))
        else:
            self._sync_controls()
