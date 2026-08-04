#!/usr/bin/env python3
"""Render the Memphis metro zone map from metro_zones.json.

Real geography: an equirectangular projection with a cos(latitude) correction, so
distances and box proportions are true to scale. Stdlib only, self-contained output.
"""

import json
import math
import sys

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"

NAVY, GOLD = "#1B1F3B", "#C5A55A"
PAGE_TITLE = "MCTV &mdash; Memphis Metro Zone Map"

data = json.load(open(f"{OUT}/metro_zones.json"))
meta, tiers = data["meta"], data["tiers"]
B = meta["bounds"]

# ------------------------------------------------------------------ projection
LAT0 = (B["lat_min"] + B["lat_max"]) / 2
KX = math.cos(math.radians(LAT0))          # degrees of longitude are shorter up here

MAP_W = 1000.0
span_x = (B["lon_max"] - B["lon_min"]) * KX
span_y = B["lat_max"] - B["lat_min"]
MAP_H = MAP_W * span_y / span_x            # keeps the map to scale


def px(lon):
    return (lon - B["lon_min"]) * KX / span_x * MAP_W


def py(lat):
    return (B["lat_max"] - lat) / span_y * MAP_H


def poly(points):
    return " ".join(f"{px(lon):.1f},{py(lat):.1f}" for lon, lat in points)


# ------------------------------------------------------------------ validation
errors = []
for z in data["zones"]:
    if not (B["lat_min"] <= z["lat"][0] < z["lat"][1] <= B["lat_max"]):
        errors.append(f"{z['id']}: latitude {z['lat']} outside map bounds")
    if not (B["lon_min"] <= z["lon"][0] < z["lon"][1] <= B["lon_max"]):
        errors.append(f"{z['id']}: longitude {z['lon']} outside map bounds")
    if z["tier"] not in tiers:
        errors.append(f"{z['id']}: unknown tier {z['tier']}")
for c in data["cities"]:
    if not (B["lat_min"] <= c["lat"] <= B["lat_max"] and B["lon_min"] <= c["lon"] <= B["lon_max"]):
        errors.append(f"{c['name']}: coordinates outside map bounds")
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------------- map layers
counties = "".join(
    f'<rect x="{px(c["lon"][0]):.1f}" y="{py(c["lat"][1]):.1f}" '
    f'width="{px(c["lon"][1]) - px(c["lon"][0]):.1f}" '
    f'height="{py(c["lat"][0]) - py(c["lat"][1]):.1f}" '
    f'class="county"/>'
    f'<text class="countylab" x="{px(c["lon"][0]) + 8:.1f}" y="{py(c["lat"][1]) + c.get("label_dy", 20):.1f}">'
    f'{esc(c["name"])}</text>'
    for c in data["counties"]
)

river = (
    f'<polyline points="{poly(data["river"])}" class="river"/>'
    f'<text class="riverlab" x="{px(-90.30):.1f}" y="{py(34.78):.1f}">MISSISSIPPI RIVER</text>'
)

roads = "".join(
    f'<polyline points="{poly(r["points"])}" class="road"/>'
    f'<text class="roadlab" x="{max(px(r["points"][0][0]) + 6, 8):.1f}" '
    f'y="{py(r["points"][0][1]) - 6:.1f}">{esc(r["name"])}</text>'
    for r in data["interstates"]
)

state_line = (
    f'<line x1="{px(B["lon_min"]):.1f}" y1="{py(34.9957):.1f}" '
    f'x2="{px(B["lon_max"]):.1f}" y2="{py(34.9957):.1f}" class="stateline"/>'
    f'<text class="statelab" x="{px(-89.40):.1f}" y="{py(34.9957) - 8:.1f}">TENNESSEE</text>'
    f'<text class="statelab" x="{px(-89.40):.1f}" y="{py(34.9957) + 18:.1f}">MISSISSIPPI</text>'
)

