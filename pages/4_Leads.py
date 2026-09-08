# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Internal leads dashboard — view and manage client intake submissions."""

import streamlit as st
import sys
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.leads_service import (
    get_all_leads,
    update_lead_status,
    update_lead,
    calculate_lead_score,
    get_score_label,
    bulk_update_status,
    bulk_assign_rep,
    export_leads_csv,
)
from services.supabase_client import is_configured as supabase_configured
from services.portal_service import convert_lead_to_client
from services.config_service import load_config, get_team_first_names

st.set_page_config(page_title="Leads - MCTV Bot", page_icon="\U0001F4CB", layout="wide")

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## Incoming Leads")
st.caption("Client intake submissions from the public form. Click a lead to see details and generate a proposal.")

try:
    leads = get_all_leads()
except Exception:
    st.error("Unable to load leads. Please try again later.")
    leads = []

if not leads:
    st.info("No leads yet. Share your intake form link with prospects to start receiving submissions.")
    st.code("https://bot.mctvofms.com/Intake", language=None)
    st.stop()

# ── Compute scores for all leads ────────────────────────────────────────────
for lead in leads:
    lead["_score"] = calculate_lead_score(lead)

# ── STATS ────────────────────────────────────────────────────────────────────
new_count = sum(1 for l in leads if l.get("status") == "new")
contacted_count = sum(1 for l in leads if l.get("status") == "contacted")
proposal_count = sum(1 for l in leads if l.get("status") == "proposal_sent")
closed_count = sum(1 for l in leads if l.get("status") == "closed")
hot_count = sum(1 for l in leads if l["_score"] >= 70)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("New", new_count)
c2.metric("Contacted", contacted_count)
c3.metric("Proposal Sent", proposal_count)
c4.metric("Closed", closed_count)
c5.metric("Hot Leads", hot_count)

st.divider()

# ── DUE FOLLOW-UPS ──────────────────────────────────────────────────────────
_today = date.today()
_due_leads = []
for _lead in leads:
    _fu_date_str = _lead.get("follow_up_date")
    if _fu_date_str:
        try:
            _fu_date = datetime.strptime(str(_fu_date_str)[:10], "%Y-%m-%d").date()
            if _fu_date <= _today:
                _days_overdue = (_today - _fu_date).days
                _due_leads.append((_lead, _fu_date, _days_overdue))
        except (ValueError, TypeError):
            pass

if _due_leads:
    st.markdown("### ⏰ Due Follow-ups")
    for _lead_item, _fu_dt, _days in sorted(_due_leads, key=lambda x: x[2], reverse=True):
        _bname = _lead_item.get("business_name", "Unknown")
        _fu_note = _lead_item.get("follow_up_note", "")
        if _days == 0:
            _overdue_text = "**Due today**"
        elif _days == 1:
            _overdue_text = "**1 day overdue**"
        else:
            _overdue_text = f"**{_days} days overdue**"
        _note_text = f" — {_fu_note}" if _fu_note else ""
        st.warning(f"📋 **{_bname}** | {_overdue_text}{_note_text} (follow-up: {_fu_dt.strftime('%b %d, %Y')})")
    st.divider()

# ── FILTER & SORT ────────────────────────────────────────────────────────────
filter_col, sort_col = st.columns(2)

with filter_col:
    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "New", "Contacted", "Proposal Sent", "Closed"],
        index=0,
    )

with sort_col:
    sort_option = st.selectbox(
        "Sort by",
        ["Newest First", "Oldest First", "Score (High to Low)", "Score (Low to High)"],
        index=0,
    )

status_map = {
    "All": None,
    "New": "new",
    "Contacted": "contacted",
    "Proposal Sent": "proposal_sent",
    "Closed": "closed",
}
filter_val = status_map[filter_status]

# Apply sorting
if sort_option == "Score (High to Low)":
    leads = sorted(leads, key=lambda x: x["_score"], reverse=True)
