"""
cursor_weekly_ingest.py
- Pull weekly Cursor analytics (usage + optional AI code lines)
- Aggregate to weekly totals
- Ingest into InfluxDB as one point per week

How to run (cron weekly, Mondays 07:00 Prague):
0 7 * * MON /usr/bin/python3 /path/to/cursor_weekly_ingest.py >> /var/log/cursor_weekly_ingest.log 2>&1
"""

import csv
import io
import os
import time
import json
import math
import requests
from datetime import datetime, timedelta, timezone

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from config import influxConfig, cursorConfig
from secret import influxToken, cursorKey
from config import generalConfig as c


# ---------- Time helpers ----------
def last_completed_iso_week():
    """
    Returns (week_start_utc, week_end_utc) for the last completed ISO week in UTC.
    ISO week runs Monday 00:00:00 to next Monday 00:00:00 (exclusive).
    """
    now = datetime.now(timezone.utc)
    # Start of current ISO week (Monday) in UTC
    start_of_this_week = (now - timedelta(days=now.isoweekday() - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Last completed week is the one ending at start_of_this_week
    start_of_last_week = start_of_this_week - timedelta(days=7)
    end_of_last_week = start_of_this_week  # exclusive
    return start_of_last_week, end_of_last_week

def to_epoch_millis(dt_utc: datetime) -> int:
    """Return Unix epoch milliseconds for a UTC datetime."""
    return int(dt_utc.replace(tzinfo=timezone.utc).timestamp() * 1000)

# ---------- API calls ----------
def _post_daily_usage(start_utc: datetime, end_utc: datetime):
    """
    Calls your configured daily-usage endpoint (Cursor Admin API style).
    Expects JSON with per-day aggregates we can sum.
    """
    url = "https://api.cursor.com/teams/daily-usage-data"
    headers = {
        "Authorization": f"Bearer {cursorKey}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "startDate": to_epoch_millis(start_utc),
        "endDate": to_epoch_millis(end_utc),
        "teamId": cursorConfig.get("team_id")
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    return r.json()


def _get_ai_code_changes_csv(start_utc: datetime, end_utc: datetime):
    """
    Optional: pulls AI code changes CSV (if configured).
    Expected CSV columns should contain suggested/accepted line counts.
    If endpoint not set, returns None.
    """
    url = "https://api.cursor.com/analytics/ai-code/changes.csv"
    if not url:
        return None

    headers = {
        "Authorization": f"Bearer {cursorKey}",
        "Accept": "text/csv",
    }
    params = {
        "startDate": to_epoch_millis(start_utc),
        "endDate": to_epoch_millis(end_utc),
        # Add teamId if your endpoint requires it
        "teamId": cursorConfig.get("team_id", "")
    }
    r = requests.get(url, headers=headers, params=params, timeout=120)
    if r.status_code == 401:
        # Not authorized for AI Code Tracking; continue without CSV
        print("[WARN] AI code CSV unauthorized (401). Skipping line-level backfill; continuing with daily usage only.")
        return None
    r.raise_for_status()
    return r.text


# ---------- Aggregation ----------
def _sum_daily_usage_to_week(daily_json: dict) -> dict:
    """
    Sums daily aggregates to weekly totals.
    Flexible key mapping with safe .get(...) defaults.
    """
    totals = {
        "chat_tabs_shown": 0,
        "chat_total_accepts": 0,
        "chat_total_applies": 0,
        "tabs_accepted": 0,
        "agent_requests": 0,
        # If your daily endpoint includes line-level aggregates, map them here:
        "chat_suggested_lines": 0,
        "chat_accepted_lines": 0,
    }

    # Accept a couple of likely shapes:
    # 1) {"days": [{"date":"...", "totals": {...}} , ...]}
    # 2) {"data": [{"date":"...", ...}], ...}
    rows = []
    if isinstance(daily_json, dict):
        if "days" in daily_json:
            rows = daily_json["days"]
        elif "data" in daily_json:
            rows = daily_json["data"]
        elif isinstance(daily_json.get("results"), list):
            rows = daily_json["results"]
        else:
            # Maybe it's already a list
            if isinstance(daily_json, list):
                rows = daily_json

    for row in rows:
        rec = row.get("totals", row)
        totals["chat_tabs_shown"]    += int(rec.get("totalTabsShown", rec.get("chatTabsShown", 0)) or 0)
        totals["chat_total_accepts"] += int(rec.get("totalAccepts", rec.get("chatTotalAccepts", 0)) or 0)
        totals["chat_total_applies"] += int(rec.get("totalApplies", rec.get("chatTotalApplies", 0)) or 0)
        totals["tabs_accepted"]      += int(rec.get("totalTabsAccepted", rec.get("tabsAccepted", 0)) or 0)
        totals["agent_requests"]     += int(rec.get("agentRequests", rec.get("totalAgentRequests", 0)) or 0)

        # Optional line metrics if present in daily JSON (else keep 0; CSV path can fill these):
        totals["chat_suggested_lines"] += int(rec.get("chatSuggestedLines", rec.get("suggestedLines", 0)) or 0)
        totals["chat_accepted_lines"]  += int(rec.get("chatAcceptedLines",  rec.get("acceptedLines", 0)) or 0)

    return totals


def _sum_ai_code_changes_csv(csv_text: str) -> dict:
    """
    Sums suggested/accepted lines from an AI-code CSV export.
    Tries a few common header names; adjust mapping if needed.
    """
    if not csv_text:
        return {"chat_suggested_lines": 0, "chat_accepted_lines": 0}

    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    sug_total = 0
    acc_total = 0

    # Common column name variants (tweak to match your endpoint’s schema)
    sug_cols = ["suggestedLines", "aiSuggestedAddedLines", "suggested_added_lines", "suggested_total_lines"]
    acc_cols = ["acceptedLines", "aiAcceptedAddedLines", "accepted_added_lines", "accepted_total_lines"]

    for row in reader:
        s = 0
        a = 0
        for col in sug_cols:
            if col in row and row[col]:
                try:
                    s = int(float(row[col]))
                    break
                except ValueError:
                    pass
        for col in acc_cols:
            if col in row and row[col]:
                try:
                    a = int(float(row[col]))
                    break
                except ValueError:
                    pass
        sug_total += s
        acc_total += a

    return {"chat_suggested_lines": sug_total, "chat_accepted_lines": acc_total}


def _compute_ratios(week: dict) -> dict:
    def safe_div(n, d):
        return float(n) / float(d) if d and float(d) != 0.0 else 0.0

    return {
        "visibility_to_accept_rate": safe_div(week["chat_total_accepts"], week["chat_tabs_shown"]),  # Accepts / Shown
        "accept_to_apply_rate": safe_div(week["chat_total_applies"], week["chat_total_accepts"]),    # Applies / Accepts
        "line_conversion_rate": safe_div(week["chat_accepted_lines"], week["chat_suggested_lines"]), # Accepted Lines / Suggested Lines
    }


# ---------- Influx write ----------
def _write_week_to_influx(week_start_utc: datetime, data: dict):
    client = InfluxDBClient(url=influxConfig["url"], token=influxToken, org=influxConfig["org"])
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Tags
    team_id = cursorConfig.get("team_id", "unknown")
    point = (
        Point("CursorAnalyticsWeekly")
        .tag("team", team_id)
        .field("chat_tabs_shown", int(data["chat_tabs_shown"]))
        .field("chat_total_accepts", int(data["chat_total_accepts"]))
        .field("chat_total_applies", int(data["chat_total_applies"]))
        .field("tabs_accepted", int(data["tabs_accepted"]))
        .field("agent_requests", int(data["agent_requests"]))
        .field("chat_suggested_lines", int(data["chat_suggested_lines"]))
        .field("chat_accepted_lines", int(data["chat_accepted_lines"]))
        .field("visibility_to_accept_rate", float(data["visibility_to_accept_rate"]))
        .field("accept_to_apply_rate", float(data["accept_to_apply_rate"]))
        .field("line_conversion_rate", float(data["line_conversion_rate"]))
        .time(week_start_utc)  # one point per week at week start
    )

    if c.get("debug"):
        print("Writing Influx point:", point.to_line_protocol())

    write_api.write(bucket=influxConfig["bucket"], record=point)
    client.close()


# ---------- Orchestration ----------
def run(weeks_back: int = 1):
    """
    weeks_back = 1 -> last completed week
    weeks_back = 2 -> the week before last, etc.
    """
    # Get the last completed ISO week window; then move back (weeks_back-1) weeks
    base_start_utc, base_end_utc = last_completed_iso_week()
    start_utc = base_start_utc - timedelta(weeks=(weeks_back - 1))
    end_utc = base_end_utc - timedelta(weeks=(weeks_back - 1))

    if c.get("debug"):
        print(f"Weekly window UTC: {start_utc.isoformat()} → {end_utc.isoformat()}")

    # 1) Daily usage → weekly totals
    daily_json = _post_daily_usage(start_utc, end_utc)
    week_totals = _sum_daily_usage_to_week(daily_json)

    # 2) Optional AI code CSV → weekly line totals (overrides if present)
    csv_text = _get_ai_code_changes_csv(start_utc, end_utc)
    if csv_text:
        lines = _sum_ai_code_changes_csv(csv_text)
        # Prefer CSV line counts if non-zero; otherwise keep daily totals
        if lines["chat_suggested_lines"] or lines["chat_accepted_lines"]:
            week_totals["chat_suggested_lines"] = lines["chat_suggested_lines"]
            week_totals["chat_accepted_lines"] = lines["chat_accepted_lines"]

    # 3) Ratios
    ratios = _compute_ratios(week_totals)
    payload = {**week_totals, **ratios}

    # 4) Write
    _write_week_to_influx(start_utc, payload)


if __name__ == "__main__":
    # Allow overriding weeks_back via env (e.g., backfill)
    wb = int(os.getenv("WEEKS_BACK", "1"))
    run(weeks_back=wb)