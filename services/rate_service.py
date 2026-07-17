# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Impression rate-model service.

Drop into: mctv-bot/services/rate_service.py

Reads `venue_rates_v`, a Postgres view that computes the MCTV impression
model LIVE against the latest per-screen whitelist sweep:

    weekly impressions = weekly visits x min(cap, dwell / loop_min)
                         x (1 + (screens - 1) x cross-screen %)
    rate/4wk = max(floor, nearest-$5 of impressions x 4 / 1000 x CPM)

Inputs live in Supabase: `venue_rate_inputs` (traffic = NTV360 snapshot,
dwell overrides from Host Install Forms, venue types), `venue_type_defaults`
(calibrated type profiles), `rate_model_params` (CPM/cap/floor knobs), and
`screen_loops` (per-venue ACTUAL loop from the latest sweep). Rates move
automatically when any of those change.

Public API:
    venue_rates() ............ all venues with impressions + list rate
    market_rate_summary(rows)  per-market rollups for KPI cards
    apply_tiers(rows) ........ marquee/quartile tiering (mutates + returns)
    model_params() ........... the current knob values
"""
from __future__ import annotations

import os
from statistics import median
from typing import Any

from supabase import create_client, Client

_sb: Client | None = None


def _supabase() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
        )
    return _sb


def venue_rates() -> list[dict[str, Any]]:
    """All venues from the live view, highest list rate first."""
    res = _supabase().table("venue_rates_v").select("*").execute()
    rows = res.data or []
    for r in rows:
        r["rate_4wk"] = float(r["rate_4wk"] or 0)
        r["weekly_impressions"] = float(r["weekly_impressions"] or 0)
        r["loop_min"] = float(r["loop_min"] or 0)
    # Defense-in-depth: apply the Phase-1 venue cap from rate_model_params even
    # if the capped view flip hasn't run yet (harmless double-cap after it has),
    # so tiering downstream always sees capped rates.
    cap = model_params().get("venue_cap_4wk")
    if cap:
        for r in rows:
            r["rate_4wk"] = min(r["rate_4wk"], float(cap))
    rows.sort(key=lambda r: r["rate_4wk"], reverse=True)
    return rows


def model_params() -> dict[str, Any]:
    res = _supabase().table("rate_model_params").select("*").eq("id", 1).execute()
    return (res.data or [{}])[0]


def apply_tiers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Marquee + quartile tiering, same logic as the standalone rate card:
    marquee = rate > 1.6x the median of the top quartile (priced individually);
    everyone else falls into rank quartiles priced at the tier median."""
    if not rows:
        return rows
    ranked = sorted(rows, key=lambda r: r["rate_4wk"], reverse=True)
    q_len = max(1, len(ranked) // 4)
    top_q_median = median([r["rate_4wk"] for r in ranked[:q_len]])
    marquee_cut = 1.6 * top_q_median
    marquee = [r for r in ranked if r["rate_4wk"] > marquee_cut]
    rest = [r for r in ranked if r["rate_4wk"] <= marquee_cut]
    for r in marquee:
        r["tier"] = "Marquee"
        r["tier_rate"] = r["rate_4wk"]
    names = ["Platinum", "Gold", "Silver", "Bronze"]
    if rest:
        per = max(1, round(len(rest) / 4))
        buckets = [rest[i * per:(i + 1) * per] for i in range(3)]
        buckets.append(rest[3 * per:])
        buckets = [b for b in buckets if b]
        prev_rate = None
        prev_name = None
        for name, bucket in zip(names, buckets):
            t_rate = float(median([r["rate_4wk"] for r in bucket]))
            if prev_rate is not None and t_rate == prev_rate:
                name = prev_name  # merge equal-priced tiers
            for r in bucket:
                r["tier"] = name
                r["tier_rate"] = t_rate
            prev_rate, prev_name = t_rate, name
    return rows


def market_rate_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        m = out.setdefault(r["market"], {"venues": 0, "weekly_impressions": 0.0, "list_4wk": 0.0})
        m["venues"] += 1
        m["weekly_impressions"] += r["weekly_impressions"]
        m["list_4wk"] += r["rate_4wk"]
    return out
