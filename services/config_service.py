# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Configuration loader and manager."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"
PROMPTS_PATH = CONFIG_DIR / "prompts.json"


def load_config() -> dict:
    """Load the master config.json. Returns empty dict if file is missing."""
    if not CONFIG_PATH.exists():
        logger.warning("Config file not found: %s — returning empty dict", CONFIG_PATH)
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save modified config back to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_prompts() -> dict:
    """Load the prompt templates from prompts.json. Returns empty dict if file is missing."""
    if not PROMPTS_PATH.exists():
        logger.warning("Prompts file not found: %s — returning empty dict", PROMPTS_PATH)
        return {}
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_team_member(config: dict, name: str) -> dict:
    """Find a team member by name."""
    for member in config["team"]:
        if member["name"] == name:
            return member
    return config["team"][0]


def get_team_names(config: dict) -> list:
    """Return list of team member names for dropdowns."""
    return [m["name"] for m in config["team"]]


def get_market_names(config: dict, active_only: bool = True) -> list:
    """Return list of market names."""
    markets = config["markets"]
    if active_only:
        return [k for k, v in markets.items() if v["status"] == "active"]
    return list(markets.keys())


def get_team_first_names(config: dict) -> list:
    """Return list of team member first/display names for dropdowns.

    Derives a short display name from each full team member name:
      'T. Creed Cannon' -> 'Creed'  (skips initials like 'T.')
      'Mary Michael Cannon' -> 'Mary Michael'
      'Swayze Hollingsworth' -> 'Swayze'
    """
    names = []
    for m in config.get("team", []):
        parts = m["name"].split()
        # Drop leading initials like "T."
        while parts and parts[0].endswith("."):
            parts = parts[1:]
        # Last part is surname; everything before it is the display name
        if len(parts) > 1:
            names.append(" ".join(parts[:-1]))
        elif parts:
            names.append(parts[0])
    return names


def get_hours_per_day(config: dict) -> int:
    """Return operating hours per day from config (default 12)."""
    return config.get("network", {}).get("hours_per_day", 12)


def get_days_per_month(config: dict) -> int:
    """Return operating days per month from config (default 30)."""
    return config.get("network", {}).get("days_per_month", 30)


def get_pricing_tier(config: dict, index: int) -> dict:
    """Get a pricing tier by index."""
    tiers = config["pricing"]["elite_tiers"]
    if 0 <= index < len(tiers):
        return tiers[index]
    return tiers[0]


def get_all_tiers(config: dict) -> list:
    """Get all pricing tiers."""
    return config["pricing"]["elite_tiers"]


# ── CPM Helpers ──────────────────────────────────────────────────────────────

def parse_impression_count(impression_str) -> float:
    """Parse '1.9M+' or '409K+' or plain numbers to a float."""
    text = str(impression_str).strip().rstrip("+").replace(",", "")
    if text.upper().endswith("M"):
        return float(text[:-1]) * 1_000_000
    elif text.upper().endswith("K"):
        return float(text[:-1]) * 1_000
    try:
        return float(text)
    except ValueError:
        return 0.0


def get_network_impressions(config: dict) -> float:
    """Get total monthly impressions from config."""
    return parse_impression_count(config["network"]["monthly_impressions"])


def get_total_screens(config: dict) -> int:
    """Get total screen count from config."""
    text = str(config["network"]["total_screens"]).strip().rstrip("+")
    try:
        return int(text)
    except ValueError:
        return 0


def calculate_cpm(monthly_rate: float, impressions: float) -> float:
    """Calculate CPM (Cost Per Thousand Impressions)."""
    if impressions <= 0 or monthly_rate <= 0:
        return 0.0
    return (monthly_rate / impressions) * 1000


def get_tier_impressions(config: dict, screen_count: int) -> float:
    """Estimate monthly impressions for a given screen count."""
    total_screens = get_total_screens(config)
    total_impressions = get_network_impressions(config)
    if total_screens <= 0:
        return 0.0
    return (screen_count / total_screens) * total_impressions


CPM_BENCHMARK_TEXT = (
    "Industry CPM comparison:  Radio $5\u2013$12  |  Print $10\u2013$30  |  "
    "Outdoor/Billboards $3\u2013$8  |  Cable TV $15\u2013$30  |  "
    "Digital display $5\u2013$15  |  Social media $6\u2013$12"
)


# \u2500\u2500 Good / Better / Best tier comparison \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Used by the contract document (generators/contract_generator.py), the client
# portal's package picker (pages/portal_contract.py) and the rep-side preview
# (pages/9_Contracts.py). They MUST agree: the document stars one column and
# the portal pre-selects one radio, and a client who sees two different
# recommendations on the same deal has been given a reason to hesitate.

TIER_COMPARISON_MAX = 3


def tier_number(option, key: str):
    """Numeric field of a tier option, or None when the option doesn't carry it.

    Never raises: these options come back out of a JSONB column and are read
    on the client portal, where a TypeError is a blank page mid-signature.
    Returns None (not a default) for null/blank/non-numeric values -- a figure
    the row doesn't actually carry must never be displayed or written back as
    if it did. Callers decide what "missing" means on their surface.
    """
    if not isinstance(option, dict):
        return None
    v = option.get(key)
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN guard: NaN != NaN


def _tier_screens(option) -> float:
    """Screen count of a tier option as a sort key. Unreadable values sort first."""
    v = tier_number(option, "screens")
    return 0.0 if v is None else v


def order_tier_options(tier_options: list) -> list:
    """Return tier options as a Good -> Better -> Best ladder.

    Sorted by screen count ascending, because the comparison reads
    left-to-right and MCTV's ladder is monotonic (more screens, lower cost
    per screen). Stored order is the rep's click order, which is arbitrary.
    Sorting is idempotent, so an already-ordered list is unchanged.
    Non-dict entries are dropped: every consumer immediately calls .get()
    on each option, and a stray string in the JSONB would crash all three
    surfaces at once.
    """
    if not tier_options or not isinstance(tier_options, list):
        return []
    return sorted((o for o in tier_options if isinstance(o, dict)),
                  key=_tier_screens)


def recommended_tier_index(count: int) -> int:
    """Index of the tier to recommend within an ordered ladder.

    The middle rung, which is what Good/Better/Best anchors on; the
    lower-middle when the count is even. Returns 0 for 2 options and 1 for 3
    \u2014 the two counts the Contracts page allows \u2014 so capped comparisons keep
    their existing behaviour, while a 4- or 5-option contract stored before
    the cap no longer stars the second-cheapest package.
    """
    if count <= 0:
        return 0
    return (count - 1) // 2
