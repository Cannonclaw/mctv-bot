# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host territory mapping and host-desirability scoring.

New-territory expansion starts with one question: which venues do we want a
screen in, and in what order do we knock on their doors? This module answers
it in two halves.

**The map** — ``TERRITORIES`` breaks the expansion footprint into named zones
with the anchors, demographics, and venue density that make a zone worth
working. Zones are ordered by ``priority`` (zone 1 gets walked first — a
cluster of screens in one corridor sells far better than the same count
scattered), and each carries a ``status``: ``granted`` (build now),
``granted-transition`` (ours per the Aug 2026 NTV360 amendment, but the
incumbent operator has screens to transition first), ``verify-grant`` (check
the amendment map), ``partner`` (the incumbent's turf — access via the
partnership, never direct outreach), or ``future`` (not granted; a later ask).

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
    "Mid-South Expansion": {
        "state": "MS/TN",
        "status": "granted",
        "description": (
            "The territory added by the NTV360 franchise amendment signed "
            "Aug 20-21, 2026 (replaces Attachment 1 in its entirety), plus the "
            "adjacent partner and future zones it borders. Granted: Senatobia, "
            "part of Batesville + all of Sardis Lake, and the Bartlett / "
            "Lakeland / Germantown TN suburbs. DeSoto County remains the "
            "incumbent operator's; Memphis proper is a future ask."
        ),
        "zones": {
            "Batesville / Sardis Lake": {
                "priority": 1,
                "status": "granted",
                "anchors": ["Hwy 6 / I-55 junction", "Sardis Lake Marina & Blackjack Rd",
                            "John W. Kyle State Park", "Batesville Square", "Batesville Civic Center"],
                "profile": "Panola County retail hub (~33K county trade area) plus the most "
                           "developed of the four North MS Corps lakes.",
                "why_first": (
                    "25 minutes down Hwy 6 from Oxford — installs and service runs "
                    "piggyback on existing routes, and no indoor network operates in "
                    "the county. Two plays: the year-round Batesville hub (square, "
                    "medical, Hwy 6 retail), and the seasonal lake economy, where a "
                    "handful of choke-point venues (marina, Dam Store, state park "
                    "corridor) capture nearly every visitor. Sign lake venues over "
                    "winter so screens are live for February tournament season."
                ),
                "demographics": {
                    "population": "Batesville ~7.4K city / Panola Co ~32.8K; Sardis town 1.7K",
                    "income": "MHI $51.7K city / $45.9K county — thinner ad budgets; sell hub traffic",
                    "note": "Employment growing against flat population: GE Aerospace +100 jobs, "
                            "Yancey +250; four Corps lakes draw ~3.2M visitors/yr regionally. "
                            "Amendment grants PART of Batesville — confirm exact boundary.",
                },
                "target_categories": [
                    "Bar/Restaurant", "Medical & Dental", "Travel & Tourism",
                    "Gas/Grocery", "Auto Shop", "Barbershop/Salon",
                ],
            },
            "Senatobia": {
                "priority": 2,
                "status": "granted",
                "anchors": ["NWCC main campus (record 8,250 enrollment)", "Heindl Center (1,203 seats)",
                            "Main St / courthouse square", "I-55 exits"],
                "profile": "Mini college town 30 min south of Memphis; the NWCC anchor market.",
                "why_first": (
                    "The NWCC relationship (2 years, deck presented June 2026) is the "
                    "single highest-leverage signature on the board: one contract seeds "
                    "screens across Senatobia, the Heindl Center, the Southaven DeSoto "
                    "Center, and the Oxford tech center — and gives every later "
                    "institutional pitch its reference. Campus first, then the square "
                    "cluster off the campus credibility."
                ),
                "demographics": {
                    "population": "City ~8.3K / Tate Co ~28.6K; NWCC enrollment 8,250 (+26.5% in 4 yrs)",
                    "income": "MHI $54K city / $64K county",
                    "note": "Growth is institutional (NWCC, ABB) rather than residential. "
                            "Confirm whether the grant is Senatobia proper or all of Tate County.",
                },
                "target_categories": [
                    "Education", "Bar/Restaurant", "Medical & Dental",
                    "Barbershop/Salon", "Health & Fitness",
                ],
            },
            "Germantown": {
                "priority": 3,
                "status": "granted-transition",
                "anchors": ["Poplar Ave corridor", "Methodist Germantown / Campbell Clinic",
                            "Saddle Creek", "Forest Hill Irene retail"],
                "profile": "The richest audience in the Mid-South: ~41K people at ~$150K MHI.",
                "why_first": (
                    "Highest advertiser budgets per capita of any market on the map, and "
                    "strict local sign ordinances suppress outdoor billboards — indoor "
                    "screens are the only DOOH game in town. GATE: the incumbent "
                    "operator has existing screens here; build only after N-Compass has "
                    "communicated the territory change and a transition path (buy, wind "
                    "down, or partner-service) is agreed."
                ),
                "demographics": {
                    "population": "~41.3K (2020 census)",
                    "income": "MHI ~$149.9K — 3rd highest in TN",
                    "note": "Incumbent (Desoto Local) screens present per her location map — "
                            "transition required before host outreach.",
                },
                "target_categories": [
                    "Medical & Dental", "Professional Services", "Bar/Restaurant",
                    "Health & Fitness", "Barbershop/Salon",
                ],
            },
            "Bartlett": {
                "priority": 4,
                "status": "granted-transition",
                "anchors": ["Stage Rd corridor (~44.7K AADT)", "Bartlett Station / old town",
                            "Wolfchase fringe"],
                "profile": "Mature family suburb of ~57K at ~$101K MHI; deep local-business bench.",
                "why_first": (
                    "Volume flank of the TN cluster: dense locally-owned restaurants, "
                    "dental offices, and service businesses along Stage Rd. Same "
                    "incumbent-transition gate as Germantown; build the Bartlett and "
                    "Lakeland clusters on the same service day."
                ),
                "demographics": {
                    "population": "~57.7K (2020 census)",
                    "income": "MHI ~$100.7K",
                    "note": "Incumbent screens present per her location map.",
                },
                "target_categories": [
                    "Bar/Restaurant", "Medical & Dental", "Auto Shop",
                    "Health & Fitness", "Family Rec & Entertainment",
                ],
            },
            "Lakeland": {
                "priority": 5,
                "status": "granted-transition",
                "anchors": ["The Lake District", "US-64 corridor"],
                "profile": "Fastest-growing, most affluent NE suburb: ~14.5K at ~$116K+ MHI.",
                "why_first": (
                    "Small but surging (+110% since 2000) with almost no existing indoor "
                    "inventory. The Lake District is a single-landlord, multi-venue "
                    "anchor conversation. Rides along with Bartlett on install and "
                    "service days."
                ),
                "demographics": {
                    "population": "~14.5K",
                    "income": "MHI ~$116K+ (avg ~$140K), ~80% homeownership",
                    "note": "Incumbent screens present per her location map.",
                },
                "target_categories": [
                    "Bar/Restaurant", "Retail & Boutique", "Health & Fitness",
                    "Medical & Dental",
                ],
            },
            "Collierville": {
                "priority": 6,
                "status": "verify-grant",
                "anchors": ["Town Square", "W Poplar corridor", "Carriage Crossing",
                            "Baptist Collierville"],
                "profile": "~51K at ~$139K MHI — #1 income among TN cities over 50K.",
                "why_first": (
                    "The natural sixth zone if the Attachment 1 map covers it — a "
                    "walkable historic square (the Oxford playbook) plus the metro's "
                    "second-richest audience. NOT confirmed in the grant: check the "
                    "amendment map before any outreach."
                ),
                "demographics": {
                    "population": "~51.3K (2020 census)",
                    "income": "MHI ~$138.6K, poverty 3.2%",
                    "note": "Grant status unconfirmed — verify against Attachment 1.",
                },
                "target_categories": [
                    "Bar/Restaurant", "Retail & Boutique", "Medical & Dental",
                    "Professional Services",
                ],
            },
            "DeSoto County (partner zone)": {
                "priority": 7,
                "status": "partner",
                "anchors": ["Olive Branch / Goodman Rd", "Hernando square", "Southaven / Silo Square",
                            "NWCC DeSoto Center", "Snowden Grove"],
                "profile": "MS's fastest-growing county (~199K) — the incumbent operator's home turf.",
                "why_first": (
                    "NOT ours to build: DeSoto County stays with the incumbent N-Compass "
                    "operator (Desoto Local, ~35 screens). Access runs through the "
                    "partnership — cross-sell our advertisers onto her screens and hers "
                    "onto ours, and service the NWCC DeSoto Center jointly. No MCTV host "
                    "outreach inside this county."
                ),
                "demographics": {
                    "population": "County ~199K; Olive Branch ~42-43K, Southaven ~56K, Hernando ~18.5K",
                    "income": "OB ~$90K / Southaven ~$70K (est.) / Hernando ~$77K",
                    "note": "Fastest-growing county in Mississippi, 25 straight years of growth.",
                },
                "target_categories": [],
            },
            "East Memphis (future)": {
                "priority": 8,
                "status": "future",
                "anchors": ["Poplar corridor offices", "Mendenhall / Brookhaven Circle",
                            "OrthoSouth / medical groups"],
                "profile": "The advertiser capital of the Mid-South — corridor zips at $86-124K MHI.",
                "why_first": (
                    "Not in the grant. The prize is advertiser budgets more than host "
                    "count: regional ad decisions are made here. Return to N-Compass "
                    "with expansion performance as the proof for a Memphis-proper ask."
                ),
                "demographics": {
                    "population": "Memphis ~606-611K (declining); corridor is the stable affluent quadrant",
                    "income": "Corridor zips $86K-$124K vs $52K citywide",
                    "note": "Future ask — no rights today.",
                },
                "target_categories": [],
            },
            "Memphis core (future)": {
                "priority": 9,
                "status": "future",
                "anchors": ["Overton Square / Cooper-Young", "Crosstown Concourse",
                            "Downtown / Beale", "U of M Highland strip"],
                "profile": "10x audience, first named indoor competitor (Social Indoor).",
                "why_first": (
                    "Not in the grant, and the only market with a direct free-screen "
                    "competitor. If granted later: beachhead via single-landlord "
                    "anchors (Crosstown, JCC), never scattered singles."
                ),
                "demographics": {
                    "population": "Shelby Co ~910K; Midtown 38104 ~22.6K",
                    "income": "City MHI ~$52K; $23.7B capital investment landed in 2025",
                    "note": "Future ask — no rights today. Social Indoor active in the DMA.",
                },
                "target_categories": [],
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
