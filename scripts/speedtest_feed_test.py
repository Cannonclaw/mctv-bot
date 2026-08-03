# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Self-check for the sponsored live speed-test feed.

Covers the parts that can break silently in production: the config
clamps, the URL round-trip, the payload generator, and the ASGI routes
(page, ping, capped download, discarded upload). No network, no
Supabase, no Streamlit - run it anywhere:

    python scripts/speedtest_feed_test.py
"""

import asyncio
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from server_routes import (  # noqa: E402
    DOWN_PATH,
    PING_PATH,
    UP_PATH,
    _wrap_asgi,
    tornado_rules,
)
from services.speedtest_feed import (  # noqa: E402
    BLOCK_SIZE,
    MAX_DOWN_REQUEST_BYTES,
    FeedConfig,
    clamp_down_bytes,
    feed_url,
    iter_payload,
    parse_feed_config,
    payload_block,
    plays_per_hour,
)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name:52} {detail}")
    if not ok:
        FAILURES.append(name)


# ── config ─────────────────────────────────────────────────────────────────

def test_config():
    d = FeedConfig()
    check("defaults are a valid 5-10s intro/outro",
          5 <= d.intro_seconds <= 10 and 5 <= d.outro_seconds <= 10,
          f"{d.intro_seconds}s intro / {d.outro_seconds}s outro")

    wild = FeedConfig(intro_seconds=99, outro_seconds=0, test_seconds=999,
                      interval_seconds=1, max_down_mb=9999, streams=50,
                      color="not-a-color", logo="http://insecure.example/l.png",
                      endpoint="ftp://nope")
    check("out-of-range timings clamp",
          wild.intro_seconds == 10 and wild.outro_seconds == 5
          and wild.test_seconds == 45 and wild.interval_seconds == 60,
          f"{wild.intro_seconds}/{wild.test_seconds}/{wild.outro_seconds}")
    check("bad colour falls back", wild.color == "#c5a55a", wild.color)
    check("http logo rejected (mixed content on the player)",
          wild.logo == "", repr(wild.logo))
    check("unknown endpoint scheme falls back to cf",
          wild.endpoint == "cf", wild.endpoint)

    https_logo = FeedConfig(logo="https://cdn.example/logo.png")
    check("https logo kept", https_logo.logo.startswith("https://"))

    custom = FeedConfig(endpoint="https://speed.sponsor.net/")
    check("sponsor endpoint kept without trailing slash",
          custom.endpoint == "https://speed.sponsor.net", custom.endpoint)

    cfg = FeedConfig(intro_seconds=6, test_seconds=20, outro_seconds=6)
    check("cycle length adds up", cfg.cycle_seconds == 32,
          f"{cfg.cycle_seconds}s -> {plays_per_hour(cfg)} plays/hr")
    check("venue bandwidth estimate is sane",
          0 < cfg.monthly_venue_gb < 200, f"{cfg.monthly_venue_gb} GB/screen/mo")


def test_url_round_trip():
    cfg = FeedConfig(
        sponsor="Tombigbee Fiber", tagline="Gig speed, local hands",
        color="#00A0DF", phone="662-555-0100", web="tombigbeefiber.com",
        compare_mbps=1000, compare_label="Tombigbee 1 Gig",
        intro_seconds=7, outro_seconds=9, test_seconds=22,
        venue="Rafters", market="Oxford", endpoint="local",
    )
    url = feed_url(cfg, base="https://mctv-bot.onrender.com")
    check("URL points at the feed route",
          url.startswith("https://mctv-bot.onrender.com/feed/speedtest?"),
          url[:78] + "...")
    check("defaults are omitted from the URL",
          "max_down_mb" not in url and "width" not in url)

    back = parse_feed_config(url)
    for field in ("sponsor", "tagline", "color", "phone", "web", "compare_mbps",
                  "compare_label", "intro_seconds", "outro_seconds",
                  "test_seconds", "venue", "market", "endpoint"):
        if getattr(back, field) != getattr(cfg, field):
            check(f"round-trip preserves {field}", False,
                  f"{getattr(cfg, field)!r} -> {getattr(back, field)!r}")
            return
    check("every field survives the URL round-trip", True,
          f"{back.sponsor} @ {back.venue}")

    check("unknown query keys are ignored",
          parse_feed_config("?sponsor=X&evil=1").sponsor == "X")


# ── payload ────────────────────────────────────────────────────────────────

def test_payload():
    block = payload_block()
    check("payload block is one reused 256 KiB buffer",
          len(block) == BLOCK_SIZE and payload_block() is block,
          f"{len(block)} bytes")

    # Random, not zeros: a proxy that gzips must not turn 8 MiB into 8 KiB.
    unique = len(set(block[:4096]))
    check("payload is incompressible-looking", unique > 200, f"{unique}/256 byte values")

    total = sum(len(c) for c in iter_payload(700_000))
    check("iter_payload yields exactly what was asked", total == 700_000, f"{total} bytes")
    check("no chunk exceeds the block size",
          all(len(c) <= BLOCK_SIZE for c in iter_payload(700_000)))

    check("download request is capped",
          clamp_down_bytes(10 ** 12) == MAX_DOWN_REQUEST_BYTES,
          f"{MAX_DOWN_REQUEST_BYTES // 1024 // 1024} MiB")
    check("garbage byte counts do not explode",
          clamp_down_bytes("nonsense") == BLOCK_SIZE and clamp_down_bytes(-5) == 0)


# ── ASGI routes ────────────────────────────────────────────────────────────

async def call(app, path, method="GET", query=b"", body=b""):
    """Drive the wrapped ASGI app and collect one response."""
    scope = {"type": "http", "path": path, "method": method, "query_string": query,
             "headers": []}
    sent = {"status": None, "headers": [], "body": b"", "chunks": 0}
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            sent["status"] = message["status"]
            sent["headers"] = {k.decode(): v.decode() for k, v in message["headers"]}
        else:
            sent["body"] += message.get("body") or b""
            sent["chunks"] += 1

    await app(scope, receive, send)
    return sent


async def test_asgi():
    fell_through = {"n": 0}

    async def inner(scope, receive, send):
        fell_through["n"] += 1
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"streamlit"})

    app = _wrap_asgi(inner)

    page = await call(app, "/feed/speedtest")
    check("GET /feed/speedtest serves the feed",
          page["status"] == 200 and b"<title>" in page["body"],
          f"{len(page['body'])} bytes, {page['headers'].get('content-type')}")
    check("trailing slash hits the same page",
          (await call(app, "/feed/speedtest/"))["status"] == 200)
    check("/rates still served", (await call(app, "/rates"))["status"] == 200)

    ping = await call(app, PING_PATH)
    check("ping answers 204 and no-store",
          ping["status"] == 204 and "no-store" in ping["headers"].get("cache-control", ""))
    check("test endpoints are CORS-open",
          ping["headers"].get("access-control-allow-origin") == "*")

    down = await call(app, DOWN_PATH, query=b"bytes=600000")
    check("download returns the requested size",
          down["status"] == 200 and len(down["body"]) == 600_000,
          f"{len(down['body'])} bytes in {down['chunks']} chunks")
    check("download is streamed, not buffered whole", down["chunks"] > 1,
          f"{down['chunks']} chunks")
    check("download honours Content-Length",
          down["headers"].get("content-length") == "600000")

    huge = await call(app, DOWN_PATH, query=b"bytes=999999999")
    check("oversized download request is capped",
          len(huge["body"]) == MAX_DOWN_REQUEST_BYTES,
          f"{len(huge['body']) // 1024 // 1024} MiB")

    head = await call(app, DOWN_PATH, method="HEAD", query=b"bytes=600000")
    check("HEAD sends no payload", head["body"] == b"")

    up = await call(app, UP_PATH, method="POST", body=b"x" * 200_000)
    check("upload is swallowed with a 204", up["status"] == 204)

    opts = await call(app, UP_PATH, method="OPTIONS")
    check("CORS preflight answered",
          opts["status"] == 204
          and "POST" in opts["headers"].get("access-control-allow-methods", ""))

    before = fell_through["n"]
    other = await call(app, "/some/streamlit/page")
    check("everything else falls through to Streamlit",
          other["body"] == b"streamlit" and fell_through["n"] == before + 1)


# ── Tornado routes ─────────────────────────────────────────────────────────
# Streamlit ships tornado, so in the deployed image this always runs. It is
# skipped only on a bare checkout without it.

async def test_tornado():
    import tornado.httpclient
    import tornado.web

    app = tornado.web.Application(tornado_rules())
    server = app.listen(0, address="127.0.0.1")
    port = list(server._sockets.values())[0].getsockname()[1]
    client = tornado.httpclient.AsyncHTTPClient()
    root = f"http://127.0.0.1:{port}"

    async def get(path, **kw):
        return await client.fetch(root + path, raise_error=False, **kw)

    page = await get("/feed/speedtest")
    check("tornado: feed page served",
          page.code == 200 and b"<title>" in page.body, f"{len(page.body)} bytes")
    check("tornado: /rates still served", (await get("/rates")).code == 200)
    check("tornado: trailing slash accepted", (await get("/feed/speedtest/")).code == 200)

    ping = await get(PING_PATH)
    check("tornado: ping is 204 + CORS",
          ping.code == 204 and ping.headers.get("Access-Control-Allow-Origin") == "*")

    down = await get(DOWN_PATH + "?bytes=900000")
    check("tornado: download returns the requested size",
          down.code == 200 and len(down.body) == 900_000, f"{len(down.body)} bytes")

    huge = await get(DOWN_PATH + "?bytes=99999999")
    check("tornado: oversized download capped",
          len(huge.body) == MAX_DOWN_REQUEST_BYTES,
          f"{len(huge.body) // 1024 // 1024} MiB")

    up = await get(UP_PATH, method="POST", body=b"z" * 300_000)
    check("tornado: upload swallowed with a 204", up.code == 204)

    opts = await get(UP_PATH, method="OPTIONS", allow_nonstandard_methods=True)
    check("tornado: CORS preflight answered", opts.code == 204)

    server.stop()


# ── the page itself ────────────────────────────────────────────────────────

def test_page_contract():
    html = (ROOT / "static" / "feed_speedtest.html").read_text(encoding="utf-8")

    # Every FeedConfig field must actually be read by the page, or the
    # builder would emit settings that silently do nothing on screen.
    from dataclasses import fields
    missing = [f.name for f in fields(FeedConfig) if f.name not in html]
    check("page reads every config key the builder writes", not missing, str(missing))

    check("page is self-contained (no external scripts or styles)",
          not re.search(r"<(script|link)[^>]+(src|href)=", html))
    check("sponsor copy never goes in via innerHTML",
          ".innerHTML" not in html)
    check("page states when a result is stale rather than faking it",
          "Last measured" in html and "ageText" in html)
    check("demo mode is badged on screen", "Simulated · Demo mode" in html)
    check("failed test says so instead of inventing a number",
          "Live speed test unavailable right now" in html)


def main() -> int:
    print("── config ─────────────────────────────────────────────────────")
    test_config()
    test_url_round_trip()
    print("── payload ────────────────────────────────────────────────────")
    test_payload()
    print("── asgi routes ────────────────────────────────────────────────")
    asyncio.run(test_asgi())
    print("── tornado routes ─────────────────────────────────────────────")
    try:
        import tornado  # noqa: F401
    except ImportError:
        print("[SKIP] tornado not installed (it ships with streamlit)")
    else:
        asyncio.run(test_tornado())
    print("── page ───────────────────────────────────────────────────────")
    test_page_contract()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
