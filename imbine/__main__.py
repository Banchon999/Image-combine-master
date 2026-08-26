# -*- coding: utf-8 -*-
"""จุดเริ่มโปรแกรม:  python -m imbine"""

import sys


def main():
    try:
        from .ui.tk_app import main as run_app
    except ImportError as e:
        # tkinter ไม่ได้มากับ Python ทุกชุด (บน Linux ต้องลงแยก) —
        # บอกวิธีแก้ไปเลย ดีกว่าโยน traceback ดิบใส่หน้าผู้ใช้
        sys.exit(
            f"เปิดหน้าต่างโปรแกรมไม่ได้: {e}\n\n"
            "ถ้าเป็นเพราะไม่มี tkinter ให้ติดตั้งก่อน:\n"
            "  Debian/Ubuntu : sudo apt install python3-tk\n"
            "  Fedora        : sudo dnf install python3-tkinter\n"
            "  Windows/macOS : ติดตั้ง Python จาก python.org (มี tkinter มาให้)"
        )
    run_app()


if __name__ == "__main__":
    main()
