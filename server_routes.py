# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Serve the public non-Streamlit routes as raw HTTP.

Two things live out here, both of them pages that must answer a plain GET
with no Streamlit shell around them:

  GET  /rates ................. the public rate calculator
  GET  /feed/speedtest ........ the sponsored live speed-test screen feed
  GET  /feed/speedtest/ping ... 204, for latency probes
  GET  /feed/speedtest/down ... N bytes of incompressible payload
  POST /feed/speedtest/up ..... swallows an upload, answers 204

Streamlit exposes no routing API, so this reaches into the web server it
boots and inserts these routes ahead of Streamlit's catch-all (which
otherwise answers /rates with the app shell). Two stacks are handled
because Streamlit is mid-migration from Tornado to Starlette/uvicorn and
which one runs depends on the version pip resolves at image build time:

  * Tornado   - RequestHandlers at the head of the wildcard router
  * Starlette - a wrapper around the ASGI app handed to uvicorn

Both patches follow the same rule as the ones in app.py: they reach into
private innards, so each is guarded on its own and none of them are
allowed to stop the app from booting. The pages stay reachable at
/app/static/<file>.html regardless (Streamlit's own static serving, see
the SAFE_APP_STATIC_FILE_EXTENSIONS patch in app.py), so a patch that
stops matching a future Streamlit degrades to a longer URL, not a missing
page. The speed-test endpoints have no such fallback - a feed pointed at
`endpoint=local` needs these routes; the default `endpoint=cf` does not
touch this server at all.

A NOTE ON THE TEST ENDPOINTS: they hand out bandwidth to anyone who asks,
so every response is capped (see MAX_DOWN_REQUEST_BYTES in
services/speedtest_feed.py) and nothing is ever buffered whole - the
download streams a reused random block and the upload is discarded as it
arrives.

