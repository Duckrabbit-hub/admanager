import io
import os
import secrets

from flask import (Flask, Response, redirect, render_template, request,
                    send_file, session, url_for)

import analytics
import automation
import config
import inbox as inbox_module
import storage
from connectors import get_connector

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
AUTH_ENABLED = bool(ADMIN_USERNAME and ADMIN_PASSWORD)

PLATFORM_LABELS = {"facebook": "Facebook", "tiktok": "TikTok", "shopee": "Shopee"}
OBJECTIVE_LABELS = {"traffic": "เพิ่มทราฟฟิก", "conversions": "เพิ่มยอดขาย/คอนเวอร์ชัน",
                     "awareness": "สร้างการรับรู้แบรนด์", "engagement": "เพิ่มการมีส่วนร่วม"}


@app.context_processor
def _inject_globals():
    # ให้ badge จำนวนข้อความยังไม่อ่าน และชื่อแพลตฟอร์ม ใช้ได้ใน template ทุกหน้าโดยไม่ต้องส่งทีละหน้า
    return {
        "inbox_unread_count": inbox_module.count_unread(),
        "platform_labels": PLATFORM_LABELS,
    }


@app.before_request
def _require_login():
    if not AUTH_ENABLED:
        return None
    if request.endpoint in ("login", "static", "inbox.webhook_facebook"):
        return None
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if (secrets.compare_digest(u, ADMIN_USERNAME or "")
                and secrets.compare_digest(p, ADMIN_PASSWORD or "")):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "username หรือ password ไม่ถูกต้อง"
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


def _enriched_campaigns():
    campaigns = storage.load_campaigns()
    out = []
    for c in campaigns:
        connector = get_connector(c["platform"], c.get("account_id"))
        metrics = connector.fetch_metrics(c)
        enriched = dict(c)
        enriched["metrics"] = metrics
        out.append(enriched)
    return out


@app.route("/")
def dashboard():
    campaigns = _enriched_campaigns()
    totals = {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0}
    for c in campaigns:
        for k in totals:
            totals[k] += c["metrics"].get(k, 0)
    inbox_unread_count = inbox_module.count_unread()
    return render_template("dashboard.html", campaigns=campaigns, totals=totals,
                            platform_labels=PLATFORM_LABELS, inbox_unread_count=inbox_unread_count)


@app.route("/campaign/new", methods=["GET", "POST"])
def new_campaign():
    accounts = config.accounts_by_platform()
    if request.method == "POST":
        platform = request.form.get("platform")
        account_id = request.form.get("account_id") or None
        account = config.get_account(platform, account_id) if account_id else None
        campaign = {
            "name": request.form.get("name", "").strip() or "แคมเปญไม่มีชื่อ",
            "platform": platform,
            "account_id": account_id,
            "account_label": account.get("label") if account else None,
            "objective": request.form.get("objective", "traffic"),
            "daily_budget": float(request.form.get("daily_budget") or 0),
            "original_daily_budget": float(request.form.get("daily_budget") or 0),
            "start_date": request.form.get("start_date") or "",
            "notes": request.form.get("notes", ""),
            "status": "active",
            "auto_paused": False,
            "automation_excluded": False,
        }
        connector = get_connector(platform, account_id)
        result = connector.create_campaign(campaign)
        campaign["platform_campaign_id"] = result["platform_campaign_id"]
        campaign["mode"] = result["mode"]
        storage.add_campaign(campaign)
        return redirect(url_for("dashboard"))

    account_configured = {
        p: {a["id"]: config.is_account_configured(p, a) for a in accs}
        for p, accs in accounts.items()
    }
    return render_template("campaign_form.html", platform_labels=PLATFORM_LABELS,
                            objective_labels=OBJECTIVE_LABELS, accounts_by_platform=accounts,
                            account_configured=account_configured)


@app.route("/campaign/<campaign_id>/toggle", methods=["POST"])
def toggle_campaign(campaign_id):
    c = storage.get_campaign(campaign_id)
    if c:
        new_status = "paused" if c["status"] == "active" else "active"
        fields = {"status": new_status}
        if new_status == "active":
            fields["auto_paused"] = False
        storage.update_campaign(campaign_id, **fields)
    return redirect(url_for("dashboard"))


