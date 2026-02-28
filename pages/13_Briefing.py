# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Team Activity Dashboard — the MCTV morning operations command center.

Auto-generates a live operational snapshot showing alerts, revenue, contracts,
leads, creative requests, and recent activity. Can also send the briefing to
the team via email + SMS.
"""

import streamlit as st
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.briefing_service import (
    generate_briefing,
    send_daily_briefing,
    format_briefing_sms,
    get_briefing_history,
)

st.set_page_config(
    page_title="Team Dashboard - MCTV Bot",
    page_icon="\U0001F4CB",
    layout="wide",
)

if not check_password():
    st.stop()


# ── Load config ───────────────────────────────────────────────────────────────

@st.cache_data
def load_config():
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()


# ── Helper: load creative requests ───────────────────────────────────────────

def _load_creative_requests() -> dict:
    """Pull creative request counts from Supabase."""
    try:
        from services.supabase_client import query_table
        all_requests = query_table("creative_requests", order="-created_at") or []

        pending = [r for r in all_requests if r.get("status") == "pending"]
        in_progress = [r for r in all_requests if r.get("status") == "in_progress"]
        review = [r for r in all_requests if r.get("status") == "review"]
        completed = [
            r for r in all_requests
            if r.get("status") in ("approved", "live")
        ]

        # Urgent requests
        urgent = [
            r for r in all_requests
            if r.get("priority") == "urgent"
            and r.get("status") in ("pending", "in_progress")
        ]

        return {
            "total": len(all_requests),
            "pending": len(pending),
            "pending_list": pending[:5],
            "in_progress": len(in_progress),
            "in_progress_list": in_progress[:5],
            "review": len(review),
            "completed": len(completed),
            "urgent": len(urgent),
            "urgent_list": urgent[:5],
        }
    except Exception:
        return {}


# ── Helper: load expiring contracts ──────────────────────────────────────────

def _load_expiring_contracts() -> dict:
    """Find contracts expiring within 30/60/90 days."""
    try:
        from services.contract_service import get_all_contracts
        all_contracts = get_all_contracts() or []
        today = date.today()

        expiring_30 = []
        expiring_60 = []
        expiring_90 = []

        for c in all_contracts:
            if c.get("status") != "active":
                continue

            # Calculate end date from start_date + term_months
            start_str = c.get("start_date", "")
            term_months = c.get("term_months") or c.get("term", 0)
            if not start_str or not term_months:
                continue

            try:
                start_date = date.fromisoformat(start_str)
                # Approximate end date
                end_date = start_date + timedelta(days=int(term_months) * 30)
                days_remaining = (end_date - today).days

                if days_remaining < 0:
                    continue  # Already expired

                entry = {
                    "title": c.get("title", "Untitled"),
                    "client_name": c.get("client_name", c.get("client_id", "Unknown")),
                    "end_date": end_date.isoformat(),
                    "days_remaining": days_remaining,
                    "monthly_rate": float(c.get("monthly_rate", 0) or c.get("rate", 0) or 0),
                }

                if days_remaining <= 30:
                    expiring_30.append(entry)
                elif days_remaining <= 60:
                    expiring_60.append(entry)
                elif days_remaining <= 90:
                    expiring_90.append(entry)
            except (ValueError, TypeError):
                continue

        # Sort by most urgent first
        expiring_30.sort(key=lambda x: x["days_remaining"])
        expiring_60.sort(key=lambda x: x["days_remaining"])
        expiring_90.sort(key=lambda x: x["days_remaining"])

        return {
            "within_30": expiring_30,
            "within_60": expiring_60,
            "within_90": expiring_90,
            "total_at_risk": len(expiring_30) + len(expiring_60) + len(expiring_90),
            "mrr_at_risk": sum(c["monthly_rate"] for c in expiring_30 + expiring_60 + expiring_90),
        }
    except Exception:
        return {}


# ── Page header ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .alert-card {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }
    .alert-critical {
        background: #FEE2E2;
        border-left: 4px solid #DC2626;
        color: #991B1B;
    }
    .alert-warning {
        background: #FEF3C7;
        border-left: 4px solid #D97706;
        color: #92400E;
    }
    .alert-info {
        background: #DBEAFE;
        border-left: 4px solid #2563EB;
        color: #1E40AF;
    }
    .section-divider {
        border-top: 2px solid #E5E7EB;
        margin: 24px 0 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Team Activity Dashboard")
st.caption(f"Operations command center \u2014 {datetime.now().strftime('%A, %B %d, %Y')}")


# ── Action bar ────────────────────────────────────────────────────────────────

col_refresh, col_send, col_history, _ = st.columns([1, 1, 1, 3])

with col_refresh:
    refresh_clicked = st.button(
        "Refresh Dashboard",
        type="primary",
        use_container_width=True,
    )

with col_send:
    send_clicked = st.button(
        "Send to Team",
        use_container_width=True,
    )

with col_history:
    show_history = st.button(
        "Briefing History",
        use_container_width=True,
    )


# ── Auto-generate or refresh ────────────────────────────────────────────────

if refresh_clicked or "briefing" not in st.session_state:
    with st.spinner("Loading dashboard data..."):
        try:
            briefing = generate_briefing()
            st.session_state.briefing = briefing
            st.session_state.briefing_time = datetime.now()

            # Also load supplementary data
            st.session_state.creative_data = _load_creative_requests()
            st.session_state.expiring_data = _load_expiring_contracts()
        except Exception as e:
            st.error(f"Failed to load dashboard: {e}")
            st.stop()


if send_clicked:
    with st.spinner("Sending briefing to team..."):
        try:
            result = send_daily_briefing(config)
            st.session_state.briefing = result.get("briefing", {})
            st.session_state.briefing_time = datetime.now()
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


# ── Show briefing history modal ──────────────────────────────────────────────

if show_history:
    with st.expander("Briefing History (Last 30 Days)", expanded=True):
        history = get_briefing_history(limit=30)
        if history:
            hist_data = []
            for entry in history:
                details = entry.get("details", {})
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                hist_data.append({
                    "Date": entry.get("created_at", "")[:16].replace("T", " "),
                    "MRR": f"${details.get('mrr', 0):,.0f}",
                    "Alerts": details.get("alerts", 0),
                    "Email": "Sent" if details.get("email_sent") else "Failed",
                    "SMS": "Sent" if details.get("sms_sent") else "Failed",
                })
            st.dataframe(
                pd.DataFrame(hist_data),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No briefing history yet. Send your first briefing to start tracking.")


# ── Load data ────────────────────────────────────────────────────────────────

briefing = st.session_state.get("briefing")
if not briefing:
    st.info("Click **Refresh Dashboard** to load the operations snapshot.")
    st.stop()

creative_data = st.session_state.get("creative_data", {})
expiring_data = st.session_state.get("expiring_data", {})


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: PRIORITY ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

alerts = briefing.get("alerts", [])

# Add creative request alerts
if creative_data.get("urgent", 0) > 0:
    alerts.append(
        f"{creative_data['urgent']} urgent creative request"
        f"{'s' if creative_data['urgent'] != 1 else ''} need attention"
    )

# Add contract expiration alerts
if expiring_data.get("within_30"):
    count = len(expiring_data["within_30"])
    mrr = sum(c["monthly_rate"] for c in expiring_data["within_30"])
    alerts.insert(0,
        f"{count} contract{'s' if count != 1 else ''} expiring within 30 days "
        f"(${mrr:,.0f}/mo at risk)"
    )

if alerts:
    st.markdown("### Priority Actions")
    for i, alert in enumerate(alerts):
        # First 2 alerts are critical, next 2 are warnings, rest are info
        if i < 2:
            css_class = "alert-critical"
        elif i < 4:
            css_class = "alert-warning"
        else:
            css_class = "alert-info"
        st.markdown(
            f'<div class="alert-card {css_class}">{alert}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("")  # Spacing


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: EXECUTIVE SUMMARY (KPI Cards)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown("### Executive Summary")

summary = briefing.get("executive_summary", {})

s1, s2, s3, s4, s5, s6 = st.columns(6)

with s1:
    mrr = summary.get("monthly_recurring_revenue", 0)
    st.metric("Monthly MRR", f"${mrr:,.0f}")

with s2:
    active_clients = summary.get("active_clients", 0)
    st.metric("Active Clients", active_clients)

with s3:
    pending = summary.get("contracts_awaiting_signature", 0)
    st.metric("Pending Signature", pending)

with s4:
    overdue_amt = summary.get("overdue_amount", 0)
    st.metric("Overdue AR", f"${overdue_amt:,.0f}")

with s5:
    hot = summary.get("hot_leads", 0)
    st.metric("Hot Leads", hot)

with s6:
    new_today = summary.get("new_leads_today", 0)
    st.metric("New Leads Today", new_today)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: THREE-COLUMN DETAIL VIEW
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns(3)


# ── LEFT COLUMN: Revenue ─────────────────────────────────────────────────────

with col_left:
    st.markdown("### Revenue & AR")

    revenue = briefing.get("revenue", {})
    if revenue:
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Total Billed", f"${revenue.get('total_billed', 0):,.0f}")
            st.metric("Collected", f"${revenue.get('total_collected', 0):,.0f}")
        with r2:
            st.metric("Outstanding", f"${revenue.get('total_outstanding', 0):,.0f}")
            st.metric("Overdue", f"${revenue.get('total_overdue', 0):,.0f}")

        # AR Aging
        ar_aging = revenue.get("ar_aging", {})
        if ar_aging:
            st.markdown("**AR Aging**")
            aging_items = []
            for period, amount in ar_aging.items():
                aging_items.append(f"**{period}**: ${amount:,.0f}")
            st.markdown(" | ".join(aging_items))

        # Overdue accounts
        overdue_list = revenue.get("overdue_list", [])
        if overdue_list:
            st.markdown("**Overdue Accounts**")
            for inv in overdue_list[:5]:
                days = inv.get("days_overdue", 0)
                badge = "critical" if days >= 45 else "warning" if days >= 30 else "info"
                st.markdown(
                    f'<div class="alert-card alert-{badge}" style="padding:8px 12px;font-size:13px;">'
                    f'**{inv.get("business_name", "Unknown")}** '
                    f'&mdash; ${inv.get("amount", 0):,.0f} '
                    f'({days} days overdue)'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("No revenue data available.")


# ── MIDDLE COLUMN: Contracts ─────────────────────────────────────────────────

with col_mid:
    st.markdown("### Contracts")

    contracts = briefing.get("contracts", {})
    if contracts:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Draft", contracts.get("draft", 0))
            st.metric("Sent", contracts.get("sent", 0))
        with c2:
            st.metric("Active", contracts.get("active", 0))
            st.metric("MRR", f"${contracts.get('active_mrr', 0):,.0f}")

        needs_attention = contracts.get("needs_attention", [])
        if needs_attention:
            st.markdown("**Needs Follow-Up**")
            for item in needs_attention[:5]:
                title = item.get("title", "Unknown")
                days = item.get("days_waiting", "?")
                st.warning(f"{title} \u2014 {days} days awaiting signature")

    # Contract Expirations
    if expiring_data:
        exp_30 = expiring_data.get("within_30", [])
        exp_60 = expiring_data.get("within_60", [])
        exp_90 = expiring_data.get("within_90", [])
        total_at_risk = expiring_data.get("total_at_risk", 0)

        if total_at_risk > 0:
            st.markdown("**Expiring Soon**")
            mrr_risk = expiring_data.get("mrr_at_risk", 0)
            st.caption(f"{total_at_risk} contract{'s' if total_at_risk != 1 else ''} \u2014 ${mrr_risk:,.0f}/mo at risk")

            for c in exp_30:
                st.markdown(
                    f'<div class="alert-card alert-critical" style="padding:6px 10px;font-size:12px;">'
                    f'{c["client_name"]} \u2014 {c["days_remaining"]}d left (${c["monthly_rate"]:,.0f}/mo)'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            for c in exp_60[:3]:
                st.markdown(
                    f'<div class="alert-card alert-warning" style="padding:6px 10px;font-size:12px;">'
                    f'{c["client_name"]} \u2014 {c["days_remaining"]}d left (${c["monthly_rate"]:,.0f}/mo)'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            for c in exp_90[:2]:
                st.markdown(
                    f'<div class="alert-card alert-info" style="padding:6px 10px;font-size:12px;">'
                    f'{c["client_name"]} \u2014 {c["days_remaining"]}d left (${c["monthly_rate"]:,.0f}/mo)'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    if not contracts and not expiring_data:
        st.info("No contract data available.")


# ── RIGHT COLUMN: Leads + Creative ───────────────────────────────────────────

with col_right:
    st.markdown("### Leads Pipeline")

    leads = briefing.get("leads", {})
    if leads:
        hot_leads = leads.get("hot", [])

        l1, l2, l3 = st.columns(3)
        with l1:
            st.metric("Hot", len(hot_leads))
        with l2:
            st.metric("Warm", leads.get("warm_count", 0))
        with l3:
            st.metric("Cold", leads.get("cold_count", 0))

        if hot_leads:
            st.markdown("**Hot Leads**")
            for hl in hot_leads[:5]:
                city = f" ({hl.get('city', '')})" if hl.get("city") else ""
                st.markdown(
                    f'<div class="alert-card alert-info" style="padding:6px 10px;font-size:12px;">'
                    f'{hl.get("business_name", "Unknown")}{city} '
                    f'&mdash; Score: {hl.get("score", 0)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        follow_ups = leads.get("follow_ups_due", [])
        if follow_ups:
            st.markdown("**Follow-Ups Overdue**")
            for fu in follow_ups[:5]:
                biz = fu.get("business_name", "Unknown")
                due = fu.get("follow_up_date", "")
                if due:
                    try:
                        dt = datetime.fromisoformat(due)
                        due = dt.strftime("%b %d")
                    except (ValueError, TypeError):
                        pass
                st.warning(f"{biz} \u2014 due {due}")
    else:
        st.info("No lead data available.")

    # Creative Requests section
    if creative_data:
        st.markdown("---")
        st.markdown("### Creative Requests")

        cr1, cr2, cr3 = st.columns(3)
        with cr1:
            st.metric("Pending", creative_data.get("pending", 0))
        with cr2:
            st.metric("In Progress", creative_data.get("in_progress", 0))
        with cr3:
            st.metric("In Review", creative_data.get("review", 0))

        urgent_list = creative_data.get("urgent_list", [])
        if urgent_list:
            st.markdown("**Urgent Requests**")
            for req in urgent_list[:3]:
                title = req.get("title", "Untitled")
                rtype = req.get("request_type", "general").replace("_", " ").title()
                st.markdown(
                    f'<div class="alert-card alert-critical" style="padding:6px 10px;font-size:12px;">'
                    f'{title} ({rtype})'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3B: LEAD SOURCE ATTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════════

attribution = briefing.get("attribution", {})
funnel = attribution.get("funnel", {})

if funnel:
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Lead Source Attribution")
    st.caption("Full funnel: how leads find MCTV and convert to revenue")

    # ── Conversion Funnel Table ──────────────────────────────────────────────
    attr_left, attr_right = st.columns([3, 2])

    with attr_left:
        st.markdown("**Conversion Funnel**")

        funnel_rows = []
        for source, data in sorted(
            funnel.items(),
            key=lambda x: x[1].get("revenue", 0),
            reverse=True,
        ):
            funnel_rows.append({
                "Source": source,
                "Leads": data.get("leads", 0),
                "Clients": data.get("clients", 0),
                "Contracts": data.get("contracts", 0),
                "Revenue": f"${data.get('revenue', 0):,.0f}",
                "Conv %": f"{data.get('conversion_rate', 0):.1f}%",
            })

        if funnel_rows:
            st.dataframe(
                pd.DataFrame(funnel_rows),
                use_container_width=True,
                hide_index=True,
            )

    with attr_right:
        st.markdown("**Revenue by Source**")

        revenue_by_source = attribution.get("revenue_by_source", {})
        if revenue_by_source:
            rev_df = pd.DataFrame(
                [{"Source": src, "Revenue": amt} for src, amt in revenue_by_source.items()]
            )
            st.bar_chart(rev_df.set_index("Source"), horizontal=True)
        else:
            st.info("No revenue data by source yet.")

    # ── Rep Performance + Time to Close ──────────────────────────────────────
    rep_col, ttc_col = st.columns([3, 2])

    with rep_col:
        reps = attribution.get("rep_performance", [])
        if reps:
            st.markdown("**Sales Rep Performance**")
            rep_rows = []
            for r in reps:
                rep_rows.append({
                    "Rep": r.get("rep", "Unknown"),
                    "Leads": r.get("leads", 0),
                    "Clients": r.get("clients", 0),
                    "Contracts": r.get("contracts", 0),
                    "Revenue": f"${r.get('revenue', 0):,.0f}",
                    "Avg Deal": f"${r.get('avg_deal_size', 0):,.0f}",
                })
            st.dataframe(
                pd.DataFrame(rep_rows),
                use_container_width=True,
                hide_index=True,
            )

    with ttc_col:
        ttc = attribution.get("time_to_close", {})
        if ttc:
            st.markdown("**Avg Days to Close**")
            for source, days in sorted(ttc.items(), key=lambda x: x[1]):
                speed = "fast" if days <= 14 else "medium" if days <= 30 else "slow"
                icon = {
                    "fast": "\u26a1",
                    "medium": "\u23f3",
                    "slow": "\U0001f422",
                }.get(speed, "")
                st.markdown(f"{icon} **{source}**: {days:.0f} days")

        # Top source callout
        top = attribution.get("top_source", "N/A")
        totals = attribution.get("totals", {})
        if top != "N/A" and totals.get("revenue", 0) > 0:
            st.markdown("---")
            st.markdown(
                f'<div class="alert-card alert-info">'
                f'<strong>Top Source:</strong> {top}<br>'
                f'{totals.get("leads", 0)} leads \u2192 '
                f'{totals.get("clients", 0)} clients \u2192 '
                f'${totals.get("revenue", 0):,.0f} revenue'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: RECENT ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

act_col, sms_col = st.columns([2, 1])

with act_col:
    st.markdown("### Recent Activity")

    recent_activity = briefing.get("recent_activity", [])
    if recent_activity:
        activity_rows = []
        for entry in recent_activity:
            created = entry.get("created_at", "")
            time_str = ""
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    time_str = dt.strftime("%b %d, %I:%M %p")
                except (ValueError, TypeError):
                    time_str = created[:16]

            activity_rows.append({
                "Time": time_str,
                "Action": entry.get("action", ""),
                "Type": entry.get("entity_type", ""),
            })
        st.dataframe(
            pd.DataFrame(activity_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No recent activity to display.")

with sms_col:
    st.markdown("### SMS Preview")
    try:
        sms_text = format_briefing_sms(briefing)
        st.code(sms_text, language=None)
    except Exception as e:
        st.error(f"Could not format SMS preview: {e}")

    # SMS activity
    sms_summary = briefing.get("sms_summary", {})
    recent_sms = sms_summary.get("recent_count", 0)
    if recent_sms > 0:
        st.caption(f"{recent_sms} SMS messages sent in the last 24 hours")


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

briefing_time = st.session_state.get("briefing_time")
if briefing_time:
    display_time = briefing_time.strftime("%B %d, %Y at %I:%M %p")
    st.caption(f"Dashboard loaded at {display_time}")
elif briefing.get("generated_at"):
    try:
        dt = datetime.fromisoformat(briefing["generated_at"])
        display_time = dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        display_time = briefing["generated_at"]
    st.caption(f"Generated at {display_time}")
