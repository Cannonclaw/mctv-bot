# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Loop-inventory data service.

Drop into: mctv-bot/services/loop_inventory_service.py

Reads the tables loaded by the n-compass per-screen whitelist sweep
(July 2026). Key model fact: playlist content is license-whitelisted, so a
screen's REAL loop is the sum of the playlist items whitelisted to its
license — NOT the playlist's row-sum.

Tables:
    screen_loops  — one row per license (screen) per sweep date.
    dark_content  — playlist items whitelisted to 0 licenses (present in a
                    playlist but playing nowhere), with revenue context.

Public API:
    latest_sweep_date() ......... most recent swept_at (ISO string) or None
    screen_loops(swept_at) ...... rows for a sweep date (latest by default)
    market_summary(rows) ........ per-market aggregates for KPI cards
    dark_content(include_closed)  dark items, open-only by default
    dark_monthly_at_stake(rows) . sum of monthly_value on open paid items
"""
from __future__ import annotations

import os
from typing import Any

from supabase import create_client, Client

TARGET_SECONDS = 900  # 15:00 loop target (4 plays/hr)

# ---------------------------------------------------------------------------
# Lazy client
# ---------------------------------------------------------------------------

_sb: Client | None = None


def _supabase() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
        )
    return _sb


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def latest_sweep_date() -> str | None:
    """Most recent swept_at across all markets, as an ISO date string."""
    res = (
        _supabase()
        .table("screen_loops")
        .select("swept_at")
        .order("swept_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0]["swept_at"] if rows else None


def screen_loops(swept_at: str | None = None) -> list[dict[str, Any]]:
    """All screen rows for one sweep date (the latest sweep by default)."""
    day = swept_at or latest_sweep_date()
    if day is None:
        return []
    res = (
        _supabase()
        .table("screen_loops")
        .select("*")
        .eq("swept_at", day)
        .order("loop_seconds", desc=True)
        .execute()
    )
    return res.data or []


def market_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-market aggregates: screens, over-target count, avg/min/max loop."""
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        m = out.setdefault(
            r["market"],
            {"screens": 0, "over_target": 0, "total_seconds": 0,
             "min_seconds": None, "max_seconds": 0},
        )
        secs = r["loop_seconds"]
        m["screens"] += 1
        m["total_seconds"] += secs
        m["max_seconds"] = max(m["max_seconds"], secs)
        m["min_seconds"] = secs if m["min_seconds"] is None else min(m["min_seconds"], secs)
        if r.get("over_target"):
            m["over_target"] += 1
    for m in out.values():
        m["avg_seconds"] = round(m["total_seconds"] / m["screens"]) if m["screens"] else 0
    return out


def dark_content(include_closed: bool = False) -> list[dict[str, Any]]:
    """Dark items (whitelisted to 0 screens). Open findings only by default."""
    q = _supabase().table("dark_content").select("*")
    if not include_closed:
        q = q.eq("status", "open")
    rows = (q.execute().data) or []
    rows.sort(key=lambda r: (r.get("monthly_value") or 0), reverse=True)
    return rows


def dark_monthly_at_stake(rows: list[dict[str, Any]]) -> float:
    """Monthly revenue tied up in open paid dark items."""
    return float(sum(
        r.get("monthly_value") or 0
        for r in rows
        if r.get("bucket") == "paid" and r.get("status") == "open"
    ))
