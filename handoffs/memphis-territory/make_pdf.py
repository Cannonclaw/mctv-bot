#!/usr/bin/env python3
"""Print the send version of the areas map to PDF.

Renders territory-ask-send.html (built with `build_territory_ask.py --send`),
which is exactly two pages: the markets, then the map.

Chromium is pre-installed in this environment; the pip playwright package
expects a newer build, so the executable path is passed explicitly rather
than running `playwright install`.
"""
from playwright.sync_api import sync_playwright

SRC = "file:///home/user/mctv-bot/handoffs/memphis-territory/territory-ask-send.html"
OUT = "/home/user/mctv-bot/handoffs/memphis-territory/MCTV-Memphis-Areas-of-Interest.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    pg = b.new_page(color_scheme="light")
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(SRC, wait_until="networkidle")
    pg.emulate_media(media="print", color_scheme="light")
    pg.wait_for_timeout(400)
    pg.pdf(path=OUT, format="Letter", print_background=True,
           margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
           prefer_css_page_size=True)
    if errs:
        raise SystemExit(f"page errors: {errs}")
    b.close()
print(f"wrote {OUT}")
