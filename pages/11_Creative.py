"""Internal creative request management — review, assign, and update client requests."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import is_configured, query_table, update_row, insert_row
from services.portal_service import get_client, get_all_clients
from services.notification_service import notify_creative_status_update
from services.storage_service import get_signed_url, BUCKET_CREATIVE_UPLOADS, BUCKET_CREATIVE_DELIVERIES

st.set_page_config(page_title="Creative Requests - MCTV Bot", page_icon="\U0001F3A8", layout="wide")

if not check_password():
    st.stop()

if not is_configured():
    st.warning("Supabase is not configured yet.")
    st.stop()


# ── Page header ─────────────────────────────────────────────────────────────

st.markdown("## Creative Request Management")
st.caption("Review client creative submissions, manage status, and deliver finished assets.")

# ── Summary metrics ─────────────────────────────────────────────────────────

all_requests = query_table("creative_requests", order="-created_at")

pending = [r for r in all_requests if r.get("status") == "pending"]
in_progress = [r for r in all_requests if r.get("status") == "in_progress"]
review = [r for r in all_requests if r.get("status") == "review"]
completed = [r for r in all_requests if r.get("status") in ("approved", "live")]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Requests", len(all_requests))
c2.metric("Pending", len(pending))
c3.metric("In Progress", len(in_progress))
c4.metric("In Review", len(review))
c5.metric("Completed", len(completed))

st.divider()

# ── Filter ──────────────────────────────────────────────────────────────────

filter_col1, filter_col2 = st.columns([3, 7])

with filter_col1:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Pending", "In Progress", "Review", "Approved", "Live", "Rejected"],
        index=0,
    )

status_map = {
    "All": None, "Pending": "pending", "In Progress": "in_progress",
    "Review": "review", "Approved": "approved", "Live": "live", "Rejected": "rejected",
}
filter_val = status_map.get(status_filter)

requests = all_requests
if filter_val:
    requests = [r for r in requests if r.get("status") == filter_val]

if not requests:
    st.info("No creative requests found.")
    st.stop()

st.caption(f"Showing {len(requests)} request(s)")

# ── Request Cards ───────────────────────────────────────────────────────────

for req in requests:
    rid = req.get("id", "")
    title = req.get("title", "Request")
    req_type = req.get("request_type", "general").replace("_", " ").title()
    rstatus = req.get("status", "pending")
    priority = req.get("priority", "normal")
    assigned = req.get("assigned_to", "")
    client_id = req.get("client_id", "")
    created = req.get("created_at", "")[:16] if req.get("created_at") else ""

    # Get client info
    client = get_client(client_id) if client_id else None
    client_name = client.get("business_name", "Unknown") if client else "Unknown"
    client_email = client.get("contact_email", "") if client else ""
    contact_name = client.get("contact_name", "") if client else ""

    status_emoji = {
        "pending": "\U0001F7E1",
        "in_progress": "\U0001F535",
        "review": "\U0001F7E0",
        "approved": "\u2705",
        "live": "\U0001F7E2",
        "rejected": "\U0001F534",
    }.get(rstatus, "\u26AA")

    priority_badge = " \U0001F525" if priority == "urgent" else ""

    with st.expander(
        f"{status_emoji} **{title}** — {client_name} | {req_type} | "
        f"{rstatus.replace('_', ' ').title()}{priority_badge}",
        expanded=(rstatus in ("pending", "in_progress")),
    ):
        # Details
        det1, det2 = st.columns(2)
        with det1:
            st.markdown("**Request Details**")
            st.text(f"Title: {title}")
            st.text(f"Type: {req_type}")
            st.text(f"Client: {client_name}")
            st.text(f"Submitted: {created}")
            if req.get("description"):
                st.markdown("**Description:**")
                st.text(req.get("description"))

        with det2:
            st.markdown("**Status & Assignment**")
            st.text(f"Status: {rstatus.replace('_', ' ').title()}")
            st.text(f"Priority: {priority.title()}")
            st.text(f"Assigned To: {assigned or 'Unassigned'}")
            if req.get("completed_at"):
                st.text(f"Completed: {req.get('completed_at', '')[:16]}")

        # Internal notes
        if req.get("internal_notes"):
            st.markdown("**Internal Notes:**")
            st.text(req.get("internal_notes"))

        # Attached files
        files = query_table("creative_files", filters={"request_id": rid})
        if files:
            st.markdown(f"**Attached Files ({len(files)}):**")
            for f in files:
                fname = f.get("file_name", "file")
                fpath = f.get("storage_path", "")
                fsize = f.get("file_size", 0)
                size_str = f"{fsize / 1024:.1f} KB" if fsize else ""

                fc1, fc2 = st.columns([3, 1])
                fc1.text(f"  {fname} ({f.get('file_type', '')}) {size_str}")
                if fpath:
                    url = get_signed_url(BUCKET_CREATIVE_UPLOADS, fpath)
                    if url:
                        fc2.markdown(f"[Download]({url})")

        st.divider()

        # ── Action row ──────────────────────────────────────────────
        act1, act2, act3, act4 = st.columns(4)

        # Status update
        with act1:
            new_status = st.selectbox(
                "Update Status",
                ["pending", "in_progress", "review", "approved", "live", "rejected"],
                index=["pending", "in_progress", "review", "approved", "live", "rejected"].index(rstatus),
                key=f"status_{rid}",
            )

        # Assignment
        with act2:
            new_assigned = st.selectbox(
                "Assign To",
                ["", "Creed", "Mary Michael", "Swayze"],
                index=["", "Creed", "Mary Michael", "Swayze"].index(assigned) if assigned in ["", "Creed", "Mary Michael", "Swayze"] else 0,
                key=f"assign_{rid}",
            )

        # Priority
        with act3:
            new_priority = st.selectbox(
                "Priority",
                ["normal", "urgent", "low"],
                index=["normal", "urgent", "low"].index(priority) if priority in ["normal", "urgent", "low"] else 0,
                key=f"priority_{rid}",
            )

        # Save changes
        with act4:
            changes_made = (
                new_status != rstatus or
                new_assigned != assigned or
                new_priority != priority
            )
            if changes_made:
                if st.button("Save Changes", key=f"save_{rid}", type="primary",
                             use_container_width=True):
                    update_data = {
                        "status": new_status,
                        "assigned_to": new_assigned,
                        "priority": new_priority,
                        "updated_at": "now()",
                    }

                    # Mark completed if moving to approved/live
                    if new_status in ("approved", "live") and rstatus not in ("approved", "live"):
                        from datetime import datetime
                        update_data["completed_at"] = datetime.now().isoformat()

                    update_row("creative_requests", rid, update_data)

                    # Notify client if status changed
                    if new_status != rstatus and client_email:
                        notes_to_send = req.get("internal_notes", "")
                        # Don't send internal notes to client on most statuses
                        if new_status != "rejected":
                            notes_to_send = ""

                        notify_creative_status_update(
                            client_email=client_email,
                            client_name=contact_name,
                            request_title=title,
                            new_status=new_status,
                            notes=notes_to_send,
                        )

                    st.success(f"Updated. Client {'notified' if new_status != rstatus else 'not notified'}.")
                    st.rerun()

        # ── Internal notes editor ───────────────────────────────────
        st.markdown("---")
        notes_val = st.text_area(
            "Internal Notes (not visible to client)",
            value=req.get("internal_notes", ""),
            key=f"notes_{rid}",
            height=80,
        )
        if notes_val != (req.get("internal_notes") or ""):
            if st.button("Save Notes", key=f"save_notes_{rid}", use_container_width=True):
                update_row("creative_requests", rid, {"internal_notes": notes_val})
                st.success("Notes saved.")
                st.rerun()
