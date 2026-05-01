# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Per-Rep Dashboard.

Picks a rep, shows their attributed MRR, pipeline, commission accrual
(MTD + YTD), open deals, hot leads, stalled deals, and recent wins.
Also lets the team snapshot the current month's commission into the
commission_payouts ledger for payroll.
"""

import sys
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.config_service import (
    load_config, get_team_first_names, get_team_names,
)
from services.rep_dashboard_service import (
    accrue_current_month, compute_rep_metrics, list_payouts,
)

st.set_page_config(
    page_title="Rep Dashboard - MCTV Bot",
    page_icon="\U0001F4B0",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## Rep Dashboard")
st.caption(
    "Pipeline, MRR attributed, and commission accrual per rep. Switch reps "
    "with the dropdown. Click 'Snapshot to Ledger' at month-end to lock in "
    "the month's payout."
)


# ── Pick a rep ──────────────────────────────────────────────────────────────

cfg = load_config()
team_full = get_team_names(cfg) or ["Mary Michael Cannon"]
team_first = get_team_first_names(cfg) or ["Mary Michael"]

# Build a (full_name, first_name) lookup
team = list(zip(team_full, team_first))

selected = st.selectbox(
    "Sales rep",
    options=[t[0] for t in team],
    index=0,
)
rep_full = selected
rep_first = next((f for n, f in team if n == selected), selected.split()[0])


# ── Pull metrics ────────────────────────────────────────────────────────────

with st.spinner(f"Computing metrics for {rep_full}..."):
    m = compute_rep_metrics(rep_full, rep_first)

st.caption(f"As of {m['as_of']} CT")


# ── KPI tiles ───────────────────────────────────────────────────────────────

st.markdown("### Revenue + Commission")
k1, k2, k3, k4 = st.columns(4)
k1.metric("MRR Attributed", f"${m['mrr_attributed']:,.0f}",
          delta=f"{m['active_contract_count']} active")
k2.metric("MTD Commission", f"${m['mtd_commission']:,.2f}")
k3.metric("YTD Commission", f"${m['ytd_commission']:,.2f}")
projected_year = m['mtd_commission'] * 12 if m['mtd_commission'] else 0
k4.metric("Annualized Pace", f"${projected_year:,.0f}",
          help="MTD × 12. Rough but honest.")

st.markdown("### Pipeline")
p1, p2, p3, p4 = st.columns(4)
p1.metric("Open Deals", m["open_deal_count"])
p2.metric("Pipeline Value", f"${m['pipeline_value']:,.0f}/mo")
p3.metric("Weighted Pipeline", f"${m['weighted_pipeline']:,.0f}/mo")
p4.metric("Hot Leads", m["hot_lead_count"])

if m["stalled_deal_count"]:
    st.warning(f"\u26A0\uFE0F **{m['stalled_deal_count']} stalled deal(s)** — "
                f"in same stage past threshold. See below.")

st.divider()


# ── Active contracts (commission breakdown) ─────────────────────────────────

st.markdown("### Your Active Contracts")
if m["active_contracts"]:
    rows = []
    for c in m["active_contracts"]:
        client = c.get("_client") or {}
        rate = client.get("commission_rate", 0.10)
        monthly = float(c.get("monthly_rate", 0) or 0)
        rows.append({
            "Client": client.get("business_name", ""),
            "Tier": c.get("tier_name", "Custom"),
            "Monthly Rate": f"${monthly:,.0f}",
            "Commission Rate": f"{float(rate or 0.10) * 100:.0f}%",
            "Monthly Commission": f"${monthly * float(rate or 0.10):.2f}",
            "Start": (c.get("start_date") or "")[:10],
            "End": (c.get("end_date") or "")[:10],
            "Status": c.get("status", ""),
        })
    st.dataframe(rows, width="stretch", hide_index=True)
else:
    st.info("No active contracts attributed to this rep yet.")

st.divider()


# ── Stalled deals ───────────────────────────────────────────────────────────

if m["stalled_deals"]:
    st.markdown("### Stalled Deals (your action needed)")
    rows = [{
        "Business": d.get("business_name", ""),
        "Stage": d.get("stage", ""),
        "Days in Stage": d.get("_days_stalled", 0),
        "Monthly Value": f"${float(d.get('monthly_value', 0) or 0):,.0f}",
        "Next Action": d.get("next_action", "—"),
    } for d in m["stalled_deals"]]
    st.dataframe(rows, width="stretch", hide_index=True)
    st.divider()


# ── Recent wins ─────────────────────────────────────────────────────────────

if m["recent_wins"]:
    st.markdown("### Recent Wins (last 60 days)")
    rows = [{
        "Client": (w.get("_client") or {}).get("business_name", ""),
        "Tier": w.get("tier_name", "Custom"),
        "Monthly Rate": f"${float(w.get('monthly_rate', 0) or 0):,.0f}",
        "Created": (w.get("created_at") or "")[:10],
    } for w in m["recent_wins"]]
    st.dataframe(rows, width="stretch", hide_index=True)
    st.divider()


# ── Payout ledger ───────────────────────────────────────────────────────────

st.markdown("### Commission Payout Ledger")
payouts = list_payouts(rep_full, limit=12)
if payouts:
    rows = [{
        "Period": f"{p.get('period_year')}-{p.get('period_month'):02d}",
        "Amount": f"${float(p.get('amount', 0) or 0):,.2f}",
        "Status": p.get("status", "").title(),
        "Paid At": (p.get("paid_at") or "")[:10],
        "Method": p.get("paid_method", ""),
    } for p in payouts]
    st.dataframe(rows, width="stretch", hide_index=True)
else:
    st.caption("No payouts on file yet.")

cact1, cact2, _ = st.columns([1, 1, 2])
if cact1.button("\U0001F4CC Snapshot This Month", width="stretch",
                 help="Lock in MTD commission into the payouts ledger"):
    saved = accrue_current_month(rep_full, rep_first)
    if saved:
        st.success(f"Snapshotted {date.today().strftime('%B %Y')} commission "
                   f"of ${m['mtd_commission']:,.2f} for {rep_full}.")
        st.rerun()
    else:
        st.error("Could not save snapshot. Check Supabase configuration.")

if cact2.button("\U0001F4CA YTD Breakdown", width="stretch"):
    st.session_state["show_ytd_breakdown"] = not st.session_state.get(
        "show_ytd_breakdown", False)
    st.rerun()

if st.session_state.get("show_ytd_breakdown") and m["breakdown_ytd"]:
    st.markdown("##### YTD breakdown by contract")
    rows = [{
        "Client": b.get("client_name", ""),
        "Monthly Rate": f"${b.get('monthly_rate', 0):,.0f}",
        "Commission Rate": f"{b.get('commission_rate', 0) * 100:.0f}%",
        "Months in Year": b.get("months_in_year", 0),
        "Commission YTD": f"${b.get('amount', 0):,.2f}",
    } for b in m["breakdown_ytd"]]
    st.dataframe(rows, width="stretch", hide_index=True)
