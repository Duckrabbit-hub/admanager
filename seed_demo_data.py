"""seed_demo_data.py — สร้างข้อมูลตัวอย่าง (แคมเปญ + แชท) ให้เห็นภาพตอนเปิดใช้งานครั้งแรก

รันครั้งเดียวตอนติดตั้ง (หรือรันใหม่ได้ทุกเมื่อถ้าอยากรีเซ็ตข้อมูลตัวอย่าง — จะไม่ลบของจริงที่มีอยู่
ถ้าพบไฟล์ data/campaigns.json หรือ data/conversations.json อยู่แล้วจะข้ามไปเลย ไม่ทับข้อมูลจริงของผู้ใช้)

    python seed_demo_data.py
"""
import os
import uuid
from datetime import datetime, timedelta

import storage
from inbox import save_conversations, CONVERSATIONS_FILE
from storage import CAMPAIGNS_FILE


def _n_days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def seed_campaigns():
    if os.path.exists(CAMPAIGNS_FILE):
        print("data/campaigns.json มีอยู่แล้ว — ข้าม (ไม่ทับข้อมูลเดิม)")
        return
    demo = [
        {
            "name": "ตัวอย่าง: โปรโมชั่นเสื้อผ้าแฟชั่น",
            "platform": "facebook", "account_id": None, "account_label": None,
            "objective": "conversions", "daily_budget": 300.0, "original_daily_budget": 300.0,
            "start_date": _n_days_ago(18), "notes": "ตัวอย่างแคมเปญ — ลบได้จากหน้าแดชบอร์ด",
            "status": "active", "auto_paused": False, "automation_excluded": False,
            "platform_campaign_id": f"MOCK-FACEBOOK-{uuid.uuid4().hex[:6]}", "mode": "mock",
        },
        {
            "name": "ตัวอย่าง: วิดีโอรีวิวสินค้า",
            "platform": "tiktok", "account_id": None, "account_label": None,
            "objective": "awareness", "daily_budget": 150.0, "original_daily_budget": 150.0,
            "start_date": _n_days_ago(10), "notes": "ตัวอย่างแคมเปญ — ลบได้จากหน้าแดชบอร์ด",
            "status": "active", "auto_paused": False, "automation_excluded": False,
            "platform_campaign_id": f"MOCK-TIKTOK-{uuid.uuid4().hex[:6]}", "mode": "mock",
        },
        {
            "name": "ตัวอย่าง: โฆษณาในร้านค้า Shopee",
            "platform": "shopee", "account_id": None, "account_label": None,
            "objective": "traffic", "daily_budget": 100.0, "original_daily_budget": 100.0,
            "start_date": _n_days_ago(25), "notes": "ตัวอย่างแคมเปญ — ลบได้จากหน้าแดชบอร์ด",
            "status": "paused", "auto_paused": False, "automation_excluded": False,
            "platform_campaign_id": f"MOCK-SHOPEE-{uuid.uuid4().hex[:6]}", "mode": "mock",
        },
    ]
    for c in demo:
        storage.add_campaign(c)
    print(f"สร้างแคมเปญตัวอย่าง {len(demo)} รายการแล้ว")


def seed_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        print("data/conversations.json มีอยู่แล้ว — ข้าม (ไม่ทับข้อมูลเดิม)")
        return

    def ts(mins_ago):
        return (datetime.now() - timedelta(minutes=mins_ago)).strftime("%Y-%m-%d %H:%M")

    demo = [
        {
            "id": "conv_" + uuid.uuid4().hex[:10],
            "platform": "facebook", "account_id": None, "account_label": None,
            "customer_id": "demo_customer_1", "customer_name": "ลูกค้าตัวอย่าง (Facebook)",
            "platform_conversation_id": None,
            "messages": [
                {"id": uuid.uuid4().hex[:10], "from": "customer", "text": "สวัสดีค่ะ เสื้อตัวนี้มีไซส์ L ไหมคะ",
                 "at": ts(40), "mode": "live"},
                {"id": uuid.uuid4().hex[:10], "from": "page", "text": "สวัสดีค่ะ มีค่ะ รบกวนแจ้งรุ่นที่สนใจได้เลยค่ะ",
                 "at": ts(35), "mode": "mock", "error": None},
                {"id": uuid.uuid4().hex[:10], "from": "customer", "text": "รุ่นเสื้อยืดสีขาวค่ะ",
                 "at": ts(5), "mode": "live"},
            ],
            "last_message_at": ts(5), "unread": True,
        },
        {
            "id": "conv_" + uuid.uuid4().hex[:10],
            "platform": "shopee", "account_id": None, "account_label": None,
            "customer_id": "demo_customer_2", "customer_name": "ลูกค้าตัวอย่าง (Shopee)",
            "platform_conversation_id": None,
            "messages": [
                {"id": uuid.uuid4().hex[:10], "from": "customer", "text": "ของจัดส่งวันไหนคะ",
                 "at": ts(200), "mode": "mock"},
                {"id": uuid.uuid4().hex[:10], "from": "page", "text": "จัดส่งภายใน 1-2 วันทำการค่ะ",
                 "at": ts(190), "mode": "mock", "error": None},
            ],
            "last_message_at": ts(190), "unread": False,
        },
    ]
    save_conversations(demo)
    print(f"สร้างบทสนทนาตัวอย่าง {len(demo)} รายการแล้ว "
          "(นี่เป็นข้อมูลจำลองทั้งหมด — ข้อความจริงจาก Facebook webhook จะเข้ามาเพิ่มเองเมื่อมีลูกค้าทักมา)")


if __name__ == "__main__":
    seed_campaigns()
    seed_conversations()
    print("เสร็จแล้ว — เปิดเว็บแอปแล้วดูที่หน้าแดชบอร์ด/กล่องข้อความได้เลย")
