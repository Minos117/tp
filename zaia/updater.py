"""ตรวจรุ่น/อัปเดตจาก GitHub Raw: ดาวน์โหลดเฉพาะไฟล์ที่ต่าง, ตรวจ SHA-256 ก่อนเขียน, สำรอง .bak, จัดการไฟล์ล็อก"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from .version import APP_VER, SETUP_REV


def app_dir():
    return os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "ZAIA-Prepare-Personal"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def vtuple(v):
    out = []
    for x in str(v).split("."):
        out.append(int("".join(c for c in x if c.isdigit()) or 0))
    return tuple(out)


def fetch_manifest(base):
    if not base:
        raise ValueError("ยังไม่ได้ตั้งค่า URL อัปเดต")
    if not base.endswith("/"):
        base += "/"
    return json.loads(_get(base + "update.json").decode("utf-8")), base


def is_newer(m):
    return vtuple(m.get("version", "0")) > vtuple(APP_VER)


def needs_setup(m):
    return int(m.get("setup_rev", 1)) > SETUP_REV


def plan(m, root=None):
    """รายชื่อไฟล์ที่ต้องดาวน์โหลด (ไม่มีในเครื่อง หรือ hash ต่าง)"""
    root = root or app_dir()
    todo = []
    for f in m.get("files", []):
        p = os.path.join(root, *f["path"].split("/"))
        if not os.path.exists(p) or sha256_file(p) != f["sha256"].lower():
            todo.append(f)
    return todo


def apply(m, base, files, root=None, progress=lambda s: None):
    """คืน (จำนวนไฟล์, รายการรอสลับตอนปิดโปรแกรม)  ถ้า hash ไม่ตรง = ไม่เขียนไฟล์นั้นและ raise"""
    root = root or app_dir()
    if not base.endswith("/"):
        base += "/"
    pend = []
    tmpdir = tempfile.mkdtemp(prefix="zaia_upd_")
    staged = []
    for f in files:                                   # ดาวน์โหลดและตรวจ hash ให้ครบก่อน แล้วค่อยเขียน
        progress("ดาวน์โหลด " + f["path"])
        data = _get(base + urllib.parse.quote(f.get("url", f["path"]), safe="/"), timeout=120)
        if hashlib.sha256(data).hexdigest() != f["sha256"].lower():
            raise ValueError("SHA-256 ไม่ตรงกับ update.json: " + f["path"])
        t = os.path.join(tmpdir, "%d.bin" % len(staged))
        with open(t, "wb") as fh:
            fh.write(data)
        staged.append((f, t))
    for f, t in staged:
        dst = os.path.join(root, *f["path"].split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            shutil.copy2(dst, dst + ".bak")
        try:
            os.replace(t, dst)
        except OSError:                                # ไฟล์ล็อก (เช่น exe ที่กำลังรัน) -> สลับหลังปิดโปรแกรม
            shutil.copy2(t, dst + ".new")
            pend.append(dst)
        progress("เขียน " + f["path"])
    shutil.rmtree(tmpdir, ignore_errors=True)
    return len(staged), pend


def finish_pending(pend, exe=None):
    """สร้างสคริปต์สลับไฟล์ที่ล็อกหลังโปรแกรมปิด แล้วเปิดโปรแกรมใหม่"""
    if not pend:
        return
    exe = exe or sys.executable
    lines = ["@echo off", "ping 127.0.0.1 -n 3 >nul"]
    for p in pend:
        lines.append('move /y "%s.new" "%s" >nul' % (p, p))
    lines.append('start "" "%s"' % exe)
    lines.append('del "%~f0"')
    path = os.path.join(tempfile.gettempdir(), "zaia_finish_update.cmd")
    with open(path, "w", encoding="mbcs" if os.name == "nt" else "utf-8") as f:   # mbcs = codepage ของเครื่อง (รองรับพาธไทย)
        f.write("\r\n".join(lines) + "\r\n")
    subprocess.Popen(["cmd", "/c", path], creationflags=0x08000000)
