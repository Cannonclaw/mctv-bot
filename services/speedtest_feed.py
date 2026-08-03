# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sponsored live speed-test feed — config, URL building, payload helpers.

The feed itself is a self-contained page (static/feed_speedtest.html) that
a screen loads as a URL zone: sponsor intro -> live speed test -> sponsor
outro, looping forever. Everything the sponsor controls travels in the
query string, so selling a new sponsor is a new URL, not a deploy.

This module is the Python half:

  * FeedConfig ......... validated sponsor/timing settings
  * feed_url() ......... build the screen URL from a FeedConfig
  * parse_feed_config()  rebuild a FeedConfig from a URL (round-trips)
  * payload(n) ......... incompressible bytes for the local test endpoint
  * clamp_down_bytes() . hard server-side cap on a download request

WHERE THE TEST MEASURES TO (`endpoint`):
  "cf"     - Cloudflare's public speed endpoints. Default. Costs MCTV no
             bandwidth and measures the venue's real path to the internet,
             which is the number a fiber sponsor actually wants shown.
  "local"  - our own /feed/speedtest/* endpoints. Every byte is Render
             bandwidth we pay for, so this is for demos, and for venues
             where Cloudflare is unreachable (the page falls back to it
             on its own).
  a URL    - sponsor-hosted, Cloudflare-shaped (`/__down?bytes=`, `/__up`)
             and CORS-open. The best answer when the sponsor is an ISP:
             the test then runs against the sponsor's own network.

BANDWIDTH IS THE VENUE'S. A real test moves real bytes over the host's
Wi-Fi, so the feed measures on an interval (default 30 min) and shows the
last result with an honest age stamp in between - it never re-animates a
stale number as if it were live. At the defaults that is roughly 23 GB of
venue traffic per screen per month; `interval_seconds` is the knob.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

# --------------------------------------------------------------------------
# Limits. The page enforces its own copies of these; these are the server
# and builder side, so a hand-edited URL cannot ask for something silly.
# --------------------------------------------------------------------------

INTRO_RANGE = (5, 10)      # seconds, per the sponsorship spec
OUTRO_RANGE = (5, 10)
TEST_RANGE = (10, 45)      # seconds budgeted for the measurement phase
INTERVAL_RANGE = (60, 21600)   # seconds between real measurements
MAX_DOWN_MB_RANGE = (2, 64)    # per-test download budget
MAX_UP_MB_RANGE = (1, 32)      # per-test upload budget

# One HTTP download request may not exceed this. The page asks for far
# less; the cap exists so a stray /feed/speedtest/down?bytes=99999999999
# cannot turn our own dyno into someone's free bandwidth faucet.
MAX_DOWN_REQUEST_BYTES = 8 * 1024 * 1024
MAX_UP_REQUEST_BYTES = 8 * 1024 * 1024

DEFAULT_BASE_URL = "https://mctv-bot.onrender.com"
FEED_PATH = "/feed/speedtest"

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Cloudflare's public endpoints, and anything shaped like them.
CLOUDFLARE_BASE = "https://speed.cloudflare.com"


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clean_text(value: object, limit: int = 120) -> str:
    """Collapse whitespace and trim. Text lands on screen via textContent,
    so this is tidiness, not the injection defense."""
    text = " ".join(str(value or "").split())
    return text[:limit]


def _clean_color(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("#"):
        text = "#" + text
    return text.lower() if HEX_COLOR.match(text) else fallback


def _clean_https(value: object) -> str:
    """Only https (or a data: image) may reach a screen. A logo over http
    is a mixed-content block on the player, i.e. a blank box."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("data:image/"):
        return text[:4096]
    parts = urlsplit(text)
    if parts.scheme == "https" and parts.netloc:
        return text[:600]
    return ""


def _clean_endpoint(value: object) -> str:
    text = str(value or "").strip() or "cf"
    if text in ("cf", "cloudflare"):
        return "cf"
    if text == "local":
        return "local"
    cleaned = _clean_https(text)
    return cleaned.rstrip("/") if cleaned else "cf"


@dataclass
class FeedConfig:
    """Everything a sponsored speed-test feed needs to render.

    Field names double as query-string keys, so adding a field here is all
    it takes for the builder page and the feed page to agree on it - as
    long as the same key is read in static/feed_speedtest.html.
    """

    # Sponsor identity
    sponsor: str = "Your Fiber Company"
    tagline: str = "Fiber internet, built for Mississippi"
    logo: str = ""                      # https URL or data: image
    color: str = "#c5a55a"              # accent
    color2: str = "#0a1220"             # backdrop
    phone: str = ""
    web: str = ""
    cta: str = "Ask about fiber at your address"

    # Comparison bar on the result card. Set compare_mbps to 0 to hide it.
    compare_mbps: int = 0
    compare_label: str = ""

    # Timing (seconds)
    intro_seconds: int = 8
    outro_seconds: int = 8
    test_seconds: int = 20
    interval_seconds: int = 1800        # between real measurements

    # Measurement
    endpoint: str = "cf"
    max_down_mb: int = 24
    max_up_mb: int = 8
    streams: int = 4

    # Placement / presentation
    venue: str = ""
    market: str = ""
    width: int = 1920
    height: int = 1080
    demo: bool = False                  # simulated numbers, badged on screen

    def __post_init__(self) -> None:
        self.sponsor = _clean_text(self.sponsor, 48) or "Your Fiber Company"
        self.tagline = _clean_text(self.tagline, 90)
        self.cta = _clean_text(self.cta, 90)
        self.phone = _clean_text(self.phone, 32)
        self.web = _clean_text(self.web, 90)
        self.venue = _clean_text(self.venue, 48)
        self.market = _clean_text(self.market, 32)
        self.compare_label = _clean_text(self.compare_label, 48)

        self.logo = _clean_https(self.logo)
        self.color = _clean_color(self.color, "#c5a55a")
        self.color2 = _clean_color(self.color2, "#0a1220")
        self.endpoint = _clean_endpoint(self.endpoint)

        self.intro_seconds = int(_clamp(_int(self.intro_seconds, 8), *INTRO_RANGE))
        self.outro_seconds = int(_clamp(_int(self.outro_seconds, 8), *OUTRO_RANGE))
        self.test_seconds = int(_clamp(_int(self.test_seconds, 20), *TEST_RANGE))
        self.interval_seconds = int(
            _clamp(_int(self.interval_seconds, 1800), *INTERVAL_RANGE))
        self.max_down_mb = int(_clamp(_int(self.max_down_mb, 24), *MAX_DOWN_MB_RANGE))
        self.max_up_mb = int(_clamp(_int(self.max_up_mb, 8), *MAX_UP_MB_RANGE))
        self.streams = int(_clamp(_int(self.streams, 4), 1, 8))
        self.compare_mbps = int(_clamp(_int(self.compare_mbps, 0), 0, 10000))
        self.width = int(_clamp(_int(self.width, 1920), 320, 7680))
        self.height = int(_clamp(_int(self.height, 1080), 320, 7680))
        self.demo = bool(self.demo)

    # -- derived -----------------------------------------------------------

    @property
    def cycle_seconds(self) -> int:
        """Wall-clock length of one intro -> test -> outro pass."""
        return self.intro_seconds + self.test_seconds + self.outro_seconds

    @property
    def monthly_venue_gb(self) -> float:
        """Rough venue bandwidth per screen per month at these settings.

        12 broadcast hours a day, 30 days, one real test per interval,
        assuming a connection fast enough to spend the whole byte budget.
        """
        tests_per_day = (12 * 3600) / self.interval_seconds
        mb_per_test = self.max_down_mb + self.max_up_mb
        return round(tests_per_day * 30 * mb_per_test / 1024, 1)

    def as_params(self) -> dict[str, str]:
        """Query params, omitting anything still at its default."""
        defaults = FeedConfig()
        out: dict[str, str] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value == getattr(defaults, f.name):
                continue
            if isinstance(value, bool):
                out[f.name] = "1" if value else "0"
            else:
                out[f.name] = str(value)
        return out


def _int(value: object, fallback: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return fallback


def _bool(value: object, fallback: bool = False) -> bool:
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return fallback


# --------------------------------------------------------------------------
# URL round-trip
# --------------------------------------------------------------------------

def base_url() -> str:
    """Public origin the screens will hit."""
    return (os.environ.get("PUBLIC_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def feed_url(config: FeedConfig, base: str | None = None) -> str:
    """The URL to paste into the player's URL/web zone."""
    root = (base or base_url()).rstrip("/")
    params = config.as_params()
    query = urlencode(params, quote_via=quote)
    return f"{root}{FEED_PATH}" + (f"?{query}" if query else "")


def parse_feed_config(url_or_query: str) -> FeedConfig:
    """Rebuild a FeedConfig from a full feed URL or a bare query string."""
    query = urlsplit(url_or_query).query or url_or_query.lstrip("?")
    raw = dict(parse_qsl(query, keep_blank_values=True))
    known = {f.name for f in fields(FeedConfig)}
    kwargs: dict[str, object] = {}
    for key, value in raw.items():
        if key not in known:
            continue
        kwargs[key] = _bool(value) if key == "demo" else value
    return FeedConfig(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Local test endpoint payload
# --------------------------------------------------------------------------

BLOCK_SIZE = 256 * 1024
_block: bytes | None = None


def payload_block() -> bytes:
    """A 256 KiB block of random bytes, generated once and reused.

    Random so no proxy can gzip it into a fake gigabit; reused so serving
    8 MiB does not cost 8 MiB of entropy and CPU per request. gzip's
    32 KiB window never spans two copies of a block this size, so the
    repetition on the wire is not compressible either.
    """
    global _block
    if _block is None:
        _block = os.urandom(BLOCK_SIZE)
    return _block


def clamp_down_bytes(requested: object) -> int:
    """Server-side cap for /feed/speedtest/down."""
    n = _int(requested, BLOCK_SIZE)
    return int(_clamp(n, 0, MAX_DOWN_REQUEST_BYTES))


def iter_payload(total: int):
    """Yield `total` bytes in BLOCK_SIZE chunks, so nothing large is held."""
    block = payload_block()
    sent = 0
    while sent < total:
        chunk = block if total - sent >= BLOCK_SIZE else block[: total - sent]
        sent += len(chunk)
        yield chunk


# --------------------------------------------------------------------------
# Sales helper
# --------------------------------------------------------------------------

def plays_per_hour(config: FeedConfig, zone_share: float = 1.0) -> float:
    """How many times the sponsor's name appears per screen per hour.

    Both the intro and the outro are sponsor frames, so one cycle is two
    brand impressions plus the corner mark that never leaves the screen.
    `zone_share` is the fraction of the hour the feed actually holds the
    zone (1.0 when the feed owns a dedicated screen zone).
    """
    if config.cycle_seconds <= 0:
        return 0.0
    return round(3600.0 / config.cycle_seconds * zone_share, 1)
