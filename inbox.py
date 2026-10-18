"""inbox.py — กล่องข้อความรวม (Unified Inbox)

รวมแชทจากทุกเพจ/ร้านค้าที่เชื่อมไว้ในระบบไว้ที่เดียว ตอบลูกค้าได้โดยไม่ต้อง login
Facebook/Shopee โดยตรง (ใช้ Page Access Token / Shopee Chat API ที่กรอกไว้ในหน้าตั้งค่า)

- ข้อความใหม่เข้ามาแบบเรียลไทม์ผ่าน Facebook Messenger webhook (/webhook/facebook)
  Shopee ยังไม่มี webhook ในเวอร์ชันนี้ (ดู docs_api_setup_guide.md) — ใช้ mock/seed data แสดงตัวอย่างแทน
- ถ้ายังไม่ได้กรอก credential จริง การ "ตอบ" จะเป็นแค่การจำลอง (ไม่ได้ส่งถึงลูกค้าจริง)
  — ระบบจะโชว์ป้ายเตือนให้เห็นชัดเจนเสมอ กันเข้าใจผิด
"""
import json
import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import config
import db
from messaging import MESSAGING_PLATFORMS, get_messaging_connector
from messaging.facebook_messenger import verify_signature

CONVERSATIONS_FILE = os.path.join(config.DATA_DIR, "conversations.json")
_DB_KEY = "conversations"

bp = Blueprint("inbox", __name__)


# ---------------------------------------------------------------------------
# storage — ถ้ามี DATABASE_URL เก็บถาวรในฐานข้อมูล ไม่งั้น fallback ไฟล์ JSON ในเครื่อง
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def load_conversations():
    if db.available():
        return db.get(_DB_KEY, [])
    _ensure_data_dir()
    if not os.path.exists(CONVERSATIONS_FILE):
        return []
    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_conversations(conversations):
    if db.available():
        db.set(_DB_KEY, conversations)
        return
    _ensure_data_dir()
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)


def get_conversation(conv_id):
    for c in load_conversations():
        if c["id"] == conv_id:
            return c
    return None


def count_unread():
    return sum(1 for c in load_conversations() if c.get("unread"))


def _find_account_by_page_id(page_id):
    for acc in config.list_accounts("facebook"):
        if acc.get("page_id") == page_id:
            return acc
    return None


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# webhook รับข้อความเข้าแบบเรียลไทม์ (Facebook Messenger)
# ---------------------------------------------------------------------------

@bp.route("/webhook/facebook", methods=["GET", "POST"])
def webhook_facebook():
    if request.method == "GET":
        # Facebook เรียกตอนตั้งค่า webhook ครั้งแรกในหน้า App Dashboard เพื่อยืนยันว่า URL นี้เป็นของเราจริง
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge", "")
        known_tokens = {a.get("verify_token") for a in config.list_accounts("facebook") if a.get("verify_token")}
        if mode == "subscribe" and token and token in known_tokens:
            return challenge, 200
        return "verification failed", 403

    # POST — ข้อความ/อีเวนต์ใหม่เข้ามาจริง
    raw_body = request.get_data()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return jsonify({"status": "bad payload"}), 400

    if payload.get("object") != "page":
        return jsonify({"status": "ignored"}), 200

    for entry in payload.get("entry", []):
        page_id = entry.get("id")
        account = _find_account_by_page_id(page_id)

        # ตรวจลายเซ็น X-Hub-Signature-256 ด้วย app_secret ของบัญชีที่ตรงกับเพจนี้ กันข้อมูลปลอม
        if account and account.get("app_secret"):
            sig = request.headers.get("X-Hub-Signature-256", "")
            if not verify_signature(account["app_secret"], raw_body, sig):
                continue  # ลายเซ็นไม่ตรง ข้ามอีเวนต์นี้ (ไม่ใช่ของจริงจาก Facebook)

        for event in entry.get("messaging", []):
            message = event.get("message")
            if not message or message.get("is_echo"):
                continue  # ข้าม echo ของข้อความที่เราส่งเอง
            sender_id = event.get("sender", {}).get("id")
            text = message.get("text", "")
            if sender_id and text:
                _ingest_incoming_message(
                    platform="facebook",
                    account=account,
                    customer_id=sender_id,
                    customer_name=f"ลูกค้า Facebook ({sender_id[-6:]})",
                    text=text,
                )
    return jsonify({"status": "ok"}), 200


def _ingest_incoming_message(platform, account, customer_id, customer_name, text):
    conversations = load_conversations()
    account_id = account.get("id") if account else None
    account_label = account.get("label") if account else None

    conv = None
    for c in conversations:
        if c["platform"] == platform and c["customer_id"] == customer_id and c.get("account_id") == account_id:
            conv = c
            break

    if conv is None:
        conv = {
            "id": "conv_" + uuid.uuid4().hex[:10],
            "platform": platform,
            "account_id": account_id,
            "account_label": account_label,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "platform_conversation_id": None,
            "messages": [],
        }
        conversations.append(conv)

    conv["messages"].append({
        "id": uuid.uuid4().hex[:10], "from": "customer", "text": text,
        "at": _now(), "mode": "live",
    })
    conv["last_message_at"] = _now()
    conv["unread"] = True
    save_conversations(conversations)
    return conv


# ---------------------------------------------------------------------------
# UI routes
# ---------------------------------------------------------------------------

@bp.route("/inbox")
def inbox_list():
    conversations = sorted(load_conversations(), key=lambda c: c.get("last_message_at", ""), reverse=True)
    selected_id = request.args.get("conv")
    selected = get_conversation(selected_id) if selected_id else (conversations[0] if conversations else None)

    if selected and selected.get("unread"):
        all_conv = load_conversations()
        for c in all_conv:
            if c["id"] == selected["id"]:
                c["unread"] = False
        save_conversations(all_conv)
        selected["unread"] = False

    messaging_status = {}
    for c in conversations:
        acc = config.get_account(c["platform"], c.get("account_id")) if c.get("account_id") else None
        messaging_status[c["id"]] = config.is_messaging_configured(c["platform"], acc)

    return render_template("inbox.html", conversations=conversations, selected=selected,
                            messaging_status=messaging_status,
                            platform_labels={"facebook": "Facebook", "shopee": "Shopee"})


@bp.route("/inbox/<conv_id>/reply", methods=["POST"])
def inbox_reply(conv_id):
    text = request.form.get("text", "").strip()
    conv = get_conversation(conv_id)
    if conv and text:
        connector = get_messaging_connector(conv["platform"], conv.get("account_id"))
        result = connector.send_message(conv, text)
        conversations = load_conversations()
        for c in conversations:
            if c["id"] == conv_id:
                c["messages"].append({
                    "id": uuid.uuid4().hex[:10], "from": "page", "text": text,
                    "at": _now(), "mode": result["mode"], "error": result.get("error"),
                })
                c["last_message_at"] = _now()
        save_conversations(conversations)
    return redirect(url_for("inbox.inbox_list", conv=conv_id))


@bp.route("/inbox/<conv_id>/read", methods=["POST"])
def inbox_mark_read(conv_id):
    conversations = load_conversations()
    for c in conversations:
        if c["id"] == conv_id:
            c["unread"] = False
    save_conversations(conversations)
    return jsonify({"status": "ok"})
