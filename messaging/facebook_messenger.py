"""messaging/facebook_messenger.py — Facebook Messenger Platform (Send API + Webhooks)
อ้างอิง: https://developers.facebook.com/docs/messenger-platform
ต้องมีสิทธิ์ pages_messaging ผ่าน App Review (คนละสิทธิ์กับ ads_management ที่ใช้ยิงแอด)
"""
import hashlib
import hmac

import requests

from .base import MessagingConnector

GRAPH_URL = "https://graph.facebook.com/v21.0"


class FacebookMessengerConnector(MessagingConnector):
    platform = "facebook"

    def __init__(self, account=None):
        super().__init__(account)
        acc = self.account
        self.page_id = acc.get("page_id")
        self.page_access_token = acc.get("page_access_token")
        self.app_secret = acc.get("app_secret")
        self.configured = bool(self.page_id and self.page_access_token)

    def _send_live(self, conversation, text):
        resp = requests.post(f"{GRAPH_URL}/me/messages", params={
            "access_token": self.page_access_token,
        }, json={
            "recipient": {"id": conversation["customer_id"]},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(body["error"].get("message", "Facebook Send API error"))


def verify_signature(app_secret, payload_bytes, signature_header):
    """ตรวจสอบ X-Hub-Signature-256 ที่ Facebook ส่งมากับ webhook POST ทุกครั้ง
    กัน request ปลอมที่ไม่ได้มาจาก Facebook จริง"""
    if not app_secret or not signature_header:
        return False
    try:
        algo, sig = signature_header.split("=", 1)
    except ValueError:
        return False
    if algo != "sha256":
        return False
    expected = hmac.new(app_secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
