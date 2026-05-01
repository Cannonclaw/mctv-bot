# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Weekly advertiser pulse email.

Run every Monday morning. For each active advertiser, sends a short
"this is what your campaign is doing" email with live performance numbers
and a CTA to the portal dashboard.

Usage:
    python scripts/weekly_advertiser_pulse.py
    python scripts/weekly_advertiser_pulse.py --dry-run
    python scripts/weekly_advertiser_pulse.py --to creed@mctvofms.com  # test send

Schedule on Render: 8:30 AM CT every Monday.
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
logger = logging.getLogger("weekly_pulse")


def _build_pulse(client: dict, contracts: list) -> dict:
    """Compute the pulse numbers shown in this week's email."""
    from services.portal_service import _compute_live_performance
    active = [c for c in contracts if c.get("status") in ("signed", "active")]
    total_screens = sum(int(c.get("screen_count", 0) or 0) for c in active)
    perf = _compute_live_performance(active, total_screens)
    return {
        "client_name": client.get("contact_name", ""),
        "business_name": client.get("business_name", ""),
        "email": client.get("contact_email", ""),
        "screens": total_screens,
        "mtd_plays": int(perf.get("mtd_plays_estimated", 0) or 0),
        "mtd_impressions": int(perf.get("mtd_impressions_estimated", 0) or 0),
        "last_month_plays": int(perf.get("last_month_plays", 0) or 0),
        "ctd_plays": int(perf.get("contract_to_date_plays", 0) or 0),
        "data_source": perf.get("data_source", "modeled"),
    }


def _email_body(pulse: dict, portal_url: str) -> tuple[str, str]:
    """Return (subject, plain-text body) for the pulse email."""
    week_label = date.today().strftime("Week of %b %d")
    subject = f"MCTV Pulse — {week_label}"

    if pulse["mtd_plays"] == 0 and pulse["last_month_plays"] == 0:
        # New advertiser — encouraging tone, no numbers yet
        body = f"""Hi {pulse['client_name']},

Quick MCTV pulse for {pulse['business_name']}.

Your campaign is running across {pulse['screens']} screen(s). Performance
data lands once we get our next NTV360 dashboard sync — usually mid-month.
We'll have hard numbers in your next pulse.

In the meantime, your live dashboard is here:
{portal_url}/portal_dashboard

Need creative tweaks or want to add screens? Reply to this email or hit your
MCTV rep.

— Team MCTV
www.mctvofms.com
"""
        return subject, body

    body = f"""Hi {pulse['client_name']},

Quick MCTV pulse for {pulse['business_name']}.

Month-to-date:
  • Plays delivered: {pulse['mtd_plays']:,}
  • Impressions:     {pulse['mtd_impressions']:,}
  • Active screens:  {pulse['screens']}

Last month's total: {pulse['last_month_plays']:,} plays.
Contract-to-date:  {pulse['ctd_plays']:,} plays.

See it live + drill into per-venue performance:
{portal_url}/portal_dashboard

Want a creative refresh, more screens, or a different city mix? Reply and
we'll line it up.

— Team MCTV
www.mctvofms.com
"""
    return subject, body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print emails without sending.")
    parser.add_argument("--to", default="",
                        help="Override delivery address (test send).")
    args = parser.parse_args()

    from services.supabase_client import query_table
    from services.notification_service import _send_email

    portal_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")

    contracts = query_table(
        "contracts",
        filters={"status": "active"},
        order="-created_at",
    ) or []
    if not contracts:
        logger.info("No active contracts; nothing to send.")
        return 0

    # Group contracts by client
    by_client: dict = {}
    for c in contracts:
        cid = c.get("client_id", "")
        if cid:
            by_client.setdefault(cid, []).append(c)

    sent = 0
    skipped = 0
    failed = 0

    for client_id, client_contracts in by_client.items():
        rows = query_table("clients", filters={"id": client_id}, limit=1)
        if not rows:
            continue
        client = rows[0]
        if client.get("client_type", "advertiser") != "advertiser":
            continue
        if client.get("status") not in ("active", "onboarding"):
            continue

        email = (args.to or client.get("contact_email") or "").strip()
        if not email:
            skipped += 1
            continue

        pulse = _build_pulse(client, client_contracts)
        subject, body = _email_body(pulse, portal_url)

        if args.dry_run:
            logger.info("[DRY] Would send to %s — %s", email, subject)
            print("---")
            print(f"To: {email}")
            print(f"Subject: {subject}")
            print(body)
            continue

        try:
            ok = _send_email(email, subject, body)
            if ok:
                sent += 1
                logger.info("Pulse sent: %s", email)
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.error("Send failed for %s: %s", email, e)

    logger.info("Done. sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
