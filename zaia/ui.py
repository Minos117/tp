"""ZAIA Prepare Personal - หน้าจอ (tkinter)"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from . import core, layout, luna, render, updater
from .version import APP_NAME, APP_VER, UPDATE_BASE

GEO = {}
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo_th.json"), encoding="utf-8") as _f:
        GEO = json.load(_f)
except (OSError, ValueError):
    GEO = {}

BIG = ("Tahoma", 13, "bold")


def err(msg, title="ผิดพลาด"):
    messagebox.showerror(title, msg)


class Spin(ttk.Spinbox):
    pass


LOG_BG, LOG_FG = "#0C0C0C", "#D4D4D4"
_LOG_KEYS = (("err", ("ผิดพลาด", "Error", "error", "ไม่สำเร็จ", "ล้มเหลว", "Traceback")),
             ("warn", ("ยกเลิก", "หยุด", "เตือน", "ข้าม", "ไม่พบ", "ยังไม่")),
             ("ok", ("เสร็จ", "สำเร็จ", "ส่งพิมพ์แล้ว", "ตรงกัน", "เป็นรุ่นล่าสุด", "อัปเดตแล้ว")),
             ("info", ("→", "มีรุ่นใหม่", "ไฟล์", "รุ่น ")))


def _thai_font():
    """ฟอนต์ที่มีอักษรไทยในตัว (ไม่ต้องพึ่งฟอนต์สำรอง ตัวหนังสือจึงไม่ปนหลายแบบ)"""
    fams = set(tkfont.families())
    return next((f for f in ("Leelawadee UI", "Tahoma", "Segoe UI", "Loma") if f in fams), "TkDefaultFont")


def make_log(parent, **kw):
    """ช่อง log พื้นดำ ข้อความหลายสีแบบคอนโซล Python"""
    t = tk.Text(parent, bg=LOG_BG, fg=LOG_FG, insertbackground="white", relief="flat", padx=10, pady=8,
                font=(_thai_font(), 11), state="disabled", wrap="word", **kw)
    for tag, col in (("ts", "#7A7A7A"), ("err", "#FF5C57"), ("warn", "#F3F99D"), ("ok", "#5AF78E"), ("info", "#57C7FF"), ("head", "#FF6AC1")):
        t.tag_config(tag, foreground=col)
    return t


def log_line(t, line):
    """เขียน 1 บรรทัดลง make_log: [เวลา] เทา + ข้อความสีตามเนื้อหา"""
    t.config(state="normal")
    if line.startswith("▶"):                       # หัวข้อรุ่น (changelog)
        t.insert("end", line + "\n", "head")
        t.see("end")
        t.config(state="disabled")
        return
    if line.startswith("  •"):                     # รายการใน changelog ใช้สีปกติ
        t.insert("end", line + "\n", "")
        t.see("end")
        t.config(state="disabled")
        return
    ts = ""
    if line.startswith("[") and "]" in line[:12]:
        i = line.index("]") + 1
        ts, line = line[:i], line[i:]
    tag = ""
    for name, keys in _LOG_KEYS:
        if any(k in line for k in keys):
            tag = name
            break
    if ts:
        t.insert("end", ts, "ts")
    t.insert("end", line if line.endswith("\n") else line + "\n", tag)
    t.see("end")
    t.config(state="disabled")


def log_set(t, s):
    t.config(state="normal")
    t.delete("1.0", "end")
    t.config(state="disabled")
    for ln in s.splitlines():
        log_line(t, ln)
    t.yview_moveto(0)                              # แสดงจากบรรทัดบนสุด (รายการอัปเดตอ่านจากบนลงล่าง)


class Page(ttk.Frame):
    """หน้าเนื้อหาในหน้าต่างหลัก (เดิมเป็นหน้าต่างย่อย) — shim ให้โค้ดเดิมใช้ได้"""

    def __init__(self, app):
        super().__init__(app.content)
        self.app = app

    def title(self, t):
        self.app.set_title(t)

    def geometry(self, *a):
        pass

    def transient(self, *a):
        pass

    def protocol(self, *a):
        pass

    def bind(self, seq=None, func=None, add=None):
        return self.app.bind(seq, func, add)

    def destroy(self):
        if getattr(self.app, "_closing", False):
            return ttk.Frame.destroy(self)
        self.app.go_home()


# ====================================================================== หน้าต่างพรีวิว
class PreviewWin(tk.Toplevel):
    def __init__(self, app, pages, title):
        super().__init__(app)
        self.title("ตัวอย่างก่อนพิมพ์ - " + title)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)
        self.app, self.pages, self.i = app, pages, 0
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Button(bar, text="◀ ก่อนหน้า", command=lambda: self.go(-1)).pack(side="left", padx=4, pady=4)
        self.lbl = ttk.Label(bar, text="")
        self.lbl.pack(side="left", padx=8)
        ttk.Button(bar, text="ถัดไป ▶", command=lambda: self.go(1)).pack(side="left")
        ttk.Label(bar, text="  (ตัวอย่างโดยประมาณ — ตำแหน่งจริงดูตอนพิมพ์)").pack(side="left")
        self.cv = tk.Canvas(self, bg="#777")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(100, self.draw)

    def go(self, d):
        self.i = max(0, min(len(self.pages) - 1, self.i + d))
        self.draw()

    def draw(self):
        pg = self.pages[self.i]
        k = min((self.cv.winfo_width() - 20) / pg.w, (self.cv.winfo_height() - 20) / pg.h)
        if k <= 1:
            return
        render.draw_tk(self.cv, pg, k, self.app.font_family(), tkfont)
        self.cv.move("all", 10, 10)
        self.lbl.config(text="หน้า %d / %d" % (self.i + 1, len(self.pages)))


class EnvEditor(tk.Toplevel):
    """จัดวางจ่าหน้าซองอิสระ: ลากตราครุฑ/ผู้ส่ง/ที่/ผู้รับ ด้วยเมาส์หรือนิ้ว (ปุ่มลูกศรเลื่อนทีละ 0.5 มม.) และย่อ/ขยายได้"""

    def __init__(self, app, st, person):
        super().__init__(app)
        self.title("จัดวางจ่าหน้าซองอิสระ")
        self.app, self.st, self.person = app, dict(st), person
        self.adj = {k: list(v) for k, v in (st.get("env_adj") or {}).items()}
        self.sel = tk.StringVar(value="garuda")
        sw = self.winfo_screenwidth()
        self.k = max(2.0, min(4.2, (sw - 40) / 210.0))
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)
        y0 = {"บน": 0.0, "กลาง": 99.0, "ล่าง": 198.0}.get(str(st.get("env_pos", "บน")).replace("ส่วน", ""), 0.0)
        self.y0 = y0
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        for key, lab in layout.ENV_ITEMS:
            ttk.Radiobutton(top, text=lab, value=key, variable=self.sel, command=self.draw).pack(side="left", padx=6)
        ttk.Label(top, text="ลากชิ้นงานด้วยเมาส์ได้เลย").pack(side="left", padx=10)
        self.cv = tk.Canvas(self, bg="#777", highlightthickness=0, width=int(210 * self.k), height=int(99 * self.k))
        self.cv.pack(padx=8, pady=4)
        self.info = ttk.Label(self, text="", font=(app.ui_font, 11, "bold"))
        self.info.pack()
        bt = ttk.Frame(self, padding=6)
        bt.pack(fill="x")
        for txt, d in (("◀", (-0.5, 0)), ("▶", (0.5, 0)), ("▲", (0, -0.5)), ("▼", (0, 0.5))):
            ttk.Button(bt, text=txt, width=4, command=lambda d=d: self.nudge(*d)).pack(side="left", padx=2)
        ttk.Button(bt, text="ย่อ −", command=lambda: self.scale(-5)).pack(side="left", padx=(14, 2))
        ttk.Button(bt, text="ขยาย +", command=lambda: self.scale(5)).pack(side="left", padx=2)
        ttk.Button(bt, text="คืนชิ้นนี้", command=self.reset_one).pack(side="left", padx=(14, 2))
        ttk.Button(bt, text="คืนทั้งหมด", command=self.reset_all).pack(side="left", padx=2)
        ttk.Button(bt, text="ยกเลิก", command=self.destroy).pack(side="right", padx=2)
        ttk.Button(bt, text="บันทึกตำแหน่ง", style="Accent.TButton", command=self.ok).pack(side="right", padx=8)
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<B1-Motion>", self.move)
        for key, d in (("Left", (-0.5, 0)), ("Right", (0.5, 0)), ("Up", (0, -0.5)), ("Down", (0, 0.5))):
            self.bind("<%s>" % key, lambda e, d=d: self.nudge(*d))
        self.bind("<Escape>", lambda e: self.destroy())
        self._last = None
        self.draw()

    def page(self):
        st = dict(self.st)
        st["env_adj"] = self.adj
        return layout.build("env", [self.person], st, core.ALL_TYPES, "", "อำเภอ")[0]

    def draw(self):
        pg = self.page()
        k = self.k
        render.draw_tk(self.cv, pg, k, self.app.font_family(), tkfont)
        self.cv.configure(scrollregion=(0, self.y0 * k, 210 * k, (self.y0 + 99) * k))
        self.cv.xview_moveto(0)
        self.cv.yview_moveto(self.y0 / pg.h)
        b = layout.env_boxes(pg).get(self.sel.get())
        if b:
            self.cv.create_rectangle(b[0] * k, b[1] * k, b[2] * k, b[3] * k, outline="#245EDC", width=2, dash=(5, 3))
        a = self.adj.get(self.sel.get()) or [0, 0, 100]
        a = list(a) + [0, 0, 100][len(a):]
        self.info.config(text="%s :  ซ้าย/ขวา %+.1f มม.   บน/ล่าง %+.1f มม.   ขนาด %d%%" % (dict(layout.ENV_ITEMS)[self.sel.get()], a[0], a[1], a[2]))
        self._boxes = layout.env_boxes(pg)

    def cur(self):
        a = self.adj.setdefault(self.sel.get(), [0, 0, 100])
        while len(a) < 3:
            a.append(100 if len(a) == 2 else 0)
        return a

    def down(self, e):
        x, y = self.cv.canvasx(e.x) / self.k, self.cv.canvasy(e.y) / self.k
        hit = [(n, b) for n, b in self._boxes.items() if n != "fold" and b[0] <= x <= b[2] and b[1] <= y <= b[3]]
        if hit:
            hit.sort(key=lambda t: (t[1][2] - t[1][0]) * (t[1][3] - t[1][1]))      # ชิ้นเล็กสุดที่ถูกจุดนั้น
            self.sel.set(hit[0][0])
        self._last = (x, y)
        self.draw()

    def move(self, e):
        if not self._last:
            return
        x, y = self.cv.canvasx(e.x) / self.k, self.cv.canvasy(e.y) / self.k
        a = self.cur()
        a[0] = round(a[0] + x - self._last[0], 2)
        a[1] = round(a[1] + y - self._last[1], 2)
        self._last = (x, y)
        self.draw()

    def nudge(self, dx, dy):
        a = self.cur()
        a[0] += dx
        a[1] += dy
        self.draw()

    def scale(self, d):
        a = self.cur()
        a[2] = max(30, min(300, a[2] + d))
        self.draw()

    def reset_one(self):
        self.adj.pop(self.sel.get(), None)
        self.draw()

    def reset_all(self):
        self.adj.clear()
        self.draw()

    def ok(self):
        clean = {k: [round(x, 2) for x in v[:3]] for k, v in self.adj.items() if v and (abs(v[0]) > 1e-6 or abs(v[1]) > 1e-6 or abs((v[2] if len(v) > 2 else 100) - 100) > 1e-6)}
        self.app.st["env_adj"] = clean
        core.save_settings(self.app.st)
        self.destroy()
        messagebox.showinfo("บันทึกแล้ว", "บันทึกตำแหน่งจ่าหน้าซองแล้ว (ใช้กับการพิมพ์และตัวอย่างทันที)")


# ====================================================================== ตั้งค่า
class VScroll(ttk.Frame):
    """กรอบเลื่อนขึ้นลงได้ (แถบเลื่อน + ล้อเมาส์) ใส่เนื้อหาใน .inner — กันปุ่ม/ช่องตกจอเมื่อหน้าต่างเตี้ย"""

    def __init__(self, parent, bg=None):
        super().__init__(parent)
        self.cv = tk.Canvas(self, highlightthickness=0, bg=bg or BG)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        self.inner = ttk.Frame(self.cv)
        self._win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._cfg)
        self.cv.bind("<Configure>", self._fit)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", lambda ev: self.cv.yview_scroll(-1 * (ev.delta // 120), "units")))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _fit(self, e):
        """ให้เนื้อหากว้างเต็มกรอบ และสูงอย่างน้อยเท่ากรอบ (พื้นถมเต็ม ไม่เห็นสีเทาของ canvas)"""
        self.cv.itemconfigure(self._win, width=e.width, height=max(e.height, self.inner.winfo_reqheight()))

    def _cfg(self, e):
        self.cv.configure(scrollregion=self.cv.bbox("all"))
        self.cv.itemconfigure(self._win, height=max(self.cv.winfo_height(), self.inner.winfo_reqheight()))


class SettingsWin(Page):
    SAMPLE_PX = 5.0     # พิกเซลต่อมม. ในช่องดูตัวอย่างผู้ลงนาม

    def __init__(self, app):
        super().__init__(app)
        st = app.st
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        f1 = ttk.Frame(nb, padding=16)
        nb.add(f1, text="  ทั่วไป  ")
        self.v = {}
        rows = [("amphoe", "อำเภอสำรอง (ใช้เมื่อข้อมูลไม่มีอำเภอ)"), ("province", "จังหวัดสำรอง (ใช้เมื่อข้อมูลไม่มีจังหวัด)"),
                ("org", "อักษรย่อจังหวัด"), ("year", "ปีที่ตรวจสอบ (พ.ศ.)"), ("font", "ฟอนต์พิมพ์"),
                ("delay", "หน่วงเวลาระหว่างชุด (วินาที)"), ("update_url", "URL อัปเดต (GitHub Raw)")]
        for i, (k, lab) in enumerate(rows):
            ttk.Label(f1, text=lab).grid(row=i, column=0, sticky="w", pady=5)
            self.v[k] = tk.StringVar(value=str(st.get(k, "")))
            ttk.Entry(f1, textvariable=self.v[k], width=50).grid(row=i, column=1, pady=5, padx=8)
        self.tam_p2 = tk.BooleanVar(value=bool(st.get("show_tambon_p2", True)))
        ttk.Checkbutton(f1, text="พิมพ์ชื่อตำบลมุมขวาบนของหน้า 2 เป็นต้นไป (บัญชีตรวจสอบสภาพ / บัญชีสรุป)", variable=self.tam_p2).grid(
            row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=4)
        self.backup = tk.BooleanVar(value=st.get("backup", True))
        ttk.Checkbutton(f1, text="สำรองไฟล์ Excel ต้นฉบับอัตโนมัติก่อนเขียนกลับ", variable=self.backup).grid(
            row=len(rows), column=0, columnspan=2, sticky="w", pady=8)
        # ---- ข้อมูลหน่วยสัสดี (ใช้กับ เมนู 6 แบบพิมพ์รายบุคคล + จ่าหน้าซอง)
        f3o = ttk.Frame(nb)
        nb.add(f3o, text="  ข้อมูลหน่วย / แบบพิมพ์รายบุคคล  ")
        sc3 = VScroll(f3o)
        sc3.pack(fill="both", expand=True)
        f3 = ttk.Frame(sc3.inner, padding=16)
        f3.pack(fill="both", expand=True)
        ttk.Label(f3, text="กรอกครั้งเดียว โปรแกรมดึงไปใส่แบบพิมพ์รายบุคคลและซองจดหมายให้ทุกใบ (เมนู 2)", foreground="#555").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        rows3 = [("unit_name", "ชื่อหน่วย (ผู้ส่งบนซอง)"), ("unit_addr", "ที่ตั้ง/บรรทัดที่อยู่ (เช่น ที่ว่าการอำเภอ)"),
                 ("unit_amphoe", "อำเภอของหน่วย (ว่าง = ใช้อำเภอสำรอง)"), ("unit_province", "จังหวัดของหน่วย (ว่าง = ใช้จังหวัดสำรอง)"),
                 ("unit_zip", "รหัสไปรษณีย์หน่วย (ว่าง = คิดให้อัตโนมัติ)"), ("sad_tel", "เบอร์โทรสัสดีอำเภอ (พิมพ์บนแบบพิมพ์)"),
                 ("deadline", "ให้ส่งคืนภายในวันที่ (เช่น 15 ธันวาคม 2569)"), ("env_no", "เลขที่หนังสือบนซอง “ที่ …” (ว่าง = ไม่พิมพ์)")]
        for i, (k, lab) in enumerate(rows3, 1):
            ttk.Label(f3, text=lab).grid(row=i, column=0, sticky="w", pady=5)
            self.v[k] = tk.StringVar(value=str(st.get(k, "")))
            ttk.Entry(f3, textvariable=self.v[k], width=46).grid(row=i, column=1, pady=5, padx=8, sticky="w")
        self.env_pos = tk.StringVar(value=str(st.get("env_pos", "บน")).replace("ส่วน", ""))
        ttk.Label(f3, text="จ่าหน้าซอง: พิมพ์ด้านหลัง A4 แล้วพับสาม — วางที่ส่วน").grid(row=len(rows3) + 3, column=0, sticky="w", pady=6)
        ttk.Combobox(f3, textvariable=self.env_pos, values=["บน", "กลาง", "ล่าง"], state="readonly", width=10).grid(row=len(rows3) + 3, column=1, sticky="w", padx=8)
        self.zipmsg = ttk.Label(f3, text="")
        ttk.Button(f3, text="คิดรหัสไปรษณีย์จากอำเภอ/จังหวัดของหน่วย", command=self.guess_zip).grid(row=len(rows3) + 1, column=1, sticky="w", pady=6, padx=8)
        self.zipmsg.grid(row=len(rows3) + 2, column=1, sticky="w", padx=8)
        # ---- ปรับแบบพิมพ์เอง (ข้อความ / ขนาด / ตำแหน่ง / เปิด-ปิดส่วนต่าง ๆ)
        f4o = ttk.Frame(nb)
        nb.add(f4o, text="  ปรับแบบพิมพ์  ")
        top4 = ttk.Frame(f4o, padding=(16, 12, 16, 4))
        top4.pack(fill="x")
        ttk.Label(top4, text="เลือกแบบพิมพ์ที่จะปรับ").pack(side="left")
        names = {k: v[0] for k, v in layout.SCHEMA.items()}
        self.tpl_kind = tk.StringVar(value=names["form"])
        cb4 = ttk.Combobox(top4, textvariable=self.tpl_kind, values=list(names.values()), state="readonly", width=34)
        cb4.pack(side="left", padx=8)
        cb4.bind("<<ComboboxSelected>>", lambda e: self.tpl_build())
        ttk.Button(top4, text="ดูตัวอย่าง", command=self.tpl_preview).pack(side="left", padx=4)
        ttk.Button(top4, text="คืนค่าเริ่มต้นแบบนี้", command=self.tpl_reset).pack(side="left", padx=4)
        ttk.Label(f4o, text="ตัวแปรที่ใส่ในข้อความได้: {year} ปี  {amphoe} อำเภอ  {province} จังหวัด  {tel} เบอร์สัสดี  {deadline} วันส่งคืน  {ptype} ประเภท  {tambon} ตำบล"
                  "\nกด “บันทึกการตั้งค่า” ด้านล่างเพื่อใช้จริง (ดูตัวอย่างใช้ค่าที่กำลังแก้อยู่ได้เลยโดยไม่ต้องบันทึก)", foreground="#555", justify="left").pack(anchor="w", padx=16)
        self.tpl_names = {v: k for k, v in names.items()}
        self.tpl_vars = {}
        sc4 = VScroll(f4o)
        sc4.pack(fill="both", expand=True, padx=16, pady=6)
        self.tpl_box = ttk.Frame(sc4.inner, padding=4)
        self.tpl_box.pack(fill="both", expand=True)
        self.tpl_build()
        # ---- ผู้ลงนาม + ลายเซ็น (ดูตัวอย่างจริง ลากลายเซ็นไปวางได้)
        f2 = ttk.Frame(nb, padding=16)
        nb.add(f2, text="  ผู้ลงนาม / ลายเซ็น  ")
        self.keys = {"จังหวัด": "sign_province", "อำเภอ": "sign_amphoe", "กำนัน": "sign_kamnan"}
        self.lines = {lv: list(st.get(k, [])) for lv, k in self.keys.items()}
        self.lv = tk.StringVar(value="อำเภอ")
        self.sig_level = tk.StringVar(value=st.get("sig_level", "อำเภอ"))
        self.sig_path = tk.StringVar(value=st.get("sig_image", ""))
        self.sig_w = tk.DoubleVar(value=float(st.get("sig_w", 32)))
        self.dx, self.dy = float(st.get("sig_dx", 0)), float(st.get("sig_dy", 0))
        lsc = VScroll(f2)
        lsc.pack(side="left", fill="y", padx=(0, 16))
        left = lsc.inner
        ttk.Label(left, text="ระดับผู้ลงนามที่แก้ไข").pack(anchor="w")
        cb = ttk.Combobox(left, textvariable=self.lv, values=core.LEVELS, state="readonly", width=14)
        cb.pack(anchor="w", pady=(2, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.switch())
        ttk.Label(left, text="ข้อความ 1 บรรทัดต่อ 1 แถว ชิดซ้ายของกล่อง\nเคาะวรรคเพื่อเลื่อนเองได้ (เหมือนใน Excel)\nใช้ {ตำบล} แทนชื่อตำบลของกำนัน", justify="left").pack(anchor="w")
        self.txt = tk.Text(left, width=40, height=7, font=(app.ui_font, 12))
        self.txt.pack(anchor="w", pady=6)
        self.txt.bind("<KeyRelease>", lambda e: self.edited())
        ttk.Separator(left).pack(fill="x", pady=8)
        ttk.Label(left, text="ลายเซ็น (PNG พื้นโปร่งแสงจะสวยที่สุด)").pack(anchor="w")
        r = ttk.Frame(left)
        r.pack(anchor="w", pady=4)
        ttk.Button(r, text="เลือกไฟล์ภาพ…", command=self.pick_sig).pack(side="left")
        ttk.Button(r, text="ไม่ใช้ลายเซ็น", command=lambda: (self.sig_path.set(""), self.draw())).pack(side="left", padx=6)
        ttk.Label(left, text="ใช้ลายเซ็นกับผู้ลงนามระดับ").pack(anchor="w", pady=(6, 0))
        c2 = ttk.Combobox(left, textvariable=self.sig_level, values=core.LEVELS, state="readonly", width=14)
        c2.pack(anchor="w")
        c2.bind("<<ComboboxSelected>>", lambda e: self.draw())
        ttk.Label(left, text="ขนาดภาพ (มม. กว้าง)").pack(anchor="w", pady=(8, 0))
        ttk.Scale(left, from_=12, to=80, variable=self.sig_w, command=lambda v: self.draw(), length=260).pack(anchor="w")
        ttk.Button(left, text="รีเซ็ตตำแหน่งลายเซ็น", command=self.reset_pos).pack(anchor="w", pady=8)
        right = ttk.Frame(f2)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="ตัวอย่างบล็อกลงนามในกระดาษ — ลากลายเซ็นด้วยเมาส์เพื่อวางตำแหน่ง", font=(app.ui_font, 11, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(right, bg="white", highlightthickness=1, highlightbackground="#AAB6CF", height=420)
        self.cv.pack(fill="both", expand=True, pady=6)
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<ButtonPress-1>", self.drag0)
        self.cv.bind("<B1-Motion>", self.drag1)
        self._ph = None
        self._drag = None
        nb.pack_forget()
        ttk.Button(self, text="บันทึกการตั้งค่า", style="Accent.TButton", command=self.save).pack(side="bottom", anchor="e", pady=10)
        # ---- ธีมสี
        f5 = ttk.Frame(nb, padding=12)
        nb.add(f5, text="  ธีมสี  ")
        self.theme_ui(f5)
        nb.pack(fill="both", expand=True)
        self.switch()

    # ---- ธีมสี (พรีเซ็ต 20 ชุด กดแล้วเปลี่ยนทันที)
    def theme_ui(self, f):
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="รูปปุ่ม:").pack(side="left")
        self.btn_style = tk.StringVar(value=luna.STYLE)
        for txt, val in (("เรียบ (แนะนำ)", "flat"), ("เงาแบบ Windows XP", "glossy")):
            ttk.Radiobutton(top, text=txt, value=val, variable=self.btn_style,
                            command=lambda: self.app.set_theme(self.app.st.get("theme", luna.DEFAULT), self.btn_style.get())).pack(side="left", padx=8)
        ttk.Label(top, text="   คลิกการ์ดสีเพื่อเปลี่ยนธีมทันที (บันทึกให้อัตโนมัติ)").pack(side="left")
        sc = VScroll(f)
        sc.pack(fill="both", expand=True, pady=8)
        self.theme_cv = {}
        cols = 4
        for i, (key, name, base, btn, line) in enumerate(luna.THEMES):
            cv = tk.Canvas(sc.inner, width=150, height=104, highlightthickness=3, cursor="hand2", bd=0)
            cv.grid(row=i // cols, column=i % cols, padx=6, pady=6)
            cv.bind("<Button-1>", lambda e, k=key: self.app.set_theme(k))
            self.theme_cv[key] = (cv, name)
        self.theme_draw()

    def theme_draw(self):
        cur = self.app.st.get("theme", luna.DEFAULT)
        for key, (cv, name) in self.theme_cv.items():
            c = luna.theme_colors(key)
            cv.delete("all")
            cv.config(bg=c["BG"], highlightbackground=luna.TITLE_LINE if key == cur else c["LINE"], highlightcolor=luna.TITLE_LINE)
            cv.create_rectangle(0, 0, 36, 104, fill=c["SIDE"], outline="")
            for j in range(4):
                cv.create_rectangle(8, 24 + j * 14, 28, 31 + j * 14, fill=c["SIDE_ACT_BG"] if j == 0 else c["SIDE_HOVER"], outline="")
            cv.create_rectangle(36, 0, 150, 16, fill=c["SIDE"], outline="")
            cv.create_rectangle(36, 16, 150, 19, fill=c["TITLE_LINE"], outline="")
            cv.create_rectangle(46, 28, 140, 52, fill="white", outline=c["LINE"])
            cv.create_rectangle(52, 34, 96, 40, fill=c["NAVY"], outline="")
            cv.create_rectangle(52, 44, 120, 47, fill=c["LINE_D"], outline="")
            cv.create_rectangle(92, 62, 140, 78, fill=c["BTN"], outline="")
            cv.create_rectangle(46, 62, 86, 78, fill=c["HEAD_L"], outline=c["LINE_D"])
            cv.create_text(42, 94, text=("✔ " if key == cur else "") + name, anchor="w", fill=c["NAVY"], font=(self.app.ui_font, 9, "bold"))

    # ---- ปรับแบบพิมพ์
    def tpl_kindkey(self):
        return self.tpl_names[self.tpl_kind.get()]

    def tpl_build(self):
        kind = self.tpl_kindkey()
        for w in self.tpl_box.winfo_children():
            w.destroy()
        vs = self.tpl_vars.setdefault(kind, {})
        d = layout.tp(self.app.st, kind)
        for i, (key, lab, typ, dflt) in enumerate(layout.SCHEMA[kind][1]):
            if key not in vs:
                vs[key] = tk.BooleanVar(value=bool(d[key])) if typ == "b" else tk.StringVar(value=str(d[key]))
            if typ == "b":
                ttk.Checkbutton(self.tpl_box, text=lab, variable=vs[key]).grid(row=i, column=0, columnspan=2, sticky="w", pady=3)
            else:
                ttk.Label(self.tpl_box, text=lab).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 10))
                ttk.Entry(self.tpl_box, textvariable=vs[key], width=70 if typ == "t" else 10).grid(row=i, column=1, sticky="w", pady=3)
        if kind == "env":
            ttk.Button(self.tpl_box, text="จัดวางอิสระ (ลากตราครุฑ/ที่อยู่ ตามใจ)", style="Accent.TButton",
                       command=self.env_edit).grid(row=len(layout.SCHEMA[kind][1]) + 1, column=0, columnspan=2, sticky="w", pady=12)

    def env_edit(self):
        st = dict(self.app.st)
        for k in ("unit_name", "unit_addr", "unit_amphoe", "unit_province", "unit_zip", "env_no", "amphoe", "province"):
            if k in self.v:
                st[k] = self.v[k].get().strip()
        st["env_pos"] = self.env_pos.get()
        st["tpl"] = self.tpl_collect()
        rows = self.app.db.persons[:1] or [dict(rank="ส.อ.", name="สมชาย", surname="ใจดี", house="99", moo="5", tambon="ตัวอย่าง",
                                               amphoe=st.get("amphoe", "ตัวอย่าง"), province=st.get("province", "ตัวอย่าง"))]
        EnvEditor(self.app, st, rows[0])

    def tpl_collect(self):
        out = {k: dict(v) for k, v in (self.app.st.get("tpl", {}) or {}).items()}     # ของเดิมที่ยังไม่ได้เปิดดู คงไว้
        for kind, vs in self.tpl_vars.items():
            dflt = {k: v for k, _l, _t, v in layout.SCHEMA[kind][1]}
            typ = {k: t for k, _l, t, _v in layout.SCHEMA[kind][1]}
            o = {}
            for k, var in vs.items():
                v = var.get()
                if typ[k] == "n":
                    try:
                        v = float(v)
                        v = int(v) if v == int(v) else v
                    except ValueError:
                        v = dflt[k]
                if v != dflt[k]:
                    o[k] = v
            if o:
                out[kind] = o
            else:
                out.pop(kind, None)
        return out

    def tpl_reset(self):
        kind = self.tpl_kindkey()
        self.tpl_vars.pop(kind, None)
        self.app.st.setdefault("tpl", {}).pop(kind, None)
        if kind == "env":
            self.app.st.pop("env_adj", None)
        self.tpl_build()

    def tpl_preview(self):
        kind = self.tpl_kindkey()
        st = dict(self.app.st)
        for k in ("sad_tel", "deadline", "env_no", "unit_name", "unit_addr", "unit_amphoe", "unit_province", "unit_zip", "amphoe", "province", "year"):
            if k in self.v:
                st[k] = self.v[k].get().strip()
        st["env_pos"] = self.env_pos.get()
        st["tpl"] = self.tpl_collect()
        rows = self.app.db.persons[:3] or [dict(rank="ส.อ.", name="สมชาย", surname="ใจดี", nid="1234567890123", year="ทบ.2566", mark="ส.น.0000", branch="พ.",
                                               father="สมศักดิ์", fsur="ใจดี", mother="สมหญิง", msur="ใจดี", house="99", moo="5", tambon="ตัวอย่าง",
                                               amphoe=st.get("amphoe", "ตัวอย่าง"), province=st.get("province", "ตัวอย่าง"))]
        try:
            pages = layout.build(kind, rows, st, core.ALL_TYPES, "", "อำเภอ")
        except Exception as e:
            return err("สร้างตัวอย่างไม่สำเร็จ: %s" % e)
        PreviewWin(self.app, pages, layout.SCHEMA[kind][0])

    def guess_zip(self):
        a = self.v["unit_amphoe"].get().strip() or self.v["amphoe"].get().strip()
        p = self.v["unit_province"].get().strip() or self.v["province"].get().strip()
        z = core.zip_lookup(p, a)
        if z:
            self.v["unit_zip"].set(z)
        self.zipmsg.config(text=("พบ %s" % z) if z else "ไม่พบรหัสของ อ.%s จ.%s — กรอกเอง" % (a, p))

    # ---- ตัวแก้ไขผู้ลงนาม
    def switch(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(self.lines[self.lv.get()]))
        self.draw()

    def edited(self):
        t = [l for l in self.txt.get("1.0", "end").split("\n")]
        while t and t[-1] == "":
            t.pop()
        self.lines[self.lv.get()] = t
        self.draw()

    def pick_sig(self):
        p = filedialog.askopenfilename(filetypes=[("ภาพ", "*.png *.jpg *.jpeg")])
        if p:
            self.sig_path.set(p)
            self.draw()

    def reset_pos(self):
        self.dx = self.dy = 0.0
        self.draw()

    def geom(self):
        k = self.SAMPLE_PX
        W = self.cv.winfo_width() or 700
        return k, W / 2, 50

    def draw(self):
        cv = self.cv
        cv.delete("all")
        k, cx, y0 = self.geom()
        lv = self.lv.get()
        lines = self.lines[lv]
        fam = self.app.font_family()
        f = tkfont.Font(family=fam, size=-int(16 * 25.4 / 72 * k))
        cv.create_text(12, 12, anchor="nw", fill="#8A94A8", text="(ตัวอย่างบล็อกลงนาม — กรอบซ้ายสุดคือขอบซ้ายของกล่องในกระดาษ)", font=(self.app.ui_font, 10))
        tam = (self.app.db.tambons() or ["ตัวอย่าง"])[0]
        for i, t in enumerate(lines):
            cv.create_text(cx - 40 * k, y0 + (i + 0.5) * layout.LINE * k, text=t.rstrip().replace("{ตำบล}", tam), font=f, anchor="w")
        idx = layout.sig_name_index(lv)
        self._sig_box = None
        p = self.sig_path.get()
        if p and os.path.exists(p):
            try:
                from PIL import Image, ImageTk
                im = Image.open(p).convert("RGBA")
                w = self.sig_w.get()
                h = w * im.height / im.width
                ph = ImageTk.PhotoImage(im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS))
                self._ph = ph
                x = cx + self.dx * k
                y = y0 + (idx - layout.SIG_LIFT) * layout.LINE * k + self.dy * k
                cv.create_image(x, y, image=ph, anchor="center", tags="sig")
                self._sig_box = (x - w * k / 2, y - h * k / 2, x + w * k / 2, y + h * k / 2)
                if self.sig_level.get() != lv:
                    cv.create_text(cx, y0 + len(lines) * layout.LINE * k + 20, fill="#B42318",
                                   text="ลายเซ็นตั้งให้ใช้กับระดับ “%s” — ระดับนี้จะไม่แสดงลายเซ็น" % self.sig_level.get(), font=(self.app.ui_font, 11))
            except Exception:
                pass

    def drag0(self, e):
        b = self._sig_box
        self._drag = (e.x, e.y) if b and b[0] <= e.x <= b[2] and b[1] <= e.y <= b[3] else None

    def drag1(self, e):
        if self._drag:
            k = self.SAMPLE_PX
            self.dx += (e.x - self._drag[0]) / k
            self.dy += (e.y - self._drag[1]) / k
            self._drag = (e.x, e.y)
            self.draw()

    def save(self):
        st = self.app.st
        try:
            for k, v in self.v.items():
                val = v.get().strip()
                st[k] = float(val) if k == "delay" else val
        except ValueError:
            return err("ค่าตัวเลขไม่ถูกต้อง")
        for lv, k in self.keys.items():
            st[k] = self.lines[lv]
        st["backup"] = self.backup.get()
        st["env_pos"] = self.env_pos.get()
        st["show_tambon_p2"] = self.tam_p2.get()
        st["tpl"] = self.tpl_collect()
        st["sig_image"], st["sig_level"] = self.sig_path.get(), self.sig_level.get()
        st["sig_w"], st["sig_dx"], st["sig_dy"] = round(self.sig_w.get(), 1), round(self.dx, 2), round(self.dy, 2)
        core.save_settings(st)
        messagebox.showinfo("บันทึกแล้ว", "บันทึกการตั้งค่าเรียบร้อย")
        self.app.go_home()


# ====================================================================== 1) นำเข้าข้อมูล
class ImportWin(Page):
    def __init__(self, app):
        super().__init__(app)
        self.title("นำเข้าข้อมูลจากไฟล์ Excel")
        self.geometry("980x720")
        self.app = app
        self.transient(app)
        self.path = tk.StringVar()
        self.sheet = tk.StringVar()
        self.hrow = tk.IntVar(value=1)
        self.srow = tk.IntVar(value=2)
        self.erow = tk.IntVar(value=0)
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="ไฟล์:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path, width=50).grid(row=0, column=1, padx=4, sticky="we")
        top.columnconfigure(1, weight=1)
        ttk.Button(top, text="เลือกไฟล์…", command=self.pick).grid(row=0, column=2)
        ttk.Label(top, text="ชีต:").grid(row=1, column=0, sticky="w", pady=4)
        self.cb = ttk.Combobox(top, textvariable=self.sheet, state="readonly", width=40)
        self.cb.grid(row=1, column=1, sticky="w", padx=4)
        self.cb.bind("<<ComboboxSelected>>", lambda e: self.load_headers())
        r2 = ttk.Frame(top)
        r2.grid(row=2, column=0, columnspan=3, sticky="w", pady=4)
        for lab, var in (("แถวหัวตาราง", self.hrow), ("เริ่มดึงแถวที่", self.srow), ("ถึงแถวที่", self.erow)):
            ttk.Label(r2, text=lab).pack(side="left", padx=(8, 2))
            Spin(r2, from_=1, to=100000, textvariable=var, width=7).pack(side="left")
        r3 = ttk.Frame(top)
        r3.grid(row=3, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Button(r3, text="อ่านหัวตารางใหม่", command=self.load_headers).pack(side="left", padx=8)
        ttk.Button(r3, text="หาแถวสุดท้ายอัตโนมัติ", command=self.find_last).pack(side="left")
        b = ttk.Frame(self, padding=8)          # แถบปุ่มล่างสุด: pack ก่อนเสมอ จะไม่ถูกดันตกจอ
        b.pack(side="bottom", fill="x")
        mid = ttk.LabelFrame(self, text="จับคู่คอลัมน์ (เลือกคอลัมน์ในไฟล์ที่ตรงกับข้อมูลแต่ละช่อง)", padding=6)
        mid.pack(fill="both", expand=True, padx=8)
        self.cv = cv = tk.Canvas(mid, height=190, highlightthickness=0)
        sb = ttk.Scrollbar(mid, orient="vertical", command=cv.yview)
        self.mf = ttk.Frame(cv)
        self.mf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        self._win = cv.create_window((0, 0), window=self.mf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cv.bind("<Configure>", self._resize)
        cv.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", lambda ev: cv.yview_scroll(-1 * (ev.delta // 120), "units")))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        bot = ttk.LabelFrame(self, text="ตัวอย่าง 5 แถวแรกที่จะนำเข้า", padding=6)
        bot.pack(side="bottom", fill="x", padx=8, pady=6)
        self.tv = ttk.Treeview(bot, height=4, show="headings")
        hs = ttk.Scrollbar(bot, orient="horizontal", command=self.tv.xview)
        self.tv.configure(xscrollcommand=hs.set)
        self.tv.pack(fill="x")
        hs.pack(fill="x")
        self.mvars, self.opts = {}, []
        self.ncols = 2
        ttk.Button(b, text="รีเฟรชตัวอย่าง", command=self.preview).pack(side="left")
        ttk.Button(b, text="นำเข้า", style="Accent.TButton", command=self.do_import).pack(side="right")
        ttk.Button(b, text="ยกเลิก", command=self.destroy).pack(side="right", padx=6)
        self.msg = ttk.Label(b, text="")
        self.msg.pack(side="left", padx=10)

    def _resize(self, e):
        """ขยาย/ย่อหน้าต่างแล้วจัดช่องจับคู่ให้พอดีความกว้าง (2-4 คอลัมน์)"""
        self.cv.itemconfigure(self._win, width=e.width)
        n = max(1, min(4, e.width // 430))
        if n != self.ncols and self.mvars:
            self.ncols = n
            self._grid()

    def _grid(self):
        n = self.ncols
        for i, k in enumerate(self.mvars):
            lab, cb = self.mrows[k]
            lab.grid(row=i // n, column=(i % n) * 2, sticky="w", padx=4, pady=1)
            cb.grid(row=i // n, column=(i % n) * 2 + 1, padx=4, pady=1)

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm *.xlsb"), ("ทั้งหมด", "*.*")])
        if p:
            self.open_path(p)

    def open_path(self, p):
        self.path.set(p)
        try:
            sh = core.list_sheets(p)
        except Exception as e:
            return err("เปิดไฟล์ไม่ได้: %s" % e)
        self.cb["values"] = sh
        guess = "ฐานข้อมูล" if "ฐานข้อมูล" in sh else sh[0]
        self.sheet.set(guess)
        self.load_headers()

    def load_headers(self):
        try:
            rows = core.read_rows(self.path.get(), self.sheet.get(), self.hrow.get(), self.hrow.get())
        except Exception as e:
            return err("อ่านชีตไม่ได้: %s" % e)
        hdr = rows[0][1] if rows else []
        n = max(len(hdr), 45)
        hdr = hdr + [""] * (n - len(hdr))
        self.opts = ["(ไม่ดึง)"] + ["%s  %s" % (core.col_letter(i + 1), h) for i, h in enumerate(hdr)]
        mp = core.auto_map(hdr)
        for w in self.mf.winfo_children():
            w.destroy()
        self.mvars, self.mrows = {}, {}
        for i, (k, (title, _l)) in enumerate(core.FIELDS.items()):
            star = " *" if k in core.REQUIRED else ""
            lab = ttk.Label(self.mf, text="%s%s" % (title, star), width=22)
            v = tk.StringVar(value=self.opts[mp[k]] if k in mp else "(ไม่ดึง)")
            cb = ttk.Combobox(self.mf, textvariable=v, values=self.opts, state="readonly", width=30)
            cb.bind("<<ComboboxSelected>>", lambda e: self.preview())
            self.mvars[k] = v
            self.mrows[k] = (lab, cb)
        self._grid()
        self.srow.set(self.hrow.get() + 1)
        self.find_last()

    def mapping(self):
        m = {}
        for k, v in self.mvars.items():
            val = v.get()
            if val != "(ไม่ดึง)":
                m[k] = core.col_index(val.split()[0])
        return m

    def find_last(self):
        try:
            self.erow.set(core.detect_last_row(self.path.get(), self.sheet.get(), self.srow.get(), self.mapping()))
        except Exception as e:
            self.msg.config(text=str(e))
        self.preview()

    def preview(self):
        try:
            m = self.mapping()
            rows = core.read_rows(self.path.get(), self.sheet.get(), self.srow.get(), self.srow.get() + 4)
        except Exception:
            return
        keys = [k for k in ("rank", "name", "surname", "nid", "moo", "tambon", "type", "result") if k in m]
        self.tv["columns"] = ["row"] + keys
        self.tv.heading("row", text="แถว")
        self.tv.column("row", width=50)
        for k in keys:
            self.tv.heading(k, text=core.FIELDS[k][0])
            self.tv.column(k, width=110)
        self.tv.delete(*self.tv.get_children())
        for r, cells in rows:
            self.tv.insert("", "end", values=[r] + [cells[m[k] - 1] if m[k] - 1 < len(cells) else "" for k in keys])
        miss = [core.FIELDS[k][0] for k in core.REQUIRED if k not in m]
        self.msg.config(text=("ยังไม่ได้เลือก: " + ", ".join(miss)) if miss else "จะนำเข้าแถว %d–%d" % (self.srow.get(), self.erow.get()))

    def do_import(self):
        m = self.mapping()
        miss = [core.FIELDS[k][0] for k in core.REQUIRED if k not in m]
        if miss:
            return err("ต้องจับคู่คอลัมน์: " + ", ".join(miss))
        if self.app.db.persons and not messagebox.askyesno("ยืนยัน", "มีข้อมูลเดิมในโปรแกรม %d คน\nการนำเข้าจะแทนที่ข้อมูลเดิม (ไฟล์ Excel เดิมไม่ถูกแก้) ต่อไปไหม?" % len(self.app.db.persons)):
            return
        try:
            ps = core.build_persons(self.path.get(), self.sheet.get(), self.srow.get(), self.erow.get(), m)
        except Exception as e:
            return err("นำเข้าไม่สำเร็จ: %s" % e)
        if not ps:
            return err("ไม่พบข้อมูลในช่วงแถวที่เลือก")
        self.app.db.set_import(ps, {"path": self.path.get(), "sheet": self.sheet.get(), "mapping": m,
                                    "header_row": self.hrow.get(), "start": self.srow.get(), "end": self.erow.get()})
        self.app.refresh_status()
        no_res = [core.FIELDS[k][0] for k in core.RESULT_FIELDS if k not in m]
        extra = ("\n\nหมายเหตุ: คอลัมน์ผลตรวจที่ไม่ได้จับคู่ จะไม่ถูกเขียนกลับไฟล์: " + ", ".join(no_res)) if no_res else ""
        messagebox.showinfo("สำเร็จ", "นำเข้า %d คน (%d ตำบล)%s" % (len(ps), len(self.app.db.tambons()), extra))
        self.destroy()


# ====================================================================== 3) บันทึกผล
class RecordWin(Page):
    def __init__(self, app):
        super().__init__(app)
        self.title("บันทึกผลการตรวจสอบสภาพ")
        self.app, self.db = app, app.db
        self.cur = None
        fam = app.ui_font
        self.F = tkfont.Font(family=fam, size=11)                    # ฟอนต์ปรับขนาดอัตโนมัติตามขนาดหน้าต่าง
        self.FB = tkfont.Font(family=fam, size=13, weight="bold")
        self.FL = tkfont.Font(family=fam, size=12)
        self.FH = tkfont.Font(family=fam, size=18, weight="bold")
        stl = ttk.Style()
        for nm in ("Rec.TLabel", "Rec.TCheckbutton", "Rec.TRadiobutton"):
            stl.configure(nm, font=self.F)
        stl.configure("Rec.TButton", font=self.F)
        stl.configure("Rec.Accent.TButton", font=self.FB)
        self._k = None
        left = ttk.Frame(self, padding=6)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="ค้นหา (เลขบัตร / ชื่อ / สกุล)", style="Rec.TLabel").pack(anchor="w")
        self.q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.q, width=30, font=self.F)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda ev: self.refill())
        e.bind("<Return>", lambda ev: self.pick_first())
        self.tam = tk.StringVar(value=core.ALL_TAMBON)
        cb = ttk.Combobox(left, textvariable=self.tam, values=[core.ALL_TAMBON] + self.db.tambons(), state="readonly", font=self.F)
        cb.pack(fill="x", pady=3)
        cb.bind("<<ComboboxSelected>>", lambda ev: self.refill())
        self.only = tk.BooleanVar()
        ttk.Checkbutton(left, text="เฉพาะที่ยังไม่บันทึก", variable=self.only, command=self.refill, style="Rec.TCheckbutton").pack(anchor="w")
        fr = ttk.Frame(left)
        fr.pack(fill="both", expand=True)
        self.lb = tk.Listbox(fr, width=34, exportselection=False, font=self.FL, activestyle="none", bg="white", fg="#1B2A4A", selectbackground=luna.BLUE_SEL, selectforeground="white",
                           highlightthickness=1, highlightbackground=luna.LINE_D, relief="flat", borderwidth=0)
        sc = ttk.Scrollbar(fr, command=self.lb.yview)
        self.lb.config(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda ev: self.on_select())
        self.prog = ttk.Label(left, text="", style="Rec.TLabel")
        self.prog.pack(anchor="w")
        vs = VScroll(self)
        vs.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(vs.inner, padding=10)
        right.pack(fill="both", expand=True)
        self.saved = tk.Label(right, text="", fg="#15803D", bg=BG, font=self.FB, anchor="w", padx=8)
        self.saved.pack(fill="x", pady=(0, 6))          # แถบข้อความ "บันทึกข้อมูลแล้ว" อยู่บนสุด มองเห็นเสมอ
        self._saved_job = None
        self.head = ttk.Label(right, text="— เลือกรายชื่อทางซ้าย —", font=self.FH)
        self.head.pack(anchor="w")
        self.sub = ttk.Label(right, text="", wraplength=700, style="Rec.TLabel")
        right.bind("<Configure>", lambda e: self.sub.config(wraplength=max(300, e.width - 30)))
        self.sub.pack(anchor="w", pady=(0, 8))
        g = ttk.Frame(right)
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)
        self.v = {k: tk.StringVar() for k in ("result", "occ", "detail", "place", "province", "amphoe2", "tel", "tel_par", "tel_work")}
        r = 0
        ttk.Label(g, text="ผลการตรวจ", style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
        rf = ttk.Frame(g)
        rf.grid(row=r, column=1, sticky="we")
        ttk.Radiobutton(rf, text="มีตัว", value="มีตัว", variable=self.v["result"], style="Rec.TRadiobutton").pack(side="left", padx=6)
        ttk.Radiobutton(rf, text="ไม่มีตัว", value="ไม่มีตัว", variable=self.v["result"], style="Rec.TRadiobutton").pack(side="left", padx=6)
        r += 1
        ttk.Label(g, text="อาชีพ/สถานภาพ", style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
        self.occ = ttk.Combobox(g, textvariable=self.v["occ"], values=core.OCCUPATIONS, width=18, font=self.F)
        self.occ.grid(row=r, column=1, sticky="we")
        self.occ.bind("<<ComboboxSelected>>", lambda ev: self.occ_changed())
        r += 1
        ttk.Label(g, text="รายละเอียด ( )", style="Rec.TLabel").grid(row=r, column=0, sticky="w")
        self.det = ttk.Entry(g, textvariable=self.v["detail"], width=18, state="disabled", font=self.F)
        self.det.grid(row=r, column=1, sticky="we", pady=3)
        r += 1
        ttk.Label(g, text="สถานที่", style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
        pf = ttk.Frame(g)
        pf.grid(row=r, column=1, sticky="we")
        ttk.Entry(pf, textvariable=self.v["place"], width=14, font=self.F).pack(fill="x")
        ttk.Button(pf, text="ใส่ตามภูมิลำเนา", command=self.domicile, style="Rec.TButton").pack(anchor="w", pady=3)
        r += 1
        ttk.Label(g, text="จังหวัด", style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
        self.cp = ttk.Combobox(g, textvariable=self.v["province"], values=sorted(GEO), width=18, font=self.F)
        self.cp.grid(row=r, column=1, sticky="we")
        self.cp.bind("<<ComboboxSelected>>", lambda ev: self.prov_changed())
        r += 1
        ttk.Label(g, text="อำเภอ / เขต", style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
        self.ca = ttk.Combobox(g, textvariable=self.v["amphoe2"], width=18, font=self.F)
        self.ca.grid(row=r, column=1, sticky="we")
        for k, lab in (("tel", "โทรศัพท์ (เจ้าตัว)"), ("tel_par", "โทรศัพท์ (ผู้ปกครอง)"), ("tel_work", "โทรศัพท์ (ที่ทำงาน)")):
            r += 1
            ttk.Label(g, text=lab, style="Rec.TLabel").grid(row=r, column=0, sticky="w", pady=6)
            ttk.Entry(g, textvariable=self.v[k], width=18, font=self.F).grid(row=r, column=1, sticky="we")
        bt = ttk.Frame(right)
        bt.pack(fill="x", pady=14)
        ttk.Button(bt, text="◀ ก่อนหน้า", command=lambda: self.step(-1), style="Rec.TButton").pack(side="left")
        ttk.Button(bt, text="ถัดไป ▶", command=lambda: self.step(1), style="Rec.TButton").pack(side="left", padx=4)
        ttk.Button(bt, text="บันทึก", style="Rec.Accent.TButton", command=lambda: self.save(False)).pack(side="left", padx=14)
        ttk.Button(bt, text="บันทึกแล้วไปคนต่อไป", style="Rec.Accent.TButton", command=lambda: self.save(True)).pack(side="left")
        ttk.Button(bt, text="ล้างผลคนนี้", command=self.clear_one, style="Rec.TButton").pack(side="right")
        self.view = []
        self.refill()
        e.focus_set()
        self.bind("<Configure>", self._rescale)

    def _rescale(self, ev):
        """ขยาย/ย่อฟอนต์และปุ่มตามขนาดหน้าต่างอัตโนมัติ (0.9x - 1.5x) เพื่อให้อ่านง่ายทั้งจอใหญ่และแท็บเล็ต"""
        if ev.widget is not self:
            return
        self.lb.config(width=24 if ev.width < 1000 else 34)
        k = round(max(0.9, min(1.5, min(ev.width / 1000.0, ev.height / 640.0))) * 10) / 10
        if k == self._k:
            return
        self._k = k
        self.F.configure(size=round(11 * k))
        self.FL.configure(size=round(11 * k))
        self.FB.configure(size=round(13 * k))
        self.FH.configure(size=round(18 * k))
        stl = ttk.Style()
        stl.configure("Rec.TButton", padding=(round(12 * k), round(7 * k)))
        stl.configure("Rec.Accent.TButton", padding=(round(14 * k), round(8 * k)))

    # ---- รายการ
    def refill(self):
        q = self.q.get()
        base = self.db.select(core.ALL_TYPES, self.tam.get())
        if q.strip():
            ids = {id(p) for p in self.db.find(q)}
            base = [p for p in base if id(p) in ids]
        if self.only.get():
            base = [p for p in base if not self.db.filled(p)]
        self.view = base
        self.lb.delete(0, "end")
        for p in base:
            self.lb.insert("end", " %s%s %s  ม.%s ต.%s" % (p["rank"], p["name"], p["surname"], p["moo"], p["tambon"]))
            if self.db.filled(p):                      # บันทึกแล้ว = ตัวอักษรสีเขียว (ไม่ใช้สัญลักษณ์ ✓ ที่ฟอนต์ไทยไม่มี)
                self.lb.itemconfig("end", fg="#1B7F3B")
        done = sum(1 for p in self.db.persons if self.db.filled(p))
        self.prog.config(text="บันทึกแล้ว %d / %d คน" % (done, len(self.db.persons)))

    def pick_first(self):
        if self.view:
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(0)
            self.on_select()

    def on_select(self):
        s = self.lb.curselection()
        if s:
            self.load(self.view[s[0]])

    def step(self, d):
        s = self.lb.curselection()
        i = (s[0] if s else -1) + d
        if 0 <= i < len(self.view):
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(i)
            self.lb.see(i)
            self.load(self.view[i])

    # ---- ฟอร์ม
    def load(self, p):
        self.cur = p
        self.head.config(text="%s%s  %s" % (p["rank"], p["name"], p["surname"]))
        self.sub.config(text="เลขบัตร %s   |   %s ม.%s ต.%s อ.%s จ.%s   |   %s" % (
            p["nid"], p["house"], p["moo"], p["tambon"], p["amphoe"], p["province"], p["type"]))
        self.v["result"].set(p.get("result", ""))
        st = p.get("status", "")
        occ, det = st, ""
        import re
        m = re.match(r"^(.*?)\s*\((.*)\)$", st)
        if m and (m.group(1) + " ( )") in core.OCCUPATIONS:
            occ, det = m.group(1) + " ( )", m.group(2)
        self.v["occ"].set(occ)
        self.v["detail"].set(det)
        self.v["place"].set(p.get("place", ""))
        self.v["province"].set(p.get("prov2", ""))
        self.prov_changed(keep=p.get("amphoe2", ""))
        for k in ("tel", "tel_par", "tel_work"):
            self.v[k].set(p.get(k, ""))
        self.occ_changed()

    def occ_changed(self):
        self.det.config(state="normal" if self.v["occ"].get().endswith("( )") else "disabled")

    def prov_changed(self, keep=None):
        self.ca["values"] = GEO.get(self.v["province"].get(), [])
        self.v["amphoe2"].set(keep if keep is not None else "")

    def domicile(self):
        p = self.cur
        if not p:
            return
        self.v["place"].set("%s ม.%s ต.%s" % (p["house"], p["moo"], p["tambon"]))      # เฉพาะบ้านเลขที่ หมู่ ตำบล (จังหวัด/อำเภอไม่แตะ)

    def save(self, nxt):
        p = self.cur
        if not p:
            return
        if not self.v["result"].get():
            return err("เลือก มีตัว / ไม่มีตัว ก่อน")
        occ = self.v["occ"].get().strip()
        if occ.endswith("( )"):
            d = self.v["detail"].get().strip()
            occ = occ[:-3].strip() + (" (%s)" % d if d else "")
        p["result"] = self.v["result"].get()
        p["status"] = occ
        p["place"] = self.v["place"].get().strip()
        p["prov2"] = self.v["province"].get().strip()
        p["amphoe2"] = self.v["amphoe2"].get().strip()
        for k in ("tel", "tel_par", "tel_work"):
            p[k] = self.v[k].get().strip()
        self.db.save()
        self.flash("✔ บันทึกข้อมูลแล้ว: %s %s %s" % (p.get("rank", ""), p["name"], p["surname"]))
        i = self.lb.curselection()[0] if self.lb.curselection() else -1
        self.refill()
        self.app.refresh_status()
        if i >= 0:
            j = min(i + (1 if nxt else 0), len(self.view) - 1)
            if self.only.get() and not nxt:
                j = min(i, len(self.view) - 1)
            if 0 <= j:
                self.lb.selection_set(j)
                self.lb.see(j)
                self.load(self.view[j])

    def flash(self, text, ms=4000):
        self.saved.config(text=text, bg="#E7F6EC")
        if self._saved_job:
            self.after_cancel(self._saved_job)
        self._saved_job = self.after(ms, lambda: self.saved.winfo_exists() and self.saved.config(text="", bg=BG))

    def clear_one(self):
        p = self.cur
        if p and messagebox.askyesno("ยืนยัน", "ล้างผลของ %s %s ?" % (p["name"], p["surname"])):
            for k in core.RESULT_FIELDS:
                p[k] = ""
            self.db.save()
            self.refill()
            self.load(p)
            self.app.refresh_status()


# ====================================================================== 2/4/5) พิมพ์
class PrintWin(Page):
    TITLES = {"reg": "จัดพิมพ์บัญชีตรวจสอบสภาพ", "sum": "บัญชีสรุปผลการตรวจสอบ", "send": "ส่งข้อมูลให้ผู้ใหญ่บ้านตรวจสอบ",
              "form": "แบบพิมพ์รายบุคคล", "env": "จ่าหน้าซอง (ด้านหลัง A4)"}

    def __init__(self, app, kind):
        super().__init__(app)
        self.title(self.TITLES[kind])
        self.geometry("860x700")
        self.app, self.db, self.kind = app, app.db, kind
        self.cancel = False
        self.busy = False
        self.q = queue.Queue()
        self.cfg = {}
        g = ttk.Frame(self, padding=10)
        g.pack(fill="x")
        self.ptype = tk.StringVar(value=core.ALL_TYPES)
        self.level = tk.StringVar(value="อำเภอ")
        self.tam = tk.StringVar(value=core.ALL_TAMBON)
        self.moo = tk.StringVar(value="ทั้งหมด")
        self.copies = tk.IntVar(value=1)
        self.delay = tk.DoubleVar(value=float(app.st.get("delay", 5)))
        self.only = tk.BooleanVar()
        self.printer = tk.StringVar(value=app.st.get("printer") or render.default_printer())
        r = 0
        ttk.Label(g, text="ประเภททหาร").grid(row=r, column=0, sticky="w", pady=3)
        self.cptype = ttk.Combobox(g, textvariable=self.ptype, values=[core.ALL_TYPES] + self.db.types_present(), state="readonly", width=40)
        self.cptype.grid(row=r, column=1, sticky="w")
        self.cptype.bind("<<ComboboxSelected>>", lambda e: self.upd())
        if kind == "form":
            r += 1
            ttk.Label(g, text="ชนิดงานพิมพ์").grid(row=r, column=0, sticky="w", pady=3)
            self.sub = tk.StringVar(value="แบบพิมพ์ (A4 แนวตั้ง 1 หน้า/คน)")
            cs = ttk.Combobox(g, textvariable=self.sub, state="readonly", width=40,
                              values=["แบบพิมพ์ (A4 แนวตั้ง 1 หน้า/คน)", "จ่าหน้าซอง (DL 220×110 มม. 1 ซอง/คน)"])
            cs.grid(row=r, column=1, sticky="w")
            cs.bind("<<ComboboxSelected>>", lambda e: self.set_sub())
        elif kind != "send":
            r += 1
            ttk.Label(g, text="ผู้ลงนามระดับ").grid(row=r, column=0, sticky="w", pady=3)
            ttk.Combobox(g, textvariable=self.level, values=core.LEVELS, state="readonly", width=12).grid(row=r, column=1, sticky="w")
        else:
            r += 1
            ttk.Label(g, text="ผู้ลงนาม").grid(row=r, column=0, sticky="w")
            ttk.Label(g, text="ระดับอำเภอ (ข้อความ “ตรวจถูกต้อง”)").grid(row=r, column=1, sticky="w")
        r += 1
        ttk.Label(g, text="ตำบล").grid(row=r, column=0, sticky="w", pady=3)
        self.ctam = ttk.Combobox(g, textvariable=self.tam, values=[core.ALL_TAMBON] + self.db.tambons_for(), state="readonly", width=20)
        self.ctam.grid(row=r, column=1, sticky="w")
        self.ctam.bind("<<ComboboxSelected>>", lambda e: self.upd())
        r += 1
        ttk.Label(g, text="หมู่ที่").grid(row=r, column=0, sticky="w", pady=3)
        self.cmoo = ttk.Combobox(g, textvariable=self.moo, values=["ทั้งหมด"] + self.db.moos_for(), state="readonly", width=20)
        self.cmoo.grid(row=r, column=1, sticky="w")
        self.cmoo.bind("<<ComboboxSelected>>", lambda e: self.upd())
        r += 1
        ttk.Label(g, text="จำนวนชุด/ฉบับ").grid(row=r, column=0, sticky="w", pady=3)
        o = ttk.Frame(g)
        o.grid(row=r, column=1, sticky="w")
        Spin(o, from_=1, to=20, textvariable=self.copies, width=5).pack(side="left")
        ttk.Label(o, text="   หน่วงระหว่างชุด (วินาที)").pack(side="left")
        Spin(o, from_=0, to=120, textvariable=self.delay, width=5).pack(side="left")
        ttk.Checkbutton(o, text="เฉพาะที่ยังไม่พิมพ์", variable=self.only, command=self.upd).pack(side="left", padx=12)
        r += 1
        ttk.Label(g, text="เครื่องพิมพ์").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Combobox(g, textvariable=self.printer, values=render.list_printers(), width=50).grid(row=r, column=1, sticky="w")
        self.info = ttk.Label(self, text="", padding=(10, 0))
        self.info.pack(anchor="w")
        bf = ttk.Frame(self, padding=10)
        bf.pack(fill="x")
        btns = [("ดูตัวอย่าง", self.preview, "TButton")]
        if kind == "send":
            btns += [("พิมพ์หมู่ที่เลือก", lambda: self.go("sel"), "Accent.TButton"), ("พิมพ์ทีละหมู่", lambda: self.go("moo"), "Accent.TButton")]
        else:
            btns += [("พิมพ์ที่เลือก (1 ชุด เรียงหมู่)", lambda: self.go("sel"), "Accent.TButton"), ("พิมพ์ทีละตำบล", lambda: self.go("tam"), "Accent.TButton")]
        for txt, cmd, stl in btns:
            ttk.Button(bf, text=txt, command=cmd, style=stl).pack(side="left", padx=3)
        ttk.Button(bf, text="ยกเลิก (Esc)", command=self.stop).pack(side="right", padx=3)
        ttk.Button(bf, text="ล้างสถานะพิมพ์แล้ว", command=self.reset_marks).pack(side="right", padx=3)
        self.log = make_log(self, height=18)
        self.log.pack(fill="both", expand=True, padx=10, pady=6)
        self.bind("<Escape>", lambda e: self.stop())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.upd()
        self.pump()

    def refresh_lists(self):
        """รายการตำบล/หมู่ แสดงเฉพาะที่มีคนตามประเภทที่เลือก"""
        pt = self.ptype.get()
        self.ctam["values"] = [core.ALL_TAMBON] + self.db.tambons_for(pt)
        if self.tam.get() not in self.ctam["values"]:
            self.tam.set(core.ALL_TAMBON)
        self.cmoo["values"] = ["ทั้งหมด"] + self.db.moos_for(pt, self.tam.get())
        if self.moo.get() not in self.cmoo["values"]:
            self.moo.set("ทั้งหมด")

    def set_sub(self):
        self.kind = "env" if self.sub.get().startswith("จ่าหน้า") else "form"
        self.upd()

    def post(self, fn, *a):
        self.q.put((fn, a))

    def pump(self):
        try:
            while True:
                fn, a = self.q.get_nowait()
                fn(*a)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(150, self.pump)

    # ---- ช่วย
    def mark_key(self):
        return self.kind if self.kind in ("sum", "send", "form", "env") else "reg_" + self.level.get()

    def sel(self, tam=None, moo=None):
        return self.db.select(self.ptype.get(), tam or self.tam.get(), moo if moo is not None else (None if self.moo.get() == "ทั้งหมด" else self.moo.get()),
                              self.mark_key() if self.only.get() else None)

    def upd(self):
        self.refresh_lists()
        t = self.tam.get()
        rows = self.sel()
        done = sum(1 for p in self.db.select(self.ptype.get(), t, None if self.moo.get() == "ทั้งหมด" else self.moo.get()) if self.mark_key() in p.get("printed", {}))
        self.info.config(text="ตรงเงื่อนไข %d คน  |  (พิมพ์แล้ว %d คน ในช่วงที่เลือก)" % (len(rows), done))

    def say(self, s):
        line = "[%s] %s\n" % (time.strftime("%H:%M:%S"), s)
        self.post(self._say, line)
        try:
            with open(os.path.join(core.data_dir(), "PrintLog.txt"), "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass

    def _say(self, line):
        log_line(self.log, line)

    def stop(self):
        if self.busy:
            self.cancel = True
            self.say("กำลังยกเลิก…")

    def close(self):
        if self.busy:
            return messagebox.showinfo("กำลังพิมพ์", "กด ยกเลิก ก่อนปิดหน้าต่าง")
        self.destroy()

    def reset_marks(self):
        if messagebox.askyesno("ยืนยัน", "ล้างสถานะ “พิมพ์แล้ว” ของแบบนี้ (%s) ทั้งหมด?\nใช้เมื่อกระดาษเสีย/ต้องการพิมพ์ซ้ำ" % self.mark_key()):
            self.db.clear_printed([self.mark_key()])
            self.upd()

    def pages_for(self, persons, tam):
        st = dict(self.app.st)
        c = self.cfg or {"ptype": self.ptype.get(), "level": self.level.get()}
        return layout.build(self.kind, persons, st, c["ptype"], tam, c["level"])

    def preview(self):
        rows = self.sel()
        if not rows:
            return err("ไม่มีรายชื่อตามเงื่อนไข")
        tam = self.tam.get() if self.tam.get() != core.ALL_TAMBON else ""
        pages = self.pages_for(rows, tam)
        PreviewWin(self.app, pages, self.TITLES[self.kind])

    # ---- พิมพ์
    def jobs(self, mode):
        t = self.tam.get()
        moo = None if self.moo.get() == "ทั้งหมด" else self.moo.get()
        if mode == "sel":
            rows = self.sel()
            return [("%s%s" % (t, (" หมู่ " + moo) if moo else ""), rows, "" if t == core.ALL_TAMBON else t)] if rows else []
        tams = self.db.tambons() if t == core.ALL_TAMBON else [t]
        out = []
        for tm in tams:
            if mode == "tam":
                rows = self.sel(tm)
                if rows:
                    out.append(("ตำบล" + tm, rows, tm))
            else:
                for m in self.db.moos(tm):
                    rows = self.sel(tm, m)
                    if rows:
                        out.append(("ตำบล%s หมู่ %s" % (tm, m), rows, tm))
        return out

    def go(self, mode):
        if self.busy:
            return
        jobs = self.jobs(mode)
        if not jobs:
            return err("ไม่มีรายชื่อตามเงื่อนไข")
        if self.kind in ("form", "env"):
            st = self.app.st
            miss = [n for k, n in (("sad_tel", "เบอร์โทรสัสดี"), ("deadline", "วันส่งคืน")) if not st.get(k)] if self.kind == "form" else \
                   [n for k, n in (("unit_province", "จังหวัดของหน่วย"),) if not (st.get(k) or st.get("province"))]
            if miss and not messagebox.askyesno("ข้อมูลยังไม่ครบ", "ยังไม่ได้กรอกในตั้งค่า: %s\nจะพิมพ์ช่องนั้นเป็นค่าว่าง ต้องการพิมพ์ต่อไหม?" % ", ".join(miss)):
                return
        if os.name != "nt":
            return err("การพิมพ์ใช้ได้เฉพาะบน Windows (ดูตัวอย่างใช้ได้ทุกระบบ)")
        if not messagebox.askyesno("ยืนยัน", "จะพิมพ์ %d ชุด รวม %d คน × %d ฉบับ\nเครื่องพิมพ์: %s\nเริ่มเลยไหม?" % (
                len(jobs), sum(len(j[1]) for j in jobs), self.copies.get(), self.printer.get() or "(ค่าเริ่มต้น)")):
            return
        self.app.st["printer"] = self.printer.get()
        core.save_settings(self.app.st)
        self.cfg = {"ptype": self.ptype.get(), "level": self.level.get(), "printer": self.printer.get(),
                    "copies": self.copies.get(), "delay": float(self.delay.get()), "key": self.mark_key()}
        self.cancel, self.busy = False, True
        threading.Thread(target=self.worker, args=(jobs,), daemon=True).start()

    def worker(self, jobs):
        form = layout.FORMS[self.kind]
        key = self.cfg["key"]
        try:
            for n, (label, rows, tam) in enumerate(jobs, 1):
                if self.cancel:
                    break
                self.say("ชุดที่ %d/%d: %s (%d คน)" % (n, len(jobs), label, len(rows)))
                pages = self.pages_for(rows, tam)
                gp = render.GdiPrinter(self.cfg["printer"], form["paper"], form["landscape"], self.font(), self.cfg["copies"])
                try:
                    gp.print_doc(pages, "ZAIA %s %s" % (self.kind, label), lambda: self.cancel)
                finally:
                    gp.close()
                if self.cancel:
                    self.say("ยกเลิกระหว่างชุดนี้ — ไม่ทำเครื่องหมายพิมพ์แล้ว")
                    break
                self.post(self.db.mark_printed, rows, key)
                self.say("ส่งพิมพ์แล้ว %d หน้า" % len(pages))
                if n < len(jobs):
                    t_end = time.time() + self.cfg["delay"]
                    while time.time() < t_end and not self.cancel:
                        time.sleep(0.2)
            self.say("เสร็จสิ้น" if not self.cancel else "หยุดแล้ว")
        except Exception as e:
            self.say("ผิดพลาด: %s" % e)
            self.post(err, "พิมพ์ไม่สำเร็จ:\n%s" % e)
        finally:
            self.busy = False
            self.post(self.upd)

    def font(self):
        return self.app.font_family()


class PersonalWin(PrintWin):
    """เมนู 2: แบบพิมพ์รายบุคคล + จ่าหน้าซอง — หน้าจอเดียว 3 ขั้น เลือกคน -> เลือกสิ่งที่พิมพ์ -> พิมพ์"""

    def __init__(self, app):
        Page.__init__(self, app)
        self.app, self.db, self.kind = app, app.db, "form"
        self.title("แบบพิมพ์รายบุคคล + จ่าหน้าซอง")
        self.cancel, self.busy, self.cfg = False, False, {}
        self.q = queue.Queue()
        self.ptype = tk.StringVar(value=core.ALL_TYPES)
        self.tam = tk.StringVar(value=core.ALL_TAMBON)
        self.moo = tk.StringVar(value="ทั้งหมด")
        self.only = tk.BooleanVar()
        self.do_form, self.do_env = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        self.copies = tk.IntVar(value=1)
        self.printer = tk.StringVar(value=app.st.get("printer") or render.default_printer())
        self.eprinter = tk.StringVar(value=app.st.get("env_printer", ""))
        self.delay = tk.DoubleVar(value=0)
        self.level = tk.StringVar(value="อำเภอ")
        f = app.ui_font
        sc = VScroll(self)
        sc.pack(fill="both", expand=True)
        body = ttk.Frame(sc.inner, padding=12)
        body.pack(fill="both", expand=True)

        def step(n, t):
            ttk.Label(body, text="ขั้นที่ %s  %s" % (n, t), font=(f, 13, "bold")).pack(anchor="w", pady=(10, 4))

        step(1, "เลือกคนที่จะพิมพ์")
        g = ttk.Frame(body)
        g.pack(anchor="w")
        ttk.Label(g, text="ประเภททหาร").grid(row=0, column=0, sticky="w", pady=3)
        self.cptype = ttk.Combobox(g, textvariable=self.ptype, values=[core.ALL_TYPES] + self.db.types_present(), state="readonly", width=36)
        self.cptype.grid(row=0, column=1, sticky="w", padx=8)
        self.cptype.bind("<<ComboboxSelected>>", lambda e: self.upd())
        ttk.Label(g, text="ตำบล").grid(row=1, column=0, sticky="w", pady=3)
        self.ctam = ttk.Combobox(g, textvariable=self.tam, values=[core.ALL_TAMBON] + self.db.tambons_for(), state="readonly", width=20)
        self.ctam.grid(row=1, column=1, sticky="w", padx=8)
        self.ctam.bind("<<ComboboxSelected>>", lambda e: self.upd())
        ttk.Label(g, text="หมู่ที่").grid(row=2, column=0, sticky="w", pady=3)
        self.cmoo = ttk.Combobox(g, textvariable=self.moo, values=["ทั้งหมด"] + self.db.moos_for(), state="readonly", width=20)
        self.cmoo.grid(row=2, column=1, sticky="w", padx=8)
        self.cmoo.bind("<<ComboboxSelected>>", lambda e: self.upd())
        ttk.Checkbutton(g, text="เฉพาะคนที่ยังไม่เคยพิมพ์", variable=self.only, command=self.upd).grid(row=3, column=1, sticky="w", padx=8, pady=3)
        self.info = ttk.Label(body, text="", font=(f, 14, "bold"), foreground=GREEN)
        self.info.pack(anchor="w", pady=(6, 0))

        step(2, "เลือกสิ่งที่จะพิมพ์")
        r2 = ttk.Frame(body)
        r2.pack(anchor="w")
        ttk.Checkbutton(r2, text="แบบพิมพ์รายบุคคล (A4 แนวตั้ง 1 หน้า/คน)", variable=self.do_form, command=self.upd).pack(anchor="w")
        ttk.Checkbutton(r2, text="จ่าหน้าซอง (พิมพ์ด้านหลัง A4 ของแบบพิมพ์ แล้วพับสามส่งไปรษณีย์)", variable=self.do_env, command=self.upd).pack(anchor="w")
        o = ttk.Frame(body)
        o.pack(anchor="w", pady=(4, 0))
        ttk.Label(o, text="จำนวนฉบับ/ชุด").pack(side="left")
        Spin(o, from_=1, to=20, textvariable=self.copies, width=5).pack(side="left", padx=6)
        self.warn = ttk.Label(body, text="", foreground="#C2410C", wraplength=640, justify="left")
        self.warn.pack(anchor="w", pady=(6, 0))
        ttk.Button(body, text="ไปแก้ข้อมูลหน่วย/เบอร์โทร/วันส่งคืนที่ตั้งค่า", command=lambda: app.nav("settings")).pack(anchor="w", pady=2)

        step(3, "เลือกเครื่องพิมพ์ แล้วกดพิมพ์")
        g2 = ttk.Frame(body)
        g2.pack(anchor="w")
        ttk.Label(g2, text="เครื่องพิมพ์ (แบบพิมพ์)").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(g2, textvariable=self.printer, values=render.list_printers(), width=46).grid(row=0, column=1, padx=8)
        ttk.Label(g2, text="ถ้าติ๊กทั้งสองอย่าง โปรแกรมพิมพ์แบบพิมพ์ก่อน แล้วให้พลิกกระดาษใส่ใหม่เพื่อพิมพ์ซองด้านหลัง", foreground="#555").grid(row=1, column=0, columnspan=2, sticky="w", pady=3)
        bf = ttk.Frame(body)
        bf.pack(anchor="w", pady=10)
        ttk.Button(bf, text="ดูตัวอย่างแบบพิมพ์", command=lambda: self.preview("form")).pack(side="left", padx=3)
        ttk.Button(bf, text="ดูตัวอย่างซอง", command=lambda: self.preview("env")).pack(side="left", padx=3)
        ttk.Button(bf, text="พิมพ์ทดสอบ 1 คน", command=lambda: self.go(True)).pack(side="left", padx=3)
        ttk.Button(bf, text="พิมพ์ทั้งหมดที่เลือก", style="Accent.TButton", command=lambda: self.go(False)).pack(side="left", padx=3)
        ttk.Button(bf, text="ยกเลิก (Esc)", command=self.stop).pack(side="left", padx=12)
        ttk.Button(body, text="ล้างสถานะ “พิมพ์แล้ว” ของงานนี้", command=self.reset_marks).pack(anchor="w")
        self.log = make_log(body, height=9)
        self.log.pack(fill="x", pady=8)
        self.bind("<Escape>", lambda e: self.stop())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.upd()
        self.pump()

    def keys(self):
        return [k for k, v in (("form", self.do_form), ("env", self.do_env)) if v.get()]

    def mark_key(self):
        return (self.keys() or ["form"])[0]

    def sel(self, key=None, tam=None):
        return self.db.select(self.ptype.get(), tam or self.tam.get(), None if self.moo.get() == "ทั้งหมด" else self.moo.get(),
                              (key or self.mark_key()) if self.only.get() else None)

    def upd(self):
        self.refresh_lists()
        rows = self.sel()
        k = self.keys()
        self.info.config(text="จะพิมพ์ %d คน%s" % (len(rows), ("  →  %d หน้า/ใบ" % (len(rows) * len(k))) if k else "  (ยังไม่ได้เลือกสิ่งที่จะพิมพ์)"))
        st = self.app.st
        miss = []
        if self.do_form.get():
            miss += [n for key, n in (("sad_tel", "เบอร์โทรสัสดี"), ("deadline", "วันที่ส่งคืน")) if not st.get(key)]
        if self.do_env.get() and not (st.get("unit_province") or st.get("province")):
            miss.append("จังหวัดของหน่วย")
        self.warn.config(text=("⚠ ยังไม่ได้กรอกในตั้งค่า: " + ", ".join(miss) + " (ช่องนั้นจะว่าง)") if miss else "")

    def preview(self, kind):
        rows = self.sel(kind)
        if not rows:
            return err("ไม่มีรายชื่อตามเงื่อนไข")
        PreviewWin(self.app, layout.build(kind, rows, dict(self.app.st), self.ptype.get(), "", "อำเภอ"), self.TITLES[kind])

    def reset_marks(self):
        if messagebox.askyesno("ยืนยัน", "ล้างสถานะ “พิมพ์แล้ว” ของแบบพิมพ์และซองทั้งหมด?"):
            self.db.clear_printed(["form", "env"])
            self.upd()

    def go(self, test):
        if self.busy:
            return
        if not self.keys():
            return err("ติ๊กเลือกสิ่งที่จะพิมพ์ก่อน (แบบพิมพ์ และ/หรือ ซอง)")
        jobs = []
        for k in self.keys():
            rows = self.sel(k)
            if test:
                rows = rows[:1]
            if rows:
                jobs.append((k, rows))
        if not jobs:
            return err("ไม่มีรายชื่อตามเงื่อนไข")
        if os.name != "nt":
            return err("การพิมพ์ใช้ได้เฉพาะบน Windows (ดูตัวอย่างใช้ได้ทุกระบบ)")
        txt = "\n".join("%s %d ใบ/หน้า × %d ฉบับ" % (self.TITLES[k], len(r), self.copies.get()) for k, r in jobs)
        if not messagebox.askyesno("ยืนยัน", "%s\nเริ่มพิมพ์เลยไหม?" % txt):
            return
        self.app.st["printer"], self.app.st["env_printer"] = self.printer.get(), self.eprinter.get()
        core.save_settings(self.app.st)
        self.cancel, self.busy = False, True
        threading.Thread(target=self.worker2, args=(jobs, test), daemon=True).start()

    def worker2(self, jobs, test):
        st = dict(self.app.st)
        n_done = 0
        try:
            for k, rows in jobs:
                if self.cancel:
                    break
                form = layout.FORMS[k]
                pr = self.printer.get()
                if k == "env" and n_done:
                    ev = threading.Event()
                    self.post(self._flip, ev)
                    ev.wait()
                    if self.cancel:
                        break
                self.say("%s: %d ใบ/หน้า → %s" % (self.TITLES[k], len(rows), pr or "(เครื่องพิมพ์เริ่มต้น)"))
                pages = layout.build(k, rows, st, self.ptype.get(), "", "อำเภอ")
                gp = render.GdiPrinter(pr, form["paper"], form["landscape"], self.app.font_family(), self.copies.get())
                try:
                    gp.print_doc(pages, "ZAIA %s" % k, lambda: self.cancel)
                finally:
                    gp.close()
                if self.cancel:
                    self.say("ยกเลิกระหว่างงานนี้ — ไม่ทำเครื่องหมายพิมพ์แล้ว")
                    break
                if not test:
                    self.post(self.db.mark_printed, rows, k)
                self.say("ส่งพิมพ์แล้ว %d หน้า" % len(pages))
                n_done += 1
            self.say("เสร็จสิ้น" if not self.cancel else "หยุดแล้ว")
        except Exception as e:
            self.say("ผิดพลาด: %s" % e)
            self.post(err, "พิมพ์ไม่สำเร็จ:\n%s" % e)
        finally:
            self.busy = False
            self.post(self.upd)

    def _flip(self, ev):
        if not messagebox.askokcancel("พลิกกระดาษ", "แบบพิมพ์พิมพ์เสร็จแล้ว\nให้นำกระดาษชุดนั้นพลิกด้านใส่ถาดใหม่ (เรียงลำดับเดิม) แล้วกด OK เพื่อพิมพ์จ่าหน้าซองด้านหลัง"):
            self.cancel = True
        ev.set()


# ====================================================================== อัปเดต
class UpdateWin(Page):
    def __init__(self, app):
        super().__init__(app)
        self.title("ตรวจสอบอัปเดต")
        self.geometry("620x420")
        self.app = app
        self.url = tk.StringVar(value=app.st.get("update_url") or UPDATE_BASE)
        self.m = None
        ttk.Label(self, text="รุ่นปัจจุบัน %s" % APP_VER, padding=8).pack(anchor="w")
        f = ttk.Frame(self, padding=(8, 0))
        f.pack(fill="x")
        ttk.Label(f, text="ลิงก์ (GitHub Raw):").pack(side="left")
        ttk.Entry(f, textvariable=self.url, width=60).pack(side="left", padx=4)
        ttk.Button(self, text="ตรวจสอบ", command=self.check).pack(pady=6)
        self.box = make_log(self, height=14)
        self.box.pack(fill="both", expand=True, padx=8)
        self.btn = ttk.Button(self, text="ดาวน์โหลดและอัปเดต", command=self.apply, state="disabled")
        self.btn.pack(pady=8)

    def put(self, s):
        log_set(self.box, s)

    @staticmethod
    def _ver(v):
        try:
            return tuple(int(x) for x in str(v).split("."))
        except ValueError:
            return (0,)

    def changes(self, m, since=None, limit=None):
        """ข้อความรายการสิ่งที่ปรับ จาก changelog ใน update.json  since=แสดงเฉพาะรุ่นที่ใหม่กว่านี้"""
        cl = [c for c in (m.get("changelog") or []) if since is None or self._ver(c["version"]) > self._ver(since)]
        cl = cl[:limit] if limit else cl
        if not cl:
            return m.get("notes", "")
        return "\n".join("▶ รุ่น %s\n%s\n" % (c["version"], "\n".join("  • " + t for t in c["items"])) for c in cl)

    def check(self):
        self.btn.config(state="disabled")
        try:
            self.m, self.base = updater.fetch_manifest(self.url.get().strip())
        except Exception as e:
            return self.put("ผิดพลาด: %s\n\nวางลิงก์ใหม่ในช่องด้านบนแล้วกด ตรวจสอบ อีกครั้ง" % e)
        m = self.m
        self.mode = "files"
        if updater.has_patch(m):        # แพตช์โค้ดออนไลน์ (ไม่ต้องติดตั้ง Setup ใหม่)
            self.mode = "patch"
            pv = m["patch"]
            if self._ver(pv["version"]) <= self._ver(APP_VER):
                self.put("เป็นรุ่นล่าสุดแล้ว (%s)\n\nประวัติการอัปเดตล่าสุด:\n%s" % (APP_VER, self.changes(m, limit=5)))
                return
            self.put("มีแพตช์รุ่น %s (ปัจจุบัน %s)\nไฟล์โค้ด %d ไฟล์ จะดาวน์โหลดทั้งชุดและตรวจ SHA-256 ก่อนใช้งาน\nหลังอัปเดตโปรแกรมจะเปิดใหม่เอง\n\nสิ่งที่ปรับในรุ่นนี้:\n%s" % (
                pv["version"], APP_VER, len(pv["files"]), self.changes(m, since=APP_VER)))
            self.btn.config(state="normal")
            return
        if not updater.is_newer(m):
            return self.put("เป็นรุ่นล่าสุดแล้ว (%s)\n\nประวัติการอัปเดตล่าสุด:\n%s" % (APP_VER, self.changes(m, limit=5)))
        self.todo = updater.plan(m)      # อัปเดตได้เสมอ ไม่ว่ารุ่นห่างแค่ไหน (เทียบ hash ทุกไฟล์) setup_rev เป็นแค่คำแนะนำ
        extra = ("\n\n(แนะนำ: รุ่นนี้มี Setup ใหม่ %s)" % m.get("setup_url", "")) if updater.needs_setup(m) else ""
        if not self.todo:
            return self.put("รุ่น %s บน GitHub: ไฟล์ในเครื่องตรงกับรุ่นนี้ครบแล้ว (hash ตรงทุกไฟล์) ไม่มีไฟล์ใหม่ให้ดาวน์โหลด\n\n%s" % (m.get("version"), m.get("notes", "")))
        self.put("มีรุ่นใหม่ %s\nไฟล์ที่จะดาวน์โหลด (%d):\n%s\n\n%s%s" % (
            m.get("version"), len(self.todo), "\n".join(" - %s" % f["path"] for f in self.todo), m.get("notes", ""), extra))
        self.btn.config(state="normal" if self.todo else "disabled")

    def apply(self):
        if getattr(self, "mode", "") == "patch":
            if not messagebox.askyesno("ยืนยัน", "ติดตั้งแพตช์รุ่น %s แล้วเปิดโปรแกรมใหม่?\n(ข้อมูลที่นำเข้าไม่หาย)" % self.m["patch"]["version"]):
                return
            try:
                updater.apply_patch(self.m, self.base, progress=lambda s: (self.put(s), self.update_idletasks()))
            except Exception as e:
                return self.put("อัปเดตไม่สำเร็จ: %s\n\nไม่มีไฟล์ใดถูกเปลี่ยน ลองใหม่ได้" % e)
            self.app.db.save()
            updater.restart()
            self.app._closing = True
            self.app.destroy()
            return
        if not messagebox.askyesno("ยืนยัน", "อัปเดตไฟล์ %d รายการ? (สำรองไฟล์เดิมเป็น .bak)" % len(self.todo)):
            return
        try:
            n, pend = updater.apply(self.m, self.base, self.todo, progress=lambda s: (self.put(s), self.update_idletasks()))
        except Exception as e:
            return self.put("อัปเดตไม่สำเร็จ: %s\n\nไม่มีไฟล์ใดถูกเขียนทับ (ตรวจ hash ก่อนเขียน)\nวางลิงก์ใหม่แล้วลองอีกครั้งได้" % e)
        if pend:
            messagebox.showinfo("เสร็จ", "อัปเดต %d ไฟล์ บางไฟล์ถูกล็อก โปรแกรมจะปิดและเปิดใหม่เพื่อสลับไฟล์" % n)
            updater.finish_pending(pend)
            self.app.destroy()
        else:
            messagebox.showinfo("เสร็จ", "อัปเดต %d ไฟล์แล้ว กรุณาเปิดโปรแกรมใหม่" % n)
            self.app.destroy()


# ====================================================================== หน้าแรก + หน้าต่างหลัก
NAVY = BG = ACCENT = GREEN = CARD = MUTED = SIDE = SIDE_HOVER = SIDE_ACT = GREEN_BTN = GREEN_BTN_HOVER = BORDER = ""


def sync_theme():
    """คัดลอกสีของธีมปัจจุบัน (luna.py) มาเป็นค่าคงที่ของหน้าจอ  เรียกหลัง luna.set_theme()"""
    globals().update(NAVY=luna.NAVY, BG=luna.BG, ACCENT=luna.BLUE, GREEN=luna.GREEN, CARD=luna.CARD, MUTED=luna.MUTED, SIDE=luna.SIDE,
                     SIDE_HOVER=luna.SIDE_HOVER, SIDE_ACT=luna.SIDE_ACT_BG, GREEN_BTN=luna.BTN, GREEN_BTN_HOVER=luna.BTN_HOVER, BORDER=luna.LINE)


sync_theme()
_COLOR_OPTS = ("bg", "fg", "highlightbackground", "highlightcolor", "activebackground", "activeforeground", "selectbackground", "troughcolor")


def recolor(w, mp):
    """ไล่เปลี่ยนสีของวิดเจ็ต tk ทั้งต้นไม้ ตามตาราง สีเก่า→สีใหม่ (คงข้อมูลที่กรอกไว้ ไม่ต้องสร้างหน้าใหม่)"""
    if not isinstance(w, ttk.Widget):
        for o in _COLOR_OPTS:
            try:
                v = str(w.cget(o)).lower()
            except tk.TclError:
                continue
            if v in mp:
                try:
                    w.configure(**{o: mp[v]})
                except tk.TclError:
                    pass
    elif isinstance(w, ttk.Treeview):
        try:
            w.tag_configure("ptype", background=luna.HEAD_L)
            w.tag_configure("tam", background=luna.ROW_ALT)
        except tk.TclError:
            pass
    for c in w.winfo_children():
        if not isinstance(c, tk.Toplevel):
            recolor(c, mp)


class TitleBar(tk.Canvas):
    """แถบหัวเรื่องแบบ XP: ไล่สีแนวตั้งมันวาว + เงาตัวอักษร + เส้นส้มใต้แถบ  ใช้ .config(text=...) เหมือน Label"""

    def __init__(self, parent, font):
        super().__init__(parent, height=62, highlightthickness=0, bd=0, bg=luna.SIDE)
        self.font, self.text, self.H, self.news, self._img = font, "", 62, "", None
        self.bind("<Configure>", lambda e: self.draw())

    def config(self, **kw):
        if "text" in kw:
            self.text = kw.pop("text")
        if "news" in kw:
            self.news = kw.pop("news")
        if kw:
            super().config(**kw)
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = max(1, self.winfo_width()), self.H
        self._img = ImageTk_photo(luna.vgrad(w, h - 3, luna.TITLE_STOPS), self)
        self.create_image(0, 0, image=self._img, anchor="nw")
        self.create_rectangle(0, h - 3, w, h, fill=luna.TITLE_LINE, outline="")          # เส้นสีใต้แถบ (เหมือนหัวเมนู Start)
        self.create_line(0, h - 3, w, h - 3, fill=luna.TITLE_LINE_L)
        fs = 16 if h < 50 else self.font[1]
        fn = (self.font[0], fs, "bold")
        self.create_text(19, h / 2 - 1, text=self.text, anchor="w", fill=luna.TITLE_SHADOW, font=fn)       # เงา
        self.create_text(18, h / 2 - 2, text=self.text, anchor="w", fill="white", font=fn)
        if self.news:
            self.create_text(w - 18, h / 2 - 1, text=self.news, anchor="e", fill="#FFE680", font=(self.font[0], 11, "bold"))


def ImageTk_photo(im, master):
    from PIL import ImageTk
    return ImageTk.PhotoImage(im, master=master)


class SideHead(tk.Canvas):
    """หัวแถบเมนูซ้าย ไล่สีน้ำเงินเข้ม→ฟ้า มีโลโก้ + ชื่อโปรแกรม (แบบหัวเมนู Start)"""

    def __init__(self, parent, logo, font):
        super().__init__(parent, highlightthickness=0, bd=0, height=96, bg=luna.SIDE_TOP)
        self.logo, self.font, self.compact, self._img = logo, font, False, None
        self.bind("<Configure>", lambda e: self.draw())

    def draw(self):
        self.delete("all")
        w, h = max(1, self.winfo_width()), 62 if self.compact else 96
        self.config(height=h)
        self._img = ImageTk_photo(luna.vgrad(w, h, ((0, luna.SIDE_TOP), (0.85, luna.SIDE), (1, luna.SIDE))), self)
        self.create_image(0, 0, image=self._img, anchor="nw")
        x = 12 if self.compact else 18
        if self.logo:
            self.create_image(x, h / 2, image=self.logo, anchor="w")
            x += 68
        fs = 11 if self.compact else 13
        self.create_text(x + 1, h / 2 + 1, text="ZAIA\nPrepare Personal", anchor="w", fill=luna.TITLE_SHADOW, font=(self.font, fs, "bold"))
        self.create_text(x, h / 2, text="ZAIA\nPrepare Personal", anchor="w", fill="white", font=(self.font, fs, "bold"))


def asset(name):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", name)


class Card(tk.Frame):
    """การ์ดคลิกได้"""

    def __init__(self, parent, num, title, desc, cmd, color=None):
        color = color or ACCENT
        super().__init__(parent, bg=CARD, highlightthickness=2, highlightbackground=BORDER, cursor="hand2")
        fam = parent.winfo_toplevel().ui_font
        self.badge = tk.Label(self, text=num, bg=color, fg="white", font=(fam, 18, "bold"), width=2)
        self.badge.pack(side="left", fill="y")
        box = tk.Frame(self, bg=CARD)
        box.pack(side="left", fill="both", expand=True, padx=16, pady=14)
        tk.Label(box, text=title, bg=CARD, fg=NAVY, font=(fam, 15, "bold"), anchor="w", justify="left").pack(fill="x")
        tk.Label(box, text=desc, bg=CARD, fg=MUTED, font=(fam, 11), anchor="w", justify="left", wraplength=330).pack(fill="x", pady=(4, 0))
        for w in [self, box] + list(box.winfo_children()) + [self.badge]:
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>", lambda e: self.config(highlightbackground=color))
            w.bind("<Leave>", lambda e: self.config(highlightbackground=BORDER))


class HomePage(Page):
    def __init__(self, app):
        super().__init__(app)
        db, fam = app.db, app.ui_font
        n = len(db.persons)
        done = sum(1 for p in db.persons if db.filled(p))
        printed = sum(1 for p in db.persons if any(k.startswith("reg_") for k in p.get("printed", {})))
        cv = tk.Canvas(self, bg=BG, highlightthickness=0)             # หน้าแรกเลื่อนขึ้นลงได้ (ล้อเมาส์/แถบเลื่อน) ไม่ให้ขั้นตอนตกจอ
        vs = ttk.Scrollbar(self, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=BG)
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        self.cv = cv
        self.bind_all("<MouseWheel>", self._wheel)
        left = n - done
        if not n:
            nxt = ("import", "เริ่มที่นี่: นำเข้าข้อมูลจากไฟล์ Excel")
        elif left:
            nxt = ("record", "ขั้นตอนถัดไป: บันทึกผลการตรวจสอบ (เหลือ %d คน)" % left)
        elif db.dirty_count():
            nxt = ("writeback", "ขั้นตอนถัดไป: เขียนผลกลับไฟล์ Excel (%d คน)" % db.dirty_count())
        else:
            nxt = ("reg", "ขั้นตอนถัดไป: พิมพ์บัญชีตรวจสอบสภาพ")
        go = tk.Label(inner, text="▶  " + nxt[1], bg=GREEN_BTN, fg="white", font=(fam, 15, "bold"), anchor="w", padx=22, pady=14, cursor="hand2")
        go.pack(fill="x", pady=(0, 14))
        go.bind("<Button-1>", lambda e: app.writeback() if nxt[0] == "writeback" else app.nav(nxt[0]))
        go.bind("<Enter>", lambda e: go.config(bg=luna.mix(GREEN_BTN, "#000000", 0.2)))
        go.bind("<Leave>", lambda e: go.config(bg=GREEN_BTN))
        row = tk.Frame(inner, bg=BG)
        row.pack(fill="x")
        stats = [("รายชื่อทั้งหมด", str(n), "คน", NAVY), ("บันทึกผลแล้ว", str(done), "จาก %d คน" % n, GREEN),
                 ("รอเขียนกลับ Excel", str(db.dirty_count()), "คน", luna.ORANGE), ("พิมพ์บัญชีตรวจสอบแล้ว", str(printed), "คน", ACCENT)]
        cards = []
        for i, (t, v, u, c) in enumerate(stats):
            row.columnconfigure(i, weight=1, uniform="s")
            f = tk.Frame(row, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
            cards.append(f)
            tk.Frame(f, bg=c, height=5).pack(fill="x")
            tk.Label(f, text=t, bg=CARD, fg=MUTED, font=(fam, 11)).pack(anchor="w", padx=16, pady=(12, 0))
            tk.Label(f, text=v, bg=CARD, fg=c, font=(fam, 28, "bold")).pack(anchor="w", padx=16)
            tk.Label(f, text=u, bg=CARD, fg=MUTED, font=(fam, 10)).pack(anchor="w", padx=16, pady=(0, 10))
        state = {"cols": 0}

        def reflow(e=None):
            cols = 4 if row.winfo_width() >= 820 else 2           # จอแคบ: การ์ดสถิติเรียง 2x2
            if cols == state["cols"]:
                return
            state["cols"] = cols
            for j in range(4):
                row.columnconfigure(j, weight=1 if j < cols else 0, uniform="s" if j < cols else "")
            for j, f in enumerate(cards):
                f.grid(row=j // cols, column=j % cols, sticky="nsew", padx=(0 if j % cols == 0 else 8, 0), pady=(0, 8))
        row.bind("<Configure>", reflow)
        reflow()
        pb = ttk.Progressbar(inner, maximum=max(1, n), value=done, style="Green.Horizontal.TProgressbar")
        pb.pack(fill="x", pady=(12, 4))
        src = db.source.get("path", "")
        tk.Label(inner, bg=BG, fg=MUTED, font=(fam, 11), anchor="w",
                 text=("ไฟล์ข้อมูล: %s  [%s]" % (src, db.source.get("sheet", ""))) if n else "ยังไม่มีข้อมูล — เริ่มที่ขั้นตอน 1 นำเข้าข้อมูลจากไฟล์ Excel").pack(fill="x")
        _progress_table(inner, db, fam)

    def _wheel(self, e):
        try:
            if self.cv.winfo_exists():
                self.cv.yview_scroll(-1 * (e.delta // 120), "units")
        except tk.TclError:
            pass

    def destroy(self):
        try:
            self.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        super().destroy()


def _progress_table(self, db, fam):
    """ตารางความคืบหน้า: ประเภททหาร > ตำบล > หมู่ (ดับเบิลคลิกที่แถวเพื่อกางหรือหุบ)"""
    if not db.persons:
        return
    box = tk.Frame(self, bg=BG)
    box.pack(fill="x", pady=(12, 0))
    tk.Label(box, text="ความคืบหน้าแยกประเภท / ตำบล / หมู่", bg=BG, fg=NAVY, font=(fam, 13, "bold"), anchor="w").pack(fill="x")
    cols = ("all", "done", "left", "pct")
    tv = ttk.Treeview(box, columns=cols, height=12, selectmode="browse")
    tv.heading("#0", text="ประเภท / ตำบล / หมู่")
    for c, t, w in (("all", "ทั้งหมด", 70), ("done", "ดำเนินการแล้ว", 110), ("left", "คงเหลือ", 80), ("pct", "ร้อยละ", 64)):
        tv.heading(c, text=t)
        tv.column(c, width=w, minwidth=w, anchor="e", stretch=False)
    tv.column("#0", width=200, minwidth=150, stretch=True)
    tv.tag_configure("ptype", background=luna.HEAD_L, font=(fam, 11, "bold"))
    tv.tag_configure("tam", background=luna.ROW_ALT)
    tv.tag_configure("zero", foreground="#B42318")
    sb = ttk.Scrollbar(box, command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", fill="x", expand=True)
    sb.pack(side="left", fill="y")

    def row(parent, text, a, d, tags):
        pc = "%d%%" % round(100 * d / a) if a else "-"
        return tv.insert(parent, "end", text=text, values=(a, d, a - d, pc), tags=tags + (("zero",) if a - d else ()), open=False)
    T = [0, 0]
    for t, a, d, tams in db.summary():
        it = row("", t, a, d, ("ptype",))
        T[0] += a
        T[1] += d
        for tb, a2, d2, moos in tams:
            it2 = row(it, "ต." + tb, a2, d2, ("tam",))
            for m, a3, d3 in moos:
                row(it2, "หมู่ " + m, a3, d3, ())
    row("", "รวมทั้งหมด", T[0], T[1], ("ptype",))

    def toggle(e):
        i = tv.identify_row(e.y)
        if i:
            tv.item(i, open=not tv.item(i, "open"))
    tv.bind("<Double-1>", toggle)




class App(tk.Tk):
    def __init__(self):
        if os.name == "nt":
            try:        # ให้ Windows แยกเป็นโปรแกรมของเราเอง (ไอคอนบน Taskbar ไม่ใช่ของ Python)
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZAIA.PreparePersonal.App")
            except Exception:
                pass
        super().__init__()
        self.title("%s  %s" % (APP_NAME, APP_VER))
        self.minsize(760, 520)
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                self.geometry("1280x800")
        self.st = core.load_settings()
        luna.set_theme(self.st.get("theme", luna.DEFAULT), self.st.get("btn_style", "flat"))
        sync_theme()
        self.db = core.DB()
        self._fams = set(tkfont.families())
        self.ui_font = next((f for f in ("Leelawadee UI", "Segoe UI", "Tahoma", "Loma") if f in self._fams), "Tahoma")
        for n in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(n).configure(family=self.ui_font, size=11)
            except tk.TclError:
                pass
        self.configure(bg=BG)
        try:
            from PIL import Image, ImageTk
            im = Image.open(asset("logo.png"))
            self._logo_big = ImageTk.PhotoImage(im.resize((56, 56), Image.LANCZOS))
            self.iconphoto(True, ImageTk.PhotoImage(im.resize((64, 64), Image.LANCZOS)))
        except Exception:
            self._logo_big = None
        if os.name == "nt":
            try:
                self.iconbitmap(asset("logo.ico"))
                self.iconbitmap(default=asset("logo.ico"))
            except tk.TclError:
                pass
        self.style()
        self.side = tk.Frame(self, bg=SIDE, width=270)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.h1 = TitleBar(main, (self.ui_font, 20, "bold"))
        self.h1.pack(fill="x")
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=24, pady=(16, 16))
        self._sidebtns, self._compact = [], None
        self.build_side()
        self.bind("<Configure>", self._on_resize)
        self.cur = None
        self.nav("home")
        self.bind_all("<F1>", lambda e: self.nav("home"))
        self.after(1500, self.silent_check)

    # ---- รูปแบบ
    def style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        f = self.ui_font
        st.configure(".", background=BG, font=(f, 11))
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground="#1F2937", font=(f, 11))
        st.configure("TLabelframe", background=BG)
        st.configure("TLabelframe.Label", background=BG, foreground=NAVY, font=(f, 11, "bold"))
        for w in ("TCheckbutton", "TRadiobutton"):
            st.configure(w, background=BG, font=(f, 11))
        st.configure("TEntry", padding=6, fieldbackground="white")
        st.configure("TCombobox", padding=6, fieldbackground="white")
        st.configure("TSpinbox", padding=5, fieldbackground="white")
        st.configure("Treeview", rowheight=28, font=(f, 11), fieldbackground="white")
        st.configure("Treeview.Heading", font=(f, 11, "bold"), padding=6)
        st.configure("TNotebook.Tab", padding=(16, 8), font=(f, 11))
        self._luna = luna.install(st, self)           # ปุ่มเงา/สี/แท็บ/แถบเลื่อน แบบ Luna (เก็บภาพไว้กันถูกลบ)
        st.configure("TButton", font=(f, 11))
        st.configure("Accent.TButton", font=(f, 11, "bold"))

    def set_theme(self, key, btn_style=None):
        """เปลี่ยนธีมสีทันที (ไม่ต้องรีสตาร์ต/ไม่เสียข้อมูลที่กรอกค้าง) แล้วบันทึกลงการตั้งค่า"""
        style = btn_style or self.st.get("btn_style", "flat")
        old = luna.palette()
        luna.set_theme(key, style)
        sync_theme()
        new = luna.palette()
        mp = {}
        for k, ov in old.items():
            if ov.lower() != new[k].lower() and ov.upper() != "#FFFFFF":
                mp.setdefault(ov.lower(), new[k])
        self.style()
        self.configure(bg=BG)
        recolor(self, mp)
        for c in (self.h1, self._head):
            c.draw()
        b = getattr(self, "_navkey", "home")
        for k, w in self.navbtn.items():
            w.config(bg=SIDE_ACT if k == b else SIDE, fg=luna.SIDE_ACT_FG if k == b else luna.SIDE_TXT)
        self.st["theme"], self.st["btn_style"] = key, style
        core.save_settings(self.st)
        if hasattr(self.cur, "theme_draw"):
            self.cur.theme_draw()

    def build_side(self):
        f = self.ui_font
        self._head = SideHead(self.side, self._logo_big, f)
        self._head.pack(fill="x", pady=(0, 10))
        self.navbtn = {}
        for key, txt in (("home", "หน้าแรก"), ("import", "1  นำเข้าข้อมูล"), ("form", "2  แบบพิมพ์รายบุคคล / ซอง"),
                         ("send", "3  ส่งผู้ใหญ่บ้านตรวจสอบ"), ("record", "4  บันทึกผลการตรวจสอบ"), ("reg", "5  พิมพ์บัญชีตรวจสอบสภาพ"),
                         ("sum", "6  บัญชีสรุปผลการตรวจสอบ")):
            self.navbtn[key] = self.side_btn(txt, lambda k=key: self.nav(k))
        tk.Frame(self.side, bg=luna.SIDE_SEP, height=1).pack(fill="x", padx=18, pady=14)
        self.side_btn("เขียนผลกลับไฟล์ Excel", self.writeback)
        cl = self.side_btn("ล้างข้อมูล  ▾", None)
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="ล้างผลการตรวจสอบ", command=self.clear_results)
        m.add_command(label="ล้างสถานะ “พิมพ์แล้ว” (กระดาษเสีย/พิมพ์ใหม่)", command=self.clear_printed)
        m.add_separator()
        m.add_command(label="ล้างข้อมูลที่นำเข้าทั้งหมด", command=self.clear_all)
        cl.bind("<Button-1>", lambda e: m.tk_popup(cl.winfo_rootx() + 20, cl.winfo_rooty() + 40))
        self.navbtn["settings"] = self.side_btn("ตั้งค่า", lambda: self.nav("settings"))
        self.navbtn["update"] = self.side_btn("ตรวจสอบอัปเดต", lambda: self.nav("update"))
        ft = tk.Label(self.side, text="รุ่น %s" % APP_VER, bg=luna.SIDE_TOP, fg=luna.SIDE_FOOT, font=(f, 10), pady=9)
        ft.pack(side="bottom", fill="x")

    def _on_resize(self, e):
        """จอเล็ก (เช่นแท็บเล็ต 10 นิ้ว ที่ขยาย 150%): ย่อแถบเมนูซ้ายและช่องไฟ ให้เนื้อหามีที่มากขึ้น"""
        if e.widget is not self:
            return
        c = e.width < 1000
        if c == self._compact:
            return
        self._compact = c
        self.side.config(width=224 if c else 270)
        for b in self._sidebtns:
            b.config(font=(self.ui_font, 11 if c else 12), padx=14 if c else 22, pady=4 if c else 11)
        self._head.compact = c
        self._head.draw()
        self.h1.config(height=46 if c else 62)
        self.h1.H = 46 if c else 62
        self.h1.draw()
        self.content.pack_configure(padx=10 if c else 24, pady=8 if c else 16)

    def side_btn(self, text, cmd):
        b = tk.Label(self.side, text=text, bg=SIDE, fg=luna.SIDE_TXT, font=(self.ui_font, 12), anchor="w", padx=22, pady=11, cursor="hand2")
        b.pack(fill="x")
        self._sidebtns.append(b)
        b.bind("<Enter>", lambda e: b.config(bg=SIDE_HOVER) if b.cget("bg") != SIDE_ACT else None)
        b.bind("<Leave>", lambda e: b.config(bg=SIDE) if b.cget("bg") != SIDE_ACT else None)
        if cmd:
            b.bind("<Button-1>", lambda e: cmd())
        return b

    # ---- นำทาง
    def set_title(self, t):
        self.h1.config(text=t)

    TITLES = {"home": "หน้าแรก", "import": "1  นำเข้าข้อมูลจากไฟล์ Excel", "send": "3  ส่งข้อมูลให้ผู้ใหญ่บ้านตรวจสอบ",
              "record": "4  บันทึกผลการตรวจสอบสภาพ", "reg": "5  จัดพิมพ์บัญชีตรวจสอบสภาพ", "sum": "6  บัญชีสรุปผลการตรวจสอบ",
              "form": "2  แบบพิมพ์รายบุคคล + จ่าหน้าซอง", "settings": "ตั้งค่า", "update": "ตรวจสอบอัปเดต"}

    def nav(self, key):
        if key in ("send", "record", "reg", "sum", "form") and not self.db.persons:
            messagebox.showinfo("ยังไม่มีข้อมูล", "กรุณานำเข้าข้อมูลจาก Excel ก่อน (ขั้นตอน 1)")
            key = "import"
        if self.cur is not None:
            try:
                if getattr(self.cur, "busy", False) is True:
                    return messagebox.showinfo("กำลังพิมพ์", "กด ยกเลิก ก่อนเปลี่ยนหน้า")
                ttk.Frame.destroy(self.cur)
            except tk.TclError:
                pass
        self.unbind("<Escape>")
        mk = {"home": lambda: HomePage(self), "import": lambda: ImportWin(self), "record": lambda: RecordWin(self),
              "send": lambda: PrintWin(self, "send"), "reg": lambda: PrintWin(self, "reg"), "sum": lambda: PrintWin(self, "sum"), "form": lambda: PersonalWin(self),
              "settings": lambda: SettingsWin(self), "update": lambda: UpdateWin(self)}
        self.set_title(self.TITLES[key])
        self._navkey = key
        self.cur = mk[key]()
        self.cur.pack(fill="both", expand=True)
        for k, b in self.navbtn.items():
            b.config(bg=SIDE_ACT if k == key else SIDE, fg=luna.SIDE_ACT_FG if k == key else luna.SIDE_TXT)

    def go_home(self):
        self.nav("home")

    def destroy(self):
        self._closing = True
        super().destroy()

    def font_family(self):
        f = self.st.get("font") or "TH SarabunIT๙"
        for c in (f, "TH SarabunIT๙", "TH SarabunPSK", "Angsana New", "Tahoma"):
            if c in self._fams:
                return c
        return "Tahoma"

    def refresh_status(self):
        if self.cur is not None and isinstance(self.cur, HomePage):
            self.nav("home")

    # ---- เขียนกลับ / ล้าง
    def writeback(self):
        if not self.db.persons:
            return messagebox.showinfo("เขียนกลับ", "ยังไม่มีข้อมูล")
        n = self.db.dirty_count()
        if not n:
            return messagebox.showinfo("เขียนกลับ", "ไม่มีผลที่เปลี่ยนจากไฟล์ต้นฉบับ")
        if core.is_xlsb(self.db.source.get("path", "")):
            if not messagebox.askyesno("เขียนผลกลับไฟล์ .xlsb", "จะเขียนผลของ %d คน ลงไฟล์ .xlsb เดิมผ่าน Microsoft Excel:\n%s\nชีต: %s\n\nแก้เฉพาะช่องผลตรวจ ส่วนอื่นไม่ถูกแตะ (บันทึกเป็น .xlsb เหมือนเดิม)\nต้องปิดไฟล์นี้ใน Excel ก่อน — ต่อไหม?\n%s" % (
                    n, self.db.source.get("path"), self.db.source.get("sheet"),
                    "ระบบจะสำรองไฟล์เดิมไว้ข้างไฟล์ก่อนเขียน" if self.st.get("backup", True) else "⚠ ปิดการสำรองไฟล์ไว้")):
                return
            self.config(cursor="watch")
            self.update_idletasks()
            try:
                cells, bak = core.write_back(self.db, self.st.get("backup", True))
            except core.ExcelError as e:
                self.config(cursor="")
                if e.code == "NOEXCEL" and messagebox.askyesno("ไม่พบ Excel", "%s\nสร้างไฟล์ .xlsx ใหม่ข้างไฟล์เดิมแทน (ค่าล้วน ไม่มีรูปแบบ/มาโคร) ไหม?" % e):
                    try:
                        cells, bak = core.write_back(self.db, xlsb_export=True)
                    except Exception as e2:
                        return err("ส่งออกไม่สำเร็จ: %s" % e2)
                    self.refresh_status()
                    return messagebox.showinfo("สำเร็จ", "สร้างไฟล์ใหม่แล้ว:\n%s\nไฟล์ .xlsb เดิมไม่ถูกแก้" % bak)
                return err("เขียนกลับไม่สำเร็จ: %s" % e) if e.code != "NOEXCEL" else None
            except Exception as e:
                self.config(cursor="")
                return err("เขียนกลับไม่สำเร็จ: %s" % e)
            self.config(cursor="")
            self.refresh_status()
            return messagebox.showinfo("สำเร็จ", "เขียน %d เซลล์ลงไฟล์ .xlsb เดิมแล้ว%s" % (cells, ("\nสำรองไว้ที่: " + bak) if bak else ""))
        if not messagebox.askyesno("เขียนผลกลับไฟล์ต้นฉบับ", "จะเขียนผลของ %d คน ลงไฟล์:\n%s\nชีต: %s\n\nแก้เฉพาะช่องผลตรวจ (มี/ไม่มี สถานภาพ สถานที่ อำเภอ จังหวัด เบอร์โทร) ส่วนอื่นไม่ถูกแตะ\n%s" % (
                n, self.db.source.get("path"), self.db.source.get("sheet"),
                "ระบบจะสำรองไฟล์เดิมไว้ข้างไฟล์ก่อนเขียน" if self.st.get("backup", True) else "⚠ ปิดการสำรองไฟล์ไว้")):
            return
        try:
            cells, bak = core.write_back(self.db, self.st.get("backup", True))
        except Exception as e:
            return err("เขียนกลับไม่สำเร็จ: %s" % e)
        self.refresh_status()
        messagebox.showinfo("สำเร็จ", "เขียน %d เซลล์แล้ว%s" % (cells, ("\nสำรองไว้ที่: " + bak) if bak else ""))

    def clear_results(self):
        if self.db.persons and messagebox.askyesno("ล้างผลการตรวจสอบ", "ล้างผลการตรวจสอบของทุกคนในโปรแกรม?\n(ไฟล์ Excel เดิมยังไม่ถูกแก้จนกว่าจะกด “เขียนผลกลับ”)"):
            self.db.clear_results()
            self.refresh_status()

    def clear_printed(self):
        if self.db.persons and messagebox.askyesno("ล้างสถานะพิมพ์แล้ว", "ล้างเครื่องหมาย “พิมพ์แล้ว” ทุกแบบ?"):
            self.db.clear_printed()
            messagebox.showinfo("เสร็จ", "ล้างแล้ว")
            self.refresh_status()

    def clear_all(self):
        if self.db.persons and messagebox.askyesno("ล้างข้อมูลที่นำเข้า", "ลบข้อมูลทั้งหมดในโปรแกรม (ผลตรวจ+สถานะพิมพ์)?\nไฟล์ Excel ต้นฉบับไม่ถูกลบ\n\nผลที่ยังไม่เขียนกลับจะหายไป — ต่อไหม?"):
            self.db.clear_all()
            self.refresh_status()

    def silent_check(self):
        url = self.st.get("update_url") or UPDATE_BASE
        if not url:
            return
        self._nv = None

        def run():
            try:
                m, _ = updater.fetch_manifest(url)
                if updater.has_patch(m):
                    self._nv = m["patch"]["version"]
                elif updater.is_newer(m):
                    self._nv = m.get("version")
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()
        self.after(1000, self._poll_news, 0)

    def _poll_news(self, n):
        if self._nv:
            self.h1.config(news="● มีรุ่นใหม่ %s — เมนู ตรวจสอบอัปเดต" % self._nv)
        elif n < 15:
            self.after(1000, self._poll_news, n + 1)


def main():
    App().mainloop()
