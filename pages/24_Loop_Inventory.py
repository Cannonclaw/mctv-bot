# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Loop Inventory — Streamlit page for the MCTV Team Member portal.

What each screen ACTUALLY plays (per-license whitelist sweep of the
n-compass playlists), which venues are over the 15:00 loop target, and
dark content — items sitting in a playlist but playing on zero screens,
including paid ads with monthly revenue at stake.

Drop into: mctv-bot/pages/24_Loop_Inventory.py
"""
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.loop_inventory_service import (
    TARGET_SECONDS,
    dark_content,
    dark_monthly_at_stake,
    latest_sweep_date,
    market_summary,
    screen_loops,
)

st.set_page_config(
    page_title="Loop Inventory - MCTV Bot",
    page_icon="\U0001F4FA",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mmss(seconds: int | float | None) -> str:
    s = int(seconds or 0)
    return f"{s // 60}:{s % 60:02d}"


MARKET_LABELS = {"oxford": "Oxford", "tupelo": "Tupelo", "starkville": "Starkville"}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

sweep = latest_sweep_date()
rows = screen_loops(sweep) if sweep else []
dark = dark_content()
at_stake = dark_monthly_at_stake(dark)
summary = market_summary(rows)


# ---------------------------------------------------------------------------
# Header + network KPIs
# ---------------------------------------------------------------------------

st.markdown("## \U0001F4FA Loop Inventory")
st.caption(
    "Per-screen **actual** loops from the n-compass whitelist sweep — a screen's "
    "real loop is the sum of playlist items whitelisted to its license, not the "
    "playlist total. Target: **15:00** (4 plays/hr)."
    + (f" Last sweep: **{sweep}**." if sweep else "")
)

if not rows:
    st.info(
        "No sweep data yet. Run the per-screen whitelist sweep and load "
        "`screen_loops` (see the loop-inventory manifest in OneDrive)."
    )
    st.stop()

over_total = sum(1 for r in rows if r.get("over_target"))
k1, k2, k3, k4 = st.columns(4)
k1.metric("Screens swept", len(rows))
k2.metric("Over 15:00 target", over_total,
          delta=None if over_total == 0 else f"{over_total} to trim",
          delta_color="inverse")
k3.metric("Worst loop", mmss(max(r["loop_seconds"] for r in rows)))
k4.metric("Dark-ad $ at stake", f"${at_stake:,.0f}/mo")

st.divider()


# ---------------------------------------------------------------------------
# Per-market tabs
# ---------------------------------------------------------------------------

markets = [m for m in ("oxford", "tupelo", "starkville") if m in summary]
markets += [m for m in summary if m not in markets]
tabs = st.tabs([MARKET_LABELS.get(m, m.title()) for m in markets])

for tab, market in zip(tabs, markets):
    with tab:
        s = summary[market]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Screens", s["screens"])
        c2.metric("Over target", s["over_target"])
        c3.metric("Avg loop", mmss(s["avg_seconds"]))
        c4.metric("Range", f"{mmss(s['min_seconds'])} – {mmss(s['max_seconds'])}")

        table = [
            {
                "Venue / screen": r["venue_name"],
                "Loop": mmss(r["loop_seconds"]),
                "Seconds": r["loop_seconds"],
                "Items": r["item_count"],
                "Over target": bool(r.get("over_target")),
            }
            for r in rows
            if r["market"] == market
        ]
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Seconds": st.column_config.ProgressColumn(
                    "vs 25:00",
                    min_value=0,
                    max_value=1500,
                    format="%d",
                ),
                "Over target": st.column_config.CheckboxColumn(disabled=True),
            },
        )
        if s["over_target"]:
            st.caption(
                f"{s['over_target']} screen(s) above {mmss(TARGET_SECONDS)} — "
                "trim candidates (see the Oxford Phase-1 playbook)."
            )
        else:
            st.caption("All screens at or under target \U00002705")


# ---------------------------------------------------------------------------
# Dark content
# ---------------------------------------------------------------------------

st.divider()
st.markdown("### \U0001F573\U0000FE0F Dark content — in a playlist, playing nowhere")

if not dark:
    st.success("No open dark-content findings.")
else:
    paid_dark = [d for d in dark if d.get("bucket") == "paid"]
    if paid_dark:
        st.warning(
            f"**{len(paid_dark)} paid ad(s) not airing** — "
            f"${at_stake:,.0f}/mo at stake. Resolve in the portal "
            "(whitelist or remove) and update status here."
        )
    st.dataframe(
        [
            {
                "Advertiser / item": d.get("advertiser") or d["file_name"],
                "Market": MARKET_LABELS.get(d["market"], d["market"]),
                "Type": d["bucket"],
                "$/mo": d.get("monthly_value"),
                "Status": d["status"],
                "Finding": d.get("finding") or "",
                "File": d["file_name"],
            }
            for d in dark
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "$/mo": st.column_config.NumberColumn(format="$%d"),
            "Finding": st.column_config.TextColumn(width="large"),
        },
    )

st.caption(
    "Source: `screen_loops` / `dark_content` in Supabase, loaded by the "
    "n-compass per-screen whitelist sweep. Refresh by re-running the sweep; "
    "history accumulates by `swept_at`."
)
