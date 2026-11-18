"""ตัวแสดงผล ops: PIL (ภาพทดสอบ), Tk canvas (พรีวิว), Windows GDI (เครื่องพิมพ์)"""
import os

FIT_MIN = 0.55


def fit_factors(page, k, measure):
    """ตัวคูณย่อขนาดตัวอักษรต่อ op (ข้อความใน grp เดียวกันใช้ค่าต่ำสุดร่วมกัน) k = px/มม."""
    fac, grp = {}, {}
    for i, op in enumerate(page.ops):
        if op[0] != "text":
            continue
        _, x, y, w, h, text, al, pt, bold, g = op[:10]
        px = pt * 25.4 / 72 * k
        tw = measure(text, px, bold)
        f = 1.0 if tw <= w * k or tw <= 0 else max(FIT_MIN, 0.97 * (w * k) / tw)
        fac[i] = f
        if g is not None:
            grp[g] = min(grp.get(g, 1.0), f)
    for i, op in enumerate(page.ops):
        if op[0] == "text" and op[9] is not None:
            fac[i] = grp[op[9]]
    return fac


# ---------------------------------------------------------------- PIL
def find_font(name_hint=""):
    cands = []
    if os.name == "nt":
        wd = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        cands += [os.path.join(wd, f) for f in ("THSarabunIT.ttf", "THSarabun.ttf", "angsa.ttf", "tahoma.ttf")]
    cands += ["/usr/share/fonts/truetype/tlwg/Loma.ttf", "/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf",
              "/usr/share/fonts/opentype/tlwg/Loma.otf"]
    for c in cands:
        if os.path.exists(c):
            return c
    import glob
    g = glob.glob("/usr/share/fonts/**/Loma*.[to]tf", recursive=True)
    return g[0] if g else None


def render_pil(page, dpi=100, fontfile=None, boldfile=None):
    from PIL import Image, ImageDraw, ImageFont
    k = dpi / 25.4
    im = Image.new("RGB", (int(page.w * k), int(page.h * k)), "white")
    d = ImageDraw.Draw(im)
    fontfile = fontfile or find_font()
    cache = {}

    def font(px, bold):
        key = (round(px), bold)
        if key not in cache:
            f = boldfile if (bold and boldfile) else fontfile
            cache[key] = ImageFont.truetype(f, max(5, round(px)))
        return cache[key]

    fac = fit_factors(page, k, lambda tx, px, b: font(px, b).getlength(tx))
    for oi, op in enumerate(page.ops):
        t = op[0]
        if t == "fill":
            _, x, y, w, h, g = op
            d.rectangle([x * k, y * k, (x + w) * k, (y + h) * k], fill=(g, g, g))
        elif t == "line":
            _, x1, y1, x2, y2, w, dash = op
            lw = max(1, round(w * k))
            if dash:
                xx = x1
                while xx < x2:
                    d.line([xx * k, y1 * k, min(xx + 0.8, x2) * k, y2 * k], fill="black", width=lw)
                    xx += 1.6
            else:
                d.line([x1 * k, y1 * k, x2 * k, y2 * k], fill="black", width=lw)
        elif t == "text":
            _, x, y, w, h, text, al, pt, bold, _g = op[:10]
            col = "#%02x%02x%02x" % op[10] if len(op) > 10 else "black"
            px = pt / 72 * dpi
            f = font(px * fac[oi], bold)
            tw = f.getlength(text)
            tx = x * k + (0 if al == "l" else (w * k - tw) / 2 if al == "c" else w * k - tw)
            d.text((tx, (y + h / 2) * k), text, font=f, fill=col, anchor="lm")
            if bold == "u":
                uy = (y + h / 2) * k + f.size * 0.55
                d.line([tx, uy, tx + tw, uy], fill="black", width=max(1, round(f.size / 14)))
        elif t == "img":
            _, path, x, y, w, h = op
            try:
                sg = Image.open(path).convert("RGBA").resize((max(1, int(w * k)), max(1, int(h * k))))
                im.paste(sg, (int(x * k), int(y * k)), sg)
            except Exception:
                pass
    return im


