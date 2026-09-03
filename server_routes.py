# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Serve the public pages that are not Streamlit apps.

Five routes, all public, all GET/HEAD:

    /rates              the self-serve rate calculator (static/rates.html)
    /board              the venue lobby feed board  (static/board.html)
    /board/events.json  the schedule the board polls (venue_events_service)
    /mdot               the MDOT sponsorship mockup (static/mdot.html), so it
                        can be texted as a link instead of an HTML attachment
    /hbarena-mockup     the Huntington Bank Arena pitch mockup
                        (static/hbarena_mockup.html), same reason

Streamlit exposes no routing API, so this reaches into the web server it
boots and inserts the routes ahead of Streamlit's catch-all (which
otherwise answers /rates with the app shell). Two stacks are handled
because Streamlit is mid-migration from Tornado to Starlette/uvicorn and
which one runs depends on the version pip resolves at image build time:

  * Tornado   - a RequestHandler at the head of the wildcard router
  * Starlette - a wrapper around the ASGI app handed to uvicorn

Both patches follow the same rule as the ones in app.py: they reach into
private innards, so each is guarded on its own and none of them are
allowed to stop the app from booting. The static pages stay reachable at
/app/static/<name>.html regardless (Streamlit's own static serving, see the
SAFE_APP_STATIC_FILE_EXTENSIONS patch in app.py), so a patch that stops
matching a future Streamlit degrades to a longer URL, not a missing page.
The JSON feed has no such fallback - if the patches ever stop matching, the
board keeps rendering its last good schedule and raises the stale marker.

install() has to run BEFORE the server starts - i.e. from run_server.py.
Patches applied from app.py run too late, the routes are already built.
"""

import asyncio
import json
import logging
import time
import urllib.parse
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"

# Trailing slashes are stripped before comparing, so /rates and /rates/ both hit.
RATES_PATH = "/rates"
RATES_FILE = STATIC_DIR / "rates.html"

BOARD_PATH = "/board"
BOARD_FILE = STATIC_DIR / "board.html"
BOARD_DATA_PATH = "/board/events.json"

MDOT_PATH = "/mdot"
MDOT_FILE = STATIC_DIR / "mdot.html"

# Pitch mockup for Huntington Bank Arena — their own announced shows rendered
# as MCTV screen creative. A link is easier to send than an attachment.
HBARENA_PATH = "/hbarena-mockup"
HBARENA_FILE = STATIC_DIR / "hbarena_mockup.html"

# Plain HTML pages, path -> file. The JSON feed below is handled separately
# because it is generated rather than read off disk.
HTML_PAGES = {
    RATES_PATH: RATES_FILE,
    BOARD_PATH: BOARD_FILE,
    MDOT_PATH: MDOT_FILE,
    HBARENA_PATH: HBARENA_FILE,
}

HTML_CACHE_CONTROL = "public, max-age=300"
# Per-page overrides. A one-off pitch link is edited and re-sent mid-conversation,
# and carries a prospect's live offer terms, so it must not sit in a shared cache.
PAGE_CACHE_CONTROL = {HBARENA_PATH: "no-cache"}
# The board polls this every minute and re-derives now/next locally in between;
# a cached copy in front of it would only ever show a stale room assignment.
DATA_CACHE_CONTROL = "no-store"

# Schedule reads are shared by every screen hanging off one venue, so hold the
# rendered payload briefly rather than hitting Supabase once per board.
DATA_TTL_SECONDS = 30

_page_cache: dict[Path, bytes] = {}
_data_cache: dict[str, tuple[float, bytes]] = {}


def _page_bytes(path: Path) -> bytes | None:
    """Read a static page off disk once and hold it in memory.

    None when the file cannot be read, which _resolve turns into "not ours" so
    an unreadable page falls through to Streamlit instead of 500-ing.
    """
    cached = _page_cache.get(path)
    if cached is None:
        try:
            cached = path.read_bytes()
        except OSError as exc:
            logging.warning("public pages: %s unreadable (%s)", path, exc)
            return None
        _page_cache[path] = cached
    return cached


def _board_payload_bytes(query: str) -> bytes:
    """The board's schedule as JSON, cached per venue for DATA_TTL_SECONDS."""
    venue = urllib.parse.parse_qs(query or "").get("venue", [""])[0].strip().lower()

    hit = _data_cache.get(venue)
    if hit and (time.monotonic() - hit[0]) < DATA_TTL_SECONDS:
        return hit[1]

    from services.venue_events_service import board_payload

    body = json.dumps(board_payload(venue or None), default=str).encode("utf-8")
    _data_cache[venue] = (time.monotonic(), body)
    return body


def _error_bytes(message: str) -> bytes:
    return json.dumps({"error": message}).encode("utf-8")


