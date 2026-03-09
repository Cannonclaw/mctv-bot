# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Internal contract management — create, send, track, and manage contracts."""

import json
import logging
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import is_configured
from services.contract_service import (
    create_contract, get_all_contracts, get_contract, update_contract,
    delete_contract, generate_contract_document, send_contract,
    activate_contract, cancel_contract, get_contract_summary,
    get_contract_download_url, get_expiring_contracts, renew_contract,
    _days_remaining,
)
from services.portal_service import get_all_clients, get_client

st.set_page_config(page_title="Contracts - MCTV Bot", page_icon="\U0001F4DD", layout="wide")

if not check_password():
    st.stop()


# ── Load config for tiers ──────────────────────────────────────────────────

@st.cache_data
def load_config():
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()
TIERS = config.get("pricing", {}).get("elite_tiers", [])
MARKETS = list(config.get("markets", {}).keys())

# ── Supabase gate ───────────────────────────────────────────────────────────

if not is_configured():
    st.warning("Supabase is not configured yet.")
    st.markdown(
        "To use contract management, set `SUPABASE_URL`, `SUPABASE_KEY`, and "
        "`SUPABASE_SERVICE_KEY` in your environment variables."
    )
    st.stop()


# ── Page header ─────────────────────────────────────────────────────────────

st.markdown("## Contract Management")
st.caption("Create advertising contracts, generate branded PDFs, send to clients for signature, and track the lifecycle.")

# ── Summary metrics ─────────────────────────────────────────────────────────

try:
    summary = get_contract_summary()
except Exception:
    st.error("Unable to load contract summary.")
    summary = {}

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Contracts", summary.get("total", 0))
c2.metric("Drafts", summary.get("draft", 0))
c3.metric("Awaiting Signature", summary.get("awaiting_signature", 0))
c4.metric("Active", summary.get("active", 0))
c5.metric("Active MRR", f"${summary.get('active_mrr', 0):,.2f}")
_exp_count = summary.get("expiring_soon", 0)
c6.metric("Expiring Soon", _exp_count, delta=f"-{_exp_count}" if _exp_count else None,
          delta_color="inverse" if _exp_count else "off")

st.divider()

# ── Search ─────────────────────────────────────────────────────────────────
contract_search = st.text_input("🔍 Search contracts...", key="contract_search",
                                placeholder="Search by client name, contract title, or status")

# ── Tabs ────────────────────────────────────────────────────────────────────

tab_list, tab_expiring, tab_create = st.tabs([
    "All Contracts",
    f"Expiring Soon ({_exp_count})" if _exp_count else "Expiring Soon",
    "Create New Contract",
])


# ── TAB: All Contracts ──────────────────────────────────────────────────────

