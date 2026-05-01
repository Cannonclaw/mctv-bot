# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Screen health monitor — detects suspected dark or under-performing screens
by comparing NTV360 actual plays vs. expected plays from network defaults.

Since MCTV does not own NTV360 hardware, there's no direct heartbeat. This
service infers health from the most recent NTV360 snapshot:

    expected_plays_per_month = plays_per_hour * hours_per_day * days_per_month * license_count

A venue is flagged based on the ratio of actual / expected plays:
    < 0.10  -> "dark" (almost certainly offline)
    < 0.50  -> "low" (under-delivering, worth investigating)
    >= 0.50 -> "ok"
"""

import json
import logging
from datetime import date

from services.config_service import (
    get_days_per_month, get_hours_per_day, load_config,
)
from services.ntv360_service import get_latest_snapshot

logger = logging.getLogger(__name__)


def check_screen_health(target_month: str | None = None) -> dict:
    """Inspect the latest NTV360 snapshot and classify each venue's health.

    Returns:
        {
            "snapshot_month": "YYYY-MM",
            "checked_at": "ISO timestamp",
            "expected_per_screen": int,
            "venue_count": int,
            "dark": [{host_name, plays, expected, ratio, license_count}, ...],
            "low":  [...],
            "ok":   int,
            "missing_in_snapshot": int,
        }
    """
    config = load_config()
    plays_per_hour = int(config.get("network", {}).get("plays_per_hour", 4))
    hours_per_day = get_hours_per_day(config)
    days_per_month = get_days_per_month(config)
    expected_per_screen = plays_per_hour * hours_per_day * days_per_month

    snap = get_latest_snapshot(target_month) or get_latest_snapshot()
    if not snap:
        return {
            "snapshot_month": "",
            "checked_at": date.today().isoformat(),
            "expected_per_screen": expected_per_screen,
            "venue_count": 0,
            "dark": [], "low": [], "ok": 0, "missing_in_snapshot": 0,
            "warning": "No NTV360 snapshot available — upload one via Reports first.",
        }

    venue_data = snap.get("venue_data", [])
    if isinstance(venue_data, str):
        try:
            venue_data = json.loads(venue_data)
        except (json.JSONDecodeError, TypeError):
            venue_data = []

    dark, low, ok = [], [], 0
    for v in venue_data:
        host = v.get("host_name", "")
        plays = int(v.get("total_plays", 0) or 0)
        screens = int(v.get("screen_count", 1) or 1)
        expected = expected_per_screen * max(screens, 1)
        ratio = (plays / expected) if expected else 0.0
        record = {
            "host_name": host,
            "plays": plays,
            "expected": expected,
            "ratio": round(ratio, 3),
            "license_count": screens,
            "city": v.get("city", ""),
        }
        if ratio < 0.10:
            dark.append(record)
        elif ratio < 0.50:
            low.append(record)
        else:
            ok += 1

    # Cross-check with master dashboard so we can flag venues that are
    # registered but didn't appear in the snapshot at all.
    try:
        from pathlib import Path
        dash_path = Path(__file__).parent.parent / "data" / "network_dashboard.json"
        with open(dash_path, encoding="utf-8") as f:
            master = json.load(f).get("venues", {})
        snapshot_hosts = {(v.get("host_name") or "").lower() for v in venue_data}
        missing = [m["host_name"] for m in master.values()
                   if (m.get("host_name") or "").lower() not in snapshot_hosts]
        missing_count = len(missing)
    except Exception:
        missing_count = 0

    # Sort by worst-first
    dark.sort(key=lambda r: r["ratio"])
    low.sort(key=lambda r: r["ratio"])

    return {
        "snapshot_month": snap.get("snapshot_month", ""),
        "checked_at": date.today().isoformat(),
        "expected_per_screen": expected_per_screen,
        "venue_count": len(venue_data),
        "dark": dark,
        "low": low,
        "ok": ok,
        "missing_in_snapshot": missing_count,
    }
