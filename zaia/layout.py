"""แบบพิมพ์ -> รายการคำสั่งวาด (หน่วยมิลลิเมตร) ใช้ร่วมกันทั้งพรีวิว / เครื่องพิมพ์ / ภาพทดสอบ

ops:
  ('line', x1, y1, x2, y2, w, dashed)
  ('text', x, y, w, h, text, align['l'|'c'|'r'], pt, bold, grp)   วางกึ่งกลางแนวตั้งใน h, ย่อให้พอดีกว้าง w (grp เดียวกัน = ย่อเท่ากัน)
  ('fill', x, y, w, h, gray 0-255)
  ('img', path, x, y, w, h)
"""
import os

LINE = 20.25 * 25.4 / 72          # ความสูงแถวมาตรฐานใน Excel (มม.)
PT = 25.4 / 72
PAD = 1.1
FORMS = {
    "reg": dict(title="บัญชีตรวจสอบสภาพ", paper=5, landscape=True, w=355.6, h=215.9, ml=6, mr=6, mt=8, mb=10),
    "sum": dict(title="บัญชีสรุปผลการตรวจสอบ", paper=9, landscape=True, w=297, h=210, ml=10, mr=10, mt=8, mb=8),
    "send": dict(title="แบบส่งผู้ใหญ่บ้าน", paper=9, landscape=True, w=297, h=210, ml=10, mr=10, mt=8, mb=8),
    "form": dict(title="แบบพิมพ์รายบุคคล", paper=9, landscape=False, w=210, h=297, ml=6.35, mr=6.35, mt=10, mb=8),
    "env": dict(title="จ่าหน้าซอง (ด้านหลัง A4 พับสาม)", paper=9, landscape=False, w=210, h=297, ml=0, mr=0, mt=0, mb=0),
}


# ---- ค่าที่ผู้ใช้ปรับเองได้ (หน้า ตั้งค่า > ปรับแบบพิมพ์)  ชนิด: n=ตัวเลข  t=ข้อความ  b=เปิด/ปิด
# ตัวแปรในข้อความ: {year} {amphoe} {province} {tel} {deadline} {ptype} {tambon}
_G = [("dx", "เลื่อนทั้งหน้า ซ้าย(-)/ขวา(+) มม.", "n", 0), ("dy", "เลื่อนทั้งหน้า บน(-)/ล่าง(+) มม.", "n", 0),
      ("fs", "ขนาดตัวอักษรทั้งแบบ (%)", "n", 100)]
SCHEMA = {
    "form": ("แบบพิมพ์รายบุคคล (เมนู 2)", _G + [
        ("ls", "ระยะห่างระหว่างบรรทัด (%)", "n", 100),
        ("t_title", "หัวเรื่อง", "t", "รายละเอียดการตรวจสอบสภาพทหารกองหนุน ประจำปี {year}"),
        ("t_unit", "บรรทัดสัสดี/เบอร์โทร", "t", "สัสดีอำเภอ{amphoe} โทร {tel}"),
        ("t_return", "ข้อ 5 ส่งคืน (สีแดง)", "t", "5.กรุณาส่งคืน  หน่วยสัสดีอำเภอ{amphoe} ภายในวันที่ {deadline}"),
        ("t_cert", "ข้อความรับรอง", "t", "ขอรับรองว่าได้ตรวจสอบข้อมูลจากทหารกองหนุนจริง"),
        ("t_headman", "ตำแหน่งผู้ลงนาม", "t", "ผู้ใหญ่บ้าน"),
        ("t_note1", "หมายเหตุ บรรทัด 1", "t", "หมายเหตุ  ตามพระราชบัญญัติรับราชการทหาร พ.ศ.2497  มาตรา 47  ทหารกองเกินและ"),
        ("t_note2", "หมายเหตุ บรรทัด 2", "t", "ทหารกองหนุนผู้ใด ไม่มาเข้ารับการเรียกพลเพื่อตรวจสอบ ตามมาตรา 36 ต้องระวางโทษ"),
        ("t_note3", "หมายเหตุ บรรทัด 3", "t", "ทั้งจำคุกและปรับ"),
        ("b_status", "แสดงหัวข้อ 3 สถานภาพปัจจุบัน", "b", True),
        ("b_phone", "แสดงหัวข้อ 4 เบอร์โทรศัพท์", "b", True),
        ("b_cert", "แสดงช่องรับรอง/ลงชื่อผู้ใหญ่บ้าน", "b", True),
        ("b_note", "แสดงหมายเหตุท้ายแบบ", "b", True)]),
    "env": ("จ่าหน้าซอง (เมนู 2)", _G + [
        ("t_dear", "คำขึ้นต้นผู้รับ", "t", "เรียน"),
        ("gh", "ความสูงตราครุฑ (มม.)", "n", 25),
        ("b_garuda", "แสดงตราครุฑ", "b", True),
        ("b_fold", "แสดงเส้นประรอยพับสาม", "b", True)]),
    "reg": ("บัญชีตรวจสอบสภาพ (เมนู 5)", _G + [
        ("t_title", "หัวเรื่อง", "t", "บัญชีตรวจสอบสภาพทหารกองหนุน"),
        ("t_form", "เลขแบบ (มุมขวาบน)", "t", "ทบ. 100 - 070"),
        ("t_red", "ข้อความสีแดงมุมขวาบน", "t", "ตรวจสอบสภาพทหารกองหนุนประจำปี {year}")]),
    "sum": ("บัญชีสรุปผลการตรวจสอบ (เมนู 6)", _G + [
        ("t_title", "หัวเรื่อง", "t", "บัญชีรายชื่อการตรวจสอบสภาพทหารกองหนุนประจำปี {year} ประเภท {ptype}")]),
    "send": ("ส่งผู้ใหญ่บ้านตรวจสอบ (เมนู 3)", _G + [
        ("t_title", "หัวเรื่อง", "t", "บัญชีรายชื่อการตรวจสอบสภาพทหารกองหนุนประจำปี {year} ประเภท {ptype}")]),
}