with tab_list:
    # Filters
    filter_col1, filter_col2 = st.columns([3, 7])
    with filter_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Draft", "Sent", "Viewed", "Signed", "Active", "Expired", "Cancelled"],
            index=0,
            key="contract_status_filter",
        )

    status_val = status_filter.lower() if status_filter != "All" else None
    try:
        contracts = get_all_contracts(status=status_val)
    except Exception:
        st.error("Unable to load contracts. Please try again later.")
        contracts = []

    # Build client name cache for search filtering
    _client_cache = {}
    for _con in contracts:
        _cid = _con.get("client_id", "")
        if _cid and _cid not in _client_cache:
            _cl = get_client(_cid)
            _client_cache[_cid] = _cl.get("business_name", "Unknown Client") if _cl else "Unknown Client"

    # Apply search filter
    if contract_search:
        _q = contract_search.strip().lower()
        contracts = [
            c for c in contracts
            if _q in (c.get("title", "") or "").lower()
            or _q in (c.get("status", "") or "").lower()
            or _q in _client_cache.get(c.get("client_id", ""), "Unknown Client").lower()
        ]

    if not contracts:
        st.info("No contracts found. Use the 'Create New Contract' tab to get started.")
    else:
        st.caption(f"Showing {len(contracts)} contract(s)")

        for contract in contracts:
            cid = contract.get("id", "")
            title = contract.get("title", "Untitled")
            cstatus = contract.get("status", "draft")
            client_id = contract.get("client_id", "")
            tier = contract.get("tier_name", "")
            rate = float(contract.get("monthly_rate", 0))
            screens = contract.get("screen_count", 0)
            term = contract.get("term_months", 0)
            has_doc = bool(contract.get("document_url"))

            # Get client name (use cache)
            client_name = _client_cache.get(client_id, "Unknown Client")

            # Status styling
            status_emoji = {
                "draft": "\u270F\uFE0F",
                "sent": "\U0001F4E8",
                "viewed": "\U0001F440",
                "signed": "\u2705",
                "active": "\U0001F7E2",
                "expired": "\u23F0",
                "cancelled": "\U0001F534",
            }.get(cstatus, "\u26AA")

            doc_badge = " \U0001F4C4" if has_doc else ""
            signed_badge = ""
            if contract.get("signed_by"):
                signed_badge = f" (signed by {contract.get('signed_by')})"

            # Expiration badge for active contracts
            exp_badge = ""
            if cstatus == "active":
                _dr = _days_remaining(contract)
                if _dr is not None and 0 <= _dr <= 30:
                    exp_badge = f" \U0001F534 **{_dr}d left**"
                elif _dr is not None and 30 < _dr <= 60:
                    exp_badge = f" \U0001F7E1 {_dr}d left"
                elif _dr is not None and 60 < _dr <= 90:
                    exp_badge = f" \U0001F7E0 {_dr}d left"

            with st.expander(
                f"{status_emoji} **{title}** — {client_name} | "
                f"${rate:,.2f}/mo | {screens} screens | {cstatus.title()}{exp_badge}{doc_badge}",
                expanded=False,
            ):
                # Contract details
                det_col1, det_col2 = st.columns(2)

                with det_col1:
                    st.markdown("**Contract Details**")
                    st.text(f"Title: {title}")
                    st.text(f"Client: {client_name}")
                    ctype_display = contract.get('contract_type', 'advertiser').replace('_', ' ').title()
                    st.text(f"Type: {ctype_display}")
                    st.text(f"Tier: {tier or 'Custom'}")
                    st.text(f"Screens: {screens}")
                    st.text(f"Monthly Rate: ${rate:,.2f}")
                    st.text(f"Term: {term} months")

                with det_col2:
                    st.markdown("**Status & Dates**")
                    st.text(f"Status: {cstatus.title()}")
                    st.text(f"Markets: {', '.join(contract.get('markets', [])) or 'N/A'}")
                    st.text(f"Start: {contract.get('start_date', 'TBD')}")
                    st.text(f"End: {contract.get('end_date', 'TBD')}")
                    st.text(f"Auto-Renew: {'Yes' if contract.get('auto_renew') else 'No'}")
                    st.text(f"Created By: {contract.get('created_by', 'N/A')}")
                    created = contract.get("created_at", "")[:16] if contract.get("created_at") else "N/A"
                    st.text(f"Created: {created}")

                # Signature info
                if contract.get("signed_by"):
                    st.markdown("**Signature Record**")
                    st.text(f"Signed By: {contract.get('signed_by')}")
                    st.text(f"Signed At: {contract.get('signed_at', 'N/A')[:19] if contract.get('signed_at') else 'N/A'}")
                    st.text(f"IP Address: {contract.get('signed_ip', 'N/A')}")

                st.divider()

                # ── Action buttons ──────────────────────────────────────
                action_cols = st.columns(6)

                with action_cols[0]:
                    # Generate / regenerate document (draft only)
                    if cstatus == "draft":
                        gen_label = "Regenerate Doc" if has_doc else "Generate Doc"
                        if st.button(gen_label, key=f"gen_{cid}",
                                     width='stretch', type="primary"):
                            with st.spinner("Generating contract document..."):
                                result = generate_contract_document(cid, config)
                                if result:
                                    st.success("Contract document generated!")
                                    st.rerun()
                                else:
                                    st.error("Failed to generate contract. Check logs.")

                with action_cols[1]:
                    # Send to client
                    if cstatus in ("draft", "sent") and has_doc:
                        if st.button("Send to Client", key=f"send_{cid}",
                                     width='stretch'):
                            with st.spinner("Sending contract..."):
                                result = send_contract(cid)
                                if result:
                                    email_ok = result.get("email_sent", False)
                                    sms_ok = result.get("sms_sent", False)
                                    if email_ok and sms_ok:
                                        st.success("Contract sent! Client notified by email + SMS. Team confirmation sent.")
                                    elif email_ok:
                                        st.success("Contract sent! Client notified by email. Team confirmation sent.")
                                    elif sms_ok:
                                        st.warning("Contract sent. SMS delivered but email failed — check client email address.")
                                    else:
                                        st.warning("Contract marked as sent but notifications failed. Check client email/phone.")
                                    st.rerun()
                                else:
                                    st.error("Failed to send contract. Check that the client exists and contract has a document.")
                    elif cstatus == "draft" and not has_doc:
                        st.button("Send to Client", key=f"send_{cid}",
                                  width='stretch', disabled=True,
                                  help="Generate the document first")

                with action_cols[2]:
                    # Activate (signed contracts only)
                    if cstatus == "signed":
                        if st.button("Activate", key=f"activate_{cid}",
                                     width='stretch', type="primary"):
                            result = activate_contract(cid)
                            if result:
                                st.success("Contract activated.")
                                st.rerun()

                # Download — check for local PDF and DOCX files
                doc_url = contract.get("document_url", "")
                local_docx = Path(doc_url) if doc_url else None
                local_pdf = local_docx.with_suffix(".pdf") if local_docx else None

                with action_cols[3]:
                    # PDF download (preferred)
                    if local_pdf and local_pdf.exists():
                        with open(local_pdf, "rb") as f:
                            st.download_button(
                                "\U0001F4C4 PDF",
                                data=f.read(),
                                file_name=local_pdf.name,
                                mime="application/pdf",
                                key=f"dl_pdf_{cid}",
                                width='stretch',
                            )
                    elif has_doc and not (local_docx and local_docx.exists()):
                        # Try Supabase Storage signed URL
                        url = get_contract_download_url(cid)
                        if url:
                            st.link_button("\U0001F4C4 Download", url=url,
                                           width='stretch')

                with action_cols[4]:
                    # DOCX download (always available if doc exists)
                    if local_docx and local_docx.exists():
                        with open(local_docx, "rb") as f:
                            st.download_button(
                                "\U0001F4DD Word",
                                data=f.read(),
                                file_name=local_docx.name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_docx_{cid}",
                                width='stretch',
                            )

                with action_cols[5]:
                    # Cancel / Delete / Renew
                    if cstatus in ("draft", "sent", "viewed"):
                        if st.button("Cancel", key=f"cancel_{cid}",
                                     width='stretch'):
                            st.session_state[f"confirm_cancel_{cid}"] = True
                    elif cstatus == "cancelled":
                        if st.button("Delete", key=f"delete_{cid}",
                                     width='stretch'):
                            st.session_state[f"confirm_delete_contract_{cid}"] = True
                    elif cstatus in ("active", "expired"):
                        if st.button("\U0001F504 Renew", key=f"renew_{cid}",
                                     width='stretch', type="primary"):
                            with st.spinner("Creating renewal contract..."):
                                renewed = renew_contract(cid)
                                if renewed:
                                    st.success(
                                        f"Renewal draft created! Go to **All Contracts** "
                                        f"to find the new draft."
                                    )
                                    st.rerun()
                                else:
                                    st.error("Failed to create renewal. Check logs.")

                # Cancel confirmation
                if st.session_state.get(f"confirm_cancel_{cid}"):
                    st.warning(f"Cancel this contract? This will notify the client if already sent.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        cancel_reason = st.text_input("Reason (optional)", key=f"cancel_reason_{cid}")
                        if st.button("Yes, Cancel Contract", key=f"yes_cancel_{cid}",
                                     width='stretch'):
                            cancel_contract(cid, reason=cancel_reason)
                            st.success("Contract cancelled.")
                            del st.session_state[f"confirm_cancel_{cid}"]
                            st.rerun()
                    with cc2:
                        if st.button("Keep Contract", key=f"no_cancel_{cid}",
                                     width='stretch'):
                            del st.session_state[f"confirm_cancel_{cid}"]
                            st.rerun()

                # Delete confirmation
                if st.session_state.get(f"confirm_delete_contract_{cid}"):
                    st.warning("Permanently delete this contract record?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, Delete", key=f"yes_del_contract_{cid}",
                                     width='stretch'):
                            delete_contract(cid)
                            st.success("Contract deleted.")
                            del st.session_state[f"confirm_delete_contract_{cid}"]
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"no_del_contract_{cid}",
                                     width='stretch'):
                            del st.session_state[f"confirm_delete_contract_{cid}"]
                            st.rerun()


