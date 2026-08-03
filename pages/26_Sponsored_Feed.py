# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sponsored Feed — Streamlit page for the MCTV Team Member portal.

Builds the URL for the sponsored live speed-test feed: an ISP or fiber
company buys a screen zone, and the screen runs

    sponsor intro (5-10s) -> live speed test -> sponsor outro (5-10s)

on a loop, measuring the venue's actual internet connection. Every
sponsor setting rides in the query string, so selling a second sponsor is
a second URL off this page - no deploy, no new file.

What the rep does here: fill in the sponsor, watch the preview, copy the
URL, hand it to n-compass as a URL/web zone.

Drop into: mctv-bot/pages/26_Sponsored_Feed.py
"""

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.config_service import get_market_names, load_config
from services.speedtest_feed import (
    FEED_PATH,
    FeedConfig,
    base_url,
    feed_url,
    plays_per_hour,
)

st.set_page_config(
    page_title="Sponsored Feed - MCTV Bot",
    page_icon="\U0001F4F6",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

markets = get_market_names(load_config(), active_only=False) or [
    "Oxford", "Starkville", "Tupelo", "Columbus", "West Point"]

st.markdown("## \U0001F4F6 Sponsored Live Speed Test Feed")
st.caption(
    "An internet or fiber company sponsors the feed; the screen runs a "
    "**real speed test on the venue's own connection** between their intro "
    "and outro. Fill this in, preview it, then paste the URL into the "
    "player as a URL/web zone."
)

# ── the form ───────────────────────────────────────────────────────────────

with st.form("feed_builder"):
    st.markdown("#### Sponsor")
    c1, c2 = st.columns(2)
    sponsor = c1.text_input("Sponsor name", "Tombigbee Fiber",
                            help="Shown big on the intro and outro.")
    tagline = c2.text_input("Tagline",
                            "Gig-speed fiber, built and run right here in North Mississippi")

    c1, c2, c3 = st.columns([2, 1, 1])
    logo = c1.text_input("Logo URL (https only)", "",
                         help="Must be https — an http image is blocked by the "
                              "player as mixed content and shows as a blank box. "
                              "Leave empty to use the name as a wordmark.")
    color = c2.color_picker("Accent colour", "#00a0df")
    color2 = c3.color_picker("Backdrop", "#071022")

    c1, c2, c3 = st.columns(3)
    phone = c1.text_input("Phone on the outro", "662-555-0100")
    web = c2.text_input("Website on the outro", "tombigbeefiber.com")
    cta = c3.text_input("Fallback call to action", "Ask about fiber at your address",
                        help="Used when there is no phone or website, and on the "
                             "card shown if a test cannot run.")

    st.markdown("#### Comparison bar (optional)")
    c1, c2 = st.columns([1, 2])
    compare_mbps = c1.number_input(
        "Sponsor's advertised speed (Mbps)", min_value=0, max_value=10000,
        value=1000, step=50,
        help="Draws a bar of the measured speed against this one. Set 0 to "
             "hide it. Only put a number here the sponsor actually sells.")
    compare_label = c2.text_input("Label for that bar", "Tombigbee 1 Gig Fiber")

    st.markdown("#### Timing")
    c1, c2, c3, c4 = st.columns(4)
    intro_seconds = c1.slider("Intro (s)", 5, 10, 8)
    test_seconds = c2.slider("Test window (s)", 10, 45, 20)
    outro_seconds = c3.slider("Outro (s)", 5, 10, 8)
    interval_minutes = c4.slider(
        "Minutes between real tests", 1, 120, 30,
        help="Between measurements the feed shows the last result with its "
             "age on screen. A real test moves real bytes over the host's "
             "Wi-Fi, so this is the knob that keeps the feed a good guest "
             "on their network.")

    st.markdown("#### Placement and measurement")
    c1, c2, c3 = st.columns(3)
    venue = c1.text_input("Venue name", "", help="Named on screen: \"the Wi-Fi at ___\".")
    market = c2.selectbox("Market", [""] + markets)
    endpoint_choice = c3.selectbox(
        "Test measures against",
        ["Cloudflare (recommended)", "MCTV's own server", "Sponsor-hosted (enter URL)"],
        help="Cloudflare costs MCTV nothing and measures the venue's real "
             "path to the internet. MCTV's server bills us for every byte — "
             "use it for demos. Sponsor-hosted is the best story of all: the "
             "test runs against the ISP's own network.")

    c1, c2, c3 = st.columns(3)
    endpoint_url = c1.text_input("Sponsor endpoint URL", "",
                                 help="Only used for the sponsor-hosted option. "
                                      "Must be https, CORS-open, and expose "
                                      "/__down?bytes= and /__up.")
    width = c2.number_input("Screen width (px)", 320, 7680, 1920, step=10)
    height = c3.number_input("Screen height (px)", 320, 7680, 1080, step=10)

    demo = st.checkbox(
        "Demo mode (simulated numbers, badged SIMULATED on screen)",
        value=False,
        help="For showing the concept on a laptop with no dependence on the "
             "network. Never put a demo-mode URL on a live screen.")

    submitted = st.form_submit_button("Build feed URL", type="primary")

# Build on every rerun so the page has something to show before the first
# submit; `submitted` only decides whether to celebrate.
endpoint = {
    "Cloudflare (recommended)": "cf",
    "MCTV's own server": "local",
    "Sponsor-hosted (enter URL)": endpoint_url or "cf",
}[endpoint_choice]

cfg = FeedConfig(
    sponsor=sponsor, tagline=tagline, logo=logo, color=color, color2=color2,
    phone=phone, web=web, cta=cta,
    compare_mbps=int(compare_mbps), compare_label=compare_label,
    intro_seconds=intro_seconds, outro_seconds=outro_seconds,
    test_seconds=test_seconds, interval_seconds=interval_minutes * 60,
    endpoint=endpoint, venue=venue, market=market,
    width=int(width), height=int(height), demo=demo,
)

if endpoint_choice == "Sponsor-hosted (enter URL)" and cfg.endpoint == "cf":
    st.warning(
        "That sponsor endpoint was not a usable https URL, so the feed will "
        "fall back to Cloudflare."
    )
if logo and not cfg.logo:
    st.warning(
        "That logo URL was dropped — it has to be https (or a data: image). "
        "The feed will show the sponsor name as a wordmark instead."
    )

url = feed_url(cfg)

# ── what they get ──────────────────────────────────────────────────────────

st.divider()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Loop length", f"{cfg.cycle_seconds}s",
          help="Intro + test window + outro.")
k2.metric("Sponsor frames / hour", f"{plays_per_hour(cfg) * 2:,.0f}",
          help="Two branded frames per cycle (intro and outro), plus the "
               "corner mark that never leaves the screen.")
k3.metric("Real tests / hour", f"{3600 / cfg.interval_seconds:,.1f}")
k4.metric("Venue data / screen / month", f"{cfg.monthly_venue_gb:,.1f} GB",
          help="Rough worst case at these settings: 12 broadcast hours a "
               "day, on a connection fast enough to spend the whole byte "
               "budget every test. Raise the interval to lower it.")

if cfg.endpoint == "local" and cfg.monthly_venue_gb > 5:
    st.warning(
        f"**{cfg.monthly_venue_gb:,.1f} GB per screen per month would come "
        "out of MCTV's Render bandwidth**, and it multiplies by every screen "
        "running this feed. Keep 'MCTV's own server' for demos and single "
        "screens; use Cloudflare or a sponsor-hosted endpoint for a rollout."
    )

st.markdown("#### The URL for the player")
st.code(url, language="text")
st.link_button("Open the feed in a new tab", url)

st.markdown("#### Preview")
st.caption(
    "Live preview, running the real thing. The first cycle starts with the "
    "intro, so give it a few seconds."
)
preview_ratio = cfg.height / cfg.width
preview_height = int(1100 * preview_ratio) + 20
components.html(
    f'<iframe src="{FEED_PATH}?{url.split("?", 1)[1] if "?" in url else ""}" '
    f'style="width:100%;height:{preview_height}px;border:0;border-radius:10px" '
    'title="Sponsored feed preview"></iframe>',
    height=preview_height + 10,
)
st.caption(
    f"If the preview stays blank, the app is running without the public "
    f"routes (`streamlit run app.py` instead of `python run_server.py`). "
    f"The page is still reachable at `/app/static/feed_speedtest.html`, and "
    f"the deployed copy at {base_url()} always has them."
)

# ── handoff ────────────────────────────────────────────────────────────────

with st.expander("How to put this on screens", expanded=False):
    st.markdown(
        f"""
**In the player (n-compass):** add the URL above as a **URL / web zone**,
not as a media file. The page loops on its own forever — there is nothing
to schedule beyond how long the zone holds the screen.

**Zone size:** the feed is built for **{cfg.width}×{cfg.height}**. It
scales itself to whatever box the player gives it and letterboxes rather
than stretching, so a mismatch is ugly but never broken. For portrait
screens, set the width and height above to match and rebuild the URL.

**One URL per venue.** Put the venue name in, so the screen can say
*"the Wi-Fi at {cfg.venue or 'Rafters'}"* instead of something vague, and
so the reconciliation in Loop Inventory can tell two sponsor feeds apart.

**What the screen will say about the numbers:**

- while a test is running — *Testing now · Live*
- between tests — *Last measured 12 minutes ago*, with the age on the
  result card
- when it cannot reach the test server — the sponsor card and
  *"Live speed test unavailable right now"*. It never invents a number.

**Before you sell it:** run the feed on the actual venue's connection for
a day. A venue on tired DSL will show a small number next to the
sponsor's gig-fiber bar — which is either the best ad the sponsor ever
bought or one they would rather not run. That is a conversation to have
with them first, not a surprise on screen.
"""
    )

if submitted:
    st.success("URL built. Copy it from the box above.")
