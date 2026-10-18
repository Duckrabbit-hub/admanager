"""connectors/shopee_ads.py — Shopee Open Platform Ads API
อ้างอิง: https://open.shopee.com/ (ขอ Partner ID/Key ผ่าน Shopee Partner Support)
หมายเหตุ: field name บางส่วนอาจต้อง verify กับเอกสารจริงที่ Shopee Partner ส่งให้ตอนอนุมัติ
"""
import hashlib
import hmac
import time

import requests

from .base import AdConnector

API_URL = "https://partner.shopeemobile.com/api/v2"


class ShopeeAdsConnector(AdConnector):
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

    def _create_campaign_live(self, campaign):
        path = "/ads/create_manual_product_ads"
        resp = requests.post(f"{API_URL}{path}", params=self._common_params(path), json={
            "campaign_name": campaign.get("name"),
            "daily_budget": campaign.get("daily_budget"),
            "campaign_status": "paused",  # เริ่มแบบ paused เสมอ
        }, timeout=20)
        resp.raise_for_status()
        body = resp.json()
        cid = body.get("response", {}).get("campaign_id")
        if not cid:
            raise RuntimeError(body.get("message", "Shopee API error"))
        return {"platform_campaign_id": cid, "mode": "live"}

    def _fetch_metrics_live(self, campaign):
        path = "/ads/get_campaign_performance"
        resp = requests.get(f"{API_URL}{path}", params={
            **self._common_params(path), "campaign_id": campaign["platform_campaign_id"],
        }, timeout=20)
        resp.raise_for_status()
        body = resp.json().get("response", {})
        return {
            "spend": float(body.get("expense", 0)), "impressions": int(body.get("impression", 0)),
            "clicks": int(body.get("clicks", 0)),
            # ชื่อฟิลด์ conversions ของ Shopee ไม่ชัดเจนในเอกสารสาธารณะ — best-effort จากฟิลด์ที่พบบ่อยที่สุด
            "conversions": int(body.get("order", body.get("broad_order", body.get("checkout_count", 0)))),
        }

    # Shopee ไม่ implement daily series live — fallback เป็น mock trend อัตโนมัติ (endpoint ไม่ชัดพอ)

    def _pause_campaign_live(self, campaign):
        path = "/ads/update_campaign_status"
        resp = requests.post(f"{API_URL}{path}", params=self._common_params(path), json={
            "campaign_id": campaign["platform_campaign_id"], "campaign_status": "paused",
        }, timeout=20)
        resp.raise_for_status()

    def _set_budget_live(self, campaign, new_budget):
        path = "/ads/update_campaign_budget"
        resp = requests.post(f"{API_URL}{path}", params=self._common_params(path), json={
            "campaign_id": campaign["platform_campaign_id"], "daily_budget": new_budget,
        }, timeout=20)
        resp.raise_for_status()
