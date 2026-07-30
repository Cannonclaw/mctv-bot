# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Screen inventory service — the manual book of record for what plays where.

`screen_loops` (the n-compass whitelist sweep) measures how much each screen
plays: loop_seconds and item_count per license. It does not say WHAT. This
service holds the "what", entered and maintained by hand:

    loop_items         one creative per row, scoped to a market
    loop_item_screens  per-screen include/exclude overrides

It mirrors the n-compass model (one playlist per market + a per-license
whitelist), so an item is run-of-network across its market by default and
only the exceptions get typed in. That keeps entry down to roughly one row
per creative instead of one row per creative per screen.

Two reconciliations fall out of that:

    reconcile_sweep()  expected item count / loop seconds per screen vs what
                       the whitelist sweep actually measured (screen_loops)
    reconcile_plays()  expected (venue, creative) pairs vs the Encompass /
                       NTV360 play export — catches booked-but-not-airing and
                       airing-but-not-tracked

Storage is Supabase REST with a local JSON fallback (data/inventory/), the
same pattern pipeline_service uses so the page still works offline.
"""

import json
import logging
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "inventory"

ITEMS_TABLE = "loop_items"
OVERRIDES_TABLE = "loop_item_screens"

# 15:00 loop target (4 plays/hr) — same target screen_loops is measured against.
TARGET_SECONDS = 900

# Sweep rows whose venue_name starts with one of these are diagnostic notes
# from the whitelist sweep, not real screens. They are excluded from expected
# loop math so they cannot skew a market's variance.
DIAGNOSTIC_PREFIXES = ("CROSS-MARKET:", "ORPHAN:", "NOTE:")

MARKETS = ["oxford", "starkville", "tupelo", "columbus", "west_point"]

MARKET_LABELS = {
    "oxford": "Oxford",
    "starkville": "Starkville",
    "tupelo": "Tupelo",
    "columbus": "Columbus",
    "west_point": "West Point",
}

# What kind of slot the creative occupies. Only 'paid' carries revenue.
BUCKETS = {
    "paid":      "Paid advertiser",
    "host":      "Host promo (venue's own spot)",
    "house":     "House / MCTV promo",
    "psa":       "PSA",
    "trade":     "Trade / barter",
    "community": "Community content",
}

STATUSES = ["active", "pending", "paused", "ended"]

# Statuses that should be on screen right now.
LIVE_STATUSES = ("active",)


# ── Helpers ──────────────────────────────────────────────────────────────────

def normalize(name: str | None) -> str:
    """Loose key for matching venue and file names across systems.

    Encompass exports, the whitelist sweep, and hand entry all spell venues
    slightly differently ("B's Hickory Smoke BBQ" vs "Bs Hickory Smoke Bbq").
    Lowercase, strip punctuation and file extensions, collapse whitespace.
    """
    text = (name or "").strip().lower()
    text = re.sub(r"\.(mp4|mov|jpg|jpeg|png|avi|wmv|mpg|mpeg|webm)$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def market_label(market: str) -> str:
    return MARKET_LABELS.get(market, (market or "").replace("_", " ").title())


def mmss(seconds) -> str:
    """Seconds as m:ss."""
    total = int(seconds or 0)
    return f"{total // 60}:{total % 60:02d}"


def is_diagnostic(venue_name: str | None) -> bool:
    """True for sweep annotation rows that are not real screens."""
    name = (venue_name or "").strip()
    return any(name.startswith(prefix) for prefix in DIAGNOSTIC_PREFIXES)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Storage: Supabase with local JSON fallback ───────────────────────────────

def _supabase_ready() -> bool:
    try:
        from services.supabase_client import is_configured
        return bool(is_configured())
    except Exception:  # pragma: no cover - import/env issues fall back to disk
        return False


def _local_path(table: str) -> Path:
    return DATA_DIR / f"{table}.json"


def _local_read(table: str) -> list:
    path = _local_path(table)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            rows = json.load(handle)
        return rows if isinstance(rows, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read local %s: %s", table, exc)
        return []


def _local_write(table: str, rows: list) -> bool:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_local_path(table), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, default=str)
        return True
    except OSError as exc:
        logger.error("Could not write local %s: %s", table, exc)
        return False


def _fetch(table: str) -> list:
    if _supabase_ready():
        try:
            from services.supabase_client import query_table
            return query_table(table, select="*") or []
        except Exception as exc:
            logger.error("Supabase read failed for %s, using local copy: %s", table, exc)
    return _local_read(table)


def _insert(table: str, row: dict) -> dict | None:
    if _supabase_ready():
        try:
            from services.supabase_client import insert_row
            saved = insert_row(table, row)
            if saved:
                return saved
        except Exception as exc:
            logger.error("Supabase insert failed for %s, using local copy: %s", table, exc)
    row.setdefault("id", str(uuid.uuid4()))
    row.setdefault("created_at", _now())
    rows = _local_read(table)
    rows.append(row)
    return row if _local_write(table, rows) else None


def _update(table: str, row_id: str, changes: dict) -> dict | None:
    if _supabase_ready():
        try:
            from services.supabase_client import update_row
            saved = update_row(table, row_id, changes)
            if saved:
                return saved
        except Exception as exc:
            logger.error("Supabase update failed for %s, using local copy: %s", table, exc)
    rows = _local_read(table)
    updated = None
    for row in rows:
        if str(row.get("id")) == str(row_id):
            row.update(changes)
            row["updated_at"] = _now()
            updated = row
            break
    if updated is None:
        return None
    return updated if _local_write(table, rows) else None


def _delete(table: str, row_id: str) -> bool:
    if _supabase_ready():
        try:
            from services.supabase_client import delete_row
            if delete_row(table, row_id):
                return True
        except Exception as exc:
            logger.error("Supabase delete failed for %s, using local copy: %s", table, exc)
    rows = _local_read(table)
    kept = [r for r in rows if str(r.get("id")) != str(row_id)]
    if len(kept) == len(rows):
        return False
    return _local_write(table, kept)


# ── Loop items ───────────────────────────────────────────────────────────────

def get_items(market: str | None = None, status: str | None = None) -> list:
    """All loop items, newest edits first. Filter by market and/or status."""
    rows = _fetch(ITEMS_TABLE)
    if market:
        rows = [r for r in rows if (r.get("market") or "") == market]
    if status:
        rows = [r for r in rows if (r.get("status") or "") == status]
    rows.sort(key=lambda r: (
        (r.get("advertiser") or r.get("file_name") or "").lower()
    ))
    return rows


def get_item(item_id: str) -> dict | None:
    for row in _fetch(ITEMS_TABLE):
        if str(row.get("id")) == str(item_id):
            return row
    return None


def save_item(data: dict) -> dict | None:
    """Create a loop item. `market` and `file_name` are required.

    Returns the saved row, or None when the write failed or a creative with
    that file name already exists in the market.
    """
    market = (data.get("market") or "").strip()
    file_name = (data.get("file_name") or "").strip()
    if not market or not file_name:
        logger.error("save_item needs both market and file_name")
        return None

    existing = find_item_by_file(market, file_name)
    if existing:
        logger.error("%s already tracked in %s", file_name, market)
        return None

    row = {
        "market": market,
        "file_name": file_name,
        "advertiser": (data.get("advertiser") or "").strip() or None,
        "client_id": data.get("client_id") or None,
        "bucket": data.get("bucket") or "paid",
        "duration_seconds": int(data.get("duration_seconds") or 15),
        "monthly_value": data.get("monthly_value"),
        "status": data.get("status") or "active",
        "run_of_network": bool(data.get("run_of_network", True)),
        "start_date": data.get("start_date") or None,
        "end_date": data.get("end_date") or None,
        "contract_id": data.get("contract_id") or None,
        "notes": (data.get("notes") or "").strip() or None,
        "verified_at": data.get("verified_at") or None,
        "updated_by": data.get("updated_by") or None,
    }
    # Dates arrive as date objects from Streamlit inputs; JSON needs strings.
    for key in ("start_date", "end_date", "verified_at"):
        if isinstance(row[key], (date, datetime)):
            row[key] = row[key].isoformat()[:10]
    if row["monthly_value"] in ("", 0):
        row["monthly_value"] = None

    return _insert(ITEMS_TABLE, row)


def update_item(item_id: str, changes: dict) -> dict | None:
    """Patch a loop item. Only the keys given are written."""
    clean = dict(changes)
    for key in ("start_date", "end_date", "verified_at"):
        if isinstance(clean.get(key), (date, datetime)):
            clean[key] = clean[key].isoformat()[:10]
    if "duration_seconds" in clean:
        clean["duration_seconds"] = int(clean["duration_seconds"] or 15)
    if clean.get("monthly_value") in ("", 0):
        clean["monthly_value"] = None
    return _update(ITEMS_TABLE, item_id, clean)


def delete_item(item_id: str) -> bool:
    """Remove a loop item and any overrides pointing at it."""
    for override in get_overrides(item_id=item_id):
        _delete(OVERRIDES_TABLE, override["id"])
    return _delete(ITEMS_TABLE, item_id)


def find_item_by_file(market: str, file_name: str) -> dict | None:
    """Look an item up the way the play export spells it — loosely."""
    key = normalize(file_name)
    for row in _fetch(ITEMS_TABLE):
        if (row.get("market") or "") != market:
            continue
        if normalize(row.get("file_name")) == key:
            return row
    return None


def mark_verified(item_id: str, verified_by: str = "") -> dict | None:
    """Stamp an item as confirmed against the portal today."""
    return update_item(item_id, {
        "verified_at": date.today().isoformat(),
        "updated_by": verified_by or None,
    })


# ── Per-screen overrides ─────────────────────────────────────────────────────

def get_overrides(item_id: str | None = None, venue_name: str | None = None) -> list:
    rows = _fetch(OVERRIDES_TABLE)
    if item_id:
        rows = [r for r in rows if str(r.get("item_id")) == str(item_id)]
    if venue_name:
        key = normalize(venue_name)
        rows = [r for r in rows if normalize(r.get("venue_name")) == key]
    return rows


def add_override(item_id: str, venue_name: str, mode: str = "include",
                 license_id: str | None = None, reason: str = "",
                 created_by: str = "") -> dict | None:
    """Put an item on, or pull it off, one venue's screens.

    license_id None applies the override to every screen at the venue.
    """
    if mode not in ("include", "exclude"):
        logger.error("override mode must be include or exclude, got %r", mode)
        return None
    venue_name = (venue_name or "").strip()
    if not item_id or not venue_name:
        return None

    for existing in get_overrides(item_id=item_id, venue_name=venue_name):
        if str(existing.get("license_id") or "") == str(license_id or ""):
            # Same screen already has an override — flip its mode rather than
            # writing a duplicate the unique index would reject anyway.
            if existing.get("mode") != mode:
                return _update(OVERRIDES_TABLE, existing["id"], {"mode": mode,
                                                                 "reason": reason or None})
            return existing

    return _insert(OVERRIDES_TABLE, {
        "item_id": item_id,
        "venue_name": venue_name,
        "license_id": license_id or None,
        "mode": mode,
        "reason": (reason or "").strip() or None,
        "created_by": created_by or None,
    })


def delete_override(override_id: str) -> bool:
    return _delete(OVERRIDES_TABLE, override_id)


# ── Screens (from the whitelist sweep) ───────────────────────────────────────

def get_screens(market: str | None = None, swept_at: str | None = None,
                include_diagnostic: bool = False) -> list:
    """Screens from a sweep of `screen_loops`, latest sweep by default.

    Each row is one license: venue_name, license_id, loop_seconds, item_count.
    """
    try:
        from services.supabase_client import query_table
    except ImportError:
        return []

    filters = {}
    if market:
        filters["market"] = market
    if swept_at:
        filters["swept_at"] = swept_at

    try:
        rows = query_table("screen_loops", select="*",
                           filters=filters or None, order="-swept_at") or []
    except Exception as exc:
        logger.error("Could not read screen_loops: %s", exc)
        return []

    if not swept_at and rows:
        # query_table has no aggregate support, so trim to the newest sweep here.
        latest = max((r.get("swept_at") or "") for r in rows)
        rows = [r for r in rows if (r.get("swept_at") or "") == latest]

    if not include_diagnostic:
        rows = [r for r in rows if not is_diagnostic(r.get("venue_name"))]

    rows.sort(key=lambda r: ((r.get("market") or ""), (r.get("venue_name") or "")))
    return rows


def get_venues(market: str | None = None) -> list:
    """Distinct venue names in the latest sweep, for pickers."""
    seen = {}
    for row in get_screens(market=market):
        name = (row.get("venue_name") or "").strip()
        if name and name not in seen:
            seen[name] = True
    return sorted(seen)


# ── Expected loop math ───────────────────────────────────────────────────────

def _override_map(overrides: list) -> dict:
    """Index overrides as {(item_id, venue_key, license_key): mode}."""
    index = {}
    for row in overrides:
        key = (
            str(row.get("item_id")),
            normalize(row.get("venue_name")),
            str(row.get("license_id") or ""),
        )
        index[key] = row.get("mode") or "include"
    return index


def _override_mode(index: dict, item_id: str, venue_name: str,
                   license_id: str | None) -> str | None:
    """Mode that applies to one screen: license-specific beats venue-wide."""
    venue_key = normalize(venue_name)
    specific = index.get((str(item_id), venue_key, str(license_id or "")))
    if specific:
        return specific
    return index.get((str(item_id), venue_key, ""))


def plays_on_screen(item: dict, venue_name: str, license_id: str | None,
                    index: dict) -> bool:
    """Is this item expected on this screen right now?"""
    if (item.get("status") or "") not in LIVE_STATUSES:
        return False
    mode = _override_mode(index, item.get("id"), venue_name, license_id)
    if item.get("run_of_network"):
        return mode != "exclude"
    return mode == "include"


def expected_by_screen(market: str, items: list | None = None,
                       overrides: list | None = None,
                       screens: list | None = None) -> list:
    """Expected loop contents for every screen in a market.

    Returns one dict per screen: venue_name, license_id, expected_count,
    expected_seconds, and the item rows themselves.
    """
    items = [i for i in (items if items is not None else get_items(market))
             if (i.get("market") or "") == market]
    overrides = overrides if overrides is not None else get_overrides()
    screens = screens if screens is not None else get_screens(market=market)
    index = _override_map(overrides)

    results = []
    for screen in screens:
        venue = screen.get("venue_name") or ""
        license_id = screen.get("license_id")
        on_screen = [i for i in items if plays_on_screen(i, venue, license_id, index)]
        results.append({
            "venue_name": venue,
            "license_id": license_id,
            "market": screen.get("market") or market,
            "expected_count": len(on_screen),
            "expected_seconds": sum(int(i.get("duration_seconds") or 0) for i in on_screen),
            "items": on_screen,
        })
    return results


def inventory_summary(items: list) -> dict:
    """Counts and revenue for a set of loop items."""
    live = [i for i in items if (i.get("status") or "") in LIVE_STATUSES]
    paid = [i for i in live if (i.get("bucket") or "") == "paid"]
    return {
        "total": len(items),
        "active": len(live),
        "paid": len(paid),
        "unverified": len([i for i in live if not i.get("verified_at")]),
        "monthly_value": float(sum(float(i.get("monthly_value") or 0) for i in paid)),
        "base_loop_seconds": sum(
            int(i.get("duration_seconds") or 0)
            for i in live if i.get("run_of_network")
        ),
    }


# ── Reconciliation: inventory vs the whitelist sweep ─────────────────────────

def reconcile_sweep(market: str, items: list | None = None,
                    overrides: list | None = None,
                    screens: list | None = None,
                    tolerance: int = 0) -> list:
    """Compare expected loop contents against what the sweep measured.

    `tolerance` is the item-count delta to forgive before flagging a screen.
    Returns one row per screen with both sides and the variance.
    """
    screens = screens if screens is not None else get_screens(market=market)
    expected = expected_by_screen(market, items=items, overrides=overrides,
                                  screens=screens)

    by_key = {
        (normalize(s.get("venue_name")), str(s.get("license_id") or "")): s
        for s in screens
    }

    rows = []
    for exp in expected:
        key = (normalize(exp["venue_name"]), str(exp["license_id"] or ""))
        screen = by_key.get(key, {})
        actual_count = int(screen.get("item_count") or 0)
        actual_seconds = int(screen.get("loop_seconds") or 0)
        count_delta = exp["expected_count"] - actual_count

        if abs(count_delta) <= tolerance:
            verdict = "match"
        elif count_delta < 0:
            # Sweep found more than we have on the books.
            verdict = "untracked_items"
        else:
            verdict = "missing_from_screen"

        rows.append({
            "venue_name": exp["venue_name"],
            "license_id": exp["license_id"],
            "expected_count": exp["expected_count"],
            "actual_count": actual_count,
            "count_delta": count_delta,
            "expected_seconds": exp["expected_seconds"],
            "actual_seconds": actual_seconds,
            "seconds_delta": exp["expected_seconds"] - actual_seconds,
            "over_target": actual_seconds > TARGET_SECONDS,
            "verdict": verdict,
        })

    rows.sort(key=lambda r: (-abs(r["count_delta"]), r["venue_name"]))
    return rows


# ── Reconciliation: inventory vs the Encompass play export ───────────────────

def reconcile_plays(play_records: list, market: str,
                    items: list | None = None,
                    overrides: list | None = None,
                    screens: list | None = None) -> dict:
    """Check the inventory against an Encompass / NTV360 play export.

    `play_records` are PlayRecord objects (or dicts) from
    services.excel_parser.parse_excel — the content-report format carries both
    host_name and content_name, which is what makes this join possible.

    Returns:
        not_airing  expected at a venue but the export shows no plays there
        untracked   plays in the export for a creative we have no row for
        dark_items  tracked items with zero plays anywhere in the export
        matched     count of (venue, creative) pairs that lined up
        venues_in_export / has_content_names for sanity-checking the upload
    """
    items = [i for i in (items if items is not None else get_items(market))
             if (i.get("market") or "") == market]
    expected = expected_by_screen(market, items=items, overrides=overrides,
                                  screens=screens)

    # Actual plays keyed by (venue, creative). Venues repeat across a venue's
    # screens in the export, so sum rather than overwrite.
    actual: dict = {}
    plays_by_file: dict = {}
    venues_in_export = set()
    has_content_names = False

    for record in play_records:
        if isinstance(record, dict):
            host = record.get("host_name")
            content = record.get("content_name")
            count = record.get("play_count") or 0
        else:
            host = getattr(record, "host_name", "")
            content = getattr(record, "content_name", "")
            count = getattr(record, "play_count", 0) or 0

        venue_key = normalize(host)
        file_key = normalize(content)
        if not venue_key:
            continue
        venues_in_export.add(venue_key)
        if file_key:
            has_content_names = True
            actual[(venue_key, file_key)] = actual.get((venue_key, file_key), 0) + int(count)
            plays_by_file[file_key] = plays_by_file.get(file_key, 0) + int(count)

    # Expected pairs, collapsed to venue level — the export reports per venue,
    # not per license, so two screens at one venue are one row here.
    expected_pairs: dict = {}
    for screen in expected:
        venue_key = normalize(screen["venue_name"])
        for item in screen["items"]:
            file_key = normalize(item.get("file_name"))
            expected_pairs.setdefault((venue_key, file_key), {
                "venue_name": screen["venue_name"],
                "item": item,
            })

    not_airing, matched = [], 0
    for (venue_key, file_key), meta in expected_pairs.items():
        if venue_key not in venues_in_export:
            # Venue absent from the export entirely — that's a screen-health
            # question, not an inventory error. Skip rather than cry wolf.
            continue
        plays = actual.get((venue_key, file_key), 0)
        if plays > 0:
            matched += 1
        else:
            item = meta["item"]
            not_airing.append({
                "venue_name": meta["venue_name"],
                "file_name": item.get("file_name"),
                "advertiser": item.get("advertiser"),
                "bucket": item.get("bucket"),
                "monthly_value": item.get("monthly_value"),
            })

    tracked_files = {normalize(i.get("file_name")) for i in items}
    untracked: dict = {}
    for (venue_key, file_key), plays in actual.items():
        if plays <= 0 or file_key in tracked_files:
            continue
        entry = untracked.setdefault(file_key, {"file_key": file_key, "plays": 0,
                                                "venues": set()})
        entry["plays"] += plays
        entry["venues"].add(venue_key)

    untracked_rows = sorted(
        ({"file_name": e["file_key"], "plays": e["plays"], "venues": len(e["venues"])}
         for e in untracked.values()),
        key=lambda r: -r["plays"],
    )

    dark_items = [
        {
            "file_name": i.get("file_name"),
            "advertiser": i.get("advertiser"),
            "bucket": i.get("bucket"),
            "monthly_value": i.get("monthly_value"),
        }
        for i in items
        if (i.get("status") or "") in LIVE_STATUSES
        and plays_by_file.get(normalize(i.get("file_name")), 0) == 0
    ]

    not_airing.sort(key=lambda r: (-(float(r.get("monthly_value") or 0)),
                                   r["venue_name"]))
    dark_items.sort(key=lambda r: -(float(r.get("monthly_value") or 0)))

    return {
        "matched": matched,
        "expected_pairs": len(expected_pairs),
        "not_airing": not_airing,
        "untracked": untracked_rows,
        "dark_items": dark_items,
        "venues_in_export": len(venues_in_export),
        "has_content_names": has_content_names,
        "monthly_at_risk": float(sum(
            float(r.get("monthly_value") or 0)
            for r in dark_items if r.get("bucket") == "paid"
        )),
    }


# ── Seeding ──────────────────────────────────────────────────────────────────

def seed_from_plays(play_records: list, market: str,
                    default_seconds: int = 15,
                    created_by: str = "") -> dict:
    """Create draft loop items from an Encompass export's creative names.

    A shortcut past the blank page: every creative the export shows playing in
    this market gets a pending, run-of-network row to be corrected by hand.
    Existing items are left alone.

    Returns {"created": n, "skipped": n, "names": [...]}.
    """
    counts: dict = {}
    for record in play_records:
        if isinstance(record, dict):
            content = record.get("content_name")
            count = record.get("play_count") or 0
        else:
            content = getattr(record, "content_name", "")
            count = getattr(record, "play_count", 0) or 0
        name = (content or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + int(count)

    created, skipped, names = 0, 0, []
    for name in sorted(counts):
        if find_item_by_file(market, name):
            skipped += 1
            continue
        saved = save_item({
            "market": market,
            "file_name": name,
            "bucket": "paid",
            "duration_seconds": default_seconds,
            "status": "pending",
            "run_of_network": True,
            "notes": f"Seeded from play export ({counts[name]} plays). Confirm advertiser, length, and screens.",
            "updated_by": created_by,
        })
        if saved:
            created += 1
            names.append(name)
        else:
            skipped += 1

    return {"created": created, "skipped": skipped, "names": names}
