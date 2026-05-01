# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Contract expiration alert cron script.

Run manually:
    python scripts/contract_alerts.py

Dry run (check without sending notifications):
    python scripts/contract_alerts.py --dry-run

Schedule on Render:
    Add a cron job in render.yaml targeting this script.
    Recommended: 7:15 AM CT daily (Mon-Fri), right after daily briefing.

Schedule locally (Windows Task Scheduler):
    Action: python
    Arguments: scripts/contract_alerts.py
    Start in: C:\\Users\\msaac\\OneDrive - Mississippi Asthma & Allergy Clinic, P.A\\Desktop\\MCTV-Bot
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path so services/ imports work
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("contract_alerts")

# ---------------------------------------------------------------------------
# Imports from project
# ---------------------------------------------------------------------------
from services.contract_service import (  # noqa: E402
    get_expiring_contracts,
    check_and_expire_contracts,
    renew_contract,
    _alert_already_sent,
    _log_alert_sent,
)
from services.notification_service import (  # noqa: E402
    notify_contract_expiring_team,
    notify_contract_expiring_client,
    notify_contract_expired_team,
    sms_contract_expiring,
)
from services.portal_service import get_client  # noqa: E402


def _group_by_bucket(contracts: list) -> dict:
    """Group expiring contracts into 30/60/90 day buckets."""
    buckets = {"30": [], "60": [], "90": []}
    for c in contracts:
        dr = c.get("days_remaining", 999)
        if dr <= 30:
            buckets["30"].append(c)
        elif dr <= 60:
            buckets["60"].append(c)
        else:
            buckets["90"].append(c)
    return buckets


def _enrich_with_client(contracts: list) -> list:
    """Add client_name and client contact info to each contract dict."""
    for c in contracts:
        client = get_client(c.get("client_id", ""))
        if client:
            c["client_name"] = client.get("business_name", "Unknown")
            c["client_email"] = client.get("contact_email", "")
            c["client_phone"] = client.get("contact_phone", "")
            c["contact_name"] = client.get("contact_name", "")
        else:
            c["client_name"] = "Unknown Client"
            c["client_email"] = ""
            c["client_phone"] = ""
            c["contact_name"] = ""
    return contracts


