# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Rate Card — Streamlit page for the MCTV Team Member portal.

Live impression-model pricing for every venue: OOH-style rates computed
from NTV360 traffic, calibrated dwell profiles, and each venue's ACTUAL
per-screen loop from the latest whitelist sweep. Rates update themselves
when loops are trimmed, traffic snapshots refresh, or the model knobs
change — no more static rate sheets.

Drop into: mctv-bot/pages/25_Rate_Card.py
"""
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.rate_service import (
    apply_tiers,
    market_rate_summary,
    model_params,
    venue_rates,
)

st.set_page_config(
    page_title="Rate Card - MCTV Bot",
    page_icon="\U0001F4B5",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

MARKET_LABELS = {"oxford": "Oxford", "tupelo": "Tupelo",
                 "starkville": "Starkville", "special": "Special Venues"}


def mmss(minutes: float) -> str:
    s = int(round(minutes * 60))
    return f"{s // 60}:{s % 60:02d}"


rows = venue_rates()
params = model_params()
apply_tiers(rows)
summary = market_rate_summary(rows)

st.markdown("## \U0001F4B5 Rate Card")
st.caption(
    "OOH-style impression pricing, computed **live**: NTV360 traffic × "
    "exposures (dwell ÷ the venue's *actual* loop from the latest sweep) "
    "× screen coverage. "
    f"CPM **${params.get('cpm', 6)}** · exposure cap {params.get('exposure_cap', 6)} "
    f"· floor ${params.get('floor_4wk', 25)}/4wk. "
    "Knobs live in `rate_model_params`; venue inputs in `venue_rate_inputs`."
)

if not rows:
    st.info("No venues in `venue_rate_inputs` yet.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venues priced", len(rows))
k2.metric("Network weekly impressions", f"{sum(r['weekly_impressions'] for r in rows):,.0f}")
k3.metric("Network list value / 4wk", f"${sum(r['rate_4wk'] for r in rows):,.0f}")
k4.metric("Marquee venues", sum(1 for r in rows if r.get("tier") == "Marquee"))

st.divider()

markets = [m for m in ("oxford", "tupelo", "starkville", "special") if m in summary]
tabs = st.tabs([MARKET_LABELS.get(m, m.title()) for m in markets])

for tab, market in zip(tabs, markets):
    with tab:
        s = summary[market]
        c1, c2, c3 = st.columns(3)
        c1.metric("Venues", s["venues"])
        c2.metric("Weekly impressions", f"{s['weekly_impressions']:,.0f}")
        c3.metric("List value / 4wk", f"${s['list_4wk']:,.0f}")

        st.dataframe(
            [
                {
                    "Venue": r["venue_name"],
                    "Type": r["type_label"],
                    "Screens": r["screens"],
                    "Loop": mmss(r["loop_min"]) + ("" if r["loop_from_sweep"] else " *"),
                    "Impr/wk": round(r["weekly_impressions"]),
                    "List $/4wk": r["rate_4wk"],
                    "Tier": r.get("tier", ""),
                    "Tier $/4wk": r.get("tier_rate", r["rate_4wk"]),
                }
                for r in rows
                if r["market"] == market
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Impr/wk": st.column_config.NumberColumn(format="%d"),
                "List $/4wk": st.column_config.NumberColumn(format="$%d"),
                "Tier $/4wk": st.column_config.NumberColumn(format="$%d"),
            },
        )
        st.caption(
            "Loop = venue's actual per-screen loop from the latest sweep "
            "(* = manual/fallback value, not sweep-matched). Tier price = "
            "median of the venue's rank quartile; Marquee venues priced "
            "individually."
        )

st.divider()
with st.expander("Model sources & how to adjust"):
    st.markdown(
        "- **Traffic**: NTV360 network-dashboard monthly snapshots (the same "
        "basis metric as MCTV traction reports); venues without NTV data use "
        "calibrated type defaults (`venue_type_defaults`).\n"
        "- **Dwell**: host-reported Install Form values where available "
        "(e.g. Oxford Park Commission 3:00), else type defaults.\n"
        "- **Loop**: per-venue actual from `screen_loops` (latest whitelist "
        "sweep) — shorter loops = more exposures per visit = higher rates.\n"
        "- **Adjust**: edit `rate_model_params` (CPM, cap, floor) or "
        "`venue_rate_inputs` (traffic/dwell/type) in Supabase; this page and "
        "`venue_rates_v` recompute instantly.\n"
        "- Impression counts are modeled upper-bound estimates (disclosed as "
        "such) — n-compass has no native impression counting."
    )