elif sort_option == "Score (Low to High)":
    leads = sorted(leads, key=lambda x: x["_score"])
elif sort_option == "Oldest First":
    leads = sorted(leads, key=lambda x: x.get("submitted_at", ""))
# "Newest First" is the default order from the DB query — no re-sort needed

# ── Filter leads for display ────────────────────────────────────────────────
display_leads = [
    lead for lead in leads
    if not filter_val or lead.get("status") == filter_val
]

# ── Initialize selection state ───────────────────────────────────────────────
if "selected_leads" not in st.session_state:
    st.session_state["selected_leads"] = set()

# Clean up stale selections (IDs that are no longer in the displayed list)
visible_ids = {lead.get("id", "") for lead in display_leads}
st.session_state["selected_leads"] &= visible_ids

# ── BULK ACTIONS BAR ─────────────────────────────────────────────────────────
selected = st.session_state["selected_leads"]

if selected:
    st.markdown("---")
    st.markdown(f"**{len(selected)} lead(s) selected**")

    bulk_cols = st.columns([2, 3, 2, 2])

    with bulk_cols[0]:
        if st.button("Mark All as Contacted", key="bulk_contacted", width='stretch'):
            try:
                bulk_update_status(list(selected), "contacted")
                st.session_state["selected_leads"] = set()
                st.success(f"{len(selected)} lead(s) marked as Contacted")
                st.rerun()
            except Exception:
                st.error("Failed to update leads")

    with bulk_cols[1]:
        _cfg = load_config()
        rep_options = [""] + get_team_first_names(_cfg)
        bulk_rep = st.selectbox("Assign Rep", rep_options, key="bulk_rep_select", label_visibility="collapsed")

    with bulk_cols[2]:
        if st.button("Apply Rep", key="bulk_apply_rep", width='stretch'):
            if bulk_rep:
                try:
                    bulk_assign_rep(list(selected), bulk_rep)
                    st.session_state["selected_leads"] = set()
                    st.success(f"Assigned **{bulk_rep}** to {len(selected)} lead(s)")
                    st.rerun()
                except Exception:
                    st.error("Failed to assign rep")
            else:
                st.warning("Select a rep first")

    with bulk_cols[3]:
        selected_lead_data = [l for l in display_leads if l.get("id", "") in selected]
        csv_data = export_leads_csv(selected_lead_data)
        st.download_button(
            "Export Selected",
            data=csv_data,
            file_name="mctv_leads_export.csv",
            mime="text/csv",
            key="bulk_export",
            width='stretch',
        )

    st.markdown("---")

