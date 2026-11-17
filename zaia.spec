# -*- mode: python ; coding: utf-8 -*-
# โค้ด zaia ไม่ถูกคอมไพล์รวมใน exe แต่แนบเป็นไฟล์ .py (src/) เพื่อให้อัปเดตออนไลน์แบบแพตช์ได้ (ดู app.py / updater.py)
import ast
import glob
from PyInstaller.utils.hooks import collect_submodules

mods = set()
for f in glob.glob('zaia/*.py'):
    for n in ast.walk(ast.parse(open(f, encoding='utf-8').read())):
        if isinstance(n, ast.Import):
            mods.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            mods.add(n.module)
hidden = sorted({m for m in mods if m.split('.')[0] != 'zaia'} | {
    'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.font',
    'PIL._tkinter_finder', 'lxml._elementpath', 'win32api', 'win32ui', 'win32print', 'win32gui', 'win32con',
    'ctypes', 'glob', 'zipfile', 'urllib.request', 'urllib.parse', 'hashlib', 'queue', 'threading'})
for pkg in ('openpyxl', 'PIL', 'pyxlsb', 'lxml'):
    hidden += collect_submodules(pkg)

a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=[('zaia/*.py', 'src/zaia'), ('zaia/geo_th.json', 'src/zaia'), ('assets', 'src/assets')],
    hiddenimports=hidden,
    excludes=['zaia'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZAIA Prepare Personal', console=False, icon='assets/logo.ico')
coll = COLLECT(exe, a.binaries, a.datas, name='ZAIA Prepare Personal')
