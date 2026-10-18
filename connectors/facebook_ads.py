"""connectors/facebook_ads.py — Facebook (Meta) Marketing API
อ้างอิง: https://developers.facebook.com/docs/marketing-apis
ต้องมีสิทธิ์ ads_management ผ่าน App Review ก่อนใช้กับบัญชีจริง (ดู docs_api_setup_guide.md)
"""
import requests

from .base import AdConnector

GRAPH_URL = "https://graph.facebook.com/v21.0"
CONVERSION_ACTION_TYPES = {"offsite_conversion", "purchase", "lead", "complete_registration"}


def _sum_conversions(actions):
    if not actions:
        return 0
    total = 0
    for a in actions:
        if a.get("action_type") in CONVERSION_ACTION_TYPES:
            try:
                total += int(float(a.get("value", 0)))
            except (TypeError, ValueError):
                pass
    return total


class FacebookAdsConnector(AdConnector):
    platform = "facebook"

    def __init__(self, account=None):
        super().__init__(account)
        acc = self.account
        self.access_token = acc.get("access_token")
        self.ad_account_id = acc.get("ad_account_id")
        self.configured = bool(acc.get("app_id") and acc.get("app_secret")
                                and self.access_token and self.ad_account_id)

    def _act_id(self):
        aid = self.ad_account_id or ""
        return aid if aid.startswith("act_") else f"act_{aid}"

    def _create_campaign_live(self, campaign):
        url = f"{GRAPH_URL}/{self._act_id()}/campaigns"
        objective_map = {"traffic": "OUTCOME_TRAFFIC", "conversions": "OUTCOME_SALES",
                          "awareness": "OUTCOME_AWARENESS", "engagement": "OUTCOME_ENGAGEMENT"}
        resp = requests.post(url, data={
            "name": campaign.get("name"),
            "objective": objective_map.get(campaign.get("objective"), "OUTCOME_TRAFFIC"),
            "status": "PAUSED",  # เริ่มแบบ paused เสมอ ให้ผู้ใช้ตรวจสอบก่อนเปิดจริง
            "special_ad_categories": "[]",
            "access_token": self.access_token,
        }, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return {"platform_campaign_id": data["id"], "mode": "live"}

    def _fetch_metrics_live(self, campaign):
        pcid = campaign["platform_campaign_id"]
        resp = requests.get(f"{GRAPH_URL}/{pcid}/insights", params={
            "fields": "spend,impressions,clicks,actions",
            "access_token": self.access_token,
        }, timeout=20)
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        if not rows:
            return {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
        row = rows[0]
        return {
            "spend": float(row.get("spend", 0)),
            "impressions": int(row.get("impressions", 0)),
            "clicks": int(row.get("clicks", 0)),
            "conversions": _sum_conversions(row.get("actions")),
        }

    def _fetch_daily_series_live(self, campaign, days):
        pcid = campaign["platform_campaign_id"]
        resp = requests.get(f"{GRAPH_URL}/{pcid}/insights", params={
            "fields": "spend,impressions,clicks,actions,date_start",
            "time_increment": 1,
            "date_preset": None,
            "time_range": '{"since":"' + _n_days_ago(days) + '","until":"today"}',
            "access_token": self.access_token,
        }, timeout=20)
        resp.raise_for_status()
        out = []
        for row in resp.json().get("data", []):
            out.append({
                "date": row.get("date_start"),
                "spend": float(row.get("spend", 0)),
                "impressions": int(row.get("impressions", 0)),
                "clicks": int(row.get("clicks", 0)),
                "conversions": _sum_conversions(row.get("actions")),
            })
        return out

    def _pause_campaign_live(self, campaign):
        pcid = campaign["platform_campaign_id"]
        resp = requests.post(f"{GRAPH_URL}/{pcid}", data={
            "status": "PAUSED", "access_token": self.access_token,
        }, timeout=20)
        resp.raise_for_status()

    def _set_budget_live(self, campaign, new_budget):
        pcid = campaign["platform_campaign_id"]
        resp = requests.post(f"{GRAPH_URL}/{pcid}", data={
            "daily_budget": int(new_budget * 100),  # Meta ใช้หน่วยสตางค์/เซนต์
            "access_token": self.access_token,
        }, timeout=20)
        resp.raise_for_status()


def _n_days_ago(days):
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
