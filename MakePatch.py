r"""สร้างส่วน "patch" ใน update.json จากซอร์ส (zaia\*.py, geo_th.json, assets\*) -- ไม่ต้อง build exe
ใช้: python MakePatch.py [path ของ update.json เดิม]   แล้วอัป update.json + ซอร์สขึ้น GitHub (ไฟล์ซอร์สที่ราก repo คือไฟล์ที่ดาวน์โหลด)
รุ่นแพตช์ = APP_VER ใน zaia\version.py; เครื่องที่ติดตั้งรุ่นต่ำกว่าจะเห็นแพตช์ในหน้า ตรวจสอบอัปเดต"""
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    src = open(os.path.join(ROOT, "zaia", "version.py"), encoding="utf-8").read()
    ver = re.search(r'^APP_VER\s*=\s*"([^"]+)"', src, re.M).group(1)
    rev = int(re.search(r"^SETUP_REV\s*=\s*(\d+)", src, re.M).group(1))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "update.json")
    try:
        m = json.load(open(out, encoding="utf-8"))
    except Exception:
        m = {"files": []}
    paths = sorted(glob.glob(os.path.join(ROOT, "zaia", "*.py")) + [os.path.join(ROOT, "zaia", "geo_th.json"), os.path.join(ROOT, "zaia", "zip_th.json")]
                   + glob.glob(os.path.join(ROOT, "assets", "*")))
    files = []
    for p in paths:
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        data = open(p, "rb").read()
        files.append({"path": rel, "url": rel, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    m["version"], m["setup_rev"] = ver, rev
    m.setdefault("files", [])
    m["patch"] = {"version": ver, "files": files}
    try:                                   # ประวัติการอัปเดต (changelog.json) แสดงในหน้า ตรวจสอบอัปเดต
        m["changelog"] = json.load(open(os.path.join(ROOT, "changelog.json"), encoding="utf-8"))
        top = m["changelog"][0]            # เครื่องรุ่นเก่าแสดงเฉพาะ notes จึงใส่รุ่นล่าสุดไว้ให้
        m["notes"] = "รุ่น %s:\n" % top["version"] + "\n".join(" - " + t for t in top["items"])
    except (OSError, ValueError):
        pass
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    print("OK patch %s files=%d -> %s" % (ver, len(files), out))


if __name__ == "__main__":
    main()
