# -*- mode: python ; coding: utf-8 -*-
"""
สูตรแพ็ก Imbine เป็นโปรแกรมรันได้บน Windows ด้วย PyInstaller

    pip install . pyinstaller
    pyinstaller imbine.spec

ได้ผลลัพธ์ที่ dist/Imbine/ — โฟลเดอร์เดียวที่ก๊อปไปเครื่องไหนก็รันได้
โดยไม่ต้องติดตั้ง Python

**ทำไมเป็น onedir ไม่ใช่ onefile:** onefile ต้องคลายไฟล์ทั้งชุด (PySide6
อย่างเดียวก็ร้อยกว่าเมกะไบต์) ลงโฟลเดอร์ชั่วคราวใหม่ *ทุกครั้งที่เปิด* ทำให้
รอห้าถึงสิบห้าวินาทีก่อนหน้าต่างจะขึ้น และพฤติกรรมคลายไฟล์ลง temp แล้วรัน
คือสิ่งที่โปรแกรมป้องกันไวรัสจับผิดบ่อยที่สุด onedir เปิดแทบจะทันทีและ
ถูกบีบเป็น .zip ก่อนแนบ Release อยู่แล้ว ผู้ใช้จึงโหลดไฟล์เดียวเหมือนกัน
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ไฟล์ที่ต้องไปด้วย — คำแปล ไอคอน และฟอนต์ไทยสำหรับลายน้ำ
datas = [
    ("imbine/locales", "imbine/locales"),
    ("assets/icons", "assets/icons"),
    ("assets/fonts", "assets/fonts"),
    ("assets/icon.ico", "assets"),
]

# ตัดของที่ไม่ได้ใช้ออก ไม่งั้น PySide6 ลากมาทั้งชุดจนไฟล์บวมเป็นหลาย GB
excludes = [
    # tkinter ไม่ถูกใช้แล้วตั้งแต่ย้ายมา Qt แต่ PyInstaller ยังชอบเก็บมาให้
    "tkinter", "_tkinter", "Tkinter",
    # โมดูล Qt ที่โปรแกรมนี้ไม่ได้แตะเลย (QtWebEngine ตัวเดียวก็ร่วม 300 MB)
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPositioning", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtSerialPort", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSpatialAudio", "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech", "PySide6.QtUiTools", "PySide6.QtNetworkAuth",
    # การจัดลำดับภาพอัตโนมัติเป็น extra ที่ต้องลงเพิ่มเอง ไม่ได้แถมมากับ .exe
    "cv2", "numpy", "scipy", "matplotlib", "pandas",
    # ของสำหรับนักพัฒนา
    "pytest", "setuptools", "pip", "IPython",
]

a = Analysis(
    ["imbine/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    # steps ถูกประกอบแบบไล่ import ในแพ็กเกจ PyInstaller จึงตามเจอครบอยู่แล้ว
    # แต่ระบุไว้ชัด ๆ กันขั้นที่ถูกเพิ่มทีหลังหลุด
    hiddenimports=collect_submodules("imbine.steps"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Imbine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX ทำให้โดน antivirus จับผิดบ่อยกว่าที่ประหยัดได้
    console=False,      # เป็นโปรแกรมหน้าต่าง ไม่ต้องมี console ดำ ๆ โผล่มา
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Imbine",
)
