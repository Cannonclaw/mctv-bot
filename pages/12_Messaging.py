# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""SMS Messaging dashboard — compose, send templates, manage opt-ins, view history."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.sms_service import (
    is_configured, send_sms, send_template, get_templates,
    format_phone, set_consent, check_consent, get_all_consent,
    get_message_history,
)
from services.config_service import load_config, get_team_first_names

st.set_page_config(page_title="Messaging - MCTV Bot", page_icon="\U0001F4F1", layout="wide")

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## SMS Messaging")
st.caption("Send texts to leads, clients, and host venues. All messages require opt-in consent.")

# ── Config check ─────────────────────────────────────────────────────────────

if not is_configured():
    st.warning("Twilio SMS is not configured yet.")
    st.markdown(
        "To enable text messaging, add these environment variables to your "
        "`.env` file or Render dashboard:"
    )
    st.code(
        "TWILIO_ACCOUNT_SID=your_account_sid\n"
        "TWILIO_AUTH_TOKEN=your_auth_token\n"
        "TWILIO_PHONE_NUMBER=+1XXXXXXXXXX",
        language=None,
    )
    st.info(
        "Sign up at twilio.com/try-twilio for a free trial. "
        "You'll also need to register for A2P 10DLC to send to US numbers at scale."
    )
    # Don't stop — still allow opt-in management and history viewing


# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_compose, tab_templates, tab_consent, tab_history = st.tabs([
    "Compose", "Quick Templates", "Opt-In Management", "Message History"
])


# ── TAB: Compose ─────────────────────────────────────────────────────────────

