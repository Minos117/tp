"""ธีมสีของโปรแกรม: 20 พรีเซ็ต + รูปปุ่ม 2 แบบ (เรียบ / เงาแบบ Windows XP)  วาดด้วย PIL ไม่ต้องมีไฟล์ภาพ
ตัวแปรสีเป็นตัวแปรโมดูล (BG, NAVY, SIDE, ...)  เรียก set_theme() แล้วอ่านค่าใหม่ได้ทันที"""
from PIL import Image, ImageDraw, ImageTk

# (รหัส, ชื่อ, สีหลัก(แถบซ้าย/หัวเรื่อง), สีปุ่มหลัก, สีเส้นใต้หัวเรื่อง)
THEMES = (
    ("luna", "XP ฟ้า (Luna)", "#2B63D9", "#3C9A3C", "#FFB22E"),
    ("silver", "XP เงิน (Silver)", "#6F7A9C", "#46558C", "#CDD3E4"),
    ("olive", "XP มะกอก (Olive)", "#6A8A3A", "#8C6A2F", "#E8C766"),
    ("navy", "กรมท่า-ทอง", "#1F3A73", "#C08A1E", "#E6B84D"),
    ("ocean", "ทะเลสีฟ้า", "#0E7FA8", "#D8672B", "#FFC857"),
    ("forest", "ป่าเขียว", "#2F6B45", "#A9741F", "#D9B65D"),
    ("emerald", "มรกต", "#0F8A6C", "#0B6B54", "#9FE3CD"),
    ("sage", "เขียวเสจ", "#6F8F72", "#4C6B50", "#D3DEC6"),
    ("rose", "กุหลาบ", "#C2547A", "#9A3560", "#F4B6C8"),
    ("berry", "ราสป์เบอร์รี", "#A8264F", "#7A1F3D", "#F2A65A"),
    ("purple", "ม่วงราชวงศ์", "#5B3E96", "#C98F10", "#F0C75E"),
    ("lavender", "ลาเวนเดอร์", "#8A7CC9", "#5E4FA8", "#DDD6F5"),
    ("crimson", "แดงเข้ม", "#A32424", "#7A1616", "#E8A33D"),
    ("sunset", "ส้มพระอาทิตย์", "#D9622B", "#A3410F", "#FFD27A"),
    ("amber", "ทองอำพัน", "#B8861B", "#7A5A0F", "#F5DC8A"),
    ("choco", "ช็อกโกแลต", "#6B4A3A", "#B5651D", "#E0C097"),
    ("slate", "เทาหินชนวน", "#4F5D75", "#2F6BB3", "#B8C4D9"),
    ("charcoal", "ถ่านดำ", "#33383F", "#3A7BD5", "#9AA5B5"),
    ("sky", "ฟ้าสดใส", "#4FA3E0", "#2677B8", "#CDE8F8"),
    ("mint", "มิ้นต์", "#3DB39E", "#1F8A78", "#CBF0E4"),
)
DEFAULT = "luna"
KEYS = ("BG", "CARD", "LINE", "LINE_D", "NAVY", "BLUE", "BLUE_SEL", "GREEN", "ORANGE", "MUTED", "HEAD_L", "TROUGH", "ROW_ALT", "SIDE", "SIDE_TOP",
        "SIDE_HOVER", "SIDE_ACT_BG", "SIDE_ACT_FG", "SIDE_SEP", "SIDE_TXT", "SIDE_FOOT", "BTN", "BTN_HOVER", "TITLE_LINE", "TITLE_LINE_L", "TITLE_SHADOW")
BG = CARD = LINE = LINE_D = NAVY = BLUE = BLUE_SEL = GREEN = ORANGE = MUTED = HEAD_L = TROUGH = ROW_ALT = ""
SIDE = SIDE_TOP = SIDE_HOVER = SIDE_ACT_BG = SIDE_ACT_FG = SIDE_SEP = SIDE_TXT = SIDE_FOOT = BTN = BTN_HOVER = ""
TITLE_LINE = TITLE_LINE_L = TITLE_SHADOW = ""
TITLE_STOPS = ()
STYLE = "flat"
_n = [0]


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """ผสมสี a กับ b  t=0 → a, t=1 → b"""
    x, y = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(int(x[i] + (y[i] - x[i]) * t) for i in range(3))


