# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Daily briefing dashboard — generate and send the MCTV morning operations snapshot."""

import streamlit as st
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.briefing_service import (
    generate_briefing,
    send_daily_briefing,
    format_briefing_sms,
)

st.set_page_config(page_title="Daily Briefing - MCTV Bot", page_icon="\U0001F4CA", layout="wide")

if not check_password():
    st.stop()


# ── Load config ───────────────────────────────────────────────────────────────

@st.cache_data
def load_config():
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()


# ── Page header ───────────────────────────────────────────────────────────────

st.title("Daily Briefing")
st.caption("Your morning snapshot of MCTV operations")


# ── Action bar ────────────────────────────────────────────────────────────────

col_gen, col_send, _ = st.columns([1, 1, 4])

with col_gen:
    generate_clicked = st.button("Generate Briefing", type="primary", use_container_width=True)

with col_send:
    send_clicked = st.button("Send to Team", use_container_width=True)


# ── Generate briefing ─────────────────────────────────────────────────────────

if generate_clicked:
    with st.spinner("Generating briefing..."):
        try:
            briefing = generate_briefing()
            st.session_state.briefing = briefing
        except Exception as e:
            st.error(f"Failed to generate briefing: {e}")

if send_clicked:
    with st.spinner("Sending to team..."):
        try:
            result = send_daily_briefing(config)
            st.session_state.briefing = result.get("briefing", {})
            if result.get("success"):
                parts = []
                if result.get("email_sent"):
                    parts.append("email")
                if result.get("sms_sent"):
                    parts.append("SMS")
                if parts:
                    st.success(f"Briefing sent to team via {' and '.join(parts)}!")
                else:
                    st.warning("Briefing generated but delivery failed. Check SMTP/Twilio settings.")
            for err in result.get("errors", []):
                st.warning(err)
        except Exception as e:
            st.error(f"Failed to send briefing: {e}")


# ── Display briefing ─────────────────────────────────────────────────────────

briefing = st.session_state.get("briefing")

if not briefing:
    st.info("Click **Generate Briefing** to create today's operations snapshot.")
    st.stop()


# ── 1. Alerts ─────────────────────────────────────────────────────────────────

alerts = briefing.get("alerts", [])
if alerts:
    for alert in alerts:
        st.warning(alert)


# ── 2. Executive Summary ─────────────────────────────────────────────────────

st.subheader("Executive Summary")

summary = briefing.get("executive_summary", {})
s1, s2, s3, s4 = st.columns(4)

with s1:
    mrr = summary.get("monthly_recurring_revenue", 0)
    st.metric("MRR", f"${mrr:,.0f}")

with s2:
    active_clients = summary.get("active_clients", 0)
    st.metric("Active Clients", active_clients)

with s3:
    pending = summary.get("contracts_awaiting_signature", 0)
    st.metric("Contracts Pending", pending)

with s4:
    overdue = summary.get("overdue_amount", 0)
    st.metric("Overdue Amount", f"${overdue:,.0f}")


# ── 3. Revenue ────────────────────────────────────────────────────────────────

st.subheader("Revenue")

revenue = briefing.get("revenue", {})

if revenue:
    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric("Total Billed", f"${revenue.get('total_billed', 0):,.2f}")

    with r2:
        st.metric("Collected", f"${revenue.get('total_collected', 0):,.2f}")

    with r3:
        st.metric("Outstanding", f"${revenue.get('total_outstanding', 0):,.2f}")

    with r4:
        st.metric("Overdue", f"${revenue.get('total_overdue', 0):,.2f}")

    overdue_list = revenue.get("overdue_list", [])
    if overdue_list:
        st.markdown("**Overdue Accounts**")
        df_overdue = pd.DataFrame(overdue_list)
        display_cols = []
        if "business_name" in df_overdue.columns:
            display_cols.append("business_name")
        if "amount" in df_overdue.columns:
            display_cols.append("amount")
        if "days_overdue" in df_overdue.columns:
            display_cols.append("days_overdue")
        col_rename = {
            "business_name": "Business",
            "amount": "Amount Due",
            "days_overdue": "Days Overdue",
        }
        if display_cols:
            st.dataframe(
                df_overdue[display_cols].rename(columns=col_rename),
                use_container_width=True,
                hide_index=True,
            )

    ar_aging = revenue.get("ar_aging", {})
    if ar_aging:
        st.markdown("**AR Aging**")
        aging_rows = [{"Period": k, "Amount": f"${v:,.2f}"} for k, v in ar_aging.items()]
        st.dataframe(pd.DataFrame(aging_rows), use_container_width=True, hide_index=True)