with tab_compose:
    st.markdown("### Send a Text")

    # Try to load contacts from leads and clients for quick selection
    contacts = []
    try:
        from services.leads_service import get_all_leads
        for lead in get_all_leads():
            phone = lead.get("contact_phone", "")
            if phone:
                contacts.append({
                    "label": f"{lead.get('business_name', '')} — {lead.get('contact_name', '')}",
                    "phone": phone,
                    "name": lead.get("contact_name", ""),
                })
    except Exception:
        pass

    try:
        from services.portal_service import get_all_clients
        for client in get_all_clients():
            phone = client.get("contact_phone", "")
            if phone:
                contacts.append({
                    "label": f"{client.get('business_name', '')} — {client.get('contact_name', '')} (Client)",
                    "phone": phone,
                    "name": client.get("contact_name", ""),
                })
    except Exception:
        pass

    # Contact picker or manual entry
    compose_col1, compose_col2 = st.columns([3, 2])

    with compose_col1:
        use_contact = st.toggle("Pick from contacts", value=bool(contacts))

        if use_contact and contacts:
            contact_options = [""] + [c["label"] for c in contacts]
            selected = st.selectbox("Select Contact", contact_options, key="compose_contact")
            if selected:
                match = next((c for c in contacts if c["label"] == selected), None)
                phone_input = match["phone"] if match else ""
            else:
                phone_input = ""
        else:
            phone_input = st.text_input("Phone Number", placeholder="(662) 555-1234",
                                        key="compose_phone")

    with compose_col2:
        formatted = format_phone(phone_input) if phone_input else ""
        if formatted:
            has_consent = check_consent(formatted)
            if has_consent:
                st.success(f"Opted in: {formatted}")
            else:
                st.warning(f"No consent: {formatted}")
                if st.button("Opt In This Number", key="quick_optin"):
                    name = ""
                    if use_contact and contacts:
                        match = next((c for c in contacts if c["phone"] == phone_input), None)
                        name = match["name"] if match else ""
                    set_consent(formatted, True, name)
                    st.success("Opted in!")
                    st.rerun()
        elif phone_input:
            st.error("Invalid phone number format")

    message = st.text_area("Message", placeholder="Type your message here...",
                           height=120, key="compose_message")

    char_count = len(message) if message else 0
    segments = (char_count // 160) + 1 if char_count > 0 else 0
    st.caption(f"{char_count} characters ({segments} SMS segment{'s' if segments != 1 else ''})")

    # Warn if phone doesn't look valid (non-blocking)
    import re
    _phone_digits = re.sub(r'\D', '', phone_input) if phone_input else ""
    if phone_input and len(_phone_digits) < 10:
        st.warning("Please enter a valid phone number (at least 10 digits)")

    if st.button("Send Message", type="primary", width='stretch',
                 disabled=not (formatted and message)):
        with st.spinner("Sending..."):
            result = send_sms(formatted, message)
            if result["success"]:
                st.success(f"Message sent to {formatted}")
                st.balloons()
            else:
                st.error(f"Failed: {result['error']}")


# ── TAB: Quick Templates ────────────────────────────────────────────────────

with tab_templates:
    st.markdown("### Quick Send Templates")
    st.caption("Select a template, fill in the blanks, and send.")

    templates = get_templates()
    # Exclude 'custom' from template picker (that's what Compose is for)
    template_options = {k: v for k, v in templates.items() if k != "custom"}

    template_key = st.selectbox(
        "Template",
        list(template_options.keys()),
        format_func=lambda k: template_options[k]["name"],
        key="template_picker",
    )

    if template_key:
        template = template_options[template_key]
        st.markdown(f"**Preview:** _{template['body']}_")
        st.divider()

        # Phone number input
        tmpl_col1, tmpl_col2 = st.columns(2)

        with tmpl_col1:
            if contacts:
                tmpl_contact_options = [""] + [c["label"] for c in contacts]
                tmpl_selected = st.selectbox("Contact", tmpl_contact_options,
                                             key="tmpl_contact")
                if tmpl_selected:
                    tmpl_match = next((c for c in contacts if c["label"] == tmpl_selected), None)
                    tmpl_phone = tmpl_match["phone"] if tmpl_match else ""
                else:
                    tmpl_phone = ""
            else:
                tmpl_phone = st.text_input("Phone Number", key="tmpl_phone_input")

        with tmpl_col2:
            tmpl_formatted = format_phone(tmpl_phone) if tmpl_phone else ""
            if tmpl_formatted:
                if check_consent(tmpl_formatted):
                    st.success(f"Opted in: {tmpl_formatted}")
                else:
                    st.warning("No consent on file")

        # Template variables
        st.markdown("**Fill in template variables:**")
        variables = {}
        var_cols = st.columns(min(len(template["variables"]), 3))
        for i, var in enumerate(template["variables"]):
            col_idx = i % min(len(template["variables"]), 3)
            # Pre-fill common variables
            default = ""
            if var == "rep_name":
                _msg_cfg = load_config()
                _msg_team = get_team_first_names(_msg_cfg)
                default = _msg_team[0] if _msg_team else ""
            elif var == "contact_name" and contacts and tmpl_phone:
                match = next((c for c in contacts if c["phone"] == tmpl_phone), None)
                default = match["name"] if match else ""
            elif var == "business_name" and contacts and tmpl_phone:
                match = next((c for c in contacts if c["phone"] == tmpl_phone), None)
                if match:
                    default = match["label"].split(" — ")[0]

            with var_cols[col_idx]:
                variables[var] = st.text_input(
                    var.replace("_", " ").title(),
                    value=default,
                    key=f"tmpl_var_{var}",
                )

        # Preview filled template
        try:
            preview = template["body"].format(**variables)
            st.markdown(f"**Message preview:**")
            st.info(preview)
        except KeyError:
            preview = ""

        all_filled = all(variables.values())
        if st.button("Send Template", type="primary", width='stretch',
                     disabled=not (tmpl_formatted and all_filled)):
            with st.spinner("Sending..."):
                result = send_template(template_key, tmpl_phone, variables)
                if result["success"]:
                    st.success(f"Sent '{template['name']}' to {tmpl_formatted}")
                    st.balloons()
                else:
                    st.error(f"Failed: {result['error']}")


# ── TAB: Opt-In Management ──────────────────────────────────────────────────

with tab_consent:
    st.markdown("### Opt-In / Opt-Out Management")
    st.caption(
        "TCPA requires documented consent before texting anyone. "
        "Add contacts here when they verbally or digitally consent to receive texts."
    )

    # Add new consent
    with st.form("add_consent"):
        consent_col1, consent_col2, consent_col3 = st.columns([2, 2, 1])
        with consent_col1:
            consent_phone = st.text_input("Phone Number", placeholder="(662) 555-1234")
        with consent_col2:
            consent_name = st.text_input("Name", placeholder="Joe Smith")
        with consent_col3:
            consent_action = st.selectbox("Action", ["Opt In", "Opt Out"])

        if st.form_submit_button("Save Consent", type="primary", width='stretch'):
            formatted_consent = format_phone(consent_phone)
            if formatted_consent:
                opted_in = consent_action == "Opt In"
                set_consent(formatted_consent, opted_in, consent_name)
                status = "opted in" if opted_in else "opted out"
                st.success(f"{consent_name or formatted_consent} {status}")
                st.rerun()
            else:
                st.error("Invalid phone number format")

    # Bulk opt-in from contacts
    st.divider()
    if contacts:
        st.markdown("**Quick opt-in from existing contacts:**")
        consent_records = get_all_consent()
        consented_phones = {r.get("phone", "") for r in consent_records if r.get("opted_in")}

        unconsented = [
            c for c in contacts
            if format_phone(c["phone"]) and format_phone(c["phone"]) not in consented_phones
        ]

        if unconsented:
            st.caption(f"{len(unconsented)} contacts without consent on file")
            for i, c in enumerate(unconsented[:20]):
                btn_col1, btn_col2 = st.columns([4, 1])
                with btn_col1:
                    st.text(f"{c['label']} — {c['phone']}")
                with btn_col2:
                    if st.button("Opt In", key=f"bulk_optin_{i}_{c['phone']}",
                                 width='stretch'):
                        set_consent(format_phone(c["phone"]), True, c["name"])
                        st.rerun()
        else:
            st.success("All contacts with phone numbers have consent on file.")

    # Current consent list
    st.divider()
    st.markdown("**Current Consent Records:**")
    consent_list = get_all_consent()
    if consent_list:
        for record in consent_list:
            status_icon = "\u2705" if record.get("opted_in") else "\u274C"
            name = record.get("name", "")
            phone = record.get("phone", "")
            updated = record.get("updated_at", "")[:16]
            st.text(f"{status_icon}  {name or 'Unknown'} — {phone}  (updated {updated})")
    else:
        st.info("No consent records yet. Add contacts above to start.")


# ── TAB: Message History ────────────────────────────────────────────────────

with tab_history:
    st.markdown("### Message History")

    history = get_message_history(limit=100)

    if not history:
        st.info("No messages sent yet.")
    else:
        st.caption(f"Showing {len(history)} recent messages")

        for msg in history:
            sent_at = msg.get("sent_at", "")[:16]
            to = msg.get("to", "")
            body = msg.get("body", "")
            template_name = msg.get("template", "")
            status = msg.get("status", "sent")
            error = msg.get("error", "")

            status_icon = {
                "sent": "\u2705",
                "failed": "\u274C",
                "skipped": "\u23ED\uFE0F",
            }.get(status, "\u2753")

            label = f"{status_icon} {sent_at} — {to}"
            if template_name:
                tmpl = get_templates().get(template_name, {})
                label += f" ({tmpl.get('name', template_name)})"

            with st.expander(label, expanded=False):
                st.text(body)
                if error:
                    st.error(f"Error: {error}")
