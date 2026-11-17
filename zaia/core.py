"""ZAIA Prepare Personal - แกนข้อมูล: นำเข้า / เขียนกลับ Excel / เลือก-เรียง / ตั้งค่า"""
import copy
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from datetime import datetime

# ---------------------------------------------------------------- คงที่
TYPES = ["นายทหารสัญญาบัตรกองหนุน", "นายทหารประทวนกองหนุน",
         "ส.ต.กองประจำการและพลทหารกองหนุน"]
ALL_TYPES = "ทุกประเภท"
ALL_TAMBON = "ทุกตำบล"
LEVELS = ["กำนัน", "อำเภอ", "จังหวัด"]

# key: (หัวคอลัมน์ในเทมเพลต, ชื่อคอลัมน์ Excel ในเทมเพลต)
FIELDS = {
    "seq": ("ลำดับ", "A"), "rank": ("ยศ", "C"), "name": ("ชื่อ", "D"),
    "surname": ("สกุล", "E"), "nid": ("เลขปชช", "F"), "house": ("เลขที่", "I"),
    "moo": ("หมู่", "J"), "tambon": ("ตำบล", "K"), "year": ("ชั้นปี", "M"),
    "mark": ("เลข เครื่องหมาย", "N"), "amphoe": ("อำเภอ", "O"),
    "province": ("จังหวัด", "P"), "father": ("บิดา", "Q"), "fsur": ("สกุลบิดา", "R"),
    "mother": ("มารดา", "S"), "msur": ("สกุลมารดา", "T"), "branch": ("เหล่า", "Z"),
    "type": ("ประเภท", "AP"),
    "result": ("มี/ไม่มี", "AH"), "status": ("สถานภาพ", "AI"), "place": ("สถานที่", "AJ"),
    "amphoe2": ("อำเภอ2", "AK"), "prov2": ("จังหวัด3", "AL"),
    "tel": ("เบอร์ตัว", "AM"), "tel_par": ("เบอร์ผู้ปกครอง", "AN"),
    "tel_work": ("เบอร์ที่ทำงาน", "AO"), "note": ("หมายเหตุ", "AQ"),
}
RESULT_FIELDS = ["result", "status", "place", "amphoe2", "prov2",
                 "tel", "tel_par", "tel_work"]          # เขียนกลับเฉพาะกลุ่มนี้
REQUIRED = ["name", "surname", "tambon", "moo"]

OCCUPATIONS = ["ศึกษา", "รับจ้าง ( )", "เกษตรกร", "ธุรกิจส่วนตัว", "ว่างงาน", "ช่าง",
               "รับราชการ", "พนักงานบริษัท", "พนักงาน", "ทำงานโรงงาน", "ลูกจ้าง",
               "ลูกจ้างราชการ", "ขับรถ", "ไปทำงานต่างประเทศ", "ต้องโทษ", "ก่อสร้าง",
               "รปภ.", "ทำงานอื่นๆ ( )"]

PRINT_KINDS = {"reg_กำนัน": "บัญชีตรวจสอบสภาพ-ตำบล", "reg_อำเภอ": "บัญชีตรวจสอบสภาพ-อำเภอ",
               "reg_จังหวัด": "บัญชีตรวจสอบสภาพ-จังหวัด", "sum": "บัญชีสรุปผลการตรวจสอบ",
               "send": "ส่งผู้ใหญ่บ้าน"}


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "ZAIA Prepare Personal")
    os.makedirs(d, exist_ok=True)
    return d


def norm(s):
    return re.sub(r"\s+", "", str(s if s is not None else "")).lower()