def tp(st, kind):
    """ค่าแบบพิมพ์ = ค่าเริ่มต้น + ที่ผู้ใช้ปรับ (st['tpl'][kind])"""
    d = {k: v for k, _l, _t, v in SCHEMA[kind][1]}
    d.update({k: v for k, v in (st.get("tpl", {}).get(kind, {}) or {}).items() if k in d})
    return d


def fmt(text, **kw):
    for k, v in kw.items():
        text = text.replace("{%s}" % k, str(v))
    return text


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _apply_global(pages, o):
    """เลื่อนทั้งหน้า (dx,dy) และปรับขนาดตัวอักษร (fs%) กับทุกคำสั่งวาด"""
    dx, dy, fs = _num(o.get("dx"), 0), _num(o.get("dy"), 0), _num(o.get("fs"), 100) / 100.0
    if not dx and not dy and abs(fs - 1) < 1e-9:
        return pages
    for pg in pages:
        new = []
        for op in pg.ops:
            t = op[0]
            if t == "line":
                op = (t, op[1] + dx, op[2] + dy, op[3] + dx, op[4] + dy) + op[5:]
            elif t == "text":
                op = (t, op[1] + dx, op[2] + dy) + op[3:7] + (op[7] * fs,) + op[8:]
            elif t == "fill":
                op = (t, op[1] + dx, op[2] + dy) + op[3:]
            elif t == "img":
                op = (t, op[1], op[2] + dx, op[3] + dy) + op[4:]
            new.append(op)
        pg.ops = new
    return pages


class Page:
    def __init__(self, w, h):
        self.w, self.h, self.ops = w, h, []


def chars_mm(w):
    return (w * 7 + 5) / 96 * 25.4


def signer_lines(st, level, tambon=""):
    key = {"กำนัน": "sign_kamnan", "อำเภอ": "sign_amphoe", "จังหวัด": "sign_province"}[level]
    return [str(x).replace("{ตำบล}", tambon).rstrip() for x in st.get(key, [])]   # ชิดซ้าย เคาะวรรคเลื่อนเอง


SIG_LIFT = 0.15      # ค่าเริ่มต้น: ลายเซ็นอยู่เหนือบรรทัดชื่อผู้ลงนาม (ปรับเลื่อนได้ในตั้งค่า)


def sig_name_index(level):
    return {"อำเภอ": 2, "กำนัน": 1, "จังหวัด": 0}[level]


