# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""US Census ACS 5-Year demographic lookups by ZIP, with Supabase caching.

Pulls age, household income, and education distributions for a ZIP Code
Tabulation Area (ZCTA) from the Census Bureau public API. Free; an optional
``CENSUS_API_KEY`` env var raises the rate limit.

Cached responses live in ``zip_demographics_cache`` for 90 days.
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

CENSUS_BASE = "https://api.census.gov/data/2022/acs/acs5"
CACHE_TTL_DAYS = 90

# ── ACS variable IDs (5-Year, table B01001 / B19001 / B15003) ────────────────
# Age (B01001) — total + 10 male brackets + 10 female brackets we'll bucket.
AGE_VARS = {
    "total":      "B01001_001E",
    # Male
    "m_under_5":  "B01001_003E", "m_5_9":      "B01001_004E", "m_10_14":    "B01001_005E",
    "m_15_17":    "B01001_006E", "m_18_19":    "B01001_007E", "m_20":       "B01001_008E",
    "m_21":       "B01001_009E", "m_22_24":    "B01001_010E", "m_25_29":    "B01001_011E",
    "m_30_34":    "B01001_012E", "m_35_39":    "B01001_013E", "m_40_44":    "B01001_014E",
    "m_45_49":    "B01001_015E", "m_50_54":    "B01001_016E", "m_55_59":    "B01001_017E",
    "m_60_61":    "B01001_018E", "m_62_64":    "B01001_019E", "m_65_66":    "B01001_020E",
    "m_67_69":    "B01001_021E", "m_70_74":    "B01001_022E", "m_75_79":    "B01001_023E",
    "m_80_84":    "B01001_024E", "m_85_plus":  "B01001_025E",
    # Female (parallel structure)
    "f_under_5":  "B01001_027E", "f_5_9":      "B01001_028E", "f_10_14":    "B01001_029E",
    "f_15_17":    "B01001_030E", "f_18_19":    "B01001_031E", "f_20":       "B01001_032E",
    "f_21":       "B01001_033E", "f_22_24":    "B01001_034E", "f_25_29":    "B01001_035E",
    "f_30_34":    "B01001_036E", "f_35_39":    "B01001_037E", "f_40_44":    "B01001_038E",
    "f_45_49":    "B01001_039E", "f_50_54":    "B01001_040E", "f_55_59":    "B01001_041E",
    "f_60_61":    "B01001_042E", "f_62_64":    "B01001_043E", "f_65_66":    "B01001_044E",
    "f_67_69":    "B01001_045E", "f_70_74":    "B01001_046E", "f_75_79":    "B01001_047E",
    "f_80_84":    "B01001_048E", "f_85_plus":  "B01001_049E",
}

# Household income (B19001) — 16 brackets we'll bucket into 6.
INCOME_VARS = {
    "total":     "B19001_001E",
    "lt_10k":    "B19001_002E", "k10_15":  "B19001_003E", "k15_20":  "B19001_004E",
    "k20_25":    "B19001_005E", "k25_30":  "B19001_006E", "k30_35":  "B19001_007E",
    "k35_40":    "B19001_008E", "k40_45":  "B19001_009E", "k45_50":  "B19001_010E",
    "k50_60":    "B19001_011E", "k60_75":  "B19001_012E", "k75_100": "B19001_013E",
    "k100_125":  "B19001_014E", "k125_150":"B19001_015E", "k150_200":"B19001_016E",
    "k200_plus": "B19001_017E",
    "median":    "B19013_001E",
}

# Education (B15003) — 25+ years old, by attainment. Bucket into 4.
EDUCATION_VARS = {
    "total":          "B15003_001E",
    "less_hs_1":      "B15003_002E", "less_hs_2":      "B15003_003E",
    "less_hs_3":      "B15003_004E", "less_hs_4":      "B15003_005E",
    "less_hs_5":      "B15003_006E", "less_hs_7":      "B15003_007E",
    "less_hs_8":      "B15003_008E", "less_hs_9":      "B15003_009E",
    "less_hs_10":     "B15003_010E", "less_hs_11":     "B15003_011E",
    "less_hs_12":     "B15003_012E", "less_hs_no_dip": "B15003_016E",
    "hs_grad":        "B15003_017E", "ged":            "B15003_018E",
    "some_college_1": "B15003_019E", "some_college_2": "B15003_020E",
    "associates":     "B15003_021E",
    "bachelors":      "B15003_022E",
    "masters":        "B15003_023E",
    "professional":   "B15003_024E",
    "doctorate":      "B15003_025E",
}