def s(v):
    """แปลงค่าเซลล์เป็นข้อความโดยไม่ปรับเปลี่ยนมากกว่าที่จำเป็น"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def col_letter(n):
    r = ""
    while n:
        n, m = divmod(n - 1, 26)
        r = chr(65 + m) + r
    return r


def col_index(letter):
    n = 0
    for ch in letter.upper():
        n = n * 26 + ord(ch) - 64
    return n


def guess_type(p):
    t = p.get("type", "")
    if t:
        return t
    rk = p.get("rank", "").replace(" ", "")      # เดาจากยศ เมื่อไฟล์ไม่มีคอลัมน์ประเภท (ควรตรวจซ้ำ)
    if rk.startswith(("ร.ต", "ร.ท", "ร.อ", "พ.ต", "พ.ท", "พ.อ", "พล.ต", "พล.ท", "พล.อ")):
        return TYPES[0]
    if rk.startswith(("ส.อ", "ส.ท", "จ.ส", "ด.ต")):
        return TYPES[1]
    return TYPES[2]


def type_rank(t):
    for i, x in enumerate(TYPES):
        if t == x:
            return i
    return len(TYPES)


def moo_key(m):
    m = str(m).strip()
    return (0, int(m)) if m.isdigit() else (1, m)


# ---------------------------------------------------------------- ตั้งค่า
DEFAULT_SETTINGS = {
    "amphoe": "", "province": "", "org": "ส.น.", "year": "2570", "font": "TH SarabunIT๙",
    "printer": "", "delay": 5, "backup": True,
    "sign_province": ["ได้ตรวจถูกต้องแล้ว"],
    "sign_amphoe": ["ได้ตรวจถูกต้องแล้ว", "        ร.ท.", "            ( พัทยา  จุลนีย์ )",
                    "ผช.สด.อ.พังโคน รักษาราชการแทน", "        สด.อ.พรรณานิคม จว.ส.น."],
    "sign_kamnan": ["ได้ตรวจถูกต้องแล้ว", "", "           กำนันตำบล{ตำบล}"],
    "sig_image": "", "sig_level": "อำเภอ", "sig_w": 32.0, "sig_dx": 0.0, "sig_dy": 0.0,
    "update_url": "",
}


def load_settings():
    p = os.path.join(data_dir(), "settings.json")
    st = copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(p, encoding="utf-8") as f:
            st.update(json.load(f))
    except (OSError, ValueError):
        pass
    return st


def save_settings(st):
    with open(os.path.join(data_dir(), "settings.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- ฐานข้อมูลภายใน
class DB:
    """persons: list ของ dict (คีย์ตาม FIELDS) + _row (แถวในไฟล์ต้นฉบับ) + _orig (ค่าผลตรวจตอนนำเข้า/เขียนกลับ)
    + printed {kind: 'dd/mm/yy hh:mm'}"""

    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "data.json")
        self.persons = []
        self.source = {}
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            self.persons, self.source = d.get("persons", []), d.get("source", {})
        except (OSError, ValueError):
            self.persons, self.source = [], {}

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"persons": self.persons, "source": self.source}, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ---- นำเข้า
    def set_import(self, persons, source):
        self.persons, self.source = persons, source
        self.save()

    def tambons(self):
        out = []
        for p in self.persons:
            if p["tambon"] and p["tambon"] not in out:
                out.append(p["tambon"])
        return out

    def moos(self, tambon=None):
        m = {p["moo"] for p in self.persons if p["moo"] and (not tambon or tambon == ALL_TAMBON or p["tambon"] == tambon)}
        return sorted(m, key=moo_key)

    def filled(self, p):
        return bool(p.get("result"))

    def summary(self, by="tambon"):
        """สรุปรายประเภท: [(ประเภท, ทั้งหมด, ทำแล้ว, [(ตำบล, ทั้งหมด, ทำแล้ว, [(หมู่, ทั้งหมด, ทำแล้ว)])])]  ทำแล้ว = บันทึกผลแล้ว"""
        tam_order = {t: i for i, t in enumerate(self.tambons())}
        tree = {}
        for p in self.persons:
            t, tb, mo = guess_type(p) or "ไม่ระบุ", p["tambon"] or "-", str(p["moo"] or "-")
            d = 1 if self.filled(p) else 0
            tree.setdefault(t, {}).setdefault(tb, {}).setdefault(mo, [0, 0])
            tree[t][tb][mo][0] += 1
            tree[t][tb][mo][1] += d
        out = []
        for t in sorted(tree, key=type_rank):
            tams = []
            for tb in sorted(tree[t], key=lambda x: tam_order.get(x, 999)):
                moos = [(m, v[0], v[1]) for m, v in sorted(tree[t][tb].items(), key=lambda kv: moo_key(kv[0]))]
                tams.append((tb, sum(m[1] for m in moos), sum(m[2] for m in moos), moos))
            out.append((t, sum(x[1] for x in tams), sum(x[2] for x in tams), tams))
        return out

    # ---- เลือก/เรียง
    def select(self, ptype=ALL_TYPES, tambon=ALL_TAMBON, moo=None, only_unprinted=None):
        """คืนรายการคน เรียง: ประเภท(สัญญาบัตร→ประทวน→พลฯ) แล้วหมู่น้อย→มาก (ตำบลเรียงตามลำดับที่พบ)"""
        tam_order = {t: i for i, t in enumerate(self.tambons())}
        rows = [p for p in self.persons
                if (ptype in (ALL_TYPES, "", None) or guess_type(p) == ptype)
                and (tambon in (ALL_TAMBON, "", None) or p["tambon"] == tambon)
                and (not moo or str(p["moo"]) == str(moo))]
        if only_unprinted:
            rows = [p for p in rows if only_unprinted not in p.get("printed", {})]
        rows.sort(key=lambda p: (tam_order.get(p["tambon"], 999), type_rank(guess_type(p)),
                                 moo_key(p["moo"]), p.get("_row", 0)))
        return rows

    def find(self, q):
        q = norm(q)
        if not q:
            return []
        return [p for p in self.persons
                if q in norm(p["nid"]) or q in norm(p["name"] + p["surname"])
                or q in norm(p["rank"] + p["name"] + p["surname"])]

    # ---- ล้าง
    def clear_results(self):
        for p in self.persons:
            for k in RESULT_FIELDS:
                p[k] = ""
        self.save()

    def clear_printed(self, kinds=None):
        for p in self.persons:
            if kinds is None:
                p["printed"] = {}
            else:
                for k in kinds:
                    p.get("printed", {}).pop(k, None)
        self.save()

    def clear_all(self):
        self.persons, self.source = [], {}
        self.save()

    def mark_printed(self, plist, kind):
        stamp = datetime.now().strftime("%d/%m/%y %H:%M")
        for p in plist:
            p.setdefault("printed", {})[kind] = stamp
        self.save()

    def dirty_count(self):
        return sum(1 for p in self.persons if any(p.get(k, "") != p.get("_orig", {}).get(k, "") for k in RESULT_FIELDS))


# ---------------------------------------------------------------- อ่านไฟล์ Excel
def is_xlsb(path):
    return str(path).lower().endswith(".xlsb")


def list_sheets(path):
    if is_xlsb(path):
        from pyxlsb import open_workbook
        with open_workbook(path) as wb:
            return list(wb.sheets)
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def read_rows(path, sheet, first, last=None, maxcol=80):
    """คืน list ของ (เลขแถว, [ข้อความ...]) ตั้งแต่แถว first ถึง last (None = ท้ายสุด)"""
    if is_xlsb(path):
        from pyxlsb import open_workbook
        out = []
        with open_workbook(path) as wb:
            with wb.get_sheet(sheet) as sh:
                for row in sh.rows(sparse=False):
                    if not row:
                        continue
                    rn = row[0].r + 1
                    if rn < first:
                        continue
                    if last is not None and rn > last:
                        break
                    out.append((rn, [s(c.v) for c in row[:maxcol]]))
        return out
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        out = []
        for i, row in enumerate(ws.iter_rows(min_row=first, max_row=last, max_col=maxcol, values_only=True), start=first):
            out.append((i, [s(v) for v in row]))
        return out
    finally:
        wb.close()


def export_xlsb_as_xlsx(db):
    """.xlsb เขียนกลับตรง ๆ ไม่ได้ -> สร้าง .xlsx ใหม่ข้างไฟล์เดิม (ค่าล้วน ไม่มีรูปแบบ/มาโคร) ใส่ผลตรวจ แล้วใช้ไฟล์นั้นเป็นต้นฉบับต่อไป"""
    import openpyxl
    src = db.source
    path, sheet, mapping = src["path"], src["sheet"], src.get("mapping", {})
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    for rn, cells in read_rows(path, sheet, 1, None, maxcol=200):
        for ci, v in enumerate(cells, start=1):
            if v != "":
                ws.cell(rn, ci, v)
    for p in db.persons:
        for k in RESULT_FIELDS:
            c = mapping.get(k)
            if c and p.get("_row"):
                ws.cell(p["_row"], c).value = p.get(k, "") or None
    out = os.path.splitext(path)[0] + ".ผลตรวจ.xlsx"
    wb.save(out)
    src["path"], src["sheet"] = out, ws.title
    for p in db.persons:
        p["_orig"] = {k: p.get(k, "") for k in RESULT_FIELDS}
    db.save()
    return out


def auto_map(headers):
    """headers: list ข้อความหัวคอลัมน์ (index 0 = คอลัมน์ A) -> {field: เลขคอลัมน์ 1-based}"""
    m = {}
    nh = [norm(h) for h in headers]
    for key, (title, _letter) in FIELDS.items():
        t = norm(title)
        if t in nh:
            m[key] = nh.index(t) + 1
    return m


def detect_last_row(path, sheet, start, mapping):
    cols = [mapping[k] for k in ("nid", "name") if k in mapping]
    last = start - 1
    for r, cells in read_rows(path, sheet, start):
        if any(c - 1 < len(cells) and cells[c - 1] for c in cols):
            last = r
    return last


def build_persons(path, sheet, start, end, mapping, orig_default=True):
    persons = []
    for r, cells in read_rows(path, sheet, start, end):
        def g(k):
            c = mapping.get(k)
            return cells[c - 1] if c and c - 1 < len(cells) else ""
        p = {k: g(k) for k in FIELDS}
        if not (p["nid"] or p["name"]):
            continue
        p["type"] = guess_type(p)
        p["_row"] = r
        p["_orig"] = {k: p[k] for k in RESULT_FIELDS}
        p["printed"] = {}
        persons.append(p)
    return persons


# ---------------------------------------------------------------- เขียนกลับต้นฉบับ (แก้ XML ในที่ ไม่แตะอย่างอื่น)
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _sheet_part(z, sheet_name):
    from lxml import etree
    wb = etree.fromstring(z.read("xl/workbook.xml"))
    rid = None
    for sh in wb.iter("{%s}sheet" % NS_MAIN):
        if sh.get("name") == sheet_name:
            rid = sh.get("{%s}id" % NS_REL)
    if not rid:
        raise ValueError("ไม่พบชีต " + sheet_name)
    rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for r in rels:
        if r.get("Id") == rid:
            t = r.get("Target")
            return t.lstrip("/") if t.startswith("/") else "xl/" + t
    raise ValueError("ไม่พบ part ของชีต")


def patch_sheet_xml(xml, edits):
    """edits: {(row:int, col:int): str} ตั้งค่าเซลล์เป็นข้อความ (ว่าง = ล้างค่า คงสไตล์เดิม)"""
    from lxml import etree
    root = etree.fromstring(xml, etree.XMLParser(huge_tree=True, remove_blank_text=False))
    sd = root.find("{%s}sheetData" % NS_MAIN)
    rows = {int(r.get("r")): r for r in sd.findall("{%s}row" % NS_MAIN)}
    q = lambda t: "{%s}%s" % (NS_MAIN, t)
    for (rn, cn), val in sorted(edits.items()):
        row = rows.get(rn)
        if row is None:
            row = etree.Element(q("row"))
            row.set("r", str(rn))
            after = [k for k in rows if k < rn]
            if after:
                rows[max(after)].addnext(row)
            else:
                sd.insert(0, row)
            rows[rn] = row
        ref = "%s%d" % (col_letter(cn), rn)
        cell = None
        pos = None
        for c in row.findall(q("c")):
            m = re.match(r"([A-Z]+)", c.get("r"))
            ci = col_index(m.group(1))
            if ci == cn:
                cell = c
                break
            if ci < cn:
                pos = c
        if cell is None:
            cell = etree.Element(q("c"))
            cell.set("r", ref)
            if pos is not None:
                pos.addnext(cell)
            else:
                row.insert(0, cell)
        for ch in list(cell):
            cell.remove(ch)
        if "t" in cell.attrib:
            del cell.attrib["t"]
        if val != "":
            cell.set("t", "inlineStr")
            is_ = etree.SubElement(cell, q("is"))
            t = etree.SubElement(is_, q("t"))
            t.text = val
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def write_back(db, backup=True, log=None):
    """เขียนเฉพาะช่องผลตรวจที่เปลี่ยน กลับไฟล์ต้นฉบับ คืน (จำนวนเซลล์, ที่อยู่ไฟล์สำรอง)"""
    src = db.source
    if is_xlsb(src.get("path", "")) and db.dirty_count():
        return -1, export_xlsb_as_xlsx(db)
    path, sheet, mapping = src.get("path"), src.get("sheet"), src.get("mapping", {})
    if not path or not os.path.exists(path):
        raise FileNotFoundError("ไม่พบไฟล์ต้นฉบับ: %s" % path)
    edits = {}
    for p in db.persons:
        for k in RESULT_FIELDS:
            c = mapping.get(k)
            if not c or not p.get("_row"):
                continue
            if p.get(k, "") != p.get("_orig", {}).get(k, ""):
                edits[(p["_row"], c)] = p.get(k, "")
    if not edits:
        return 0, ""
    bak = ""
    if backup:
        base, ext = os.path.splitext(path)
        bak = "%s.สำรอง-%s%s" % (base, time.strftime("%Y%m%d-%H%M%S"), ext)
        shutil.copy2(path, bak)
    with zipfile.ZipFile(path) as zin:
        part = _sheet_part(zin, sheet)
        new_xml = patch_sheet_xml(zin.read(part), edits)
        fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1], dir=os.path.dirname(path))
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w") as zout:
                for info in zin.infolist():
                    data = new_xml if info.filename == part else zin.read(info.filename)
                    zi = zipfile.ZipInfo(info.filename, info.date_time)
                    zi.compress_type = info.compress_type
                    zi.external_attr = info.external_attr
                    zi.create_system = info.create_system
                    zout.writestr(zi, data)
        except Exception:
            os.remove(tmp)
            raise
    try:
        os.replace(tmp, path)
    except PermissionError:
        os.remove(tmp)
        raise PermissionError("เขียนไฟล์ไม่ได้ (อาจเปิดค้างใน Excel) กรุณาปิดไฟล์แล้วลองใหม่")
    for p in db.persons:
        p["_orig"] = {k: p.get(k, "") for k in RESULT_FIELDS}
    db.save()
    return len(edits), bak
