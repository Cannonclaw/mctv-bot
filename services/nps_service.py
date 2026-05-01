# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""NPS survey service.

Handles the lifecycle of an NPS survey: creating a token-gated survey row
when a milestone hits, accepting the response, and aggregating scores.

Standard NPS:
    promoters  - score 9 or 10
    passives   - score 7 or 8
    detractors - score 0-6
    NPS = %promoters - %detractors  (range -100 to +100)
"""

import logging
from datetime import date, datetime

from services.supabase_client import (
    insert_row, query_table, update_row,
)

logger = logging.getLogger(__name__)


MILESTONES = [
    ("30d",  30),
    ("90d",  90),
    ("180d", 180),
]


def categorize(score: int) -> str:
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def find_due_surveys(now: date | None = None) -> list[dict]:
    """Return active contracts that have a milestone due but no survey yet.

    Each item: {contract_id, client_id, milestone, days_active, contract}
    """
    now = now or date.today()
    contracts = query_table(
        "contracts",
        filters={"status": "active"},
        order="-created_at",
    ) or []

    due = []
    for c in contracts:
        sd = c.get("start_date")
        if not sd:
            continue
        try:
            start = datetime.fromisoformat(sd).date()
        except (ValueError, TypeError):
            continue
        days_active = (now - start).days
        for milestone_key, threshold in MILESTONES:
            if days_active >= threshold:
                # Skip if already sent
                existing = query_table(
                    "nps_responses",
                    filters={"contract_id": c["id"], "milestone": milestone_key},
                    limit=1,
                )
                if existing:
                    continue
                due.append({
                    "contract_id": c["id"],
                    "client_id": c.get("client_id", ""),
                    "milestone": milestone_key,
                    "days_active": days_active,
                    "contract": c,
                })
                # Only fire the earliest unfired milestone per contract per run
                break
    return due


def create_survey(contract_id: str, client_id: str, milestone: str) -> dict | None:
    """Insert a fresh nps_responses row and return it (with survey_token)."""
    row = insert_row("nps_responses", {
        "contract_id": contract_id,
        "client_id": client_id,
        "milestone": milestone,
    })
    return row


def find_survey_by_token(token: str) -> dict | None:
    if not token:
        return None
    rows = query_table("nps_responses",
                       filters={"survey_token": token}, limit=1)
    return rows[0] if rows else None


def submit_response(token: str, score: int, what_working: str = "",
                    what_not_working: str = "", open_to_referrals: bool = False
                    ) -> dict | None:
    """Record the user's NPS answer."""
    survey = find_survey_by_token(token)
    if not survey:
        return None
    score = max(0, min(10, int(score)))
    return update_row("nps_responses", survey["id"], {
        "score": score,
        "category": categorize(score),
        "what_working": what_working[:1500] if what_working else None,
        "what_not_working": what_not_working[:1500] if what_not_working else None,
        "open_to_referrals": bool(open_to_referrals),
        "responded_at": datetime.now().isoformat(),
    })


def get_aggregate(window_days: int = 180) -> dict:
    """Compute network-wide NPS over the last `window_days`.

    Returns {nps, promoter_pct, passive_pct, detractor_pct, response_count}.
    """
    rows = query_table("nps_responses", order="-responded_at", limit=500) or []

    cutoff = None
    if window_days:
        cutoff_date = date.today().toordinal() - window_days
        cutoff = date.fromordinal(cutoff_date).isoformat()

    responded = [r for r in rows if r.get("score") is not None]
    if cutoff:
        responded = [r for r in responded
                     if (r.get("responded_at") or "")[:10] >= cutoff]

    n = len(responded)
    if n == 0:
        return {"nps": 0, "promoter_pct": 0, "passive_pct": 0,
                "detractor_pct": 0, "response_count": 0}

    promoters = sum(1 for r in responded if r.get("category") == "promoter")
    passives = sum(1 for r in responded if r.get("category") == "passive")
    detractors = sum(1 for r in responded if r.get("category") == "detractor")

    p_pct = round(promoters / n * 100, 1)
    pa_pct = round(passives / n * 100, 1)
    d_pct = round(detractors / n * 100, 1)

    return {
        "nps": round(p_pct - d_pct, 1),
        "promoter_pct": p_pct,
        "passive_pct": pa_pct,
        "detractor_pct": d_pct,
        "response_count": n,
    }
