#!/usr/bin/env python3
"""Render the negotiation map: her observed footprint vs. the territory we want.

Two layers that must stay visually distinct — what we have OBSERVED (her pins, and
the hull around them) and what we are ASKING FOR (the wealth arc). The hull is an
inference and is labelled as one everywhere it appears.
"""

import json
import math
import sys

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"
PAGE_TITLE = "MCTV &mdash; Her Footprint vs. What We Want"

HER = "#C4576B"      # observed — hers
WANT = "#C5A55A"     # asking for
NAVY = "#1B1F3B"

data = json.load(open(f"{OUT}/territory_ask.json"))
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


# ------------------------------------------------------------------ validation
errors = []
inside = lambda la, lo: (B["lat_min"] <= la <= B["lat_max"]
                         and B["lon_min"] <= lo <= B["lon_max"])
for la, lo in data["her_pins"]:
    if not inside(la, lo):
        errors.append(f"pin {la},{lo} outside map bounds")
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


# --------------------------------------------------- convex hull of her pins
def hull(points):
    """Andrew's monotone chain. Input (lat, lon); returns hull in order."""
    pts = sorted(set((lo, la) for la, lo in points))
    if len(pts) <= 2:
        return [(la, lo) for lo, la in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [(la, lo) for lo, la in lower[:-1] + upper[:-1]]


h = hull(data["her_pins"])
hull_pts = " ".join(f"{px(lo):.1f},{py(la):.1f}" for la, lo in h)

# ------------------------------------------------------------------- layers
counties = "".join(
    f'<rect x="{px(c["lon"][0]):.1f}" y="{py(c["lat"][1]):.1f}" '
    f'width="{px(c["lon"][1]) - px(c["lon"][0]):.1f}" '
    f'height="{py(c["lat"][0]) - py(c["lat"][1]):.1f}" class="county"/>'
    f'<text class="countylab" x="{px(c["lon"][0]) + 9:.1f}" '
    f'y="{py(c["lat"][1]) + 20:.1f}">{esc(c["name"])}</text>'
    for c in data["counties"]
)

roads = "".join(
    f'<polyline points="'
    + " ".join(f"{px(lo):.1f},{py(la):.1f}" for lo, la in r["points"])
    + f'" class="road"/>'
    f'<text class="roadlab" x="{px(r["points"][-1][0]) - 4:.1f}" '
    f'y="{py(r["points"][-1][1]) - 7:.1f}" text-anchor="end">{esc(r["name"])}</text>'
    for r in data["interstates"]
)

state_line = (
    f'<line x1="0" y1="{py(34.9957):.1f}" x2="{MAP_W}" y2="{py(34.9957):.1f}" class="stateline"/>'
    # Right-aligned and spread vertically: the left edge is where the county
    # captions sit, and TENNESSEE/MISSISSIPPI landed on top of "DESOTO CO, MS".
    f'<text class="statelab" x="{MAP_W - 14:.0f}" y="{py(34.9957) - 10:.1f}" '
    f'text-anchor="end">TENNESSEE</text>'
    f'<text class="statelab" x="{MAP_W - 14:.0f}" y="{py(34.9957) + 42:.1f}" '
    f'text-anchor="end">MISSISSIPPI</text>'
)

# the arc we want — a thick band through the target cities
arc_pts = " ".join(f"{px(lo):.1f},{py(la):.1f}" for la, lo in data["arc"])
arc = (
    f'<polyline points="{arc_pts}" class="arcband"/>'
    f'<polyline points="{arc_pts}" class="arcline"/>'
)

her_hull = (
    f'<polygon points="{hull_pts}" class="hull"/>'
    f'<text class="hulllab" x="{px(-89.62):.1f}" y="{py(35.35):.1f}" text-anchor="end">'
    f"INFERRED FROM PINS &mdash; NOT A CONFIRMED BOUNDARY</text>"
)

her_pins = "".join(
    f'<circle cx="{px(lo):.1f}" cy="{py(la):.1f}" r="5" class="herpin"/>'
    for la, lo in data["her_pins"]
)


def money(v):
    return f"${v:,.0f}" if v else "&mdash;"


targets = "".join(
    f'<g class="tgt">'
    f'<circle cx="{px(t["lon"]):.1f}" cy="{py(t["lat"]):.1f}" '
    f'r="{9 + math.sqrt(t["pop"]) / 26:.1f}" '
    f'class="tgtdot p{t["priority"]}"/>'
    f'<text class="tgtlab" x="{px(t["lon"]):.1f}" y="{py(t["lat"]) - 17:.1f}" '
    f'text-anchor="middle">{esc(t["name"])}</text>'
    f'<text class="tgtinc" x="{px(t["lon"]):.1f}" y="{py(t["lat"]) + 26:.1f}" '
    f'text-anchor="middle">{money(t["hhi"])}</text>'
    f"</g>"
    for t in data["targets"]
)

excluded = "".join(
    f'<g class="exc">'
    f'<circle cx="{px(e["lon"]):.1f}" cy="{py(e["lat"]):.1f}" r="7" class="excdot"/>'
    f'<line x1="{px(e["lon"]) - 5:.1f}" y1="{py(e["lat"]) - 5:.1f}" '
    f'x2="{px(e["lon"]) + 5:.1f}" y2="{py(e["lat"]) + 5:.1f}" class="excx"/>'
    f'<line x1="{px(e["lon"]) + 5:.1f}" y1="{py(e["lat"]) - 5:.1f}" '
    f'x2="{px(e["lon"]) - 5:.1f}" y2="{py(e["lat"]) + 5:.1f}" class="excx"/>'
    f'<text class="exclab" x="{px(e["lon"]):.1f}" y="{py(e["lat"]) + 22:.1f}" '
    f'text-anchor="middle">{esc(e["name"])}</text>'
    f"</g>"
    for e in data["excluded"]
)

MILES = 10
bar = MILES / 69.05 / span_y * MAP_H
bx, by = 34, MAP_H - 30
scale = (
    f'<line x1="{bx}" y1="{by}" x2="{bx + bar:.1f}" y2="{by}" class="scale"/>'
    f'<line x1="{bx}" y1="{by-6}" x2="{bx}" y2="{by+6}" class="scale"/>'
    f'<line x1="{bx+bar:.1f}" y1="{by-6}" x2="{bx+bar:.1f}" y2="{by+6}" class="scale"/>'
    f'<text class="scalelab" x="{bx + bar/2:.1f}" y="{by-10}" text-anchor="middle">'
    f"{MILES} MILES</text>"
)

map_svg = (
    f'<svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" '
    f'aria-label="Her observed footprint against the territory we want">'
    f"{counties}{roads}{state_line}{arc}{her_hull}{her_pins}{excluded}{targets}{scale}</svg>"
)

p1 = [t for t in data["targets"] if t["priority"] == 1]
p2 = [t for t in data["targets"] if t["priority"] == 2]
arc_pop = sum(t["pop"] for t in data["targets"])


def rows(ts):
    return "".join(
        f'<tr><td><b>{esc(t["name"])}</b> <span class="st">{t["state"]}</span></td>'
        f'<td>{t["pop"]:,}</td><td>{money(t["hhi"])}</td>'
        f'<td class="nt">{esc(t["note"])}</td></tr>'
        for t in sorted(ts, key=lambda t: -t["hhi"])
    )


exc_rows = "".join(
    f'<tr><td><b>{esc(e["name"])}</b></td><td>{e["pop"]:,}</td>'
    f'<td>{money(e["hhi"])}</td><td class="nt">{esc(e["why"])}</td></tr>'
    for e in data["excluded"]
)

CSS = """
  :root { --navy:#1B1F3B; --gold:#C5A55A; --her:#C4576B; --bg:#f7f7f9; --card:#fff;
          --text:#1a1a1a; --muted:#5d616b; --line:#e3e3e8; --land:#eceef2; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36;
            --land:#181e26; }
  }
  :root[data-theme="dark"] { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6;
                             --line:#2a2f36; --land:#181e26; }
  :root[data-theme="light"] { --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#5d616b;
                              --line:#e3e3e8; --land:#eceef2; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.55; }
  header.top { background:var(--navy); color:#fff; padding:34px 24px; border-bottom:5px solid var(--gold); }
  header.top h1 { margin:0 0 6px; font-size:27px; text-wrap:balance; }
  header.top p { margin:0; color:#c9cbd6; font-size:14px; }
  .badge-int { display:inline-block; margin-top:12px; background:var(--her); color:#fff;
    font-size:11px; letter-spacing:.8px; text-transform:uppercase; padding:4px 10px; font-weight:bold; }
  .wrap { max-width:1160px; margin:0 auto; padding:24px; }
  h2 { font-size:19px; margin:32px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--gold);
       text-wrap:balance; }
  .stats { display:flex; flex-wrap:wrap; gap:12px; margin:0 0 16px; }
  .stat { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
          padding:11px 15px; min-width:150px; flex:1; }
  .stat b { display:block; font-size:21px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .stat span { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .stat.hers { border-left-color:var(--her); }
  .stat.hers b { color:var(--her); }
  .mapbox { background:var(--card); border:1px solid var(--line); padding:10px; margin-bottom:14px;
            overflow-x:auto; }
  .mapbox svg { display:block; width:100%; min-width:680px; height:auto; }
  .county { fill:var(--land); stroke:var(--muted); stroke-width:1; stroke-dasharray:3 3;
            fill-opacity:.7; }
  .countylab { font:bold 11px Arial,sans-serif; fill:var(--muted); letter-spacing:.7px; }
  .road { fill:none; stroke:#8a94a6; stroke-width:2.2; stroke-linejoin:round; opacity:.75; }
  .roadlab { font:bold 10px Arial,sans-serif; fill:#8a94a6; }
  .stateline { stroke:var(--muted); stroke-width:1.6; stroke-dasharray:9 6; opacity:.8; }
  .statelab { font:bold 11px Arial,sans-serif; fill:var(--muted); letter-spacing:1.5px; }
  .arcband { fill:none; stroke:var(--gold); stroke-width:52; stroke-opacity:.20;
             stroke-linejoin:round; stroke-linecap:round; }
  .arcline { fill:none; stroke:var(--gold); stroke-width:2.5; stroke-dasharray:10 6;
             stroke-opacity:.85; stroke-linejoin:round; }
  .hull { fill:var(--her); fill-opacity:.07; stroke:var(--her); stroke-width:2.5;
          stroke-dasharray:12 7; }
  .hulllab { font:bold 11px Arial,sans-serif; fill:var(--her); letter-spacing:.8px; }
  .herpin { fill:var(--her); stroke:#fff; stroke-width:1.3; opacity:.95; }
  .tgtdot { fill:var(--gold); stroke:#fff; stroke-width:2.5; }
  .tgtdot.p2 { fill-opacity:.55; }
  .tgtlab { font:bold 13px Arial,sans-serif; fill:var(--text);
            paint-order:stroke fill; stroke:var(--card); stroke-width:4px; stroke-linejoin:round; }
  .tgtinc { font:bold 11.5px Arial,sans-serif; fill:var(--gold);
            paint-order:stroke fill; stroke:var(--card); stroke-width:3.5px; stroke-linejoin:round; }
  .excdot { fill:none; stroke:var(--muted); stroke-width:1.6; opacity:.8; }
  .excx { stroke:var(--muted); stroke-width:1.8; opacity:.8; }
  .exclab { font:11px Arial,sans-serif; fill:var(--muted);
            paint-order:stroke fill; stroke:var(--card); stroke-width:3px; stroke-linejoin:round; }
  .scale { stroke:var(--muted); stroke-width:2; }
  .scalelab { font:bold 10px Arial,sans-serif; fill:var(--muted); letter-spacing:.6px; }
  .legend { display:flex; flex-wrap:wrap; gap:16px; font-size:12.5px; color:var(--muted);
            margin-bottom:18px; align-items:center; }
  .legend i { display:inline-block; width:14px; height:14px; border-radius:50%; margin-right:6px;
              vertical-align:-3px; }
  .legend i.band { border-radius:2px; width:22px; height:11px; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
             padding:15px 19px; font-size:13.5px; margin-bottom:18px; }
  .callout.key { border-left-color:var(--gold); }
  .callout.warn { border-left-color:var(--her); }
  .callout b { color:var(--gold); }
  .callout.warn b { color:var(--her); }
  .tablewrap { overflow-x:auto; margin-bottom:18px; }
  table { border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
          font-size:13px; min-width:640px; }
  th,td { padding:9px 13px; border-bottom:1px solid var(--line); text-align:left;
          vertical-align:top; }
  td:nth-child(2), td:nth-child(3) { font-variant-numeric:tabular-nums; white-space:nowrap; }
  th { background:var(--navy); color:#fff; font-size:11px; text-transform:uppercase;
       letter-spacing:.6px; }
  tr:last-child td { border-bottom:none; }
  .st { font-size:10px; color:var(--muted); border:1px solid var(--line); padding:1px 4px; }
  .nt { color:var(--muted); font-size:12.5px; }
  footer { padding:30px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

BODY = f"""<header class="top">
  <h1>Her Footprint vs. What We Want</h1>
  <p>Negotiation map for the n-Compass conversation &middot; MCTV Elite Advertising &middot;
     {meta['updated']}</p>
  <span class="badge-int">Internal &mdash; not for n-Compass</span>
</header>
<div class="wrap">

  <div class="stats">
    <div class="stat hers"><b>~{len(data['her_pins'])}</b><span>Her observed pins</span></div>
    <div class="stat hers"><b>2</b><span>States she operates in</span></div>
    <div class="stat"><b>{arc_pop:,}</b><span>People in the arc we want</span></div>
    <div class="stat"><b>$149,920</b><span>Top target income</span></div>
    <div class="stat"><b>$85,500</b><span>Lowest target income</span></div>
  </div>

  <div class="callout warn">
    <b>Read the dashed red boundary carefully.</b> It is the convex hull of her observed pins
    &mdash; <b>where she has screens, not where her territory ends</b>. Nobody has shown us the
    actual grant. Her real boundary could be larger, smaller, or a completely different shape.
    That is the first thing to ask Don, and this map is drawn to make the question obvious.
  </div>

  <h2>The map</h2>
  <div class="legend">
    <span><i style="background:{HER}"></i>Her screens (observed)</span>
    <span><i class="band" style="background:{HER};opacity:.35"></i>Inferred footprint &mdash; not a boundary</span>
    <span><i class="band" style="background:{WANT};opacity:.45"></i>The arc we want</span>
    <span><i style="background:{WANT}"></i>Priority 1 target</span>
    <span><i style="background:{WANT};opacity:.55"></i>Priority 2 target</span>
    <span>&#10005; deliberately excluded</span>
  </div>
  <div class="mapbox">{map_svg}</div>

  <div class="callout key">
    <b>The shape of the ask is a crescent, not a county.</b> Arlington and Lakeland at the top,
    down through Bartlett, Germantown and Collierville, across the state line into Olive Branch,
    then west to Southaven and south to Hernando. <b>{arc_pop:,} people, every one of those
    markets at or above $85,500 median household income.</b>
    <br><br>
    Germantown sits about <b>9 miles</b> from Olive Branch and Collierville about <b>11</b>. The
    state line is the only thing between them &mdash; and it is the only reason we have been
    treating them as two different conversations.
  </div>

  <h2>Priority 1 &mdash; what we actually want</h2>
  <div class="tablewrap"><table>
    <tr><th>Market</th><th>Population</th><th>Median HHI</th><th>Note</th></tr>
    {rows(p1)}
  </table></div>

  <h2>Priority 2 &mdash; take it if it comes</h2>
  <div class="tablewrap"><table>
    <tr><th>Market</th><th>Population</th><th>Median HHI</th><th>Note</th></tr>
    {rows(p2)}
  </table></div>

  <h2>Deliberately not asking for</h2>
  <div class="callout">
    Worth naming these out loud. Asking for everything makes the ask look unconsidered; asking for
    a specific shape makes it look like we have done the work &mdash; which we have.
  </div>
  <div class="tablewrap"><table>
    <tr><th>Market</th><th>Population</th><th>Median HHI</th><th>Why not</th></tr>
    {exc_rows}
  </table></div>

  <h2>What the map tells you to ask</h2>
  <div class="callout key">
    <b>1. Where does her territory actually end?</b> The red hull is our guess. If her grant is
    bigger than her pins, asking for &ldquo;DeSoto County&rdquo; leaves the best ground on the
    table.
    <br><br>
    <b>2. How is she operating in Tennessee?</b> Ten-plus pins sit north of the state line, in the
    richest suburbs on this map. Whatever arrangement permits that is the arrangement we want.
    <br><br>
    <b>3. She is thin everywhere.</b> ~{len(data['her_pins'])} pins across seven towns in two
    states. Not one of these markets is built out &mdash; Southaven alone would carry ~160 screens
    at the density we run in Oxford. This is a toehold being handed over, not a network.
  </div>

  <div class="callout warn">
    <b>Precision note.</b> {esc(meta['pin_note'])} {esc(meta['hull_note'])}
  </div>

</div>
<footer>MCTV Digital, Inc. &mdash; internal negotiation map. Generated from territory_ask.json.</footer>
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

print(f"territory-ask.html written: {len(data['her_pins'])} pins, {len(h)} hull vertices, "
      f"{len(data['targets'])} targets, {len(html):,} bytes")
print(f"  arc population {arc_pop:,} | map {MAP_W:.0f}x{MAP_H:.0f}")
