#!/usr/bin/env python3
"""Render the 60-mile radius scan around MCTV's current markets.

Same projection approach as build_metro_map.py — equirectangular with a cos(latitude)
correction, so the radius rings are true circles on the ground. Stdlib only.
"""

import json
import math
import sys

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"
PAGE_TITLE = "MCTV &mdash; 60-Mile Radius Scan"

data = json.load(open(f"{OUT}/radius_scan.json"))
config = json.load(open(f"{ROOT}/config/config.json"))
meta, tiers = data["meta"], data["tiers"]
B = meta["bounds"]
R = meta["radius_miles"]

LAT0 = (B["lat_min"] + B["lat_max"]) / 2
KX = math.cos(math.radians(LAT0))
MAP_W = 1000.0
span_x = (B["lon_max"] - B["lon_min"]) * KX
span_y = B["lat_max"] - B["lat_min"]
MAP_H = MAP_W * span_y / span_x
MI_PER_DEG_LAT = 69.05
RING_PX = R / MI_PER_DEG_LAT / span_y * MAP_H     # radius in px (uniform: map is to scale)


def px(lon):
    return (lon - B["lon_min"]) * KX / span_x * MAP_W


def py(lat):
    return (B["lat_max"] - lat) / span_y * MAP_H


def miles(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2
         + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# nearest current market for each candidate
current = data["current"]
for c in data["candidates"] + data["outside"]:
    d = sorted((miles((c["lat"], c["lon"]), (m["lat"], m["lon"])), m["name"]) for m in current)
    c["dist"], c["nearest"] = round(d[0][0], 1), d[0][1]

# ------------------------------------------------------------------ validation
errors = []
for c in data["candidates"]:
    if c["dist"] > R:
        errors.append(f'{c["name"]}: {c["dist"]} mi is outside the {R}-mile radius')
    if str(c["tier"]) not in tiers:
        errors.append(f'{c["name"]}: unknown tier {c["tier"]}')
for c in data["outside"]:
    if c["dist"] <= R:
        errors.append(f'{c["name"]}: listed as outside but is only {c["dist"]} mi')
cfg_screens = {k: v["screens"] for k, v in config["markets"].items()}
for m in current:
    if cfg_screens.get(m["name"]) != m["screens"]:
        errors.append(f'{m["name"]}: {m["screens"]} screens != config.json {cfg_screens.get(m["name"])}')
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)

# ---------------------------------------------------------------------- layers
rings = "".join(
    f'<circle cx="{px(m["lon"]):.1f}" cy="{py(m["lat"]):.1f}" r="{RING_PX:.1f}" class="ring"/>'
    for m in current
)
homes = "".join(
    f'<g class="home">'
    f'<circle cx="{px(m["lon"]):.1f}" cy="{py(m["lat"]):.1f}" '
    f'r="{6 + m["screens"] * 0.13:.1f}" class="homedot"/>'
    f'<text class="homelab" x="{px(m["lon"]):.1f}" y="{py(m["lat"]) - 12:.1f}" '
    f'text-anchor="middle">{esc(m["name"])} &middot; {m["screens"]}</text>'
    f"</g>"
    for m in current
)


def cand_marker(c, faded=False):
    t = tiers.get(str(c.get("tier", 4)), {"color": "#8A8FA3"})
    color = "#8A8FA3" if faded else t["color"]
    r = 4 + min(math.sqrt(max(c.get("population") or 1500, 1)) / 26, 12)
    cls = "cand faded" if faded else "cand"
    return (
        f'<g class="{cls}" data-tier="{c.get("tier", "")}">'
        f'<circle cx="{px(c["lon"]):.1f}" cy="{py(c["lat"]):.1f}" r="{r:.1f}" '
        f'fill="{color}" stroke="#fff" stroke-width="1.6" opacity=".92"/>'
        f'<text class="candlab" x="{px(c["lon"]) + r + 4:.1f}" y="{py(c["lat"]) + 4:.1f}">'
        f'{esc(c["name"].split(",")[0])}</text>'
        f"</g>"
    )


markers = "".join(cand_marker(c) for c in data["candidates"])
outside = "".join(cand_marker(c, faded=True) for c in data["outside"])