@app.route("/campaign/<campaign_id>/delete", methods=["POST"])
def delete_campaign(campaign_id):
    storage.delete_campaign(campaign_id)
    return redirect(url_for("dashboard"))


@app.route("/analytics")
def analytics_page():
    campaigns = _enriched_campaigns()
    report = analytics.build_report(campaigns)
    return render_template("analytics.html", report=report, platform_labels=PLATFORM_LABELS)


@app.route("/automation", methods=["GET", "POST"])
def automation_page():
    if request.method == "POST":
        cfg = {
            "enabled": request.form.get("enabled") == "on",
            "check_interval_minutes": int(request.form.get("check_interval_minutes") or 15),
            "pause_threshold_cpa": float(request.form.get("pause_threshold_cpa") or 0) or None,
            "min_ctr_percent": float(request.form.get("min_ctr_percent") or 0) or None,
            "boost_percent": float(request.form.get("boost_percent") or 20),
            "boost_budget_cap_multiplier": float(request.form.get("boost_budget_cap_multiplier") or 3),
            "min_days_before_action": int(request.form.get("min_days_before_action") or 3),
        }
        automation.save_config(cfg)
        return redirect(url_for("automation_page"))
    cfg = automation.load_config()
    log = automation.load_log()[-50:][::-1]
    campaigns = storage.load_campaigns()
    return render_template("automation.html", cfg=cfg, log=log, campaigns=campaigns,
                            platform_labels=PLATFORM_LABELS,
                            min_peers=automation.MIN_PEERS_FOR_SCORE)


@app.route("/automation/exclude/<campaign_id>", methods=["POST"])
def toggle_exclude(campaign_id):
    c = storage.get_campaign(campaign_id)
    if c:
        storage.update_campaign(campaign_id, automation_excluded=not c.get("automation_excluded", False))
    return redirect(url_for("automation_page"))


@app.route("/export.xlsx")
def export_xlsx():
    import openpyxl
    campaigns = _enriched_campaigns()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "แคมเปญ"
    ws.append(["ชื่อแคมเปญ", "แพลตฟอร์ม", "บัญชี", "งบ/วัน", "สถานะ", "ยอดใช้จ่าย",
               "Impressions", "Clicks", "Conversions", "โหมดข้อมูล"])
    for c in campaigns:
        m = c["metrics"]
        ws.append([c["name"], PLATFORM_LABELS.get(c["platform"], c["platform"]),
                   c.get("account_label") or "-", c["daily_budget"], c["status"],
                   m.get("spend", 0), m.get("impressions", 0), m.get("clicks", 0),
                   m.get("conversions", 0), m.get("source", "mock")])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="adshooter_report.xlsx",
                      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        platform = request.form.get("platform")
        account_id = request.form.get("account_id") or None
        label = request.form.get("label", "").strip()
        fields = {f: request.form.get(f, "").strip()
                  for f in config.ALL_FIELDS.get(platform, []) if request.form.get(f, "").strip()}
        existing = config.get_account(platform, account_id) if account_id else None
        if account_id and existing:
            config.update_account(platform, account_id, label, fields)
        else:
            config.add_account(platform, label, fields)
        return redirect(url_for("settings"))

    accounts = config.accounts_by_platform()
    account_configured = {
        p: {a["id"]: config.is_account_configured(p, a) for a in accs}
        for p, accs in accounts.items()
    }
    messaging_configured = {
        p: {a["id"]: config.is_messaging_configured(p, a) for a in accs}
        for p, accs in accounts.items() if p in config.MESSAGING_FIELDS
    }
    return render_template("settings.html", accounts_by_platform=accounts,
                            account_configured=account_configured,
                            messaging_configured=messaging_configured,
                            platform_labels=PLATFORM_LABELS,
                            all_fields=config.ALL_FIELDS,
                            messaging_fields=config.MESSAGING_FIELDS)


@app.route("/settings/<platform>/<account_id>/delete", methods=["POST"])
def delete_account_route(platform, account_id):
    config.delete_account(platform, account_id)
    return redirect(url_for("settings"))


# --- กล่องข้อความรวม (Inbox) ---
app.register_blueprint(inbox_module.bp)


automation.start_background_thread()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
