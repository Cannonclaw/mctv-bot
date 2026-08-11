# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Venue events — the schedule behind the lobby feed board.

Host venues that run programming (the Oxford Conference Center first) want the
day's events on the MCTV screen in their lobby. This service holds that
schedule and shapes it for the board:

    venue_events        one row per event per venue (migration 025)

Two things live here that the table deliberately does not do:

    board_payload()     everything GET /board/events.json returns — the day's
                        events, already masked, labelled, and sorted
    mask()              private bookings render as "Private Event" but keep
                        their room, so the board reads as occupied without
                        putting a family's name on a public screen

Storage is Supabase REST with a local JSON fallback (data/venue_events/), the
same pattern pipeline_service and screen_inventory_service use, so the board
still renders when Supabase is unreachable.

Nothing in this module imports Streamlit — server_routes.py loads it inside the
web server process, before any Streamlit page exists.
"""

import json
import logging
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "venue_events"

EVENTS_TABLE = "venue_events"

DEFAULT_VENUE = "oxford-conference-center"

# Venues with a board. Adding one is a dict entry plus rows in venue_events —
# the board HTML and the route are venue-agnostic.
BOARD_VENUES = {
    "oxford-conference-center": {
        "name": "Oxford Conference Center",
        "subtitle": "Today at the Conference Center",
        "market": "oxford",
        "timezone": "America/Chicago",
    },
}

STATUSES = ["scheduled", "cancelled", "postponed"]

# What a masked booking says on screen.
PRIVATE_TITLE = "Private Event"

# An event counts as "on now" from this long before its start time — people are
# walking in and looking for the room while it still says 8:59.
LEAD_IN_MINUTES = 15

# How long a finished event stays on the board before it drops off.
LINGER_MINUTES = 20

# When the rest of today holds nothing, the board previews this far ahead.
LOOKAHEAD_DAYS = 7


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(name: str | None) -> str:
    """'Oxford Conference Center' -> 'oxford-conference-center'."""
    text = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower())
    return text.strip("-")


def venue_config(venue_slug: str | None) -> dict:
    """Board display config for a venue, defaulting to the Conference Center."""
    slug = (venue_slug or "").strip().lower() or DEFAULT_VENUE
    config = BOARD_VENUES.get(slug)
    if config is None:
        # Unknown slug: still serve a board rather than a 404, titled off the
        # slug itself. A venue added to venue_events but not to BOARD_VENUES
        # should show its schedule, not an error screen.
        config = {
            "name": slug.replace("-", " ").title(),
            "subtitle": "Today's Schedule",
            "market": None,
            "timezone": "America/Chicago",
        }
    return {"slug": slug, **config}


def _tzinfo(name: str):
    """Venue timezone, falling back to a fixed US Central rule.

    Slim container images occasionally ship without the tz database, and a
    board that renders every time an hour off is worse than one that hardcodes
    the only timezone all five markets are in.
    """
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:  # pragma: no cover - only when tzdata is missing
        logger.warning("timezone %s unavailable, using fixed US Central rule", name)
        return _CentralFallback()


class _CentralFallback(tzinfo):
    """Minimal America/Chicago: CDT from the 2nd Sunday in March to the 1st in November."""

    def _is_dst(self, dt: datetime) -> bool:
        year = dt.year
        march = date(year, 3, 8)
        start = march + timedelta(days=(6 - march.weekday()) % 7)  # 2nd Sunday
        nov = date(year, 11, 1)
        end = nov + timedelta(days=(6 - nov.weekday()) % 7)        # 1st Sunday
        return start <= dt.date() < end

    def utcoffset(self, dt):
        return timedelta(hours=-5 if dt and self._is_dst(dt) else -6)

    def dst(self, dt):
        return timedelta(hours=1) if dt and self._is_dst(dt) else timedelta(0)

    def tzname(self, dt):
        return "CDT" if dt and self._is_dst(dt) else "CST"

    def fromutc(self, dt):
        # datetime.astimezone() calls this with a naive dt already in "self" terms.
        guess = dt + timedelta(hours=-6)
        return dt + self.utcoffset(guess)


def parse_dt(value, tz=None) -> datetime | None:
    """Parse a timestamp from Supabase, a JSON file, or a Streamlit widget.

    Naive values are read as venue-local. Everything comes back aware and, when
    `tz` is given, converted into it.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        text = str(value).strip().replace(" ", "T", 1)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        # Postgres hands back microseconds at whatever precision it feels like;
        # fromisoformat before 3.11 wants exactly 3 or 6 digits.
        text = re.sub(r"\.(\d{1,6})\d*", lambda m: "." + m.group(1).ljust(6, "0"), text)
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            logger.warning("could not parse timestamp %r", value)
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz or timezone.utc)
    return parsed.astimezone(tz) if tz else parsed