# ── Public API ───────────────────────────────────────────────────────────────

def get_demographics(zip_code: str, force_refresh: bool = False) -> dict:
    """Return a normalized demographic dict for a 5-digit ZIP.

    On cache hit (within ``CACHE_TTL_DAYS``), no HTTP call is made.
    On Census failure, returns a baseline dict with ``source='unavailable'``.
    """
    zip_code = (zip_code or "").strip()[:5]
    if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
        return _empty_demographics(zip_code, "invalid_zip")

    if not force_refresh:
        cached = _load_cached(zip_code)
        if cached:
            return cached

    raw = _fetch_census(zip_code)
    if not raw:
        return _empty_demographics(zip_code, "census_unavailable")

    normalized = _normalize(zip_code, raw)
    _save_cache(zip_code, normalized)
    return normalized


def get_demographics_for_zips(zip_codes: list[str]) -> dict[str, dict]:
    """Batch helper. Returns ``{zip: demographics}``."""
    return {z: get_demographics(z) for z in dict.fromkeys(zip_codes)}


# ── Census API ───────────────────────────────────────────────────────────────

def _fetch_census(zip_code: str) -> dict | None:
    """Issue three GETs (age, income, education) and return raw value maps."""
    api_key = os.environ.get("CENSUS_API_KEY", "").strip()
    out = {}
    for label, varmap in (
        ("age", AGE_VARS),
        ("income", INCOME_VARS),
        ("education", EDUCATION_VARS),
    ):
        var_csv = ",".join(varmap.values())
        params = {
            "get": var_csv,
            "for": f"zip code tabulation area:{zip_code}",
        }
        if api_key:
            params["key"] = api_key
        url = f"{CENSUS_BASE}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MCTV-Simulator/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning("Census %s fetch failed for ZIP %s: %s", label, zip_code, e)
            return None

        # Census returns: [[header...], [values...]]
        if not rows or len(rows) < 2:
            return None
        header, values = rows[0], rows[1]
        var_to_value = dict(zip(header, values))
        # Map our friendly names back
        out[label] = {name: var_to_value.get(var) for name, var in varmap.items()}

    return out


# ── Normalization ────────────────────────────────────────────────────────────

def _to_int(v) -> int:
    try:
        n = int(v)
        return n if n >= 0 else 0
    except (TypeError, ValueError):
        return 0


