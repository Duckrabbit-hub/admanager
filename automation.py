"""automation.py — ระบบยิงแอด/หยุดแอดอัตโนมัติ (Auto-Pilot)

ปิดใช้งานเป็นค่าเริ่มต้นเสมอ ต้องเข้าไปเปิดสวิตช์เองในหน้า "ระบบอัตโนมัติ"
เมื่อเปิดใช้งาน จะเช็คแคมเปญที่ active เป็นระยะ แล้ว:
  1. หยุดแคมเปญที่ไม่มีประสิทธิภาพ (เรียก API จริงไปหยุดที่ตัวแพลตฟอร์มด้วย ถ้า connector ตั้งค่าไว้)
  2. เพิ่มงบ/วันให้แคมเปญที่ทำผลงานดี (เรียก API จริงไปปรับงบด้วยเช่นกัน)

ความปลอดภัย: ไม่ลบแคมเปญ, ไม่เปิดแคมเปญที่ถูกหยุดกลับมาเองอัตโนมัติ, แคมเปญใหม่ (อายุน้อยกว่า
min_days_before_action) ไม่ถูกแตะ, ต้องมี active peer อย่างน้อย MIN_PEERS_FOR_SCORE ตัวถึงใช้คะแนน
เปรียบเทียบ (percentile) ตัดสินได้, เพดานงบ boost อิงจากงบตั้งต้น (original_daily_budget) ไม่ใช่งบปัจจุบัน,
เว้นระยะกันเพิ่มงบถี่เกินไป, ยกเว้นแคมเปญที่ตั้ง automation_excluded ได้เป็นรายตัว
"""
import json
import os
import threading
import time
from datetime import datetime

import analytics
import config
import db
import storage
from connectors import get_connector

AUTOMATION_FILE = os.path.join(config.DATA_DIR, "automation.json")
LOG_FILE = os.path.join(config.DATA_DIR, "automation_log.json")
_CONFIG_DB_KEY = "automation_config"
_LOG_DB_KEY = "automation_log"

MIN_PEERS_FOR_SCORE = 3
BOOST_COOLDOWN_HOURS = 12

_thread_lock = threading.Lock()
_thread_started = False

DEFAULT_CONFIG = {
    "enabled": False,
    "check_interval_minutes": 15,
    "pause_threshold_cpa": None,
    "min_ctr_percent": None,
    "boost_percent": 20,
    "boost_budget_cap_multiplier": 3,
    "min_days_before_action": 3,
}


def _ensure_data_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def load_config():
    if db.available():
        cfg = db.get(_CONFIG_DB_KEY, {})
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    _ensure_data_dir()
    if not os.path.exists(AUTOMATION_FILE):
        return dict(DEFAULT_CONFIG)
    try:
        with open(AUTOMATION_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    if db.available():
        db.set(_CONFIG_DB_KEY, cfg)
        return
    _ensure_data_dir()
    with open(AUTOMATION_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_log():
    if db.available():
        return db.get(_LOG_DB_KEY, [])
    _ensure_data_dir()
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _append_log(entry):
    log = load_log()
    entry["at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    log.append(entry)
    log = log[-500:]
    if db.available():
        db.set(_LOG_DB_KEY, log)
        return
    _ensure_data_dir()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def _enriched_active_campaigns():
    out = []
    for c in storage.load_campaigns():
        if c["status"] != "active":
            continue
        connector = get_connector(c["platform"], c.get("account_id"))
        metrics = connector.fetch_metrics(c)
        enriched = dict(c)
        enriched["metrics"] = metrics
        out.append(enriched)
    return out


def evaluate_and_apply():
    cfg = load_config()
    campaigns = _enriched_active_campaigns()
    scored = analytics.score_campaigns(campaigns) if len(campaigns) >= MIN_PEERS_FOR_SCORE else {}

    for c in campaigns:
        if c.get("automation_excluded"):
            continue
        days_running = _days_running(c)
        if days_running < cfg["min_days_before_action"]:
            continue

        m = c["metrics"]
        cpa = (m["spend"] / m["conversions"]) if m.get("conversions") else None
        ctr = (m["clicks"] / m["impressions"] * 100) if m.get("impressions") else 0
        score = scored.get(c["id"])

        should_pause = False
        reason = None
        if cfg.get("pause_threshold_cpa") and cpa and cpa > cfg["pause_threshold_cpa"]:
            should_pause, reason = True, f"CPA ({cpa:.2f}) เกินเกณฑ์ที่ตั้งไว้ ({cfg['pause_threshold_cpa']})"
        elif cfg.get("min_ctr_percent") and ctr < cfg["min_ctr_percent"]:
            should_pause, reason = True, f"CTR ({ctr:.2f}%) ต่ำกว่าเกณฑ์ที่ตั้งไว้ ({cfg['min_ctr_percent']}%)"
        elif score is not None and score <= 20:
            should_pause, reason = True, f"คะแนนรวมต่ำ ({score:.0f}/100) เทียบกับแคมเปญอื่นที่กำลังรันอยู่"

        if should_pause:
            connector = get_connector(c["platform"], c.get("account_id"))
            live_ok = connector.pause_campaign(c)
            storage.update_campaign(c["id"], status="paused", auto_paused=True)
            _append_log({"campaign_id": c["id"], "campaign_name": c["name"], "action": "pause",
                         "reason": reason, "live_applied": live_ok})
            continue

        should_boost = score is not None and score >= 80
        if should_boost:
            last_boost = c.get("last_boost_at")
            if last_boost:
                try:
                    hrs = (datetime.now() - datetime.strptime(last_boost, "%Y-%m-%d %H:%M")).total_seconds() / 3600
                    if hrs < BOOST_COOLDOWN_HOURS:
                        continue
                except ValueError:
                    pass
            cap = c.get("original_daily_budget", c["daily_budget"]) * cfg["boost_budget_cap_multiplier"]
            new_budget = round(min(cap, c["daily_budget"] * (1 + cfg["boost_percent"] / 100)), 2)
            if new_budget > c["daily_budget"]:
                connector = get_connector(c["platform"], c.get("account_id"))
                live_ok = connector.set_budget(c, new_budget)
                storage.update_campaign(c["id"], daily_budget=new_budget,
                                         last_boost_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
                _append_log({"campaign_id": c["id"], "campaign_name": c["name"], "action": "boost",
                             "reason": f"คะแนนรวมสูง ({score:.0f}/100) เพิ่มงบจาก {c['daily_budget']} เป็น {new_budget}",
                             "live_applied": live_ok})


def _days_running(campaign):
    try:
        start = datetime.strptime(campaign.get("start_date", ""), "%Y-%m-%d")
    except ValueError:
        return 999
    return max(0, (datetime.now() - start).days)


def _background_loop():
    last_run = 0.0
    while True:
        try:
            cfg = load_config()
            interval_sec = max(60, int(cfg.get("check_interval_minutes", 15)) * 60)
            if cfg.get("enabled") and (time.time() - last_run) >= interval_sec:
                evaluate_and_apply()
                last_run = time.time()
        except Exception:
            pass  # ไม่ให้ thread พังทั้งกระบวนการ — ข้ามรอบนี้แล้วลองใหม่รอบหน้า
        time.sleep(60)


def start_background_thread():
    global _thread_started
    with _thread_lock:
        if _thread_started:
            return
        _thread_started = True
        threading.Thread(target=_background_loop, daemon=True).start()