def _clock(dt: datetime) -> str:
    """3:05 PM, no leading zero (%-I is not portable to Windows)."""
    hour = dt.hour % 12 or 12
    return f"{hour}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def time_label(start: datetime | None, end: datetime | None, all_day: bool = False) -> str:
    """'9:00 AM – 12:30 PM', '9:00 AM', or 'All Day'."""
    if all_day:
        return "All Day"
    if start is None:
        return ""
    if end is None or end == start:
        return _clock(start)
    return f"{_clock(start)} – {_clock(end)}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Storage: Supabase with local JSON fallback ───────────────────────────────

def _supabase_ready() -> bool:
    try:
        from services.supabase_client import is_configured
        return bool(is_configured())
    except Exception:  # pragma: no cover - import/env issues fall back to disk
        return False


def _local_path() -> Path:
    return DATA_DIR / f"{EVENTS_TABLE}.json"


def _local_read() -> list:
    path = _local_path()
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            rows = json.load(handle)
        return rows if isinstance(rows, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read local %s: %s", EVENTS_TABLE, exc)
        return []


def _local_write(rows: list) -> bool:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_local_path(), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, default=str)
        return True
    except OSError as exc:
        logger.error("Could not write local %s: %s", EVENTS_TABLE, exc)
        return False


def _fetch(venue_slug: str | None = None) -> list:
    if _supabase_ready():
        try:
            from services.supabase_client import query_table
            filters = {"venue_slug": venue_slug} if venue_slug else None
            return query_table(EVENTS_TABLE, select="*", filters=filters,
                               order="starts_at") or []
        except Exception as exc:
            logger.error("Supabase read failed for %s, using local copy: %s",
                         EVENTS_TABLE, exc)
    rows = _local_read()
    if venue_slug:
        rows = [r for r in rows if (r.get("venue_slug") or "") == venue_slug]
    return rows


# ── CRUD ─────────────────────────────────────────────────────────────────────

def list_events(venue_slug: str | None = None, start=None, end=None,
                include_cancelled: bool = True) -> list:
    """Raw event rows for a venue, oldest first.

    `start` / `end` bound starts_at. Both are inclusive of the start and
    exclusive of the end, so a day query is [midnight, next midnight).
    """
    rows = _fetch(venue_slug)
    tz = _tzinfo(venue_config(venue_slug)["timezone"])
    lower = parse_dt(start, tz)
    upper = parse_dt(end, tz)

    kept = []
    for row in rows:
        starts = parse_dt(row.get("starts_at"), tz)
        if starts is None:
            continue
        if lower and starts < lower:
            continue
        if upper and starts >= upper:
            continue
        if not include_cancelled and (row.get("status") or "") == "cancelled":
            continue
        kept.append(row)

    kept.sort(key=lambda r: (str(parse_dt(r.get("starts_at"), tz)),
                             (r.get("room") or "")))
    return kept


def get_event(event_id: str) -> dict | None:
    for row in _fetch():
        if str(row.get("id")) == str(event_id):
            return row
    return None


