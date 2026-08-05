#!/usr/bin/env python3
"""Render the areas-of-interest map for the n-Compass conversation.

Deliberately open-ended: this states which markets we want, not where anyone's
territory line falls. No inferred boundary is drawn — that is a question for
n-Compass, not a claim for us to make on a page.

Palette is MCTV's "Light & Airy" scheme (sky blue + warm amber) rather than the
navy/gold house scheme, because this map needs to read across a room.
"""

import json
import math
import sys

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"
PAGE_TITLE = "MCTV &mdash; Memphis Areas of Interest"

AMBER = "#E89E3C"    # priority 1 — the markets we want most
BLUE = "#2E5E86"     # priority 2 — want, lower urgency
SLATE = "#8A93A3"    # lower-priority markers
NAVY = "#1B1F3B"

data = json.load(open(f"{OUT}/territory_ask.json"))
config = json.load(open(f"{ROOT}/config/config.json"))
cfg_markets = config["markets"]
network_today = sum(m["screens"] for m in cfg_markets.values())
oxford = cfg_markets["Oxford"]["screens"]
market_list = ", ".join(
    f'{k} ({v["screens"]})'
    for k, v in sorted(cfg_markets.items(), key=lambda kv: -kv[1]["screens"])
)
meta = data["meta"]
B = meta["bounds"]

LAT0 = (B["lat_min"] + B["lat_max"]) / 2
KX = math.cos(math.radians(LAT0))
MAP_W = 1000.0
span_x = (B["lon_max"] - B["lon_min"]) * KX
span_y = B["lat_max"] - B["lat_min"]
MAP_H = MAP_W * span_y / span_x


def px(lon):
    return (lon - B["lon_min"]) * KX / span_x * MAP_W


def py(lat):
    return (B["lat_max"] - lat) / span_y * MAP_H


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def money(v):
    return f"${v:,.0f}" if v else "&mdash;"


# ------------------------------------------------------------------ validation
errors = []
inside = lambda la, lo: (B["lat_min"] <= la <= B["lat_max"]
                         and B["lon_min"] <= lo <= B["lon_max"])
for t in data["targets"] + data["excluded"]:
    if not inside(t["lat"], t["lon"]):
        errors.append(f'{t["name"]} outside map bounds')
for la, lo in data["arc"]:
    if not inside(la, lo):
        errors.append(f"arc point {la},{lo} outside map bounds")
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)

# ---------------------------------------------------------------------- layers
counties = "".join(
    f'<rect x="{px(c["lon"][0]):.1f}" y="{py(c["lat"][1]):.1f}" '
    f'width="{px(c["lon"][1]) - px(c["lon"][0]):.1f}" '
    f'height="{py(c["lat"][0]) - py(c["lat"][1]):.1f}" class="county"/>'
    f'<text class="countylab" x="{px(c["lon"][0]) + 10:.1f}" '
    f'y="{py(c["lat"][1]) + 22:.1f}">{esc(c["name"])}</text>'
    for c in data["counties"]
)

roads = "".join(
    f'<polyline points="'
    + " ".join(f"{px(lo):.1f},{py(la):.1f}" for lo, la in r["points"])
    + '" class="road"/>'
    f'<text class="roadlab" x="{px(r["points"][-1][0]) - 5:.1f}" '
    f'y="{py(r["points"][-1][1]) - 8:.1f}" text-anchor="end">{esc(r["name"])}</text>'
    for r in data["interstates"]
)

state_line = (
    f'<line x1="0" y1="{py(34.9957):.1f}" x2="{MAP_W}" y2="{py(34.9957):.1f}" class="stateline"/>'
    f'<text class="statelab" x="{MAP_W - 16:.0f}" y="{py(34.9957) - 12:.1f}" '
    f'text-anchor="end">TENNESSEE</text>'
    f'<text class="statelab" x="{MAP_W - 16:.0f}" y="{py(34.9957) + 46:.1f}" '
    f'text-anchor="end">MISSISSIPPI</text>'
)

arc_pts = " ".join(f"{px(lo):.1f},{py(la):.1f}" for la, lo in data["arc"])
arc = f'<polyline points="{arc_pts}" class="arcband"/>'


