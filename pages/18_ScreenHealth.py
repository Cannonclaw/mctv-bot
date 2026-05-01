# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Screen Health — flags suspected dark or low-delivery venues from the
latest NTV360 snapshot.
"""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.screen_health_service import check_screen_health

st.set_page_config(
    page_title="Screen Health - MCTV Bot",
    page_icon="\U0001F6A8",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## Screen Health")
st.caption(
    "Compares the most recent NTV360 snapshot against expected plays per screen "
    "(plays_per_hour × hours_per_day × days_per_month × license_count). "
    "Venues delivering far below expected are likely dark or having issues."
)

with st.spinner("Inspecting latest snapshot..."):
    health = check_screen_health()

if health.get("warning"):
    st.warning(health["warning"])
    st.stop()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Snapshot", health["snapshot_month"] or "—")
m2.metric("Venues checked", health["venue_count"])
m3.metric("Dark (<10% expected)", len(health["dark"]))
m4.metric("Low (10-50% expected)", len(health["low"]))
m5.metric("Healthy (>=50%)", health["ok"])

st.caption(f"Expected plays/screen this period: {health['expected_per_screen']:,}")

if health["missing_in_snapshot"]:
    st.info(
        f"{health['missing_in_snapshot']} venues from the master dashboard "
        f"do not appear in the latest snapshot at all. Could be new, removed, "
        f"or a naming mismatch — worth a quick audit."
    )

st.divider()

# ── Dark venues ─────────────────────────────────────────────────────────────
if health["dark"]:
    st.markdown("### \U0001F6A8 Suspected Dark Screens")
    st.caption("Below 10% of expected plays. Most likely offline. Investigate first.")
    rows = [{
        "Venue": v["host_name"],
        "City": v.get("city", ""),
        "Screens": v["license_count"],
        "Plays": f"{v['plays']:,}",
        "Expected": f"{v['expected']:,}",
        "Ratio": f"{v['ratio']*100:.1f}%",
    } for v in health["dark"]]
    st.dataframe(rows, width="stretch", hide_index=True)
else:
    st.success("No suspected dark screens. Network is fully delivering.")

st.divider()

# ── Low-delivery ────────────────────────────────────────────────────────────
if health["low"]:
    st.markdown("### \u26A0\uFE0F Under-delivering")
    st.caption("Between 10% and 50% of expected. Could be partial day downtime, "
                "configuration drift, or busy-hours mismatch.")
    rows = [{
        "Venue": v["host_name"],
        "City": v.get("city", ""),
        "Screens": v["license_count"],
        "Plays": f"{v['plays']:,}",
        "Expected": f"{v['expected']:,}",
        "Ratio": f"{v['ratio']*100:.1f}%",
    } for v in health["low"]]
    st.dataframe(rows, width="stretch", hide_index=True)

st.divider()
st.caption(
    "Health is derived from monthly NTV360 snapshots — uploaded via the Reports "
    "page. For day-of detection, upload more frequently."
)
