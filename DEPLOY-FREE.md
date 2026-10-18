# Deploy ฟรี ไม่ต้องใช้บัตรเครดิต/เดบิต (PythonAnywhere)

วิธีนี้ไม่ต้องกรอกบัตรเครดิต/เดบิตเลย เหมาะกับเริ่มใช้งานจริงแบบเบา ๆ หรือทดสอบฟีเจอร์กล่องข้อความเรียลไทม์
(ซึ่งต้องมี URL สาธารณะแบบ HTTPS — PythonAnywhere ให้ URL แบบนี้มาให้ฟรีทันทีที่สมัคร)

**ข้อจำกัดที่ควรรู้ก่อน**: tier ฟรีจำกัด CPU seconds/วัน และบางครั้งเว็บช้ากว่าปกติตอนเพิ่งปลุกจาก idle
— เหมาะกับใช้งานจริงระดับเล็ก/กลาง หรือทดสอบก่อน ถ้าทราฟฟิกมากขึ้นค่อยพิจารณาแพลตฟอร์มอื่นใน `DEPLOY.md`

> ⚠️ **สำคัญ**: PythonAnywhere free tier **บล็อก outbound HTTP request ไปโดเมนนอก whitelist ที่เขากำหนด**
> — การเรียก API จริงของ Facebook/TikTok/Shopee (ซึ่งเป็นการเรียกออกจากเซิร์ฟเวอร์นี้ไปยังโดเมนนอก) **อาจใช้
> ไม่ได้บน plan ฟรี** (ระบบจะ fallback เป็นข้อมูลจำลองอัตโนมัติ ไม่ error แต่จะไม่ใช่ข้อมูลจริง) ส่วน **webhook
> กล่องข้อความ (ข้อมูลวิ่งเข้ามาจาก Facebook เข้าเซิร์ฟเวอร์นี้ ไม่ใช่ขาออก) ใช้งานได้ตามปกติไม่ติดปัญหานี้** —
> ถ้าต้องการให้ยิงแอด API จริงทำงานได้ด้วย ให้อัปเกรด plan ของ PythonAnywhere ที่ปลดบล็อกโดเมนนอก whitelist
> หรือพิจารณา deploy แบบอื่นใน `DEPLOY.md` แทน (ข้อจำกัดนี้อาจเปลี่ยนแปลงได้ ควรเช็คหน้า pricing/forum ของ
> PythonAnywhere อีกครั้งก่อนตัดสินใจ)

## 1. สมัครบัญชี

ไปที่ [pythonanywhere.com](https://www.pythonanywhere.com) → Pricing & signup → เลือก **Create a Beginner account**
(ฟรี ไม่ขอบัตร) → ยืนยันอีเมล

## 2. อัปโหลดโค้ดโปรแกรม

เปิดแท็บ **Files** แล้วอัปโหลดไฟล์ `admanager.zip` ทั้งโฟลเดอร์ (หรือใช้แท็บ **Consoles** → Bash แล้ว
`git clone`/`wget` ถ้าโค้ดอยู่บน GitHub ของคุณ) จากนั้นแตกไฟล์ในแท็บ Bash console:

```bash
unzip admanager.zip -d admanager
cd admanager
```

## 3. สร้าง virtualenv และติดตั้งไลบรารี

ในแท็บ Bash console เดิม:

```bash
mkvirtualenv --python=python3.10 admanager-env
pip install -r requirements.txt
python seed_demo_data.py   # ไม่บังคับ แค่สร้างข้อมูลตัวอย่างให้ดูก่อน
```

(ครั้งต่อไปที่เปิด Bash console ใหม่ ต้องสั่ง `workon admanager-env` ก่อนถึงจะใช้ venv นี้ต่อได้)

## 4. สร้าง Web app

ไปที่แท็บ **Web** → **Add a new web app** → เลือก **Manual configuration** (ห้ามเลือก Flask เพราะจะสร้าง
โค้ดใหม่ทับ) → เลือกเวอร์ชัน Python ให้ตรงกับที่สร้าง venv ไว้ (เช่น 3.10)

กรอกในหน้าตั้งค่า Web app:

| ช่อง | ค่า |
|---|---|
| Source code | `/home/<ชื่อผู้ใช้>/admanager` |
| Working directory | `/home/<ชื่อผู้ใช้>/admanager` |
| Virtualenv | `/home/<ชื่อผู้ใช้>/.virtualenvs/admanager-env` |
| Static files URL | `/static/` |
| Static files Directory | `/home/<ชื่อผู้ใช้>/admanager/static` |

## 5. แก้ไฟล์ WSGI

คลิกลิงก์ไฟล์ WSGI (เช่น `/var/www/<ชื่อผู้ใช้>_pythonanywhere_com_wsgi.py`) แล้ว**ลบเนื้อหาเดิมทั้งหมด**
แทนด้วยโค้ดนี้ (แก้ `<ชื่อผู้ใช้>` และค่า `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SECRET_KEY` ให้เป็นของจริง
ก่อนบันทึก — **ตั้งรหัสผ่านให้คาดเดายาก** เพราะหน้านี้จะเป็นสาธารณะทันทีที่เปิดใช้งาน):

```python
import os
import sys

path = "/home/<ชื่อผู้ใช้>/admanager"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "ตั้งรหัสผ่านที่นี่"
os.environ["SECRET_KEY"] = "ตั้งเป็นตัวอักษร/เลขสุ่มยาว ๆ ที่นี่"

from app import app as application
```

> ⚠️ ระวังอย่าวางค่าตัวแปรใด ๆ ไว้นอกบรรทัด `os.environ[...] = "..."` เฉย ๆ (เช่น วางคีย์ลอย ๆ แยกบรรทัด)
> เพราะ Python จะอ่านเป็นชื่อตัวแปรที่ไม่มีค่า แล้วทำให้เว็บพังตั้งแต่โหลดไฟล์

บันทึกไฟล์ แล้วกลับไปแท็บ **Web** กดปุ่ม **Reload**

## 6. เปิดเว็บ

เว็บจะอยู่ที่ `https://<ชื่อผู้ใช้>.pythonanywhere.com` — ถ้าเปิดแล้วค้าง/ช้ามาก ให้กด Reload อีกครั้งแล้วรอ
30-45 วินาทีก่อนลองใหม่ (เว็บที่เพิ่ง deploy หรือเพิ่งตื่นจาก idle ต้องวอร์มอัพก่อน) ถ้ายัง error ให้ดูไฟล์
log ที่แท็บ Web (Error log / Server log)

## 7. เปิดใช้งานกล่องข้อความเรียลไทม์ (Facebook webhook)

URL ของคุณ (`https://<ชื่อผู้ใช้>.pythonanywhere.com`) เป็น HTTPS สาธารณะอยู่แล้ว ใช้เป็น webhook ได้ทันที —
นำ `https://<ชื่อผู้ใช้>.pythonanywhere.com/webhook/facebook` ไปตั้งในหน้า Meta App Dashboard ตามขั้นตอนใน
[`docs_api_setup_guide.md`](./docs_api_setup_guide.md)

## อัปเดตโค้ดเวอร์ชันใหม่ทีหลัง

อัปโหลด/แทนที่ไฟล์ในโฟลเดอร์ `admanager` ให้เป็นเวอร์ชันใหม่ แล้วกด **Reload** ที่แท็บ Web อีกครั้ง (ไม่ต้อง
สร้าง venv ใหม่ ถ้า `requirements.txt` ไม่เปลี่ยน)
