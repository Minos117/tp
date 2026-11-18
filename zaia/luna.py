"""ธีม Windows XP (Luna): ปุ่มเงาไล่สี แถบหัวเรื่องมันวาว สีน้ำเงิน-ขาว-เขียว-ส้ม (วาดด้วย PIL ไม่ต้องมีไฟล์ภาพ)"""
from PIL import Image, ImageDraw, ImageTk

# พาเลตต์เดียวทั้งโปรแกรม
BG = "#EAF0FB"          # พื้นเนื้อหา ฟ้าอ่อนแบบแผงขวาเมนู Start
CARD = "#FFFFFF"
LINE = "#9DB9EB"        # เส้นขอบอ่อน
LINE_D = "#7F9DB9"      # ขอบช่องกรอก (สี XP)
NAVY = "#0A246A"
BLUE = "#245EDC"
BLUE_SEL = "#316AC5"
GREEN = "#2E8B2E"
ORANGE = "#F08A00"
MUTED = "#4F6288"
HEAD_L = "#DCE7FA"      # หัวตาราง/แท็บ
TROUGH = "#D5E1F6"
SIDE = "#2B63D9"
SIDE_TOP = "#0E3FB0"
SIDE_BOT = "#1A4FC6"
SIDE_HOVER = "#4A82EE"
SIDE_ACT_BG, SIDE_ACT_FG = "#E3EEFD", NAVY

TITLE_STOPS = ((0.0, "#0A5BE8"), (0.08, "#4A9BFF"), (0.20, "#2E8AFF"), (0.55, "#0F6CF5"), (0.92, "#0457E0"), (1.0, "#0B45C0"))


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def grad_at(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            a, b = _rgb(c0), _rgb(c1)
            return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return _rgb(stops[-1][1])


def _btn_img(top, mid, bot, border, glow=None, size=24, r=3):
    """ภาพปุ่มมุมมน ไล่สีแนวตั้ง (วาด 4 เท่าแล้วย่อ ให้ขอบเนียน) — ใช้ 9-slice"""
    s = 4
    W = H = size * s
    im = Image.new("RGB", (W, H))
    px = im.load()
    stops = ((0.0, top), (0.5, mid), (0.52, mid), (1.0, bot))
    for y in range(H):
        c = grad_at(stops, y / (H - 1))
        for x in range(W):
            px[x, y] = c
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), r * s, fill=255)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, W - 1, H - 1), r * s, outline=border, width=s)
    if glow:                                                   # วงส้มรอบในตอนเมาส์ชี้ (แบบปุ่ม XP)
        d.rounded_rectangle((s, s, W - 1 - s, H - 1 - s), max(1, (r - 1) * s), outline=glow, width=2 * s)
    return out.resize((size, size), Image.LANCZOS)