# ── TAB: Expiring Soon ─────────────────────────────────────────────────────

with tab_expiring:
    st.markdown("### Contracts Expiring Soon")
    st.caption("Active contracts approaching their end date, grouped by urgency. Renew with one click.")

    try:
        expiring = get_expiring_contracts(90)
    except Exception:
        st.error("Unable to load expiring contracts.")
        expiring = []

    if not expiring:
        st.info("No active contracts are expiring within the next 90 days.")
    else:
        # Build client cache for expiring contracts
        _exp_client_cache = {}
        for _ec in expiring:
            _ecid = _ec.get("client_id", "")
            if _ecid and _ecid not in _exp_client_cache:
                _ecl = get_client(_ecid)
                _exp_client_cache[_ecid] = _ecl if _ecl else {}

        # Group by bucket
        bucket_30 = [c for c in expiring if c.get("days_remaining", 999) <= 30]
        bucket_60 = [c for c in expiring if 30 < c.get("days_remaining", 999) <= 60]
        bucket_90 = [c for c in expiring if 60 < c.get("days_remaining", 999) <= 90]

        # MRR at risk summary
        total_at_risk = sum(float(c.get("monthly_rate", 0)) for c in expiring)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total Expiring", len(expiring))
        r2.metric("Within 30 Days", len(bucket_30))
        r3.metric("Within 60 Days", len(bucket_60))
        r4.metric("MRR at Risk", f"${total_at_risk:,.0f}")

        st.divider()

        for bucket_label, bucket_data, bucket_color in [
            ("\U0001F534 Critical — Within 30 Days", bucket_30, "red"),
            ("\U0001F7E1 Warning — 31-60 Days", bucket_60, "orange"),
            ("\U0001F7E0 Watch — 61-90 Days", bucket_90, "blue"),
        ]:
            if not bucket_data:
                continue

            mrr = sum(float(c.get("monthly_rate", 0)) for c in bucket_data)
            st.markdown(f"#### {bucket_label} ({len(bucket_data)} contracts, ${mrr:,.0f}/mo)")

            for ec in bucket_data:
                ec_id = ec.get("id", "")
                ec_title = ec.get("title", "Untitled")
                ec_rate = float(ec.get("monthly_rate", 0))
                ec_days = ec.get("days_remaining", 0)
                ec_end = ec.get("end_date_calc", "TBD")
                ec_auto = ec.get("auto_renew", False)
                ec_client = _exp_client_cache.get(ec.get("client_id", ""), {})
                ec_bname = ec_client.get("business_name", "Unknown Client")

                with st.expander(
                    f"**{ec_title}** — {ec_bname} | ${ec_rate:,.0f}/mo | "
                    f"**{ec_days} days left** | Ends {ec_end} | "
                    f"{'Auto-renew' if ec_auto else 'Manual'}",
                    expanded=(ec_days <= 30),
                ):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.text(f"Client: {ec_bname}")
                        st.text(f"Contact: {ec_client.get('contact_name', 'N/A')}")
                        st.text(f"Email: {ec_client.get('contact_email', 'N/A')}")
                        st.text(f"Phone: {ec_client.get('contact_phone', 'N/A')}")
                    with ec2:
                        st.text(f"Monthly Rate: ${ec_rate:,.2f}")
                        st.text(f"Term: {ec.get('term_months', 0)} months")
                        st.text(f"End Date: {ec_end}")
                        st.text(f"Auto-Renew: {'Yes' if ec_auto else 'No'}")

                    renew_col, spacer = st.columns([1, 2])
                    with renew_col:
                        if st.button(
                            "\U0001F504 Create Renewal Draft",
                            key=f"exp_renew_{ec_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            with st.spinner("Creating renewal..."):
                                renewed = renew_contract(ec_id)
                                if renewed:
                                    st.success(
                                        f"Renewal draft created for **{ec_bname}**! "
                                        f"Check the **All Contracts** tab."
                                    )
                                    st.rerun()
                                else:
                                    st.error("Failed to create renewal.")

            st.divider()


# ── TAB: Create New Contract ────────────────────────────────────────────────

with tab_create:
    st.markdown("### Create New Contract")
    st.caption("Select a client, choose a tier, and generate a branded contract document.")

    # Get clients for dropdown
    clients = get_all_clients()
    if not clients:
        st.warning("No clients found. Add a client on the Client Management page first.")
        st.page_link("pages/8_Clients.py", label="Go to Client Management", icon="\U0001F465")
        st.stop()

    client_options = {
        f"{c.get('business_name', 'Unknown')} ({c.get('contact_name', '')})": c.get("id", "")
        for c in clients
    }

    # Load host benefit config for free screen count
    host_free_screens = config.get("pricing", {}).get("host_free_outside_screens", 10)

    with st.form("new_contract_form"):
        # Client selection
        selected_client_label = st.selectbox(
            "Client *",
            options=list(client_options.keys()),
        )
        selected_client_id = client_options.get(selected_client_label, "")

        # Contract type
        fc1, fc2 = st.columns(2)
        with fc1:
            contract_type = st.selectbox(
                "Contract Type *",
                ["Advertiser", "Host", "Host Advertising",
                 "Category Exclusivity", "Bundle", "Renewal"],
                help=(
                    "**Host Advertising** = hosts who pay for extra screens  |  "
                    "**Category Exclusivity** = no competitor ads on their screens  |  "
                    "**Bundle** = multiple brands under one contract  |  "
                    "**Renewal** = renew an existing partnership with loyalty terms"
                ),
            )
        with fc2:
            title = st.text_input(
                "Contract Title",
                placeholder="Auto-generated if blank",
            )

        # Host Advertising discount slider
        is_host_ad = (contract_type == "Host Advertising")
        discount_pct = 0
        if is_host_ad:
            st.markdown(
                f"**Host Advertising Discount** — This host gets "
                f"**{host_free_screens} free screens** for hosting. "
                f"Additional screens are billed at a discounted rate."
            )
            discount_pct = st.slider(
                "Discount off standard rate (%)",
                min_value=0, max_value=50, value=10, step=5,
                help="10% = host pays 90% of the normal advertiser rate for extra screens",
            )

        # Category Exclusivity fields
        exclusive_category = ""
        if contract_type == "Category Exclusivity":
            exclusive_category = st.text_input(
                "Exclusive Category *",
                placeholder="e.g., Real Estate, Dental, Auto Repair",
                help="The business category this advertiser will own exclusively on their screens",
            )

        # Bundle fields
        bundle_brands = []
        if contract_type == "Bundle":
            brands_input = st.text_area(
                "Brand Names (one per line) *",
                placeholder="Brand 1\nBrand 2\nBrand 3",
                help="List each brand or business location in the bundle",
            )
            if brands_input:
                bundle_brands = [b.strip() for b in brands_input.strip().split("\n") if b.strip()]

        # Renewal: optional original contract reference
        is_renewal = (contract_type == "Renewal")
        renewal_source_contract = None
        if is_renewal and selected_client_id:
            from services.contract_service import get_contracts_for_client
            client_contracts = get_contracts_for_client(selected_client_id)
            active_contracts = [
                c for c in client_contracts
                if c.get("status") in ("active", "signed", "expired")
            ]
            if active_contracts:
                contract_labels = {
                    f"{c.get('title', 'Contract')} ({c.get('status', '').title()})": c
                    for c in active_contracts
                }
                selected_renewal_label = st.selectbox(
                    "Renewing from (optional)",
                    ["None — new renewal"] + list(contract_labels.keys()),
                    help="Select the original contract to pre-fill details",
                )
                if selected_renewal_label != "None — new renewal":
                    renewal_source_contract = contract_labels.get(selected_renewal_label)

        # Multi-tier comparison toggle (advertiser and renewal only)
        include_tier_options = False
        selected_tier_names = []
        if contract_type in ("Advertiser", "Renewal"):
            include_tier_options = st.checkbox(
                "Include tier comparison (Good / Better / Best)",
                help="Present 2-3 package options for the client to choose from",
            )
            if include_tier_options:
                tier_name_list = [t.get("name", "") for t in TIERS]
                selected_tier_names = st.multiselect(
                    "Select tiers to include (2-3)",
                    tier_name_list,
                    default=tier_name_list[:3] if len(tier_name_list) >= 3 else tier_name_list,
                )

        # Tier / package selection
        st.markdown("**Package Details**")
        tier_col1, tier_col2, tier_col3 = st.columns(3)

        tier_names = [t.get("name", "") for t in TIERS] + ["Custom"]

        with tier_col1:
            selected_tier = st.selectbox("Tier", tier_names, index=0)

        # Auto-fill from tier
        tier_data = next((t for t in TIERS if t.get("name") == selected_tier), None)

        with tier_col2:
            screen_count = st.number_input(
                "Screen Count",
                min_value=1, max_value=200,
                value=tier_data.get("screens", 10) if tier_data else 10,
            )

        # Calculate rate — apply discount for Host Advertising
        base_rate = float(tier_data.get("monthly_rate", 350.0)) if tier_data else 350.0
        default_rate = base_rate * (1 - discount_pct / 100) if is_host_ad else base_rate

        with tier_col3:
            monthly_rate = st.number_input(
                "Monthly Rate ($)",
                min_value=0.0, max_value=50000.0,
                value=round(default_rate, 2),
                step=50.0,
                help=f"{discount_pct}% discount applied" if is_host_ad and discount_pct > 0 else "",
            )

        # Term and dates
        term_col1, term_col2, term_col3 = st.columns(3)

        with term_col1:
            term_months = st.selectbox("Term (months)", [1, 3, 6, 12], index=2)

        with term_col2:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now().date(),
            )

        with term_col3:
            auto_renew = st.checkbox("Auto-Renew", value=True)

        # Markets
        selected_markets = st.multiselect(
            "Markets",
            options=MARKETS,
            default=["Oxford"],
        )

        # Created by
        prep_col1, prep_col2 = st.columns(2)
        with prep_col1:
            created_by = st.selectbox(
                "Prepared By",
                ["Creed", "Mary Michael", "Swayze"],
                index=0,
            )

        submitted = st.form_submit_button("Create Contract", type="primary",
                                          width='stretch')

        if submitted:
            if not selected_client_id:
                st.error("Please select a client.")
            elif contract_type == "Category Exclusivity" and not exclusive_category:
                st.error("Please enter the exclusive business category.")
            elif contract_type == "Bundle" and not bundle_brands:
                st.error("Please enter at least one brand name for the bundle.")
            elif include_tier_options and len(selected_tier_names) < 2:
                st.error("Please select at least 2 tiers for the comparison table.")
            else:
                # Calculate end date
                start_str = start_date.strftime("%Y-%m-%d")
                end_dt = start_date + relativedelta(months=term_months)
                end_str = end_dt.strftime("%Y-%m-%d")

                # Determine contract type and tier name
                ct_value = contract_type.lower().replace(" ", "_")
                if is_host_ad:
                    tier_label = f"Host Discount {discount_pct}% - {selected_tier if selected_tier != 'Custom' else f'{screen_count} Screens'}"
                else:
                    tier_label = selected_tier if selected_tier != "Custom" else f"{screen_count} Screens"

                # Build tier_options list for multi-tier contracts
                tier_options_data = None
                if include_tier_options and selected_tier_names:
                    tier_options_data = []
                    for tn in selected_tier_names:
                        t = next((t for t in TIERS if t.get("name") == tn), None)
                        if t:
                            tier_options_data.append({
                                "name": t.get("name", ""),
                                "screens": t.get("screens", 10),
                                "rate": float(t.get("monthly_rate", 350)),
                            })

                with st.spinner("Creating contract..."):
                    try:
                        result = create_contract(
                            client_id=selected_client_id,
                            contract_type=ct_value,
                            title=title,
                            tier_name=tier_label,
                            screen_count=screen_count,
                            monthly_rate=monthly_rate,
                            term_months=term_months,
                            start_date=start_str,
                            end_date=end_str,
                            auto_renew=auto_renew,
                            markets=selected_markets,
                            created_by=created_by,
                            exclusive_category=exclusive_category,
                            bundle_brands=bundle_brands,
                            tier_options=tier_options_data,
                        )
                    except Exception as e:
                        logger.error("Contract creation exception: %s", e)
                        st.error(f"Failed to create contract: {e}")
                        result = None

                    if result:
                        contract_id = result.get("id", "")

                        # Auto-generate the document immediately
                        if contract_id:
                            try:
                                doc_result = generate_contract_document(
                                    contract_id, config
                                )
                            except Exception as e:
                                logger.error("Document generation exception: %s", e)
                                doc_result = None

                            if doc_result:
                                st.success(
                                    f"Contract created for **{selected_client_label}** "
                                    f"and document generated! Go to the **All Contracts** "
                                    f"tab to download the PDF and Word file."
                                )
                            else:
                                st.success(f"Contract created for **{selected_client_label}**.")
                                st.warning(
                                    "Document generation failed. You can try again "
                                    "from the All Contracts tab."
                                )
                        else:
                            st.success(f"Contract created for **{selected_client_label}**.")

                        st.balloons()
                    elif result is None:
                        st.error(
                            "Failed to create contract. This may be a database issue — "
                            "check the Render logs for details."
                        )