def _dry_run() -> int:
    """Check expirations and print summary without sending notifications."""
    logger.info("DRY RUN -- checking contract expirations (nothing will be sent)...")

    # Step 1: Find contracts that should be expired
    from services.contract_service import get_expired_contracts
    past_due = get_expired_contracts()

    # Step 2: Find contracts expiring within 90 days
    expiring = get_expiring_contracts(90)
    expiring = _enrich_with_client(expiring)
    buckets = _group_by_bucket(expiring)

    print("\n" + "=" * 60)
    print("CONTRACT EXPIRATION CHECK -- DRY RUN")
    print("=" * 60)

    print(f"\nContracts past due (need auto-expire): {len(past_due)}")
    for c in past_due:
        client = get_client(c.get("client_id", ""))
        bname = client.get("business_name", "Unknown") if client else "Unknown"
        print(f"  - {bname} | {c.get('title', 'N/A')} | ended {c.get('end_date_calc', 'N/A')}")

    total_expiring = len(expiring)
    total_mrr = sum(float(c.get("monthly_rate", 0)) for c in expiring)
    print(f"\nExpiring within 90 days: {total_expiring} contracts (${total_mrr:,.0f}/mo at risk)")

    for label, key in [("Within 30 days", "30"), ("31-60 days", "60"), ("61-90 days", "90")]:
        items = buckets.get(key, [])
        if items:
            mrr = sum(float(c.get("monthly_rate", 0)) for c in items)
            print(f"\n  {label}: {len(items)} contracts (${mrr:,.0f}/mo)")
            for c in items:
                already = _alert_already_sent(c["id"], f"expiring_{key}", "email")
                flag = " [ALREADY SENT]" if already else " [WOULD SEND]"
                print(
                    f"    - {c.get('client_name', 'Unknown')} | {c.get('title', 'N/A')} | "
                    f"{c.get('days_remaining', '?')}d left | ${float(c.get('monthly_rate', 0)):,.0f}/mo{flag}"
                )

    print("\n" + "=" * 60)
    logger.info("Dry run complete -- no notifications sent.")
    return 0


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="MCTV Contract Expiration Alerts")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check expirations without sending notifications",
    )
    args = parser.parse_args()

    if args.dry_run:
        return _dry_run()

    logger.info("Starting contract expiration check...")
    results = {"expired": 0, "team_email": False, "client_emails": 0, "client_sms": 0}

    # ── Step 1: Auto-expire past-due contracts ────────────────────────────
    try:
        newly_expired = check_and_expire_contracts()
        results["expired"] = len(newly_expired)
        if newly_expired:
            # Enrich with client names for the team notification
            newly_expired = _enrich_with_client(newly_expired)
            notify_contract_expired_team(newly_expired)
            logger.info("Auto-expired %d contract(s), team notified", len(newly_expired))

            # Auto-renew contracts that have auto_renew enabled
            for c in newly_expired:
                if c.get("auto_renew"):
                    try:
                        renewed = renew_contract(c["id"])
                        if renewed:
                            logger.info(
                                "Auto-renewed contract %s -> %s (%s)",
                                c["id"], renewed.get("id"), c.get("client_name", ""),
                            )
                    except Exception as e:
                        logger.error("Failed to auto-renew contract %s: %s", c["id"], e)
    except Exception as e:
        logger.error("Error during auto-expire: %s", e)

    # ── Step 2: Check expiring contracts (within 90 days) ─────────────────
    try:
        expiring = get_expiring_contracts(90)
        expiring = _enrich_with_client(expiring)
    except Exception as e:
        logger.error("Error fetching expiring contracts: %s", e)
        expiring = []

    if not expiring and not results["expired"]:
        logger.info("No contracts expiring or expired. All clear.")
        return 0

    buckets = _group_by_bucket(expiring)

    # ── Step 3: Send team summary email (all buckets) ─────────────────────
    # Only send if there's at least one contract we haven't alerted about
    has_new_alerts = False
    for bucket_key, items in buckets.items():
        for c in items:
            if not _alert_already_sent(c["id"], f"expiring_{bucket_key}", "email"):
                has_new_alerts = True
                break
        if has_new_alerts:
            break

    if has_new_alerts:
        try:
            team_sent = notify_contract_expiring_team(buckets)
            results["team_email"] = team_sent
            if team_sent:
                # Log team alerts for each contract
                for bucket_key, items in buckets.items():
                    for c in items:
                        if not _alert_already_sent(c["id"], f"expiring_{bucket_key}", "email"):
                            _log_alert_sent(c["id"], f"expiring_{bucket_key}", "team", "email")
                logger.info("Team expiration summary email sent")
        except Exception as e:
            logger.error("Error sending team email: %s", e)

    # ── Step 4: Send client notifications (30-day bucket only) ────────────
    for c in buckets.get("30", []):
        cid = c.get("id", "")
        email = c.get("client_email", "")
        phone = c.get("client_phone", "")
        contact = c.get("contact_name", "")
        bname = c.get("client_name", "")
        title = c.get("title", "")
        days = c.get("days_remaining", 30)
        auto = c.get("auto_renew", False)

        # Generate one-click renewal token (only if not auto-renew, since
        # auto-renew contracts handle themselves).
        renewal_url = ""
        if not auto:
            try:
                from services.contract_service import generate_renewal_offer
                offer = generate_renewal_offer(cid)
                if offer:
                    renewal_url = offer.get("url", "")
            except Exception as e:
                logger.warning("Failed to generate renewal token for %s: %s", cid, e)

        # Client email (only if not already sent)
        if email and not _alert_already_sent(cid, "expiring_30_client", "email"):
            try:
                sent = notify_contract_expiring_client(
                    email, contact, title, days, auto, renewal_url=renewal_url,
                )
                if sent:
                    _log_alert_sent(cid, "expiring_30_client", email, "email")
                    results["client_emails"] += 1
                    logger.info("Client expiration email sent to %s", email)
            except Exception as e:
                logger.error("Error sending client email to %s: %s", email, e)

        # Client SMS (only if not already sent)
        if phone and not _alert_already_sent(cid, "expiring_30_client", "sms"):
            try:
                sms_contract_expiring(phone, contact, bname, days)
                _log_alert_sent(cid, "expiring_30_client", phone, "sms")
                results["client_sms"] += 1
                logger.info("Client expiration SMS sent to %s", phone)
            except Exception as e:
                logger.error("Error sending client SMS to %s: %s", phone, e)

    # ── Summary ───────────────────────────────────────────────────────────
    logger.info(
        "Contract alert check complete | Expired: %d | Team email: %s | "
        "Client emails: %d | Client SMS: %d",
        results["expired"],
        "sent" if results["team_email"] else "skipped",
        results["client_emails"],
        results["client_sms"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
