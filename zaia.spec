# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=[('zaia/geo_th.json', 'zaia'), ('assets', 'assets')],
    hiddenimports=['win32ui', 'win32print', 'win32gui', 'win32con', 'PIL._tkinter_finder', 'lxml.etree'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZAIA Prepare Personal', console=False, icon='assets/logo.ico')
coll = COLLECT(exe, a.binaries, a.datas, name='ZAIA Prepare Personal')