# state lines: MS/TN at 34.9957, MS/AL at -88.20 (approx, north of Lowndes)
state_lines = (
    f'<line x1="{px(B["lon_min"]):.1f}" y1="{py(34.9957):.1f}" '
    f'x2="{px(-88.20):.1f}" y2="{py(34.9957):.1f}" class="stateline"/>'
    f'<line x1="{px(-88.20):.1f}" y1="{py(B["lat_min"]):.1f}" '
    f'x2="{px(-88.20):.1f}" y2="{py(34.9957):.1f}" class="stateline"/>'
    f'<text class="statelab" x="{px(-90.6):.1f}" y="{py(35.25):.1f}">TENNESSEE</text>'
    f'<text class="statelab" x="{px(-87.6):.1f}" y="{py(34.6):.1f}">ALABAMA</text>'
    f'<text class="statelab" x="{px(-90.6):.1f}" y="{py(34.6):.1f}">MISSISSIPPI</text>'
)

bx, by = 40, MAP_H - 34
bar = R / MI_PER_DEG_LAT / span_y * MAP_H
scale = (
    f'<line x1="{bx}" y1="{by}" x2="{bx + bar:.1f}" y2="{by}" class="scale"/>'
    f'<line x1="{bx}" y1="{by-6}" x2="{bx}" y2="{by+6}" class="scale"/>'
    f'<line x1="{bx+bar:.1f}" y1="{by-6}" x2="{bx+bar:.1f}" y2="{by+6}" class="scale"/>'
    f'<text class="scalelab" x="{bx + bar/2:.1f}" y="{by-10}" text-anchor="middle">'
    f"{R} MILES</text>"
)

map_svg = (
    f'<svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" '
    f'aria-label="60-mile radius around MCTV markets">'
    f"{rings}{state_lines}{outside}{markers}{homes}{scale}</svg>"
)

# ----------------------------------------------------------------------- cards
def money(v):
    return f"${v:,.0f}" if v else "&mdash;"


named = [c for c in data["candidates"] if c.get("against") is not None]
fill = [c for c in data["candidates"] if c.get("against") is None]
named.sort(key=lambda c: c["rank"])

cards = "".join(
    f'<article class="card" data-tier="{c["tier"]}">'
    f'<header style="border-left-color:{tiers[str(c["tier"])]["color"]}">'
    f"<h3>{esc(c['name'])}</h3>"
    f'<span class="dist">{c["dist"]:.0f} mi &middot; {esc(c["nearest"])}</span></header>'
    f'<div class="figs"><div><b>{c["population"]:,}</b><span>Population</span></div>'
    f'<div><b>{money(c["hhi"])}</b><span>Median HHI</span></div></div>'
    f'<p class="for">{esc(c["note"])}</p>'
    f'<p class="agn"><b>Against:</b> {esc(c["against"])}</p>'
    f"</article>"
    for c in named
)

fill.sort(key=lambda c: c["dist"])
fill_rows = "".join(
    f'<tr><td><b>{esc(c["name"])}</b></td><td>{c["dist"]:.0f} mi</td>'
    f'<td>{esc(c["nearest"])}</td><td>{c["population"]:,}</td>'
    f'<td>{esc(c["note"].split(". ", 1)[1] if ". " in c["note"] else "")}</td></tr>'
    for c in fill
)
out_rows = "".join(
    f'<tr><td><b>{esc(c["name"])}</b></td><td>{c["dist"]:.0f} mi</td>'
    f'<td>{esc(c["nearest"])}</td><td>{esc(c["note"])}</td></tr>'
    for c in sorted(data["outside"], key=lambda c: c["dist"])
)

fill_pop = sum(c["population"] for c in fill)

