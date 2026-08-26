# -*- coding: utf-8 -*-
"""จุดเริ่มโปรแกรม:  python -m imbine"""

def main():
    """เปิด Qt frontend หลักของโปรแกรม"""
    try:
        # Qt ต้องถูก import เฉพาะใน entry point/UI เท่านั้น เพื่อให้ imbine
        # ยังคงใช้เป็นไลบรารีบนเครื่องแบบ headless ได้
        from .ui.qt import run
    except ImportError as e:
        raise SystemExit(
            f"เปิดหน้าต่างโปรแกรมไม่ได้: {e}\n\n"
            "ติดตั้ง Qt binding ด้วยคำสั่ง: pip install PySide6"
        )
    return run()


if __name__ == "__main__":
    main()
