# คู่มือเตรียมความพร้อม API: Facebook, TikTok, Shopee (ยิงแอด + กล่องข้อความ)

เอกสารนี้สรุปสิ่งที่ต้อง "ขอ/สมัคร" กับแต่ละแพลตฟอร์ม ก่อนที่โปรแกรมจะเชื่อมต่อ API จริงได้ เพราะทั้ง 3
แพลตฟอร์มไม่ได้ให้สิทธิ์ยิงแอด/อ่านแชทอัตโนมัติกับทุกคนทันที ต้องผ่านขั้นตอนตรวจสอบก่อน — **ระหว่างรอ
อนุมัติ โปรแกรมใช้งานได้เต็มรูปแบบด้วยข้อมูลจำลอง (mock data)** ทั้งฝั่งยิงแอดและฝั่งกล่องข้อความ แล้วค่อย
สลับเป็นของจริงอัตโนมัติทันทีที่กรอก credentials ครบในหน้า "ตั้งค่า API"

## สรุปภาพรวม

| แพลตฟอร์ม | สิทธิ์ที่ต้องขอ | ใครอนุมัติ | เวลาโดยประมาณ |
|---|---|---|---|
| Facebook (Meta) — ยิงแอด | Business Verification + App Review (`ads_management`) | Meta ตรวจสอบเอง | หลายวัน–หลายสัปดาห์ |
| Facebook (Meta) — กล่องข้อความ | App Review (`pages_messaging`) + ตั้ง webhook | Meta ตรวจสอบเอง | หลายวัน–หลายสัปดาห์ (แยกจากสิทธิ์ยิงแอด) |
| TikTok — ยิงแอด | สมัคร TikTok for Business Developer + สร้าง App | TikTok ตรวจสอบ | ~2-3 วันทำการ |
| TikTok — กล่องข้อความ | ไม่มี — TikTok ไม่มี API แชทสาธารณะสำหรับเรื่องนี้ | — | — |
| Shopee — ยิงแอด/แชท | กรอกฟอร์มขอ API (Shopee API Request Form) ผ่าน Open Platform | Shopee ตรวจสอบ | ไม่ระบุแน่ชัด |

---

## 1. Facebook / Meta — ยิงแอด (Marketing API)

### ขั้นตอน
1. สร้าง Meta Business Portfolio (business.facebook.com) และ **Business Verification** — ยืนยันตัวตนธุรกิจ
   ด้วยเอกสารทางกฎหมาย (ทะเบียนการค้า/นิติบุคคล, ที่อยู่, เบอร์โทร, เว็บไซต์)
2. สร้างแอปที่ developers.facebook.com เลือกประเภท "Business"
3. เพิ่มผลิตภัณฑ์ **Marketing API** เข้าแอป
4. ยื่นขอสิทธิ์ `ads_management` ผ่าน App Review (อาจต้องขอ `business_management`, `pages_read_engagement`
   ร่วมด้วย) — ต้องมีการเรียก Marketing API ใช้งานจริงอย่างน้อย ~500 ครั้งใน 15 วัน error rate ต่ำกว่า 15%
   ก่อนขอสิทธิ์ระดับสูงได้ (เกณฑ์นี้ปรับได้ตามประกาศของ Meta)
5. ผ่านแล้วต้องทำ **annual data use recertification** ทุกปีภายใน 60 วัน ไม่งั้นสิทธิ์ถูกระงับอัตโนมัติ

### Credentials ที่จะได้ → กรอกในหน้าตั้งค่า
`App ID`, `App Secret`, `Access Token` (ของ Ad Account), `Ad Account ID`

---

## 2. Facebook / Meta — กล่องข้อความ (Messenger Platform, ใหม่)

ฟีเจอร์นี้ใช้สิทธิ์ **คนละตัว** กับการยิงแอด (permission scope แยกกันคนละอย่าง) ต้องขอ App Review แยกต่างหาก
แม้จะใช้แอป Meta เดียวกันก็ตาม