# ── LEAD CARDS ───────────────────────────────────────────────────────────────
for lead in display_leads:
    status = lead.get("status", "new")
    lead_id = lead.get("id", "")
    score = lead["_score"]
    score_label, score_color = get_score_label(score)

    status_emoji = {
        "new": "\U0001F7E2",       # green circle
        "contacted": "\U0001F7E1",  # yellow circle
        "proposal_sent": "\U0001F535",  # blue circle
        "closed": "\u2705",         # checkmark
    }.get(status, "\u26AA")

    # Score badge emoji
    score_emoji = {
        "Hot": "\U0001F525",   # fire
        "Warm": "\u2B50",      # star
        "Cold": "\u2744\uFE0F",  # snowflake
    }.get(score_label, "")

    # ── Card header row: checkbox + score badge + business info ──────────
    header_cols = st.columns([0.5, 9, 2.5])

    with header_cols[0]:
        is_selected = st.checkbox(
            "sel",
            value=(lead_id in st.session_state["selected_leads"]),
            key=f"sel_{lead_id}",
            label_visibility="collapsed",
        )
        if is_selected:
            st.session_state["selected_leads"].add(lead_id)
        else:
            st.session_state["selected_leads"].discard(lead_id)

    with header_cols[2]:
        st.markdown(
            f"<span style='background-color:{score_color};color:white;padding:2px 10px;"
            f"border-radius:12px;font-size:0.85em;font-weight:600;'>"
            f"{score_emoji} {score_label} ({score})</span>",
            unsafe_allow_html=True,
        )

    # ── Prominent Convert to Client button for hot / proposal_sent leads ──
    show_prominent_convert = (
        supabase_configured()
        and status not in ("closed",)
        and (status == "proposal_sent" or score >= 70)
    )

    with header_cols[1]:
        business_name = lead.get("business_name", "Unknown")
        contact_name = lead.get("contact_name", "")
        city = lead.get("city", "")
        industry = lead.get("industry", "")
        assigned_rep = lead.get("assigned_rep", "")
        rep_text = f" | \U0001F464 {assigned_rep}" if assigned_rep else ""
        st.markdown(
            f"{status_emoji} **{business_name}** — "
            f"{contact_name} | {city} | {industry}{rep_text}"
        )

    if show_prominent_convert:
        convert_cols = st.columns([8, 2])
        with convert_cols[1]:
            if st.button(
                "Convert to Client",
                key=f"prominent_convert_{lead_id}",
                type="primary",
                width='stretch',
            ):
                st.session_state[f"show_convert_{lead_id}"] = True

    with st.expander(
        f"View details — {business_name}",
        expanded=(status == "new"),
    ):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Contact Info**")
            st.text(f"Name: {lead.get('contact_name', 'N/A')}")
            st.text(f"Email: {lead.get('contact_email', 'N/A')}")
            st.text(f"Phone: {lead.get('contact_phone', 'N/A')}")
            st.text(f"City: {lead.get('city', 'N/A')}")
            st.text(f"Industry: {lead.get('industry', 'N/A')}")

        with col2:
            st.markdown("**Submission Details**")
            st.text(f"Interest: {lead.get('interest_level', 'N/A')}")
            st.text(f"How Heard: {lead.get('how_heard', 'N/A')}")
            st.text(f"Submitted: {lead.get('submitted_at', 'N/A')[:16]}")
            st.text(f"Lead Score: {score} ({score_label})")
            st.text(f"Assigned Rep: {lead.get('assigned_rep') or 'Unassigned'}")

            # Logo preview
            logo_file = lead.get("logo_file")
            if logo_file:
                logo_path = Path(__file__).parent.parent / "data" / "logos" / logo_file
                if logo_path.exists():
                    st.image(str(logo_path), width=120, caption="Client Logo")

        if lead.get("goals"):
            st.markdown("**Goals:**")
            st.text(lead.get("goals"))

        if lead.get("additional_notes"):
            st.markdown("**Notes:**")
            st.text(lead.get("additional_notes"))

        # ── Follow-up Reminder ───────────────────────────────────────────
        st.divider()
        st.markdown("**📅 Follow-up Reminder**")

        _existing_fu_date = lead.get("follow_up_date")
        _existing_fu_note = lead.get("follow_up_note", "")

        # Show existing follow-up info
        if _existing_fu_date:
            try:
                _parsed_fu = datetime.strptime(str(_existing_fu_date)[:10], "%Y-%m-%d").date()
                _days_until = (_parsed_fu - _today).days
                if _days_until < 0:
                    st.error(f"Follow-up was {abs(_days_until)} day(s) ago ({_parsed_fu.strftime('%b %d, %Y')}): {_existing_fu_note}")
                elif _days_until == 0:
                    st.warning(f"Follow-up due today: {_existing_fu_note}")
                else:
                    st.info(f"Follow-up in {_days_until} day(s) ({_parsed_fu.strftime('%b %d, %Y')}): {_existing_fu_note}")
            except (ValueError, TypeError):
                pass

        fu_col1, fu_col2, fu_col3 = st.columns([2, 4, 2])
        with fu_col1:
            fu_date = st.date_input(
                "Follow-up date",
                value=None,
                key=f"fu_date_{lead_id}",
                min_value=_today,
            )
        with fu_col2:
            fu_note = st.text_input(
                "Follow-up note",
                placeholder="e.g., Call about pricing",
                key=f"fu_note_{lead_id}",
            )
        with fu_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Save Follow-up", key=f"save_fu_{lead_id}",
                         width='stretch', type="primary"):
                if fu_date:
                    try:
                        update_lead(lead_id, {
                            "follow_up_date": fu_date.isoformat(),
                            "follow_up_note": fu_note or "",
                        })
                        st.success(f"Follow-up set for {fu_date.strftime('%b %d, %Y')}")
                        st.rerun()
                    except Exception:
                        st.error("Failed to save follow-up")
                else:
                    st.warning("Please select a follow-up date")

        # ── Actions ──────────────────────────────────────────────────────
        st.divider()
        action_cols = st.columns(5)

        with action_cols[0]:
            if st.button("Mark Contacted", key=f"contacted_{lead_id}", width='stretch'):
                try:
                    update_lead_status(lead_id, "contacted")
                    st.success("Lead status updated to 'Contacted'")
                    st.rerun()
                except Exception:
                    st.error("Failed to update lead status")

        with action_cols[1]:
            if st.button("Proposal Sent", key=f"proposal_{lead_id}", width='stretch'):
                try:
                    update_lead_status(lead_id, "proposal_sent")
                    st.success("Lead status updated to 'Proposal Sent'")
                    st.rerun()
                except Exception:
                    st.error("Failed to update lead status")

        with action_cols[2]:
            if st.button("Closed / Won", key=f"closed_{lead_id}", width='stretch'):
                try:
                    update_lead_status(lead_id, "closed")
                    st.success("Lead status updated to 'Closed'")
                    st.rerun()
                except Exception:
                    st.error("Failed to update lead status")

        with action_cols[3]:
            st.page_link(
                "pages/1_Proposals.py",
                label="Generate Proposal",
                icon="\U0001F4DD",
                width='stretch',
            )

        with action_cols[4]:
            if supabase_configured():
                if st.button("Convert to Client", key=f"convert_{lead_id}",
                             width='stretch', type="primary"):
                    st.session_state[f"show_convert_{lead_id}"] = True
            else:
                st.button("Convert to Client", key=f"convert_{lead_id}",
                          width='stretch', disabled=True,
                          help="Configure Supabase to enable client management")

        # ── Convert to Client form (shown when clicked) ──────────────
        if st.session_state.get(f"show_convert_{lead_id}"):
            st.markdown("---")
            st.markdown("**Convert to Client**")
            st.caption("This will create a client record from this lead's info.")

            conv_col1, conv_col2 = st.columns(2)
            with conv_col1:
                conv_type = st.selectbox(
                    "Client Type",
                    ["Advertiser", "Host"],
                    key=f"conv_type_{lead_id}",
                )
            with conv_col2:
                _cfg = load_config()
                conv_rep = st.selectbox(
                    "Assign Rep",
                    [""] + get_team_first_names(_cfg),
                    key=f"conv_rep_{lead_id}",
                )

            conv_btn1, conv_btn2 = st.columns(2)
            with conv_btn1:
                if st.button("Create Client", key=f"do_convert_{lead_id}",
                             type="primary", width='stretch'):
                    with st.spinner("Converting lead to client..."):
                        result = convert_lead_to_client(
                            lead=lead,
                            client_type=conv_type.lower(),
                            assigned_rep=conv_rep,
                        )
                        if result:
                            update_lead_status(lead_id, "closed")
                            st.success(
                                f"**{lead.get('business_name', '')}** converted to client. "
                                f"Go to the Clients page to manage their account."
                            )
                            del st.session_state[f"show_convert_{lead_id}"]
                            st.rerun()
                        else:
                            st.error("Failed to convert lead. Check logs for details.")
            with conv_btn2:
                if st.button("Cancel", key=f"cancel_convert_{lead_id}",
                             width='stretch'):
                    del st.session_state[f"show_convert_{lead_id}"]
                    st.rerun()
