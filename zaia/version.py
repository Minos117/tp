APP_NAME = "ZAIA Prepare Personal"
APP_VER = "1.0.9"      # ต้องตรงกับ AppVersion ใน installer.iss และ update.json (MakeRelease.py ตรวจให้)
SETUP_REV = 1          # เพิ่มเลขนี้เมื่อต้องติดตั้งใหม่ด้วย setup (ไม่ใช่แค่แทนที่ไฟล์)
# ใส่ URL ฐานของ GitHub Raw ที่เก็บ update.json เช่น https://raw.githubusercontent.com/OWNER/REPO/main/
# ห้ามเปลี่ยน URL นี้และรูปแบบ update.json (version, setup_rev, files[path,url,sha256,size]) ใน GitHub -- ทุกรุ่นทุกเครื่องพึ่งสิ่งนี้เพื่ออัปเดตได้ตลอด
UPDATE_BASE = "https://raw.githubusercontent.com/Minos117/tp/main/"