zone_boxes = []
for z in data["zones"]:
    color = tiers[z["tier"]]["color"]
    x, y = px(z["lon"][0]), py(z["lat"][1])
    w, h = px(z["lon"][1]) - x, py(z["lat"][0]) - y
    on_table = z["territory"].startswith("DeSoto")
    dash = "" if on_table else ' stroke-dasharray="9 5"'
    zone_boxes.append(
        f'<g class="zone" data-tier="{z["tier"]}" data-zone="{z["id"]}">'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{color}" fill-opacity=".14" stroke="{color}" stroke-width="3"{dash}/>'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="30" height="21" fill="{color}"/>'
        f'<text class="zid" x="{x + 15:.1f}" y="{y + 15:.1f}" text-anchor="middle">{z["id"]}</text>'
        f"</g>"
    )
zone_boxes = "".join(zone_boxes)

cities = "".join(
    f'<g class="city">'
    f'<circle cx="{px(c["lon"]):.1f}" cy="{py(c["lat"]):.1f}" '
    f'r="{3.5 + math.sqrt(c["pop"]) / 90:.1f}" class="dot"/>'
    f'<text class="citylab" x="{px(c["lon"]) + 9:.1f}" y="{py(c["lat"]) + 4:.1f}">'
    f'{esc(c["name"])}</text>'
    f"</g>"
    for c in data["cities"]
)

# scale bar: 10 miles
MILES = 10
deg_lon = MILES / (69.17 * KX)
bar_px = deg_lon * KX / span_x * MAP_W
bx, by = 40, MAP_H - 40
scale_bar = (
    f'<line x1="{bx}" y1="{by}" x2="{bx + bar_px:.1f}" y2="{by}" class="scale"/>'
    f'<line x1="{bx}" y1="{by - 6}" x2="{bx}" y2="{by + 6}" class="scale"/>'
    f'<line x1="{bx + bar_px:.1f}" y1="{by - 6}" x2="{bx + bar_px:.1f}" y2="{by + 6}" class="scale"/>'
    f'<text class="scalelab" x="{bx + bar_px / 2:.1f}" y="{by - 11}" text-anchor="middle">'
    f"{MILES} MILES</text>"
)

map_svg = (
    f'<svg viewBox="0 0 {MAP_W:.0f} {MAP_H:.0f}" role="img" '
    f'aria-label="Memphis metropolitan area zone map">'
    f"{counties}{river}{roads}{state_line}{zone_boxes}{cities}{scale_bar}</svg>"
)

# ------------------------------------------------------------------ zone cards
def money(v):
    return f"${v:,.0f}" if v else "&mdash;"


rows = []
for z in sorted(data["zones"], key=lambda z: z["rank"]):
    color = tiers[z["tier"]]["color"]
    on_table = z["territory"].startswith("DeSoto")
    hhi = (
        money(z["hhi_low"]) if z["hhi_low"] == z["hhi_high"]
        else f'{money(z["hhi_low"])}&ndash;{money(z["hhi_high"])}'
    )
    rows.append(
        f'<article class="zcard" data-tier="{z["tier"]}">'
        f'<header style="border-left-color:{color}">'
        f'<span class="badge" style="background:{color}">{z["id"]}</span>'
        f"<h3>{esc(z['name'])}</h3>"
        f'<span class="tierlab">{esc(tiers[z["tier"]]["label"])}</span></header>'
        f'<p class="anchors">{esc(z["anchors"])}</p>'
        f'<div class="figs">'
        f'<div><b>{z["population"]:,}</b><span>Population</span></div>'
        f"<div><b>{hhi}</b><span>Median household income</span></div>"
        f"</div>"
        f'<p class="terr {"on" if on_table else "off"}">{esc(z["territory"])}</p>'
        f'<p class="why">{esc(z["why"])}</p>'
        f'<p class="verdict">{esc(z["verdict"])}</p>'
        f"</article>"
    )
zone_cards = "".join(rows)

on_table_pop = sum(z["population"] for z in data["zones"] if z["territory"].startswith("DeSoto"))
tier_a_pop = sum(z["population"] for z in data["zones"] if z["tier"] == "A")
tn_a_pop = sum(
    z["population"] for z in data["zones"]
    if z["tier"] == "A" and not z["territory"].startswith("DeSoto")
)

