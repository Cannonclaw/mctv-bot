# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Event feed service — turns a venue's public calendar into screen content.

A "feed" is a standing arrangement with a venue: we pull their published
calendar on a schedule, normalize it, and render it as loop slides that run on
their screens. The venue gets a always-current event board they don't maintain;
we get a reason to put screens somewhere we want them.

    event_feeds   one row per venue calendar we track
    feed_events   the normalized events pulled from it (cache + history)

Fetching is stdlib only (urllib), same rule as web_scraper. Three source types:

    tribe   The Events Calendar REST API (WordPress) — the common case for
            venue and tourism sites. Clean JSON, venue data included.
    ics     Any iCalendar feed (Google Calendar, Outlook, most booking apps).
    manual  Paste an .ics export or type events in. Always available, and the
            answer when a site's WAF blocks automated fetches.

`discover()` probes a bare site URL for the first two so nobody has to know
which one a venue runs.

Storage is Supabase REST with a local JSON fallback (data/feeds/), the same
pattern screen_inventory_service and pipeline_service use, so the page still
works when Supabase is unreachable.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "feeds"

FEEDS_TABLE = "event_feeds"
EVENTS_TABLE = "feed_events"

MARKETS = ["oxford", "starkville", "tupelo", "columbus", "west_point"]

MARKET_LABELS = {
    "oxford": "Oxford",
    "starkville": "Starkville",
    "tupelo": "Tupelo",
    "columbus": "Columbus",
    "west_point": "West Point",
}

SOURCE_TYPES = {
    "tribe": "The Events Calendar (WordPress)",
    "ics": "iCalendar / ICS feed",
    "manual": "Manual entry / pasted export",
}

STATUSES = ["active", "paused", "prospect"]

# Browser UA. Venue sites are marketing sites behind CDNs that reject the
# default urllib agent outright.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

FETCH_TIMEOUT = 20

# Paths probed by discover(), in the order we want to find them.
TRIBE_PATHS = ["/wp-json/tribe/events/v1/events"]
ICS_PATHS = [
    "/events.ics",
    "/calendar.ics",
    "/?ical=1",
    "/events/?ical=1",
    "/schedule/?ical=1",
    "/schedule/list/?ical=1",
]

# Slide defaults — 4 events reads cleanly at across-the-room distance.
DEFAULT_EVENTS_PER_SLIDE = 4
DEFAULT_WINDOW_DAYS = 21
DEFAULT_MAX_SLIDES = 6


# ── Helpers ──────────────────────────────────────────────────────────────────

def market_label(market: str) -> str:
    return MARKET_LABELS.get(market, (market or "").replace("_", " ").title())


def slugify(text: str) -> str:
    """Lowercase hyphenated slug — feed keys and generated file names."""
    clean = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower())
    return clean.strip("-") or "feed"


