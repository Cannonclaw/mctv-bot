# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Serve standalone public HTML pages at their own short URLs.

Currently:

  * GET /rates - the self-serve rate calculator
  * GET /mdot  - the MDOT road-conditions sponsorship mockup, so it can be
                 texted as a plain mctvofms link instead of a file

Streamlit exposes no routing API, so this reaches into the web server it
boots and inserts the extra routes ahead of Streamlit's catch-all (which
otherwise answers them with the app shell). Two stacks are handled
because Streamlit is mid-migration from Tornado to Starlette/uvicorn and
which one runs depends on the version pip resolves at image build time:

  * Tornado   - a RequestHandler at the head of the wildcard router
  * Starlette - a wrapper around the ASGI app handed to uvicorn

Both patches follow the same rule as the ones in app.py: they reach into
private innards, so each is guarded on its own and none of them are
allowed to stop the app from booting. Pages under static/ stay reachable
at /app/static/<name>.html regardless (Streamlit's own static serving, see
the SAFE_APP_STATIC_FILE_EXTENSIONS patch in app.py), so a patch that
stops matching a future Streamlit degrades to a longer URL, not a missing
page.

install() has to run BEFORE the server starts - i.e. from run_server.py.
Patches applied from app.py run too late, the routes are already built.
"""

import logging
from pathlib import Path

_ROOT = Path(__file__).parent

# path -> file on disk. Trailing slash is stripped before comparing, so
# /rates and /rates/ both hit. The mockup is served from the handoff
# package rather than copied into static/, so there is one source of truth
# to edit before a pitch.
PAGES: dict[str, Path] = {
    "/rates": _ROOT / "static" / "rates.html",
    "/mdot": _ROOT / "handoffs" / "mdot-traffic-partnership" / "mockup.html",
}
CACHE_CONTROL = "public, max-age=300"

_page_cache: dict[str, bytes] = {}


def _page_bytes(path: str) -> bytes:
    """Read a page off disk once and hold it in memory."""
    if path not in _page_cache:
        _page_cache[path] = PAGES[path].read_bytes()
    return _page_cache[path]


def _install_tornado() -> None:
    import tornado.web
    from streamlit.web.server import server as st_server

    class PageHandler(tornado.web.RequestHandler):
        def initialize(self, page_path):
            self.page_path = page_path

        def get(self):
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.set_header("Cache-Control", CACHE_CONTROL)
            self.write(_page_bytes(self.page_path))

        def check_xsrf_cookie(self):
            # Public page, no cookie to check.
            pass

    original_create_app = st_server.Server._create_app

    def _create_app(self):
        app = original_create_app(self)
        router = app.wildcard_router
        for path in _installable():
            router.add_rules([(rf"{path}/?", PageHandler, {"page_path": path})])
            # add_rules appends; Streamlit's catch-all is already in the
            # list, so the new rule only wins if we move it to the front.
            router.rules.insert(0, router.rules.pop())
        return app

    st_server.Server._create_app = _create_app


def _wrap_asgi(app):
    if not callable(app):  # uvicorn also accepts "module:attr" strings
        return app

    async def pages_asgi(scope, receive, send):
        path = scope.get("path", "").rstrip("/") or "/"
        if (
            scope.get("type") == "http"
            and path in PAGES
            and scope.get("method") in ("GET", "HEAD")
        ):
            try:
                body = _page_bytes(path)
            except OSError as exc:
                logging.warning("public pages: %s unreadable (%s)", PAGES[path], exc)
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

    return pages_asgi


def _install_asgi() -> None:
    import uvicorn

    original_init = uvicorn.Config.__init__

    def __init__(self, app, *args, **kwargs):
        original_init(self, _wrap_asgi(app), *args, **kwargs)

    uvicorn.Config.__init__ = __init__


def _installable() -> list[str]:
    """Paths whose backing file is actually on disk."""
    return [path for path, file in PAGES.items() if file.exists()]


def install() -> None:
    """Register the public pages on whichever server Streamlit is about to boot."""
    for path, file in PAGES.items():
        if not file.exists():
            logging.warning("public pages: %s missing, %s not installed", file, path)

    paths = _installable()
    if not paths:
        return

    for stack, patch in (("Tornado", _install_tornado), ("ASGI", _install_asgi)):
        try:
            patch()
            logging.info(
                "public pages: %s installed on the %s server", ", ".join(paths), stack
            )
        except ImportError:
            logging.info("public pages: %s server not present, skipping", stack)
        except Exception as exc:
            logging.warning(
                "public pages: could not install %s on the %s server (%s) - "
                "pages under static/ still served at /app/static/<name>.html",
                ", ".join(paths), stack, exc,
            )