def grad_at(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            a, b = _rgb(c0), _rgb(c1)
            return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return _rgb(stops[-1][1])


def palette():
    g = globals()
    return {k: g[k] for k in KEYS}


def theme_colors(key):
    """คืน dict สีทั้งชุดของพรีเซ็ต (ไม่เปลี่ยนค่าโมดูล)"""
    t = next((x for x in THEMES if x[0] == key), THEMES[0])
    base, btn, line = t[2], t[3], t[4]
    W, K = "#FFFFFF", "#000000"
    navy = mix(base, K, 0.62)
    return dict(BG=mix(base, W, 0.92), CARD=W, LINE=mix(base, W, 0.62), LINE_D=mix(base, W, 0.35), NAVY=navy, BLUE=base, BLUE_SEL=mix(base, K, 0.12),
                GREEN="#2E8B2E", ORANGE="#E07B00", MUTED=mix(navy, "#8A8A8A", 0.45), HEAD_L=mix(base, W, 0.84), TROUGH=mix(base, W, 0.8),
                ROW_ALT=mix(base, W, 0.95), SIDE=base, SIDE_TOP=mix(base, K, 0.32), SIDE_HOVER=mix(base, W, 0.2), SIDE_ACT_BG=mix(base, W, 0.9),
                SIDE_ACT_FG=navy, SIDE_SEP=mix(base, W, 0.35), SIDE_TXT="#FFFFFF", SIDE_FOOT=mix(base, W, 0.8), BTN=btn, BTN_HOVER=mix(btn, W, 0.18),
                TITLE_LINE=line, TITLE_LINE_L=mix(line, W, 0.5), TITLE_SHADOW=mix(base, K, 0.55))


def set_theme(key, style="flat"):
    global TITLE_STOPS, STYLE
    g = globals()
    c = theme_colors(key)
    for k, v in c.items():
        g[k] = v
    STYLE = style if style in ("flat", "glossy") else "flat"
    b, W, K = c["SIDE"], "#FFFFFF", "#000000"
    if STYLE == "glossy":
        TITLE_STOPS = ((0.0, mix(b, W, 0.05)), (0.08, mix(b, W, 0.38)), (0.2, mix(b, W, 0.2)), (0.55, b), (0.92, mix(b, K, 0.12)), (1.0, mix(b, K, 0.28)))
    else:
        TITLE_STOPS = ((0.0, mix(b, W, 0.1)), (1.0, mix(b, K, 0.1)))


set_theme(DEFAULT)


def _btn_img(top, mid, bot, border, glow=None, size=24, r=3):
    """ภาพปุ่มมุมมน ไล่สีแนวตั้ง (วาด 4 เท่าแล้วย่อ ให้ขอบเนียน) — ใช้ 9-slice"""
    s = 4
    W = H = size * s
    im = Image.new("RGB", (W, H))
    d0 = ImageDraw.Draw(im)
    stops = ((0.0, top), (0.5, mid), (0.52, mid), (1.0, bot))
    for y in range(H):
        d0.line((0, y, W, y), fill=grad_at(stops, y / (H - 1)))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), r * s, fill=255)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, W - 1, H - 1), r * s, outline=border, width=s)
    if glow:
        d.rounded_rectangle((s, s, W - 1 - s, H - 1 - s), max(1, (r - 1) * s), outline=glow, width=2 * s)
    return out.resize((size, size), Image.LANCZOS)


def _states(fill_top, fill_mid, fill_bot, border, hover_border):
    """ภาพ 4 สถานะ: ปกติ/ชี้/กด/ปิดใช้"""
    W, K = "#FFFFFF", "#000000"
    if STYLE == "glossy":
        n = _btn_img(fill_top, fill_mid, fill_bot, border)
        h = _btn_img(mix(fill_top, W, 0.2), mix(fill_mid, W, 0.12), mix(fill_bot, W, 0.1), border, glow=hover_border)
        p = _btn_img(mix(fill_bot, K, 0.1), mix(fill_mid, K, 0.08), mix(fill_top, K, 0.02), border)
    else:
        n = _btn_img(fill_mid, fill_mid, fill_mid, border, r=3)
        h = _btn_img(mix(fill_mid, W, 0.14), mix(fill_mid, W, 0.14), mix(fill_mid, W, 0.14), hover_border, r=3)
        p = _btn_img(mix(fill_mid, K, 0.14), mix(fill_mid, K, 0.14), mix(fill_mid, K, 0.14), border, r=3)
    d = _btn_img("#F1F1EE", "#F1F1EE", "#E6E6E2", "#C3C6CC")
    return n, h, p, d


