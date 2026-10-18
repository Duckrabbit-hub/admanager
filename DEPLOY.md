# Deploy ขึ้นเว็บ (ตัวเลือกอื่นนอกจาก PythonAnywhere)

ถ้าต้องการเว็บที่เร็วกว่า/ไม่ต้องวอร์มอัพจาก idle หรือรองรับทราฟฟิกมากกว่า tier ฟรีของ PythonAnywhere
(ดู `DEPLOY-FREE.md` ถ้าไม่อยากผูกบัตรเครดิตเลย) นี่คือวิธี deploy ด้วย [Render](https://render.com)
ซึ่งมีไฟล์ตั้งค่าเตรียมไว้ให้แล้ว (`render.yaml`, `Procfile`)

> ℹ️ เงื่อนไขเรื่องบัตรเครดิต/เดบิตของแต่ละแพลตฟอร์มโฮสติ้งเปลี่ยนแปลงได้ตลอด แนะนำให้เช็คหน้า pricing ของ
> Render ให้แน่ใจอีกครั้งก่อนสมัคร ถ้าไม่สะดวกผูกบัตรเลยให้ใช้ `DEPLOY-FREE.md` แทน
>
> ⚠️ **ถ้าเลือก plan ฟรีของ Render**: เว็บจะ sleep หลังไม่มีคนเข้าประมาณ 15 นาที — ตอนหลับ ระบบอัตโนมัติ
> (Auto-Pilot) จะไม่ได้ตรวจแคมเปญตามรอบที่ตั้งไว้ และ Facebook จะส่ง webhook มาไม่ถึง (ต้องรอเว็บตื่นก่อน ซึ่งมี
> ดีเลย์) จึงไม่เหมาะกับใช้ฟีเจอร์เรียลไทม์จริงจัง เหมาะกับ demo/ทดสอบเท่านั้น — ถ้าต้องการให้ทำงานต่อเนื่องจริง
> ต้องใช้ plan เสียเงินของ Render (ไม่ sleep) หรือพิจารณา VPS ของตัวเองด้านล่าง

## ขั้นตอน

1. อัปโหลดโค้ดโปรแกรมขึ้น GitHub repository ของคุณ (ไฟล์ `render.yaml` และ `Procfile` รวมอยู่ในนั้นแล้ว)
2. เข้า [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** → เชื่อม repository
   ที่อัปโหลดไว้ → Render จะอ่านค่าจาก `render.yaml` ให้อัตโนมัติ
3. ตอนตั้งค่า ใส่ค่า environment variables ที่ Render จะถามหา (`ADMIN_USERNAME`, `ADMIN_PASSWORD`) —
   `SECRET_KEY` ถูกตั้งให้สุ่มอัตโนมัติแล้วจาก `render.yaml`
4. กด **Apply** / **Deploy** รอ build เสร็จ จะได้ URL แบบ `https://adshooter-xxxx.onrender.com`
5. (ไม่บังคับ) เปิด Shell ของ service นั้นจากหน้า Render แล้วรันครั้งเดียว `python seed_demo_data.py`
   เพื่อสร้างข้อมูลตัวอย่างให้ดูก่อน

ไฟล์ `render.yaml` ตั้งดิสก์ถาวร (`/var/data`) ไว้ให้แล้ว เพื่อไม่ให้ข้อมูลแคมเปญ/แชทหายตอน redeploy —
ถ้าย้ายไปแพลตฟอร์มอื่นที่ไม่มีดิสก์ถาวร ต้องหาทางเก็บข้อมูลแยก (เช่น เชื่อมฐานข้อมูลภายนอก) เองเพิ่มเติม

## เปิดใช้งานกล่องข้อความเรียลไทม์ (Facebook webhook)

URL ที่ได้จาก Render เป็น HTTPS สาธารณะอยู่แล้ว นำ `https://<โดเมนของคุณ>/webhook/facebook` ไปตั้งในหน้า
Meta App Dashboard ตามขั้นตอนใน [`docs_api_setup_guide.md`](./docs_api_setup_guide.md) ได้เลย

## รันด้วย Docker/VPS ของตัวเอง

ถ้ามี VPS อยู่แล้ว ใช้คำสั่งนี้รันได้โดยไม่ต้องพึ่ง Render:

```bash
pip install -r requirements.txt
export ADMIN_USERNAME=admin ADMIN_PASSWORD=รหัสผ่านจริง SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
gunicorn app:app --bind 0.0.0.0:8000 --workers 1 --threads 4
```

แล้วตั้ง reverse proxy (เช่น Nginx/Caddy) ให้มี HTTPS หน้าบ้าน (จำเป็นสำหรับฟีเจอร์กล่องข้อความเรียลไทม์)
