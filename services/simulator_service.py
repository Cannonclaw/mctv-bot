# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Audience & package simulator engine.

Pure-function build (no Streamlit imports). Given a list of venue keys from
``data/network_dashboard.json``, returns aggregated impressions, plays, CPM,
and a blended demographic profile, plus a recommended pricing tier.

Reuses:
  - services.config_service.calculate_cpm + get_all_tiers
  - services.ntv360_service.get_play_data_for_report (real plays when present)
  - services.census_service.get_demographics (ZIP-level ACS data)
  - data/venue_audience_profiles.json (per-category multipliers)
"""

import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path

from services.config_service import (
    calculate_cpm,
    get_all_tiers,
    get_days_per_month,
    get_hours_per_day,
    load_config,
)
from services.census_service import get_demographics_for_zips
from models.simulator_data import (
    DemographicBlend,
    ScenarioResult,
    TierRecommendation,
    VenueScenario,
)

logger = logging.getLogger(__name__)

DASHBOARD_PATH = Path(__file__).parent.parent / "data" / "network_dashboard.json"
PROFILES_PATH = Path(__file__).parent.parent / "data" / "venue_audience_profiles.json"
GEOCODES_PATH = Path(__file__).parent.parent / "data" / "venue_geocodes.json"

# Plays-per-hour assumption per screen when NTV360 data is unavailable.
# Falls back to config.network.plays_per_hour, default 4.
DEFAULT_PLAYS_PER_HOUR = 4

# Address parser: trailing "STATE ZIP" e.g. "...Oxford MS 38655"
_ZIP_RE = re.compile(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$")


# ── Data loaders (cached at module level) ────────────────────────────────────

_dashboard_cache: dict | None = None
_profiles_cache: dict | None = None
_geocodes_cache: dict | None = None


def load_dashboard() -> dict:
    """Load the venue dashboard from disk. Cached after first read."""
    global _dashboard_cache
    if _dashboard_cache is None:
        try:
            with open(DASHBOARD_PATH, encoding="utf-8") as f:
                _dashboard_cache = json.load(f)
        except FileNotFoundError:
            logger.warning("network_dashboard.json missing at %s", DASHBOARD_PATH)
            _dashboard_cache = {"venues": {}}
    return _dashboard_cache


def load_audience_profiles() -> dict:
    """Load the per-category audience-multiplier profiles."""
    global _profiles_cache
    if _profiles_cache is None:
        try:
            with open(PROFILES_PATH, encoding="utf-8") as f:
                _profiles_cache = json.load(f)
        except FileNotFoundError:
            logger.warning("venue_audience_profiles.json missing at %s", PROFILES_PATH)
            _profiles_cache = {}
    return _profiles_cache


def load_geocodes() -> dict:
    """Load the venue geocode sidecar (key -> {lat, lon, matched_address})."""
    global _geocodes_cache
    if _geocodes_cache is None:
        try:
            with open(GEOCODES_PATH, encoding="utf-8") as f:
                _geocodes_cache = json.load(f)
        except FileNotFoundError:
            logger.warning("venue_geocodes.json missing — run scripts/geocode_venues.py")
            _geocodes_cache = {}
    return _geocodes_cache


def list_venues() -> list[dict]:
    """Return all venues as a list of dicts with key, city, and lat/lon."""
    dash = load_dashboard()
    geo = load_geocodes()
    out = []
    for key, v in dash.get("venues", {}).items():
        city, zip_code = _parse_address(v.get("address", ""))
        gc = geo.get(key) or {}
        out.append({
            "key": key,
            "host_name": v.get("host_name", key),
            "category": v.get("category", ""),
            "general_category": v.get("general_category", "Other"),
            "address": v.get("address", ""),
            "city": city,
            "zip": zip_code,
            "license_count": int(v.get("license_count", 1) or 1),
            "traffic": float(v.get("traffic", 0) or 0),
            "dwell_time": float(v.get("dwell_time", 0) or 0),
            "impressions": float(v.get("impressions", 0) or 0),
            "lat": float(gc.get("lat") or 0),
            "lon": float(gc.get("lon") or 0),
        })
    out.sort(key=lambda r: r["host_name"])
    return out


def _parse_address(address: str) -> tuple[str, str]:
    """Extract (city, zip) from an address string. Returns ('', '') if unmatched."""
    if not address:
        return "", ""
    m = _ZIP_RE.search(address.strip())
    zip_code = m.group(2) if m else ""
    # City is the last comma-separated segment before "STATE ZIP"
    city = ""
    if "," in address:
        # e.g. "450 MS-12 Suite B, Starkville MS 39759"
        last_segment = address.rsplit(",", 1)[-1].strip()
        # Strip the trailing "MS 39759" if present
        cleaned = _ZIP_RE.sub("", last_segment).strip()
        city = cleaned
    return city, zip_code


# ── Engine ───────────────────────────────────────────────────────────────────

def build_scenario(
    venue_keys: list[str],
    custom_monthly_rate: float = 0.0,
    target_month: str | None = None,
) -> ScenarioResult:
    """Build a full scenario from a list of venue keys.

    Args:
        venue_keys: Keys into ``data/network_dashboard.json``'s ``venues`` map.
        custom_monthly_rate: If >0, overrides the recommended tier's rate.
        target_month: YYYY-MM for NTV360 lookup. Defaults to current month.

    Returns:
        ScenarioResult with per-venue + aggregate metrics + recommendation.
    """
    dash = load_dashboard().get("venues", {})
    profiles = load_audience_profiles()
    geocodes = load_geocodes()
    config = load_config()

    if not target_month:
        target_month = date.today().strftime("%Y-%m")

    # Pull NTV360 plays once (single Supabase round-trip)
    ntv360 = _safe_get_ntv360(target_month)

    hours_per_day = get_hours_per_day(config)
    days_per_month = get_days_per_month(config)
    plays_per_hour = int(config.get("network", {}).get("plays_per_hour", DEFAULT_PLAYS_PER_HOUR))

    # Resolve venues + collect ZIPs for one Census batch
    resolved = []
    zips_needed: list[str] = []
    for key in venue_keys:
        v = dash.get(key)
        if not v:
            logger.warning("Simulator: unknown venue key %s", key)
            continue
        city, zip_code = _parse_address(v.get("address", ""))
        resolved.append((key, v, city, zip_code))
        if zip_code:
            zips_needed.append(zip_code)

    zip_demos = get_demographics_for_zips(zips_needed) if zips_needed else {}

    # Build per-venue scenarios
    venues: list[VenueScenario] = []
    for key, v, city, zip_code in resolved:
        venues.append(_build_venue_scenario(
            key=key,
            v=v,
            city=city,
            zip_code=zip_code,
            zip_demo=zip_demos.get(zip_code, {}),
            profiles=profiles,
            geocode=geocodes.get(key, {}),
            ntv360=ntv360,
            hours_per_day=hours_per_day,
            days_per_month=days_per_month,
            plays_per_hour=plays_per_hour,
        ))

    # Aggregate
    total_screens = sum(v.license_count for v in venues)
    total_impressions = sum(v.monthly_impressions for v in venues)
    total_plays = sum(v.monthly_plays for v in venues)
    total_traffic = sum(v.monthly_traffic for v in venues)
    cities = sorted({v.city for v in venues if v.city})

    blend = _blend_demographics(venues, zip_demos)
    recommendation = recommend_tier(
        config=config,
        screen_count=total_screens,
        total_impressions=total_impressions,
        custom_monthly_rate=custom_monthly_rate,
    )

    return ScenarioResult(
        venues=venues,
        total_screens=total_screens,
        total_monthly_impressions=total_impressions,
        total_monthly_plays=total_plays,
        total_monthly_traffic=total_traffic,
        cities=cities,
        blend=blend,
        recommendation=recommendation,
    )


def _safe_get_ntv360(target_month: str) -> dict:
    """Fetch NTV360 plays defensively — never raise to caller."""
    try:
        from services.ntv360_service import get_play_data_for_report
        return get_play_data_for_report(target_month) or {}
    except Exception as e:
        logger.debug("NTV360 lookup skipped: %s", e)
        return {}


def _build_venue_scenario(*, key, v, city, zip_code, zip_demo, profiles,
                          geocode, ntv360, hours_per_day, days_per_month,
                          plays_per_hour) -> VenueScenario:
    license_count = int(v.get("license_count", 1) or 1)
    traffic = float(v.get("traffic", 0) or 0)
    dwell = float(v.get("dwell_time", 0) or 0)

    # Impressions: dashboard pre-computes (Traffic × Dwell × Licenses / 15) but
    # we recompute in case the formula evolves. Fall back to the cached value
    # if dashboard fields are missing.
    impressions = (traffic * dwell * license_count / 15.0) if (traffic and dwell) else float(v.get("impressions", 0) or 0)

    # Plays: prefer real NTV360, else model from network defaults.
    venue_plays_lookup = ntv360.get("venue_plays", {}) if ntv360 else {}
    host_lower = (v.get("host_name", "") or key).strip().lower()
    real = venue_plays_lookup.get(host_lower)
    if real and int(real.get("total_plays", 0)) > 0:
        plays = int(real["total_plays"])
        plays_source = "ntv360"
    else:
        plays = int(plays_per_hour * hours_per_day * days_per_month * license_count)
        plays_source = "modeled"

    general_cat = v.get("general_category", "Other") or "Other"
    profile = profiles.get(general_cat) or profiles.get("Other") or {}
    age_pct, income_pct, education_pct = _apply_profile_to_zip(zip_demo, profile)

    return VenueScenario(
        venue_key=key,
        host_name=v.get("host_name", key),
        category=v.get("category", ""),
        general_category=general_cat,
        address=v.get("address", ""),
        city=city,
        zip_code=zip_code,
        license_count=license_count,
        lat=float(geocode.get("lat") or 0),
        lon=float(geocode.get("lon") or 0),
        monthly_traffic=traffic,
        dwell_time_minutes=dwell,
        monthly_impressions=impressions,
        monthly_plays=plays,
        plays_source=plays_source,
        age_pct=age_pct,
        income_pct=income_pct,
        education_pct=education_pct,
        audience_tags=list(profile.get("tags", [])),
    )


# ── Demographic blending ─────────────────────────────────────────────────────

def _apply_profile_to_zip(zip_demo: dict, profile: dict) -> tuple[dict, dict, dict]:
    """Apply category multipliers to ZIP baseline distributions, then renormalize."""
    age_keys = ["under_18", "18_24", "25_34", "35_44", "45_54", "55_64", "65_plus"]
    income_keys = ["under_35k", "35k_50k", "50k_75k", "75k_100k", "100k_150k", "over_150k"]
    edu_keys = ["high_school_or_less", "some_college", "bachelors", "graduate"]

    age_base = zip_demo.get("age_pct", {}) if zip_demo else {}
    income_base = zip_demo.get("income_pct", {}) if zip_demo else {}
    edu_base = zip_demo.get("education_pct", {}) if zip_demo else {}

    age_mult = profile.get("age_multipliers") or [1.0] * len(age_keys)
    inc_mult = profile.get("income_multipliers") or [1.0] * len(income_keys)
    edu_mult = profile.get("education_multipliers") or [1.0] * len(edu_keys)

    age_skewed = _renormalize({
        k: float(age_base.get(k, 0)) * float(age_mult[i] if i < len(age_mult) else 1.0)
        for i, k in enumerate(age_keys)
    })
    income_skewed = _renormalize({
        k: float(income_base.get(k, 0)) * float(inc_mult[i] if i < len(inc_mult) else 1.0)
        for i, k in enumerate(income_keys)
    })
    edu_skewed = _renormalize({
        k: float(edu_base.get(k, 0)) * float(edu_mult[i] if i < len(edu_mult) else 1.0)
        for i, k in enumerate(edu_keys)
    })

    return age_skewed, income_skewed, edu_skewed


def _renormalize(weighted: dict) -> dict:
    """Scale a dict of weights so values sum to 100. Returns zeros if total=0."""
    total = sum(weighted.values())
    if total <= 0:
        return {k: 0.0 for k in weighted}
    return {k: round(v / total * 100, 1) for k, v in weighted.items()}


def _blend_demographics(venues: list[VenueScenario],
                        zip_demos: dict[str, dict]) -> DemographicBlend:
    """Impressions-weighted blend of per-venue demographic distributions."""
    if not venues:
        return DemographicBlend()

    age_keys = ["under_18", "18_24", "25_34", "35_44", "45_54", "55_64", "65_plus"]
    income_keys = ["under_35k", "35k_50k", "50k_75k", "75k_100k", "100k_150k", "over_150k"]
    edu_keys = ["high_school_or_less", "some_college", "bachelors", "graduate"]

    age_acc = {k: 0.0 for k in age_keys}
    inc_acc = {k: 0.0 for k in income_keys}
    edu_acc = {k: 0.0 for k in edu_keys}
    weight_sum = 0.0
    income_dollar_sum = 0.0
    income_weight = 0.0
    tags: set[str] = set()
    cities: set[str] = set()

    for v in venues:
        weight = max(v.monthly_impressions, 1.0)
        weight_sum += weight
        for k in age_keys:
            age_acc[k] += v.age_pct.get(k, 0) * weight
        for k in income_keys:
            inc_acc[k] += v.income_pct.get(k, 0) * weight
        for k in edu_keys:
            edu_acc[k] += v.education_pct.get(k, 0) * weight
        tags.update(v.audience_tags)
        if v.city:
            cities.add(v.city)

        zd = zip_demos.get(v.zip_code, {})
        median = int(zd.get("median_household_income", 0) or 0)
        if median > 0:
            income_dollar_sum += median * weight
            income_weight += weight

    if weight_sum <= 0:
        return DemographicBlend()

    age_pct = _renormalize({k: age_acc[k] / weight_sum for k in age_keys})
    income_pct = _renormalize({k: inc_acc[k] / weight_sum for k in income_keys})
    edu_pct = _renormalize({k: edu_acc[k] / weight_sum for k in edu_keys})
    median_blend = int(income_dollar_sum / income_weight) if income_weight > 0 else 0

    return DemographicBlend(
        age_pct=age_pct,
        income_pct=income_pct,
        education_pct=edu_pct,
        median_household_income_blended=median_blend,
        audience_tags=sorted(tags),
        cities_covered=sorted(cities),
    )


# ── Tier recommendation ──────────────────────────────────────────────────────

def recommend_tier(
    config: dict,
    screen_count: int,
    total_impressions: float,
    custom_monthly_rate: float = 0.0,
) -> TierRecommendation:
    """Snap to the closest existing pricing tier by screen count.

    Picks the tier whose ``screens`` is the largest value <= ``screen_count``.
    For very small selections (<10), uses the smallest tier with prorated CPM.
    """
    tiers = get_all_tiers(config) or []
    if not tiers:
        return TierRecommendation(
            tier_index=0, tier_name="Custom", screen_count=screen_count,
            monthly_rate=custom_monthly_rate, cost_per_screen=0.0,
            cpm=calculate_cpm(custom_monthly_rate, total_impressions),
            plays_per_month_label="—",
            custom_override_rate=custom_monthly_rate,
        )

    # Sort tiers ascending by screens
    sorted_tiers = sorted(enumerate(tiers), key=lambda kv: int(kv[1].get("screens", 0)))
    chosen_idx, chosen = sorted_tiers[0]
    for idx, t in sorted_tiers:
        if int(t.get("screens", 0)) <= screen_count:
            chosen_idx, chosen = idx, t

    monthly_rate = float(chosen.get("monthly_rate", 0))
    cost_per_screen = float(chosen.get("cost_per_screen", 0))
    plays_label = str(chosen.get("plays_per_month", ""))

    effective_rate = custom_monthly_rate if custom_monthly_rate > 0 else monthly_rate
    cpm = calculate_cpm(effective_rate, total_impressions)

    return TierRecommendation(
        tier_index=chosen_idx,
        tier_name=str(chosen.get("name", "")),
        screen_count=int(chosen.get("screens", screen_count)),
        monthly_rate=monthly_rate,
        cost_per_screen=cost_per_screen,
        cpm=cpm,
        plays_per_month_label=plays_label,
        custom_override_rate=custom_monthly_rate,
    )


# ── Persistence ──────────────────────────────────────────────────────────────

def save_scenario(
    *,
    prospect_name: str,
    prospect_email: str = "",
    prospect_phone: str = "",
    prospect_business: str = "",
    venue_keys: list[str],
    result: ScenarioResult,
    custom_monthly_rate: float = 0.0,
    created_by: str = "",
    assigned_rep: str = "",
    notes: str = "",
) -> dict | None:
    """Persist a scenario to ``simulator_scenarios``. Returns the saved row."""
    try:
        from services.supabase_client import insert_row
    except ImportError:
        logger.error("supabase_client not available — cannot save scenario")
        return None

    payload = {
        "prospect_name": prospect_name,
        "prospect_email": prospect_email or None,
        "prospect_phone": prospect_phone or None,
        "prospect_business": prospect_business or None,
        "venue_keys": venue_keys,
        "computed_metrics": result.to_dict(),
        "recommended_tier": result.recommendation.to_dict() if result.recommendation else {},
        "custom_monthly_rate": float(custom_monthly_rate) if custom_monthly_rate > 0 else None,
        "created_by": created_by or None,
        "assigned_rep": assigned_rep or None,
        "notes": notes or None,
    }
    return insert_row("simulator_scenarios", payload)


def load_scenario_by_token(share_token: str) -> dict | None:
    """Fetch a saved scenario by its share token. Bumps view_count + viewed_at."""
    try:
        from services.supabase_client import query_table, update_row
    except ImportError:
        return None

    rows = query_table(
        "simulator_scenarios",
        select="*",
        filters={"share_token": share_token},
        limit=1,
    )
    if not rows:
        return None
    scenario = rows[0]

    # Best-effort view tracking — never block return on failure.
    try:
        update_row(
            "simulator_scenarios",
            scenario["id"],
            {
                "viewed_at": datetime.now(timezone.utc).isoformat(),
                "view_count": int(scenario.get("view_count", 0) or 0) + 1,
            },
        )
    except Exception as e:
        logger.debug("view_count update failed: %s", e)

    # computed_metrics may come back as JSON string
    cm = scenario.get("computed_metrics")
    if isinstance(cm, str):
        try:
            scenario["computed_metrics"] = json.loads(cm)
        except (json.JSONDecodeError, TypeError):
            scenario["computed_metrics"] = {}
    rt = scenario.get("recommended_tier")
    if isinstance(rt, str):
        try:
            scenario["recommended_tier"] = json.loads(rt)
        except (json.JSONDecodeError, TypeError):
            scenario["recommended_tier"] = {}
    vk = scenario.get("venue_keys")
    if isinstance(vk, str):
        try:
            scenario["venue_keys"] = json.loads(vk)
        except (json.JSONDecodeError, TypeError):
            scenario["venue_keys"] = []

    return scenario


def list_recent_scenarios(limit: int = 25) -> list[dict]:
    """Recent saved scenarios for the internal sidebar."""
    try:
        from services.supabase_client import query_table
        return query_table(
            "simulator_scenarios",
            select="id,prospect_name,prospect_business,share_token,created_at,view_count",
            order="-created_at",
            limit=limit,
        )
    except Exception:
        return []