targets = "".join(
    f'<g class="tgt">'
    f'<circle cx="{px(t["lon"]):.1f}" cy="{py(t["lat"]):.1f}" '
    f'r="{13 + math.sqrt(t["pop"]) / 22:.1f}" class="tgtdot p{t["priority"]}"/>'
    f'<text class="tgtlab" x="{px(t["lon"]):.1f}" y="{py(t["lat"]) - 24:.1f}" '
    f'text-anchor="middle">{esc(t["name"])}</text>'
    f'<text class="tgtinc" x="{px(t["lon"]):.1f}" y="{py(t["lat"]) + 36:.1f}" '
    f'text-anchor="middle">{money(t["hhi"])}</text>'
    f"</g>"
    for t in data["targets"]
)

lower = "".join(
    f'<g class="low">'
    f'<circle cx="{px(e["lon"]):.1f}" cy="{py(e["lat"]):.1f}" r="8" class="lowdot"/>'
    f'<text class="lowlab" x="{px(e["lon"]):.1f}" y="{py(e["lat"]) + 24:.1f}" '
    f'text-anchor="middle">{esc(e["name"])}</text>'
    f"</g>"
    for e in data["excluded"]
)

MILES = 10
bar = MILES / 69.05 / span_y * MAP_H
bx, by = 36, MAP_H - 32
scale = (
    f'<line x1="{bx}" y1="{by}" x2="{bx + bar:.1f}" y2="{by}" class="scale"/>'
    f'<line x1="{bx}" y1="{by-7}" x2="{bx}" y2="{by+7}" class="scale"/>'
    f'<line x1="{bx+bar:.1f}" y1="{by-7}" x2="{bx+bar:.1f}" y2="{by+7}" class="scale"/>'
    f'<text class="scalelab" x="{bx + bar/2:.1f}" y="{by-12}" text-anchor="middle">'
    f"{MILES} MILES</text>"
)

map_svg = (
    f'<svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" '
    f'aria-label="Memphis-area markets MCTV is interested in">'
    f"{counties}{roads}{state_line}{arc}{lower}{targets}{scale}</svg>"
)

p1 = sorted([t for t in data["targets"] if t["priority"] == 1], key=lambda t: -t["hhi"])
p2 = sorted([t for t in data["targets"] if t["priority"] == 2], key=lambda t: -t["hhi"])
arc_pop = sum(t["pop"] for t in data["targets"])
p1_pop = sum(t["pop"] for t in p1)


def cards(ts, color):
    return "".join(
        f'<article class="mkt" style="border-top-color:{color}">'
        f'<h3>{esc(t["name"])} <span class="st">{t["state"]}</span></h3>'
        f'<div class="figs">'
        f'<div><b>{t["pop"]:,}</b><span>People</span></div>'
        f'<div><b>{money(t["hhi"])}</b><span>Median household income</span></div>'
        f"</div></article>"
        for t in ts
    )


