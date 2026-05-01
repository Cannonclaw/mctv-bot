# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Weekly per-rep recap email.

Every Monday morning, each MCTV rep gets a personalized "your week ahead"
email built from pipeline_opportunities + contracts + leads scoped to deals
assigned to them.

Usage:
    python scripts/weekly_rep_recap.py
    python scripts/weekly_rep_recap.py --dry-run
    python scripts/weekly_rep_recap.py --rep "Mary Michael"

Schedule on Render: 8:00 AM CT every Monday.
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
logger = logging.getLogger("weekly_rep_recap")


def _matches_rep(value: str, rep_full: str, rep_first: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return False
    return (rep_full.lower() in v) or (v in rep_full.lower()) or \
           (rep_first.lower() in v)


def build_rep_digest(rep_full: str, rep_first: str) -> dict:
    """Pull everything a rep cares about for the week ahead."""
    from services.supabase_client import query_table

    today = date.today()
    end_of_week = today + timedelta(days=7)
    cutoff_30d_ago = (today - timedelta(days=30)).isoformat()

    # All deals in pipeline (advertiser + host)
    deals = query_table(
        "pipeline_opportunities",
        order="-updated_at",
        limit=500,
    ) or []
    my_deals = [d for d in deals
                if _matches_rep(d.get("assigned_rep", ""), rep_full, rep_first)]

    open_stages = {"prospect", "outreach", "engaged", "discovery",
                   "proposal_sent", "negotiation", "contract_sent",
                   "identified", "first_visit", "pitched",
                   "agreement_sent", "install_scheduled"}
    open_deals = [d for d in my_deals if d.get("stage") in open_stages]

    pipeline_value = sum(
        float(d.get("monthly_value", 0) or 0) * (int(d.get("probability", 0) or 0) / 100.0)
        for d in open_deals
    )
    raw_pipeline = sum(float(d.get("monthly_value", 0) or 0) for d in open_deals)

    follow_ups = []
    for d in open_deals:
        nd = (d.get("next_action_date") or "")[:10]
        if not nd:
            continue
        try:
            d_date = date.fromisoformat(nd)
        except ValueError:
            continue
        if today <= d_date <= end_of_week:
            follow_ups.append(d)
    follow_ups.sort(key=lambda x: x.get("next_action_date", ""))

    # Stalled deals: in same stage > 14 days
    stalled = []
    for d in open_deals:
        entered = (d.get("stage_entered_at") or d.get("updated_at") or "")[:10]
        if not entered:
            continue
        try:
            entered_date = date.fromisoformat(entered)
        except ValueError:
            continue
        if (today - entered_date).days >= 14:
            stalled.append(d)
    stalled.sort(key=lambda x: x.get("stage_entered_at", ""))

    # Hot leads (score >= 75) where assigned_rep matches
    leads = query_table("leads", order="-submitted_at", limit=200) or []
    try:
        from services.leads_service import calculate_lead_score
        hot_leads = [l for l in leads
                     if calculate_lead_score(l) >= 75
                     and _matches_rep(l.get("assigned_rep", "") or rep_full,
                                       rep_full, rep_first)]
    except Exception:
        hot_leads = []
    hot_leads = hot_leads[:8]

    # Recent wins (closed-won in last 30 days)
    recent_wins = [d for d in my_deals
                    if d.get("stage") in ("won", "live")
                    and (d.get("updated_at") or "")[:10] >= cutoff_30d_ago]

    return {
        "rep_full": rep_full,
        "rep_first": rep_first,
        "open_count": len(open_deals),
        "pipeline_value_weighted": pipeline_value,
        "pipeline_value_raw": raw_pipeline,
        "follow_ups": follow_ups[:10],
        "stalled": stalled[:8],
        "hot_leads": hot_leads,
        "recent_wins": recent_wins[:5],
    }


def format_email(digest: dict, portal_url: str) -> tuple[str, str]:
    today_str = date.today().strftime("%b %d, %Y")
    subject = f"Your MCTV Week Ahead — {today_str}"

    lines = [
        f"Good morning, {digest['rep_first']}.",
        "",
        "Here's your week ahead at a glance.",
        "",
        "PIPELINE",
        f"  Open deals: {digest['open_count']}",
        f"  Weighted value: ${digest['pipeline_value_weighted']:,.0f}/mo",
        f"  Raw pipeline:   ${digest['pipeline_value_raw']:,.0f}/mo",
        "",
    ]

    if digest["follow_ups"]:
        lines.append("FOLLOW-UPS THIS WEEK")
        for d in digest["follow_ups"]:
            nd = (d.get("next_action_date") or "")[:10]
            action = d.get("next_action") or "follow up"
            lines.append(f"  • {nd} — {d.get('business_name', '')}: {action}")
        lines.append("")
    else:
        lines.append("FOLLOW-UPS THIS WEEK: none scheduled — pencil some in.")
        lines.append("")

    if digest["stalled"]:
        lines.append("STALLED (same stage 14+ days)")
        for d in digest["stalled"]:
            since = (d.get("stage_entered_at") or d.get("updated_at") or "")[:10]
            lines.append(
                f"  • {d.get('business_name', '')} — {d.get('stage', '')} "
                f"since {since}"
            )
        lines.append("")

    if digest["hot_leads"]:
        lines.append("HOT LEADS (score 75+)")
        for l in digest["hot_leads"]:
            lines.append(f"  • {l.get('business_name', '')} ({l.get('city', '')})")
        lines.append("")

    if digest["recent_wins"]:
        lines.append("RECENT WINS (last 30 days)")
        for d in digest["recent_wins"]:
            lines.append(
                f"  • {d.get('business_name', '')} — "
                f"${float(d.get('monthly_value', 0) or 0):,.0f}/mo"
            )
        lines.append("")

    lines.append("Pipeline:")
    lines.append(f"  {portal_url}/14_Pipeline")
    lines.append("")
    lines.append("Leads:")
    lines.append(f"  {portal_url}/4_Leads")
    lines.append("")
    lines.append("— MCTV Bot")

    return subject, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rep", default="",
                        help="Send to a specific rep name (substring match).")
    args = parser.parse_args()

    from services.config_service import load_config, get_team_first_names
    from services.notification_service import _send_email

    cfg = load_config()
    team = cfg.get("team", []) or []
    first_names = get_team_first_names(cfg) or []

    portal_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")

    sent = 0
    failed = 0

    for member, rep_first in zip(team, first_names + [""] * (len(team) - len(first_names))):
        rep_full = member.get("name", "")
        email = member.get("email", "")
        if args.rep and args.rep.lower() not in rep_full.lower():
            continue
        if not email:
            continue

        digest = build_rep_digest(rep_full, rep_first or rep_full.split()[0])
        subject, body = format_email(digest, portal_url)

        if args.dry_run:
            logger.info("[DRY] To %s — %s", email, subject)
            print("---")
            print(f"To: {email}")
            print(f"Subject: {subject}")
            print(body)
            continue

        try:
            ok = _send_email(email, subject, body)
            if ok:
                sent += 1
                logger.info("Recap sent to %s", email)
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.error("Send failed for %s: %s", email, e)

    logger.info("Done. sent=%d failed=%d", sent, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
