"""ZAIA Prepare Personal - หน้าจอ (tkinter)"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from . import core, layout, render, updater
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


# ====================================================================== ตั้งค่า
class VScroll(ttk.Frame):
    """กรอบเลื่อนขึ้นลงได้ (แถบเลื่อน + ล้อเมาส์) ใส่เนื้อหาใน .inner — กันปุ่ม/ช่องตกจอเมื่อหน้าต่างเตี้ย"""

    def __init__(self, parent, bg=None):
        super().__init__(parent)
        self.cv = tk.Canvas(self, highlightthickness=0, **({"bg": bg} if bg else {}))
        sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        self.inner = ttk.Frame(self.cv)
        self._win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._cfg)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", lambda ev: self.cv.yview_scroll(-1 * (ev.delta // 120), "units")))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _cfg(self, e):
        self.cv.configure(scrollregion=self.cv.bbox("all"), width=self.inner.winfo_reqwidth())


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
        ttk.Label(f3, text="กรอกครั้งเดียว โปรแกรมดึงไปใส่แบบพิมพ์รายบุคคลและซองจดหมายให้ทุกใบ (เมนู 6)", foreground="#555").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        rows3 = [("unit_name", "ชื่อหน่วย (ผู้ส่งบนซอง)"), ("unit_addr", "ที่ตั้ง/บรรทัดที่อยู่ (เช่น ที่ว่าการอำเภอ)"),
                 ("unit_amphoe", "อำเภอของหน่วย (ว่าง = ใช้อำเภอสำรอง)"), ("unit_province", "จังหวัดของหน่วย (ว่าง = ใช้จังหวัดสำรอง)"),
                 ("unit_zip", "รหัสไปรษณีย์หน่วย (ว่าง = คิดให้อัตโนมัติ)"), ("sad_tel", "เบอร์โทรสัสดีอำเภอ (พิมพ์บนแบบพิมพ์)"),
                 ("deadline", "ให้ส่งคืนภายในวันที่ (เช่น 15 ธันวาคม 2569)"), ("env_no", "เลขที่หนังสือบนซอง “ที่ …” (ว่าง = ไม่พิมพ์)")]
        for i, (k, lab) in enumerate(rows3, 1):
            ttk.Label(f3, text=lab).grid(row=i, column=0, sticky="w", pady=5)
            self.v[k] = tk.StringVar(value=str(st.get(k, "")))
            ttk.Entry(f3, textvariable=self.v[k], width=46).grid(row=i, column=1, pady=5, padx=8, sticky="w")
        self.zipmsg = ttk.Label(f3, text="")
        ttk.Button(f3, text="คิดรหัสไปรษณีย์จากอำเภอ/จังหวัดของหน่วย", command=self.guess_zip).grid(row=len(rows3) + 1, column=1, sticky="w", pady=6, padx=8)
        self.zipmsg.grid(row=len(rows3) + 2, column=1, sticky="w", padx=8)
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
        nb.pack(fill="both", expand=True)
        self.switch()

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
        self.geometry("1120x680")
        self.app, self.db = app, app.db
        self.cur = None
        left = ttk.Frame(self, padding=6)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="ค้นหา (เลขบัตร / ชื่อ / สกุล)").pack(anchor="w")
        self.q = tk.StringVar()
        e = ttk.Entry(left, textvariable=self.q, width=34)
        e.pack(fill="x")
        e.bind("<KeyRelease>", lambda ev: self.refill())
        e.bind("<Return>", lambda ev: self.pick_first())
        self.tam = tk.StringVar(value=core.ALL_TAMBON)
        cb = ttk.Combobox(left, textvariable=self.tam, values=[core.ALL_TAMBON] + self.db.tambons(), state="readonly")
        cb.pack(fill="x", pady=3)
        cb.bind("<<ComboboxSelected>>", lambda ev: self.refill())
        self.only = tk.BooleanVar()
        ttk.Checkbutton(left, text="เฉพาะที่ยังไม่บันทึก", variable=self.only, command=self.refill).pack(anchor="w")
        fr = ttk.Frame(left)
        fr.pack(fill="both", expand=True)
        self.lb = tk.Listbox(fr, width=38, exportselection=False, font=("Tahoma", 11))
        sc = ttk.Scrollbar(fr, command=self.lb.yview)
        self.lb.config(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda ev: self.on_select())
        self.prog = ttk.Label(left, text="")
        self.prog.pack(anchor="w")
        right = ttk.Frame(self, padding=10)
        right.pack(side="left", fill="both", expand=True)
        self.saved = tk.Label(right, text="", fg="#15803D", bg=BG, font=(app.ui_font, 13, "bold"), anchor="w", padx=8)
        self.saved.pack(fill="x", pady=(0, 6))          # แถบข้อความ "บันทึกข้อมูลแล้ว" อยู่บนสุด มองเห็นเสมอ
        self._saved_job = None
        self.head = ttk.Label(right, text="— เลือกรายชื่อทางซ้าย —", font=BIG)
        self.head.pack(anchor="w")
        self.sub = ttk.Label(right, text="", wraplength=700)
        self.sub.pack(anchor="w", pady=(0, 8))
        g = ttk.Frame(right)
        g.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("result", "occ", "detail", "place", "province", "amphoe2", "tel", "tel_par", "tel_work")}
        r = 0
        ttk.Label(g, text="ผลการตรวจ").grid(row=r, column=0, sticky="w", pady=4)
        rf = ttk.Frame(g)
        rf.grid(row=r, column=1, sticky="w")
        ttk.Radiobutton(rf, text="มีตัว", value="มีตัว", variable=self.v["result"]).pack(side="left", padx=6)
        ttk.Radiobutton(rf, text="ไม่มีตัว", value="ไม่มีตัว", variable=self.v["result"]).pack(side="left", padx=6)
        r += 1
        ttk.Label(g, text="อาชีพ/สถานภาพ").grid(row=r, column=0, sticky="w", pady=4)
        self.occ = ttk.Combobox(g, textvariable=self.v["occ"], values=core.OCCUPATIONS, width=28)
        self.occ.grid(row=r, column=1, sticky="w")
        self.occ.bind("<<ComboboxSelected>>", lambda ev: self.occ_changed())
        r += 1
        ttk.Label(g, text="รายละเอียด ( )").grid(row=r, column=0, sticky="w")
        self.det = ttk.Entry(g, textvariable=self.v["detail"], width=40, state="disabled")
        self.det.grid(row=r, column=1, sticky="w", pady=3)
        r += 1
        ttk.Label(g, text="สถานที่").grid(row=r, column=0, sticky="w", pady=4)
        pf = ttk.Frame(g)
        pf.grid(row=r, column=1, sticky="w")
        ttk.Entry(pf, textvariable=self.v["place"], width=36).pack(side="left")
        ttk.Button(pf, text="คลิก ใส่ที่อยู่ตามภูมิลำเนา", command=self.domicile).pack(side="left", padx=6)
        r += 1
        ttk.Label(g, text="จังหวัด").grid(row=r, column=0, sticky="w", pady=4)
        self.cp = ttk.Combobox(g, textvariable=self.v["province"], values=sorted(GEO), width=28)
        self.cp.grid(row=r, column=1, sticky="w")
        self.cp.bind("<<ComboboxSelected>>", lambda ev: self.prov_changed())
        r += 1
        ttk.Label(g, text="อำเภอ / เขต").grid(row=r, column=0, sticky="w", pady=4)
        self.ca = ttk.Combobox(g, textvariable=self.v["amphoe2"], width=28)
        self.ca.grid(row=r, column=1, sticky="w")
        for k, lab in (("tel", "โทรศัพท์ (เจ้าตัว)"), ("tel_par", "โทรศัพท์ (ผู้ปกครอง)"), ("tel_work", "โทรศัพท์ (ที่ทำงาน)")):
            r += 1
            ttk.Label(g, text=lab).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(g, textvariable=self.v[k], width=30).grid(row=r, column=1, sticky="w")
        bt = ttk.Frame(right)
        bt.pack(fill="x", pady=14)
        ttk.Button(bt, text="◀ ก่อนหน้า", command=lambda: self.step(-1)).pack(side="left")
        ttk.Button(bt, text="ถัดไป ▶", command=lambda: self.step(1)).pack(side="left", padx=4)
        ttk.Button(bt, text="บันทึก", style="Accent.TButton", command=lambda: self.save(False)).pack(side="left", padx=14)
        ttk.Button(bt, text="บันทึกแล้วไปคนต่อไป", style="Accent.TButton", command=lambda: self.save(True)).pack(side="left")
        ttk.Button(bt, text="ล้างผลคนนี้", command=self.clear_one).pack(side="right")
        self.view = []
        self.refill()
        e.focus_set()

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
            self.lb.insert("end", "%s %s%s %s  (ม.%s ต.%s)" % ("✓" if self.db.filled(p) else "  ", p["rank"], p["name"], p["surname"], p["moo"], p["tambon"]))
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
        self.v["place"].set("%s ม.%s ต.%s อ.%s" % (p["house"], p["moo"], p["tambon"], p["amphoe"]))
        self.v["province"].set(p["province"])
        self.prov_changed(keep=p["amphoe"])

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
              "form": "แบบพิมพ์รายบุคคล", "env": "จ่าหน้าซองจดหมาย (DL)"}

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
        ttk.Combobox(g, textvariable=self.ptype, values=[core.ALL_TYPES] + core.TYPES, state="readonly", width=40).grid(row=r, column=1, sticky="w")
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
        self.ctam = ttk.Combobox(g, textvariable=self.tam, values=[core.ALL_TAMBON] + self.db.tambons(), state="readonly", width=20)
        self.ctam.grid(row=r, column=1, sticky="w")
        self.ctam.bind("<<ComboboxSelected>>", lambda e: self.upd())
        r += 1
        ttk.Label(g, text="หมู่ที่").grid(row=r, column=0, sticky="w", pady=3)
        self.cmoo = ttk.Combobox(g, textvariable=self.moo, values=["ทั้งหมด"] + self.db.moos(), state="readonly", width=20)
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
        for txt, cmd, stl in (("ดูตัวอย่าง", self.preview, "TButton"), ("พิมพ์ที่เลือก (1 ชุด เรียงหมู่)", lambda: self.go("sel"), "Accent.TButton"),
                              ("พิมพ์ทีละตำบล", lambda: self.go("tam"), "Accent.TButton"), ("พิมพ์ทีละหมู่", lambda: self.go("moo"), "Accent.TButton")):
            ttk.Button(bf, text=txt, command=cmd, style=stl).pack(side="left", padx=3)
        ttk.Button(bf, text="ยกเลิก (Esc)", command=self.stop).pack(side="right", padx=3)
        ttk.Button(bf, text="ล้างสถานะพิมพ์แล้ว", command=self.reset_marks).pack(side="right", padx=3)
        self.log = tk.Text(self, height=18, font=("Consolas", 11), state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=6)
        self.bind("<Escape>", lambda e: self.stop())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.upd()
        self.pump()

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
        t = self.tam.get()
        self.cmoo["values"] = ["ทั้งหมด"] + self.db.moos(t)
        if self.moo.get() not in self.cmoo["values"]:
            self.moo.set("ทั้งหมด")
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
        self.log.config(state="normal")
        self.log.insert("end", line)
        self.log.see("end")
        self.log.config(state="disabled")

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
        self.box = tk.Text(self, height=14, state="disabled")
        self.box.pack(fill="both", expand=True, padx=8)
        self.btn = ttk.Button(self, text="ดาวน์โหลดและอัปเดต", command=self.apply, state="disabled")
        self.btn.pack(pady=8)

    def put(self, s):
        self.box.config(state="normal")
        self.box.delete("1.0", "end")
        self.box.insert("1.0", s)
        self.box.config(state="disabled")

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
            self.put("มีแพตช์รุ่น %s (ปัจจุบัน %s)\nไฟล์โค้ด %d ไฟล์ จะดาวน์โหลดทั้งชุดและตรวจ SHA-256 ก่อนใช้งาน\n\n%s\n\nหลังอัปเดตโปรแกรมจะเปิดใหม่เอง" % (
                pv["version"], APP_VER, len(pv["files"]), m.get("notes", "")))
            self.btn.config(state="normal")
            return
        if not updater.is_newer(m):
            return self.put("เป็นรุ่นล่าสุดแล้ว (%s)" % APP_VER)
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
NAVY, BG, ACCENT, GREEN, CARD, MUTED = "#1B2A49", "#EEF2F8", "#2F6FED", "#1E9E5A", "#FFFFFF", "#6B7790"


def asset(name):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", name)


class Card(tk.Frame):
    """การ์ดคลิกได้"""

    def __init__(self, parent, num, title, desc, cmd, color=ACCENT):
        super().__init__(parent, bg=CARD, highlightthickness=2, highlightbackground="#D8DFEC", cursor="hand2")
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
            w.bind("<Leave>", lambda e: self.config(highlightbackground="#D8DFEC"))


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
        row = tk.Frame(inner, bg=BG)
        row.pack(fill="x")
        stats = [("รายชื่อทั้งหมด", str(n), "คน", NAVY), ("บันทึกผลแล้ว", str(done), "จาก %d คน" % n, GREEN),
                 ("รอเขียนกลับ Excel", str(db.dirty_count()), "คน", "#D98A00"), ("พิมพ์บัญชีตรวจสอบแล้ว", str(printed), "คน", ACCENT)]
        for i, (t, v, u, c) in enumerate(stats):
            row.columnconfigure(i, weight=1, uniform="s")
            f = tk.Frame(row, bg=CARD, highlightthickness=1, highlightbackground="#D8DFEC")
            f.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            tk.Label(f, text=t, bg=CARD, fg=MUTED, font=(fam, 11)).pack(anchor="w", padx=16, pady=(12, 0))
            tk.Label(f, text=v, bg=CARD, fg=c, font=(fam, 28, "bold")).pack(anchor="w", padx=16)
            tk.Label(f, text=u, bg=CARD, fg=MUTED, font=(fam, 10)).pack(anchor="w", padx=16, pady=(0, 10))
        pb = ttk.Progressbar(inner, maximum=max(1, n), value=done, style="Green.Horizontal.TProgressbar")
        pb.pack(fill="x", pady=(12, 4))
        src = db.source.get("path", "")
        tk.Label(inner, bg=BG, fg=MUTED, font=(fam, 11), anchor="w",
                 text=("ไฟล์ข้อมูล: %s  [%s]" % (src, db.source.get("sheet", ""))) if n else "ยังไม่มีข้อมูล — เริ่มที่ขั้นตอน 1 นำเข้าข้อมูลจากไฟล์ Excel").pack(fill="x")
        _progress_table(inner, db, fam)
        tk.Label(inner, text="เลือกขั้นตอน", bg=BG, fg=NAVY, font=(fam, 15, "bold"), anchor="w").pack(fill="x", pady=(18, 8))
        grid = tk.Frame(inner, bg=BG)
        grid.pack(fill="both", expand=True)
        items = [("1", "นำเข้าข้อมูลจากไฟล์ Excel", "เลือกไฟล์ ชีต แถวเริ่มต้น และจับคู่คอลัมน์ พร้อมดูตัวอย่างก่อนนำเข้า", "import", ACCENT),
                 ("2", "ส่งข้อมูลให้ผู้ใหญ่บ้านตรวจสอบ", "แบบเดียวกับบัญชีสรุป (A4 แนวนอน) ช่อง G-I ว่างให้กรอก มีตัวอย่างลำดับที่ 1", "send", "#7A4FD6"),
                 ("3", "บันทึกผลการตรวจสอบสภาพ", "ค้นด้วยเลขบัตร/ชื่อ กรอก มีตัว-ไม่มีตัว อาชีพ สถานที่ จังหวัด อำเภอ เบอร์โทร", "record", GREEN),
                 ("4", "จัดพิมพ์บัญชีตรวจสอบสภาพ", "เลือกประเภททหาร ระดับผู้ลงนาม ตำบล พิมพ์เรียงหมู่ ทีละตำบล/หมู่", "reg", "#D98A00"),
                 ("5", "บัญชีสรุปผลการตรวจสอบ", "เลือกประเภท (รวมทุกประเภท) ตำบล ผู้ลงนาม และจำนวนชุด", "sum", "#C2410C"),
                 ("6", "แบบพิมพ์รายบุคคล + จ่าหน้าซอง", "A4 1 หน้า/คน ให้ผู้ใหญ่บ้านกรอก และซอง DL พร้อมรหัสไปรษณีย์ระดับตำบล (ข้อมูลหน่วยกรอกที่ตั้งค่า)", "form", "#0E7490")]
        for i, (num, t, d, key, col) in enumerate(items):
            grid.columnconfigure(i % 2, weight=1, uniform="c")
            Card(grid, num, t, d, lambda k=key: app.nav(k), col).grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0, 12), pady=(0, 12))

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
    tv = ttk.Treeview(box, columns=cols, height=7, selectmode="browse")
    tv.heading("#0", text="ประเภท / ตำบล / หมู่")
    for c, t, w in (("all", "ทั้งหมด", 90), ("done", "ดำเนินการแล้ว", 120), ("left", "ยังไม่ดำเนินการ (คงเหลือ)", 190), ("pct", "ร้อยละ", 80)):
        tv.heading(c, text=t)
        tv.column(c, width=w, anchor="e")
    tv.column("#0", width=300)
    tv.tag_configure("ptype", background="#E8EEFB", font=(fam, 11, "bold"))
    tv.tag_configure("tam", background="#F6F8FC")
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
        self.side = tk.Frame(self, bg=NAVY, width=270)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=BG)
        top.pack(fill="x", padx=24, pady=(18, 6))
        self.h1 = tk.Label(top, text="", bg=BG, fg=NAVY, font=(self.ui_font, 22, "bold"), anchor="w")
        self.h1.pack(side="left")
        self.news = tk.Label(top, text="", bg=BG, fg="#B42318", font=(self.ui_font, 11, "bold"))
        self.news.pack(side="right")
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.build_side()
        self.cur = None
        self.navbtn = {}
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
        st.configure("TButton", padding=(14, 8), font=(f, 11), background="#DCE3F0", relief="flat")
        st.map("TButton", background=[("active", "#C9D4EA")])
        st.configure("Accent.TButton", padding=(16, 9), font=(f, 11, "bold"), background=ACCENT, foreground="white")
        st.map("Accent.TButton", background=[("active", "#1F55C4")])
        st.configure("TEntry", padding=6, fieldbackground="white")
        st.configure("TCombobox", padding=6, fieldbackground="white")
        st.configure("TSpinbox", padding=5, fieldbackground="white")
        st.configure("Treeview", rowheight=28, font=(f, 11), fieldbackground="white")
        st.configure("Treeview.Heading", font=(f, 11, "bold"), padding=6)
        st.configure("TNotebook", background=BG)
        st.configure("TNotebook.Tab", padding=(16, 8), font=(f, 11))
        st.configure("Green.Horizontal.TProgressbar", troughcolor="#D8DFEC", background=GREEN, thickness=10)

    def build_side(self):
        f = self.ui_font
        head = tk.Frame(self.side, bg=NAVY)
        head.pack(fill="x", pady=(22, 18), padx=18)
        if self._logo_big:
            tk.Label(head, image=self._logo_big, bg=NAVY).pack(side="left")
        tk.Label(head, text="ZAIA\nPrepare Personal", bg=NAVY, fg="white", font=(f, 13, "bold"), justify="left").pack(side="left", padx=10)
        self.navbtn = {}
        for key, txt in (("home", "หน้าแรก"), ("import", "1  นำเข้าข้อมูล"), ("send", "2  ส่งผู้ใหญ่บ้านตรวจสอบ"),
                         ("record", "3  บันทึกผลการตรวจสอบ"), ("reg", "4  พิมพ์บัญชีตรวจสอบสภาพ"), ("sum", "5  บัญชีสรุปผลการตรวจสอบ"), ("form", "6  แบบพิมพ์รายบุคคล / ซอง")):
            self.navbtn[key] = self.side_btn(txt, lambda k=key: self.nav(k))
        tk.Frame(self.side, bg="#34466E", height=1).pack(fill="x", padx=18, pady=14)
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
        tk.Label(self.side, text="รุ่น %s" % APP_VER, bg=NAVY, fg="#8FA0C4", font=(f, 10)).pack(side="bottom", pady=12)

    def side_btn(self, text, cmd):
        b = tk.Label(self.side, text=text, bg=NAVY, fg="#E6ECFA", font=(self.ui_font, 12), anchor="w", padx=22, pady=11, cursor="hand2")
        b.pack(fill="x")
        b.bind("<Enter>", lambda e: b.config(bg="#2B3F6B") if b.cget("bg") != ACCENT else None)
        b.bind("<Leave>", lambda e: b.config(bg=NAVY) if b.cget("bg") != ACCENT else None)
        if cmd:
            b.bind("<Button-1>", lambda e: cmd())
        return b

    # ---- นำทาง
    def set_title(self, t):
        self.h1.config(text=t)

    TITLES = {"home": "หน้าแรก", "import": "1  นำเข้าข้อมูลจากไฟล์ Excel", "send": "2  ส่งข้อมูลให้ผู้ใหญ่บ้านตรวจสอบ",
              "record": "3  บันทึกผลการตรวจสอบสภาพ", "reg": "4  จัดพิมพ์บัญชีตรวจสอบสภาพ", "sum": "5  บัญชีสรุปผลการตรวจสอบ",
              "form": "6  แบบพิมพ์รายบุคคล + จ่าหน้าซอง", "settings": "ตั้งค่า", "update": "ตรวจสอบอัปเดต"}

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
              "send": lambda: PrintWin(self, "send"), "reg": lambda: PrintWin(self, "reg"), "sum": lambda: PrintWin(self, "sum"), "form": lambda: PrintWin(self, "form"),
              "settings": lambda: SettingsWin(self), "update": lambda: UpdateWin(self)}
        self.set_title(self.TITLES[key])
        self.cur = mk[key]()
        self.cur.pack(fill="both", expand=True)
        for k, b in self.navbtn.items():
            b.config(bg=ACCENT if k == key else NAVY, fg="white" if k == key else "#E6ECFA")

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
            self.news.config(text="● มีรุ่นใหม่ %s — เมนู ตรวจสอบอัปเดต" % self._nv)
        elif n < 15:
            self.after(1000, self._poll_news, n + 1)


def main():
    App().mainloop()