CSS = """
  :root { --navy:#1B1F3B; --gold:#C5A55A; --bg:#f7f7f9; --card:#fff; --text:#1a1a1a;
          --muted:#5d616b; --line:#e3e3e8; --land:#eceef2; --water:#c9d6e2; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36;
            --land:#1b212a; --water:#233243; }
  }
  :root[data-theme="dark"] { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6;
                             --line:#2a2f36; --land:#1b212a; --water:#233243; }
  :root[data-theme="light"] { --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#5d616b;
                              --line:#e3e3e8; --land:#eceef2; --water:#c9d6e2; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.55; }
  header.top { background:var(--navy); color:#fff; padding:34px 24px; border-bottom:5px solid var(--gold); }
  header.top h1 { margin:0 0 6px; font-size:27px; text-wrap:balance; }
  header.top p { margin:0; color:#c9cbd6; font-size:14px; }
  .badge-int { display:inline-block; margin-top:12px; background:#C4576B; color:#fff; font-size:11px;
               letter-spacing:.8px; text-transform:uppercase; padding:4px 10px; font-weight:bold; }
  .wrap { max-width:1180px; margin:0 auto; padding:24px; }
  h2 { font-size:19px; margin:34px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--gold);
       text-wrap:balance; }
  .stats { display:flex; flex-wrap:wrap; gap:12px; margin:0 0 18px; }
  .stat { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
          padding:11px 15px; min-width:150px; }
  .stat b { display:block; font-size:21px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .stat span { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .mapbox { background:var(--card); border:1px solid var(--line); padding:10px; margin-bottom:14px;
            overflow-x:auto; }
  .mapbox svg { display:block; width:100%; min-width:660px; height:auto; }
  .county { fill:var(--land); stroke:var(--muted); stroke-width:1; stroke-dasharray:3 3;
            fill-opacity:.75; }
  .countylab { font:bold 11px Arial,sans-serif; fill:var(--muted); letter-spacing:.7px; }
  .river { fill:none; stroke:var(--water); stroke-width:9; stroke-linecap:round;
           stroke-linejoin:round; }
  .riverlab { font:italic 11px Arial,sans-serif; fill:var(--water); }
  .road { fill:none; stroke:#7d8797; stroke-width:2.5; stroke-linejoin:round; opacity:.9; }
  .roadlab { font:bold 10.5px Arial,sans-serif; fill:#7d8797; }
  .stateline { stroke:#C4576B; stroke-width:2; stroke-dasharray:8 5; }
  .statelab { font:bold 11px Arial,sans-serif; fill:#C4576B; letter-spacing:1.4px; }
  .zid { font:bold 12px Arial,sans-serif; fill:#fff; }
  .dot { fill:var(--text); stroke:var(--card); stroke-width:1.5; }
  .citylab { font:bold 11.5px Arial,sans-serif; fill:var(--text);
             paint-order:stroke fill; stroke:var(--card); stroke-width:3px; stroke-linejoin:round; }
  .scale { stroke:var(--muted); stroke-width:2; }
  .scalelab { font:bold 10px Arial,sans-serif; fill:var(--muted); letter-spacing:.6px; }
  .zone.dim, .zcard.dim { display:none; }
  .legend { display:flex; flex-wrap:wrap; gap:15px; font-size:12px; color:var(--muted);
            margin-bottom:20px; align-items:center; }
  .legend i { display:inline-block; width:13px; height:13px; margin-right:5px; vertical-align:-2px; }
  .filters { display:flex; gap:8px; flex-wrap:wrap; margin:0 0 18px; }
  .filters button { font:inherit; font-size:13px; padding:8px 16px; cursor:pointer;
    background:var(--card); color:var(--text); border:1px solid var(--line); }
  .filters button[aria-pressed="true"] { background:var(--navy); color:#fff; border-color:var(--navy); }
  .filters button:focus-visible { outline:3px solid var(--gold); outline-offset:2px; }
  .zones { display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:15px; }
  .zcard { background:var(--card); border:1px solid var(--line); padding:0 0 15px; }
  .zcard header { display:flex; align-items:center; gap:9px; border-left:5px solid var(--gold);
                  padding:13px 15px 9px; }
  .zcard h3 { margin:0; font-size:16px; flex:1; }
  .badge { color:#fff; font:bold 11px Arial,sans-serif; padding:3px 7px; }
  .tierlab { font-size:10px; text-transform:uppercase; letter-spacing:.7px; color:var(--muted); }
  .zcard p { margin:0 15px 9px; }
  .anchors { font-size:12.5px; color:var(--muted); }
  .figs { display:flex; gap:20px; margin:0 15px 11px; }
  .figs b { display:block; font-size:17px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .figs span { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }
  .terr { font-size:11px; font-weight:bold; padding:4px 9px; display:inline-block;
          margin-bottom:10px !important; }
  .terr.on { background:rgba(79,138,87,.16); color:#4F8A57; }
  .terr.off { background:rgba(196,87,107,.16); color:#C4576B; }
  .why { font-size:13px; }
  .verdict { font-size:13px; font-weight:bold; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
             padding:15px 19px; font-size:13.5px; margin-bottom:18px; }
  .callout b { color:var(--gold); }
  .callout.gap { border-left-color:#C4576B; }
  .tablewrap { overflow-x:auto; margin-bottom:18px; }
  table { border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
          font-size:13px; min-width:520px; }
  th,td { padding:9px 13px; border-bottom:1px solid var(--line); text-align:left; }
  td + td { font-variant-numeric:tabular-nums; }
  th { background:var(--navy); color:#fff; font-size:11px; text-transform:uppercase;
       letter-spacing:.6px; }
  tr:last-child td { border-bottom:none; }
  footer { padding:30px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

income_rows = "".join(
    f"<tr><td><b>{esc(c['name'])}</b></td><td>{c['pop']:,}</td>"
    f"<td>{money(c['hhi'])}</td></tr>"
    for c in sorted(
        [c for c in data["cities"] if c["hhi"]], key=lambda c: -c["hhi"]
    )
)

body_html = f"""<header class="top">
  <h1>Memphis Metro &mdash; Where the Money Actually Is</h1>
  <p>Zone map for MCTV Elite Advertising &middot; metro population {meta['metro_population']}
     ({meta['metro_rank']}) &middot; updated {meta['updated']}</p>
  <span class="badge-int">Internal &mdash; not for n-Compass</span>
