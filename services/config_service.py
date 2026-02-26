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