def normalize(text: str | None) -> str:
    """Loose key for matching venue names across systems."""
    clean = re.sub(r"[^a-z0-9]+", " ", (text or "").strip().lower())
    return re.sub(r"\s+", " ", clean).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_html(text: str | None) -> str:
    """Plain text from an HTML fragment — calendar descriptions arrive as HTML."""
    if not text:
        return ""
    clean = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    clean = re.sub(r"</p>", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", "", clean)
    clean = (clean.replace("&amp;", "&").replace("&nbsp;", " ")
                  .replace("&#8217;", "'").replace("&#8211;", "-")
                  .replace("&quot;", '"').replace("&#039;", "'")
                  .replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", clean).strip()


def parse_dt(value) -> datetime | None:
    """Parse the date shapes calendars emit into an aware UTC datetime.

    Handles ISO 8601 (with or without a zone), The Events Calendar's
    "YYYY-MM-DD HH:MM:SS", and ICS basic format ("20260808T080000Z",
    "20260808"). Naive values are treated as UTC so comparisons never raise.
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip()
        parsed = None

        # ICS basic: 20260808T080000Z / 20260808T080000 / 20260808
        compact = re.fullmatch(r"(\d{8})(T(\d{6})(Z)?)?", text)
        if compact:
            day = compact.group(1)
            clock = compact.group(3) or "000000"
            try:
                parsed = datetime.strptime(day + clock, "%Y%m%d%H%M%S")
                if compact.group(4):
                    parsed = parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                parsed = None

        if parsed is None:
            candidate = text.replace("Z", "+00:00")
            # "2026-08-08 08:00:00" — Tribe's REST format.
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}", candidate):
                candidate = candidate.replace(" ", "T", 1)
            try:
                parsed = datetime.fromisoformat(candidate)
            except ValueError:
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
                    try:
                        parsed = datetime.strptime(text, fmt)
                        break
                    except ValueError:
                        continue

        if parsed is None:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value) -> str | None:
    parsed = parse_dt(value)
    return parsed.isoformat() if parsed else None


# ── Fetching ─────────────────────────────────────────────────────────────────

class FeedFetchError(Exception):
    """A feed source could not be read. Message is shown to the user as-is."""


def _http_get(url: str, timeout: int = FETCH_TIMEOUT) -> str:
    """GET a URL as text, with error messages a salesperson can act on."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/calendar, text/html;q=0.9, */*;q=0.8",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 406, 429):
            raise FeedFetchError(
                f"{url} refused the request (HTTP {exc.code}). The site is "
                "likely behind a bot filter — use Manual import with an .ics "
                "export, or ask the venue for a calendar share link."
            ) from exc
        if exc.code == 404:
            raise FeedFetchError(f"{url} returned 404 — no calendar at that path.") from exc
        raise FeedFetchError(f"{url} returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise FeedFetchError(f"Could not reach {url}: {exc.reason}") from exc
    except Exception as exc:  # timeouts, decode errors, bad URLs
        raise FeedFetchError(f"Could not read {url}: {exc}") from exc


def _base_url(url: str) -> str:
    """Scheme + host from any URL the user pastes in."""
    text = (url or "").strip()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = "https://" + text
    parts = urllib.parse.urlsplit(text)
    return f"{parts.scheme}://{parts.netloc}"


# ── Source: The Events Calendar (WordPress) ──────────────────────────────────

def fetch_tribe(endpoint: str, window_days: int = DEFAULT_WINDOW_DAYS,
                per_page: int = 50) -> list[dict]:
    """Events from a The Events Calendar REST endpoint.

    The API defaults to upcoming events; start_date/end_date bound it to the
    window we actually render so a busy tournament calendar doesn't page
    forever.
    """
    today = datetime.now(timezone.utc).date()
    params = {
        "per_page": min(max(int(per_page), 1), 50),
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=max(int(window_days), 1))).isoformat(),
    }
    separator = "&" if "?" in endpoint else "?"
    url = f"{endpoint}{separator}{urllib.parse.urlencode(params)}"

    raw = _http_get(url)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FeedFetchError(
            f"{endpoint} did not return JSON — it may not be a The Events "
            "Calendar site."
        ) from exc

    if not isinstance(payload, dict) or "events" not in payload:
        raise FeedFetchError(f"{endpoint} returned JSON without an 'events' list.")

    return [_from_tribe(event) for event in (payload.get("events") or [])]


def _from_tribe(event: dict) -> dict:
    venue = event.get("venue") or {}
    categories = [c.get("name", "") for c in (event.get("categories") or []) if c.get("name")]
    return {
        "uid": str(event.get("id") or event.get("global_id") or event.get("url") or ""),
        "title": _strip_html(event.get("title")),
        "starts_at": _iso(event.get("utc_start_date") or event.get("start_date")),
        "ends_at": _iso(event.get("utc_end_date") or event.get("end_date")),
        "all_day": bool(event.get("all_day")),
        "venue": _strip_html(venue.get("venue")) if isinstance(venue, dict) else "",
        "url": event.get("url") or "",
        "categories": categories,
        "description": _strip_html(event.get("excerpt") or event.get("description"))[:500],
    }


