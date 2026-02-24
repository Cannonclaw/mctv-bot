"""Internal contract management — create, send, track, and manage contracts."""

import json
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import is_configured
from services.contract_service import (
    create_contract, get_all_contracts, get_contract, update_contract,
    delete_contract, generate_contract_document, send_contract,
    activate_contract, cancel_contract, get_contract_summary,
    get_contract_download_url,
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

summary = get_contract_summary()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Contracts", summary.get("total", 0))
c2.metric("Drafts", summary.get("draft", 0))
c3.metric("Awaiting Signature", summary.get("awaiting_signature", 0))
c4.metric("Active", summary.get("active", 0))
c5.metric("Active MRR", f"${summary.get('active_mrr', 0):,.2f}")

st.divider()

# ── Tabs ────────────────────────────────────────────────────────────────────

tab_list, tab_create = st.tabs(["All Contracts", "Create New Contract"])


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
    contracts = get_all_contracts(status=status_val)

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

            # Get client name
            client = get_client(client_id) if client_id else None
            client_name = client.get("business_name", "Unknown Client") if client else "Unknown Client"

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

            with st.expander(
                f"{status_emoji} **{title}** — {client_name} | "
                f"${rate:,.2f}/mo | {screens} screens | {cstatus.title()}{doc_badge}",
                expanded=False,
            ):
                # Contract details
                det_col1, det_col2 = st.columns(2)

                with det_col1:
                    st.markdown("**Contract Details**")
                    st.text(f"Title: {title}")
                    st.text(f"Client: {client_name}")
                    st.text(f"Type: {contract.get('contract_type', 'advertiser').title()}")
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
                                     use_container_width=True, type="primary"):
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
                                     use_container_width=True):
                            with st.spinner("Sending contract..."):
                                result = send_contract(cid)
                                if result:
                                    st.success("Contract sent. Client has been notified by email.")
                                    st.rerun()
                                else:
                                    st.error("Failed to send contract.")
                    elif cstatus == "draft" and not has_doc:
                        st.button("Send to Client", key=f"send_{cid}",
                                  use_container_width=True, disabled=True,
                                  help="Generate the document first")

                with action_cols[2]:
                    # Activate (signed contracts only)
                    if cstatus == "signed":
                        if st.button("Activate", key=f"activate_{cid}",
                                     use_container_width=True, type="primary"):
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
                                use_container_width=True,
                            )
                    elif has_doc and not (local_docx and local_docx.exists()):
                        # Try Supabase Storage signed URL
                        url = get_contract_download_url(cid)
                        if url:
                            st.link_button("\U0001F4C4 Download", url=url,
                                           use_container_width=True)

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
                                use_container_width=True,
                            )

                with action_cols[5]:
                    # Cancel / Delete
                    if cstatus in ("draft", "sent", "viewed"):
                        if st.button("Cancel", key=f"cancel_{cid}",
                                     use_container_width=True):
                            st.session_state[f"confirm_cancel_{cid}"] = True
                    elif cstatus == "cancelled":
                        if st.button("Delete", key=f"delete_{cid}",
                                     use_container_width=True):
                            st.session_state[f"confirm_delete_contract_{cid}"] = True

                # Cancel confirmation
                if st.session_state.get(f"confirm_cancel_{cid}"):
                    st.warning(f"Cancel this contract? This will notify the client if already sent.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        cancel_reason = st.text_input("Reason (optional)", key=f"cancel_reason_{cid}")
                        if st.button("Yes, Cancel Contract", key=f"yes_cancel_{cid}",
                                     use_container_width=True):
                            cancel_contract(cid, reason=cancel_reason)
                            st.success("Contract cancelled.")
                            del st.session_state[f"confirm_cancel_{cid}"]
                            st.rerun()
                    with cc2:
                        if st.button("Keep Contract", key=f"no_cancel_{cid}",
                                     use_container_width=True):
                            del st.session_state[f"confirm_cancel_{cid}"]
                            st.rerun()

                # Delete confirmation
                if st.session_state.get(f"confirm_delete_contract_{cid}"):
                    st.warning("Permanently delete this contract record?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, Delete", key=f"yes_del_contract_{cid}",
                                     use_container_width=True):
                            delete_contract(cid)
                            st.success("Contract deleted.")
                            del st.session_state[f"confirm_delete_contract_{cid}"]
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"no_del_contract_{cid}",
                                     use_container_width=True):
                            del st.session_state[f"confirm_delete_contract_{cid}"]
                            st.rerun()


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
                ["Advertiser", "Host"],
            )
        with fc2:
            title = st.text_input(
                "Contract Title",
                placeholder="Auto-generated if blank",
            )

        # Tier selection (advertiser only)
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

        with tier_col3:
            monthly_rate = st.number_input(
                "Monthly Rate ($)",
                min_value=0.0, max_value=50000.0,
                value=float(tier_data.get("monthly_rate", 350.0)) if tier_data else 350.0,
                step=50.0,
            )

        # Term and dates
        term_col1, term_col2, term_col3 = st.columns(3)

        with term_col1:
            term_months = st.selectbox("Term (months)", [6, 12, 3, 1], index=0)

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
                                          use_container_width=True)

        if submitted:
            if not selected_client_id:
                st.error("Please select a client.")
            else:
                # Calculate end date
                start_str = start_date.strftime("%Y-%m-%d")
                end_dt = start_date + timedelta(days=term_months * 30)
                end_str = end_dt.strftime("%Y-%m-%d")

                with st.spinner("Creating contract..."):
                    result = create_contract(
                        client_id=selected_client_id,
                        contract_type=contract_type.lower(),
                        title=title,
                        tier_name=selected_tier if selected_tier != "Custom" else f"{screen_count} Screens",
                        screen_count=screen_count,
                        monthly_rate=monthly_rate,
                        term_months=term_months,
                        start_date=start_str,
                        end_date=end_str,
                        auto_renew=auto_renew,
                        markets=selected_markets,
                        created_by=created_by,
                    )

                    if result:
                        contract_id = result.get("id", "")

                        # Auto-generate the document immediately
                        if contract_id:
                            doc_result = generate_contract_document(
                                contract_id, config
                            )
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
                    else:
                        st.error("Failed to create contract. Check logs for details.")