# ---------------------------------------------------------------- Tk canvas
def draw_tk(canvas, page, k, family, tkfont):
    """k = พิกเซลต่อมม. ; tkfont = tkinter.font module"""
    canvas.delete("all")
    canvas.create_rectangle(0, 0, page.w * k, page.h * k, fill="white", outline="#999")
    cache = {}

    def mk(px, bold):
        key = (round(px), bold)
        if key not in cache:
            cache[key] = tkfont.Font(family=family, size=-max(5, round(px)), weight="bold" if bold else "normal",
                                     underline=1 if bold == "u" else 0)
        return cache[key]

    imgs = []
    fac = fit_factors(page, k, lambda tx, px, b: mk(px, b).measure(tx))
    for oi, op in enumerate(page.ops):
        t = op[0]
        if t == "fill":
            _, x, y, w, h, g = op
            canvas.create_rectangle(x * k, y * k, (x + w) * k, (y + h) * k, fill="#%02x%02x%02x" % (g, g, g), outline="")
        elif t == "line":
            _, x1, y1, x2, y2, w, dash = op
            canvas.create_line(x1 * k, y1 * k, x2 * k, y2 * k, width=max(1, w * k), dash=(2, 3) if dash else None)
        elif t == "text":
            _, x, y, w, h, text, al, pt, bold, _g = op[:10]
            px = pt * 25.4 / 72 * k
            f = mk(px * fac[oi], bold)
            tw = f.measure(text)
            tx = x * k + (0 if al == "l" else (w * k - tw) / 2 if al == "c" else w * k - tw)
            canvas.create_text(tx, (y + h / 2) * k, text=text, font=f, anchor="w", fill=("#%02x%02x%02x" % op[10]) if len(op) > 10 else "black")
        elif t == "img":
            try:
                from PIL import Image, ImageTk
                _, path, x, y, w, h = op
                im = Image.open(path).convert("RGBA").resize((max(1, int(w * k)), max(1, int(h * k))))
                ph = ImageTk.PhotoImage(im)
                imgs.append(ph)
                canvas.create_image(x * k, y * k, image=ph, anchor="nw")
            except Exception:
                pass
    canvas._imgs = imgs


# ---------------------------------------------------------------- Windows GDI
def list_printers():
    try:
        import win32print
        fl = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(fl)]
    except Exception:
        return []


def default_printer():
    try:
        import win32print
        return win32print.GetDefaultPrinter()
    except Exception:
        return ""


