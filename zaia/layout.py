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
}


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
    h_title = title_h + 3 * Lh + Lh        # แถว 1-5
    h_tab = hdr_lines * Lh
    avail = g["h"] - g["mt"] - g["mb"]
    ph = 3 * Lh
    sizes = paginate(len(ctx.persons), ph, avail - h_title - h_tab, avail - h_tab, 5 * Lh if ctx.level == "อำเภอ" else 3 * Lh, 5, 7)   # เทมเพลต: หน้าแรก 5 คน หน้าถัดไป 7 คน ไม่ซ้ำหัวตาราง
    pages, idx = [], 0
    for pn, k in enumerate(sizes):
        pg = Page(g["w"], g["h"])
        y = g["mt"]
        if pn == 0:
            _t(pg, xs[0], y, tw, title_h, "บัญชีตรวจสอบสภาพทหารกองหนุน", "c", 20 * s, "u")
            # กล่องข้อความมุมขวาบนตามเทมเพลต Excel: "ทบ. 100 - 070" (ชิดขวา) และข้อความสีแดงด้านล่าง (ระยะ EMU/36000 = มม., เว้นขอบกล่อง 2.54 มม.)
            m0, ins = g["mt"], 2.54 * s
            xa, xb = xs[12] + 1.85 * s + ins, xs[13] + 15.6 * s - ins
            _t(pg, xa, m0 + 0.8 * s + 1.27 * s, xb - xa, Lh, "ทบ. 100 - 070", "r", pt)
            xa, xb = xs[10] + 15.35 * s + ins, xs[13] + 15.9 * s - ins
            _t(pg, xa, m0 + 5.8 * s + 1.27 * s, xb - xa, Lh, "ตรวจสอบสภาพทหารกองหนุนประจำปี " + str(st.get("year", 2570)), "l", pt, color=(255, 0, 0))
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
    title = "บัญชีรายชื่อการตรวจสอบสภาพทหารกองหนุนประจำปี %s ประเภท %s" % (year, ctx.ptype)
    h_title = 3 * Lh
    avail = g["h"] - g["mt"] - g["mb"]
    block = {"อำเภอ": 5, "กำนัน": 3, "จังหวัด": 1}[ctx.level] * Lh
    sizes = paginate(len(ctx.persons), ph, avail - h_title - h_tab - (ph if send else 0), avail - h_tab, block)
    pages, idx = [], 0
    for pn, k in enumerate(sizes):
        pg = Page(g["w"], g["h"])
        y = g["mt"]
        if pn == 0:
            _t(pg, xs[0], y, tw, Lh, title, "c", 16 * s, True)
            y += Lh
            _t(pg, xs[0], y, tw, Lh, "อำเภอ%s   จังหวัด%s" % (st.get("_amphoe", ""), st.get("_province", "")), "c", pt, True)
            y += 2 * Lh
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
    return build_reg(ctx) if kind == "reg" else build_table(ctx)
