# Sponsored Live Speed Test Feed

A screen feed an internet or fiber company sponsors. One cycle:

```
sponsor intro (5-10s)  ->  live speed test  ->  sponsor outro (5-10s)
```

and then it loops, forever, on its own. The test is real: the screen
measures the internet connection it is actually sitting on, in the venue,
and puts the numbers up.

Build the URL on the **Sponsored Feed** page (`pages/26_Sponsored_Feed.py`),
paste it into the player as a URL/web zone, done. Every sponsor setting
rides in the query string, so a second sponsor is a second URL — no
deploy, no new file.

## The pieces

| File | What it is |
| --- | --- |
| `static/feed_speedtest.html` | The feed. Self-contained: no CDN, no external script, no fonts to fetch. |
| `services/speedtest_feed.py` | `FeedConfig` (validation + clamps), URL build/parse, payload generator. |
| `server_routes.py` | Serves `/feed/speedtest` and the `local` test endpoints on both server stacks. |
| `pages/26_Sponsored_Feed.py` | The rep-facing builder: fill in the sponsor, preview, copy the URL. |
| `scripts/speedtest_feed_test.py` | Self-check. No network, no Supabase, no Streamlit. |

## Where the test measures to

This is the decision that matters, and it is the `endpoint` setting.

**`cf` (default)** — Cloudflare's public speed endpoints. Costs MCTV
nothing and measures the venue's real path out to the internet, which is
the number a fiber sponsor actually wants on screen.

**`local`** — our own `/feed/speedtest/*` routes. Every byte is Render
bandwidth on our bill, multiplied by every screen running the feed, and
it measures the path to our dyno rather than to the internet at large.
Fine for a demo or one screen. Not for a rollout.

**A sponsor-hosted https URL** — the best version of the pitch: the test
runs against the ISP's own network. Needs to be CORS-open and shaped like
Cloudflare's (`/__down?bytes=`, `/__up`).

Whatever is chosen, the page falls back to `local` on its own if the
primary endpoint cannot be reached — a venue firewall should degrade the
feed, not break it.

## Bandwidth: the constraint that shaped the design

A real speed test moves real bytes over the **host venue's** Wi-Fi. Run
one every cycle on 125 screens and the feed stops being an ad and starts
being a problem for the people hosting us.

So the feed measures on an interval (default **30 minutes**) and shows the
last result, with its age on screen, in between. At the defaults that is
roughly **23 GB per screen per month** of venue traffic — about what an
evening of streaming costs them. `interval_seconds` is the knob;
the builder page shows the resulting number before you commit to it.

Server-side there are hard caps regardless of what a URL asks for: 8 MiB
per download request, streamed from one reused 256 KiB random block, and
uploads are discarded as they arrive rather than buffered.

## What the screen is allowed to claim

The feed will not fake a measurement. Three states, three labels:

- **testing right now** → `Testing now · Live`
- **between tests** → `Last measured 12 minutes ago`, and the result card
  repeats the age in its fine print
- **cannot reach any endpoint** → the sponsor card and *"Live speed test
  unavailable right now"*. No number at all.

Demo mode (`demo=1`) makes up plausible numbers for showing the concept on
a laptop, and wears a `SIMULATED · DEMO MODE` badge the whole time. Never
put a demo URL on a live screen.

The fine print on every result names what was measured, where, when, and
against what.

## Selling it

Two sponsor frames per cycle — the intro and the outro — plus a corner
mark that never leaves the screen. At the default 36-second cycle that is
100 intro frames and 100 outro frames per screen per hour, and the middle
section is something people in the room will actually look at, which is
not a thing most spots can claim.

One caveat worth raising with the sponsor before signing: **the venue's
connection is whatever it is**. Put this on a restaurant running tired DSL
next to a "1 Gig Fiber" comparison bar and the screen makes the sponsor's
argument better than any copy could — or embarrasses the venue, depending
on who is watching. Run it on the real connection for a day before it goes
live, and let the sponsor decide which venues they want it in.

## Checks

```
python scripts/speedtest_feed_test.py
```

Covers the config clamps, the URL round-trip, the payload cap, and the
routes on both the Tornado and ASGI stacks. The Tornado half is skipped
if tornado is not installed; it ships with Streamlit, so in the deployed
image it always runs.

The page itself was verified in Chromium end to end — a full intro → live
measurement → outro cycle against the real handlers, plus the demo path
and the both-endpoints-unreachable path.