CSS = """
  :root { --navy:#1B1F3B; --gold:#C5A55A; --bg:#f7f7f9; --card:#fff; --text:#1a1a1a;
          --muted:#5d616b; --line:#e3e3e8; --land:#eceef2; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36;
            --land:#171d25; }
  }
  :root[data-theme="dark"] { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6;
                             --line:#2a2f36; --land:#171d25; }
  :root[data-theme="light"] { --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#5d616b;
                              --line:#e3e3e8; --land:#eceef2; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.55; }
  header.top { background:var(--navy); color:#fff; padding:34px 24px; border-bottom:5px solid var(--gold); }
  header.top h1 { margin:0 0 6px; font-size:27px; text-wrap:balance; }
  header.top p { margin:0; color:#c9cbd6; font-size:14px; }
  .badge-int { display:inline-block; margin-top:12px; background:#C4576B; color:#fff; font-size:11px;
               letter-spacing:.8px; text-transform:uppercase; padding:4px 10px; font-weight:bold; }
  .wrap { max-width:1140px; margin:0 auto; padding:24px; }
  h2 { font-size:19px; margin:34px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--gold);
       text-wrap:balance; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
             padding:15px 19px; font-size:13.5px; margin-bottom:18px; }
  .callout.key { border-left-color:var(--gold); }
  .callout.gap { border-left-color:#C4576B; }
  .callout b { color:var(--gold); }
  .mapbox { background:var(--card); border:1px solid var(--line); padding:10px; margin-bottom:14px;
            overflow-x:auto; }
  .mapbox svg { display:block; width:100%; min-width:680px; height:auto; }
  .ring { fill:var(--gold); fill-opacity:.055; stroke:var(--gold); stroke-width:1.5;
          stroke-dasharray:6 5; stroke-opacity:.55; }
  .homedot { fill:var(--navy); stroke:var(--gold); stroke-width:3; }
  @media (prefers-color-scheme: dark) { .homedot { fill:#e6e6e6; } }
  .homelab { font:bold 12px Arial,sans-serif; fill:var(--text);
             paint-order:stroke fill; stroke:var(--card); stroke-width:3.5px; stroke-linejoin:round; }
  .candlab { font:11px Arial,sans-serif; fill:var(--text);
             paint-order:stroke fill; stroke:var(--card); stroke-width:3px; stroke-linejoin:round; }
  .cand.faded { opacity:.4; }
  .stateline { stroke:#C4576B; stroke-width:1.5; stroke-dasharray:7 5; opacity:.7; }
  .statelab { font:bold 11px Arial,sans-serif; fill:#C4576B; letter-spacing:1.4px; opacity:.75; }
  .scale { stroke:var(--muted); stroke-width:2; }
  .scalelab { font:bold 10px Arial,sans-serif; fill:var(--muted); letter-spacing:.6px; }
  .legend { display:flex; flex-wrap:wrap; gap:15px; font-size:12px; color:var(--muted);
            margin-bottom:18px; align-items:center; }
  .legend i { display:inline-block; width:13px; height:13px; border-radius:50%; margin-right:5px;
              vertical-align:-2px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:15px;
           margin-bottom:20px; }
  .card { background:var(--card); border:1px solid var(--line); padding:0 0 14px; }
  .card header { border-left:5px solid var(--gold); padding:13px 15px 8px; }
  .card h3 { margin:0; font-size:16px; }
  .dist { font-size:11.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .figs { display:flex; gap:22px; margin:10px 15px 11px; }
  .figs b { display:block; font-size:17px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .figs span { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
  .card p { margin:0 15px 9px; font-size:13px; }
  .agn { color:var(--muted); }
  .agn b { color:#C4576B; }
  .tablewrap { overflow-x:auto; margin-bottom:18px; }
  table { border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
          font-size:13px; min-width:560px; }
  th,td { padding:8px 12px; border-bottom:1px solid var(--line); text-align:left; }
  td:nth-child(2), td:nth-child(4) { font-variant-numeric:tabular-nums; }
  th { background:var(--navy); color:#fff; font-size:11px; text-transform:uppercase;
       letter-spacing:.6px; }
  tr:last-child td { border-bottom:none; }
  footer { padding:30px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

BODY = f"""<header class="top">
  <h1>What's Within 60 Miles</h1>
  <p>Expansion candidates around Oxford, Starkville, Tupelo, Columbus and West Point &middot;
     MCTV Elite Advertising &middot; {meta['updated']}</p>
  <span class="badge-int">Internal &mdash; not for n-Compass</span>