def install(st, root):
    """ตั้งค่า ttk.Style ทั้งหมดตามธีมปัจจุบัน (เรียกซ้ำได้เมื่อเปลี่ยนธีม) คืน list ภาพที่ต้องเก็บไว้"""
    keep = []
    _n[0] += 1
    i = _n[0]
    W, K = "#FFFFFF", "#000000"

    def P(img):
        p = ImageTk.PhotoImage(img, master=root)
        keep.append(p)
        return p
    b = SIDE
    # ปุ่มรอง
    if STYLE == "flat":
        f0 = mix(b, W, 0.93)
        n = P(_btn_img(f0, f0, f0, mix(b, W, 0.3)))
        h = P(_btn_img(W, W, W, BTN))
        p = P(_btn_img(HEAD_L, HEAD_L, HEAD_L, BTN))
        d = P(_btn_img("#F1F1EE", "#F1F1EE", "#F1F1EE", "#C3C6CC"))
    else:
        n, h, p, d = [P(x) for x in _states(W, mix(b, W, 0.94), mix(b, W, 0.8), mix(b, K, 0.25), "#FFC24A")]
    e1, e2 = "Luna.btn%d" % i, "Luna.pri%d" % i
    st.element_create(e1, "image", n, ("disabled", d), ("pressed", p), ("active", h), border=5, sticky="nsew")
    # ปุ่มหลัก
    pe = mix(BTN, K, 0.3)
    if STYLE == "glossy":
        gn, gh, gp, gd = _states(mix(BTN, W, 0.4), BTN, mix(BTN, K, 0.18), pe, "#FFC24A")
    else:
        gn, gh, gp, gd = _states(BTN, BTN, BTN, pe, mix(BTN, W, 0.5))
    st.element_create(e2, "image", P(gn), ("disabled", P(gd)), ("pressed", P(gp)), ("active", P(gh)), border=5, sticky="nsew")
    for sty, el in (("TButton", e1), ("Accent.TButton", e2)):
        st.layout(sty, [(el, {"sticky": "nswe", "children": [("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
    st.configure("TButton", foreground=NAVY, padding=(14, 7))
    st.map("TButton", foreground=[("disabled", "#8A94A8")])
    st.configure("Accent.TButton", foreground="white", padding=(16, 8))
    st.map("Accent.TButton", foreground=[("disabled", "#8A94A8")])

    st.configure(".", background=BG)
    st.configure("TFrame", background=BG)
    st.configure("TLabel", background=BG, foreground=mix(NAVY, K, 0.35))
    st.configure("TLabelframe", background=BG, bordercolor=LINE)
    st.configure("TLabelframe.Label", background=BG, foreground=NAVY)
    for w in ("TCheckbutton", "TRadiobutton"):
        st.configure(w, background=BG, indicatorbackground="white", indicatorcolor="white", foreground=mix(NAVY, K, 0.35))
        st.map(w, background=[("active", BG)], indicatorcolor=[("selected", BTN)])
    for w in ("TEntry", "TCombobox", "TSpinbox"):
        st.configure(w, fieldbackground="white", bordercolor=LINE_D, lightcolor="white", darkcolor="white")
        st.map(w, bordercolor=[("focus", BLUE)], lightcolor=[("focus", LINE)], darkcolor=[("focus", LINE)])
    for w in ("TCombobox", "TSpinbox"):
        st.configure(w, arrowcolor=NAVY, background=HEAD_L)
    st.map("TCombobox", background=[("active", mix(BLUE, W, 0.9))], fieldbackground=[("readonly", "white")])
    st.configure("Treeview", fieldbackground="white", bordercolor=LINE)
    st.configure("Treeview.Heading", background=HEAD_L, foreground=NAVY, bordercolor=LINE, lightcolor=mix(BLUE, W, 0.95), darkcolor=HEAD_L)
    st.map("Treeview.Heading", background=[("active", mix(BLUE, W, 0.9))])
    st.map("Treeview", background=[("selected", BLUE_SEL)], foreground=[("selected", "white")])
    st.configure("TNotebook", background=BG, bordercolor=LINE_D, lightcolor=BG, darkcolor=BG)
    st.configure("TNotebook.Tab", background=HEAD_L, foreground=NAVY, bordercolor=LINE_D, lightcolor=mix(BLUE, W, 0.95), darkcolor=HEAD_L)
    st.map("TNotebook.Tab", background=[("selected", "#FFFFFF"), ("active", mix(BLUE, W, 0.9))], lightcolor=[("selected", TITLE_LINE)], foreground=[("selected", NAVY)])
    for o in ("Vertical", "Horizontal"):
        st.configure(o + ".TScrollbar", background=mix(BLUE, W, 0.72), troughcolor=mix(BLUE, W, 0.93), bordercolor=LINE, arrowcolor=NAVY,
                     lightcolor=mix(BLUE, W, 0.9), darkcolor=LINE, gripcount=0)
    st.map("TScrollbar", background=[("active", mix(BLUE, W, 0.55)), ("pressed", mix(BLUE, W, 0.4))])
    st.configure("Green.Horizontal.TProgressbar", troughcolor=TROUGH, background=BTN, bordercolor=LINE_D, lightcolor=mix(BTN, W, 0.35), darkcolor=BTN, thickness=12)
    st.configure("TSeparator", background=LINE)
    return keep


def vgrad(w, h, stops):
    im = Image.new("RGB", (max(1, w), max(1, h)))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line((0, y, w, y), fill=grad_at(stops, y / max(1, h - 1)))
    return im
