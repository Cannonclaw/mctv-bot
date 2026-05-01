# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Daily briefing push — Slack + SMS.

Generates the morning briefing and pushes it to:
  - Slack webhook (if SLACK_WEBHOOK_URL is set)
  - SMS to team members (if BRIEFING_SMS_RECIPIENTS is set)

Email delivery is already handled by daily_briefing.py — this script is
purely the Slack + SMS half so the team gets the headline without opening
their inbox.

Usage:
    python scripts/push_briefing.py
    python scripts/push_briefing.py --dry-run

Schedule on Render: 7:30 AM CT, Mon-Fri.
"""

import argparse
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("push_briefing")


def _slack_blocks(briefing: dict) -> list:
    """Build a Slack Block Kit payload from the briefing dict."""
    es = briefing.get("executive_summary", {})
    contracts = briefing.get("contracts", {})
    leads = briefing.get("leads", {})
    invoices = briefing.get("invoices", {})

    mrr = es.get("monthly_recurring_revenue", 0)
    active_clients = es.get("active_clients", 0)
    awaiting_sig = contracts.get("awaiting_signature", 0)
    overdue_ct = es.get("overdue_invoices_count", 0)
    overdue_amt = es.get("overdue_amount", 0)
    hot = es.get("hot_leads", 0)

    summary_lines = [
        f"*MRR:* ${mrr:,.0f}",
        f"*Active Clients:* {active_clients}",
        f"*Pending Signatures:* {awaiting_sig}",
        f"*Overdue AR:* ${overdue_amt:,.0f} ({overdue_ct} invoice{'s' if overdue_ct != 1 else ''})",
        f"*Hot Leads:* {hot}",
    ]

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "text": "MCTV Daily Briefing"}},
        {"type": "section",
         "text": {"type": "mrkdwn", "text": "\n".join(summary_lines)}},
    ]

    alerts = briefing.get("alerts", []) or []
    if alerts:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn",
                                "text": "*Top alerts*\n" + "\n".join(f"• {a}" for a in alerts[:5])}})

    follow_ups = leads.get("follow_ups_due", []) or []
    if follow_ups:
        blocks.append({"type": "divider"})
        lines = []
        for f in follow_ups[:5]:
            lines.append(f"• {f.get('business_name', '')} — {f.get('next_action', 'follow up')}")
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn",
                                "text": "*Today's follow-ups*\n" + "\n".join(lines)}})

    portal = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
    blocks.append({"type": "divider"})
    blocks.append({"type": "actions", "elements": [
        {"type": "button",
         "text": {"type": "plain_text", "text": "Open Briefing"},
         "url": f"{portal}/13_Briefing"},
        {"type": "button",
         "text": {"type": "plain_text", "text": "Pipeline"},
         "url": f"{portal}/14_Pipeline"},
    ]})

    return blocks


def post_to_slack(briefing: dict, webhook_url: str, dry_run: bool = False) -> bool:
    blocks = _slack_blocks(briefing)
    payload = {"text": "MCTV Daily Briefing", "blocks": blocks}
    if dry_run:
        logger.info("[DRY] Slack payload: %s", json.dumps(payload)[:400])
        return True
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status == 200
        logger.info("Slack post: HTTP %d", resp.status)
        return ok
    except urllib.error.HTTPError as e:
        logger.error("Slack post failed: HTTP %d %s", e.code, e.read()[:200])
        return False
    except Exception as e:
        logger.error("Slack post failed: %s", e)
        return False


def push_sms(briefing: dict, recipients: list[str], dry_run: bool = False) -> int:
    """Send the SMS-formatted briefing to each recipient. Returns count sent."""
    from services.briefing_service import format_briefing_sms
    body = format_briefing_sms(briefing)

    if dry_run:
        logger.info("[DRY] SMS to %s: %s", recipients, body)
        return 0

    sent = 0
    try:
        from services.sms_service import send_sms
    except ImportError:
        logger.error("sms_service unavailable")
        return 0

    for phone in recipients:
        phone = (phone or "").strip()
        if not phone:
            continue
        try:
            r = send_sms(phone, body, template="daily_briefing", bypass_consent=True)
            if r.get("success"):
                sent += 1
                logger.info("SMS sent to %s", phone)
            else:
                logger.warning("SMS failed to %s: %s", phone, r.get("error"))
        except Exception as e:
            logger.error("SMS exception to %s: %s", phone, e)
    return sent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payloads without posting/sending.")
    args = parser.parse_args()

    from services.briefing_service import generate_briefing

    briefing = generate_briefing()

    slack_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    sms_recipients_raw = os.environ.get("BRIEFING_SMS_RECIPIENTS", "").strip()
    sms_recipients = [s.strip() for s in sms_recipients_raw.split(",") if s.strip()]

    slack_ok = False
    sms_count = 0

    if slack_url:
        slack_ok = post_to_slack(briefing, slack_url, dry_run=args.dry_run)
    else:
        logger.info("SLACK_WEBHOOK_URL not set — skipping Slack")

    if sms_recipients:
        sms_count = push_sms(briefing, sms_recipients, dry_run=args.dry_run)
    else:
        logger.info("BRIEFING_SMS_RECIPIENTS not set — skipping SMS")

    logger.info("Done. slack=%s sms=%d", slack_ok, sms_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
