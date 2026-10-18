"""
config.py — โหลด/บันทึก credentials และค่าคงที่ของโปรแกรม

Credential schema (multi-account): data/credentials.json
{
  "facebook": [{"id": "acc_xxx", "label": "ร้าน A", "app_id": "...", "app_secret": "...",
                "access_token": "...", "ad_account_id": "...",
                "page_id": "...", "page_access_token": "...", "verify_token": "..."}, ...],
  "tiktok":   [{"id": "...", "label": "...", "app_id": "...", "app_secret": "...",
                "access_token": "...", "advertiser_id": "..."}, ...],
  "shopee":   [{"id": "...", "label": "...", "partner_id": "...", "partner_key": "...",
                "shop_id": "...", "access_token": "..."}, ...]
}

รองรับการ migrate อัตโนมัติจากไฟล์รูปแบบเก่า (บัญชีเดียวต่อแพลตฟอร์ม แบบ flat dict)
"""
import json
import os
import uuid

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(BASE_DIR, "data")
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")
_DB_KEY = "credentials"

PLATFORMS = ["facebook", "tiktok", "shopee"]

# ฟิลด์ที่ต้องกรอกครบถึงจะถือว่า "เชื่อมต่อจริงแล้ว" ต่อแพลตฟอร์ม (สำหรับยิงแอด)
REQUIRED_AD_FIELDS = {
    "facebook": ["app_id", "app_secret", "access_token", "ad_account_id"],
    "tiktok": ["app_id", "app_secret", "access_token", "advertiser_id"],
    "shopee": ["partner_id", "partner_key", "shop_id", "access_token"],
}

# ฟิลด์เพิ่มเติมสำหรับฟีเจอร์กล่องข้อความ (แยกจากสิทธิ์ยิงแอด เพราะเป็นคนละ permission scope)
MESSAGING_FIELDS = {
    "facebook": ["page_id", "page_access_token", "app_secret", "verify_token"],
    "shopee": ["partner_id", "partner_key", "shop_id", "access_token"],
}

ALL_FIELDS = {
    "facebook": ["app_id", "app_secret", "access_token", "ad_account_id",
                 "page_id", "page_access_token", "verify_token"],
    "tiktok": ["app_id", "app_secret", "access_token", "advertiser_id"],
    "shopee": ["partner_id", "partner_key", "shop_id", "access_token"],
}


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _new_id():
    return "acc_" + uuid.uuid4().hex[:10]


def _load_raw():
    if db.available():
        return db.get(_DB_KEY, {})
    _ensure_data_dir()
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_accounts():
    """โหลด credentials แล้วคืนค่าเป็น {platform: [account, ...]} เสมอ
    migrate รูปแบบเก่า {platform: {field: value}} ให้อัตโนมัติ"""
    raw = _load_raw()

    result = {p: [] for p in PLATFORMS}
    changed = False
    for platform in PLATFORMS:
        val = raw.get(platform)
        if val is None:
            continue
        if isinstance(val, list):
            result[platform] = val
        elif isinstance(val, dict):
            # รูปแบบเก่า: บัญชีเดียว ไม่มี list — ห่อเป็นบัญชีแรก
            if any(val.get(f) for f in ALL_FIELDS.get(platform, [])):
                acc = dict(val)
                acc.setdefault("id", _new_id())
                acc.setdefault("label", "บัญชีหลัก")
                result[platform] = [acc]
                changed = True

    if changed:
        save_accounts(result)
    return result


def save_accounts(accounts):
    if db.available():
        db.set(_DB_KEY, accounts)
        return
    _ensure_data_dir()
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def list_accounts(platform):
    return load_accounts().get(platform, [])


def get_account(platform, account_id):
    if not account_id:
        return None
    for acc in list_accounts(platform):
        if acc.get("id") == account_id:
            return acc
    return None


def add_account(platform, label, fields):
    accounts = load_accounts()
    acc = {"id": _new_id(), "label": label or "บัญชีใหม่"}
    acc.update(fields)
    accounts.setdefault(platform, []).append(acc)
    save_accounts(accounts)
    return acc


def update_account(platform, account_id, label, fields):
    accounts = load_accounts()
    for acc in accounts.get(platform, []):
        if acc.get("id") == account_id:
            if label:
                acc["label"] = label
            acc.update(fields)
            save_accounts(accounts)
            return acc
    return None


def delete_account(platform, account_id):
    accounts = load_accounts()
    before = len(accounts.get(platform, []))
    accounts[platform] = [a for a in accounts.get(platform, []) if a.get("id") != account_id]
    save_accounts(accounts)
    return len(accounts[platform]) < before


def is_account_configured(platform, account):
    if not account:
        return False
    required = REQUIRED_AD_FIELDS.get(platform, [])
    return all(account.get(f) for f in required)


def account_is_configured(platform, account_id):
    return is_account_configured(platform, get_account(platform, account_id))


def is_platform_configured(platform):
    return any(is_account_configured(platform, a) for a in list_accounts(platform))


def is_messaging_configured(platform, account):
    if not account:
        return False
    required = MESSAGING_FIELDS.get(platform, [])
    if not required:
        return False
    return all(account.get(f) for f in required)


def accounts_by_platform():
    accounts = load_accounts()
    return {p: accounts.get(p, []) for p in PLATFORMS}