def save_event(data: dict) -> dict | None:
    """Create an event. `title` and `starts_at` are required.

    `venue_slug` defaults to the Conference Center; `venue_name` fills itself
    in from the venue config when it is left out.
    """
    title = (data.get("title") or "").strip()
    if not title:
        logger.error("save_event needs a title")
        return None

    venue = venue_config(data.get("venue_slug"))
    tz = _tzinfo(venue["timezone"])
    starts = parse_dt(data.get("starts_at"), tz)
    if starts is None:
        logger.error("save_event needs a parseable starts_at")
        return None

    ends = parse_dt(data.get("ends_at"), tz)
    if ends is not None and ends < starts:
        logger.error("%s ends before it starts", title)
        return None

    row = {
        "venue_slug": venue["slug"],
        "venue_name": (data.get("venue_name") or venue["name"]).strip(),
        "title": title,
        "host_org": (data.get("host_org") or "").strip() or None,
        "room": (data.get("room") or "").strip() or None,
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat() if ends else None,
        "all_day": bool(data.get("all_day", False)),
        "is_private": bool(data.get("is_private", False)),
        "status": data.get("status") or "scheduled",
        "public_note": (data.get("public_note") or "").strip() or None,
        "internal_note": (data.get("internal_note") or "").strip() or None,
        "source": data.get("source") or "manual",
        "external_id": data.get("external_id") or None,
        "created_by": data.get("created_by") or None,
    }
    if row["status"] not in STATUSES:
        row["status"] = "scheduled"

    if _supabase_ready():
        try:
            from services.supabase_client import insert_row
            saved = insert_row(EVENTS_TABLE, row)
            if saved:
                return saved
        except Exception as exc:
            logger.error("Supabase insert failed for %s, using local copy: %s",
                         EVENTS_TABLE, exc)

    row.setdefault("id", str(uuid.uuid4()))
    row.setdefault("created_at", _now())
    rows = _local_read()
    rows.append(row)
    return row if _local_write(rows) else None


def update_event(event_id: str, changes: dict) -> dict | None:
    """Patch an event. Only the keys given are written."""
    clean = dict(changes)
    tz = _tzinfo(venue_config(clean.get("venue_slug"))["timezone"])
    for key in ("starts_at", "ends_at"):
        if key in clean:
            parsed = parse_dt(clean[key], tz)
            clean[key] = parsed.isoformat() if parsed else None
    if clean.get("status") and clean["status"] not in STATUSES:
        clean.pop("status")

    if _supabase_ready():
        try:
            from services.supabase_client import update_row
            saved = update_row(EVENTS_TABLE, event_id, clean)
            if saved:
                return saved
        except Exception as exc:
            logger.error("Supabase update failed for %s, using local copy: %s",
                         EVENTS_TABLE, exc)

    rows = _local_read()
    updated = None
    for row in rows:
        if str(row.get("id")) == str(event_id):
            row.update(clean)
            row["updated_at"] = _now()
            updated = row
            break
    if updated is None:
        return None
    return updated if _local_write(rows) else None


def delete_event(event_id: str) -> bool:
    if _supabase_ready():
        try:
            from services.supabase_client import delete_row
            if delete_row(EVENTS_TABLE, event_id):
                return True
        except Exception as exc:
            logger.error("Supabase delete failed for %s, using local copy: %s",
                         EVENTS_TABLE, exc)
    rows = _local_read()
    kept = [r for r in rows if str(r.get("id")) != str(event_id)]
    if len(kept) == len(rows):
        return False
    return _local_write(kept)


# ── Board shaping ────────────────────────────────────────────────────────────

def event_state(start: datetime | None, end: datetime | None,
                now: datetime, all_day: bool = False) -> str:
    """Where an event sits relative to now: on | soon | upcoming | ended."""
    if start is None:
        return "upcoming"
    if all_day:
        return "on" if start.date() == now.date() else "upcoming"

    close = start - timedelta(minutes=LEAD_IN_MINUTES)
    finish = (end or start) + timedelta(minutes=LINGER_MINUTES)

    if now >= finish:
        return "ended"
    if now >= (end or start):
        return "on"      # inside the linger window — still say it is happening
    if now >= start:
        return "on"
    if now >= close:
        return "soon"
    return "upcoming"


