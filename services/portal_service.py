# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal data access layer.

Handles client CRUD, dashboard data, and portal account management.
All admin operations use the service role key to bypass RLS.
"""

from datetime import datetime
from services.supabase_client import (
    query_table, insert_row, update_row, delete_row, sign_up
)


# ── Client CRUD ──────────────────────────────────────────────────────────────

def create_client(business_name: str, contact_name: str, contact_email: str,
                  client_type: str = "advertiser", **kwargs) -> dict | None:
    """Create a new client record.

    Args:
        business_name: Company name
        contact_name: Primary contact name
        contact_email: Primary contact email
        client_type: "advertiser" or "host"
        **kwargs: Optional fields (contact_phone, industry, city, assigned_rep,
                  lead_id, notes)

    Returns:
        Created client dict or None.
    """
    data = {
        "business_name": business_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "client_type": client_type,
        "status": "onboarding",
    }
    # Add optional fields
    for field in ["contact_phone", "industry", "city", "assigned_rep",
                  "lead_id", "notes"]:
        if field in kwargs and kwargs[field]:
            data[field] = kwargs[field]

    return insert_row("clients", data)


def get_client(client_id: str) -> dict | None:
    """Get a single client by ID."""
    results = query_table("clients", filters={"id": client_id})
    return results[0] if results else None


def get_client_by_user_id(user_id: str) -> dict | None:
    """Get a client record by their portal user ID."""
    results = query_table("clients", filters={"portal_user_id": user_id})
    return results[0] if results else None


def get_all_clients(status: str | None = None) -> list[dict]:
    """Get all clients, optionally filtered by status."""
    filters = {"status": status} if status else None
    return query_table("clients", filters=filters, order="-created_at")


def update_client(client_id: str, data: dict) -> dict | None:
    """Update a client record."""
    data["updated_at"] = datetime.now().isoformat()
    return update_row("clients", client_id, data)


def delete_client(client_id: str) -> bool:
    """Delete a client record."""
    return delete_row("clients", client_id)


# ── Convert Lead to Client ───────────────────────────────────────────────────

def convert_lead_to_client(lead: dict, client_type: str = "advertiser",
                           assigned_rep: str = "") -> dict | None:
    """Convert a lead record into a client.

    Args:
        lead: Lead dict from leads_service.get_all_leads()
        client_type: "advertiser" or "host"
        assigned_rep: Sales rep name to assign

    Returns:
        Created client dict or None.
    """
    return create_client(
        business_name=lead.get("business_name", ""),
        contact_name=lead.get("contact_name", ""),
        contact_email=lead.get("contact_email", ""),
        client_type=client_type,
        contact_phone=lead.get("contact_phone", ""),
        industry=lead.get("industry", ""),
        city=lead.get("city", ""),
        assigned_rep=assigned_rep,
        lead_id=lead.get("id", ""),
        notes=lead.get("additional_notes", ""),
    )


# ── Portal Account Management ───────────────────────────────────────────────

def invite_client_to_portal(client_id: str, email: str, password: str,
                            full_name: str) -> dict | None:
    """Create a portal login account for a client.

    Creates a Supabase Auth user and links it to the client record.
    Returns user info dict or None.
    """
    # Look up client to get their type
    client = get_client(client_id)
    if not client:
        print(f"[portal_service] Client {client_id} not found")
        return None

    role = client.get("client_type", "advertiser")  # 'advertiser' or 'host'

    # Create auth user (profile auto-created by trigger)
    user_info = sign_up(
        email=email,
        password=password,
        full_name=full_name,
        role=role,
        company_name=client.get("business_name", ""),
    )

    if not user_info:
        return None

    # Link the auth user to the client record
    update_client(client_id, {"portal_user_id": user_info["user_id"]})

    return user_info


# ── Dashboard Data ───────────────────────────────────────────────────────────

def get_client_dashboard(client_id: str) -> dict:
    """Get all dashboard data for a client in one call.

    Returns dict with: client, contracts, invoices, creative_requests,
    reports, recent_activity.
    """
    client = get_client(client_id)
    if not client:
        return {}

    contracts = query_table("contracts", filters={"client_id": client_id},
                            order="-created_at")
    invoices = query_table("invoices", filters={"client_id": client_id},
                           order="-issued_date")
    creative_requests = query_table("creative_requests",
                                    filters={"client_id": client_id},
                                    order="-created_at", limit=10)
    reports = query_table("client_reports", filters={"client_id": client_id},
                          order="-created_at", limit=5)
    activity = query_table("activity_log", filters={"client_id": client_id},
                           order="-created_at", limit=20)

    # Compute summary metrics
    active_contracts = [c for c in contracts if c.get("status") in ("signed", "active")]
    pending_invoices = [i for i in invoices if i.get("status") in ("sent", "viewed", "overdue")]
    total_screens = sum(c.get("screen_count", 0) for c in active_contracts)

    return {
        "client": client,
        "contracts": contracts,
        "invoices": invoices,
        "creative_requests": creative_requests,
        "reports": reports,
        "activity": activity,
        # Summary
        "active_contract_count": len(active_contracts),
        "total_screens": total_screens,
        "pending_invoice_count": len(pending_invoices),
        "next_invoice": pending_invoices[0] if pending_invoices else None,
    }


# ── Activity Logging ─────────────────────────────────────────────────────────

def log_activity(client_id: str, action: str, entity_type: str = "",
                 entity_id: str = "", user_id: str = "",
                 details: dict | None = None, ip_address: str = ""):
    """Log an activity event for audit trail."""
    data = {
        "client_id": client_id,
        "action": action,
    }
    if entity_type:
        data["entity_type"] = entity_type
    if entity_id:
        data["entity_id"] = entity_id
    if user_id:
        data["user_id"] = user_id
    if details:
        data["details"] = details
    if ip_address:
        data["ip_address"] = ip_address

    insert_row("activity_log", data)


# ── Admin Summary ────────────────────────────────────────────────────────────

def get_admin_summary() -> dict:
    """Get high-level stats for the internal admin dashboard."""
    all_clients = get_all_clients()
    all_contracts = query_table("contracts", order="-created_at")
    all_invoices = query_table("invoices", order="-issued_date")

    active_clients = [c for c in all_clients if c.get("status") == "active"]
    onboarding = [c for c in all_clients if c.get("status") == "onboarding"]
    overdue_invoices = [i for i in all_invoices if i.get("status") == "overdue"]
    pending_contracts = [c for c in all_contracts if c.get("status") == "sent"]
    unsigned_contracts = [c for c in all_contracts
                          if c.get("status") in ("sent", "viewed")]

    total_mrr = sum(
        c.get("monthly_rate", 0) for c in all_contracts
        if c.get("status") in ("signed", "active")
    )

    return {
        "total_clients": len(all_clients),
        "active_clients": len(active_clients),
        "onboarding_clients": len(onboarding),
        "total_contracts": len(all_contracts),
        "pending_contracts": len(pending_contracts),
        "unsigned_contracts": len(unsigned_contracts),
        "total_invoices": len(all_invoices),
        "overdue_invoices": len(overdue_invoices),
        "monthly_recurring_revenue": total_mrr,
    }