class GdiPrinter:
    """พิมพ์ pages ผ่าน GDI (Windows จัดรูปตัวอักษรไทยให้เอง) 1 เอกสาร = 1 StartDoc"""

    def __init__(self, printer, paper, landscape, font, copies=1, rot=False):
        import win32con
        import win32gui
        import win32print
        import win32ui
        self.w32 = (win32con, win32gui, win32print, win32ui)
        printer = printer or win32print.GetDefaultPrinter()
        h = win32print.OpenPrinter(printer)
        try:
            dm = win32print.GetPrinter(h, 2)["pDevMode"]
        finally:
            win32print.ClosePrinter(h)
        dm.PaperSize = paper
        dm.Orientation = 2 if landscape else 1
        dm.Copies = max(1, int(copies))
        dm.Fields |= win32con.DM_PAPERSIZE | win32con.DM_ORIENTATION | win32con.DM_COPIES
        hdc = win32gui.CreateDC("WINSPOOL", printer, dm)
        self.dc = win32ui.CreateDCFromHandle(hdc)
        self.font = font
        self.dpx = self.dc.GetDeviceCaps(88)       # LOGPIXELSX
        self.dpy = self.dc.GetDeviceCaps(90)
        self.ox = self.dc.GetDeviceCaps(112)       # PHYSICALOFFSETX
        self.oy = self.dc.GetDeviceCaps(113)
        self._fonts = {}
        self.rot = rot         # หมุนเนื้อหา (แนวนอน) 90° ลงกระดาษแนวตั้ง เช่น ซองป้อนด้านสั้น
        self._rf = {}

    def _font(self, px, bold):
        key = (round(px), bold)
        if key not in self._fonts:
            self._fonts[key] = self.w32[3].CreateFont({"name": self.font, "height": -max(5, round(px)),
                                                       "weight": 700 if bold else 400, "charset": 222,
                                                       "underline": 1 if bold == "u" else 0})
        return self._fonts[key]

    def print_doc(self, pages, title, cancel=lambda: False):
        dc = self.dc
        dc.StartDoc(title)
        try:
            for pg in pages:
                if cancel():
                    break
                dc.StartPage()
                dc.SetMapMode(1)
                dc.SetBkMode(1)
                self._draw(pg)
                dc.EndPage()
            dc.EndDoc()
        except Exception:
            try:
                dc.AbortDoc()
            except Exception:
                pass
            raise

    def close(self):
        try:
            self.dc.DeleteDC()
        except Exception:
            pass

    def _draw(self, pg):
        win32con, win32gui, win32print, win32ui = self.w32
        dc = self.dc
        kx, ky = self.dpx / 25.4, self.dpy / 25.4
        X = lambda mm: int(round(mm * kx - self.ox))
        Y = lambda mm: int(round(mm * ky - self.oy))
        if self.rot:
            H = pg.h
            PX = lambda u, v: int(round((H - v) * kx - self.ox))       # (u,v) มม. บนหน้าแนวนอน -> พิกัดอุปกรณ์แนวตั้ง
            PY = lambda u, v: int(round(u * ky - self.oy))
        def meas(tx, px, b):
            old = dc.SelectObject(self._font(px, b))
            wd = dc.GetTextExtent(tx)[0]
            dc.SelectObject(old)
            return wd
        fac = fit_factors(pg, kx, meas)
        for oi, op in enumerate(pg.ops):
            t = op[0]
            if t == "fill":
                _, x, y, w, h, g = op
                br = win32ui.CreateBrush(0, g * 0x010101, 0)
                if self.rot:
                    dc.FillRect((PX(x, y + h), PY(x, y), PX(x, y), PY(x + w, y)), br)
                else:
                    dc.FillRect((X(x), Y(y), X(x + w), Y(y + h)), br)
            elif t == "line":
                _, x1, y1, x2, y2, w, dash = op
                pen = win32ui.CreatePen(2 if dash else 0, max(1, int(round(w * kx))), 0)
                old = dc.SelectObject(pen)
                if self.rot:
                    dc.MoveTo((PX(x1, y1), PY(x1, y1)))
                    dc.LineTo((PX(x2, y2), PY(x2, y2)))
                else:
                    dc.MoveTo((X(x1), Y(y1)))
                    dc.LineTo((X(x2), Y(y2)))
                dc.SelectObject(old)
            elif t == "text":
                _, x, y, w, h, text, al, pt, bold, _g = op[:10]
                px = pt / 72 * self.dpy
                old = dc.SelectObject(self._font(px * fac[oi], bold))
                dc.SetTextColor(op[10][0] | (op[10][1] << 8) | (op[10][2] << 16) if len(op) > 10 else 0)
                tw = dc.GetTextExtent(text)[0]
                th = dc.GetTextExtent(text)[1]
                tx = X(x) + (0 if al == "l" else int((w * kx - tw) / 2) if al == "c" else int(w * kx - tw))
                ty = Y(y) + int((h * ky - th) / 2)
                if self.rot:
                    dc.SelectObject(old)
                    self._rtext(PX((tx + self.ox) / kx, (ty + self.oy) / ky), PY((tx + self.ox) / kx, (ty + self.oy) / ky), text, px * fac[oi], bold)
                else:
                    dc.TextOut(tx, ty, text)
                    dc.SelectObject(old)
            elif t == "img":
                if self.rot:
                    _, path, x, y, w, h = op
                    self._img(op, lambda m: PX(m, 0), lambda m: PY(0, 0), kx, ky, rotate=(PX(x, y + h), PY(x, y), h, w))
                else:
                    self._img(op, X, Y, kx, ky)

    def _rtext(self, x, y, text, px, bold):
        """ข้อความหมุน 90° ตามเข็ม (escapement 2700) ด้วย gdi32 ตรง ๆ -- ใช้ ctypes ธรรมดา"""
        import ctypes
        gdi = ctypes.windll.gdi32
        key = (round(px), bold)
        if key not in self._rf:
            gdi.CreateFontW.restype = ctypes.c_void_p
            self._rf[key] = gdi.CreateFontW(-max(5, round(px)), 0, 2700, 2700, 700 if bold else 400, 0, 1 if bold == "u" else 0, 0,
                                            222, 0, 0, 0, 0, self.font)
        hdc = self.dc.GetSafeHdc()
        gdi.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        gdi.SelectObject.restype = ctypes.c_void_p
        gdi.TextOutW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]
        old = gdi.SelectObject(hdc, self._rf[key])
        gdi.TextOutW(hdc, x, y, text, len(text))
        gdi.SelectObject(hdc, old)

    def _img(self, op, X, Y, kx, ky, rotate=None):
        """ลายเซ็น: ส่งภาพ DIB ตรงไปเครื่องพิมพ์ด้วย StretchDIBits (ไดรเวอร์เครื่องพิมพ์รองรับกว่า BitBlt จาก memory DC)
        โหมด SRCAND: พื้นขาวไม่ทับตัวอักษรข้างใต้ ถ้าไดรเวอร์ไม่รับ SRCAND จะลองแบบ SRCCOPY (พื้นขาว) แทน"""
        import ctypes
        c = ctypes
        from PIL import Image
        _, path, x, y, w, h = op
        if rotate:                                                      # (x, y, w_mm, h_mm) ของกรอบหลังหมุนแล้ว
            rx, ry, w, h = rotate
            X, Y = (lambda m, _v=rx: _v), (lambda m, _v=ry: _v)
            x = y = 0
        pw, ph = max(1, int(w * kx)), max(1, int(h * ky))
        sw, sh = min(pw * 2, 1600), min(ph * 2, 1600)                  # ความละเอียดต้นทางสูงกว่าปลายทางเล็กน้อย
        im = Image.open(path).convert("RGBA")
        if rotate:
            im = im.rotate(-90, expand=True)
        im = im.resize((sw, sh))
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        raw = bg.convert("RGB").tobytes("raw", "BGRX")

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", c.c_uint32), ("biWidth", c.c_int32), ("biHeight", c.c_int32),
                        ("biPlanes", c.c_uint16), ("biBitCount", c.c_uint16), ("biCompression", c.c_uint32),
                        ("biSizeImage", c.c_uint32), ("biXPelsPerMeter", c.c_int32), ("biYPelsPerMeter", c.c_int32),
                        ("biClrUsed", c.c_uint32), ("biClrImportant", c.c_uint32)]
        bih = BIH(40, sw, -sh, 1, 32, 0, len(raw), 0, 0, 0, 0)         # ความสูงติดลบ = เรียงบนลงล่าง
        buf = ctypes.create_string_buffer(raw, len(raw))
        gdi = ctypes.windll.gdi32
        gdi.StretchDIBits.argtypes = [c.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_void_p, ctypes.c_void_p, c.c_uint, c.c_uint32]
        gdi.StretchDIBits.restype = ctypes.c_int
        gdi.SetStretchBltMode.argtypes = [c.c_void_p, ctypes.c_int]
        hdc = self.dc.GetSafeHdc()
        gdi.SetStretchBltMode(hdc, 4)                                  # HALFTONE
        for rop in (0x008800C6, 0x00CC0020):                           # SRCAND แล้วค่อย SRCCOPY
            r = gdi.StretchDIBits(hdc, X(x), Y(y), pw, ph, 0, 0, sw, sh, buf, ctypes.byref(bih), 0, rop)
            if r not in (0, -1):
                return
        raise RuntimeError("พิมพ์ลายเซ็นไม่สำเร็จ (ไดรเวอร์เครื่องพิมพ์ไม่รับภาพ)")
