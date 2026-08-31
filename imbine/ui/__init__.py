# -*- coding: utf-8 -*-
"""
ส่วนติดต่อผู้ใช้

จงใจไม่ import อะไรที่ระดับโมดูลนี้ — การ import imbine.ui ต้องไม่ลาก PySide6
เข้ามา เพื่อให้ `import imbine` ยังทำงานได้บนเครื่องที่ไม่มี Qt หรือไม่มีจอ
(เช่นเครื่องรันเทสต์) ใครจะใช้ UI ให้ import imbine.ui.qt.main_window ตรง ๆ

imbine.ui.document เป็นข้อยกเว้นที่ import ได้เสมอ — มันคือโมเดลเอกสารล้วน ๆ
ที่ไม่ผูกกับ toolkit ใด
"""
