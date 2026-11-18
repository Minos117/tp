r"""สร้าง release\update.json (SHA-256 ของทุกไฟล์ใน dist) + คัดลอกไฟล์ไป release\files\
ตรวจว่า APP_VER (zaia/version.py) >= AppVersion (installer.iss = รุ่นฐาน) ก่อนเสมอ  ใช้: python MakeRelease.py [BASE_URL]
อัปโหลดทั้งโฟลเดอร์ release ไปที่ GitHub (ต้องได้รับอนุมัติก่อนเผยแพร่ครั้งแรก)"""
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist", "ZAIA Prepare Personal")
OUT = os.path.join(ROOT, "release")


def grab(path, pat):
    m = re.search(pat, open(path, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("ไม่พบ %s ใน %s" % (pat, path))
    return m.group(1)


def main():
    ver = grab(os.path.join(ROOT, "zaia", "version.py"), r'^APP_VER\s*=\s*"([^"]+)"')
    rev = int(grab(os.path.join(ROOT, "zaia", "version.py"), r"^SETUP_REV\s*=\s*(\d+)"))
    iss = grab(os.path.join(ROOT, "installer.iss"), r"^AppVersion=(.+)$").strip()
    vt = lambda v: tuple(int(x) for x in v.split("."))
    if vt(ver) < vt(iss):      # installer.iss = รุ่นฐานของตัวติดตั้ง (1.0.2) ; APP_VER ขึ้นตามแพตช์ได้ แต่ห้ามต่ำกว่า
        sys.exit("APP_VER=%s ต่ำกว่า installer.iss AppVersion=%s" % (ver, iss))
    if not os.path.isdir(DIST):
        sys.exit("ยังไม่มี dist (ให้รัน build_all.bat ก่อน)")
    shutil.rmtree(OUT, ignore_errors=True)
    files = []
    for dp, _dn, fn in os.walk(DIST):
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, DIST).replace(os.sep, "/")
            h = hashlib.sha256(open(full, "rb").read()).hexdigest()
            dst = os.path.join(OUT, "files", *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(full, dst)
            files.append({"path": rel, "url": "files/" + rel, "sha256": h, "size": os.path.getsize(full)})
    man = {"version": ver, "setup_rev": rev, "notes": "", "files": sorted(files, key=lambda x: x["path"])}
    if len(sys.argv) > 1:
        man["base"] = sys.argv[1]
    with open(os.path.join(OUT, "update.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print("OK  version=%s setup_rev=%d files=%d -> %s" % (ver, rev, len(files), OUT))


if __name__ == "__main__":
    main()
