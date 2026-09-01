# -*- coding: utf-8 -*-
"""
แถบสรุปผลลัพธ์ที่อัปเดตตลอดเวลา

ตอบคำถามที่ผู้ใช้ต้องเดาเองมาตลอดว่า "กด Export แล้วจะได้อะไร" โดยไม่ต้อง
กดอะไรเลย — จะได้กี่ไฟล์ ไฟล์ละกี่พิกเซล ประมาณกี่ MB และที่สำคัญที่สุดคือ
เตือนตั้งแต่ตอนนี้ถ้าขนาดจะเกินลิมิตของ format ที่เลือก แทนที่จะไปพังตอนบันทึก

การคำนวณอ่านแค่ส่วนหัวไฟล์ (imbine.estimate) จึงเรียกซ้ำได้ถี่ ๆ แต่ก็ยัง
หน่วงไว้เล็กน้อยเพื่อไม่ให้คำนวณใหม่ทุกครั้งที่ผู้ใช้กดลูกศรขึ้นลงบน spinbox
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...estimate import human_bytes, plan_output, probe_sizes
from ...i18n import t

# หน่วงก่อนคำนวณใหม่ — สั้นพอที่จะรู้สึกว่าตอบทันที ยาวพอที่จะไม่คำนวณ
# ซ้ำทุกครั้งที่ผู้ใช้กดลูกศรรัว ๆ
DEBOUNCE_MS = 200


class SummaryBar(QWidget):
    """แถบเดียวใต้ toolbar ที่บอกว่าจะได้ผลลัพธ์อะไร"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths = []
        self._sizes = []            # จำขนาดไว้ ไม่ต้องอ่านไฟล์ซ้ำตอนแก้ค่าตั้ง
        self._config_source = None  # callable ที่คืน StitchConfig ปัจจุบัน

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        row = QHBoxLayout()
        self.summary = QLabel()
        row.addWidget(self.summary, 1)
        layout.addLayout(row)

        self.warning = QLabel()
        self.warning.setProperty("warning", True)
        self.warning.setWordWrap(True)
        self.warning.hide()
        layout.addWidget(self.warning)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(self._recalculate)

        self.retranslate()

    def set_config_source(self, source):
        """บอกว่าจะไปอ่าน StitchConfig ปัจจุบันได้จากไหน"""
        self._config_source = source

    def set_paths(self, paths):
        """เปลี่ยนชุดภาพ — ต้องอ่านขนาดใหม่"""
        self._paths = list(paths)
        self._sizes = None
        self.schedule()

    def schedule(self):
        """ขอให้คำนวณใหม่ (หน่วงไว้ก่อน) — เรียกได้ถี่เท่าไหร่ก็ได้"""
        self._timer.start()

    def plan_now(self, config):
        """
        คำนวณทันทีโดยไม่รอ debounce — คืน OutputPlan หรือ None

        ใช้ตอนกด Export เพื่อเอาคำเตือนเรื่องลิมิตของ format ไปรวมในกล่อง
        ยืนยัน จะได้ไม่ต้องคำนวณซ้ำและได้คำตอบที่ตรงกับที่ผู้ใช้เห็นบนแถบ
        """
        if not self._paths:
            return None
        if self._sizes is None:
            self._sizes = probe_sizes(self._paths)
        try:
            return plan_output(self._sizes, config)
        except ValueError:
            return None

    def _recalculate(self):
        if not self._paths or self._config_source is None:
            self.summary.setText(t("ui.summary.empty"))
            self.warning.hide()
            return

        if self._sizes is None:
            self._sizes = probe_sizes(self._paths)

        try:
            plan = plan_output(self._sizes, self._config_source())
        except ValueError:
            # ค่าตั้งยังไม่สมเหตุสมผล (เช่นระหว่างที่ผู้ใช้กำลังพิมพ์)
            # ไม่ใช่เรื่องที่ต้องรายงาน แค่ยังบอกอะไรไม่ได้
            self.summary.setText(t("ui.summary.empty"))
            self.warning.hide()
            return

        self.summary.setText(self._describe(plan))
        if plan.warnings:
            self.warning.setText("\n".join(str(w) for w in plan.warnings))
            self.warning.show()
        else:
            self.warning.hide()

    def _describe(self, plan):
        if not plan:
            return t("ui.summary.empty")
        size = human_bytes(plan.total_bytes)
        # บอกขนาดต่อไฟล์ได้ก็ต่อเมื่อทุกไฟล์ขนาดเท่ากัน ไม่งั้นเลขจะโกหก
        if len(set(plan.parts)) == 1:
            width, height = plan.parts[0]
            return t("ui.summary.plan", images=plan.source_count,
                     parts=plan.part_count, width=width, height=height,
                     size=size)
        return t("ui.summary.plan_varied", images=plan.source_count,
                 parts=plan.part_count, size=size)

    def retranslate(self):
        self._recalculate()
