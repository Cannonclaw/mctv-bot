# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Invoice lifecycle service.

Handles invoice CRUD, status transitions, AR aging, payment recording,
partial payments, and overdue detection.  Integrates with notification_service
for emails and SMS reminders.
"""

import json
from datetime import datetime, date, timedelta

from services.supabase_client import query_table, insert_row, update_row, delete_row
from services.portal_service import get_client, log_activity
from services.notification_service import (
    notify_invoice_sent, notify_invoice_overdue, sms_invoice_reminder,
)


# ── Invoice Number Generator ────────────────────────────────────────────────

def _generate_invoice_number() -> str:
    """Generate a unique invoice number: MCTV-YYYYMM-XXXX."""
    now = datetime.now()
    prefix = f"MCTV-{now.strftime('%Y%m')}"

    # Get count of invoices this month to increment
    existing = query_table(
        "invoices",
        select="invoice_number",
        order="-created_at",
        limit=1,
    )

    if existing and existing[0].get("invoice_number", "").startswith(prefix):
        # Extract the last number and increment
        last_num = existing[0]["invoice_number"].split("-")[-1]
        try:
            next_num = int(last_num) + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:04d}"


# ── Invoice CRUD ────────────────────────────────────────────────────────────

def create_invoice(
    client_id: str,
    amount: float,
    description: str = "Monthly advertising",
    due_date: str = "",
    contract_id: str = "",
    period_start: str = "",
    period_end: str = "",
    notes: str = "",
    invoice_number: str = "",
) -> dict | None:
    """Create a new invoice record.

    Args:
        client_id: Client to invoice
        amount: Invoice amount
        description: Line item description
        due_date: Due date (YYYY-MM-DD), defaults to 30 days from now
        contract_id: Associated contract ID (optional)
        period_start: Billing period start (optional)
        period_end: Billing period end (optional)
        notes: Internal notes
        invoice_number: Custom number, auto-generated if blank

    Returns:
        Created invoice dict or None.
    """
    if not invoice_number:
        invoice_number = _generate_invoice_number()

    if not due_date:
        due_date = (date.today() + timedelta(days=30)).isoformat()

    data = {
        "client_id": client_id,
        "invoice_number": invoice_number,
        "amount": amount,
        "description": description,
        "issued_date": date.today().isoformat(),
        "due_date": due_date,
        "status": "draft",
    }

    if contract_id:
        data["contract_id"] = contract_id
    if period_start:
        data["period_start"] = period_start
    if period_end:
        data["period_end"] = period_end
    if notes:
        data["notes"] = notes

    result = insert_row("invoices", data)

    if result:
        log_activity(
            client_id=client_id,
            action=f"Invoice {invoice_number} created (${amount:,.2f})",
            entity_type="invoice",
            entity_id=result.get("id", ""),
            details={"amount": amount, "due_date": due_date},
        )

    return result


def get_invoice(invoice_id: str) -> dict | None:
    """Get a single invoice by ID."""
    results = query_table("invoices", filters={"id": invoice_id})
    return results[0] if results else None


def get_invoices_for_client(client_id: str) -> list[dict]:
    """Get all invoices for a client, newest first."""
    return query_table("invoices", filters={"client_id": client_id},
                       order="-issued_date")


def get_all_invoices(status: str | None = None) -> list[dict]:
    """Get all invoices, optionally filtered by status."""
    filters = {"status": status} if status else None
    return query_table("invoices", filters=filters, order="-issued_date")


def update_invoice(invoice_id: str, data: dict) -> dict | None:
    """Update an invoice record."""
    return update_row("invoices", invoice_id, data)


def delete_invoice(invoice_id: str) -> bool:
    """Delete an invoice record."""
    return delete_row("invoices", invoice_id)


# ── Invoice Lifecycle ───────────────────────────────────────────────────────

def send_invoice(invoice_id: str) -> dict | None:
    """Mark invoice as 'sent' and email the client.

    Returns updated invoice or None.
    """
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    if invoice.get("status") not in ("draft", "sent"):
        print(f"[invoice_service] Cannot send invoice in status: {invoice.get('status')}")
        return None

    client = get_client(invoice.get("client_id", ""))
    if not client:
        return None

    updated = update_invoice(invoice_id, {"status": "sent"})

    # Send notification
    notify_invoice_sent(
        client_email=client.get("contact_email", ""),
        client_name=client.get("contact_name", ""),
        invoice_number=invoice.get("invoice_number", ""),
        amount=float(invoice.get("amount", 0)),
        due_date=invoice.get("due_date", ""),
    )

    log_activity(
        client_id=client.get("id", ""),
        action=f"Invoice {invoice.get('invoice_number', '')} sent",
        entity_type="invoice",
        entity_id=invoice_id,
    )

    # Auto-sync to QuickBooks if connected
    try:
        from services.quickbooks_service import is_connected, sync_invoice_to_qb
        if is_connected():
            qb_inv = sync_invoice_to_qb(invoice, client)
            if qb_inv:
                print(f"[invoice_service] Synced to QuickBooks: {invoice.get('invoice_number', '')}")
    except Exception as e:
        print(f"[invoice_service] QB sync skipped: {e}")

    return updated


def mark_paid(invoice_id: str, paid_date: str = "") -> dict | None:
    """Record payment on an invoice.

    Args:
        invoice_id: Invoice to mark paid
        paid_date: Payment date (YYYY-MM-DD), defaults to today

    Returns:
        Updated invoice or None.
    """
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    if not paid_date:
        paid_date = date.today().isoformat()

    updated = update_invoice(invoice_id, {
        "status": "paid",
        "paid_date": paid_date,
    })

    if updated:
        log_activity(
            client_id=invoice.get("client_id", ""),
            action=f"Invoice {invoice.get('invoice_number', '')} marked paid",
            entity_type="invoice",
            entity_id=invoice_id,
            details={"paid_date": paid_date},
        )

    return updated


def void_invoice(invoice_id: str, reason: str = "") -> dict | None:
    """Void an invoice."""
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    updated = update_invoice(invoice_id, {"status": "void"})

    if updated:
        log_activity(
            client_id=invoice.get("client_id", ""),
            action=f"Invoice {invoice.get('invoice_number', '')} voided",
            entity_type="invoice",
            entity_id=invoice_id,
            details={"reason": reason} if reason else None,
        )

    return updated


def mark_overdue(invoice_id: str) -> dict | None:
    """Mark an invoice as overdue and send a reminder."""
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    if invoice.get("status") not in ("sent", "viewed"):
        return None

    updated = update_invoice(invoice_id, {"status": "overdue"})

    # Send overdue reminder
    client = get_client(invoice.get("client_id", ""))
    if client:
        notify_invoice_overdue(
            client_email=client.get("contact_email", ""),
            client_name=client.get("contact_name", ""),
            invoice_number=invoice.get("invoice_number", ""),
            amount=float(invoice.get("amount", 0)),
            due_date=invoice.get("due_date", ""),
        )

        log_activity(
            client_id=client.get("id", ""),
            action=f"Invoice {invoice.get('invoice_number', '')} marked overdue",
            entity_type="invoice",
            entity_id=invoice_id,
        )

    return updated


# ── Payment Reminders ──────────────────────────────────────────────────────

def get_overdue_invoices() -> list[dict]:
    """Return all invoices with status 'sent' or 'overdue' whose due_date < today."""
    today_str = date.today().isoformat()
    overdue = []

    for status in ("sent", "viewed", "overdue"):
        invoices = get_all_invoices(status=status)
        for inv in invoices:
            due = inv.get("due_date", "")
            if due and due < today_str:
                overdue.append(inv)

    return overdue


def send_payment_reminder(invoice_id: str) -> bool:
    """Send a payment reminder email (and SMS) for a single invoice.

    - Loads the invoice and associated client
    - Sends a reminder via notification_service
    - Logs the reminder in the invoice notes
    Returns True on success, False on failure.
    """
    invoice = get_invoice(invoice_id)
    if not invoice:
        return False

    client = get_client(invoice.get("client_id", ""))
    if not client:
        return False

    inv_num = invoice.get("invoice_number", "")
    amount = float(invoice.get("amount", 0))
    amount_paid = float(invoice.get("amount_paid", 0))
    balance = amount - amount_paid
    due_date = invoice.get("due_date", "")

    # Email reminder
    notify_invoice_overdue(
        client_email=client.get("contact_email", ""),
        client_name=client.get("contact_name", ""),
        invoice_number=inv_num,
        amount=balance,
        due_date=due_date,
    )

    # SMS reminder (fails silently if Twilio not configured)
    sms_invoice_reminder(
        phone=client.get("contact_phone", ""),
        contact_name=client.get("contact_name", ""),
        invoice_number=inv_num,
        amount=f"${balance:,.2f}",
        due_date=due_date,
    )

    # Log the reminder in notes
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    existing_notes = invoice.get("notes", "") or ""
    reminder_note = f"[Reminder sent {now_str}]"
    updated_notes = f"{existing_notes}\n{reminder_note}".strip()

    update_invoice(invoice_id, {
        "notes": updated_notes,
        "last_reminder_sent": now_str,
    })

    log_activity(
        client_id=client.get("id", ""),
        action=f"Payment reminder sent for {inv_num} (${balance:,.2f})",
        entity_type="invoice",
        entity_id=invoice_id,
    )

    return True


def send_bulk_reminders() -> dict:
    """Send payment reminders to all overdue invoices.

    Returns dict with 'sent' count, 'failed' count, and 'invoices' list.
    """
    overdue = get_overdue_invoices()
    results = {"total_overdue": len(overdue), "sent": 0, "failed": 0, "invoices": []}

    for inv in overdue:
        iid = inv.get("id", "")
        success = send_payment_reminder(iid)
        if success:
            results["sent"] += 1
            results["invoices"].append(inv.get("invoice_number", ""))
        else:
            results["failed"] += 1

    return results


# ── Partial Payments ───────────────────────────────────────────────────────

def _get_payments(invoice: dict) -> list[dict]:
    """Extract the payments list from invoice metadata.

    Payments are stored as a JSON-encoded list in the 'payments' field,
    or as a JSON string in the 'notes' metadata.  Prefers the dedicated field.
    """
    raw = invoice.get("payments")
    if raw:
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(raw, list):
            return raw
    return []


def get_payment_history(invoice_id: str) -> list[dict]:
    """Return the list of partial payments recorded on an invoice."""
    invoice = get_invoice(invoice_id)
    if not invoice:
        return []
    return _get_payments(invoice)


def get_balance_due(invoice: dict) -> float:
    """Calculate the remaining balance on an invoice."""
    amount = float(invoice.get("amount", 0))
    amount_paid = float(invoice.get("amount_paid", 0))
    return max(amount - amount_paid, 0.0)


def record_partial_payment(
    invoice_id: str,
    amount: float,
    payment_date: str = "",
    method: str = "Check",
    reference: str = "",
) -> dict | None:
    """Record a partial (or full) payment on an invoice.

    Args:
        invoice_id: Invoice to record payment against
        amount: Payment amount
        payment_date: Date of payment (YYYY-MM-DD), defaults to today
        method: Payment method (Check, Cash, Card, ACH, Other)
        reference: Check number, transaction ID, or other reference

    Returns:
        Updated invoice dict, or None on failure.
    """
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    if not payment_date:
        payment_date = date.today().isoformat()

    inv_amount = float(invoice.get("amount", 0))
    prev_paid = float(invoice.get("amount_paid", 0))
    new_total_paid = prev_paid + amount

    # Build payment record
    payment_record = {
        "amount": amount,
        "date": payment_date,
        "method": method,
        "reference": reference,
        "recorded_at": datetime.now().isoformat(),
    }

    # Append to payments list
    existing_payments = _get_payments(invoice)
    existing_payments.append(payment_record)

    # Determine new status
    if new_total_paid >= inv_amount:
        new_status = "paid"
        paid_date = payment_date
    else:
        new_status = invoice.get("status", "sent")
        paid_date = None

    update_data = {
        "amount_paid": round(new_total_paid, 2),
        "payments": json.dumps(existing_payments),
    }

    if new_status == "paid":
        update_data["status"] = "paid"
        update_data["paid_date"] = paid_date

    updated = update_invoice(invoice_id, update_data)

    if updated:
        inv_num = invoice.get("invoice_number", "")
        balance = max(inv_amount - new_total_paid, 0)
        action_text = (
            f"Payment ${amount:,.2f} ({method}) recorded on {inv_num}. "
            f"Balance: ${balance:,.2f}"
        )
        if new_status == "paid":
            action_text += " — PAID IN FULL"

        log_activity(
            client_id=invoice.get("client_id", ""),
            action=action_text,
            entity_type="invoice",
            entity_id=invoice_id,
            details={
                "payment_amount": amount,
                "method": method,
                "reference": reference,
                "new_balance": balance,
            },
        )

    return updated


# ── Batch Operations ────────────────────────────────────────────────────────

def check_and_mark_overdue() -> int:
    """Scan all sent/viewed invoices and mark any past-due as overdue.

    Returns count of newly overdue invoices.
    """
    today = date.today().isoformat()
    count = 0

    for status in ("sent", "viewed"):
        invoices = get_all_invoices(status=status)
        for inv in invoices:
            due = inv.get("due_date", "")
            if due and due < today:
                mark_overdue(inv.get("id", ""))
                count += 1

    return count


def generate_monthly_invoices(contract_id: str = "") -> list[dict]:
    """Generate invoices for all active contracts (or a specific one).

    Creates draft invoices for the current billing period.
    Returns list of created invoices.
    """
    from services.contract_service import get_all_contracts, get_contract

    created = []

    if contract_id:
        contracts = [get_contract(contract_id)]
    else:
        contracts = get_all_contracts(status="active")

    now = date.today()
    period_start = now.replace(day=1).isoformat()
    next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_end = (next_month - timedelta(days=1)).isoformat()

    for contract in contracts:
        if not contract:
            continue

        cid = contract.get("client_id", "")
        rate = float(contract.get("monthly_rate", 0))
        con_id = contract.get("id", "")
        tier = contract.get("tier_name", "")

        if rate <= 0:
            continue

        # Check if invoice already exists for this period
        existing = query_table("invoices", filters={
            "contract_id": con_id,
            "period_start": period_start,
        })
        if existing:
            continue  # Already invoiced

        inv = create_invoice(
            client_id=cid,
            amount=rate,
            description=f"MCTV {tier or 'Advertising'} — {now.strftime('%B %Y')}",
            contract_id=con_id,
            period_start=period_start,
            period_end=period_end,
        )
        if inv:
            created.append(inv)

    return created


# ── AR Aging Report ─────────────────────────────────────────────────────────

def get_ar_aging() -> dict:
    """Generate an accounts receivable aging report.

    Returns dict with aging buckets and totals.
    """
    outstanding = []
    for status in ("sent", "viewed", "overdue"):
        outstanding.extend(get_all_invoices(status=status))

    today = date.today()

    # Aging buckets
    current = []       # Not yet due
    past_30 = []       # 1-30 days past due
    past_60 = []       # 31-60 days past due
    past_90 = []       # 61-90 days past due
    past_90_plus = []  # 90+ days past due

    for inv in outstanding:
        due_str = inv.get("due_date", "")
        if not due_str:
            current.append(inv)
            continue

        try:
            due_date = date.fromisoformat(due_str)
        except ValueError:
            current.append(inv)
            continue

        days_past = (today - due_date).days

        if days_past <= 0:
            current.append(inv)
        elif days_past <= 30:
            past_30.append(inv)
        elif days_past <= 60:
            past_60.append(inv)
        elif days_past <= 90:
            past_90.append(inv)
        else:
            past_90_plus.append(inv)

    def _bucket_total(bucket):
        return sum(float(i.get("amount", 0)) for i in bucket)

    total_outstanding = _bucket_total(outstanding)

    return {
        "total_outstanding": total_outstanding,
        "total_invoices": len(outstanding),
        "current": {"count": len(current), "total": _bucket_total(current), "invoices": current},
        "past_30": {"count": len(past_30), "total": _bucket_total(past_30), "invoices": past_30},
        "past_60": {"count": len(past_60), "total": _bucket_total(past_60), "invoices": past_60},
        "past_90": {"count": len(past_90), "total": _bucket_total(past_90), "invoices": past_90},
        "past_90_plus": {"count": len(past_90_plus), "total": _bucket_total(past_90_plus), "invoices": past_90_plus},
    }


# ── Summary Stats ───────────────────────────────────────────────────────────

def get_invoice_summary() -> dict:
    """Get high-level invoice stats for the admin dashboard.

    Accounts for partial payments when computing collected / outstanding totals.
    """
    all_invoices = get_all_invoices()

    draft = [i for i in all_invoices if i.get("status") == "draft"]
    sent = [i for i in all_invoices if i.get("status") in ("sent", "viewed")]
    overdue = [i for i in all_invoices if i.get("status") == "overdue"]
    paid = [i for i in all_invoices if i.get("status") == "paid"]
    voided = [i for i in all_invoices if i.get("status") == "void"]

    total_billed = sum(float(i.get("amount", 0)) for i in all_invoices
                       if i.get("status") != "void")

    # Collected = amount_paid across ALL non-void invoices (includes partial payments)
    total_collected = sum(float(i.get("amount_paid", 0) or i.get("amount", 0))
                         for i in paid)
    # Add partial payments on still-outstanding invoices
    total_collected += sum(float(i.get("amount_paid", 0))
                          for i in sent + overdue
                          if float(i.get("amount_paid", 0)) > 0)

    # Outstanding = amount minus amount_paid for sent + overdue invoices
    total_outstanding = sum(
        float(i.get("amount", 0)) - float(i.get("amount_paid", 0))
        for i in sent + overdue
    )
    total_overdue = sum(
        float(i.get("amount", 0)) - float(i.get("amount_paid", 0))
        for i in overdue
    )

    return {
        "total": len(all_invoices),
        "draft": len(draft),
        "sent": len(sent),
        "overdue": len(overdue),
        "paid": len(paid),
        "voided": len(voided),
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "total_overdue": total_overdue,
    }
