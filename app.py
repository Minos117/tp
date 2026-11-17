"""ตัวเปิดโปรแกรม: โหลดโค้ด zaia จากโฟลเดอร์แพตช์ (อัปเดตออนไลน์) ถ้ามีและใหม่กว่า ไม่เช่นนั้นใช้โค้ดที่มากับตัวติดตั้ง
ถ้าโค้ดแพตช์เปิดไม่ได้ จะปิดแพตช์และถอยไปใช้โค้ดเดิมอัตโนมัติ"""
import importlib
import json
import os
import re
import sys


def _vt(v):
    return tuple(int("".join(c for c in x if c.isdigit()) or 0) for x in str(v).split("."))


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "src")
    return os.path.dirname(os.path.abspath(__file__))


def _patch_dir():
    return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"), "ZAIA Prepare Personal", "patch")


def _base_ver(base):
    try:
        s = open(os.path.join(base, "zaia", "version.py"), encoding="utf-8").read()
        return re.search(r'^APP_VER\s*=\s*"([^"]+)"', s, re.M).group(1)
    except Exception:
        return "0"


def _use_patch(base, patch):
    try:
        with open(os.path.join(patch, "patch.json"), encoding="utf-8") as f:
            meta = json.load(f)
        return _vt(meta["version"]) > _vt(_base_ver(base)) and os.path.isfile(os.path.join(patch, "zaia", "ui.py"))
    except Exception:
        return False


def _load(root):
    for k in [k for k in sys.modules if k == "zaia" or k.startswith("zaia.")]:
        del sys.modules[k]
    sys.path[:] = [root] + [p for p in sys.path if p not in (root,)]
    return importlib.import_module("za" + "ia.ui")      # ไม่ให้ PyInstaller รวมโค้ด zaia เข้า exe (โหลดจากไฟล์ .py เพื่ออัปเดตได้)


def run():
    base, patch = _base_dir(), _patch_dir()
    ui = None
    if _use_patch(base, patch):
        try:
            ui = _load(patch)
        except Exception:
            try:
                os.replace(os.path.join(patch, "patch.json"), os.path.join(patch, "patch.bad.json"))
            except OSError:
                pass
    if ui is None:
        ui = _load(base)
    ui.main()


if __name__ == "__main__":
    run()