def _resolve(path: str, query: str = "") -> tuple[str, bytes, str] | None:
    """Match a request path to (content_type, body, cache_control), or None.

    Returns None for anything this module does not own, which is the signal to
    hand the request back to Streamlit.
    """
    clean = (path or "").rstrip("/") or "/"

    if clean in HTML_PAGES:
        body = _page_bytes(HTML_PAGES[clean])
        if body is None:
            return None
        return ("text/html; charset=utf-8", body,
                PAGE_CACHE_CONTROL.get(clean, HTML_CACHE_CONTROL))

    if clean == BOARD_DATA_PATH.rstrip("/"):
        try:
            body = _board_payload_bytes(query)
        except Exception as exc:
            # A board on a wall must not go blank because Supabase blinked.
            # 503 keeps the last good schedule up with the stale marker raised.
            logging.warning("feed board: schedule unavailable (%s)", exc)
            return ("application/json; charset=utf-8",
                    _error_bytes("schedule unavailable"), DATA_CACHE_CONTROL)
        return ("application/json; charset=utf-8", body, DATA_CACHE_CONTROL)

    return None


# ── Tornado ──────────────────────────────────────────────────────────────────

def _install_tornado() -> None:
    import tornado.web
    from streamlit.web.server import server as st_server

    class PublicPageHandler(tornado.web.RequestHandler):
        async def get(self):
            # Supabase reads go over blocking urllib; off the IOLoop they go.
            resolved = await asyncio.to_thread(
                _resolve, self.request.path, self.request.query
            )
            if resolved is None:  # router matched but _resolve did not
                raise tornado.web.HTTPError(404)

            content_type, body, cache_control = resolved
            self.set_header("Content-Type", content_type)
            self.set_header("Cache-Control", cache_control)
            self.write(body)

        async def head(self):
            await self.get()

        def check_xsrf_cookie(self):
            # Public pages, no cookie to check.
            pass

    original_create_app = st_server.Server._create_app

    def _create_app(self):
        app = original_create_app(self)
        router = app.wildcard_router
        # events.json first: /board/?.* would otherwise swallow it.
        rules = [
            (r"/board/events\.json/?", PublicPageHandler),
            (r"/board/?", PublicPageHandler),
            (r"/rates/?", PublicPageHandler),
            (r"/mdot/?", PublicPageHandler),
            (r"/hbarena-mockup/?", PublicPageHandler),
        ]
        router.add_rules(rules)
        # add_rules appends; Streamlit's catch-all is already in the list, so
        # the new rules only win if they move to the front (in order).
        added = [router.rules.pop() for _ in rules][::-1]
        router.rules[0:0] = added
        return app

    st_server.Server._create_app = _create_app


# ── Starlette / uvicorn ──────────────────────────────────────────────────────

def _wrap_asgi(app):
    if not callable(app):  # uvicorn also accepts "module:attr" strings
        return app

    async def public_pages_asgi(scope, receive, send):
        if scope.get("type") == "http" and scope.get("method") in ("GET", "HEAD"):
            try:
                resolved = await asyncio.to_thread(
                    _resolve,
                    scope.get("path", ""),
                    scope.get("query_string", b"").decode("latin-1"),
                )
            except Exception as exc:
                # This wrapper sits in front of the whole app; anything that
                # goes wrong here hands the request back to Streamlit rather
                # than 500-ing a request that was never ours.
                logging.warning("public pages: %s", exc)
                resolved = None

            if resolved is not None:
                content_type, body, cache_control = resolved
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", content_type.encode()),
                        (b"content-length", str(len(body)).encode()),
                        (b"cache-control", cache_control.encode()),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"" if scope["method"] == "HEAD" else body,
                })
                return

        await app(scope, receive, send)

    return public_pages_asgi


def _install_asgi() -> None:
    import uvicorn

    original_init = uvicorn.Config.__init__

    def __init__(self, app, *args, **kwargs):
        original_init(self, _wrap_asgi(app), *args, **kwargs)

    uvicorn.Config.__init__ = __init__


# ── Entry point ──────────────────────────────────────────────────────────────

def install() -> None:
    """Register the public routes on whichever server Streamlit is about to boot."""
    missing = [f.name for f in HTML_PAGES.values() if not f.exists()]
    if missing:
        logging.warning("public pages: %s missing from static/", ", ".join(missing))
        if len(missing) == len(HTML_PAGES):
            return

    for stack, patch in (("Tornado", _install_tornado), ("ASGI", _install_asgi)):
        try:
            patch()
            logging.info("public pages: %s installed on the %s server",
                         ", ".join(HTML_PAGES), stack)
        except ImportError:
            logging.info("public pages: %s server not present, skipping", stack)
        except Exception as exc:
            logging.warning(
                "public pages: could not install routes on the %s server (%s) - "
                "pages still served at /app/static/<name>.html", stack, exc,
            )