def paginate(n, ph, avail1, avail2, block_h, cap1=None, cap2=None):
    """แบ่งคนเป็นหน้า: คืนจำนวนคนต่อหน้า; บล็อกลงนามต้องอยู่หน้าเดียวกับคนอย่างน้อย 1 คน"""
    c1 = max(1, int(avail1 // ph + 1e-9))
    c2 = max(1, int(avail2 // ph + 1e-9))
    c1 = min(c1, cap1 or c1)
    c2 = min(c2, cap2 or c2)
    sizes, left, first = [], n, True
    while left > 0:
        c = c1 if first else c2
        k = min(c, left)
        sizes.append(k)
        left -= k
        first = False
    if sizes:
        a = avail1 if len(sizes) == 1 else avail2
        if a - sizes[-1] * ph < block_h - 1e-6 and sizes[-1] > 1:
            sizes[-1] -= 1
            sizes.append(1)
        elif a - sizes[-1] * ph < block_h - 1e-6:
            sizes.append(0)          # กรณีสุดวิสัย (หน้าหนึ่งคนเดียวแล้วไม่พอ) -> บล็อกขึ้นหน้าใหม่
    return sizes


class _Ctx:
    def __init__(self, kind, st, persons, ptype, tambon, level, fontscale=1.0):
        self.kind, self.st, self.persons = kind, st, persons
        self.ptype, self.tambon, self.level = ptype, tambon, level
        self.g = FORMS[kind]
        self.s = 1.0


def _t(pg, x, y, w, h, text, align="c", pt=16, bold=False, grp=None, color=None):
    if text != "" and text is not None:
        if w > 6:                       # เว้นขอบในช่อง ไม่ให้ข้อความชนเส้น
            x, w = x + PAD, w - 2 * PAD
        op = ("text", x, y - 0.35, w, h, str(text), align, pt, bold, grp)
        pg.ops.append(op + (color,) if color else op)


def _ln(pg, x1, y1, x2, y2, w=0.25, dash=False):
    pg.ops.append(("line", x1, y1, x2, y2, w, dash))


def _sign_block(pg, ctx, x0, x1, y, Lh, pt):
    st, lvl = ctx.st, ctx.level
    lines = signer_lines(st, lvl, ctx.tambon if ctx.tambon and ctx.tambon != "ทุกตำบล" else "")
    if ctx.kind == "send":
        lines = [l.replace("ได้ตรวจถูกต้องแล้ว", "ตรวจถูกต้อง") for l in lines]
    for i, tx in enumerate(lines):
        _t(pg, x0, y + i * Lh, x1 - x0, Lh, tx, "l", pt, False, "sg")
    img = st.get("sig_image")
    if img and os.path.exists(img) and st.get("sig_level", "อำเภอ") == lvl:
        try:
            from PIL import Image
            with Image.open(img) as im:
                ar = im.height / im.width
        except Exception:
            return len(lines)
        w = float(st.get("sig_w", 32)) * ctx.s
        h = w * ar
        cx = x0 + PAD + 40 + float(st.get("sig_dx", 0))     # อ้างอิงขอบซ้ายกล่อง เหมือนตัวอย่างในหน้าตั้งค่า
        cy = y + (sig_name_index(lvl) - SIG_LIFT) * Lh + float(st.get("sig_dy", 0))
        pg.ops.append(("img", img, cx - w / 2, cy - h / 2, w, h))
    return len(lines)


def _tag_h(ctx, Lh):
    """หน้า 2 เป็นต้นไป: เว้น 1 บรรทัดบนสุดไว้ใส่ชื่อตำบลมุมขวา (ปิดได้ที่ตั้งค่า show_tambon_p2)"""
    t = ctx.tambon
    return Lh if (ctx.st.get("show_tambon_p2", True) and t and t != "ทุกตำบล") else 0.0


def _tag(pg, ctx, x1, y, Lh, pt):
    _t(pg, x1 - 60, y, 60, Lh, "ตำบล" + ctx.tambon, "r", pt, False)


def _p(p, k):
    return str(p.get(k, "") or "")


# ============================================================ บัญชีตรวจสอบสภาพ (reg)
def build_reg(ctx):
    g, st = ctx.g, ctx.st
    wch = [7.4, 22, 9.2, 13.2, 14.6, 11.2, 9.4, 10.6, 4, 17, 12.9, 9.9, 12.6, 7.8]
    cw = [chars_mm(w) for w in wch]
    usable = g["w"] - g["ml"] - g["mr"]
    s = min(1.0, usable / sum(cw))
    ctx.s = s
    cw = [w * s for w in cw]
    tw = sum(cw)
    x0 = g["ml"] + (usable - tw) / 2
    xs = [x0]
    for w in cw:
        xs.append(xs[-1] + w)
    Lh, pt = LINE * s, 16 * s
    title_h = 26.25 * 25.4 / 72 * s
    hdr_lines = 3
    o = tp(st, "reg")
    h_title = title_h + 3 * Lh + Lh        # แถว 1-5
    h_tab = hdr_lines * Lh
    avail = g["h"] - g["mt"] - g["mb"]
    ph = 3 * Lh
    th = _tag_h(ctx, Lh)
    sizes = paginate(len(ctx.persons), ph, avail - h_title - h_tab, avail - h_tab - th, 5 * Lh if ctx.level == "อำเภอ" else 3 * Lh, 5, 7)   # เทมเพลต: หน้าแรก 5 คน หน้าถัดไป 7 คน ไม่ซ้ำหัวตาราง
    pages, idx = [], 0
    for pn, k in enumerate(sizes):
        pg = Page(g["w"], g["h"])
        y = g["mt"]
        if pn == 0:
            _t(pg, xs[0], y, tw, title_h, fmt(o["t_title"], year=st.get("year", "")), "c", 20 * s, "u")
            # กล่องข้อความมุมขวาบนตามเทมเพลต Excel: "ทบ. 100 - 070" (ชิดขวา) และข้อความสีแดงด้านล่าง (ระยะ EMU/36000 = มม., เว้นขอบกล่อง 2.54 มม.)
            m0, ins = g["mt"], 2.54 * s
            xa, xb = xs[12] + 1.85 * s + ins, xs[13] + 15.6 * s - ins
            _t(pg, xa, m0 + 0.8 * s + 1.27 * s, xb - xa, Lh, o["t_form"], "r", pt)
            xa, xb = xs[10] + 15.35 * s + ins, xs[13] + 15.9 * s - ins
            _t(pg, xa, m0 + 5.8 * s + 1.27 * s, xb - xa, Lh, fmt(o["t_red"], year=st.get("year", 2570)), "l", pt, color=(255, 0, 0))
            y += title_h
            tam = ctx.tambon if ctx.tambon else ""
            info = [("สำหรับ", ctx.ptype, "แผนก", "ทหารบก"),
                    ("จังหวัด", st.get("_province", ""), "อำเภอ", st.get("_amphoe", "")),
                    ("ตำบล", tam, "", "")]
            for i, (a, b, c, d) in enumerate(info):
                yy = y + i * Lh
                _t(pg, xs[4], yy, cw[4], Lh, a, "l", pt)
                _t(pg, xs[5], yy, cw[5] + cw[6], Lh, b, "c", pt)
                _ln(pg, xs[5], yy + Lh - 0.6, xs[7], yy + Lh - 0.6, 0.2, True)
                if c:
                    _t(pg, xs[7], yy, cw[7], Lh, c, "l", pt)
                    _t(pg, xs[8], yy, cw[8] + cw[9], Lh, d, "c", pt)
                    _ln(pg, xs[8], yy + Lh - 0.6, xs[10], yy + Lh - 0.6, 0.2, True)
            y += 4 * Lh
        elif th:
            _tag(pg, ctx, xs[14], y, Lh, pt)
            y += th
        # หัวตาราง
        yt = y
        yb = y + h_tab
        _ln(pg, xs[0], yt, xs[14], yt, 0.35)
        _ln(pg, xs[0], yb, xs[14], yb, 0.35)
        for i in (0, 1, 2, 5, 7, 13, 14):
            _ln(pg, xs[i], yt, xs[i], yb, 0.35)
        _ln(pg, xs[3], yt, xs[3], yb, 0.25)
        _ln(pg, xs[4], yt + Lh, xs[4], yb, 0.25)      # ไม่ขีดผ่านคำว่า "ชื่อ"
        _ln(pg, xs[6], yt, xs[6], yb, 0.25)
        _ln(pg, xs[3], yt + Lh, xs[5], yt + Lh, 0.25)
        _ln(pg, xs[7], yt + Lh, xs[13], yt + Lh, 0.25)
        for i in (8, 9, 10, 11, 12):
            _ln(pg, xs[i], yt + Lh, xs[i], yb, 0.25)
        c = lambda i, j=None: (xs[i], (xs[(j or i) + 1] - xs[i]))
        _t(pg, xs[0], yt, cw[0], h_tab, "ลำดับ", "c", pt * 0.85)
        _t(pg, xs[1], yt, cw[1], h_tab, "ยศ, ชื่อ", "c", pt)
        _t(pg, xs[2], yt, cw[2], Lh, "เครื่องหมาย", "c", pt * 0.8)
        _t(pg, xs[2], yt + Lh, cw[2], Lh, "(เหล่า)", "c", pt)
        _t(pg, xs[3], yt, cw[3] + cw[4], Lh, "ชื่อ", "c", pt)
        _t(pg, xs[3], yt + Lh, cw[3], 2 * Lh, "บิดา", "c", pt)
        _t(pg, xs[4], yt + Lh, cw[4], 2 * Lh, "มารดา", "c", pt)
        for j, tx in enumerate(["บ้านที่", "ที่", "หมู่ที่"]):
            _t(pg, xs[5], yt + j * Lh, cw[5], Lh, tx, "c", pt)
        for j, tx in enumerate(["ถนน", "ตรอก", "ซอย"]):
            _t(pg, xs[6], yt + j * Lh, cw[6], Lh, tx, "c", pt)
        _t(pg, xs[7], yt, xs[13] - xs[7], Lh, "ตรวจสอบสภาพปรากฏว่า", "c", pt)
        for i, tx in ((7, "มีตัวอยู่หรือไม่"), (8, "ตาย"), (9, "ทุพพลภาพหรือเป็นโรค"), (12, "จำหน่ายชั่วคราว")):
            _t(pg, xs[i], yt + Lh, cw[i], 2 * Lh, tx, "c", pt * 0.85)
        for i, (a, b) in ((10, ("ไปประกอบอาชีพ", "ที่อื่นชั่วคราว")), (11, ("ไปจากท้องที่", "ไม่ทราบที่อยู่"))):
            _t(pg, xs[i], yt + Lh, cw[i], Lh, a, "c", pt * 0.85)
            _t(pg, xs[i], yt + 2 * Lh, cw[i], Lh, b, "c", pt * 0.85)
        _t(pg, xs[13], yt, cw[13], h_tab, "หมายเหตุ", "c", pt * 0.8)
        y = yb
        # คน
        for i in range(k):
            p = ctx.persons[idx]
            n = idx + 1
            idx += 1
            _t(pg, xs[0], y, cw[0], Lh, n, "c", pt)
            _t(pg, xs[1], y, cw[1], Lh, _p(p, "rank") + _p(p, "name"), "l", pt)
            _t(pg, xs[1], y + Lh, cw[1], Lh, _p(p, "surname"), "c", pt)
            _t(pg, xs[1], y + 2 * Lh, cw[1], Lh, _p(p, "nid"), "c", pt)
            _t(pg, xs[2], y, cw[2], Lh, _p(p, "year"), "c", pt)
            _t(pg, xs[2], y + Lh, cw[2], Lh, _p(p, "mark"), "c", pt)
            _t(pg, xs[2], y + 2 * Lh, cw[2], Lh, _p(p, "branch"), "c", pt)
            _t(pg, xs[3], y, cw[3], Lh, _p(p, "father"), "c", pt)
            _t(pg, xs[3], y + Lh, cw[3], Lh, _p(p, "fsur"), "c", pt)
            _t(pg, xs[4], y, cw[4], Lh, _p(p, "mother"), "c", pt)
            _t(pg, xs[4], y + Lh, cw[4], Lh, _p(p, "msur"), "c", pt)
            _t(pg, xs[5], y, cw[5], Lh, _p(p, "house"), "c", pt)
            _t(pg, xs[5], y + Lh, cw[5], Lh, _p(p, "moo"), "c", pt)
            wr = xs[13] - xs[7]
            _t(pg, xs[7] + 1, y, wr - 1, Lh, "- %s (%s) %s" % (_p(p, "result"), _p(p, "status"), _p(p, "place")), "l", pt, grp=idx)
            _t(pg, xs[7] + 1, y + Lh, wr - 1, Lh, "- (อำเภอ) %s (จังหวัด) %s (โทรศัพท์ที่ทำงาน) %s" % (_p(p, "amphoe2"), _p(p, "prov2"), _p(p, "tel_work")), "l", pt, grp=idx)
            _t(pg, xs[7] + 1, y + 2 * Lh, wr - 1, Lh, "- (โทรศัพท์เจ้าตัว) %s ,(โทรศัพท์ผู้ปกครอง) %s" % (_p(p, "tel"), _p(p, "tel_par")), "l", pt, grp=idx)
            for j in (0, 1, 2, 5, 7, 13, 14):
                _ln(pg, xs[j], y, xs[j], y + ph, 0.35)
            for j in (3, 4, 6):
                _ln(pg, xs[j], y, xs[j], y + ph, 0.25)
            _ln(pg, xs[0], y + ph, xs[14], y + ph, 0.35)
            y += ph
        if pn == len(sizes) - 1:
            _sign_block(pg, ctx, xs[7], xs[13], y, Lh, pt)
        pages.append(pg)
    return pages


# ============================================================ บัญชีสรุป (sum) / ส่งผู้ใหญ่บ้าน (send)
# ส่งผู้ใหญ่บ้าน = แบบเดียวกับบัญชีสรุปทุกประการ (A4 แนวนอน) แต่ช่อง G H I ว่าง ให้ผู้ใหญ่บ้านกรอก + แถวตัวอย่าง ลำดับ 1
def build_table(ctx):
    g, st = ctx.g, ctx.st
    send = ctx.kind == "send"
    wch = [5.5, 11.1, 13.5, 9.6, 7.4, 21.5, 17.5, 34.2, 12.1]
    cw = [chars_mm(w) for w in wch]
    usable = g["w"] - g["ml"] - g["mr"]
    s = min(1.0, usable / sum(cw))
    ctx.s = s
    cw = [w * s for w in cw]
    tw = sum(cw)
    x0 = g["ml"] + (usable - tw) / 2
    xs = [x0]
    for w in cw:
        xs.append(xs[-1] + w)
    Lh, pt = LINE * s, 16 * s
    ph = 3 * Lh
    h_tab = 3 * Lh
    year = st.get("year", "2570")
    title = fmt(tp(st, ctx.kind)["t_title"], year=year, ptype=ctx.ptype)
    h_title = 3 * Lh
    avail = g["h"] - g["mt"] - g["mb"]
    block = {"อำเภอ": 5, "กำนัน": 3, "จังหวัด": 1}[ctx.level] * Lh
    th = 0.0 if send else _tag_h(ctx, Lh)
    sizes = paginate(len(ctx.persons), ph, avail - h_title - h_tab - (ph if send else 0), avail - h_tab - th, block)
    pages, idx = [], 0
    for pn, k in enumerate(sizes):
        pg = Page(g["w"], g["h"])
        y = g["mt"]
        if pn == 0:
            _t(pg, xs[0], y, tw, Lh, title, "c", 16 * s, True)
            y += Lh
            _t(pg, xs[0], y, tw, Lh, "อำเภอ%s   จังหวัด%s" % (st.get("_amphoe", ""), st.get("_province", "")), "c", pt, True)
            y += 2 * Lh
        elif th and not send:
            _tag(pg, ctx, xs[9], y, Lh, pt)
            y += th
        yt, yb = y, y + h_tab
        _ln(pg, xs[0], yt, xs[9], yt, 0.35)
        _ln(pg, xs[0], yb, xs[9], yb, 0.35)
        for i in (0, 1, 3, 4, 9):
            _ln(pg, xs[i], yt, xs[i], yb, 0.35)
        for i in (5, 6, 7, 8):
            _ln(pg, xs[i], yt + Lh, xs[i], yb, 0.25)
        _ln(pg, xs[4], yt + Lh, xs[9], yt + Lh, 0.25)
        _t(pg, xs[0], yt, cw[0], h_tab, "ลำดับ", "c", pt * 0.85, True)
        _t(pg, xs[1], yt, cw[1] + cw[2], h_tab, "ยศ - ชื่อ- สกุล", "c", pt, True)
        _t(pg, xs[3], yt, cw[3], h_tab, "เครื่องหมาย", "c", pt * 0.85, True)
        _t(pg, xs[4], yt, xs[9] - xs[4], Lh, "ผลการตรวจสอบสภาพทหารกองหนุนประจำปี %s" % year, "c", pt, True)
        for i, tx in ((4, "มีตัว/\nไม่มีตัว"), (5, "ที่อยู่ปัจจุบัน"), (6, "หมายเลขโทรศัพท์\nที่ติดต่อได้ (ปัจจุบัน)"),
                      (7, "สถานภาพ\n(ทำงาน,ศึกษา,ว่างงาน)"), (8, "หมายเหตุ")):
            lines = tx.split("\n")
            for j, l in enumerate(lines):
                off = 1 + (2 - len(lines)) / 2
                _t(pg, xs[i], yt + (off + j) * Lh, cw[i], Lh, l, "c", pt * (0.85 if len(l) > 14 else 1), True)
        y = yb

        def row_border(yy):
            for j in (0, 1, 3, 4, 5, 6, 7, 8, 9):
                _ln(pg, xs[j], yy, xs[j], yy + ph, 0.35 if j in (0, 1, 3, 4, 9) else 0.25)
            _ln(pg, xs[0], yy + ph, xs[9], yy + ph, 0.35)
            for r_ in (1, 2):                       # เทมเพลต: เส้น hair คั่นบรรทัดในแต่ละคน
                _ln(pg, xs[0], yy + r_ * Lh, xs[9], yy + r_ * Lh, 0.1, True)

        def lines3(yy, A, B, C, D, E, F, G, H, I, grp=None):
            """ค่าแต่ละช่อง = (บรรทัด1, บรรทัด2, บรรทัด3)"""
            for j in range(3):
                yj = yy + j * Lh
                if A[j] != "":
                    _t(pg, xs[0], yj, cw[0], Lh, A[j], "c", pt * (0.6 if j == 1 else 1))
            _t(pg, xs[1], yy, cw[1] + cw[2], Lh, B, "l", pt)
            _t(pg, xs[2], yy + Lh, cw[2], Lh, C, "l", pt)
            _t(pg, xs[1], yy + 2 * Lh, cw[1] + cw[2], Lh, D, "c", pt)
            for j in range(3):
                yj = yy + j * Lh
                _t(pg, xs[3], yj, cw[3], Lh, E[j], "c", pt)
                _t(pg, xs[4], yj, cw[4], Lh, F[j], "c", pt * (0.85 if len(str(F[j])) > 6 else 1))
                _t(pg, xs[5], yj, cw[5], Lh, G[j], "l", pt)
                _t(pg, xs[6], yj, cw[6], Lh, H[j], "c", pt)
                _t(pg, xs[7], yj, cw[7], Lh, I[j], "l", pt)
            row_border(yy)

        if send and pn == 0:       # แถวตัวอย่าง (ลำดับ 1) กรอกแบบละเอียด
            pg.ops.append(("fill", xs[0], y, tw, ph, 235))
            lines3(y, (1, "ตัวอย่าง", ""), "ส.อ.สมชาย", "ใจดี", "1234567890123",
                   ("ท.บ.2566", "ส.น.0000", "พ."), ("มีตัว", "", ""),
                   ("บ้านเลขที่ 99 ม.5", "ต.ตัวอย่าง", "อ.ตัวอย่าง จ.ตัวอย่าง"),
                   ("081-234-5678", "089-999-9999", "02-123-4567"),
                   ("รับจ้าง (ตัดอ้อย)", "ร้านสมชายการเกษตร", "อ.เมือง จ.ขอนแก่น"), ("", "", ""))
            y += ph
        for i in range(k):
            p = ctx.persons[idx]
            seq = idx + 1 + (1 if send else 0)
            idx += 1
            res = ("", "", "") if send else (_p(p, "result"), "", "")
            tel = ("", "", "") if send else (_p(p, "tel"), _p(p, "tel_par"), _p(p, "tel_work"))
            if send:
                sta = ("", "", "")
            else:
                sta = (_p(p, "status"), _p(p, "place"), ("อ.%s จ.%s" % (_p(p, "amphoe2"), _p(p, "prov2"))) if (_p(p, "amphoe2") or _p(p, "prov2")) else "")
            lines3(y, (seq, "", ""), _p(p, "rank") + _p(p, "name"), _p(p, "surname"), _p(p, "nid"),
                   (_p(p, "year"), _p(p, "mark"), _p(p, "branch")), res,
                   ("บ้านเลขที่ %s ม.%s" % (_p(p, "house"), _p(p, "moo")), "ต." + _p(p, "tambon"), "อ.%s จ.%s" % (_p(p, "amphoe"), _p(p, "province"))),
                   tel, sta, ("", "", ""))
            y += ph
        if pn == len(sizes) - 1:
            _sign_block(pg, ctx, xs[7], xs[8], y, Lh, pt)
        pages.append(pg)
    return pages


# ============================================================ แบบพิมพ์รายบุคคล (form) + จ่าหน้าซอง (env)
def build_form(ctx):
    g, st = ctx.g, ctx.st
    wch = [5.9, 6.4, 8, 4.0, 4.2, 8, 8, 8, 5.2, 6.6, 5.8, 8, 8, 11.1, 8]       # A..O จากเทมเพลต Excel
    cw = [chars_mm(w) for w in wch]
    usable = g["w"] - g["ml"] - g["mr"]
    s = min(1.0, usable / sum(cw))
    cw = [w * s for w in cw]
    xs = [g["ml"] + (usable - sum(cw)) / 2]
    for w in cw:
        xs.append(xs[-1] + w)
    o = tp(st, "form")
    Lh = 23.25 * PT * s * max(0.5, _num(o["ls"], 100) / 100)
    PTS = 18                                    # TH SarabunIT๙ 18 pt (หัวข้อ/ข้อมูล) ป้ายช่องที่อยู่ 16 pt ตามเทมเพลต
    NAVY, RED = (0, 32, 96), (255, 0, 0)
    year = st.get("year", "2570")
    pages = []
    for n, p in enumerate(ctx.persons, 1):
        pg = Page(g["w"], g["h"])
        top = g["mt"]

        def Y(r):                               # แถว 1 (ลำดับที่) ตัดออกแล้ว -> เริ่มที่แถว 2
            gap = (9 if not o["b_status"] and r >= 20 else 0) + (4 if not o["b_phone"] and r >= 24 else 0)   # ซ่อนหัวข้อแล้วดึงบรรทัดที่เหลือขึ้นมา
            return top + (r - 2 - gap) * Lh

        def lab(c1, c2, r, text="", al="l", bold=True, u=False, color=None, pt=None):
            _t(pg, xs[c1], Y(r), xs[c2 + 1] - xs[c1], Lh, text, al, pt or PTS, "u" if (u and bold) else bold, "f%s" % (pt or ""), color)

        def val(c1, c2, r, text="", al="c", bold=False, line=True):
            if line:
                _ln(pg, xs[c1], Y(r) + Lh, xs[c2 + 1], Y(r) + Lh, 0.2, True)
            _t(pg, xs[c1], Y(r), xs[c2 + 1] - xs[c1], Lh, text, al, PTS, bold, None, NAVY)

        def box(c, r, text, dx=0.0):            # ช่องสี่เหลี่ยมให้ติ๊ก + ข้อความ
            sz = 4.3
            bx, by = xs[c] + 1.5 + dx, Y(r) + (Lh - sz) / 2
            for x1, y1, x2, y2 in ((bx, by, bx + sz, by), (bx + sz, by, bx + sz, by + sz), (bx + sz, by + sz, bx, by + sz), (bx, by + sz, bx, by)):
                _ln(pg, x1, y1, x2, y2, 0.35)
            _t(pg, bx + sz + 0.8, Y(r), 30, Lh, text, "l", PTS, True, "f")

        am, pv = _p(p, "amphoe") or st.get("amphoe", ""), _p(p, "province") or st.get("province", "")
        kw = dict(year=year, amphoe=_p(p, "amphoe") or st.get("amphoe", ""), province=_p(p, "province") or st.get("province", ""),
                  tel=st.get("sad_tel", ""), deadline=st.get("deadline", ""), tambon=_p(p, "tambon"))
        lab(0, 14, 2, fmt(o["t_title"], **kw), "c")
        lab(0, 14, 3, "อำเภอ%s   จังหวัด%s" % (am, pv), "c")
        lab(0, 14, 4, fmt(o["t_unit"], **kw), "c")
        lab(1, 1, 5, "1. ยศ"); val(2, 2, 5, _p(p, "rank"), bold=True)
        lab(3, 3, 5, "ชื่อ"); val(4, 7, 5, _p(p, "name"), bold=True)
        lab(8, 8, 5, "สกุล", "c"); val(9, 12, 5, _p(p, "surname"), bold=True)
        lab(1, 3, 6, "เครื่องหมาย", "r"); val(4, 9, 6, ("%s %s" % (_p(p, "year"), _p(p, "mark"))).strip(), bold=True)
        lab(10, 10, 6, "เหล่า"); val(11, 13, 6, _p(p, "branch"))
        lab(1, 5, 7, "หมายเลขประจำตัวประชาชน", "r", False); val(6, 11, 7, _p(p, "nid"))
        lab(1, 2, 8, "บิดาชื่อ", "r", False); val(3, 6, 8, (_p(p, "father") + " " + _p(p, "fsur")).strip())
        lab(7, 8, 8, "มารดาชื่อ", "r"); val(9, 12, 8, (_p(p, "mother") + " " + _p(p, "msur")).strip())
        lab(1, 5, 9, "2. ภูมิลำเนาทหารอยู่บ้านเลขที่"); val(6, 7, 9, _p(p, "house"))
        lab(8, 8, 9, "หมู่ที่", "c"); val(9, 9, 9, _p(p, "moo"))
        lab(10, 10, 9, "ตำบล", "c"); val(11, 13, 9, _p(p, "tambon"))
        lab(1, 2, 10, "อำเภอ", "r", False); val(3, 6, 10, am)
        lab(7, 8, 10, "จังหวัด", "c"); val(9, 12, 10, pv)
        if o["b_status"]:
            lab(1, 14, 11, "3  สถานภาพปัจจุบัน ทำเครื่องหมาย / และระบุสถานที่ปัจจุบัน (ให้ระบุ 1 ข้อ)")

            def addr(r):
                lab(5, 5, r, "อำเภอ", "l", pt=16); val(6, 8, r)
                lab(9, 9, r, "จังหวัด", "l", pt=16); val(10, 12, r)
                lab(13, 13, r, "รหัสไปรษณีย์", "c", pt=16); val(14, 14, r)

            box(1, 12, "ทำงาน"); lab(2, 4, 12, "ทำงานอยู่ที่", "r"); val(5, 14, 12)
            lab(0, 4, 13, "     - รับจ้างทั่วไปโปรดแจ้งรายละเอียด", "l", False, pt=16); addr(13)
            box(1, 14, "ศึกษา"); lab(2, 4, 14, "ศึกษาอยู่ที่", "r"); val(5, 8, 14)
            lab(9, 9, 14, "คณะ", "c"); val(10, 12, 14); lab(12, 13, 14, "ชั้นปีที่", "r"); val(14, 14, 14)
            addr(15)
            box(1, 16, "ว่างงาน"); lab(2, 4, 16, "อาศัยอยู่ที่", "r"); val(5, 14, 16)
            addr(17)
            box(1, 18, "อื่นๆ"); lab(2, 4, 18, "ระบุสถานที่", "r"); val(5, 14, 18)
            lab(0, 3, 19, "     - เช่น ตาย", "l", False, pt=16); lab(4, 4, 19, "ที่อยู่", "l"); addr(19)
        if o["b_phone"]:
            lab(1, 14, 20, "4  เบอร์โทรศัพท์ที่สามารถติดต่อได้ (กรณีกองทัพบกเรียกพลฯ เพื่อฝึกหรือเพื่อตรวจสอบ)")
            for r, tx in ((21, "เบอร์โทรศัพท์ เจ้าตัว"), (22, "เบอร์โทรศัพท์ บิดา มารดา ผู้ปกครอง"), (23, "เบอร์โทรศัพท์ ที่ทำงาน")):
                lab(1, 6, r, tx, "r"); val(7, 12, r); lab(13, 13, r, "โปรดระบุ", "l", False, color=RED)
        lab(1, 14, 24, fmt(o["t_return"], **kw), "l", True, True, RED)
        if o["b_cert"]:
            lab(5, 13, 25, fmt(o["t_cert"], **kw), "l", False)
            lab(5, 5, 26, "(ลงชื่อ)"); val(6, 10, 26); lab(11, 14, 26, fmt(o["t_headman"], **kw), "l", False)
            lab(6, 6, 27, "(", "l", False); lab(10, 10, 27, ")", "r", False)       # วงเล็บซ้าย-ขวายาวเท่าเส้นลงชื่อ
            _ln(pg, xs[6] + 3, Y(27) + Lh * 0.8, xs[11] - 3, Y(27) + Lh * 0.8, 0.2, True)
        if o["b_note"]:
            lab(1, 14, 29, fmt(o["t_note1"], **kw))
            lab(2, 14, 30, fmt(o["t_note2"], **kw))
            lab(2, 14, 31, fmt(o["t_note3"], **kw))
        pages.append(pg)
    return pages


def build_env(ctx):
    """จ่าหน้าซอง พิมพ์ด้านหลัง A4 แนวตั้ง แล้วพับสาม: พื้นที่ซอง = 1 ใน 3 ของหน้า (กว้าง 210 x สูง 99 มม.) เลือกส่วนบน/กลาง/ล่างได้"""
    g, st = ctx.g, ctx.st
    from . import core
    pages = []
    o = tp(st, "env")
    y0 = {"บน": 0.0, "กลาง": 99.0, "ล่าง": 198.0}.get(str(st.get("env_pos", "บน")).replace("ส่วน", ""), 0.0)
    ua = st.get("unit_amphoe") or st.get("amphoe", "") or st.get("_amphoe", "")
    up = st.get("unit_province") or st.get("province", "") or st.get("_province", "")
    uz = st.get("unit_zip") or core.zip_lookup(up, ua)
    snd = [st.get("unit_name", "หน่วยสัสดีอำเภอ"), st.get("unit_addr", ""), "อำเภอ%s" % ua if ua else "",
           ("จังหวัด%s %s" % (up, uz)).strip() if up else ""]
    snd = [x for x in snd if x]
    if st.get("unit_name", "หน่วยสัสดีอำเภอ") == "หน่วยสัสดีอำเภอ":
        snd[0] = "หน่วยสัสดีอำเภอ%s" % ua
    gr = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "garuda.png")
    if not os.path.exists(gr):
        gr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "garuda.png")
    adj = st.get("env_adj") or {}

    def A(name):                                                 # ตำแหน่ง/ขนาดที่ผู้ใช้จัดเอง: (เลื่อนซ้ายขวา มม., เลื่อนบนล่าง มม., ขนาด x)
        a = list(adj.get(name) or []) + [0, 0, 100][len(adj.get(name) or []):]
        return _num(a[0], 0), _num(a[1], 0), max(0.3, _num(a[2], 100) / 100.0)
    for p in ctx.persons:
        pg = Page(g["w"], g["h"])
        pg.tags = []

        def tag(name):
            pg.tags += [name] * (len(pg.ops) - len(pg.tags))
        if o["b_fold"]:
            for fy in (99.0, 198.0):                             # เส้นประรอยพับสาม
                _ln(pg, 4, fy, g["w"] - 4, fy, 0.15, True)
        tag("fold")
        sx = 14
        if o["b_garuda"] and os.path.exists(gr):                 # ตราครุฑมุมซ้ายบน สูงเท่าบล็อกข้อความผู้ส่ง 4 บรรทัด
            gh = _num(o["gh"], 25)
            gw = gh * 253 / 199
            ox, oy, sc = A("garuda")
            pg.ops.append(("img", gr, 14 + ox, y0 + 10 + oy, gw * sc, gh * sc))
            sx = 14 + gw + 3
        tag("garuda")
        ox, oy, sc = A("sender")
        for i, tx in enumerate(snd):
            _t(pg, sx + ox, y0 + 10 + oy + i * 6.4 * sc, 110, 6.4 * sc, tx, "l", 16 * sc, False, "s")
        tag("sender")
        if st.get("env_no"):
            ox, oy, sc = A("no")
            _t(pg, 14 + ox, y0 + 42 + oy, 90, 7 * sc, "ที่  %s" % st["env_no"], "l", 16 * sc, False, "n")
        tag("no")
        am, pv = _p(p, "amphoe") or st.get("amphoe", ""), _p(p, "province") or st.get("province", "")
        z = core.zip_lookup(pv, am, _p(p, "tambon"))
        name = ("%s %s  %s" % (_p(p, "rank"), _p(p, "name"), _p(p, "surname"))).replace("  ", " ").strip()
        ox, oy, sc = A("recip")
        rx, ry, rh = 88 + ox, y0 + 52 + oy, 9.5 * sc              # "เรียน" ยื่นออกทางซ้าย ชื่อกับที่อยู่ชิดแนวเดียวกัน
        _t(pg, rx, ry, 16, rh, o["t_dear"], "l", 18 * sc, False, "e")
        rows = [name, "บ้านเลขที่ %s หมู่ที่ %s ตำบล%s" % (_p(p, "house"), _p(p, "moo"), _p(p, "tambon")),
                "อำเภอ%s จังหวัด%s" % (am, pv), z]
        for i, tx in enumerate(rows):
            _t(pg, rx + 16, ry + i * rh, 105, rh, tx, "l", 18 * sc, False, "r%d" % (i == 3))
        tag("recip")
        pages.append(pg)
    return pages


ENV_ITEMS = (("garuda", "ตราครุฑ"), ("sender", "ผู้ส่ง (หน่วยสัสดี/ที่อยู่)"), ("no", "ที่ (เลขหนังสือ)"), ("recip", "ผู้รับ (เรียน/ชื่อ/ที่อยู่)"))


def env_boxes(page):
    """กรอบ (x1,y1,x2,y2 มม.) ของแต่ละชิ้นในหน้าซอง ใช้ในหน้าจัดวางอิสระ"""
    out = {}
    for op, tg in zip(page.ops, getattr(page, "tags", [])):
        if op[0] == "img":
            b = (op[2], op[3], op[2] + op[4], op[3] + op[5])
        elif op[0] == "text":
            b = (op[1], op[2], op[1] + op[3], op[2] + op[4])
        else:
            continue
        o = out.get(tg)
        out[tg] = b if not o else (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
    return out


def build(kind, persons, st, ptype, tambon, level):
    """kind: reg|sum|send ; level: กำนัน|อำเภอ|จังหวัด (send ใช้อำเภอเสมอ)"""
    st = dict(st)
    if persons:
        from collections import Counter
        mode = lambda k: (Counter(p.get(k, "") for p in persons if p.get(k, "")).most_common(1) or [("", 0)])[0][0]
        st["_amphoe"] = mode("amphoe") or st.get("amphoe", "")      # อำเภอ/จังหวัดของชุดข้อมูลที่พิมพ์
        st["_province"] = mode("province") or st.get("province", "")
    ctx = _Ctx(kind, st, persons, ptype, tambon, "อำเภอ" if kind == "send" else level)
    if not persons:
        return []
    if kind == "form":
        pages = build_form(ctx)
    elif kind == "env":
        pages = build_env(ctx)
    else:
        pages = build_reg(ctx) if kind == "reg" else build_table(ctx)
    return _apply_global(pages, tp(st, kind))