def _normalize(zip_code: str, raw: dict) -> dict:
    """Bucket raw ACS values into the simulator's standard shape."""
    age = raw["age"]
    income = raw["income"]
    edu = raw["education"]

    # ── Age buckets (combine M+F, partition into 7 bands) ────────────────────
    def age_sum(*keys: str) -> int:
        return sum(_to_int(age.get(k)) for k in keys)

    age_bands = {
        "under_18": age_sum("m_under_5", "m_5_9", "m_10_14", "m_15_17",
                            "f_under_5", "f_5_9", "f_10_14", "f_15_17"),
        "18_24":    age_sum("m_18_19", "m_20", "m_21", "m_22_24",
                            "f_18_19", "f_20", "f_21", "f_22_24"),
        "25_34":    age_sum("m_25_29", "m_30_34", "f_25_29", "f_30_34"),
        "35_44":    age_sum("m_35_39", "m_40_44", "f_35_39", "f_40_44"),
        "45_54":    age_sum("m_45_49", "m_50_54", "f_45_49", "f_50_54"),
        "55_64":    age_sum("m_55_59", "m_60_61", "m_62_64",
                            "f_55_59", "f_60_61", "f_62_64"),
        "65_plus":  age_sum("m_65_66", "m_67_69", "m_70_74", "m_75_79",
                            "m_80_84", "m_85_plus",
                            "f_65_66", "f_67_69", "f_70_74", "f_75_79",
                            "f_80_84", "f_85_plus"),
    }
    age_total = sum(age_bands.values()) or _to_int(age.get("total")) or 1
    age_pct = {k: round(v / age_total * 100, 1) for k, v in age_bands.items()}

    # ── Income buckets (16 → 6) ──────────────────────────────────────────────
    def inc(*keys: str) -> int:
        return sum(_to_int(income.get(k)) for k in keys)

    income_buckets = {
        "under_35k":  inc("lt_10k", "k10_15", "k15_20", "k20_25", "k25_30", "k30_35"),
        "35k_50k":    inc("k35_40", "k40_45", "k45_50"),
        "50k_75k":    inc("k50_60", "k60_75"),
        "75k_100k":   inc("k75_100"),
        "100k_150k":  inc("k100_125", "k125_150"),
        "over_150k":  inc("k150_200", "k200_plus"),
    }
    income_total = sum(income_buckets.values()) or _to_int(income.get("total")) or 1
    income_pct = {k: round(v / income_total * 100, 1) for k, v in income_buckets.items()}
    median_hh_income = _to_int(income.get("median"))

    # ── Education (4 buckets, adults 25+) ────────────────────────────────────
    def ed(*keys: str) -> int:
        return sum(_to_int(edu.get(k)) for k in keys)

    less_hs_keys = (
        "less_hs_1", "less_hs_2", "less_hs_3", "less_hs_4", "less_hs_5",
        "less_hs_7", "less_hs_8", "less_hs_9", "less_hs_10", "less_hs_11",
        "less_hs_12", "less_hs_no_dip",
    )
    education_buckets = {
        "high_school_or_less": ed(*less_hs_keys, "hs_grad", "ged"),
        "some_college":        ed("some_college_1", "some_college_2", "associates"),
        "bachelors":           ed("bachelors"),
        "graduate":            ed("masters", "professional", "doctorate"),
    }
    edu_total = sum(education_buckets.values()) or _to_int(edu.get("total")) or 1
    education_pct = {k: round(v / edu_total * 100, 1) for k, v in education_buckets.items()}

    return {
        "zip": zip_code,
        "source": "census_acs5_2022",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "population": age_total,
        "median_household_income": median_hh_income,
        "age_pct": age_pct,
        "income_pct": income_pct,
        "education_pct": education_pct,
    }


def _empty_demographics(zip_code: str, source: str) -> dict:
    """Baseline structure when Census data is unavailable."""
    return {
        "zip": zip_code,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "population": 0,
        "median_household_income": 0,
        "age_pct": {k: 0.0 for k in (
            "under_18", "18_24", "25_34", "35_44", "45_54", "55_64", "65_plus")},
        "income_pct": {k: 0.0 for k in (
            "under_35k", "35k_50k", "50k_75k", "75k_100k", "100k_150k", "over_150k")},
        "education_pct": {k: 0.0 for k in (
            "high_school_or_less", "some_college", "bachelors", "graduate")},
    }


# ── Cache ────────────────────────────────────────────────────────────────────

def _load_cached(zip_code: str) -> dict | None:
    try:
        from services.supabase_client import query_table
        rows = query_table(
            "zip_demographics_cache",
            select="*",
            filters={"zip": zip_code},
            limit=1,
        )
    except Exception as e:
        logger.debug("Cache read failed for %s: %s", zip_code, e)
        return None

    if not rows:
        return None

    row = rows[0]
    fetched_at = row.get("fetched_at", "")
    try:
        # Postgres returns ISO-8601, sometimes with trailing 'Z'
        ts = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        ts = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS + 1)

    if datetime.now(timezone.utc) - ts > timedelta(days=CACHE_TTL_DAYS):
        return None  # stale, refetch

    raw = row.get("raw_data", {})
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return raw if isinstance(raw, dict) and raw.get("zip") else None


def _save_cache(zip_code: str, data: dict) -> None:
    try:
        from services.supabase_client import upsert_row
        upsert_row(
            "zip_demographics_cache",
            {
                "zip": zip_code,
                "raw_data": data,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="zip",
        )
    except Exception as e:
        logger.debug("Cache write failed for %s: %s", zip_code, e)