else:
    st.info("No revenue data available.")


# ── 4. Contracts ──────────────────────────────────────────────────────────────

st.subheader("Contracts")

contracts = briefing.get("contracts", {})

if contracts:
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Draft", contracts.get("draft", 0))

    with c2:
        st.metric("Sent", contracts.get("sent", 0))

    with c3:
        st.metric("Awaiting Sig", contracts.get("awaiting_signature", 0))

    with c4:
        st.metric("Active", contracts.get("active", 0))

    with c5:
        st.metric("MRR", f"${contracts.get('active_mrr', 0):,.0f}")

    needs_attention = contracts.get("needs_attention", [])
    if needs_attention:
        st.markdown("**Needs Attention**")
        for item in needs_attention:
            title = item.get("title", "Unknown")
            days = item.get("days_waiting", "?")
            st.info(f"{title} -- sent {days} days ago, awaiting signature")

else:
    st.info("No contract data available.")


# ── 5. Leads ─────────────────────────────────────────────────────────────────

st.subheader("Leads")

leads = briefing.get("leads", {})

if leads:
    hot_leads = leads.get("hot", [])

    l1, l2, l3 = st.columns(3)

    with l1:
        st.metric("Hot Leads", len(hot_leads))

    with l2:
        st.metric("Warm Leads", leads.get("warm_count", 0))

    with l3:
        st.metric("Cold Leads", leads.get("cold_count", 0))

    if hot_leads:
        st.markdown("**Hot Leads**")
        df_hot = pd.DataFrame(hot_leads)
        display_cols = []
        for col in ["business_name", "score", "city", "status"]:
            if col in df_hot.columns:
                display_cols.append(col)
        col_rename = {
            "business_name": "Business",
            "score": "Score",
            "city": "City",
            "status": "Status",
        }
        if display_cols:
            st.dataframe(
                df_hot[display_cols].rename(columns=col_rename),
                use_container_width=True,
                hide_index=True,
            )

    follow_ups = leads.get("follow_ups_due", [])
    if follow_ups:
        st.markdown("**Follow-ups Due**")
        for fu in follow_ups:
            biz = fu.get("business_name", "Unknown")
            due_date = fu.get("follow_up_date", "")
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date)
                    due_date = dt.strftime("%B %d, %Y")
                except (ValueError, TypeError):
                    pass
            st.warning(f"{biz} -- follow-up due {due_date}")

else:
    st.info("No lead data available.")


# ── 6. Recent Activity ───────────────────────────────────────────────────────

st.subheader("Recent Activity")

recent_activity = briefing.get("recent_activity", [])

if recent_activity:
    df_activity = pd.DataFrame(recent_activity)
    st.dataframe(df_activity, use_container_width=True, hide_index=True)
else:
    st.info("No recent activity to display.")


# ── 7. SMS Preview ───────────────────────────────────────────────────────────

st.subheader("SMS Preview")

try:
    sms_text = format_briefing_sms(briefing)
    st.code(sms_text, language=None)
except Exception as e:
    st.error(f"Could not format SMS preview: {e}")


# ── Footer ────────────────────────────────────────────────────────────────────

generated_at = briefing.get("generated_at", "")
if generated_at:
    try:
        dt = datetime.fromisoformat(generated_at)
        display_time = dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        display_time = generated_at
    st.caption(f"Generated at {display_time}")
