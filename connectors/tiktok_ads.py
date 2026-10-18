"""connectors/tiktok_ads.py — TikTok Business (Marketing) API
อ้างอิง: https://business-api.tiktok.com/portal/docs
"""
import requests

from .base import AdConnector

API_URL = "https://business-api.tiktok.com/open_api/v1.3"


class TikTokAdsConnector(AdConnector):
    platform = "tiktok"

    def __init__(self, account=None):
        super().__init__(account)
        acc = self.account
        self.access_token = acc.get("access_token")
        self.advertiser_id = acc.get("advertiser_id")
        self.configured = bool(acc.get("app_id") and acc.get("app_secret")
                                and self.access_token and self.advertiser_id)

    def _headers(self):
        return {"Access-Token": self.access_token, "Content-Type": "application/json"}

    def _create_campaign_live(self, campaign):
        objective_map = {"traffic": "TRAFFIC", "conversions": "CONVERSIONS",
                          "awareness": "REACH", "engagement": "ENGAGEMENT"}
        resp = requests.post(f"{API_URL}/campaign/create/", headers=self._headers(), json={
            "advertiser_id": self.advertiser_id,
            "campaign_name": campaign.get("name"),
            "objective_type": objective_map.get(campaign.get("objective"), "TRAFFIC"),
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": campaign.get("daily_budget"),
            "operation_status": "DISABLE",  # เริ่มแบบปิดไว้ก่อนเสมอ
        }, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        cid = data.get("data", {}).get("campaign_id")
        if not cid:
            raise RuntimeError(data.get("message", "TikTok API error"))
        return {"platform_campaign_id": cid, "mode": "live"}

    def _fetch_metrics_live(self, campaign):
        pcid = campaign["platform_campaign_id"]
        resp = requests.get(f"{API_URL}/report/integrated/get/", headers=self._headers(), params={
            "advertiser_id": self.advertiser_id,
            "report_type": "BASIC",
            "dimensions": '["campaign_id"]',
            "metrics": '["spend","impressions","clicks","conversion"]',
            "filters": f'[{{"field_name":"campaign_id","filter_type":"IN","filter_value":"[\\"{pcid}\\"]"}}]',
        }, timeout=20)
        resp.raise_for_status()
        rows = resp.json().get("data", {}).get("list", [])
        if not rows:
            return {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
        m = rows[0].get("metrics", {})
        return {
            "spend": float(m.get("spend", 0)), "impressions": int(float(m.get("impressions", 0))),
            "clicks": int(float(m.get("clicks", 0))), "conversions": int(float(m.get("conversion", 0))),
        }

    def _fetch_daily_series_live(self, campaign, days):
        from datetime import datetime, timedelta
        pcid = campaign["platform_campaign_id"]
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        resp = requests.get(f"{API_URL}/report/integrated/get/", headers=self._headers(), params={
            "advertiser_id": self.advertiser_id,
            "report_type": "BASIC",
            "dimensions": '["campaign_id","stat_time_day"]',
            "metrics": '["spend","impressions","clicks","conversion"]',
            "start_date": start, "end_date": end,
            "filters": f'[{{"field_name":"campaign_id","filter_type":"IN","filter_value":"[\\"{pcid}\\"]"}}]',
        }, timeout=20)
        resp.raise_for_status()
        out = []
        for row in resp.json().get("data", {}).get("list", []):
            m = row.get("metrics", {})
            dims = row.get("dimensions", {})
            out.append({
                "date": (dims.get("stat_time_day") or "")[:10],
                "spend": float(m.get("spend", 0)), "impressions": int(float(m.get("impressions", 0))),
                "clicks": int(float(m.get("clicks", 0))), "conversions": int(float(m.get("conversion", 0))),
            })
        return out

    def _pause_campaign_live(self, campaign):
        resp = requests.post(f"{API_URL}/campaign/update/status/", headers=self._headers(), json={
            "advertiser_id": self.advertiser_id,
            "campaign_ids": [campaign["platform_campaign_id"]],
            "operation_status": "DISABLE",
        }, timeout=20)
        resp.raise_for_status()

    def _set_budget_live(self, campaign, new_budget):
        resp = requests.post(f"{API_URL}/campaign/update/", headers=self._headers(), json={
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign["platform_campaign_id"],
            "budget": new_budget,
        }, timeout=20)
        resp.raise_for_status()
