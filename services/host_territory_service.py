# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host territory mapping and host-desirability scoring.

New-territory expansion starts with one question: which venues do we want a
screen in, and in what order do we knock on their doors? This module answers
it in two halves.

**The map** — ``TERRITORIES`` breaks a metro into named zones (a corridor, a
downtown core, a suburb) with the anchors and venue density that make a zone
worth working. Zones are ordered by ``priority``: zone 1 gets walked first,
because a cluster of screens in one corridor sells far better than the same
screen count scattered across a metro.

**The score** — ``score_candidate()`` rates a single venue 0-100 on the six
things that actually decide whether a host screen earns its keep. Dwell time
carries the most weight: MCTV's whole pitch is a captive audience with 55+
minutes to look at something, so a tire shop waiting room outranks a busier
drive-through every time.

Nothing here talks to the network. The Host Territory page feeds candidates
in (typed by a rep, or researched with Claude) and pushes the ranked survivors
into ``pipeline_opportunities`` with ``deal_type='host'``.
"""

from __future__ import annotations

# ── The map ──────────────────────────────────────────────────────────────────
# Zones are hand-drawn sales territory, not census geography: a rep should be
# able to work one zone in a day without crossing the metro twice.

TERRITORIES = {
    "Memphis Metro": {
        "state": "TN",
        "status": "target",
        "description": (
            "First MCTV territory outside Mississippi. Adjacent to the Oxford "
            "market, so installs and service runs share a drive."
        ),
        "zones": {
            "Germantown": {
                "priority": 1,
                "anchors": ["Germantown Pkwy", "Poplar Ave corridor", "Saddle Creek"],
                "profile": "Highest household income in the metro, dense retail and medical.",
                "why_first": (
                    "Best advertiser dollars per screen in the territory. Suburban "
                    "venues have single owner-operators, so a host agreement takes "
                    "one conversation instead of a corporate review."
                ),
                "target_categories": [
                    "Medical & Dental", "Health & Fitness", "Barbershop/Salon",
                    "Auto Shop", "Bar/Restaurant",
                ],
            },
            "Collierville": {
                "priority": 2,
                "anchors": ["Town Square", "Poplar Ave", "Carriage Crossing"],
                "profile": "Affluent, tight small-business community around a walkable square.",
                "why_first": (
                    "A square-shaped downtown is the cheapest cluster we can build "
                    "— a dozen venues inside a few blocks, and hosts talk to "
                    "each other, so referrals do the second half of the work."
                ),
                "target_categories": [
                    "Bar/Restaurant", "Retail & Boutique", "Barbershop/Salon",
                    "Medical & Dental", "Professional Services",
                ],
            },
            "East Memphis": {
                "priority": 3,
                "anchors": ["Poplar Ave", "Ridgeway", "Sanderlin", "Park Ave"],
                "profile": "Office and medical density, strong daytime population.",
                "why_first": (
                    "Where the metro's advertisers actually sit. Screens here are "
                    "as much a sales demo for prospective advertisers as they are "
                    "inventory."
                ),
                "target_categories": [
                    "Medical & Dental", "Professional Services", "Health & Fitness",
                    "Bar/Restaurant", "Barbershop/Salon",
                ],
            },
            "Bartlett / Cordova": {
                "priority": 4,
                "anchors": ["Stage Rd", "Germantown Pkwy north", "Wolfchase"],
                "profile": "Family suburbs, high service-business count, heavy weekend traffic.",
                "why_first": (
                    "Volume territory. Lower per-screen advertiser value than "
                    "Germantown, but the venue count is deep and turnover is low."
                ),
                "target_categories": [
                    "Auto Shop", "Family Rec & Entertainment", "Health & Fitness",
                    "Gas/Grocery", "Barbershop/Salon",
                ],
            },
            "Midtown": {
                "priority": 5,
                "anchors": ["Overton Square", "Cooper-Young", "Union Ave", "Madison Ave"],
                "profile": "Independent bars, restaurants, and boutiques; young walkable crowd.",
                "why_first": (
                    "The most receptive hosts in the metro and the best photos for "
                    "a media kit, but smaller advertiser budgets. Work it after a "
                    "paying cluster exists east."
                ),
                "target_categories": [
                    "Bar/Restaurant", "Barbershop/Salon", "Retail & Boutique",
                    "Liquor/Wine/Beer", "Health & Fitness",
                ],
            },
            "Downtown Memphis": {
                "priority": 6,
                "anchors": ["Main St Mall", "South Main", "Beale St", "Medical District"],
                "profile": "Tourism, hotels, hospitals, and event traffic.",
                "why_first": (
                    "Highest raw traffic, hardest sell. Hotels and hospitals route "
                    "screen decisions through corporate or facilities, so treat "
                    "this as a long-cycle zone — not first-90-days work."
                ),
                "target_categories": [
                    "Travel & Tourism", "Bar/Restaurant", "Medical & Dental",
                    "Non-Profit/Community", "Retail & Boutique",
                ],
            },
            "University / Highland": {
                "priority": 7,
                "anchors": ["Highland Strip", "University of Memphis", "Central Ave"],
                "profile": "College-town strip — the closest thing here to the Oxford playbook.",
                "why_first": (
                    "We already know how to sell a college strip. The catch is "
                    "that a commuter campus does not fill venues the way Ole Miss "
                    "fills the Square, so expect thinner dwell."
                ),
                "target_categories": [
                    "Bar/Restaurant", "Barbershop/Salon", "Health & Fitness",
                    "Education", "Retail & Boutique",
                ],
            },
        },
    },
}


# ── The score ────────────────────────────────────────────────────────────────
# Six factors, each rated 0-10, weighted to 100. Dwell dominates on purpose:
# a screen is worth what the room's captive minutes are worth.

FACTORS = {
    "dwell":        {"weight": 30, "label": "Dwell time",
                     "help": "Minutes a visitor sits with nothing to do. The whole product."},
    "traffic":      {"weight": 25, "label": "Daily traffic",
                     "help": "Bodies through the door on an average day."},
    "audience":     {"weight": 15, "label": "Audience quality",
                     "help": "Spending power and decision-making of who waits there."},
    "sales_pull":   {"weight": 15, "label": "Advertiser pull",
                     "help": "Does this venue make nearby businesses want the screen?"},
    "install_ease": {"weight": 10, "label": "Install ease",
                     "help": "Wall, power, wifi, and one owner who can say yes."},
    "exclusivity":  {"weight": 5,  "label": "Exclusivity leverage",
                     "help": "Room to sell a category lockout off this venue."},
}

# Category baselines — the starting rating for a venue we know nothing else
# about. A rep's override on any factor beats the baseline.
CATEGORY_BASELINES = {
    "Auto Shop":                  {"dwell": 10, "traffic": 6, "audience": 7, "sales_pull": 7, "install_ease": 9, "exclusivity": 8},
    "Medical & Dental":           {"dwell": 9,  "traffic": 6, "audience": 9, "sales_pull": 8, "install_ease": 7, "exclusivity": 9},
    "Barbershop/Salon":           {"dwell": 9,  "traffic": 7, "audience": 7, "sales_pull": 7, "install_ease": 9, "exclusivity": 7},
    "Health & Fitness":           {"dwell": 8,  "traffic": 8, "audience": 7, "sales_pull": 7, "install_ease": 8, "exclusivity": 7},
    "Bar/Restaurant":             {"dwell": 8,  "traffic": 9, "audience": 7, "sales_pull": 8, "install_ease": 7, "exclusivity": 6},
    "Family Rec & Entertainment": {"dwell": 8,  "traffic": 7, "audience": 6, "sales_pull": 7, "install_ease": 7, "exclusivity": 6},
    "Professional Services":      {"dwell": 7,  "traffic": 5, "audience": 9, "sales_pull": 8, "install_ease": 8, "exclusivity": 7},
    "Education":                  {"dwell": 7,  "traffic": 7, "audience": 6, "sales_pull": 6, "install_ease": 5, "exclusivity": 5},
    "Travel & Tourism":           {"dwell": 7,  "traffic": 8, "audience": 7, "sales_pull": 7, "install_ease": 5, "exclusivity": 6},
    "Non-Profit/Community":       {"dwell": 6,  "traffic": 6, "audience": 6, "sales_pull": 6, "install_ease": 6, "exclusivity": 4},
    "Retail & Boutique":          {"dwell": 4,  "traffic": 7, "audience": 7, "sales_pull": 7, "install_ease": 8, "exclusivity": 6},
    "Liquor/Wine/Beer":           {"dwell": 3,  "traffic": 8, "audience": 6, "sales_pull": 7, "install_ease": 8, "exclusivity": 7},
    "Gas/Grocery":                {"dwell": 3,  "traffic": 10, "audience": 5, "sales_pull": 6, "install_ease": 7, "exclusivity": 5},
    "Other":                      {"dwell": 5,  "traffic": 5, "audience": 5, "sales_pull": 5, "install_ease": 6, "exclusivity": 5},
}

DEFAULT_BASELINE = CATEGORY_BASELINES["Other"]

# Score bands. "A" venues are worth a rep's morning; "D" venues are worth a
# flyer on the way past.
GRADES = [
    (85, "A", "Knock this week", "#2E8B57"),
    (72, "B", "Work this month", "#C5A55A"),
    (58, "C", "Keep on the list", "#E89E3C"),
    (0,  "D", "Only if you're already there", "#888888"),
]


def list_territories() -> list[str]:
    return list(TERRITORIES.keys())


def get_territory(name: str) -> dict:
    return TERRITORIES.get(name, {})


def list_zones(territory: str) -> list[tuple[str, dict]]:
    """Zones for a territory, in walk order (priority ascending)."""
    zones = get_territory(territory).get("zones", {})
    return sorted(zones.items(), key=lambda kv: kv[1].get("priority", 99))


def get_zone(territory: str, zone: str) -> dict:
    return get_territory(territory).get("zones", {}).get(zone, {})


def category_baseline(category: str) -> dict:
    return dict(CATEGORY_BASELINES.get(category, DEFAULT_BASELINE))


def grade_for(score: float) -> tuple[str, str, str]:
    """Return (letter, what-to-do, color) for a 0-100 score."""
    for floor, letter, action, color in GRADES:
        if score >= floor:
            return letter, action, color
    return "D", GRADES[-1][2], GRADES[-1][3]


def score_candidate(candidate: dict) -> dict:
    """Score one venue 0-100 on host desirability.

    Args:
        candidate: needs ``category``; may carry a ``ratings`` dict of
            per-factor 0-10 overrides, plus ``zone`` for the zone bonus.

    Returns:
        ``{"score", "grade", "action", "color", "ratings", "contributions"}``.
        ``ratings`` is what was actually scored — baseline merged with any
        overrides — so the page can show a rep where a number came from.
    """
    ratings = category_baseline(candidate.get("category", "Other"))
    for key, val in (candidate.get("ratings") or {}).items():
        if key in FACTORS and val is not None:
            ratings[key] = max(0, min(10, float(val)))

    contributions = {
        key: round(ratings[key] / 10 * meta["weight"], 1)
        for key, meta in FACTORS.items()
    }
    score = round(sum(contributions.values()), 1)

    letter, action, color = grade_for(score)
    return {
        "score": score,
        "grade": letter,
        "action": action,
        "color": color,
        "ratings": ratings,
        "contributions": contributions,
    }


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Score every candidate and return them best-first.

    Each returned dict is the candidate with its score fields merged in, so
    the caller keeps whatever else it was carrying (notes, address, contact).
    """
    scored = []
    for cand in candidates:
        result = score_candidate(cand)
        scored.append({**cand, **result})
    return sorted(scored, key=lambda c: c["score"], reverse=True)


