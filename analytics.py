"""analytics.py — คำนวณ CTR/CPC/CPA/Conversion Rate, จัดอันดับ, กราฟแนวโน้ม SVG

จัดอันดับแบบ percentile-based relative scoring (เทียบกับแคมเปญอื่นที่กำลังรันอยู่ด้วยกัน
ไม่ใช่ threshold ตายตัว) เพราะ "ดี/แย่" ขึ้นกับบริบทธุรกิจ เทียบกันเองแม่นกว่า
"""
from connectors import get_connector

CHART_WIDTH = 560
CHART_HEIGHT = 160
CHART_PAD = 28


def derived_metrics(m):
    spend = m.get("spend", 0)
    impressions = m.get("impressions", 0)
    clicks = m.get("clicks", 0)
    conversions = m.get("conversions", 0)
    return {
        "ctr": (clicks / impressions * 100) if impressions else 0,
        "cpc": (spend / clicks) if clicks else 0,
        "cpa": (spend / conversions) if conversions else 0,
        "conversion_rate": (conversions / clicks * 100) if clicks else 0,
    }


def _percentile_rank(values, value, lower_is_better=False):
    if len(values) <= 1:
        return 50.0
    sorted_vals = sorted(values)
    rank = sum(1 for v in sorted_vals if v < value)
    pct = rank / (len(sorted_vals) - 1) * 100 if len(sorted_vals) > 1 else 50
    return 100 - pct if lower_is_better else pct


def score_campaigns(campaigns):
    """คืน {campaign_id: คะแนนรวม 0-100} คำนวณจาก CTR (สูงดี) + CPA (ต่ำดี) + conversions (สูงดี)
    เทียบ percentile กับกลุ่มแคมเปญที่ส่งเข้ามาด้วยกันเท่านั้น"""
    if not campaigns:
        return {}
    derived = {c["id"]: derived_metrics(c["metrics"]) for c in campaigns}
    ctrs = [d["ctr"] for d in derived.values()]
    cpas = [d["cpa"] for d in derived.values() if d["cpa"] > 0]
    convs = [c["metrics"].get("conversions", 0) for c in campaigns]

    scores = {}
    for c in campaigns:
        d = derived[c["id"]]
        ctr_score = _percentile_rank(ctrs, d["ctr"])
        cpa_score = _percentile_rank(cpas, d["cpa"], lower_is_better=True) if d["cpa"] > 0 and cpas else 50
        conv_score = _percentile_rank(convs, c["metrics"].get("conversions", 0))
        scores[c["id"]] = round(ctr_score * 0.35 + cpa_score * 0.4 + conv_score * 0.25, 1)
    return scores


def _svg_line_chart(series, key, color, label):
    if not series:
        return ""
    values = [row.get(key, 0) for row in series]
    vmax = max(values) or 1
    vmin = min(values)
    span = (vmax - vmin) or 1
    n = len(series)
    points = []
    for i, v in enumerate(values):
        x = CHART_PAD + (i / max(1, n - 1)) * (CHART_WIDTH - CHART_PAD * 2)
        y = CHART_HEIGHT - CHART_PAD - ((v - vmin) / span) * (CHART_HEIGHT - CHART_PAD * 2)
        points.append((x, y))

    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))

    labels = []
    for i, (x, y) in enumerate(points):
        if i != 0 and i != n - 1 and i != n // 2:
            continue
        # กัน label วันแรก/สุดท้ายโดนตัดขอบ viewBox — ปรับ text-anchor ตามตำแหน่ง
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        labels.append(f'<text x="{x:.1f}" y="{CHART_HEIGHT - 6}" font-size="9" fill="#8a94a6" '
                      f'text-anchor="{anchor}">{series[i]["date"][5:]}</text>')

    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}"/>' for x, y in points[-1:])

    return (f'<svg viewBox="0 0 {CHART_WIDTH} {CHART_HEIGHT}" class="trend-chart" role="img" '
            f'aria-label="กราฟแนวโน้ม {label}">'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
            f'{dots}{"".join(labels)}</svg>')


def build_report(campaigns):
    scores = score_campaigns(campaigns)
    per_campaign = []
    platform_totals = {}

    for c in campaigns:
        d = derived_metrics(c["metrics"])
        series = get_connector(c["platform"], c.get("account_id")).fetch_daily_series(c, days=14)
        per_campaign.append({
            "id": c["id"], "name": c["name"], "platform": c["platform"],
            "account_label": c.get("account_label"), "metrics": c["metrics"], "derived": d,
            "score": scores.get(c["id"]),
            "chart_svg": _svg_line_chart(series, "spend", "#2a78d6", "ยอดใช้จ่าย"),
        })
        pt = platform_totals.setdefault(c["platform"], {"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0})
        for k in pt:
            pt[k] += c["metrics"].get(k, 0)

    per_campaign.sort(key=lambda x: x["score"] or 0, reverse=True)
    top_performers = [p for p in per_campaign if p["score"] is not None][:5]

    return {
        "per_campaign": per_campaign,
        "platform_totals": platform_totals,
        "top_performers": top_performers,
        "has_enough_for_scoring": len(campaigns) >= 3,
    }
