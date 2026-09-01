# -*- coding: utf-8 -*-
"""รายงานผลตรวจก่อนส่งออก — รายงาน ไม่ตัดสินใจแทนผู้ใช้"""

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QTextBrowser,
                               QVBoxLayout)

from ...i18n import t


class InspectionDialog(QDialog):
    def __init__(self, report, extra_warnings=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("ui.check.title"))
        self.resize(660, 400)

        warnings = list(report.warnings) + list(extra_warnings)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t("ui.check.summary", ok=len(report.ok),
                                  broken=len(report.broken))))

        details = QTextBrowser()
        details.setPlainText("\n\n".join(str(w) for w in warnings)
                             if warnings else t("ui.check.clean"))
        layout.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(t("ui.check.continue"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("ui.check.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
