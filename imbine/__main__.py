# -*- coding: utf-8 -*-
"""จุดเริ่มโปรแกรม:  python -m imbine"""

import sys


def main():
    """
    เปิดหน้าต่างโปรแกรม

    ใช้ import แบบเต็ม (imbine.ui...) ไม่ใช่ import สัมพัทธ์ (.ui...) เพราะ
    ไฟล์นี้ถูกใช้เป็น "สคริปต์ตั้งต้น" ตอนแพ็กด้วย PyInstaller ด้วย ตอนนั้น
    มันถูกรันในฐานะ __main__ ที่ไม่มีแพ็กเกจแม่ import สัมพัทธ์จึงพังทันที
    และ PyInstaller ก็จะตามหา PySide6 ไม่เจอ แล้วสร้างไฟล์ที่เปิดไม่ได้ออกมา
    """
    try:
        from imbine.ui.qt.main_window import main as run_app
    except ImportError as error:
        # แยกให้ออกระหว่าง "ไม่ได้ติดตั้ง Qt" กับ "โค้ดพัง" — เดิมดักรวมกัน
        # แล้วบอกให้ไปติดตั้ง Qt ซึ่งพาไปผิดทางเมื่อสาเหตุจริงเป็นอย่างอื่น
        if (error.name or "").split(".")[0] != "PySide6":
            raise
        sys.exit(
            f"เปิดหน้าต่างโปรแกรมไม่ได้: {error}\n\n"
            "ติดตั้งส่วนติดต่อผู้ใช้ด้วยคำสั่ง:\n"
            "  pip install 'imbine[qt]'"
        )
    return run_app()


if __name__ == "__main__":
    sys.exit(main() or 0)
