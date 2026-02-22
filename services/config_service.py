"""Configuration loader and manager."""

import json
from pathlib import Path


CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"
PROMPTS_PATH = CONFIG_DIR / "prompts.json"


def load_config() -> dict:
    """Load the master config.json."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save modified config back to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_prompts() -> dict:
    """Load the prompt templates from prompts.json."""
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


def get_pricing_tier(config: dict, index: int) -> dict:
    """Get a pricing tier by index."""
    tiers = config["pricing"]["elite_tiers"]
    if 0 <= index < len(tiers):
        return tiers[index]
    return tiers[0]


def get_all_tiers(config: dict) -> list:
    """Get all pricing tiers."""
    return config["pricing"]["elite_tiers"]
