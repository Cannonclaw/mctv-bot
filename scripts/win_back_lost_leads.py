# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Win-back campaign cron.

Daily check: for every advertiser deal stuck in stage='lost' for >= 90 days
that hasn't yet received a win-back attempt, send a short
"what's changed since you said no" email + SMS. One attempt only — we don't
spam ex-prospects.

Usage:
    python scripts/win_back_lost_leads.py
    python scripts/win_back_lost_leads.py --dry-run

Schedule on Render: 9:30 AM CT, Tue/Thu (twice a week is plenty).
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
logger = logging.getLogger("win_back")

WINBACK_SUBJECT = "MCTV — quick check-in"

WINBACK_BODY_TEMPLATE = """Hi {contact},

I'm circling back. We talked a few months ago about advertising on MCTV's
indoor billboard network and the timing wasn't right.

A few things have changed since:
  • We added screens in {markets}
  • Our network now delivers ~1.9M monthly impressions across 125+ screens
  • CPM is still $1-3 (vs. $5-12 for radio)

If anything's shifted on your side — new location, new product, busier
season coming — we'd love to take another look. Reply to this email or
text me back at (601) 201-8202.

If now's still not the time, no worries; we won't keep nudging.

— Team MCTV
www.mctvofms.com
"""

WINBACK_SMS_TEMPLATE = (
    "Hi {first_name}, MCTV here. Anything change on your end since we "
    "last talked? We'd love to take another look. Reply STOP to opt out."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print targets; don't send.")
    args = parser.parse_args()

    from services.supabase_client import query_table, update_row
    from services.notification_service import _send_email
    from services.config_service import load_config

    cfg = load_config()
    markets_active = [k for k, v in cfg.get("markets", {}).items()
                       if v.get("status") == "active"]
    markets_str = ", ".join(markets_active) or "Oxford, Starkville, Tupelo"

    cutoff = (date.today() - timedelta(days=90)).isoformat()

    candidates = query_table(
        "pipeline_opportunities",
        select=("id,business_name,contact_name,contact_email,contact_phone,"
                "stage,deal_type,updated_at,win_back_sent_at,city"),
        filters={"deal_type": "advertiser", "stage": "lost"},
        order="-updated_at",
    ) or []

    eligible = []
    for c in candidates:
        if c.get("win_back_sent_at"):
            continue
        updated = (c.get("updated_at") or "")[:10]
        if not updated or updated > cutoff:
            continue
        if not c.get("contact_email"):
            continue
        eligible.append(c)

    logger.info("Win-back candidates: %d (cutoff=%s)", len(eligible), cutoff)

    sent = 0
    failed = 0

    for c in eligible:
        first_name = (c.get("contact_name") or c.get("business_name") or "there").split()[0]
        email = c["contact_email"]
        phone = (c.get("contact_phone") or "").strip()

        body = WINBACK_BODY_TEMPLATE.format(
            contact=first_name,
            markets=markets_str,
        )
        sms_body = WINBACK_SMS_TEMPLATE.format(first_name=first_name)

        if args.dry_run:
            logger.info("[DRY] Would email %s and SMS %s", email, phone or "(no phone)")
            continue

        try:
            ok = _send_email(email, WINBACK_SUBJECT, body)
        except Exception as e:
            logger.error("Email exception for %s: %s", email, e)
            ok = False

        # SMS — best effort, only if consent on file
        if phone:
            try:
                from services.sms_service import send_sms, check_consent, format_phone
                if check_consent(format_phone(phone)):
                    send_sms(phone, sms_body, template="win_back")
            except Exception as e:
                logger.warning("SMS skipped for %s: %s", phone, e)

        if ok:
            update_row("pipeline_opportunities", c["id"], {
                "win_back_sent_at": datetime.now().isoformat(),
            })
            sent += 1
            logger.info("Win-back sent to %s (%s)", c.get("business_name"), email)
        else:
            failed += 1

    logger.info("Done. sent=%d failed=%d", sent, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
