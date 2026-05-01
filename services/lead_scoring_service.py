# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Heuristic lead scoring (v1).

Pure-function scorer — no ML, no training set yet. Replaces the rep's gut
check at the top of the funnel with a transparent rubric. Score is 0-100,
bucketed into Cold / Warm / Hot.

Signals (max points per signal in parens):
  - source           (40)  Where the lead came from. intake_form/referral hot.
  - completeness     (45)  Did we get name + email + phone + industry?
  - geo              (10)  In an active market vs. expanding vs. outside.
  - recency          (10)  Newer is hotter. Anything > 90d is treated cold.
  - stage            (15)  Pipeline stage signal. proposal_sent+ scores high.
  - sms_consent      ( 5)  Opted in to SMS = engaged + reachable.

Max possible: ~125, capped at 100.
"""

from datetime import datetime, date

# ── Lookup tables ────────────────────────────────────────────────────────────
SOURCE_POINTS = {
    "intake_form":   40,
    "referral":      45,
    "website":       30,
    "prospector":    25,
    "manual":        15,
    "cold_outreach": 10,
}

ACTIVE_MARKETS = {"oxford", "starkville", "tupelo"}
EXPANDING_MARKETS = {"columbus", "west point"}

# Industries MCTV has historically converted well in (roughly weighted).
HOT_INDUSTRIES = {
    "restaurant", "bar", "salon", "barber", "gym", "fitness",
    "medical", "dentist", "law", "real estate", "hvac",
}

STAGE_POINTS = {
    "prospect":         0,
    "outreach":         3,
    "engaged":          6,
    "discovery":        9,
    "proposal_sent":   12,
    "negotiation":     14,
    "contract_sent":   15,
    "won":             15,
    "lost":             0,
}


# ── Public API ───────────────────────────────────────────────────────────────

def score_lead(lead: dict) -> dict:
    """Score a single lead. Returns dict with score, bucket, breakdown."""
    breakdown = {}

    # Source
    source = (lead.get("source") or "manual").lower()
    breakdown["source"] = SOURCE_POINTS.get(source, 10)

    # Completeness — basic contact details
    completeness = 0
    if (lead.get("contact_name") or "").strip():    completeness += 10
    if (lead.get("contact_email") or "").strip():   completeness += 15
    if (lead.get("contact_phone") or "").strip():   completeness += 15
    if (lead.get("industry") or "").strip():        completeness += 5
    breakdown["completeness"] = completeness

    # Industry match (small bonus on top of completeness)
    industry_bonus = 0
    industry = (lead.get("industry") or "").lower()
    if any(h in industry for h in HOT_INDUSTRIES):
        industry_bonus = 5
    breakdown["industry_match"] = industry_bonus

    # Geo
    city = (lead.get("city") or "").lower()
    if any(m in city for m in ACTIVE_MARKETS):
        breakdown["geo"] = 10
    elif any(m in city for m in EXPANDING_MARKETS):
        breakdown["geo"] = 4
    else:
        breakdown["geo"] = 1

    # Recency (uses created_at or submitted_at)
    iso = lead.get("created_at") or lead.get("submitted_at") or ""
    days_old = None
    try:
        if iso:
            dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).date()
            days_old = (date.today() - dt).days
    except (ValueError, TypeError):
        days_old = None
    if days_old is None:
        recency_pts = 5
    elif days_old <= 1:
        recency_pts = 10
    elif days_old <= 7:
        recency_pts = 8
    elif days_old <= 30:
        recency_pts = 5
    elif days_old <= 90:
        recency_pts = 2
    else:
        recency_pts = 0
    breakdown["recency"] = recency_pts
    breakdown["days_old"] = days_old if days_old is not None else 0

    # Stage
    stage = (lead.get("stage") or lead.get("status") or "").lower()
    breakdown["stage"] = STAGE_POINTS.get(stage, 0)

    # SMS consent (a small but meaningful signal of engagement)
    breakdown["sms_consent"] = 5 if lead.get("sms_consent") else 0

    # Total
    total = (
        breakdown["source"]
        + breakdown["completeness"]
        + breakdown["industry_match"]
        + breakdown["geo"]
        + breakdown["recency"]
        + breakdown["stage"]
        + breakdown["sms_consent"]
    )
    score = max(0, min(100, total))

    if score >= 75:
        bucket = "hot"
    elif score >= 50:
        bucket = "warm"
    else:
        bucket = "cold"

    return {
        "score": score,
        "bucket": bucket,
        "breakdown": breakdown,
    }


def score_leads(leads: list) -> list:
    """Add 'score', 'bucket', 'score_breakdown' to each lead in the list."""
    out = []
    for lead in leads or []:
        result = score_lead(lead)
        enriched = dict(lead)
        enriched["score"] = result["score"]
        enriched["bucket"] = result["bucket"]
        enriched["score_breakdown"] = result["breakdown"]
        out.append(enriched)
    return out


def sort_by_score(leads: list, descending: bool = True) -> list:
    """Sort leads by score (default: highest first)."""
    return sorted(score_leads(leads), key=lambda l: l["score"], reverse=descending)