def zone_priority_note(territory: str, zone: str) -> str:
    """One line a rep can paste into a deal note explaining the zone's rank."""
    info = get_zone(territory, zone)
    if not info:
        return ""
    return (
        f"Zone {info.get('priority', '?')} of "
        f"{len(get_territory(territory).get('zones', {}))} — {info.get('profile', '')}"
    )


def to_host_pipeline_row(candidate: dict, territory: str, zone: str,
                         rep: str, source: str = "territory_map") -> dict:
    """Shape a scored candidate into a ``pipeline_opportunities`` host row.

    Mirrors what the Host Pipeline page writes by hand (``deal_type='host'``,
    stage ``identified``), so a seeded venue is indistinguishable from one a
    rep typed in. The score and zone ride along in the notes because the host
    pipeline has no column of its own for them.
    """
    note_lines = []
    if candidate.get("why"):
        note_lines.append(candidate["why"])
    note_lines.append(
        f"Host score {candidate.get('score', '?')}/100 "
        f"(grade {candidate.get('grade', '?')}) — {candidate.get('action', '')}"
    )
    zone_note = zone_priority_note(territory, zone)
    if zone_note:
        note_lines.append(f"{territory} / {zone}. {zone_note}")
    if candidate.get("notes"):
        note_lines.append(candidate["notes"])

    return {
        "deal_type": "host",
        "business_name": candidate.get("business_name") or candidate.get("name", "Unknown"),
        "contact_name": candidate.get("contact_name") or None,
        "contact_phone": candidate.get("contact_phone") or None,
        "contact_email": candidate.get("contact_email") or None,
        "city": candidate.get("city") or zone,
        "industry": candidate.get("category") or None,
        "address": candidate.get("address") or None,
        "website": candidate.get("website") or None,
        "stage": "identified",
        "source": source,
        "assigned_rep": rep,
        "probability": 10,
        "notes": "\n".join(n for n in note_lines if n),
    }


