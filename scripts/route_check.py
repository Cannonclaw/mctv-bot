# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Check that the public pages still route on the installed Streamlit.

/rates, /board and /mdot are not Streamlit pages. server_routes.install()
reaches into the private innards of whichever web server Streamlit is about to
boot and inserts them ahead of its catch-all. requirements.txt pins only
`streamlit>=1.40.0`, so any rebuild can resolve a newer Streamlit, and a
Streamlit that reorganises its server internals silently costs us those routes:
/rates would answer with the app shell (a login screen) instead of the rate
calculator, and the first anyone would know is a client saying the QR code
does not work.

Run this after any Streamlit bump, and after any change to server_routes.py:

    python scripts/route_check.py

Exits non-zero on the first thing that stops routing. It drives a real ASGI
request through the installed wrapper rather than booting a server, so it is
fast and needs no port.

Note on stacks: Streamlit is migrating Tornado -> Starlette/uvicorn, and by
1.61 Tornado is not installed at all. install() patches whichever is present
and skips the other, so "Tornado server not present, skipping" in the output is
normal on a modern Streamlit, not a failure. What matters is that one of the
two patches installed and the assertions below pass.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="  install: %(message)s")

import server_routes  # noqa: E402

APP_SHELL = b"<STREAMLIT APP SHELL>"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{' — ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


async def streamlit_stub(scope, receive, send):
    """Stands in for Streamlit's own app — the catch-all that must not win."""
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"text/html")]})
    await send({"type": "http.response.body", "body": APP_SHELL})


async def fetch(app, path: str, method: str = "GET") -> tuple[int | None, dict, bytes]:
    sent: list[dict] = []

    async def send(msg):
        sent.append(msg)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    await app({"type": "http", "method": method, "path": path,
               "query_string": b"", "headers": []}, receive, send)

    start = next((m for m in sent if m["type"] == "http.response.start"), {})
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return start.get("status"), dict(start.get("headers", [])), body


async def main() -> None:
    import streamlit
    import uvicorn

    print(f"streamlit {streamlit.__version__} · uvicorn {uvicorn.__version__}")
    try:
        import tornado
        print(f"tornado {tornado.version}")
    except ImportError:
        print("tornado not installed (Starlette-only Streamlit)")

    server_routes.install()

    # Constructing a Config is what streamlit's starlette_server does; the
    # patched __init__ is what swaps in our wrapper.
    cfg = uvicorn.Config(streamlit_stub, host="127.0.0.1", port=8501)
    check("uvicorn.Config.app is wrapped", cfg.app is not streamlit_stub)
    app = cfg.app

    status, headers, body = await fetch(app, "/rates")
    check("/rates serves the rate calculator, not the app shell",
          status == 200 and b"MCTV RATE CALCULATOR" in body and APP_SHELL not in body,
          f"status={status} bytes={len(body)}")
    check("/rates content-type is html",
          headers.get(b"content-type", b"").startswith(b"text/html"))
    check("/rates carries the agreement modal",
          b"ag-overlay" in body and b"syncAgreementViewport" in body)

    status, _, body = await fetch(app, "/rates/")
    check("/rates/ (trailing slash) routes too", status == 200 and APP_SHELL not in body)

    for path, marker in (("/board", b"<!doctype html"), ("/mdot", b"<!DOCTYPE html")):
        status, _, body = await fetch(app, path)
        check(f"{path} routes", status == 200 and APP_SHELL not in body, f"bytes={len(body)}")

    for path in ("/", "/Proposals"):
        _, _, body = await fetch(app, path)
        check(f"{path} falls through to Streamlit", APP_SHELL in body)

    _, _, body = await fetch(app, "/rates", method="POST")
    check("POST /rates falls through (only GET/HEAD are ours)", APP_SHELL in body)


if __name__ == "__main__":
    asyncio.run(main())
    if failures:
        print(f"\n{len(failures)} check(s) FAILED: {', '.join(failures)}")
        print("The public pages are not routing. They stay reachable at "
              "/app/static/<name>.html; fix the patches in server_routes.py.")
        sys.exit(1)
    print("\nall route checks passed")