### ขั้นตอน
1. ในแอป Meta เดิม (หรือสร้างใหม่) เพิ่มผลิตภัณฑ์ **Messenger**
2. เชื่อม Facebook Page ที่ต้องการตอบแชทเข้ากับแอป แล้วสร้าง **Page Access Token** จากหน้า Messenger →
   Settings ของแอป
3. ตั้งค่า **Webhook**: ไปที่ Messenger → Settings → Webhooks → กรอก
   - **Callback URL**: `https://<โดเมนที่ deploy ไว้>/webhook/facebook` (ต้องเป็น HTTPS สาธารณะ — ดู
     `DEPLOY-FREE.md`/`DEPLOY.md` ถ้ายังไม่มี ใช้ localhost/เครื่องตัวเองตรง ๆ ไม่ได้)
   - **Verify Token**: ตั้งค่าอะไรก็ได้ (เป็นรหัสที่ใช้ยืนยันว่า request มาจาก Meta จริง) แล้วเอาค่าเดียวกัน
     ไปกรอกในช่อง "Verify Token" ของหน้าตั้งค่าโปรแกรมด้วย — ต้องตรงกันทั้งสองที่
   - เลือก subscribe field อย่างน้อย `messages`
4. ยื่นขอสิทธิ์ `pages_messaging` ผ่าน App Review — ระหว่างรออนุมัติ ใช้ได้กับเพจที่เป็น Admin/Tester ของแอป
   เอง (โหมดทดสอบ) ก่อนได้
5. กรอก `Page ID`, `Page Access Token`, `App Secret`, `Verify Token` ในหน้าตั้งค่าโปรแกรม (ช่องเดียวกับฝั่ง
   ยิงแอด แต่เป็นฟิลด์คนละชุด) — โปรแกรมใช้ `App Secret` ตรวจลายเซ็นของทุก request ที่เข้ามาที่ webhook
   เพื่อกันข้อมูลปลอม

### Credentials ที่จะได้ → กรอกในหน้าตั้งค่า
`Page ID`, `Page Access Token`, `App Secret` (ใช้ตัวเดียวกับแอป), `Verify Token` (ตั้งเอง)

### ข้อจำกัด
- ต้องมี URL สาธารณะ HTTPS เสมอ ใช้กับเครื่องส่วนตัว/desktop mode เฉย ๆ ไม่ได้
- ถ้ายังไม่ผ่าน App Review จะใช้ได้แค่กับเพจที่เป็น Admin/Developer/Tester ของแอปเท่านั้น

---

## 3. TikTok Business API (ยิงแอด)

### ขั้นตอน
1. ไปที่ business-api.tiktok.com/portal → สมัครสมาชิก (ยืนยันเบอร์โทร/OTP)
2. เลือก "Become a Developer" → เลือกประเภทบริษัท **Direct Advertiser** หรือ Agency/Partner
3. กรอกข้อมูลบริษัท (ชื่อ, เว็บไซต์)
4. สร้างแอปใหม่ในเมนู "Create Application"
5. รออนุมัติแอปประมาณ 2-3 วันทำการ แล้วดู `App ID`/`Secret` ที่ "My Apps"
6. ทำ OAuth เพื่อขอ `access_token` เชื่อมกับบัญชีโฆษณา TikTok Ads ของตัวเอง

### Credentials ที่จะได้
`App ID`, `App Secret`, `Access Token`, `Advertiser ID`

**หมายเหตุเรื่องกล่องข้อความ**: TikTok ไม่มี public API สำหรับแชทกับลูกค้าในลักษณะนี้ จึงไม่มีในฟีเจอร์
กล่องข้อความของโปรแกรม (ใช้ตอบในแอป TikTok โดยตรงไปก่อน)

---

## 4. Shopee Open Platform (ยิงแอด + แชท)

Shopee มี API ทั้งสำหรับยิงแอด (Shop/Product Ads) และแชทกับลูกค้า (Seller Chat API) ผ่านโมดูลเดียวกันของ
Shopee Open Platform แต่รายละเอียดเกณฑ์อนุมัติเปิดเผยต่อสาธารณะน้อยกว่า Facebook/TikTok