</header>
<div class="wrap">

  <div class="stats">
    <div class="stat"><b>{meta['metro_population']}</b><span>Metro population</span></div>
    <div class="stat"><b>{tier_a_pop:,}</b><span>Tier A zones</span></div>
    <div class="stat"><b>{on_table_pop:,}</b><span>On the table (DeSoto)</span></div>
    <div class="stat"><b>{tn_a_pop:,}</b><span>Tier A NOT on the table</span></div>
    <div class="stat"><b>$149,920</b><span>Top zone income</span></div>
  </div>

  <div class="callout gap">
    <b>Read this before the map.</b> Only the two solid-outlined zones &mdash; DeSoto County &mdash;
    are what Don offered. Everything drawn with a <b>dashed outline sits in Tennessee or Arkansas
    and is a separate n-Compass territory</b> that is very likely already held by someone else.
    n-Compass sells protected territories for a $35,000 franchise fee and claims coverage in 250+
    cities, so Memphis proper is unlikely to be sitting empty. This map shows where the value is,
    not what is available &mdash; those are different questions, and the second one is a question
    for Don.
  </div>

  <h2>The map</h2>
  <div class="legend">
    <span><i style="background:{tiers['A']['color']}"></i>Tier A &mdash; primary target</span>
    <span><i style="background:{tiers['B']['color']}"></i>Tier B &mdash; secondary</span>
    <span><i style="background:{tiers['C']['color']}"></i>Tier C &mdash; watch</span>
    <span><i style="background:{tiers['D']['color']}"></i>Tier D &mdash; avoid</span>
    <span>&mdash; solid box = DeSoto (offered) &middot; dashed box = separate territory</span>
  </div>
  <div class="mapbox">{map_svg}</div>

  <div class="callout">
    <b>To scale.</b> {esc(meta['projection_note'])} City dot size scales with population.
  </div>

  <h2>The number that changes the argument</h2>
  <div class="callout">
    DeSoto County's <b>$85,500</b> median household income is the highest in Mississippi, and it is
    the reason to take the territory. But it is <b>not</b> the highest in this metro &mdash; it is
    not close. Germantown is <b>$149,920</b>, Collierville <b>$134,319</b>, Arlington
    <b>$135,105</b>. The wealthiest ground within 20 miles of the DeSoto line is on the Tennessee
    side, and it is not ours to take today.
  </div>

  <div class="tablewrap"><table>
    <tr><th>City</th><th>Population</th><th>Median household income</th></tr>
    {income_rows}
  </table></div>

  <h2>Zones, ranked</h2>
  <div class="filters">
    <button data-filter="all" aria-pressed="true">All zones</button>
    <button data-filter="A" aria-pressed="false">Tier A</button>
    <button data-filter="B" aria-pressed="false">Tier B</button>
    <button data-filter="C" aria-pressed="false">Tier C</button>
    <button data-filter="D" aria-pressed="false">Tier D</button>
  </div>
  <div class="zones">{zone_cards}</div>

  <h2>What this means for the Don conversation</h2>
  <div class="callout">
    Taking DeSoto is still right &mdash; it is the best advertiser market in Mississippi and it is
    being offered. But this map reframes the ask. <b>Olive Branch (Z4) borders the money crescent
    (Z1).</b> An Olive Branch advertiser is already selling to Germantown and Collierville
    households, because a county line is not a shopping boundary. That makes Olive Branch worth
    more than its own 47,819 residents suggest.
    <br><br>
    So add a fourth question for Don: <b>who holds Shelby County, and is any of it available or
    coming available?</b> If the answer is &ldquo;nobody&rdquo; or &ldquo;someone who is
    struggling,&rdquo; that is a far bigger conversation than DeSoto &mdash; roughly
    {tn_a_pop:,} people in Tier A Tennessee zones at incomes well above anything in our
    current network.
  </div>

  <div class="callout gap">
    <b>One correction to the earlier brief.</b> It cited BlueOval City as a growth driver for the
    region. Ford and SK On dissolved their joint venture and production dates have slipped, and
    West Tennessee counties are now underperforming their projections &mdash; Tipton is flat at
    -0.03%/yr. The Marshall County jobs story (Jabil, Amazon, Baxter) is real and unaffected;
    the BlueOval halo is not something to lean on.
  </div>

</div>
<footer>MCTV Digital, Inc. &mdash; internal planning document. Generated from metro_zones.json.</footer>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const targets = document.querySelectorAll('.zone, .zcard');
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    const f = btn.dataset.filter;
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    targets.forEach(el => el.classList.toggle('dim', !(f === 'all' || el.dataset.tier === f)));
  }}));
</script>
"""

html = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
    + body_html + "</body>\n</html>\n"
)
artifact_html = f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n" + body_html

with open(f"{OUT}/metro-map.html", "w") as f:
    f.write(html)
with open(f"{OUT}/metro-map.artifact.html", "w") as f:
    f.write(artifact_html)

print(f"metro-map.html written: {len(data['zones'])} zones, {len(data['cities'])} cities, "
      f"{len(html):,} bytes")
print(f"  map {MAP_W:.0f}x{MAP_H:.0f} px, cos-lat factor {KX:.4f} at {LAT0:.2f}N")
print(f"  tier A total {tier_a_pop:,} | on the table {on_table_pop:,} | "
      f"tier A not on the table {tn_a_pop:,}")