def install(st, root):
    """ตั้งค่า ttk.Style ทั้งหมด (ต้องเรียกหลัง theme_use('clam')) คืนค่า list ภาพที่ต้องเก็บไว้กันถูกลบ"""
    keep = []

    def P(img):
        p = ImageTk.PhotoImage(img, master=root)
        keep.append(p)
        return p
    n = P(_btn_img("#FFFFFF", "#EEF3FC", "#D3DFF5", "#1C3F84"))
    h = P(_btn_img("#FFFFFF", "#F2F6FD", "#D9E4F8", "#1C3F84", glow="#FFC24A"))
    pr = P(_btn_img("#C5D3EE", "#D3DFF5", "#E4ECFA", "#1C3F84"))
    ds = P(_btn_img("#F6F6F2", "#F1F1EC", "#E8E8E0", "#C3C6CC"))
    st.element_create("Luna.btn", "image", n, ("disabled", ds), ("pressed", pr), ("active", h), border=5, sticky="nsew")
    gn = P(_btn_img("#8FD58F", "#3FA03F", "#2A7F2A", "#1B5E1B"))
    gh = P(_btn_img("#A8E3A8", "#4FB84F", "#33902F", "#1B5E1B", glow="#FFC24A"))
    gp = P(_btn_img("#2A7F2A", "#2F8C2F", "#3FA03F", "#1B5E1B"))
    st.element_create("Luna.green", "image", gn, ("disabled", ds), ("pressed", gp), ("active", gh), border=5, sticky="nsew")
    for sty, el in (("TButton", "Luna.btn"), ("Accent.TButton", "Luna.green")):
        st.layout(sty, [(el, {"sticky": "nswe", "children": [("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
    st.configure("TButton", foreground="#10204A", padding=(14, 7))
    st.map("TButton", foreground=[("disabled", "#8A94A8")])
    st.configure("Accent.TButton", foreground="white", padding=(16, 8))
    st.map("Accent.TButton", foreground=[("disabled", "#8A94A8")])

    st.configure(".", background=BG)
    st.configure("TFrame", background=BG)
    st.configure("TLabel", background=BG, foreground="#1B2A4A")
    st.configure("TLabelframe", background=BG, bordercolor=LINE)
    st.configure("TLabelframe.Label", background=BG, foreground=NAVY)
    for w in ("TCheckbutton", "TRadiobutton"):
        st.configure(w, background=BG, indicatorbackground="white", indicatorcolor="white")
        st.map(w, background=[("active", BG)], indicatorcolor=[("selected", "#2E8B2E")])
    for w in ("TEntry", "TCombobox", "TSpinbox"):
        st.configure(w, fieldbackground="white", bordercolor=LINE_D, lightcolor="white", darkcolor="white")
        st.map(w, bordercolor=[("focus", BLUE)], lightcolor=[("focus", "#BCD2F8")], darkcolor=[("focus", "#BCD2F8")])
    st.configure("TCombobox", arrowcolor=NAVY, background="#D3DFF5")
    st.map("TCombobox", background=[("active", "#E8F0FD")], fieldbackground=[("readonly", "white")])
    st.configure("TSpinbox", arrowcolor=NAVY, background="#D3DFF5")
    st.configure("Treeview", fieldbackground="white", bordercolor=LINE)
    st.configure("Treeview.Heading", background=HEAD_L, foreground=NAVY, bordercolor=LINE, lightcolor="#F4F8FF", darkcolor=HEAD_L)
    st.map("Treeview.Heading", background=[("active", "#EAF2FE")])
    st.map("Treeview", background=[("selected", BLUE_SEL)], foreground=[("selected", "white")])
    st.configure("TNotebook", background=BG, bordercolor=LINE_D, lightcolor=BG, darkcolor=BG)
    st.configure("TNotebook.Tab", background=HEAD_L, foreground=NAVY, bordercolor=LINE_D, lightcolor="#F4F8FF", darkcolor=HEAD_L)
    st.map("TNotebook.Tab", background=[("selected", "#FFFFFF"), ("active", "#EAF2FE")], lightcolor=[("selected", "#FFC24A")], foreground=[("selected", NAVY)])
    st.configure("Vertical.TScrollbar", background="#C4D5F4", troughcolor="#EEF3FC", bordercolor=LINE, arrowcolor=NAVY, lightcolor="#F4F8FF", darkcolor="#9DB9EB", gripcount=0)
    st.configure("Horizontal.TScrollbar", background="#C4D5F4", troughcolor="#EEF3FC", bordercolor=LINE, arrowcolor=NAVY, lightcolor="#F4F8FF", darkcolor="#9DB9EB", gripcount=0)
    st.map("TScrollbar", background=[("active", "#A9C1EE"), ("pressed", "#8FAEE6")])
    st.configure("Green.Horizontal.TProgressbar", troughcolor=TROUGH, background="#3FA03F", bordercolor=LINE_D, lightcolor="#8FD58F", darkcolor=GREEN, thickness=12)
    st.configure("TSeparator", background=LINE)
    st.configure("TPanedwindow", background=BG)
    return keep


def vgrad(w, h, stops):
    im = Image.new("RGB", (max(1, w), max(1, h)))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line((0, y, w, y), fill=grad_at(stops, y / max(1, h - 1)))
    return im