def research_prompt(territory: str, zone: str, category: str, count: int) -> str:
    """Build the Claude prompt that researches host candidates in a zone.

    Same shape as the Prospector's advertiser prompt, pointed at hosts: we are
    asking for rooms with waiting people, not businesses with ad budgets.
    """
    info = get_zone(territory, zone)
    anchors = ", ".join(info.get("anchors", [])) or zone
    state = get_territory(territory).get("state", "")

    return f"""You are a field research assistant for MCTV Elite Advertising, an indoor digital billboard network expanding into {territory}, {state}.

We are looking for HOST VENUES — businesses that would let us install a free digital screen in their lobby, waiting area, or dining room. The host pays nothing; we sell the advertising.

Find exactly {count} REAL {category} businesses in the {zone} area of {territory} ({state}), near: {anchors}.

What makes a good host, in order:
1. Customers WAIT there with nothing to do (waiting rooms, chairs, a bar, a line)
2. Real daily foot traffic
3. Locally owned, so one person can say yes — avoid national chains
4. Wall space and power near where people sit

For each venue provide:
1. business_name: the actual business name
2. address: street address if known, otherwise the nearest cross street or center
3. contact_name: owner or manager name if known, otherwise "Owner"
4. dwell_note: what customers do while they wait there, and roughly how long
5. why: one sentence on why this is a good MCTV host
6. website: website URL if known, otherwise an empty string
7. dwell: 0-10 rating of captive wait time
8. traffic: 0-10 rating of daily foot traffic
9. install_ease: 0-10 rating of how easy the screen install and the yes will be

Return ONLY a valid JSON array of objects. No markdown, no explanation.
Example: [{{"business_name": "Poplar Tire & Auto", "address": "1234 Poplar Ave", "contact_name": "Owner", "dwell_note": "Customers wait 45-90 min in the lobby for oil changes", "why": "Long captive waits and a wall of chairs facing one direction", "website": "", "dwell": 10, "traffic": 6, "install_ease": 9}}]"""
