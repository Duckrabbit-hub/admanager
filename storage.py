"""storage.py — เก็บข้อมูลแคมเปญ

ถ้ามี DATABASE_URL (deploy บนเว็บ) จะเก็บถาวรในฐานข้อมูล Postgres ผ่าน db.py
ถ้าไม่มี (รันโหมด desktop ในเครื่อง) จะเก็บเป็นไฟล์ JSON ในเครื่องเหมือนเดิม — ดู db.py
"""
import json
import os
import uuid
from datetime import datetime

import db
from config import DATA_DIR

CAMPAIGNS_FILE = os.path.join(DATA_DIR, "campaigns.json")
_DB_KEY = "campaigns"


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_campaigns():
    if db.available():
        return db.get(_DB_KEY, [])
    _ensure_data_dir()
    if not os.path.exists(CAMPAIGNS_FILE):
        return []
    try:
        with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_campaigns(campaigns):
    if db.available():
        db.set(_DB_KEY, campaigns)
        return
    _ensure_data_dir()
    with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
        json.dump(campaigns, f, ensure_ascii=False, indent=2)


def get_campaign(campaign_id):
    for c in load_campaigns():
        if c["id"] == campaign_id:
            return c
    return None


def add_campaign(campaign):
    campaigns = load_campaigns()
    campaign.setdefault("id", uuid.uuid4().hex[:8])
    campaign.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    campaigns.append(campaign)
    save_campaigns(campaigns)
    return campaign


def update_campaign(campaign_id, **fields):
    campaigns = load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            c.update(fields)
            save_campaigns(campaigns)
            return c
    return None


def delete_campaign(campaign_id):
    campaigns = load_campaigns()
    campaigns = [c for c in campaigns if c["id"] != campaign_id]
    save_campaigns(campaigns)
