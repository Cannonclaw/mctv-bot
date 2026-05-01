# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Contract lifecycle service.

Handles contract CRUD, status transitions, document generation,
storage upload, and signature recording.
"""

import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)
CT = ZoneInfo("America/Chicago")

from services.supabase_client import query_table, insert_row, update_row, delete_row
from services.storage_service import (
    upload_file, upload_from_path, get_signed_url, BUCKET_CONTRACTS,
)
from services.notification_service import (
    notify_contract_ready, notify_contract_signed,
    notify_contract_sent_team,
    sms_contract_ready,
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
    # Renewal stores as 'advertising' in DB. Distinguished by title containing "Renewal".
    "renewal": "advertising",
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
        # Detect renewal: stored as 'advertising' but title contains "Renewal"
        elif (row["contract_type"] == "advertiser"
                and "Renewal" in row.get("title", "")):
            row["contract_type"] = "renewal"
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
    exclusive_category: str = "",
    bundle_brands: list[str] | None = None,
    tier_options: list[dict] | None = None,
    selected_tier: str = "",
    prepay_upfront: bool = False,
    prepay_bonus_months: int = 0,
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
    if exclusive_category:
        data["exclusive_category"] = exclusive_category
    if bundle_brands:
        data["bundle_brands"] = bundle_brands
    if tier_options:
        data["tier_options"] = tier_options
    if selected_tier:
        data["selected_tier"] = selected_tier
    if prepay_upfront:
        data["prepay_upfront"] = True
        data["prepay_bonus_months"] = prepay_bonus_months

    logger.info("Creating contract: keys=%s, type=%s, client=%s", list(data.keys()), db_type, client_id)
    try:
        result = insert_row("contracts", data)
    except Exception as e:
        logger.error("Failed to insert contract: %s | data keys: %s", e, list(data.keys()))
        return None

    if not result:
        logger.error("insert_row returned None for contract (client_id=%s, type=%s). Check supabase_client logs above for HTTP error.", client_id, db_type)
        return None

    log_activity(
        client_id=client_id,
        action="Contract created",
        entity_type="contract",
        entity_id=result.get("id", ""),
        details={"title": title, "tier": tier_name},
    )

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
        exclusive_category=contract.get("exclusive_category", ""),
        bundle_brands=contract.get("bundle_brands", []),
        tier_options=contract.get("tier_options"),
        prepay_upfront=contract.get("prepay_upfront", False),
        prepay_bonus_months=contract.get("prepay_bonus_months", 0),
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
    """Mark contract as 'sent', email the client, and notify the team.

    Returns a dict with the updated contract and notification results:
        {"contract": {...}, "email_sent": bool, "sms_sent": bool}
    Returns None if the contract cannot be sent.
    """
    contract = get_contract(contract_id)
    if not contract:
        return None

    if contract.get("status") not in ("draft", "sent"):
        return None

    client = get_client(contract.get("client_id", ""))
    if not client:
        return None

    # Update status to sent
    updated = update_contract(contract_id, {
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
    })

    client_email = client.get("contact_email", "")
    client_name = client.get("contact_name", "")
    client_phone = client.get("contact_phone", "")
    business_name = client.get("business_name", "")
    contract_title = contract.get("title", "")

    # Send notification email to client
    email_ok = notify_contract_ready(
        client_email=client_email,
        client_name=client_name,
        contract_title=contract_title,
    )

    # Send SMS notification to client
    sms_ok = sms_contract_ready(
        phone=client_phone,
        contact_name=client_name,
        business_name=business_name,
    )

    # Send confirmation to MCTV team
    notify_contract_sent_team(
        contract_title=contract_title,
        client_name=client_name,
        business_name=business_name,
        client_email=client_email,
        email_ok=email_ok,
        sms_ok=sms_ok,
    )

    log_activity(
        client_id=client.get("id", ""),
        action="Contract sent to client",
        entity_type="contract",
        entity_id=contract_id,
    )

    return {"contract": updated, "email_sent": email_ok, "sms_sent": sms_ok}


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
        logger.warning("Cannot sign contract in status: %s", contract.get("status"))
        return None

    # Block signing if contract end date has already passed
    end = _calc_end_date(contract)
    if end and end < datetime.now(CT).date():
        logger.warning("Cannot sign expired contract %s (ended %s)", contract_id, end)
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
        try:
            notify_contract_signed(
                contract_title=contract.get("title", ""),
                client_name=client.get("contact_name", ""),
                business_name=client.get("business_name", ""),
                signed_by=signed_by,
            )
        except Exception as e:
            logger.warning("Failed to send signed notification for contract %s: %s", contract_id, e)

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

    # Close the host-referral loop: if this client came from a referral,
    # mark it converted and queue a reward (5% of monthly rate as screen-time).
    try:
        client_id = contract.get("client_id", "")
        client = get_client(client_id) if client_id else None
        lead_id = (client or {}).get("lead_id", "")
        if lead_id:
            from services.referral_service import mark_referral_converted
            monthly = float(contract.get("monthly_rate", 0) or 0)
            reward = round(monthly * 0.05, 2)
            mark_referral_converted(
                lead_id=lead_id,
                client_id=client_id,
                contract_id=contract_id,
                reward_value=reward,
                reward_type="screen_time",
            )
    except Exception as e:
        print(f"[contract_service] Referral conversion hook skipped: {e}")

    # Kick off the onboarding wizard (welcome email + checklist seeded).
    try:
        from services.onboarding_service import start_onboarding
        start_onboarding(contract_id)
    except Exception as e:
        print(f"[contract_service] Onboarding kickoff skipped: {e}")

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

    # Expiring soon count (active contracts within 90 days of end)
    expiring_soon = 0
    now = datetime.now(CT)
    for c in active:
        end = _calc_end_date(c)
        if end:
            days_left = (end - now.date()).days
            if 0 <= days_left <= 90:
                expiring_soon += 1

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
        "expiring_soon": expiring_soon,
    }


# ── End-Date Helpers ─────────────────────────────────────────────────────

def _calc_end_date(contract: dict) -> date | None:
    """Calculate a contract's end date from start_date + term_months.

    Falls back to the stored end_date field if start_date/term_months
    are missing.  Returns None when nothing is available.
    """
    # Prefer explicit end_date if stored
    end_str = contract.get("end_date")
    if end_str:
        try:
            return datetime.strptime(str(end_str)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    # Calculate from start + term
    start_str = contract.get("start_date")
    term = contract.get("term_months")
    if start_str and term:
        try:
            start = datetime.strptime(str(start_str)[:10], "%Y-%m-%d").date()
            return start + relativedelta(months=int(term))
        except (ValueError, TypeError):
            pass

    return None


def _days_remaining(contract: dict) -> int | None:
    """Days remaining until contract expiry.  Negative = already past due."""
    end = _calc_end_date(contract)
    if end is None:
        return None
    return (end - datetime.now(CT).date()).days


# ── Expiration Queries ────────────────────────────────────────────────────

def get_expiring_contracts(days: int = 90) -> list[dict]:
    """Get active contracts expiring within *days* from today.

    Each returned dict is the full contract plus injected keys:
        ``end_date_calc``  (str YYYY-MM-DD)
        ``days_remaining`` (int)
    Sorted by days_remaining ascending (most urgent first).
    """
    active = get_all_contracts(status="active")
    results = []
    for c in active:
        dr = _days_remaining(c)
        if dr is not None and 0 <= dr <= days:
            c["end_date_calc"] = str(_calc_end_date(c))
            c["days_remaining"] = dr
            results.append(c)
    results.sort(key=lambda x: x["days_remaining"])
    return results


def get_expired_contracts() -> list[dict]:
    """Get active contracts whose end date has already passed.

    These need a status transition to 'expired'.
    """
    active = get_all_contracts(status="active")
    results = []
    for c in active:
        dr = _days_remaining(c)
        if dr is not None and dr <= 0:
            c["end_date_calc"] = str(_calc_end_date(c))
            c["days_remaining"] = dr
            results.append(c)
    return results


# ── Status Transitions ────────────────────────────────────────────────────

def expire_contract(contract_id: str) -> dict | None:
    """Transition an active contract to 'expired' status."""
    contract = get_contract(contract_id)
    if not contract:
        return None
    if contract.get("status") != "active":
        print(f"[contract_service] Can only expire 'active' contracts, got: {contract.get('status')}")
        return None

    updated = update_contract(contract_id, {"status": "expired"})
    log_activity(
        client_id=contract.get("client_id", ""),
        action="Contract expired (auto)",
        entity_type="contract",
        entity_id=contract_id,
        details={"end_date": str(_calc_end_date(contract))},
    )
    return updated


def check_and_expire_contracts() -> list[dict]:
    """Find all active contracts past their end date and expire them.

    Returns the list of contracts that were transitioned to 'expired'.
    """
    past_due = get_expired_contracts()
    expired = []
    for c in past_due:
        result = expire_contract(c["id"])
        if result:
            expired.append(result)
    if expired:
        print(f"[contract_service] Auto-expired {len(expired)} contract(s)")
    return expired


# ── Contract Renewal ──────────────────────────────────────────────────────

def renew_contract(
    contract_id: str,
    new_term_months: int | None = None,
    new_start_date: str | None = None,
) -> dict | None:
    """Clone an expiring/expired contract into a new draft with fresh dates.

    Copies: client_id, contract_type, tier_name, screen_count, monthly_rate,
    markets, auto_renew. Sets new start_date + term_months, status='draft'.

    Args:
        contract_id: The contract to renew.
        new_term_months: Term for the renewal (defaults to original term).
        new_start_date: Start date for renewal (defaults to day after old end).

    Returns:
        The newly-created draft contract dict, or None on failure.
    """
    original = get_contract(contract_id)
    if not original:
        print(f"[contract_service] Cannot renew — contract {contract_id} not found")
        return None

    # Calculate start date for renewal (same day as original end — no gap)
    if not new_start_date:
        end = _calc_end_date(original)
        if end:
            new_start_date = str(end)
        else:
            new_start_date = datetime.now(CT).date().isoformat()

    term = new_term_months or original.get("term_months", 6)

    # Build renewal title
    client = get_client(original.get("client_id", ""))
    bname = client.get("business_name", "Client") if client else "Client"
    title = f"MCTV Advertising Partnership Renewal - {bname}"

    new_contract = create_contract(
        client_id=original.get("client_id", ""),
        contract_type="renewal",
        title=title,
        tier_name=original.get("tier_name", ""),
        screen_count=original.get("screen_count", 10),
        monthly_rate=float(original.get("monthly_rate", 350)),
        term_months=term,
        start_date=new_start_date,
        auto_renew=original.get("auto_renew", True),
        markets=original.get("markets"),
        created_by="Auto-Renewal",
        exclusive_category=original.get("exclusive_category", ""),
        bundle_brands=original.get("bundle_brands"),
        tier_options=original.get("tier_options"),
    )

    if new_contract:
        log_activity(
            client_id=original.get("client_id", ""),
            action="Contract renewed",
            entity_type="contract",
            entity_id=new_contract.get("id", ""),
            details={
                "original_contract_id": contract_id,
                "new_start_date": new_start_date,
                "term_months": term,
            },
        )
        print(f"[contract_service] Renewed contract {contract_id} -> {new_contract.get('id')}")

    return new_contract


# ── One-Click Renewal Offers ──────────────────────────────────────────────

def generate_renewal_offer(contract_id: str) -> dict | None:
    """Issue a one-click renewal token for a contract.

    Stores a UUID on contracts.renewal_token and stamps renewal_offer_sent_at.
    Idempotent: re-running returns the same token if one is already set.

    Returns dict with {token, url, contract} or None on failure.
    """
    import os, uuid
    contract = get_contract(contract_id)
    if not contract:
        return None

    token = contract.get("renewal_token")
    if not token:
        token = str(uuid.uuid4())
        update_contract(contract_id, {
            "renewal_token": token,
            "renewal_offer_sent_at": datetime.now(CT).isoformat(),
        })
    elif not contract.get("renewal_offer_sent_at"):
        update_contract(contract_id, {
            "renewal_offer_sent_at": datetime.now(CT).isoformat(),
        })

    base_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
    return {
        "token": token,
        "url": f"{base_url}/portal_renewal?token={token}",
        "contract": contract,
    }


def find_contract_by_renewal_token(token: str) -> dict | None:
    """Look up a contract by its public renewal token."""
    if not token:
        return None
    rows = query_table("contracts", filters={"renewal_token": token}, limit=1)
    return rows[0] if rows else None


def accept_renewal_offer(token: str, term_months: int | None = None) -> dict | None:
    """Mark a renewal offer accepted and create the new draft contract.

    Returns the NEW (draft) contract dict on success, None on failure.
    Idempotent: if the offer was already accepted, returns the existing
    renewal_contract_id row.
    """
    original = find_contract_by_renewal_token(token)
    if not original:
        return None

    # Already accepted — return the existing renewal record
    if original.get("renewal_contract_id"):
        existing = get_contract(original["renewal_contract_id"])
        if existing:
            return existing

    new_contract = renew_contract(original["id"], new_term_months=term_months)
    if not new_contract:
        return None

    update_contract(original["id"], {
        "renewal_accepted_at": datetime.now(CT).isoformat(),
        "renewal_contract_id": new_contract.get("id", ""),
    })
    log_activity(
        client_id=original.get("client_id", ""),
        action="One-click renewal accepted",
        entity_type="contract",
        entity_id=new_contract.get("id", ""),
        details={"original_contract_id": original.get("id", ""), "via": "renewal_token"},
    )
    return new_contract


# ── Alert Tracking (contract_alerts_log) ──────────────────────────────────

def _alert_already_sent(contract_id: str, alert_type: str, channel: str) -> bool:
    """Check if an alert of this type has already been sent for a contract."""
    try:
        rows = query_table("contract_alerts_log", filters={
            "contract_id": contract_id,
            "alert_type": alert_type,
            "channel": channel,
        })
        return bool(rows)
    except Exception:
        # Table may not exist yet — treat as "not sent"
        return False


def _log_alert_sent(contract_id: str, alert_type: str, sent_to: str,
                    channel: str) -> None:
    """Record that an alert was sent so we don't duplicate it."""
    try:
        insert_row("contract_alerts_log", {
            "contract_id": contract_id,
            "alert_type": alert_type,
            "sent_to": sent_to,
            "channel": channel,
        })
    except Exception as e:
        print(f"[contract_service] Failed to log alert: {e}")
