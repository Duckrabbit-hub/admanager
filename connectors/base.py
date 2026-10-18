"""connectors/base.py — คลาสฐานสำหรับ connector ยิงแอดแต่ละแพลตฟอร์ม

รูปแบบ live-with-fallback-to-mock: ทุกเมธอดสาธารณะ (create_campaign, fetch_metrics,
fetch_daily_series) จะลองเรียก API จริงก่อนถ้า connector ถูกตั้งค่าไว้ (configured=True)
และแคมเปญนั้นเป็นแคมเปญจริง (ไม่ใช่ MOCK-) — ถ้า error ใด ๆ เกิดขึ้นจะ fallback กลับไปใช้
ข้อมูลจำลองแทนเสมอ (ไม่ทำให้หน้าเว็บพัง) พร้อมแท็ก source ให้ UI โชว์สถานะได้
"""
import random
from datetime import datetime, timedelta


class AdConnector:
    platform = "base"

    def __init__(self, account=None):
        self.account = account or {}
        self.configured = False  # subclass เซ็ตจริงหลัง __init__

    # ---- ต้อง override ในแต่ละแพลตฟอร์ม ----
    def _create_campaign_live(self, campaign):
        raise NotImplementedError

    def _fetch_metrics_live(self, campaign):
        raise NotImplementedError

    def _fetch_daily_series_live(self, campaign, days):
        raise NotImplementedError

    def _pause_campaign_live(self, campaign):
        raise NotImplementedError

    def _set_budget_live(self, campaign, new_budget):
        raise NotImplementedError

    # ---- helper ----
    @staticmethod
    def _is_live_campaign(connector, campaign):
        pcid = campaign.get("platform_campaign_id") or ""
        return connector.configured and not pcid.startswith("MOCK-")

    @staticmethod
    def _days_running(campaign):
        try:
            start = datetime.strptime(campaign.get("start_date", ""), "%Y-%m-%d")
        except ValueError:
            return 0
        return max(0, (datetime.now() - start).days)

    # ---- mock generators ----
    def generate_mock_metrics(self, campaign):
        days = max(1, self._days_running(campaign) or 1)
        budget = campaign.get("daily_budget", 200)
        spend = round(budget * days * random.uniform(0.7, 1.05), 2)
        impressions = int(spend * random.uniform(40, 90))
        clicks = max(1, int(impressions * random.uniform(0.01, 0.035)))
        conversions = int(clicks * random.uniform(0.02, 0.09))
        return {
            "spend": spend, "impressions": impressions, "clicks": clicks,
            "conversions": conversions, "source": "mock",
        }

    def generate_mock_daily_series(self, campaign, days=14):
        budget = campaign.get("daily_budget", 200)
        series = []
        today = datetime.now()
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            spend = round(budget * random.uniform(0.6, 1.1), 2)
            impressions = int(spend * random.uniform(40, 90))
            clicks = max(0, int(impressions * random.uniform(0.01, 0.035)))
            conversions = int(clicks * random.uniform(0.02, 0.09))
            series.append({
                "date": day.strftime("%Y-%m-%d"), "spend": spend,
                "impressions": impressions, "clicks": clicks, "conversions": conversions,
            })
        return series

    # ---- public API: live-with-fallback ----
    def create_campaign(self, campaign):
        if self.configured:
            try:
                return self._create_campaign_live(campaign)
            except Exception as e:
                campaign["_live_error"] = str(e)
        pcid = f"MOCK-{self.platform.upper()}-{random.randint(100000, 999999)}"
        return {"platform_campaign_id": pcid, "mode": "mock"}

    def fetch_metrics(self, campaign):
        if self._is_live_campaign(self, campaign):
            try:
                metrics = self._fetch_metrics_live(campaign)
                metrics["source"] = "live"
                return metrics
            except Exception as e:
                metrics = self.generate_mock_metrics(campaign)
                metrics["source"] = "live_failed_fallback_mock"
                metrics["source_error"] = str(e)
                return metrics
        return self.generate_mock_metrics(campaign)

    def fetch_daily_series(self, campaign, days=14):
        if self._is_live_campaign(self, campaign):
            try:
                return self._fetch_daily_series_live(campaign, days)
            except NotImplementedError:
                return self.generate_mock_daily_series(campaign, days)
            except Exception:
                return self.generate_mock_daily_series(campaign, days)
        return self.generate_mock_daily_series(campaign, days)

    def pause_campaign(self, campaign):
        """คืน True ถ้าสั่งหยุดที่ตัวแพลตฟอร์มจริงสำเร็จ, False ถ้าเป็น mock/ล้มเหลว (ยังอัปเดต local ได้ตามปกติ)"""
        if self._is_live_campaign(self, campaign):
            try:
                self._pause_campaign_live(campaign)
                return True
            except Exception:
                return False
        return False

    def set_budget(self, campaign, new_budget):
        if self._is_live_campaign(self, campaign):
            try:
                self._set_budget_live(campaign, new_budget)
                return True
            except Exception:
                return False
        return False
