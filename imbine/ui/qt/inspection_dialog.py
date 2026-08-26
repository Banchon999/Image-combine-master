"""Human-readable preflight report for destructive or suspicious exports."""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout


class InspectionDialog(QDialog):
    def __init__(self, report, extra_warnings=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Smart Check — ตรวจสอบก่อนส่งออก")
        self.resize(640, 390)
        warnings = list(report.warnings) + list(extra_warnings)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"ภาพที่ใช้ได้: {len(report.ok)}    ไฟล์เสีย: {len(report.broken)}"))
        details = QTextBrowser()
        details.setPlainText("\n\n".join(warnings) if warnings else
                             "✓ ตรวจสอบแล้ว ไม่พบความเสี่ยง")
        layout.addWidget(details)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("ดำเนินการต่อ")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
