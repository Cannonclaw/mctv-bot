# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host Acquisition Pipeline — track venues we're trying to sign as hosts.

Reuses the existing pipeline_opportunities table (deal_type='host') so the
plumbing — activity log, nurture sequences, assigned-rep tracking — comes for
free. Stages are host-specific: identified -> first_visit -> pitched ->
agreement_sent -> install_scheduled -> live (or lost).
"""

import sys
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import (
    delete_row, insert_row, query_table, update_row,
)
from services.config_service import load_config, get_team_first_names

st.set_page_config(
    page_title="Host Pipeline - MCTV Bot",
    page_icon="\U0001F3E2",
    layout="wide",
)

if not check_password():
    st.stop()

st.markdown("## Host Acquisition Pipeline")
st.caption(
    "Venues we're trying to sign as MCTV hosts. Move them through the stages "
    "as you progress from cold outreach to a live screen."
)


HOST_STAGES = [
    ("identified", "Identified"),
    ("first_visit", "First Visit"),
    ("pitched", "Pitched"),
    ("agreement_sent", "Agreement Sent"),
    ("install_scheduled", "Install Scheduled"),
    ("live", "Live"),
    ("lost", "Lost"),
]
STAGE_KEYS = [s[0] for s in HOST_STAGES]
STAGE_LABEL = dict(HOST_STAGES)

STAGE_COLORS = {
    "identified": "#888888",
    "first_visit": "#5F9EA0",
    "pitched": "#E89E3C",
    "agreement_sent": "#9370DB",
    "install_scheduled": "#4682B4",
    "live": "#2E8B57",
    "lost": "#722F37",
}


# ── Load opportunities ───────────────────────────────────────────────────────

opps = query_table(
    "pipeline_opportunities",
    filters={"deal_type": "host"},
    order="-updated_at",
) or []

cfg = load_config()
team_first = get_team_first_names(cfg) or ["Creed", "Mary Michael", "Swayze"]


# ── Headline metrics ────────────────────────────────────────────────────────

def _by_stage(stage: str) -> list:
    return [o for o in opps if o.get("stage") == stage]


m1, m2, m3, m4 = st.columns(4)
m1.metric("Total in pipeline", len(opps))
m2.metric("Live (signed hosts)", len(_by_stage("live")))
m3.metric("In progress", sum(len(_by_stage(s)) for s in
                              ("identified", "first_visit", "pitched",
                               "agreement_sent", "install_scheduled")))
m4.metric("Lost", len(_by_stage("lost")))

st.divider()


# ── Add new host prospect ───────────────────────────────────────────────────

with st.expander("Add a host prospect", expanded=False):
    with st.form("add_host_opp"):
        c1, c2 = st.columns(2)
        new_business = c1.text_input("Venue / Business name *")
        new_contact = c2.text_input("Contact name")
        c3, c4 = st.columns(2)
        new_email = c3.text_input("Email")
        new_phone = c4.text_input("Phone")
        c5, c6, c7 = st.columns(3)
        new_city = c5.text_input("City", value="Oxford")
        new_industry = c6.text_input("Industry / Category",
                                      placeholder="Bar, Salon, Gym, etc.")
        new_rep = c7.selectbox("Assigned rep", team_first)

        new_notes = st.text_area("Notes (location specifics, decision maker, etc.)",
                                  height=100)

        submit = st.form_submit_button("Add to pipeline", type="primary")

    if submit:
        if not new_business:
            st.error("Venue name is required.")
        else:
            row = insert_row("pipeline_opportunities", {
                "deal_type": "host",
                "business_name": new_business,
                "contact_name": new_contact or None,
                "contact_email": new_email or None,
                "contact_phone": new_phone or None,
                "city": new_city or None,
                "industry": new_industry or None,
                "stage": "identified",
                "source": "manual",
                "assigned_rep": new_rep,
                "notes": new_notes or None,
                "probability": 10,
            })
            if row:
                st.success(f"Added {new_business} to the host pipeline.")
                st.rerun()
            else:
                st.error("Could not add. Check Supabase configuration.")

st.divider()


# ── Kanban-style stage view ──────────────────────────────────────────────────

st.markdown("### Pipeline by Stage")
cols = st.columns(len(HOST_STAGES))
for i, (stage_key, stage_label) in enumerate(HOST_STAGES):
    with cols[i]:
        items = _by_stage(stage_key)
        st.markdown(
            f"<div style='border-top:4px solid {STAGE_COLORS[stage_key]}; "
            f"padding-top:0.4rem;'><b>{stage_label}</b><br>"
            f"<span style='color:#888;font-size:0.85rem;'>{len(items)} venue(s)</span></div>",
            unsafe_allow_html=True,
        )
        for o in items[:6]:
            st.markdown(
                f"<div style='background:#f7f7f7; border-radius:6px; "
                f"padding:0.4rem 0.6rem; margin:0.3rem 0; font-size:0.85rem;'>"
                f"<b>{o.get('business_name', '')}</b><br>"
                f"<span style='color:#666;'>{o.get('city', '')} · "
                f"{o.get('assigned_rep', '')}</span></div>",
                unsafe_allow_html=True,
            )

st.divider()


# ── Detail editor ────────────────────────────────────────────────────────────

st.markdown("### Manage a Venue")

if not opps:
    st.info("No host prospects yet — add one above.")
    st.stop()

opp_index = {o["id"]: o for o in opps}
opp_label = {o["id"]: f"{o.get('business_name', '?')} — {STAGE_LABEL.get(o.get('stage'), o.get('stage'))}"
             for o in opps}
selected_id = st.selectbox(
    "Pick a venue",
    options=list(opp_index.keys()),
    format_func=lambda k: opp_label.get(k, k),
)
opp = opp_index[selected_id]

dc1, dc2, dc3 = st.columns(3)
new_stage = dc1.selectbox("Stage", STAGE_KEYS,
                           index=STAGE_KEYS.index(opp.get("stage", "identified"))
                                 if opp.get("stage") in STAGE_KEYS else 0,
                           format_func=lambda k: STAGE_LABEL[k])
new_rep_sel = dc2.selectbox("Assigned rep", team_first,
                             index=team_first.index(opp.get("assigned_rep"))
                                   if opp.get("assigned_rep") in team_first else 0)
new_prob = dc3.number_input("Win probability (%)",
                              min_value=0, max_value=100,
                              value=int(opp.get("probability", 10) or 10),
                              step=5)

dc4, dc5 = st.columns(2)
next_action = dc4.text_input("Next action", value=opp.get("next_action") or "")
nad = opp.get("next_action_date") or date.today().isoformat()
try:
    nad_default = date.fromisoformat(nad)
except (ValueError, TypeError):
    nad_default = date.today()
next_action_date = dc5.date_input("Next action date", value=nad_default)

new_notes_edit = st.text_area("Notes", value=opp.get("notes") or "", height=120)

save_cols = st.columns([1, 1, 4])
if save_cols[0].button("Save changes", type="primary", width="stretch"):
    update_row("pipeline_opportunities", selected_id, {
        "stage": new_stage,
        "assigned_rep": new_rep_sel,
        "probability": new_prob,
        "next_action": next_action or None,
        "next_action_date": next_action_date.isoformat(),
        "notes": new_notes_edit or None,
    })
    st.success("Saved.")
    st.rerun()

if save_cols[1].button("Delete venue", width="stretch"):
    if st.session_state.get(f"confirm_del_host_{selected_id}"):
        delete_row("pipeline_opportunities", selected_id)
        st.success("Removed from pipeline.")
        st.session_state.pop(f"confirm_del_host_{selected_id}", None)
        st.rerun()
    else:
        st.session_state[f"confirm_del_host_{selected_id}"] = True
        st.warning("Click Delete again to confirm.")