CSS = """
  :root { --navy:#1B1F3B; --amber:#E89E3C; --blue:#2E5E86; --slate:#8A93A3;
          --bg:#f6f7f9; --card:#fff; --text:#15181f; --muted:#5b6270; --line:#dfe2e8;
          --land:#e9ecf1; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0c1016; --card:#161c25; --text:#eef0f4; --muted:#98a1b0; --line:#28303c;
            --land:#171e28; }
  }
  :root[data-theme="dark"] { --bg:#0c1016; --card:#161c25; --text:#eef0f4; --muted:#98a1b0;
                             --line:#28303c; --land:#171e28; }
  :root[data-theme="light"] { --bg:#f6f7f9; --card:#fff; --text:#15181f; --muted:#5b6270;
                              --line:#dfe2e8; --land:#e9ecf1; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.6; }
  header.top { background:var(--navy); color:#fff; padding:40px 24px; border-bottom:6px solid var(--amber); }
  header.top h1 { margin:0 0 8px; font-size:31px; text-wrap:balance; letter-spacing:-.2px; }
  header.top p { margin:0; color:#ccd2dc; font-size:15px; max-width:70ch; }
  .wrap { max-width:1160px; margin:0 auto; padding:26px 24px 10px; }
  h2 { font-size:20px; margin:36px 0 14px; padding-bottom:9px; border-bottom:3px solid var(--amber);
       text-wrap:balance; }
  .lede { font-size:16px; max-width:72ch; margin:0 0 22px; }
  .lede b { color:var(--amber); }
  .stats { display:flex; flex-wrap:wrap; gap:14px; margin:0 0 22px; }
  .stat { background:var(--card); border:1px solid var(--line); border-top:5px solid var(--amber);
          padding:14px 18px; min-width:168px; flex:1; }
  .stat b { display:block; font-size:26px; color:var(--amber); font-variant-numeric:tabular-nums;
            line-height:1.15; }
  .stat span { font-size:11.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.7px; }
  .stat.b2 { border-top-color:var(--blue); }
  .stat.b2 b { color:var(--blue); }

  /* legend — sits directly above the map and mirrors it exactly */
  .legend { background:var(--card); border:1px solid var(--line); padding:16px 18px;
            margin-bottom:0; border-bottom:none; display:flex; flex-wrap:wrap; gap:26px; }
  .lgroup { display:flex; align-items:flex-start; gap:11px; }
  .lgroup .sw { flex:none; margin-top:2px; }
  .sw.dot { width:22px; height:22px; border-radius:50%; display:block; border:3px solid #fff;
            box-shadow:0 0 0 1px rgba(0,0,0,.14); }
  .sw.dot.sm { width:12px; height:12px; border-width:2px; margin-top:6px; }
  .sw.band { width:30px; height:16px; border-radius:3px; display:block; margin-top:5px; }
  .lgroup b { display:block; font-size:13.5px; line-height:1.35; }
  .lgroup span { font-size:12px; color:var(--muted); }
  .mapbox { background:var(--card); border:1px solid var(--line); padding:12px; margin-bottom:20px;
            overflow-x:auto; }
  .mapbox svg { display:block; width:100%; min-width:700px; height:auto; }

  .county { fill:var(--land); stroke:var(--muted); stroke-width:1.2; stroke-dasharray:4 4;
            fill-opacity:.65; }
  .countylab { font:bold 12px Arial,sans-serif; fill:var(--muted); letter-spacing:.9px; }
  .road { fill:none; stroke:#98a1b0; stroke-width:2.4; stroke-linejoin:round; opacity:.6; }
  .roadlab { font:bold 10.5px Arial,sans-serif; fill:#98a1b0; }
  .stateline { stroke:var(--muted); stroke-width:2; stroke-dasharray:11 7; opacity:.85; }
  .statelab { font:bold 12px Arial,sans-serif; fill:var(--muted); letter-spacing:1.8px; }
  .arcband { fill:none; stroke:var(--amber); stroke-width:64; stroke-opacity:.28;
             stroke-linejoin:round; stroke-linecap:round; }
  .tgtdot { stroke:#fff; stroke-width:3.5; }
  .tgtdot.p1 { fill:var(--amber); }
  .tgtdot.p2 { fill:var(--blue); }
  .tgtlab { font:bold 15px Arial,sans-serif; fill:var(--text);
            paint-order:stroke fill; stroke:var(--card); stroke-width:5px; stroke-linejoin:round; }
  .tgtinc { font:bold 13px Arial,sans-serif; fill:var(--text);
            paint-order:stroke fill; stroke:var(--card); stroke-width:4px; stroke-linejoin:round; }
  .lowdot { fill:none; stroke:var(--slate); stroke-width:2.2; stroke-dasharray:3 3; }
  .lowlab { font:12px Arial,sans-serif; fill:var(--muted);
            paint-order:stroke fill; stroke:var(--card); stroke-width:3.5px; stroke-linejoin:round; }
  .scale { stroke:var(--muted); stroke-width:2.4; }
  .scalelab { font:bold 11px Arial,sans-serif; fill:var(--muted); letter-spacing:.7px; }

  .mkts { display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:14px;
          margin-bottom:22px; }
  .mkt { background:var(--card); border:1px solid var(--line); border-top:5px solid var(--amber);
         padding:14px 16px 15px; }
  .mkt h3 { margin:0 0 10px; font-size:17px; }
  .st { font-size:10.5px; color:var(--muted); border:1px solid var(--line); padding:1px 5px;
        vertical-align:2px; font-weight:normal; }
  .figs { display:flex; gap:18px; flex-wrap:wrap; }
  .figs b { display:block; font-size:18px; font-variant-numeric:tabular-nums; }
  .figs span { font-size:10.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:5px solid var(--blue);
             padding:17px 21px; font-size:14.5px; margin-bottom:20px; }
  .callout b { color:var(--amber); }
  footer { padding:34px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

BODY = f"""<header class="top">
  <h1>Memphis &mdash; Areas We're Interested In</h1>
  <p>MCTV Elite Advertising &middot; {meta['updated']}</p>