# ── Source: iCalendar ────────────────────────────────────────────────────────

def parse_ics(text: str) -> list[dict]:
    """Events from iCalendar text.

    Handles RFC 5545 line folding (continuation lines start with a space or
    tab) and the `DTSTART;VALUE=DATE:` / `DTSTART;TZID=...:` property forms.
    """
    if not text or "BEGIN:VEVENT" not in text:
        raise FeedFetchError(
            "That doesn't look like an iCalendar feed — no VEVENT blocks found."
        )

    # Unfold: a leading space or tab continues the previous line.
    unfolded: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    events: list[dict] = []
    current: dict | None = None
    for line in unfolded:
        stripped = line.strip()
        if stripped == "BEGIN:VEVENT":
            current = {}
            continue
        if stripped == "END:VEVENT":
            if current is not None:
                events.append(_from_ics(current))
            current = None
            continue
        if current is None or ":" not in line:
            continue

        prop, _, value = line.partition(":")
        name, _, param_text = prop.partition(";")
        name = name.strip().upper()
        if not name:
            continue
        value = (value.strip()
                 .replace("\\n", " ").replace("\\N", " ")
                 .replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\"))
        current[name] = value
        if name in ("DTSTART", "DTEND"):
            current[name + "_PARAMS"] = param_text.upper()

    return events


def _from_ics(raw: dict) -> dict:
    categories = [c.strip() for c in (raw.get("CATEGORIES") or "").split(",") if c.strip()]
    all_day = "VALUE=DATE" in (raw.get("DTSTART_PARAMS") or "")
    return {
        "uid": raw.get("UID") or "",
        "title": _strip_html(raw.get("SUMMARY")),
        "starts_at": _iso(raw.get("DTSTART")),
        "ends_at": _iso(raw.get("DTEND")),
        "all_day": all_day,
        "venue": _strip_html(raw.get("LOCATION")),
        "url": raw.get("URL") or "",
        "categories": categories,
        "description": _strip_html(raw.get("DESCRIPTION"))[:500],
    }


def fetch_ics(url: str) -> list[dict]:
    """Events from a hosted .ics URL."""
    return parse_ics(_http_get(url))


# ── Discovery ────────────────────────────────────────────────────────────────

def discover(site_url: str) -> dict:
    """Find a usable calendar endpoint on a bare site URL.

    Returns {source_type, endpoint, event_count, attempts}. `attempts` records
    every probe with its outcome so a failed discovery still tells the user
    what the site actually said — a WAF 403 and a plain 404 need different
    next moves.
    """
    base = _base_url(site_url)
    attempts: list[dict] = []
    if not base:
        return {"source_type": "", "endpoint": "", "event_count": 0, "attempts": attempts}

    for path in TRIBE_PATHS:
        endpoint = base + path
        try:
            events = fetch_tribe(endpoint)
            attempts.append({"endpoint": endpoint, "ok": True, "detail": f"{len(events)} events"})
            return {"source_type": "tribe", "endpoint": endpoint,
                    "event_count": len(events), "attempts": attempts}
        except FeedFetchError as exc:
            attempts.append({"endpoint": endpoint, "ok": False, "detail": str(exc)})

    for path in ICS_PATHS:
        endpoint = base + path
        try:
            events = fetch_ics(endpoint)
            attempts.append({"endpoint": endpoint, "ok": True, "detail": f"{len(events)} events"})
            return {"source_type": "ics", "endpoint": endpoint,
                    "event_count": len(events), "attempts": attempts}
        except FeedFetchError as exc:
            attempts.append({"endpoint": endpoint, "ok": False, "detail": str(exc)})

    return {"source_type": "", "endpoint": "", "event_count": 0, "attempts": attempts}


# ── Normalizing ──────────────────────────────────────────────────────────────

def clean_events(events: list[dict], venue_filter: str = "",
                 window_days: int = DEFAULT_WINDOW_DAYS,
                 now: datetime | None = None) -> list[dict]:
    """Drop unusable rows, filter to a venue and window, dedupe, sort.

    `venue_filter` matters for shared calendars — a tourism site lists every
    venue in town, and we only want the one whose screens we're feeding. An
    event whose venue is blank is kept, since single-venue feeds often omit it.
    """
    reference = now or datetime.now(timezone.utc)
    horizon = reference + timedelta(days=max(int(window_days), 1))
    wanted = normalize(venue_filter)

    kept: list[dict] = []
    for event in events or []:
        title = (event.get("title") or "").strip()
        starts = parse_dt(event.get("starts_at"))
        if not title or starts is None:
            continue

        ends = parse_dt(event.get("ends_at"))
        # Keep multi-day tournaments visible until the last day is over.
        finishes = ends or starts
        if finishes < reference.replace(hour=0, minute=0, second=0, microsecond=0):
            continue
        if starts > horizon:
            continue

        if wanted:
            venue = normalize(event.get("venue"))
            if venue and wanted not in venue and venue not in wanted:
                continue

        kept.append({
            "uid": (event.get("uid") or "").strip(),
            "title": title,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat() if ends else None,
            "all_day": bool(event.get("all_day")),
            "venue": (event.get("venue") or "").strip(),
            "url": (event.get("url") or "").strip(),
            "categories": event.get("categories") or [],
            "description": (event.get("description") or "").strip(),
        })

    # Dedupe on uid when present, else on title + start — the same tournament
    # often appears under both a series and a per-day entry.
    seen: set[str] = set()
    unique: list[dict] = []
    for event in kept:
        key = event["uid"] or f"{normalize(event['title'])}|{event['starts_at'][:10]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)

    unique.sort(key=lambda e: (e["starts_at"], e["title"]))
    return unique


# ── Slide rendering ──────────────────────────────────────────────────────────

def format_event_date(event: dict) -> str:
    """Screen-legible date: 'SAT AUG 8' or 'AUG 8-10' for a multi-day run."""
    starts = parse_dt(event.get("starts_at"))
    if starts is None:
        return ""
    ends = parse_dt(event.get("ends_at"))
    if ends and ends.date() > starts.date():
        if ends.month == starts.month:
            return f"{starts.strftime('%b').upper()} {starts.day}-{ends.day}"
        return (f"{starts.strftime('%b').upper()} {starts.day} - "
                f"{ends.strftime('%b').upper()} {ends.day}")
    return f"{starts.strftime('%a %b').upper()} {starts.day}"


def format_event_time(event: dict) -> str:
    """'8:00 AM', 'ALL DAY', or '' — trailing zeros trimmed for screen width."""
    if event.get("all_day"):
        return "ALL DAY"
    starts = parse_dt(event.get("starts_at"))
    if starts is None:
        return ""
    ends = parse_dt(event.get("ends_at"))
    if ends and ends.date() > starts.date():
        return "ALL DAY"
    if starts.hour == 0 and starts.minute == 0:
        return ""
    # Built by hand rather than strftime("%-I") — that flag is glibc-only and
    # raises on Windows, where the app also runs locally.
    hour = starts.hour % 12 or 12
    meridiem = "AM" if starts.hour < 12 else "PM"
    return (f"{hour}:{starts.minute:02d} {meridiem}" if starts.minute
            else f"{hour} {meridiem}")


def build_slides(events: list[dict], headline: str = "Upcoming Events",
                 footer: str = "", events_per_slide: int = DEFAULT_EVENTS_PER_SLIDE,
                 max_slides: int = DEFAULT_MAX_SLIDES) -> list[dict]:
    """Chunk events into screen slides.

    Each slide is {headline, footer, index, total, lines[]}, where a line is
    {date, time, title, detail}. Rendering (HTML preview, Creatomate, the
    design team's template) consumes this shape rather than the raw feed.
    """
    per_slide = max(int(events_per_slide or DEFAULT_EVENTS_PER_SLIDE), 1)
    cap = max(int(max_slides or DEFAULT_MAX_SLIDES), 1)

    chunks = [events[i:i + per_slide] for i in range(0, len(events), per_slide)][:cap]
    slides: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        slides.append({
            "index": index,
            "total": len(chunks),
            "headline": headline,
            "footer": footer,
            "lines": [{
                "date": format_event_date(event),
                "time": format_event_time(event),
                "title": event.get("title", ""),
                "detail": event.get("venue", ""),
            } for event in chunk],
        })
    for slide in slides:
        slide["total"] = len(slides)
    return slides


def slides_to_text(slides: list[dict]) -> str:
    """Plain-text script of the slides — what gets pasted to a designer."""
    blocks: list[str] = []
    for slide in slides:
        lines = [f"SLIDE {slide['index']} of {slide['total']}",
                 slide.get("headline", "")]
        for line in slide.get("lines", []):
            time_part = f" - {line['time']}" if line.get("time") else ""
            lines.append(f"  {line['date']}{time_part} | {line['title']}")
        if slide.get("footer"):
            lines.append(f"  {slide['footer']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ── HTML preview ─────────────────────────────────────────────────────────────

NAVY = "#1B1F3B"
GOLD = "#C5A55A"
CREAM = "#F0EDE4"


def _escape(text: str) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def slides_to_html(slides: list[dict], title: str = "MCTV Event Feed") -> str:
    """A 16:9 branded preview of the slides, one card per slide.

    Self-contained HTML so it can be opened from disk, dropped in a proposal,
    or screenshotted for the venue. Not the production render — the design
    team's template is — but close enough to sell from.
    """
    cards: list[str] = []
    for slide in slides:
        rows: list[str] = []
        for line in slide.get("lines", []):
            time_html = (f'<span class="time">{_escape(line["time"])}</span>'
                         if line.get("time") else "")
            detail_html = (f'<div class="detail">{_escape(line["detail"])}</div>'
                           if line.get("detail") else "")
            rows.append(
                '<li class="row">'
                f'<div class="when"><span class="date">{_escape(line["date"])}</span>{time_html}</div>'
                f'<div class="what"><div class="title">{_escape(line["title"])}</div>{detail_html}</div>'
                "</li>"
            )
        cards.append(
            '<figure class="slide">'
            '<div class="canvas">'
            f'<header><h2>{_escape(slide.get("headline", ""))}</h2><span class="rule"></span></header>'
            f'<ul class="rows">{"".join(rows)}</ul>'
            f'<footer><span>{_escape(slide.get("footer", ""))}</span>'
            f'<span class="count">{slide.get("index", 1)} / {slide.get("total", 1)}</span></footer>'
            "</div>"
            f'<figcaption>Slide {slide.get("index", 1)} of {slide.get("total", 1)}</figcaption>'
            "</figure>"
        )

    if not cards:
        cards.append('<p class="empty">No events in the window — nothing to render yet.</p>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(title)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px; background: {CREAM};
         font-family: Arial, Helvetica, sans-serif; color: {NAVY}; }}
  h1 {{ font-size: 22px; letter-spacing: .08em; text-transform: uppercase; margin: 0 0 4px; }}
  .sub {{ color: #6b6f7d; font-size: 13px; margin: 0 0 28px; }}
  .slide {{ margin: 0 0 32px; max-width: 1100px; }}
  .canvas {{ position: relative; aspect-ratio: 16 / 9; background: {NAVY};
             color: #fff; padding: 4.2% 5%; display: flex; flex-direction: column;
             box-shadow: 0 10px 30px rgba(27,31,59,.28); }}
  header h2 {{ font-size: clamp(20px, 3.4vw, 46px); margin: 0; letter-spacing: .02em;
               text-transform: uppercase; }}
  .rule {{ display: block; width: 92px; height: 5px; background: {GOLD}; margin: 14px 0 0; }}
  .rows {{ list-style: none; margin: auto 0; padding: 0; display: flex;
           flex-direction: column; gap: clamp(8px, 1.6vh, 22px); }}
  .row {{ display: grid; grid-template-columns: 27% 1fr; gap: 3%; align-items: baseline;
          border-bottom: 1px solid rgba(255,255,255,.12); padding-bottom: clamp(6px,1.2vh,14px); }}
  .row:last-child {{ border-bottom: 0; }}
  .date {{ color: {GOLD}; font-weight: 700; letter-spacing: .06em;
           font-size: clamp(12px, 1.65vw, 24px); }}
  .time {{ display: block; color: rgba(255,255,255,.62); letter-spacing: .05em;
           font-size: clamp(10px, 1.15vw, 16px); margin-top: 3px; }}
  .title {{ font-size: clamp(14px, 2.05vw, 30px); font-weight: 700; line-height: 1.18; }}
  .detail {{ color: rgba(255,255,255,.62); font-size: clamp(10px, 1.15vw, 16px); margin-top: 3px; }}
  footer {{ display: flex; justify-content: space-between; align-items: center;
            border-top: 1px solid rgba(255,255,255,.16); padding-top: 12px;
            color: rgba(255,255,255,.72); letter-spacing: .07em;
            font-size: clamp(9px, 1.05vw, 14px); text-transform: uppercase; }}
  .count {{ color: {GOLD}; }}
  figcaption {{ font-size: 12px; color: #6b6f7d; margin-top: 8px; letter-spacing: .04em; }}
  .empty {{ color: #6b6f7d; }}
</style></head>
<body>
<h1>{_escape(title)}</h1>
<p class="sub">Preview of the loop slides generated from the live calendar feed.</p>
{"".join(cards)}
</body></html>"""


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


def _replace_events(feed_id: str, rows: list[dict]) -> bool:
    """Swap a feed's cached events for a fresh pull.

    A refresh is a full replace, not a merge — the venue's calendar is the
    source of truth, and a cancelled tournament has to be able to disappear.
    """
    if _supabase_ready():
        try:
            from services.supabase_client import delete_row, insert_row
            delete_row(EVENTS_TABLE, feed_id, id_column="feed_id")
            for row in rows:
                insert_row(EVENTS_TABLE, row)
            return True
        except Exception as exc:
            logger.error("Supabase event replace failed, using local copy: %s", exc)
    existing = [r for r in _local_read(EVENTS_TABLE) if str(r.get("feed_id")) != str(feed_id)]
    for row in rows:
        row.setdefault("id", str(uuid.uuid4()))
    return _local_write(EVENTS_TABLE, existing + rows)


# ── Feeds ────────────────────────────────────────────────────────────────────

def get_feeds(market: str | None = None, status: str | None = None) -> list:
    """All feeds, newest first, optionally filtered by market and status."""
    rows = _fetch(FEEDS_TABLE)
    if market:
        rows = [r for r in rows if r.get("market") == market]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True)


def get_feed(feed_id: str) -> dict | None:
    for row in _fetch(FEEDS_TABLE):
        if str(row.get("id")) == str(feed_id):
            return row
    return None


def find_feed_by_slug(slug: str) -> dict | None:
    target = slugify(slug)
    for row in _fetch(FEEDS_TABLE):
        if row.get("slug") == target:
            return row
    return None


def save_feed(data: dict) -> dict | None:
    """Create a feed. Slug is derived from the name and must be unique."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Feed name is required.")

    slug = slugify(data.get("slug") or name)
    if find_feed_by_slug(slug):
        raise ValueError(f"A feed with the slug '{slug}' already exists.")

    source_type = data.get("source_type") or "manual"
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unknown source type '{source_type}'.")

    row = {
        "name": name,
        "slug": slug,
        "market": data.get("market") or "oxford",
        "venue_name": (data.get("venue_name") or "").strip(),
        "source_url": (data.get("source_url") or "").strip(),
        "source_type": source_type,
        "endpoint": (data.get("endpoint") or "").strip(),
        "venue_filter": (data.get("venue_filter") or "").strip(),
        "headline": (data.get("headline") or f"Upcoming at {name}").strip(),
        "footer": (data.get("footer") or "").strip(),
        "events_per_slide": int(data.get("events_per_slide") or DEFAULT_EVENTS_PER_SLIDE),
        "max_slides": int(data.get("max_slides") or DEFAULT_MAX_SLIDES),
        "window_days": int(data.get("window_days") or DEFAULT_WINDOW_DAYS),
        "status": data.get("status") or "prospect",
        "notes": (data.get("notes") or "").strip(),
        "last_fetched_at": None,
        "last_status": "",
        "last_error": "",
        "event_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    return _insert(FEEDS_TABLE, row)


ALLOWED_FEED_FIELDS = {
    "name", "market", "venue_name", "source_url", "source_type", "endpoint",
    "venue_filter", "headline", "footer", "events_per_slide", "max_slides",
    "window_days", "status", "notes", "last_fetched_at", "last_status",
    "last_error", "event_count",
}


def update_feed(feed_id: str, changes: dict) -> dict | None:
    clean = {k: v for k, v in (changes or {}).items() if k in ALLOWED_FEED_FIELDS}
    if not clean:
        return get_feed(feed_id)
    clean["updated_at"] = _now()
    return _update(FEEDS_TABLE, feed_id, clean)


def delete_feed(feed_id: str) -> bool:
    _replace_events(feed_id, [])
    return _delete(FEEDS_TABLE, feed_id)


# ── Events ───────────────────────────────────────────────────────────────────

def get_events(feed_id: str) -> list:
    """Cached events for a feed, soonest first."""
    rows = [r for r in _fetch(EVENTS_TABLE) if str(r.get("feed_id")) == str(feed_id)]
    return sorted(rows, key=lambda r: r.get("starts_at") or "")


def fetch_feed_events(feed: dict) -> list[dict]:
    """Pull raw events for a feed from its configured source.

    Manual feeds have no source to pull from — their events are whatever was
    last imported, so the cache is returned unchanged.
    """
    source_type = feed.get("source_type") or "manual"
    endpoint = (feed.get("endpoint") or "").strip()
    window = int(feed.get("window_days") or DEFAULT_WINDOW_DAYS)

    if source_type == "manual":
        return get_events(feed.get("id"))
    if not endpoint:
        raise FeedFetchError("This feed has no endpoint set. Run Discover, or paste one in.")
    if source_type == "tribe":
        return fetch_tribe(endpoint, window_days=window)
    if source_type == "ics":
        return fetch_ics(endpoint)
    raise FeedFetchError(f"Unknown source type '{source_type}'.")


def refresh_feed(feed_id: str) -> dict:
    """Pull, normalize, and cache a feed's events.

    Returns {ok, count, error, events}. A failed refresh is recorded on the
    feed (last_status / last_error) and leaves the previous events in place —
    a screen keeps showing last week's board rather than going blank because
    the venue's site had a bad morning.
    """
    feed = get_feed(feed_id)
    if not feed:
        return {"ok": False, "count": 0, "error": "Feed not found.", "events": []}

    try:
        raw = fetch_feed_events(feed)
    except FeedFetchError as exc:
        update_feed(feed_id, {"last_fetched_at": _now(), "last_status": "error",
                              "last_error": str(exc)})
        return {"ok": False, "count": 0, "error": str(exc), "events": get_events(feed_id)}

    events = clean_events(
        raw,
        venue_filter=feed.get("venue_filter") or "",
        window_days=int(feed.get("window_days") or DEFAULT_WINDOW_DAYS),
    )

    fetched = _now()
    _replace_events(feed_id, [{
        "feed_id": feed_id,
        "uid": event["uid"],
        "title": event["title"],
        "starts_at": event["starts_at"],
        "ends_at": event["ends_at"],
        "all_day": event["all_day"],
        "venue": event["venue"],
        "url": event["url"],
        "categories": event["categories"],
        "description": event["description"],
        "fetched_at": fetched,
    } for event in events])

    update_feed(feed_id, {"last_fetched_at": fetched, "last_status": "ok",
                          "last_error": "", "event_count": len(events)})
    return {"ok": True, "count": len(events), "error": "", "events": events}


def import_events(feed_id: str, events: list[dict]) -> dict:
    """Replace a feed's events with a hand-supplied list (manual / pasted ICS)."""
    feed = get_feed(feed_id)
    if not feed:
        return {"ok": False, "count": 0, "error": "Feed not found."}

    cleaned = clean_events(
        events,
        venue_filter=feed.get("venue_filter") or "",
        window_days=int(feed.get("window_days") or DEFAULT_WINDOW_DAYS),
    )
    fetched = _now()
    _replace_events(feed_id, [{
        "feed_id": feed_id, "fetched_at": fetched, **{
            k: event[k] for k in ("uid", "title", "starts_at", "ends_at", "all_day",
                                  "venue", "url", "categories", "description")
        }
    } for event in cleaned])

    update_feed(feed_id, {"last_fetched_at": fetched, "last_status": "ok",
                          "last_error": "", "event_count": len(cleaned)})
    return {"ok": True, "count": len(cleaned), "error": ""}


def feed_slides(feed: dict, events: list[dict] | None = None) -> list[dict]:
    """Slides for a feed from its cached events and slide settings."""
    rows = events if events is not None else get_events(feed.get("id"))
    return build_slides(
        rows,
        headline=feed.get("headline") or f"Upcoming at {feed.get('name', '')}",
        footer=feed.get("footer") or "",
        events_per_slide=int(feed.get("events_per_slide") or DEFAULT_EVENTS_PER_SLIDE),
        max_slides=int(feed.get("max_slides") or DEFAULT_MAX_SLIDES),
    )


def feed_health(feed: dict) -> dict:
    """Is this feed safe to leave on a screen unattended?

    Returns {level, message}. `level` is ok / warn / error. Stale is the
    failure that matters: a feed nobody notices has stopped updating is worse
    than one that visibly errored, because the screen looks fine.
    """
    status = feed.get("last_status") or ""
    if status == "error":
        return {"level": "error", "message": feed.get("last_error") or "Last refresh failed."}
    if not feed.get("last_fetched_at"):
        return {"level": "warn", "message": "Never refreshed."}

    fetched = parse_dt(feed.get("last_fetched_at"))
    if fetched is None:
        return {"level": "warn", "message": "Last refresh time is unreadable."}

    age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    if age_hours > 72:
        return {"level": "error", "message": f"Stale — last refreshed {int(age_hours / 24)} days ago."}
    if age_hours > 36:
        return {"level": "warn", "message": f"Last refreshed {int(age_hours)} hours ago."}
    if not feed.get("event_count"):
        return {"level": "warn", "message": "Refreshed fine, but no events in the window."}
    return {"level": "ok", "message": f"{feed.get('event_count')} events, refreshed cleanly."}


def refresh_all(market: str | None = None) -> list[dict]:
    """Refresh every active feed. Returns one result row per feed."""
    results = []
    for feed in get_feeds(market=market, status="active"):
        outcome = refresh_feed(feed["id"])
        results.append({"feed": feed.get("name"), "id": feed.get("id"), **outcome})
    return results
