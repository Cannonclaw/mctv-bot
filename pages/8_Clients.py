"""Internal client management — create, manage, and invite portal clients."""

import streamlit as st
import sys
import secrets
import string
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import is_configured
from services.portal_service import (
    create_client, get_all_clients, get_client, update_client, delete_client,
    invite_client_to_portal, get_admin_summary, log_activity,
)
from services.notification_service import notify_portal_account_created

st.set_page_config(page_title="Clients - MCTV Bot", page_icon="\U0001F465", layout="wide")

if not check_password():
    st.stop()


# ── Helper ──────────────────────────────────────────────────────────────────

def _generate_temp_password(length: int = 12) -> str:
    """Generate a readable temp password (no confusing chars)."""
    alphabet = string.ascii_letters + string.digits
    # Remove confusing characters: 0, O, l, 1, I
    alphabet = alphabet.replace("0", "").replace("O", "").replace("l", "").replace("1", "").replace("I", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Supabase gate ───────────────────────────────────────────────────────────

if not is_configured():
    st.warning("Supabase is not configured yet.")
    st.markdown(
        "To use the Client Portal features, set the following environment variables "
        "in your `.env` file or Render dashboard:"
    )
    st.code(
        "SUPABASE_URL=https://your-project.supabase.co\n"
        "SUPABASE_KEY=your-anon-key\n"
        "SUPABASE_SERVICE_KEY=your-service-role-key",
        language=None,
    )
    st.info(
        "Don't have a Supabase project yet? Go to supabase.com, create a free project, "
        "then copy your keys from Project Settings > API."
    )
    st.stop()


# ── Page header ─────────────────────────────────────────────────────────────

st.markdown("## Client Management")
st.caption("Create and manage client accounts. Invite them to the portal so they can view contracts, invoices, and reports.")

# ── Admin summary metrics ───────────────────────────────────────────────────

summary = get_admin_summary()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Clients", summary.get("total_clients", 0))
c2.metric("Active", summary.get("active_clients", 0))
c3.metric("Onboarding", summary.get("onboarding_clients", 0))
c4.metric("Overdue Invoices", summary.get("overdue_invoices", 0))
c5.metric("Monthly Revenue", f"${summary.get('monthly_recurring_revenue', 0):,.2f}")

st.divider()

# ── Tabs: Client List / Add Client ──────────────────────────────────────────

tab_list, tab_add = st.tabs(["All Clients", "Add New Client"])

# ── TAB: All Clients ────────────────────────────────────────────────────────

with tab_list:
    # Filter row
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 6])

    with filter_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Onboarding", "Active", "Paused", "Churned"],
            index=0,
            key="client_status_filter",
        )

    with filter_col2:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Advertiser", "Host"],
            index=0,
            key="client_type_filter",
        )

    # Fetch clients
    status_val = status_filter.lower() if status_filter != "All" else None
    clients = get_all_clients(status=status_val)

    # Apply type filter
    if type_filter != "All":
        type_val = type_filter.lower()
        clients = [c for c in clients if c.get("client_type") == type_val]

    if not clients:
        st.info("No clients found. Use the 'Add New Client' tab or convert a lead from the Leads page.")
    else:
        st.caption(f"Showing {len(clients)} client(s)")

        for client in clients:
            cid = client.get("id", "")
            bname = client.get("business_name", "Unknown")
            cname = client.get("contact_name", "")
            cemail = client.get("contact_email", "")
            ctype = client.get("client_type", "advertiser").title()
            cstatus = client.get("status", "onboarding")
            has_portal = bool(client.get("portal_user_id"))
            rep = client.get("assigned_rep", "")

            # Status emoji
            status_emoji = {
                "onboarding": "\U0001F7E1",
                "active": "\U0001F7E2",
                "paused": "\U0001F7E0",
                "churned": "\U0001F534",
            }.get(cstatus, "\u26AA")

            portal_badge = " \U0001F310" if has_portal else ""

            with st.expander(
                f"{status_emoji} **{bname}** — {cname} | {ctype}{portal_badge}",
                expanded=False,
            ):
                # Client details
                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    st.markdown("**Contact Info**")
                    st.text(f"Name: {cname}")
                    st.text(f"Email: {cemail}")
                    st.text(f"Phone: {client.get('contact_phone', 'N/A')}")
                    st.text(f"City: {client.get('city', 'N/A')}")
                    st.text(f"Industry: {client.get('industry', 'N/A')}")

                with detail_col2:
                    st.markdown("**Account Info**")
                    st.text(f"Type: {ctype}")
                    st.text(f"Status: {cstatus.title()}")
                    st.text(f"Assigned Rep: {rep or 'Unassigned'}")
                    st.text(f"Portal Access: {'Yes' if has_portal else 'No'}")
                    created = client.get("created_at", "")[:16] if client.get("created_at") else "N/A"
                    st.text(f"Created: {created}")

                if client.get("notes"):
                    st.markdown("**Notes:**")
                    st.text(client.get("notes"))

                st.divider()

                # ── Actions row ─────────────────────────────────────────
                action_cols = st.columns(5)

                # Status update
                with action_cols[0]:
                    new_status = st.selectbox(
                        "Change Status",
                        ["onboarding", "active", "paused", "churned"],
                        index=["onboarding", "active", "paused", "churned"].index(cstatus),
                        key=f"status_{cid}",
                    )
                    if new_status != cstatus:
                        if st.button("Update Status", key=f"update_status_{cid}", use_container_width=True):
                            update_client(cid, {"status": new_status})
                            log_activity(cid, f"Status changed to {new_status}",
                                         entity_type="client", entity_id=cid)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()

                # Assign rep
                with action_cols[1]:
                    new_rep = st.selectbox(
                        "Assign Rep",
                        ["", "Creed", "Mary Michael", "Swayze"],
                        index=["", "Creed", "Mary Michael", "Swayze"].index(rep) if rep in ["", "Creed", "Mary Michael", "Swayze"] else 0,
                        key=f"rep_{cid}",
                    )
                    if new_rep != rep:
                        if st.button("Assign", key=f"assign_rep_{cid}", use_container_width=True):
                            update_client(cid, {"assigned_rep": new_rep})
                            log_activity(cid, f"Assigned rep: {new_rep}",
                                         entity_type="client", entity_id=cid)
                            st.success(f"Rep updated to {new_rep}")
                            st.rerun()

                # Invite to portal
                with action_cols[2]:
                    if has_portal:
                        st.success("Portal active")
                    else:
                        if st.button("Invite to Portal", key=f"invite_{cid}",
                                     use_container_width=True, type="primary"):
                            st.session_state[f"show_invite_{cid}"] = True

                # Edit notes
                with action_cols[3]:
                    if st.button("Edit Notes", key=f"notes_btn_{cid}", use_container_width=True):
                        st.session_state[f"show_notes_{cid}"] = not st.session_state.get(f"show_notes_{cid}", False)

                # Delete
                with action_cols[4]:
                    if st.button("Delete", key=f"delete_{cid}", use_container_width=True):
                        st.session_state[f"confirm_delete_{cid}"] = True

                # ── Invite form (shown when clicked) ────────────────────
                if st.session_state.get(f"show_invite_{cid}"):
                    st.markdown("---")
                    st.markdown("**Invite to Client Portal**")
                    st.caption("This will create a login account and send them an email with credentials.")

                    temp_pass = _generate_temp_password()

                    inv_col1, inv_col2 = st.columns(2)
                    with inv_col1:
                        inv_email = st.text_input("Login Email", value=cemail, key=f"inv_email_{cid}")
                    with inv_col2:
                        inv_pass = st.text_input("Temporary Password", value=temp_pass, key=f"inv_pass_{cid}")

                    inv_btn_col1, inv_btn_col2 = st.columns(2)
                    with inv_btn_col1:
                        if st.button("Send Invite", key=f"send_invite_{cid}", type="primary",
                                     use_container_width=True):
                            with st.spinner("Creating portal account..."):
                                result = invite_client_to_portal(
                                    client_id=cid,
                                    email=inv_email,
                                    password=inv_pass,
                                    full_name=cname,
                                )
                                if result:
                                    # Send welcome email
                                    notify_portal_account_created(
                                        client_email=inv_email,
                                        client_name=cname,
                                        business_name=bname,
                                        temp_password=inv_pass,
                                    )
                                    log_activity(cid, "Portal account created",
                                                 entity_type="client", entity_id=cid,
                                                 details={"email": inv_email})
                                    st.success(f"Portal account created for {inv_email}. Welcome email sent.")
                                    del st.session_state[f"show_invite_{cid}"]
                                    st.rerun()
                                else:
                                    st.error("Failed to create portal account. Check the logs for details.")

                    with inv_btn_col2:
                        if st.button("Cancel", key=f"cancel_invite_{cid}", use_container_width=True):
                            del st.session_state[f"show_invite_{cid}"]
                            st.rerun()

                # ── Notes editor (shown when clicked) ───────────────────
                if st.session_state.get(f"show_notes_{cid}"):
                    st.markdown("---")
                    updated_notes = st.text_area(
                        "Notes",
                        value=client.get("notes", ""),
                        key=f"notes_area_{cid}",
                        height=100,
                    )
                    nc1, nc2 = st.columns(2)
                    with nc1:
                        if st.button("Save Notes", key=f"save_notes_{cid}", type="primary",
                                     use_container_width=True):
                            update_client(cid, {"notes": updated_notes})
                            st.success("Notes saved")
                            st.session_state[f"show_notes_{cid}"] = False
                            st.rerun()
                    with nc2:
                        if st.button("Cancel", key=f"cancel_notes_{cid}", use_container_width=True):
                            st.session_state[f"show_notes_{cid}"] = False
                            st.rerun()

                # ── Delete confirmation ─────────────────────────────────
                if st.session_state.get(f"confirm_delete_{cid}"):
                    st.warning(f"Are you sure you want to delete **{bname}**? This cannot be undone.")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, Delete", key=f"yes_delete_{cid}",
                                     use_container_width=True):
                            delete_client(cid)
                            st.success(f"Deleted {bname}")
                            del st.session_state[f"confirm_delete_{cid}"]
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"no_delete_{cid}",
                                     use_container_width=True):
                            del st.session_state[f"confirm_delete_{cid}"]
                            st.rerun()


