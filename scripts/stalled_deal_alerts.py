# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Stalled deal alert cron.

Daily check: identify pipeline opportunities that have been sitting in the
same stage longer than the per-stage threshold below. Email each affected
rep their personal stall list (one digest per rep), and email the team
summary to NOTIFY_EMAILS.

Stage thresholds (days):
  outreach        7
  engaged         10
  discovery       14
  proposal_sent   10
  negotiation     14
  contract_sent   7
  prospect        21
  first_visit     14
  pitched         14
  agreement_sent  10
  install_scheduled 14

Usage:
    python scripts/stalled_deal_alerts.py
    python scripts/stalled_deal_alerts.py --dry-run

Schedule on Render: 7:45 AM CT every weekday.
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
logger = logging.getLogger("stalled_deals")

THRESHOLDS = {
    "prospect":         21,
    "outreach":          7,
    "engaged":          10,
    "discovery":        14,
    "proposal_sent":    10,
    "negotiation":      14,
    "contract_sent":     7,
    # Host-pipeline stages
    "identified":       14,
    "first_visit":      14,
    "pitched":          14,
    "agreement_sent":   10,
    "install_scheduled":14,
}

# Throttle: don't re-alert the same opp more than once every N days
RE_ALERT_INTERVAL_DAYS = 5


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from services.supabase_client import query_table, update_row
    from services.config_service import load_config
    from services.notification_service import _send_email

    cfg = load_config()
    team = cfg.get("team", []) or []

    today = date.today()
    today_iso = today.isoformat()

    deals = query_table(
        "pipeline_opportunities",
        order="-updated_at",
        limit=1000,
    ) or []

    stalled_by_rep: dict[str, list] = {}
    stalled_all: list = []

    for d in deals:
        stage = d.get("stage", "")
        threshold = THRESHOLDS.get(stage)
        if not threshold:
            continue
        entered = (d.get("stage_entered_at") or d.get("updated_at") or "")[:10]
        if not entered:
            continue
        try:
            entered_d = date.fromisoformat(entered)
        except ValueError:
            continue
        days_in_stage = (today - entered_d).days
        if days_in_stage < threshold:
            continue

        # Throttle re-alerts
        last_alert = (d.get("last_stalled_alert_at") or "")[:10]
        if last_alert:
            try:
                last_d = date.fromisoformat(last_alert)
                if (today - last_d).days < RE_ALERT_INTERVAL_DAYS:
                    continue
            except ValueError:
                pass

        d["_days_in_stage"] = days_in_stage
        rep = (d.get("assigned_rep") or "Unassigned").strip()
        stalled_by_rep.setdefault(rep, []).append(d)
        stalled_all.append(d)

    logger.info("Stalled deals: %d across %d reps",
                len(stalled_all), len(stalled_by_rep))

    sent = 0

    # Per-rep emails
    for rep_name, deals_list in stalled_by_rep.items():
        deals_list.sort(key=lambda x: -x["_days_in_stage"])
        member = next((m for m in team
                       if rep_name.lower() in (m.get("name") or "").lower()
                       or (m.get("name") or "").split()[0].lower() in rep_name.lower()),
                      None)
        if not member:
            continue
        email = member.get("email")
        first = (member.get("name") or "").split()[0]
        if not email:
            continue

        lines = [
            f"Hi {first},",
            "",
            f"You have {len(deals_list)} stalled deal(s) — same stage for longer "
            f"than expected. Quick poke or a stage change clears the list.",
            "",
            "STALLED DEALS",
            "=" * 40,
        ]
        for d in deals_list[:20]:
            lines.append(
                f"  • {d.get('business_name', '?')} — "
                f"{d.get('stage', '')} for {d['_days_in_stage']} days "
                f"(${float(d.get('monthly_value', 0) or 0):,.0f}/mo). "
                f"Next: {d.get('next_action') or 'none scheduled'}"
            )

        portal_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
        lines += ["", f"Pipeline: {portal_url}/14_Pipeline", "",
                   "— MCTV Bot"]
        body = "\n".join(lines)
        subject = f"Stalled deals — {len(deals_list)} need attention"

        if args.dry_run:
            logger.info("[DRY] Would email rep %s (%d stalled)",
                        email, len(deals_list))
            continue

        try:
            ok = _send_email(email, subject, body)
            if ok:
                sent += 1
                # Mark each deal alerted
                for d in deals_list:
                    update_row("pipeline_opportunities", d["id"], {
                        "last_stalled_alert_at": datetime.now().isoformat(),
                    })
        except Exception as e:
            logger.error("Send failed to %s: %s", email, e)

    logger.info("Done. emails_sent=%d", sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
