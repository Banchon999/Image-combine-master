"""Qt frontend; โมดูลนอก :mod:`imbine.ui` จะต้องไม่ import แพ็กเกจนี้"""


def run():
    """สร้าง application และคืน exit code เมื่อ event loop จบ"""
    import sys

    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Imbine")
    window = MainWindow()
    window.show()
    return app.exec()


__all__ = ["run"]