def mask(row: dict) -> dict:
    """Strip a private booking down to what belongs on a public screen.

    Title, host, and both notes go; the room stays, so the board still reads as
    occupied. Nothing here trusts the entered title — a private row is private
    however carelessly it was typed.
    """
    if not row.get("is_private"):
        return row
    masked = dict(row)
    masked["title"] = PRIVATE_TITLE
    masked["host_org"] = None
    masked["public_note"] = None
    masked["internal_note"] = None
    return masked


def _board_event(row: dict, tz, now: datetime) -> dict:
    """One event, masked and labelled, in the shape the board renders."""
    safe = mask(row)
    start = parse_dt(row.get("starts_at"), tz)
    end = parse_dt(row.get("ends_at"), tz)
    all_day = bool(row.get("all_day"))
    status = row.get("status") or "scheduled"

    state = "cancelled" if status == "cancelled" else event_state(start, end, now, all_day)

    return {
        "id": str(row.get("id") or ""),
        "title": safe.get("title") or "",
        "host_org": safe.get("host_org"),
        "room": row.get("room"),
        "starts_at": start.isoformat() if start else None,
        "ends_at": end.isoformat() if end else None,
        "all_day": all_day,
        "time_label": time_label(start, end, all_day),
        "note": safe.get("public_note"),
        "status": status,
        "is_private": bool(row.get("is_private")),
        "state": state,
    }


def day_schedule(venue_slug: str | None = None, day=None,
                 now: datetime | None = None) -> list:
    """Every event at a venue on one venue-local day, board-shaped."""
    venue = venue_config(venue_slug)
    tz = _tzinfo(venue["timezone"])
    now = now.astimezone(tz) if now else datetime.now(tz)
    target = parse_dt(day, tz).date() if day else now.date()

    midnight = datetime.combine(target, time.min, tzinfo=tz)
    rows = list_events(venue["slug"], start=midnight, end=midnight + timedelta(days=1))
    return [_board_event(row, tz, now) for row in rows]


def board_payload(venue_slug: str | None = None,
                  now: datetime | None = None) -> dict:
    """Everything GET /board/events.json returns.

    The board re-derives `state` client-side every few seconds so the highlight
    stays honest between fetches; the copy here is what a no-JS render (or a
    debugging curl) sees.
    """
    venue = venue_config(venue_slug)
    tz = _tzinfo(venue["timezone"])
    now = now.astimezone(tz) if now else datetime.now(tz)

    events = day_schedule(venue["slug"], day=now.date(), now=now)
    live = [e for e in events if e["state"] not in ("ended", "cancelled")]

    # Nothing left today — look ahead so the screen has something to say.
    upcoming, upcoming_day = [], None
    if not live:
        for offset in range(1, LOOKAHEAD_DAYS + 1):
            ahead = now.date() + timedelta(days=offset)
            found = [e for e in day_schedule(venue["slug"], day=ahead, now=now)
                     if e["status"] != "cancelled"]
            if found:
                upcoming, upcoming_day = found, ahead
                break

    return {
        "venue": {
            "slug": venue["slug"],
            "name": venue["name"],
            "subtitle": venue["subtitle"],
            "timezone": venue["timezone"],
        },
        "generated_at": now.isoformat(),
        "day": now.date().isoformat(),
        "day_label": f"{now:%A, %B} {now.day}",
        "events": events,
        "counts": {
            "total": len(events),
            "remaining": len(live),
            "on_now": len([e for e in events if e["state"] == "on"]),
            "private": len([e for e in events if e["is_private"]]),
            "cancelled": len([e for e in events if e["status"] == "cancelled"]),
        },
        "lookahead": {
            "day": upcoming_day.isoformat() if upcoming_day else None,
            "day_label": (f"{upcoming_day:%A, %B} {upcoming_day.day}"
                          if upcoming_day else None),
            "events": upcoming,
        },
        "lead_in_minutes": LEAD_IN_MINUTES,
        "linger_minutes": LINGER_MINUTES,
    }