</header>
<div class="wrap">

  <div class="callout key">
    <b>Short answer: one real market, and it isn't in Mississippi.</b>
    <b>Tuscaloosa</b> is 53 miles from Columbus &mdash; 116,477 people plus roughly 34,000
    University of Alabama students. That is the only genuine second Oxford inside the radius, and
    Oxford is the build we have already proven at 75 screens. Everything else in range is either a
    small satellite of a market we already serve, or shrinking.
    <br><br>
    <b>But the best move inside 60 miles isn't a new market at all.</b> Columbus has
    <b>2 screens</b> and West Point has <b>1</b> &mdash; while Lowndes County absorbs a
    <b>$2.5 billion Steel Dynamics investment creating 1,000 jobs at an average wage of
    $93,000</b>, plus a $90M Kloeckner aluminum plant and a $200M Aluminum Dynamics expansion.
    We are three screens deep in a county having the biggest industrial decade in its history.
  </div>

  <h2>The map</h2>
  <div class="legend">
    <span><i style="background:#1B1F3B;border:2px solid #C5A55A"></i>Current market (screens)</span>
    <span><i style="background:{tiers['1']['color']}"></i>Worth a real look</span>
    <span><i style="background:{tiers['2']['color']}"></i>Different play</span>
    <span><i style="background:{tiers['3']['color']}"></i>Satellite fill-in</span>
    <span><i style="background:{tiers['4']['color']}"></i>Skip</span>
    <span>Dashed rings = {R}-mile radius</span>
  </div>
  <div class="mapbox">{map_svg}</div>
  <div class="callout">
    To scale &mdash; equirectangular projection with a cos(latitude) correction, so the rings are
    true circles on the ground. {esc(meta['method'])}
  </div>

  <h2>The ones worth discussing</h2>
  <div class="cards">{cards}</div>

  <h2>Satellite fill-in &mdash; {len(fill)} towns, {fill_pop:,} people</h2>
  <div class="callout">
    None of these justifies its own launch. Together they are a different proposition: every one
    sits inside an existing rep's drive, so the marginal cost of adding a handful of screens is
    close to zero &mdash; and they push the network screen count toward the tiers that matter on
    the rate card.
  </div>
  <div class="tablewrap"><table>
    <tr><th>Town</th><th>Distance</th><th>Nearest market</th><th>Population</th><th>Note</th></tr>
    {fill_rows}
  </table></div>

  <h2>Just outside the radius</h2>
  <div class="tablewrap"><table>
    <tr><th>Town</th><th>Distance</th><th>Nearest market</th><th>Note</th></tr>
    {out_rows}
  </table></div>

  <h2>Recommendation</h2>
  <div class="callout key">
    <b>1. Finish the Golden Triangle before opening anything new.</b> Columbus and West Point are
    3 screens between them against a $2.5B industrial build-out. No territory negotiation, no new
    rep, existing brand. Same argument as Tupelo's under-density, with a bigger tailwind.
    <br><br>
    <b>2. Scout Tuscaloosa, don't commit to it.</b> It is the biggest prize in range and the closest
    thing to a second Oxford we will find &mdash; but Impulse Digital Media is already running our
    exact model there, it crosses a state line, and it needs a rep who lives in it. Worth a trip and
    a competitive read, not a build decision yet.
    <br><br>
    <b>3. Fold the satellites in opportunistically.</b> Pontotoc, Fulton, New Albany, Amory,
    Aberdeen and Water Valley are all inside 25 miles of a market we already run.
  </div>

  <div class="callout gap">
    <b>Caution on Columbus itself.</b> The city is shrinking &mdash; 22,507 people, down 6.2% since
    2020, median household income $42,235 with a 21.3% poverty rate. The money is arriving in
    <i>Lowndes County</i> at $93,000 a job, not in the city's existing household base. Put the
    screens where those wages get spent, which may mean Starkville and the Highway 45 corridor more
    than downtown Columbus. That is the same lesson as Byhalia, and worth checking on the ground
    before spending.
  </div>

</div>
<footer>MCTV Digital, Inc. &mdash; internal planning document. Generated from radius_scan.json.</footer>
"""

html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        + BODY + "</body>\n</html>\n")
artifact_html = f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n" + BODY

with open(f"{OUT}/radius-map.html", "w") as f:
    f.write(html)
with open(f"{OUT}/radius-map.artifact.html", "w") as f:
    f.write(artifact_html)

print(f"radius-map.html written: {len(data['candidates'])} in radius, "
      f"{len(data['outside'])} outside, {len(html):,} bytes")
for c in sorted(named, key=lambda c: c["rank"])[:4]:
    print(f"  {c['name']:<28}{c['dist']:5.1f} mi from {c['nearest']}")
