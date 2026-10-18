"""messaging/shopee_chat.py — Shopee Open Platform Chat API (best-effort)
อ้างอิง: https://open.shopee.com/ โมดูล Chat — ต้องขอสิทธิ์เพิ่มเติมจาก Shopee Partner Support
แยกจาก shopee_ads.py เพราะอาจเป็นคนละ permission scope ในระบบของ Shopee
"""
import hashlib
import hmac
import time

import requests

from .base import MessagingConnector

API_URL = "https://partner.shopeemobile.com/api/v2"


class ShopeeChatConnector(MessagingConnector):
    platform = "shopee"

    def __init__(self, account=None):
        super().__init__(account)
        acc = self.account
        self.partner_id = acc.get("partner_id")
        self.partner_key = acc.get("partner_key")
        self.shop_id = acc.get("shop_id")
        self.access_token = acc.get("access_token")
        self.configured = bool(self.partner_id and self.partner_key
                                and self.shop_id and self.access_token)

    def _sign(self, path, timestamp):
        base = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        return hmac.new(self.partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

    def _common_params(self, path):
        ts = int(time.time())
        return {
            "partner_id": self.partner_id, "timestamp": ts, "access_token": self.access_token,
            "shop_id": self.shop_id, "sign": self._sign(path, ts),
        }

    def _send_live(self, conversation, text):
        path = "/sellerchat/send_message"
        resp = requests.post(f"{API_URL}{path}", params=self._common_params(path), json={
            "conversation_id": conversation.get("platform_conversation_id"),
            "to_id": conversation["customer_id"],
            "message_type": "text",
            "content": {"text": text},
        }, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(body.get("message", "Shopee Chat API error"))
