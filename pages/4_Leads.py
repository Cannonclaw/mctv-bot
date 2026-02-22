"""Internal leads dashboard — view and manage client intake submissions."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.leads_service import get_all_leads, update_lead_status

st.set_page_config(page_title="Leads - MCTV Bot", page_icon="\U0001F4CB", layout="wide")

if not check_password():
    st.stop()

st.markdown("## Incoming Leads")
st.caption("Client intake submissions from the public form. Click a lead to see details and generate a proposal.")

leads = get_all_leads()

if not leads:
    st.info("No leads yet. Share your intake form link with prospects to start receiving submissions.")
    st.code("https://mctv-bot.onrender.com/Intake", language=None)
    st.stop()

# ── STATS ────────────────────────────────────────────────────────────────────
new_count = sum(1 for l in leads if l.get("status") == "new")
contacted_count = sum(1 for l in leads if l.get("status") == "contacted")
proposal_count = sum(1 for l in leads if l.get("status") == "proposal_sent")
closed_count = sum(1 for l in leads if l.get("status") == "closed")

c1, c2, c3, c4 = st.columns(4)
c1.metric("New", new_count)
c2.metric("Contacted", contacted_count)
c3.metric("Proposal Sent", proposal_count)
c4.metric("Closed", closed_count)

st.divider()

# ── FILTER ───────────────────────────────────────────────────────────────────
filter_status = st.selectbox(
    "Filter by Status",
    ["All", "New", "Contacted", "Proposal Sent", "Closed"],
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

# ── LEAD CARDS ───────────────────────────────────────────────────────────────
for lead in leads:
    if filter_val and lead.get("status") != filter_val:
        continue

    status = lead.get("status", "new")
    status_emoji = {
        "new": "\U0001F7E2",       # green circle
        "contacted": "\U0001F7E1",  # yellow circle
        "proposal_sent": "\U0001F535",  # blue circle
        "closed": "\u2705",         # checkmark
    }.get(status, "\u26AA")

    interest = lead.get("interest_level", "")
    interest_tag = ""
    if "Ready" in interest:
        interest_tag = " \U0001F525"  # fire for ready-to-go leads
    elif "Interested" in interest:
        interest_tag = " \u2B50"  # star for interested

    with st.expander(
        f"{status_emoji} **{lead.get('business_name', 'Unknown')}** — "
        f"{lead.get('contact_name', '')} | {lead.get('city', '')} | "
        f"{lead.get('industry', '')}{interest_tag}",
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

        # ── Actions ──────────────────────────────────────────────────────
        st.divider()
        action_cols = st.columns(4)

        lead_id = lead.get("id", "")

        with action_cols[0]:
            if st.button("Mark Contacted", key=f"contacted_{lead_id}", use_container_width=True):
                update_lead_status(lead_id, "contacted")
                st.rerun()

        with action_cols[1]:
            if st.button("Proposal Sent", key=f"proposal_{lead_id}", use_container_width=True):
                update_lead_status(lead_id, "proposal_sent")
                st.rerun()

        with action_cols[2]:
            if st.button("Closed / Won", key=f"closed_{lead_id}", use_container_width=True):
                update_lead_status(lead_id, "closed")
                st.rerun()

        with action_cols[3]:
            st.page_link(
                "pages/1_Proposals.py",
                label="Generate Proposal",
                icon="\U0001F4DD",
                use_container_width=True,
            )
