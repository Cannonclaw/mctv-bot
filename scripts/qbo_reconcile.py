# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""QuickBooks reconciliation cron.

Daily check that the portal's invoice state matches QuickBooks. Three buckets
of issues:

  1. Auto-paid sync — Invoices our portal still shows as 'sent'/'overdue' but
     QBO already records as paid. We auto-mark them paid (this reuses
     quickbooks_service.sync_unpaid_invoices()).

  2. Sync gaps — Invoices in 'sent' state that have no qb_invoice_id, meaning
     they never made it into QBO. These need a re-sync.

  3. Stale aging — Invoices in 'sent' state for > 45 days with no payment
     activity. Could be lost / forgotten / dispute.

If any issues are found, sends a reconciliation digest email to NOTIFY_EMAILS.

Usage:
    python scripts/qbo_reconcile.py
    python scripts/qbo_reconcile.py --dry-run

Schedule on Render: 7:00 AM CT daily.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("qbo_reconcile")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report findings; don't auto-mark or email.")
    args = parser.parse_args()

    from services.invoice_service import get_all_invoices, update_invoice
    from services.quickbooks_service import (
        is_connected, sync_unpaid_invoices, sync_invoice_to_qb, get_qb_invoice_url,
    )
    from services.portal_service import get_client
    from services.notification_service import _send_email

    if not is_connected():
        logger.warning("QuickBooks is not connected — aborting")
        return 1

    # 1. Auto-paid sync (reuses existing service helper)
    if args.dry_run:
        # Pull what would change without writing
        from services.quickbooks_service import check_invoice_payments
        outstanding = []
        for status in ("sent", "viewed", "overdue"):
            outstanding.extend(get_all_invoices(status=status))
        would_pay = []
        for inv in outstanding:
            info = check_invoice_payments(inv.get("invoice_number", ""))
            if info and info.get("status") == "paid":
                would_pay.append(inv)
        sync_summary = {"checked": len(outstanding), "newly_paid": len(would_pay),
                        "would_pay": would_pay}
    else:
        sync_summary = sync_unpaid_invoices()

    logger.info("Auto-paid sync: %s", sync_summary)

    # 2. Sync gaps — sent invoices missing qb_invoice_id
    sent_invoices = get_all_invoices(status="sent") or []
    sync_gaps = [inv for inv in sent_invoices if not inv.get("qb_invoice_id")]
    logger.info("Sync gaps (no QB id): %d", len(sync_gaps))

    if not args.dry_run:
        # Try to fix sync gaps automatically
        fixed = 0
        for inv in sync_gaps:
            client = get_client(inv.get("client_id", ""))
            if not client:
                continue
            try:
                qb_inv = sync_invoice_to_qb(inv, client)
                if qb_inv and qb_inv.get("Id"):
                    update_invoice(inv["id"], {
                        "qb_invoice_id": qb_inv["Id"],
                        "qb_invoice_url": get_qb_invoice_url(qb_inv["Id"]),
                    })
                    fixed += 1
            except Exception as e:
                logger.warning("Resync failed for %s: %s",
                               inv.get("invoice_number"), e)
        logger.info("Sync gaps auto-fixed: %d/%d", fixed, len(sync_gaps))
        unfixed_gaps = [inv for inv in sync_gaps
                        if not inv.get("qb_invoice_id")]
    else:
        unfixed_gaps = sync_gaps

    # 3. Stale aging — sent for > 45 days
    cutoff = (date.today() - timedelta(days=45)).isoformat()
    stale = [inv for inv in sent_invoices
             if (inv.get("issued_date") or "") < cutoff]
    logger.info("Stale invoices (>45 days unpaid): %d", len(stale))

    # ── Compose digest ────────────────────────────────────────────────────
    has_issues = (
        sync_summary.get("newly_paid", 0) > 0
        or len(unfixed_gaps) > 0
        or len(stale) > 0
    )

    if not has_issues:
        logger.info("No reconciliation issues. Done.")
        return 0

    body_lines = [
        "MCTV QuickBooks Reconciliation",
        "=" * 40,
        "",
    ]

    if sync_summary.get("newly_paid", 0):
        body_lines.append(f"AUTO-PAID: {sync_summary['newly_paid']} invoice(s) "
                          f"marked paid from QB activity.")
        for inv in (sync_summary.get("would_pay", []) or [])[:10]:
            body_lines.append(
                f"  - {inv.get('invoice_number')}: ${float(inv.get('amount', 0)):,.2f}"
            )
        body_lines.append("")

    if unfixed_gaps:
        body_lines.append(f"SYNC GAPS: {len(unfixed_gaps)} sent invoice(s) "
                          f"NOT yet in QuickBooks. Manual sync needed.")
        for inv in unfixed_gaps[:10]:
            body_lines.append(
                f"  - {inv.get('invoice_number')}: ${float(inv.get('amount', 0)):,.2f}"
            )
        body_lines.append("")

    if stale:
        total = sum(float(inv.get("amount", 0) or 0) for inv in stale)
        body_lines.append(f"STALE AGING: {len(stale)} invoice(s) sent >45 days "
                          f"ago without payment (${total:,.2f} total).")
        for inv in stale[:15]:
            body_lines.append(
                f"  - {inv.get('invoice_number')}: ${float(inv.get('amount', 0)):,.2f} — "
                f"sent {inv.get('issued_date', '')}"
            )
        body_lines.append("")

    body_lines.append("Open the Invoices page to triage:")
    body_lines.append(os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
                       + "/10_Invoices")

    body = "\n".join(body_lines)
    subject = f"QBO Reconciliation — {date.today().isoformat()}"

    recipients = (os.environ.get("NOTIFY_EMAILS", "") or "").split(",")
    recipients = [r.strip() for r in recipients if r.strip()]

    if args.dry_run:
        logger.info("[DRY] Would email %d recipients", len(recipients))
        print(body)
        return 0

    sent_count = 0
    for r in recipients:
        try:
            if _send_email(r, subject, body):
                sent_count += 1
        except Exception as e:
            logger.error("Email failed to %s: %s", r, e)

    logger.info("Reconciliation digest emailed to %d recipients", sent_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
