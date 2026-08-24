# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Detect crons that report success while doing nothing.

Why this exists
---------------
Render shows a cron green when it exits 0. Every cron here exits 0 on an empty
result set, and an empty result set is exactly what a missing credential looks
like from inside the process. So "Successful run" cannot distinguish "there was
no work" from "I could not see the work."

This check compares what the database says *should* happen against what the
crons actually recorded. It caught nothing when it was needed most, because it
did not exist: in August 2026 `mctv-stalled-alerts` logged
"Stalled deals: 0 across 0 reps" every weekday for weeks while 60 opportunities
sat past their thresholds with `last_stalled_alert_at` NULL on every row.

Exit codes
    0  Everything consistent (or quiet for a legitimate, explained reason).
    1  At least one cron is provably not doing its job.
   78  This checker itself is not configured (EX_CONFIG).

Usage
    python scripts/cron_health_check.py
    python scripts/cron_health_check.py --quiet   # only problems
"""

import argparse
import importlib.util
import logging
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cron_health")


def _load_thresholds() -> tuple:
    """Borrow the live stall rules from the cron that owns them.

    scripts/ is not a package, so this loads the module by path rather than
    restating THRESHOLDS here — a second copy would drift the moment someone
    tuned the real one, and a health check that grades against stale rules is
    worse than none.
    """
    path = ROOT / "scripts" / "stalled_deal_alerts.py"
    spec = importlib.util.spec_from_file_location("_stalled_deal_alerts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.THRESHOLDS, mod.RE_ALERT_INTERVAL_DAYS


def _days_since(value: str, today: date) -> int | None:
    """Days since an ISO date/timestamp, or None if unparseable."""
    text = (value or "")[:10]
    if not text:
        return None
    try:
        return (today - date.fromisoformat(text)).days
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true",
                        help="Print only problems.")
    args = parser.parse_args()

    from services.env_preflight import require_env, SUPABASE_ANY_KEY
    require_env("SUPABASE_URL", SUPABASE_ANY_KEY)

    from services.supabase_client import query_table

    today = date.today()
    problems: list[str] = []
    notes: list[str] = []

    # ── Gate: can we see the database at all? ────────────────────────────────
    # Every check below reads as "nothing to do" when the answer is no, so
    # establish it once against a table that is never legitimately empty.
    clients = query_table("clients", select="id", limit=1) or []
    if not clients:
        problems.append(
            "Supabase returned no rows for `clients`, a table that is never "
            "empty. Credentials or connectivity are wrong — treat every "
            "'Successful run' in the dashboard as meaningless until fixed."
        )
        for line in problems:
            logger.error("FAIL  %s", line)
        return 1

    # ── mctv-stalled-alerts ──────────────────────────────────────────────────
    thresholds, _re_alert_days = _load_thresholds()
    deals = query_table("pipeline_opportunities", limit=1000) or []
    due = [
        d for d in deals
        if thresholds.get(d.get("stage", ""))
        and (_days_since(d.get("stage_entered_at") or d.get("updated_at", ""), today) or 0)
        >= thresholds[d["stage"]]
    ]
    ever_alerted = sum(1 for d in deals if d.get("last_stalled_alert_at"))
    if due and ever_alerted == 0:
        problems.append(
            f"stalled-alerts: {len(due)} deals are past their stall thresholds "
            f"but `last_stalled_alert_at` is NULL on all {len(deals)} rows — "
            f"the cron has never actually alerted on anything."
        )
    else:
        notes.append(f"stalled-alerts: {len(due)} due, {ever_alerted} rows previously alerted")

    # ── mctv-upsell-triggers ─────────────────────────────────────────────────
    # This one hard-aborts (exit 1) when it sees no snapshot, so a red run here
    # means "cannot read the table", not "no snapshot exists".
    snaps = query_table("ntv360_snapshots", select="snapshot_month,total_plays",
                        order="-snapshot_month", limit=1) or []
    if not snaps:
        problems.append("upsell-triggers: no NTV360 snapshot readable — the cron aborts with exit 1.")
    elif not (snaps[0].get("total_plays") or 0) > 0:
        problems.append(
            f"upsell-triggers: latest snapshot {snaps[0].get('snapshot_month')} "
            f"has zero plays — the cron aborts with exit 1."
        )
    else:
        notes.append(
            f"upsell-triggers: snapshot {snaps[0].get('snapshot_month')} "
            f"({int(snaps[0]['total_plays']):,} plays) readable"
        )

    # ── Contract-gated crons: nps-send, weekly-pulse, upsell-triggers ────────
    # These are *correctly* quiet with no active contracts. Say so explicitly,
    # so a silent cron is never mistaken for a broken one, or vice versa.
    contracts = query_table("contracts", select="id,status,start_date") or []
    active = [c for c in contracts if c.get("status") == "active"]
    if not active:
        by_status: dict = {}
        for c in contracts:
            by_status[c.get("status") or "(none)"] = by_status.get(c.get("status") or "(none)", 0) + 1
        breakdown = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items())) or "none at all"
        notes.append(
            f"nps-send / weekly-pulse / upsell-triggers: correctly silent — "
            f"0 active contracts ({breakdown}). These stay quiet until a "
            f"contract reaches 'active'; that is a CRM gap, not a cron fault."
        )
    else:
        notes.append(f"contract-gated crons: {len(active)} active contracts in scope")

    # ── mctv-winback ─────────────────────────────────────────────────────────
    lost = [d for d in deals
            if d.get("deal_type") == "advertiser" and d.get("stage") == "lost"]
    eligible = [
        d for d in lost
        if not d.get("win_back_sent_at")
        and (d.get("contact_email") or "").strip()
        and (_days_since(d.get("updated_at", ""), today) or 0) >= 90
    ]
    notes.append(f"winback: {len(eligible)} eligible of {len(lost)} lost deals")

    # ── Report ───────────────────────────────────────────────────────────────
    if not args.quiet:
        for line in notes:
            logger.info("ok    %s", line)
    for line in problems:
        logger.error("FAIL  %s", line)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if problems:
        logger.error("\n%s — %d problem(s) found.", stamp, len(problems))
        return 1
    if not args.quiet:
        logger.info("\n%s — all checks consistent.", stamp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
