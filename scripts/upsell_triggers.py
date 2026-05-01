# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Smart upsell triggers cron.

Identifies advertisers who are GETTING TOO MUCH VALUE — i.e. their actual CPM
has dropped below the upsell threshold ($1.50) over the last 30 days, AND
they've been on the network long enough to have data — and suggests they
expand to capture more of the network.

Each client gets at most one upsell email every 60 days.

Usage:
    python scripts/upsell_triggers.py
    python scripts/upsell_triggers.py --dry-run

Schedule on Render: 9:00 AM CT, every Wednesday.
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
logger = logging.getLogger("upsell_triggers")

CPM_THRESHOLD = 1.50         # below this = strong over-delivery
MIN_MONTHS_ACTIVE = 2        # need at least 2 months of data
THROTTLE_DAYS = 60           # don't send the same client more than every 60d


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from services.supabase_client import query_table, update_row
    from services.portal_service import get_client
    from services.config_service import (
        load_config, calculate_cpm, get_all_tiers,
    )
    from services.ntv360_service import get_latest_snapshot
    from services.notification_service import _send_email

    cfg = load_config()
    tiers = get_all_tiers(cfg) or []

    contracts = query_table(
        "contracts",
        filters={"status": "active"},
        order="-created_at",
    ) or []

    snap = get_latest_snapshot()
    if not snap:
        logger.warning("No NTV360 snapshot — aborting")
        return 1
    network_plays = int(snap.get("total_plays", 0) or 0)
    if network_plays <= 0:
        logger.warning("Snapshot has zero plays — aborting")
        return 1

    today = date.today()
    sent = 0
    skipped = 0

    for c in contracts:
        sd = c.get("start_date")
        if not sd:
            continue
        try:
            start = datetime.fromisoformat(sd).date()
        except (ValueError, TypeError):
            continue
        months_active = max((today - start).days // 30, 0)
        if months_active < MIN_MONTHS_ACTIVE:
            continue

        # Throttle
        last_sent = c.get("last_upsell_sent_at")
        if last_sent:
            try:
                last_d = datetime.fromisoformat(last_sent.replace("Z", "+00:00")).date()
                if (today - last_d).days < THROTTLE_DAYS:
                    continue
            except (ValueError, TypeError, AttributeError):
                pass

        screens = int(c.get("screen_count", 0) or 0)
        rate = float(c.get("monthly_rate", 0) or 0)
        if rate <= 0 or screens <= 0:
            continue

        # Estimated impressions for this client this period: prorate the
        # network's total plays by their screen share, ×60 for impressions.
        network_screens = 125  # cfg.get('network', {}).get('total_screens')
        share = screens / max(network_screens, 1)
        estimated_plays = int(network_plays * share)
        estimated_impressions = estimated_plays * 60

        cpm = calculate_cpm(rate, estimated_impressions)
        if cpm <= 0 or cpm >= CPM_THRESHOLD:
            skipped += 1
            continue

        # Pick the next tier up to suggest
        next_tier = None
        for t in sorted(tiers, key=lambda x: int(x.get("screens", 0))):
            if int(t.get("screens", 0)) > screens:
                next_tier = t
                break

        client = get_client(c.get("client_id", "")) or {}
        email = client.get("contact_email")
        if not email:
            skipped += 1
            continue
        contact = client.get("contact_name") or "there"
        business = client.get("business_name") or "your business"

        next_tier_line = ""
        if next_tier:
            next_screens = int(next_tier.get("screens", 0))
            next_rate = float(next_tier.get("monthly_rate", 0) or 0)
            extra = next_rate - rate
            next_tier_line = (
                f"\nThe natural next step is the {next_tier.get('name', 'next tier')} "
                f"({next_screens} screens / ${next_rate:,.0f}/mo — "
                f"${extra:,.0f}/mo more). At {next_screens} screens you'd be "
                f"covering noticeably more of the network during the busiest "
                f"hours.\n"
            )

        subject = f"You're crushing your CPM — let's talk expansion"
        body = f"""Hi {contact},

Quick heads-up because the numbers earned it:

{business} is currently averaging an effective CPM around ${cpm:.2f} on
MCTV — that's about {int(estimated_impressions):,} impressions/month for
${rate:,.0f}/mo. Industry CPMs run $5-12 on radio and $15-30 on cable, so
you're getting unusually strong value.

When CPM drops this low it usually means we're delivering more than you
paid for — which is great, but also means there's room to capture even
more of the network without your cost-per-eyeball going up much.
{next_tier_line}
If you've thought about going wider — adding markets, more screens, a
seasonal sponsorship — now's a good time to talk. Reply to this email or
hit your MCTV rep.

— Team MCTV
www.mctvofms.com
"""

        if args.dry_run:
            logger.info("[DRY] Upsell to %s (CPM=$%.2f) — would send to %s",
                        business, cpm, email)
            continue

        try:
            ok = _send_email(email, subject, body)
            if ok:
                update_row("contracts", c["id"], {
                    "last_upsell_sent_at": datetime.now().isoformat(),
                })
                sent += 1
                logger.info("Upsell sent to %s (CPM=$%.2f)", business, cpm)
        except Exception as e:
            logger.error("Send failed for %s: %s", business, e)

    logger.info("Done. sent=%d skipped=%d", sent, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
