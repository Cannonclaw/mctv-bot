# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""NPS survey sender cron.

Daily check: for every active contract that has hit its 30 / 90 / 180-day
milestone without a survey on file, generate a token, insert the row, and
email the client the link.

Usage:
    python scripts/nps_send.py
    python scripts/nps_send.py --dry-run
"""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nps_send")


MILESTONE_HEADLINE = {
    "30d":  "30-Day Check-In",
    "90d":  "90-Day Check-In",
    "180d": "6-Month Check-In",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print targets; don't insert or email.")
    args = parser.parse_args()

    from services.nps_service import find_due_surveys, create_survey
    from services.portal_service import get_client
    from services.notification_service import _send_email

    portal_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
    due = find_due_surveys()
    logger.info("Surveys due: %d", len(due))

    sent = 0
    failed = 0

    for item in due:
        contract = item.get("contract") or {}
        client = get_client(item["client_id"]) or {}
        email = (client.get("contact_email") or "").strip()
        contact = client.get("contact_name") or "there"
        business = client.get("business_name") or "your business"

        if not email:
            logger.info("Skipping %s — no contact_email", business)
            continue

        if args.dry_run:
            logger.info("[DRY] Would create + email %s milestone for %s (%s)",
                        item["milestone"], business, email)
            continue

        survey = create_survey(item["contract_id"], item["client_id"],
                               item["milestone"])
        if not survey:
            logger.warning("Could not create survey for %s", business)
            failed += 1
            continue

        token = survey.get("survey_token", "")
        link = f"{portal_url}/portal_nps?token={token}"
        headline = MILESTONE_HEADLINE.get(item["milestone"], "Check-In")
        subject = f"MCTV {headline} — {business}"
        body = f"""Hi {contact},

You've been on the MCTV network long enough that your feedback would actually
move the needle for us. We'd love a quick {headline.lower()}.

It's two questions and a slider — under 2 minutes:
{link}

If something's not working, we want to hear it. If something is, we want
to do more of it.

Thanks for being on the network.

— Team MCTV
www.mctvofms.com
"""

        try:
            ok = _send_email(email, subject, body)
        except Exception as e:
            logger.error("Email exception for %s: %s", email, e)
            ok = False

        if ok:
            sent += 1
            logger.info("Survey emailed: %s (%s)", business, item["milestone"])
        else:
            failed += 1

    logger.info("Done. sent=%d failed=%d", sent, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