### ขั้นตอน (เท่าที่ทราบจากเอกสาร Shopee)
1. เข้า Shopee Open Platform (open.shopee.com) หรือกรอก **Shopee API Request Form** ที่ Seller Centre/
   Partner ให้มา — ระบุด้วยว่าต้องการสิทธิ์ Ads API และ/หรือ Chat API
2. รอ Shopee ตรวจสอบและส่ง credentials กลับมา (`Partner ID`, `Partner Key`, `Shop ID`, `Access Token`)
3. นำ credentials ไปกรอกใน Shopee Seller Centre เพื่อเปิดใช้งาน แล้วกรอกชุดเดียวกันในหน้าตั้งค่าโปรแกรม
   (ใช้ credential ชุดเดียวกันทั้งฝั่งยิงแอดและฝั่งแชท)
4. สำหรับร้านค้าเดี่ยวมักได้สิทธิ์ "Shop API" ถ้าต้องการทำระบบให้ลูกค้าหลายร้าน ต้องสมัครเป็น **ISV/Partner**
   ซึ่งมีกระบวนการตรวจสอบเพิ่มเติม

### ⚠️ ข้อควรระวัง
- เกณฑ์อนุมัติของ Shopee ไม่เปิดเผยตายตัวเหมือน Meta/TikTok แนะนำติดต่อ Shopee Partner Support หรือ
  Seller Centre โดยตรงเพื่อขอฟอร์มล่าสุด
- Shopee ยังไม่มี webhook แบบเรียลไทม์ในเวอร์ชันนี้ของโปรแกรม — ข้อความจาก Shopee ในกล่องข้อความจะเป็น
  ข้อมูลตัวอย่าง/ต้องรอการเชื่อม API ก่อน (ฝั่ง "ส่ง" ตอบกลับทำงานผ่าน API ได้ทันทีที่เชื่อมแล้ว)
- ถ้าไม่ได้รับอนุมัติ API ของฝั่งยิงแอด มีทางเลือกสำรองคือใช้ Claude ควบคุมเบราว์เซอร์เข้าไปสร้าง/ปรับแคมเปญ
  ใน Shopee Ads Manager แทน (ไม่ใช่ API แต่ทำงานแทนคนกดจริง) — บอกได้เลยถ้าต้องการให้ตั้งค่าทางนี้

### Credentials ที่จะได้
`Partner ID`, `Partner Key`, `Shop ID`, `Access Token`

---

## สรุปสิ่งที่ต้องทำต่อ (Action Items)

1. [ ] จดทะเบียน/ยืนยันตัวตนธุรกิจให้พร้อม (ใช้ซ้ำได้ทั้ง 3 แพลตฟอร์ม)
2. [ ] สมัคร Meta Business Manager + Business Verification + App Review สิทธิ์ `ads_management`
3. [ ] (ถ้าต้องการกล่องข้อความ) ขอสิทธิ์ `pages_messaging` แยกต่างหาก + ตั้ง webhook ตามขั้นตอนข้างบน
4. [ ] สมัคร TikTok for Business Developer + สร้างแอป
5. [ ] ติดต่อ Shopee เพื่อขอฟอร์มสมัคร Open API (ระบุทั้ง Ads API และ Chat API ถ้าต้องการทั้งคู่)
6. [ ] เมื่อได้ credentials แต่ละอันแล้ว นำไปกรอกในหน้า **ตั้งค่า (Settings)** ของโปรแกรม ระบบจะสลับจาก
   mock data → เรียก API จริงให้อัตโนมัติ ทีละแพลตฟอร์มได้ ไม่ต้องรอให้ครบทุกอัน

ระหว่างรอการอนุมัติ โปรแกรมใช้งานได้เต็มรูปแบบด้วยข้อมูลจำลอง เพื่อออกแบบ workflow ทดสอบหน้าตา และเตรียม
ทีมงานให้พร้อมก่อนต่อ API จริง
