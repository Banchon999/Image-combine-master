# -*- coding: utf-8 -*-
"""จุดเริ่มโปรแกรม:  python -m imbine"""

import sys


def main():
    try:
        from .ui.qt.main_window import main as run_app
    except ImportError as e:
        sys.exit(
            f"เปิด Qt workspace ไม่ได้: {e}\n\n"
            "ติดตั้งส่วนติดต่อ Qt ด้วยคำสั่ง:\n  pip install 'imbine[qt]'"
        )
    run_app()


if __name__ == "__main__":
    main()