install() has to run BEFORE the server starts - i.e. from run_server.py.
Patches applied from app.py run too late, the routes are already built.
"""

import logging
from pathlib import Path
from urllib.parse import parse_qs

from services.speedtest_feed import (
    BLOCK_SIZE,
    MAX_UP_REQUEST_BYTES,
    clamp_down_bytes,
    iter_payload,
)

STATIC_DIR = Path(__file__).parent / "static"

# Trailing slashes are stripped before comparing, so /rates and /rates/
# both hit. Keys must be the stripped form.
PAGES: dict[str, Path] = {
    "/rates": STATIC_DIR / "rates.html",
    "/feed/speedtest": STATIC_DIR / "feed_speedtest.html",
}

PING_PATH = "/feed/speedtest/ping"
DOWN_PATH = "/feed/speedtest/down"
UP_PATH = "/feed/speedtest/up"

CACHE_CONTROL = "public, max-age=300"
NO_STORE = "no-store, no-cache, must-revalidate"

# The feed page may be served from another origin (a sponsor's site, a
# preview in the Streamlit app), so the measurement endpoints are open.
# They expose no data - one hands out random bytes, the other throws
# bytes away.
CORS_HEADERS = [
    (b"access-control-allow-origin", b"*"),
    (b"access-control-allow-methods", b"GET, POST, HEAD, OPTIONS"),
    (b"access-control-allow-headers", b"content-type"),
    (b"access-control-max-age", b"86400"),
    (b"timing-allow-origin", b"*"),
]

_page_cache: dict[str, bytes] = {}


def _page_bytes(path: str) -> bytes:
    """Read a static page off disk once and hold it in memory."""
    if path not in _page_cache:
        _page_cache[path] = PAGES[path].read_bytes()
    return _page_cache[path]


def _requested_bytes(query: str) -> int:
    """`bytes=` from a query string, clamped to what we are willing to send."""
    values = parse_qs(query or "").get("bytes") or ["0"]
    return clamp_down_bytes(values[0])


# ---------------------------------------------------------------------------
# Tornado
# ---------------------------------------------------------------------------

def tornado_rules() -> list:
    """The route rules to splice into Streamlit's router.

    Built separately from the patch that installs them so the handlers can
    be exercised against a plain tornado Application in
    scripts/speedtest_feed_test.py - Streamlit is a heavy thing to boot
    just to find out the download endpoint forgot to flush.
    """
    import tornado.web

    class _Public(tornado.web.RequestHandler):
        def check_xsrf_cookie(self):
            # Public endpoints, no cookie to check.
            pass

        def set_default_headers(self):
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
            self.set_header("Access-Control-Allow-Headers", "content-type")
            self.set_header("Timing-Allow-Origin", "*")

        def options(self, *_args):
            self.set_status(204)
            self.finish()

    class PageHandler(_Public):
        def initialize(self, route: str):
            self.route = route

        def get(self):
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.set_header("Cache-Control", CACHE_CONTROL)
            self.write(_page_bytes(self.route))

    class PingHandler(_Public):
        def get(self):
            self.set_header("Cache-Control", NO_STORE)
            self.set_status(204)

    class DownHandler(_Public):
        async def get(self):
            total = _requested_bytes(self.request.query)
            self.set_header("Content-Type", "application/octet-stream")
            self.set_header("Content-Length", str(total))
            self.set_header("Cache-Control", NO_STORE)
            for chunk in iter_payload(total):
                self.write(chunk)
                await self.flush()

    @tornado.web.stream_request_body
    class UpHandler(_Public):
        """Counts the upload and throws it away without ever holding it."""

        def initialize(self):
            self.received = 0

        def data_received(self, chunk):
            self.received += len(chunk)

        def post(self):
            self.set_header("Cache-Control", NO_STORE)
            self.set_status(204)

    rules: list = [
        (rf"{PING_PATH}/?", PingHandler),
        (rf"{DOWN_PATH}/?", DownHandler),
        (rf"{UP_PATH}/?", UpHandler),
    ]
    rules += [
        (rf"{route}/?", PageHandler, {"route": route})
        for route in PAGES
        if PAGES[route].exists()
    ]
    return rules


def _install_tornado() -> None:
    from streamlit.web.server import server as st_server

    rules = tornado_rules()
    original_create_app = st_server.Server._create_app

    def _create_app(self):
        app = original_create_app(self)
        router = app.wildcard_router
        router.add_rules(rules)
        # add_rules appends; Streamlit's catch-all is already in the list,
        # so the new rules only win if we move them to the front. They are
        # popped off the tail in reverse so their relative order survives.
        for _ in rules:
            router.rules.insert(0, router.rules.pop())
        return app

    st_server.Server._create_app = _create_app


# ---------------------------------------------------------------------------
# ASGI (Starlette / uvicorn)
# ---------------------------------------------------------------------------

async def _send_head(send, status: int, headers: list[tuple[bytes, bytes]]) -> None:
    await send({"type": "http.response.start", "status": status,
                "headers": headers + CORS_HEADERS})


async def _send_empty(send, status: int, cache: str = NO_STORE) -> None:
    await _send_head(send, status, [(b"cache-control", cache.encode())])
    await send({"type": "http.response.body", "body": b""})


async def _drain(receive) -> int:
    """Read a request body to the end without keeping it.

    Stops early past the cap so a hostile POST cannot tie the worker up
    forever; the connection is closed by the 413 that follows.
    """
    total = 0
    while True:
        message = await receive()
        if message["type"] != "http.request":
            return total
        total += len(message.get("body") or b"")
        if not message.get("more_body"):
            return total
        if total > MAX_UP_REQUEST_BYTES:
            return total


def _wrap_asgi(app):
    if not callable(app):  # uvicorn also accepts "module:attr" strings
        return app

    async def routed_asgi(scope, receive, send):
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return

        path = scope.get("path", "").rstrip("/") or "/"
        method = scope.get("method", "GET")

        if method == "OPTIONS" and (path in PAGES or path in (PING_PATH, DOWN_PATH, UP_PATH)):
            await _send_empty(send, 204)
            return

        if path == PING_PATH and method in ("GET", "HEAD"):
            await _send_empty(send, 204)
            return

        if path == DOWN_PATH and method in ("GET", "HEAD"):
            total = _requested_bytes(scope.get("query_string", b"").decode("latin-1"))
            await _send_head(send, 200, [
                (b"content-type", b"application/octet-stream"),
                (b"content-length", str(total).encode()),
                (b"cache-control", NO_STORE.encode()),
            ])
            if method == "HEAD" or total == 0:
                await send({"type": "http.response.body", "body": b""})
                return
            sent = 0
            for chunk in iter_payload(total):
                sent += len(chunk)
                await send({"type": "http.response.body", "body": chunk,
                            "more_body": sent < total})
            return

        if path == UP_PATH and method == "POST":
            received = await _drain(receive)
            await _send_empty(send, 413 if received > MAX_UP_REQUEST_BYTES else 204)
            return

        if path in PAGES and method in ("GET", "HEAD"):
            try:
                body = _page_bytes(path)
            except OSError as exc:
                logging.warning("public routes: %s unreadable (%s)", PAGES[path], exc)
            else:
                await _send_head(send, 200, [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", CACHE_CONTROL.encode()),
                ])
                await send({"type": "http.response.body",
                            "body": b"" if method == "HEAD" else body})
                return

        await app(scope, receive, send)

    return routed_asgi


def _install_asgi() -> None:
    import uvicorn

    original_init = uvicorn.Config.__init__

    def __init__(self, app, *args, **kwargs):
        original_init(self, _wrap_asgi(app), *args, **kwargs)

    uvicorn.Config.__init__ = __init__


# ---------------------------------------------------------------------------

def install() -> None:
    """Register the public routes on whichever server Streamlit is about to boot."""
    missing = [route for route, file in PAGES.items() if not file.exists()]
    for route in missing:
        logging.warning("public routes: %s missing, %s not installed",
                        PAGES[route], route)
    if len(missing) == len(PAGES):
        logging.warning("public routes: no pages on disk, only the "
                        "speed-test endpoints will be installed")

    # Touch the payload block at boot so the first screen to run a local
    # test does not pay for 256 KiB of entropy mid-measurement.
    from services.speedtest_feed import payload_block
    payload_block()
    logging.info("public routes: %d KiB payload block ready", BLOCK_SIZE // 1024)

    for stack, patch in (("Tornado", _install_tornado), ("ASGI", _install_asgi)):
        try:
            patch()
            logging.info("public routes: installed on the %s server", stack)
        except ImportError:
            logging.info("public routes: %s server not present, skipping", stack)
        except Exception as exc:
            logging.warning(
                "public routes: could not install on the %s server (%s) - "
                "pages still served at /app/static/<file>.html", stack, exc,
            )