</header>
<div class="wrap">

  <p class="lede">
    The markets below are where we'd want to build. They run as one continuous suburban arc from
    Arlington and Lakeland in the northeast, down through Germantown and Collierville, across the
    state line into Olive Branch, and west to Southaven and Hernando &mdash;
    <b>{arc_pop:,} people, every one of these markets at or above $85,500 median household
    income.</b>
  </p>

  <div class="stats">
    <div class="stat"><b>{len(p1)}</b><span>Markets we want most</span></div>
    <div class="stat"><b>{p1_pop:,}</b><span>People in those markets</span></div>
    <div class="stat b2"><b>{len(p2)}</b><span>Also of interest</span></div>
    <div class="stat b2"><b>{arc_pop:,}</b><span>People across the arc</span></div>
    <div class="stat"><b>$85.5K&ndash;$150K</b><span>Household income range</span></div>
  </div>

  <h2>The map</h2>

  <div class="legend">
    <div class="lgroup">
      <span class="sw dot" style="background:{AMBER}"></span>
      <span><b>Want most</b><span>Germantown, Collierville, Olive Branch, Hernando</span></span>
    </div>
    <div class="lgroup">
      <span class="sw dot" style="background:{BLUE}"></span>
      <span><b>Also interested</b><span>Southaven, Arlington, Lakeland, Bartlett</span></span>
    </div>
    <div class="lgroup">
      <span class="sw band" style="background:{AMBER};opacity:.45"></span>
      <span><b>The arc</b><span>How these markets connect</span></span>
    </div>
    <div class="lgroup">
      <span class="sw dot sm" style="background:transparent;border:2px dashed {SLATE};box-shadow:none"></span>
      <span><b>Lower priority</b><span>Not where we'd start</span></span>
    </div>
    <div class="lgroup">
      <span class="sw dot sm" style="background:transparent;border:none;box-shadow:none"></span>
      <span><b>Circle size</b><span>Scales with population</span></span>
    </div>
  </div>
  <div class="mapbox">{map_svg}</div>

  <div class="callout">
    <b>Worth noticing:</b> Germantown sits about nine miles from Olive Branch, and Collierville about
    eleven. On the ground this is one market &mdash; the same shoppers, the same commutes, the same
    restaurants. The state line is the only thing that splits it.
  </div>

  <h2>Want most</h2>
  <div class="mkts">{cards(p1, AMBER)}</div>

  <h2>Also interested</h2>
  <div class="mkts">{cards(p2, BLUE)}</div>

  <h2>What we'd build</h2>
  <div class="callout">
    We run <b>{network_today} screens</b> across North Mississippi today &mdash; {market_list}.
    Oxford is the one to look at: {oxford} screens in a town of 27,000, which is the density we
    aim for when we own a market properly.
    <br><br>
    For the Memphis area we'd expect to start in the range of <b>40 screens</b> across the first
    two markets, and grow from there as it proves out &mdash; realistically toward 75&ndash;90 over
    the first couple of years if the sell-through supports it. We'd rather build two markets
    properly than put a handful of screens in six.
    <br><br>
    Those are intentions, not promises &mdash; we'd want to walk the venues before committing to
    numbers.
  </div>

  <h2>Lower priority for us</h2>
  <div class="callout">
    Memphis proper, West Memphis and Millington aren't where we'd start, and Horn Lake we'd pick up
    once we're already working the county. Not a hard no on any of them &mdash; just not the first
    conversation.
  </div>

  <h2>Open questions</h2>
  <div class="callout">
    We've drawn this by market rather than by boundary, because we don't know where the territory
    lines actually fall &mdash; particularly across the state line, where several of the markets
    we're most interested in sit. <b>Happy to shape the ask around whatever the real boundaries
    are</b> once we understand them.
  </div>

</div>
<footer>MCTV Digital, Inc. &middot; Memphis area &middot; {meta['updated']}</footer>
"""

html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        + BODY + "</body>\n</html>\n")
artifact_html = f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n" + BODY

with open(f"{OUT}/territory-ask.html", "w") as f:
    f.write(html)
with open(f"{OUT}/territory-ask.artifact.html", "w") as f:
    f.write(artifact_html)

print(f"territory-ask.html written: {len(p1)} priority-1, {len(p2)} priority-2, "
      f"{len(data['excluded'])} lower, {len(html):,} bytes")
print(f"  arc population {arc_pop:,} | priority-1 population {p1_pop:,}")
