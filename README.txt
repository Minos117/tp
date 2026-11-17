ZAIA Prepare Personal  1.0.0 (Stable)
==============================================
สร้างเป็นโปรแกรม Windows + ไฟล์ Setup:
  1) แตก ZIP นี้ไว้ที่ใดก็ได้ (พาธไม่ควรมีอักขระแปลก)
  2) ดับเบิลคลิก build_all.bat  (ต้องต่ออินเทอร์เน็ต)
     - ติดตั้ง Python 3.12 (ถ้าไม่มี, ผ่าน winget -> ปิดหน้าต่างแล้วรันซ้ำ) + แพ็กเกจ (openpyxl, lxml, pillow, pywin32, pyinstaller)
     - สร้าง exe ด้วย PyInstaller -> dist\ZAIA Prepare Personal\
     - ติดตั้ง/ใช้ Inno Setup 6 สร้าง Setup -> Output\ZAIA_Prepare_Personal_Setup_1.0.0.exe
     - สร้าง release\update.json (SHA-256) สำหรับระบบอัปเดต
  3) รัน Setup ติดตั้ง (ติดตั้งแบบผู้ใช้ ไม่ต้องสิทธิ์ผู้ดูแล)

ใช้งาน: เมนู 1 นำเข้าข้อมูล -> 3 บันทึกผล -> "เขียนผลกลับไฟล์ Excel" -> 4/5/2 พิมพ์
ข้อมูลโปรแกรมเก็บที่ %APPDATA%\ZAIA Prepare Personal\ (data.json, settings.json, PrintLog.txt)

แก้เวอร์ชัน: zaia\version.py (APP_VER, SETUP_REV) + installer.iss (AppVersion) + update.json ต้องตรงกัน
(MakeRelease.py ตรวจให้และหยุดถ้าไม่ตรง)
อัปเดต: ใส่ URL GitHub Raw ใน zaia\version.py (UPDATE_BASE) หรือหน้าตั้งค่า -> โปรแกรมตรวจรุ่นตอนเปิดแบบเงียบ (แจ้งเตือนอย่างเดียว)
ข้อมูลจังหวัด/อำเภอ: kongvut/thai-province-data (MIT)

ยังไม่เคยทดสอบบน Windows จริง: การพิมพ์ GDI, build_all.bat, PyInstaller, Inno Setup, ตัวอัปเดตกับ GitHub จริง
รองรับนำเข้า .xlsx/.xlsm/.xlsb  (.xlsb เขียนกลับไม่ได้ -> สร้าง .xlsx ใหม่ ค่าล้วน)
โลโก้: assets\logo.png / logo.ico (วาดขึ้นใหม่ ใช้เป็นไอคอน exe และ Setup)

กติกาอัปเดต (ห้ามแตะ เพื่อให้ทุกรุ่นอัปเดตได้ตลอด):
  - UPDATE_BASE = https://raw.githubusercontent.com/Minos117/tp/main/  (update.json อยู่ราก repo, ไฟล์อยู่ files/)
  - update.json คงโครง version, setup_rev, files[path,url,sha256,size] เสมอ (เพิ่มคีย์ใหม่ได้ ห้ามลบ/เปลี่ยนชื่อ)
  - ตัวอัปเดตเทียบ hash ทุกไฟล์ จึงข้ามรุ่นได้ไม่จำกัด; setup_rev เป็นแค่คำแนะนำ ไม่บล็อกการอัปเดต
  - ทุกรุ่นถัดไปต้องมี zaia\updater.py ที่ใช้ manifest รูปแบบเดิมได้
