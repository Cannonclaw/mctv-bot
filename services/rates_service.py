# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Mortgage rate feed for the Real Estate Feeds Board rate strip.

The board never talks to an upstream rate source. A scheduled job
(``scripts/fetch_rates.py``) pulls the published weekly observation into
``market_rates``, and the board reads the cache. That keeps a screen from
depending on a third party being up, and it means one fetch serves every
board on the network.

Source is Freddie Mac's Primary Mortgage Market Survey -- weekly, free,
and citable, which is why the strip can show its provenance on screen.
Two URLs are configured because the same series is published in two
places and they break independently:

    fred    FRED series MORTGAGE30US / MORTGAGE15US (Freddie Mac PMMS data,
            redistributed by the St. Louis Fed; simple two-column CSV)
    pmms    Freddie Mac's own PMMS_history.csv

Both land in the same tolerant parser: find the last row whose first cell
is a date and whose target cell is a number. Header spellings on both
feeds have changed over the years ("DATE" vs "observation_date", varying
PMMS column labels), so nothing keys off a header name.

THE STALENESS RULE IS THE POINT. ``rate_for_display()`` returns None once
the observation is older than the configured window. A board quoting a
rate from a month ago is worse than a board that never mentioned rates,
so the strip hides rather than lying.

Network access uses stdlib urllib only, per the house convention.
"""

from __future__ import annotations

import csv
import io
import logging
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from services.config_service import load_config
from services.supabase_client import query_table, upsert_row

logger = logging.getLogger(__name__)

USER_AGENT = "MCTV-Bot/1.0 (+https://mctvofms.com)"
TIMEOUT_SECONDS = 20

# Fallback used only when config.json carries no real_estate_board.rate_strip.
DEFAULT_STALENESS_DAYS = 10

# series key -> where to get it. Ordered: first source that parses wins.
SOURCES = {
    "pmms_30yr": [
        {
            "key": "fred",
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US",
            "value_column": 1,
            "source_name": "Freddie Mac PMMS (via FRED)",
        },
        {
            "key": "pmms",
            "url": "https://www.freddiemac.com/pmms/docs/PMMS_history.csv",
            "value_column": 1,
            "source_name": "Freddie Mac Primary Mortgage Market Survey (PMMS)",
        },
    ],
    "pmms_15yr": [
        {
            "key": "fred",
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE15US",
            "value_column": 1,
            "source_name": "Freddie Mac PMMS (via FRED)",
        },
    ],
}

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y")


# ---------------------------------------------------------------------------
# Parsing — pure, no network, unit-testable
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> date | None:
    text = (text or "").strip().strip('"')
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_value(text: str) -> float | None:
    """Parse a rate cell. Rejects placeholders and implausible values."""
    text = (text or "").strip().strip('"').rstrip("%")
    # Both feeds use a dot for "no observation this week".
    if not text or text in (".", "-", "NA", "N/A", "null"):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    # A US mortgage rate outside this band means we parsed the wrong column.
    if not 0 < value < 100:
        return None
    return value


def parse_rate_csv(text: str, value_column: int = 1) -> tuple[date, float] | None:
    """Return the most recent (week_ending, rate) from a rate CSV.

    Tolerant by design: skips headers, blank rows, and gap rows rather than
    keying off a header spelling that both publishers have changed before.
    Returns the row with the latest date, not the last row in the file --
    a feed that appends out of order shouldn't decide what the board shows.
    """
    if not text or not text.strip():
        return None

    best: tuple[date, float] | None = None
    for row in csv.reader(io.StringIO(text)):
        if len(row) <= value_column:
            continue
        observed = _parse_date(row[0])
        if observed is None:
            continue  # header or junk row
        value = _parse_value(row[value_column])
        if value is None:
            continue  # gap row
        if best is None or observed > best[0]:
            best = (observed, value)

    return best


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------

def staleness_days(config: dict | None = None) -> int:
    """How old an observation may be before the strip hides itself."""
    cfg = config if config is not None else load_config()
    strip = (cfg.get("real_estate_board", {}) or {}).get("rate_strip", {}) or {}
    try:
        return int(strip.get("staleness_days", DEFAULT_STALENESS_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_STALENESS_DAYS


def is_stale(week_ending: date | str | None, config: dict | None = None,
             today: date | None = None) -> bool:
    """True when an observation is too old to display (or missing/unparseable)."""
    if week_ending is None:
        return True
    if isinstance(week_ending, str):
        week_ending = _parse_date(week_ending)
        if week_ending is None:
            return True
    reference = today or datetime.now(timezone.utc).date()
    return (reference - week_ending).days > staleness_days(config)


# ---------------------------------------------------------------------------
# Fetch + store
# ---------------------------------------------------------------------------

def _http_get(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning("rate fetch failed for %s: %s", url, exc)
        return None


def fetch_latest(series: str = "pmms_30yr") -> dict | None:
    """Fetch the newest observation for a series from the first source that works.

    Returns a dict shaped for market_rates, or None when every source fails.
    Never raises -- a rate feed being down must not take a caller with it.
    """
    for source in SOURCES.get(series, []):
        body = _http_get(source["url"])
        if not body:
            continue
        parsed = parse_rate_csv(body, value_column=source.get("value_column", 1))
        if parsed is None:
            logger.warning("rate source %s returned unparseable data for %s",
                           source["key"], series)
            continue
        observed, value = parsed
        return {
            "series": series,
            "rate_value": value,
            "week_ending": observed.isoformat(),
            "source_name": source["source_name"],
            "source_url": source["url"],
        }

    logger.error("no rate source produced a usable observation for %s", series)
    return None


def store_rate(observation: dict) -> dict | None:
    """Upsert an observation into market_rates (unique on series + week_ending)."""
    if not observation:
        return None
    return upsert_row("market_rates", observation, on_conflict="series,week_ending")


def refresh(series: str = "pmms_30yr") -> dict | None:
    """Fetch and cache one series. Entry point for the scheduled job."""
    observation = fetch_latest(series)
    if observation is None:
        return None
    stored = store_rate(observation)
    if stored is None:
        logger.error("fetched %s but could not write it to market_rates", series)
    return stored or observation


# ---------------------------------------------------------------------------
# Read side — what the board asks for
# ---------------------------------------------------------------------------

def get_cached_rate(series: str = "pmms_30yr") -> dict | None:
    """Most recent cached observation for a series, stale or not."""
    rows = query_table("market_rates", filters={"series": series},
                       order="-week_ending", limit=1)
    return rows[0] if rows else None


def rate_for_display(series: str = "pmms_30yr", config: dict | None = None,
                     today: date | None = None) -> dict | None:
    """The rate strip payload, or None when the strip should hide.

    None means "render no strip at all" -- not "render an empty strip." The
    caller is expected to omit the element entirely.
    """
    row = get_cached_rate(series)
    if not row:
        return None
    if is_stale(row.get("week_ending"), config=config, today=today):
        logger.info("rate strip hidden: %s observation %s is stale",
                    series, row.get("week_ending"))
        return None

    observed = _parse_date(str(row.get("week_ending")))
    try:
        value = float(row["rate_value"])
    except (KeyError, TypeError, ValueError):
        return None

    return {
        "series": series,
        "rate": value,
        "rate_label": f"{value:.2f}%",
        "week_ending": row.get("week_ending"),
        # Built by hand rather than with %-d: that flag is glibc-only and the
        # team also runs this on Windows.
        "week_label": (f"{observed.strftime('%b')} {observed.day}, {observed.year}"
                       if observed else ""),
        "source_name": row.get("source_name") or "",
    }