# ── TAB: Add New Client ────────────────────────────────────────────────────

with tab_add:
    st.markdown("### Add New Client")
    st.caption("Manually add a client. You can also convert leads from the Leads page.")

    with st.form("new_client_form"):
        fc1, fc2 = st.columns(2)

        with fc1:
            new_bname = st.text_input("Business Name *", placeholder="Joe's Pizza")
            new_cname = st.text_input("Contact Name *", placeholder="Joe Smith")
            new_cemail = st.text_input("Contact Email *", placeholder="joe@joespizza.com")
            new_cphone = st.text_input("Contact Phone", placeholder="662-555-1234")

        with fc2:
            new_ctype = st.selectbox("Client Type *", ["Advertiser", "Host"])
            new_industry = st.text_input("Industry", placeholder="Restaurant")
            new_city = st.selectbox("City", ["Oxford", "Starkville", "Tupelo", "Columbus", "West Point", "Other"])
            new_rep = st.selectbox("Assigned Rep", ["", "Creed", "Mary Michael", "Swayze"])

        new_notes = st.text_area("Notes", placeholder="Any additional notes about this client...", height=80)

        submitted = st.form_submit_button("Create Client", type="primary", use_container_width=True)

        if submitted:
            if not new_bname or not new_cname or not new_cemail:
                st.error("Please fill in all required fields (Business Name, Contact Name, Email).")
            else:
                with st.spinner("Creating client..."):
                    result = create_client(
                        business_name=new_bname,
                        contact_name=new_cname,
                        contact_email=new_cemail,
                        client_type=new_ctype.lower(),
                        contact_phone=new_cphone,
                        industry=new_industry,
                        city=new_city,
                        assigned_rep=new_rep,
                        notes=new_notes,
                    )
                    if result:
                        new_id = result.get("id", "")
                        log_activity(new_id, "Client created",
                                     entity_type="client", entity_id=new_id,
                                     details={"business_name": new_bname})
                        st.success(f"Client **{new_bname}** created successfully.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to create client. Check logs for details.")
