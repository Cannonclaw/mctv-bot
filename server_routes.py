# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Serve the public rate calculator as raw HTML at GET /rates.

Streamlit exposes no routing API, so this reaches into the web server it
boots and inserts one extra route ahead of Streamlit's catch-all (which
otherwise answers /rates with the app shell). Two stacks are handled
because Streamlit is mid-migration from Tornado to Starlette/uvicorn and
which one runs depends on the version pip resolves at image build time:

  * Tornado   - a RequestHandler at the head of the wildcard router
  * Starlette - a wrapper around the ASGI app handed to uvicorn

Both patches follow the same rule as the ones in app.py: they reach into
private innards, so each is guarded on its own and none of them are
allowed to stop the app from booting. The page stays reachable at
/app/static/rates.html regardless (Streamlit's own static serving, see the
SAFE_APP_STATIC_FILE_EXTENSIONS patch in app.py), so a patch that stops
matching a future Streamlit degrades to a longer URL, not a missing page.

install() has to run BEFORE the server starts - i.e. from run_server.py.
Patches applied from app.py run too late, the routes are already built.
"""

import logging
from pathlib import Path

# Trailing slash is stripped before comparing, so /rates and /rates/ both hit.
RATES_PATH = "/rates"
RATES_FILE = Path(__file__).parent / "static" / "rates.html"
CACHE_CONTROL = "public, max-age=300"

_page_cache: bytes | None = None


def _page_bytes() -> bytes:
    """Read the calculator off disk once and hold it in memory."""
    global _page_cache
    if _page_cache is None:
        _page_cache = RATES_FILE.read_bytes()
    return _page_cache


def _install_tornado() -> None:
    import tornado.web
    from streamlit.web.server import server as st_server

    class RatesHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.set_header("Cache-Control", CACHE_CONTROL)
            self.write(_page_bytes())

        def check_xsrf_cookie(self):
            # Public page, no cookie to check.
            pass

    original_create_app = st_server.Server._create_app

    def _create_app(self):
        app = original_create_app(self)
        router = app.wildcard_router
        router.add_rules([(r"/rates/?", RatesHandler)])
        # add_rules appends; Streamlit's catch-all is already in the list,
        # so the new rule only wins if we move it to the front.
        router.rules.insert(0, router.rules.pop())
        return app

    st_server.Server._create_app = _create_app


def _wrap_asgi(app):
    if not callable(app):  # uvicorn also accepts "module:attr" strings
        return app

    async def rates_asgi(scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("path", "").rstrip("/") == RATES_PATH
            and scope.get("method") in ("GET", "HEAD")
        ):
            try:
                body = _page_bytes()
            except OSError as exc:
                logging.warning("rate calculator: %s unreadable (%s)", RATES_FILE, exc)
            else:
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"text/html; charset=utf-8"),
                        (b"content-length", str(len(body)).encode()),
                        (b"cache-control", CACHE_CONTROL.encode()),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"" if scope["method"] == "HEAD" else body,
                })
                return

        await app(scope, receive, send)

    return rates_asgi


def _install_asgi() -> None:
    import uvicorn

    original_init = uvicorn.Config.__init__

    def __init__(self, app, *args, **kwargs):
        original_init(self, _wrap_asgi(app), *args, **kwargs)

    uvicorn.Config.__init__ = __init__


def install() -> None:
    """Register /rates on whichever server Streamlit is about to boot."""
    if not RATES_FILE.exists():
        logging.warning("rate calculator: %s missing, /rates not installed", RATES_FILE)
        return

    for stack, patch in (("Tornado", _install_tornado), ("ASGI", _install_asgi)):
        try:
            patch()
            logging.info("rate calculator: /rates installed on the %s server", stack)
        except ImportError:
            logging.info("rate calculator: %s server not present, skipping", stack)
        except Exception as exc:
            logging.warning(
                "rate calculator: could not install /rates on the %s server (%s) - "
                "page still served at /app/static/rates.html", stack, exc,
            )
