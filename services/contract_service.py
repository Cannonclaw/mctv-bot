# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Contract lifecycle service.

Handles contract CRUD, status transitions, document generation,
storage upload, and signature recording.
"""

from datetime import datetime
from pathlib import Path

from services.supabase_client import query_table, insert_row, update_row, delete_row
from services.storage_service import (
    upload_file, upload_from_path, get_signed_url, BUCKET_CONTRACTS,
)
from services.notification_service import (
    notify_contract_ready, notify_contract_signed,
)
from services.portal_service import get_client, log_activity


# ── Contract type mapping ──────────────────────────────────────────────────
# The UI uses friendly names ('advertiser', 'host') but the DB CHECK constraint
# requires: 'advertising', 'host_media_kit', 'category_exclusivity', 'bundle'.
# These maps translate between the two.

_TYPE_TO_DB = {
    "advertiser": "advertising",
    "host": "host_media_kit",
    # Host Advertising stores as 'advertising' in DB (constraint compatible).
    # Distinguished by tier_name starting with "Host Discount".
    "host_advertising": "advertising",
    # DB values pass through unchanged
    "advertising": "advertising",
    "host_media_kit": "host_media_kit",
    "category_exclusivity": "category_exclusivity",
    "bundle": "bundle",
}

_TYPE_FROM_DB = {
    "advertising": "advertiser",
    "host_media_kit": "host",
    "category_exclusivity": "category_exclusivity",
    "bundle": "bundle",
}


def _to_db_type(contract_type: str) -> str:
    """Convert a UI contract type to the DB-compatible value."""
    return _TYPE_TO_DB.get(contract_type.lower(), contract_type)


def _from_db_type(contract_type: str) -> str:
    """Convert a DB contract type back to the UI-friendly value."""
    return _TYPE_FROM_DB.get(contract_type, contract_type)


def _normalize_contract(row: dict) -> dict:
    """Translate contract_type from DB value back to UI-friendly value."""
    if row and "contract_type" in row:
        row["contract_type"] = _from_db_type(row["contract_type"])
        # Detect host advertising: stored as 'advertising' but tier_name
        # starts with "Host Discount"
        if (row["contract_type"] == "advertiser"
                and row.get("tier_name", "").startswith("Host Discount")):
            row["contract_type"] = "host_advertising"
    return row


# ── Contract CRUD ───────────────────────────────────────────────────────────

def create_contract(
    client_id: str,
    contract_type: str = "advertiser",
    title: str = "",
    tier_name: str = "",
    screen_count: int = 10,
    monthly_rate: float = 350.0,
    term_months: int = 6,
    start_date: str = "",
    end_date: str = "",
    auto_renew: bool = True,
    markets: list[str] | None = None,
    created_by: str = "",
) -> dict | None:
    """Create a new contract record (draft status).

    Returns the created contract dict or None.
    """
    # Map UI type to DB-compatible value
    db_type = _to_db_type(contract_type)

    if not title:
        client = get_client(client_id)
        bname = client.get("business_name", "Client") if client else "Client"
        type_label = contract_type.replace("_", " ").title()
        title = f"MCTV {type_label} Agreement - {bname}"

    data = {
        "client_id": client_id,
        "contract_type": db_type,
        "title": title,
        "tier_name": tier_name,
        "screen_count": screen_count,
        "monthly_rate": monthly_rate,
        "term_months": term_months,
        "auto_renew": auto_renew,
        "status": "draft",
    }

    if start_date:
        data["start_date"] = start_date
    if end_date:
        data["end_date"] = end_date
    if markets:
        data["markets"] = markets
    if created_by:
        data["created_by"] = created_by

    result = insert_row("contracts", data)

    if result:
        log_activity(
            client_id=client_id,
            action="Contract created",
            entity_type="contract",
            entity_id=result.get("id", ""),
            details={"title": title, "tier": tier_name},
        )

    if result:
        result = _normalize_contract(result)
    return result


def get_contract(contract_id: str) -> dict | None:
    """Get a single contract by ID."""
    results = query_table("contracts", filters={"id": contract_id})
    return _normalize_contract(results[0]) if results else None


def get_contracts_for_client(client_id: str) -> list[dict]:
    """Get all contracts for a client, newest first."""
    rows = query_table("contracts", filters={"client_id": client_id},
                       order="-created_at")
    return [_normalize_contract(r) for r in rows]


def get_all_contracts(status: str | None = None) -> list[dict]:
    """Get all contracts, optionally filtered by status."""
    filters = {"status": status} if status else None
    rows = query_table("contracts", filters=filters, order="-created_at")
    return [_normalize_contract(r) for r in rows]


def update_contract(contract_id: str, data: dict) -> dict | None:
    """Update a contract record."""
    # Map contract_type to DB value if being updated
    if "contract_type" in data:
        data["contract_type"] = _to_db_type(data["contract_type"])
    data["updated_at"] = datetime.now().isoformat()
    result = update_row("contracts", contract_id, data)
    return _normalize_contract(result) if result else None


def delete_contract(contract_id: str) -> bool:
    """Delete a contract record."""
    return delete_row("contracts", contract_id)


# ── Contract Lifecycle ──────────────────────────────────────────────────────

def generate_contract_document(contract_id: str, config: dict | None = None) -> dict | None:
    """Generate the contract document (DOCX + PDF) and store paths.

    Saves the local DOCX path as document_url (always reliable) and the
    local PDF path as pdf_url when conversion succeeds.
    Also attempts to upload to Supabase Storage as a cloud backup.

    Returns updated contract dict, or None on failure.
    """
    contract = get_contract(contract_id)
    if not contract:
        print(f"[contract_service] Contract {contract_id} not found")
        return None

    client = get_client(contract.get("client_id", ""))
    if not client:
        print(f"[contract_service] Client not found for contract {contract_id}")
        return None

    # Generate document
    from generators.contract_generator import ContractGenerator

    generator = ContractGenerator(config)
    docx_path, pdf_path, docx_bytes = generator.generate(
        client_name=client.get("contact_name", ""),
        business_name=client.get("business_name", ""),
        contract_type=contract.get("contract_type", "advertiser"),
        tier_name=contract.get("tier_name", ""),
        screen_count=contract.get("screen_count", 10),
        monthly_rate=float(contract.get("monthly_rate", 350)),
        term_months=contract.get("term_months", 6),
        markets=contract.get("markets", ["Oxford"]),
        start_date=contract.get("start_date", ""),
        auto_renew=contract.get("auto_renew", True),
        prepared_by=contract.get("created_by", ""),
        notes="",
    )

    print(f"[contract_service] DOCX generated: {docx_path}")
    print(f"[contract_service] PDF generated: {pdf_path}")

    # Store the local DOCX path as the document_url.
    # The UI layer will also check for a .pdf sibling file for download.
    local_docx = str(docx_path.resolve())
    update_data = {"document_url": local_docx}

    # Also try uploading to Supabase Storage as cloud backup (non-blocking)
    try:
        preferred = pdf_path if (pdf_path and pdf_path.exists()) else docx_path
        storage_path = f"{client.get('id', 'unknown')}/{preferred.name}"
        if preferred.suffix == ".pdf":
            uploaded = upload_from_path(BUCKET_CONTRACTS, storage_path, str(preferred))
        else:
            uploaded = upload_file(
                BUCKET_CONTRACTS, storage_path, docx_bytes,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        if uploaded:
            print(f"[contract_service] Uploaded to Supabase Storage: {storage_path}")
        else:
            print(f"[contract_service] Supabase Storage upload skipped (non-blocking)")
    except Exception as e:
        print(f"[contract_service] Storage upload error (non-blocking): {e}")

    updated = update_contract(contract_id, update_data)

    log_activity(
        client_id=client.get("id", ""),
        action="Contract document generated",
        entity_type="contract",
        entity_id=contract_id,
        details={"document_url": local_docx},
    )

    return updated


def send_contract(contract_id: str) -> dict | None:
    """Mark contract as 'sent' and email the client.

    Returns updated contract or None.
    """
    contract = get_contract(contract_id)
    if not contract:
        return None

    if contract.get("status") not in ("draft", "sent"):
        print(f"[contract_service] Cannot send contract in status: {contract.get('status')}")
        return None

    client = get_client(contract.get("client_id", ""))
    if not client:
        return None

    # Update status to sent
    updated = update_contract(contract_id, {
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
    })

    # Send notification email
    notify_contract_ready(
        client_email=client.get("contact_email", ""),
        client_name=client.get("contact_name", ""),
        contract_title=contract.get("title", ""),
    )

    log_activity(
        client_id=client.get("id", ""),
        action="Contract sent to client",
        entity_type="contract",
        entity_id=contract_id,
    )

    return updated


def record_contract_view(contract_id: str, client_id: str = "") -> dict | None:
    """Mark that the client viewed the contract.

    Args:
        contract_id: Contract to mark as viewed.
        client_id: If provided, verifies the contract belongs to this client.
    """
    contract = get_contract(contract_id)
    if not contract:
        return None

    if client_id and contract.get("client_id") != client_id:
        print(f"[contract_service] Ownership check failed: contract {contract_id} does not belong to client {client_id}")
        return None

    if contract.get("status") == "sent":
        return update_contract(contract_id, {
            "status": "viewed",
            "viewed_at": datetime.now().isoformat(),
        })
    return contract


def sign_contract(
    contract_id: str,
    signed_by: str,
    ip_address: str = "",
    user_agent: str = "",
    user_id: str = "",
    client_id: str = "",
) -> dict | None:
    """Record a contract signature (click-to-sign).

    Args:
        contract_id: Contract to sign
        signed_by: Full name typed by signer
        ip_address: Signer's IP address
        user_agent: Signer's browser user agent
        user_id: Signer's portal user ID
        client_id: If provided, verifies the contract belongs to this client.

    Returns:
        Updated contract dict or None.
    """
    contract = get_contract(contract_id)
    if not contract:
        return None

    if client_id and contract.get("client_id") != client_id:
        print(f"[contract_service] Ownership check failed: contract {contract_id} does not belong to client {client_id}")
        return None

    if contract.get("status") not in ("sent", "viewed"):
        print(f"[contract_service] Cannot sign contract in status: {contract.get('status')}")
        return None

    # Record signature
    updated = update_contract(contract_id, {
        "status": "signed",
        "signed_by": signed_by,
        "signed_at": datetime.now().isoformat(),
        "signed_ip": ip_address,
        "signed_user_agent": user_agent,
    })

    # Notify the MCTV team
    client = get_client(contract.get("client_id", ""))
    if client:
        notify_contract_signed(
            contract_title=contract.get("title", ""),
            client_name=client.get("contact_name", ""),
            business_name=client.get("business_name", ""),
            signed_by=signed_by,
        )

        log_activity(
            client_id=client.get("id", ""),
            action="Contract signed",
            entity_type="contract",
            entity_id=contract_id,
            user_id=user_id,
            details={
                "signed_by": signed_by,
                "signed_at": datetime.now().isoformat(),
            },
            ip_address=ip_address,
        )

    return updated


def activate_contract(contract_id: str) -> dict | None:
    """Transition a signed contract to active status."""
    contract = get_contract(contract_id)
    if not contract:
        return None

    if contract.get("status") != "signed":
        print(f"[contract_service] Can only activate 'signed' contracts, got: {contract.get('status')}")
        return None

    updated = update_contract(contract_id, {"status": "active"})

    log_activity(
        client_id=contract.get("client_id", ""),
        action="Contract activated",
        entity_type="contract",
        entity_id=contract_id,
    )

    return updated


def cancel_contract(contract_id: str, reason: str = "") -> dict | None:
    """Cancel a contract."""
    contract = get_contract(contract_id)
    if not contract:
        return None

    updated = update_contract(contract_id, {"status": "cancelled"})

    log_activity(
        client_id=contract.get("client_id", ""),
        action="Contract cancelled",
        entity_type="contract",
        entity_id=contract_id,
        details={"reason": reason} if reason else None,
    )

    return updated


# ── Document Access ─────────────────────────────────────────────────────────

def get_contract_download_url(contract_id: str, expires_in: int = 3600,
                              client_id: str = "") -> str | None:
    """Get a temporary download URL for a contract document.

    Args:
        contract_id: Contract to get the download URL for.
        expires_in: URL expiry in seconds (default: 1 hour).
        client_id: If provided, verifies the contract belongs to this client.

    Returns a signed URL (expires in 1 hour by default), or None.
    """
    contract = get_contract(contract_id)
    if not contract:
        return None

    if client_id and contract.get("client_id") != client_id:
        print(f"[contract_service] Ownership check failed: contract {contract_id} does not belong to client {client_id}")
        return None

    doc_url = contract.get("document_url", "")
    if not doc_url:
        return None

    # If it's a local path, return it directly
    if doc_url.startswith("/") or doc_url.startswith("C:") or doc_url.startswith("output"):
        return doc_url

    # Otherwise, get a signed URL from Supabase Storage
    return get_signed_url(BUCKET_CONTRACTS, doc_url, expires_in=expires_in)


# ── Summary Stats ───────────────────────────────────────────────────────────

def get_contract_summary() -> dict:
    """Get high-level contract stats for the admin dashboard."""
    all_contracts = get_all_contracts()

    draft = [c for c in all_contracts if c.get("status") == "draft"]
    sent = [c for c in all_contracts if c.get("status") == "sent"]
    viewed = [c for c in all_contracts if c.get("status") == "viewed"]
    signed = [c for c in all_contracts if c.get("status") == "signed"]
    active = [c for c in all_contracts if c.get("status") == "active"]
    cancelled = [c for c in all_contracts if c.get("status") == "cancelled"]

    awaiting_signature = sent + viewed  # Sent but not yet signed

    total_active_mrr = sum(
        float(c.get("monthly_rate", 0)) for c in all_contracts
        if c.get("status") in ("signed", "active")
    )

    return {
        "total": len(all_contracts),
        "draft": len(draft),
        "sent": len(sent),
        "viewed": len(viewed),
        "signed": len(signed),
        "active": len(active),
        "cancelled": len(cancelled),
        "awaiting_signature": len(awaiting_signature),
        "active_mrr": total_active_mrr,
    }
