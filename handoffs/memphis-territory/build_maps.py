#!/usr/bin/env python3
"""Render the DeSoto/Tupelo strategic market maps from markets.json.

Mirrors handoffs/rafters-oxford/build_contactsheet.py — stdlib only, MCTV branding,
self-contained output (no external requests).
"""

import json
import sys

ROOT = "/home/user/mctv-bot"
OUT = f"{ROOT}/handoffs/memphis-territory"

NAVY, GOLD = "#1B1F3B", "#C5A55A"
PAGE_TITLE = ("MCTV &mdash; Strategic Market Maps: DeSoto Expansion "
              "+ Tupelo Densification")

# Phase palette. Phase 0 = Tupelo densification (parallel track, no territory grant).
PHASE_COLOR = {0: "#4F8A57", 1: GOLD, 2: "#4A7C9B", 3: "#8A8FA3"}
PHASE_LABEL = {
    0: "Tupelo densification",
    1: "Phase 1",
    2: "Phase 2",
    3: "Phase 3",
}

ROAD_STYLE = {
    "interstate": ("#5A6A8A", 7, ""),
    "arterial": (GOLD, 5, ""),
    "highway": ("#9AA0B0", 3, ""),
    "border": ("#C4576B", 2, "6 5"),
}

CONTESTED = {"assumed contested"}
UNKNOWN = {"unknown"}


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


data = json.load(open(f"{OUT}/markets.json"))
config = json.load(open(f"{ROOT}/config/config.json"))

tiers = config["pricing"]["elite_tiers"]
valid_categories = set(config["venue_categories"])
existing_network = sum(m["screens"] for m in config["markets"].values())

meta = data["meta"]
markets = data["markets"]

# ---------------------------------------------------------------- validation
errors = []

for m in markets:
    node_sum = sum(n["screens"] for n in m["nodes"])
    if node_sum != m["target"]:
        errors.append(f"{m['name']}: nodes sum to {node_sum}, target is {m['target']}")
    for n in m["nodes"]:
        for c in n["categories"]:
            if c not in valid_categories:
                errors.append(f"{m['name']} / {n['name']}: '{c}' not in config venue_categories")

desoto = [m for m in markets if m["phase"] > 0]
cumulative = 0
for phase in (1, 2, 3):
    cumulative += sum(m["target"] for m in desoto if m["phase"] == phase)
    expected = meta["phase_targets"][str(phase)]["cumulative"]
    if cumulative != expected:
        errors.append(f"Phase {phase} cumulative is {cumulative}, expected {expected}")

if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

desoto_total = sum(m["target"] for m in desoto)
tupelo = next(m for m in markets if m["id"] == "tupelo")


# ------------------------------------------------------------------- svg bits
def road_svg(r, obstacles, width_px):
    """Draw a road, labelling it at whichever point along it sits farthest from any node.

    Anchoring every label to the polyline's end put road names straight through the
    nodes that cluster at corridor intersections, which is exactly where nodes live.
    """
    color, stroke, dash = ROAD_STYLE[r["kind"]]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    pts = [tuple(map(float, p.split(","))) for p in r["points"].split()]

    # Candidates: every vertex plus interpolated points along each segment.
    candidates = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for t in (0.0, 0.2, 0.35, 0.5, 0.65, 0.8):
            candidates.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    candidates.append(pts[-1])

    def clearance(pt):
        x, y = pt
        # Keep labels off the extreme edges so long names don't run out of the viewBox.
        if x < width_px * 0.06 or x > width_px * 0.94:
            return -1
        if not obstacles:
            return 1e9
        return min((x - ox) ** 2 + (y - oy) ** 2 for ox, oy, _ in obstacles)

    lx, ly = max(candidates, key=clearance)
    anchor = "end" if lx > width_px * 0.72 else "start" if lx < width_px * 0.28 else "middle"
    svg = (
        f'<polyline points="{r["points"]}" fill="none" stroke="{color}" stroke-width="{stroke}"'
        f'{dash_attr} stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>'
        f'<text class="roadlab" x="{lx:.0f}" y="{ly - 11:.0f}" text-anchor="{anchor}">{esc(r["name"])}</text>'
    )
    # Report where the label landed so later roads treat it as an obstacle too —
    # otherwise parallel corridors stack their names on top of each other.
    return svg, (lx, ly - 11, 34)


def roads_svg(roads, obstacles, width_px):
    obs = list(obstacles)
    out = []
    for r in roads:
        svg, placed = road_svg(r, obs, width_px)
        out.append(svg)
        obs.append(placed)
    return "".join(out)


def node_svg(n, idx):
    r = 13 + n["screens"] * 1.15
    color = PHASE_COLOR[n["phase"]]
    status = n["competitive_status"]
    if status in CONTESTED:
        ring = f' stroke="#C4576B" stroke-width="3.5" stroke-dasharray="5 4"'
    elif status in UNKNOWN:
        ring = f' stroke="#8A8FA3" stroke-width="2.5" stroke-dasharray="2 4"'
    else:
        ring = ' stroke="#ffffff" stroke-width="2.5"'
    label_y = n["y"] + r + 17
    return (
        f'<g class="node" data-phase="{n["phase"]}" data-idx="{idx}">'
        f'<circle cx="{n["x"]}" cy="{n["y"]}" r="{r:.1f}" fill="{color}"{ring} opacity=".92"/>'
        f'<text class="nodenum" x="{n["x"]}" y="{n["y"] + 6}" text-anchor="middle">{n["screens"]}</text>'
        f'<text class="nodelab" x="{n["x"]}" y="{label_y}" text-anchor="middle">{esc(n["name"])}</text>'
        f"</g>"
    )


def city_svg(c):
    r = 11 + c["screens"] * 0.55
    color = PHASE_COLOR.get(c["phase"], "#8A8FA3")
    dim = ' opacity=".45"' if c["screens"] == 0 else ' opacity=".92"'
    screens = f'{c["screens"]}' if c["screens"] else "—"
    return (
        f'<g class="node" data-phase="{c["phase"]}">'
        f'<circle cx="{c["x"]}" cy="{c["y"]}" r="{r:.1f}" fill="{color}" stroke="#fff" stroke-width="2.5"{dim}/>'
        f'<text class="nodenum" x="{c["x"]}" y="{c["y"] + 5}" text-anchor="middle">{screens}</text>'
        f'<text class="nodelab" x="{c["x"]}" y="{c["y"] + r + 16:.0f}" text-anchor="middle">{esc(c["name"])}</text>'
        f'<text class="nodesub" x="{c["x"]}" y="{c["y"] + r + 30:.0f}" text-anchor="middle">{esc(c["pop"])}</text>'
        f"</g>"
    )


def vb_width(viewbox):
    return float(viewbox.split()[2])


def obstacles_for(items, radius_fn):
    """Node circles plus the label block beneath them — roads should dodge both."""
    out = []
    for it in items:
        r = radius_fn(it)
        out.append((it["x"], it["y"], r))
        out.append((it["x"], it["y"] + r + 22, 16))
    return out


# --------------------------------------------------------------- county map
ov = data["county_overview"]
ov_w = vb_width(ov["viewBox"])
ov_obs = obstacles_for(ov["cities"], lambda c: 11 + c["screens"] * 0.55)
county_svg = (
    f'<svg viewBox="{ov["viewBox"]}" role="img" aria-label="DeSoto County corridor overview">'
    + roads_svg(ov["roads"], ov_obs, ov_w)
    + "".join(city_svg(c) for c in ov["cities"])
    + "</svg>"
)

# --------------------------------------------------------------- tier ladder
LADDER_MAX = 100
tier_marks = "".join(
    f'<div class="tick" style="left:{min(t["screens"], LADDER_MAX) / LADDER_MAX * 100:.1f}%">'
    f'<span class="tickline"></span>'
    f'<span class="ticklab"><b>{t["screens"]}</b> ${t["monthly_rate"]:,.0f}/mo</span>'
    f"</div>"
    for t in tiers
)
phase_bars = "".join(
    f'<div class="pbar" style="width:{meta["phase_targets"][str(p)]["cumulative"] / LADDER_MAX * 100:.1f}%;'
    f'background:{PHASE_COLOR[p]};z-index:{4 - p}">'
    f'<span>{PHASE_LABEL[p]} &middot; {meta["phase_targets"][str(p)]["cumulative"]}</span></div>'
    for p in (3, 2, 1)
)

# ------------------------------------------------------------- market blocks
def market_block(m):
    m_w = vb_width(m["viewBox"])
    m_obs = obstacles_for(m["nodes"], lambda n: 13 + n["screens"] * 1.15)
    svg = (
        f'<svg viewBox="{m["viewBox"]}" role="img" aria-label="{esc(m["name"])} corridor map">'
        + roads_svg(m["roads"], m_obs, m_w)
        + "".join(node_svg(n, i) for i, n in enumerate(m["nodes"]))
        + "</svg>"
    )

    cards = []
    for n in m["nodes"]:
        chips = "".join(f'<span class="chip">{esc(c)}</span>' for c in n["categories"])
        anchors = " &middot; ".join(esc(a) for a in n["anchors"])
        status = n["competitive_status"]
        scls = (
            "contested" if status in CONTESTED
            else "unknown" if status in UNKNOWN
            else "clear"
        )
        cards.append(
            f'<article class="node-card" data-phase="{n["phase"]}">'
            f'<header><span class="dot" style="background:{PHASE_COLOR[n["phase"]]}"></span>'
            f'<h4>{esc(n["name"])}</h4><b class="cnt">{n["screens"]}</b></header>'
            f'<p class="geo">{esc(n["geography"])}</p>'
            f'<p class="anchors">{anchors}</p>'
            f'<div class="chips">{chips}</div>'
            f'<p class="note">{esc(n["note"])}</p>'
            f'<span class="status {scls}">{esc(status)}</span>'
            f"</article>"
        )

    existing = (
        f'<div class="stat"><b>{m["existing"]}</b><span>Screens today</span></div>'
        if "existing" in m
        else ""
    )
    total_after = (
        f'<div class="stat"><b>{m["existing"] + m["target"]}</b><span>After build</span></div>'
        if "existing" in m
        else ""
    )

    return (
        f'<section class="market" id="{m["id"]}">'
        f'<div class="mhead" style="border-left-color:{PHASE_COLOR[m["phase"]]}">'
        f'<h3>{esc(m["name"])}</h3>'
        f'<p class="rank">{esc(m["rank"])} &middot; pop {esc(m["population"])} &middot; {esc(m["stat"])}</p>'
        f"</div>"
        f'<div class="stats">'
        f'<div class="stat"><b>{m["target"]}</b><span>Screen target</span></div>'
        f"{existing}{total_after}"
        f'<div class="stat"><b>{len(m["nodes"])}</b><span>Nodes</span></div>'
        f"</div>"
        f'<p class="why">{esc(m["why"])}</p>'
        f'<div class="mapbox">{svg}</div>'
        f'<div class="nodes">{"".join(cards)}</div>'
        f"</section>"
    )


market_blocks = "".join(market_block(m) for m in markets)

nav = "".join(
    f'<a href="#{m["id"]}">{esc(m["name"])} <b>{m["target"]}</b></a>' for m in markets
)

CSS = """
  :root { --navy:#1B1F3B; --gold:#C5A55A; --bg:#f7f7f9; --card:#fff; --text:#1a1a1a;
          --muted:#666; --line:#e3e3e8; --chip:#eff0f4; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36;
            --chip:#21262d; }
  }
  :root[data-theme="dark"] { --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6;
                             --line:#2a2f36; --chip:#21262d; }
  :root[data-theme="light"] { --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#666;
                              --line:#e3e3e8; --chip:#eff0f4; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text);
         line-height:1.55; }
  header.top { background:var(--navy); color:#fff; padding:34px 24px; border-bottom:5px solid var(--gold); }
  header.top h1 { margin:0 0 6px; font-size:26px; letter-spacing:.3px; }
  header.top p { margin:0; color:#c9cbd6; font-size:14px; }
  .badge { display:inline-block; margin-top:12px; background:#C4576B; color:#fff; font-size:11px;
           letter-spacing:.8px; text-transform:uppercase; padding:4px 10px; font-weight:bold; }
  .wrap { max-width:1180px; margin:0 auto; padding:24px; }
  h2 { font-size:19px; margin:34px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--gold);
       text-wrap:balance; }
  .stats { display:flex; flex-wrap:wrap; gap:12px; margin:0 0 18px; }
  .stat { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
          padding:11px 15px; min-width:132px; }
  .stat b { display:block; font-size:21px; color:var(--gold); font-variant-numeric:tabular-nums; }
  .stat span { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .nav { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px; }
  .nav a { text-decoration:none; font-size:13px; padding:7px 13px; background:var(--card);
           border:1px solid var(--line); color:var(--text); }
  .nav a b { color:var(--gold); }
  .filters { display:flex; gap:8px; flex-wrap:wrap; margin:0 0 18px; }
  .filters button { font:inherit; font-size:13px; padding:8px 16px; cursor:pointer;
    background:var(--card); color:var(--text); border:1px solid var(--line); }
  .filters button[aria-pressed="true"] { background:var(--navy); color:#fff; border-color:var(--navy); }
  .filters button:focus-visible, .nav a:focus-visible { outline:3px solid var(--gold);
    outline-offset:2px; }
  .mapbox { background:var(--card); border:1px solid var(--line); padding:10px; margin-bottom:18px;
            overflow-x:auto; }
  .mapbox svg { display:block; width:100%; min-width:600px; height:auto; }
  /* Halo so labels stay readable where they cross a road line. Stroke is painted
     under the fill and picks up the card background, so it works in both themes. */
  .roadlab, .nodelab, .nodesub {
    paint-order:stroke fill; stroke:var(--card); stroke-width:3.5px; stroke-linejoin:round;
  }
  .roadlab { font:600 11px Arial,sans-serif; fill:var(--muted); letter-spacing:.4px; }
  .nodenum { font:bold 13px Arial,sans-serif; fill:#fff; }
  .nodelab { font:bold 12px Arial,sans-serif; fill:var(--text); }
  .nodesub { font:11px Arial,sans-serif; fill:var(--muted); }
  .node.dim { opacity:.13; }
  .mhead { border-left:5px solid var(--gold); padding:2px 0 2px 14px; margin:0 0 14px; }
  .mhead h3 { margin:0; font-size:21px; }
  .mhead .rank { margin:3px 0 0; font-size:13px; color:var(--muted); }
  .why { font-size:14px; margin:0 0 16px; max-width:78ch; }
  .market { margin-bottom:52px; }
  .nodes { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
  .node-card { background:var(--card); border:1px solid var(--line); padding:14px 16px; }
  .node-card.dim { display:none; }
  .node-card header { display:flex; align-items:center; gap:8px; margin-bottom:7px; }
  .node-card h4 { margin:0; font-size:15px; flex:1; }
  .node-card .cnt { color:var(--gold); font-size:19px; font-variant-numeric:tabular-nums; }
  .dot { width:11px; height:11px; border-radius:50%; flex:none; }
  .geo { margin:0 0 5px; font-size:12px; color:var(--muted); }
  .anchors { margin:0 0 9px; font-size:12px; }
  .chips { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:9px; }
  .chip { background:var(--chip); font-size:10.5px; padding:3px 8px; color:var(--muted);
          letter-spacing:.2px; }
  .note { margin:0 0 9px; font-size:13px; }
  .status { font-size:10px; text-transform:uppercase; letter-spacing:.7px; padding:3px 8px;
            display:inline-block; font-weight:bold; }
  .status.clear { background:rgba(79,138,87,.16); color:#4F8A57; }
  .status.contested { background:rgba(196,87,107,.16); color:#C4576B; }
  .status.unknown { background:rgba(138,143,163,.18); color:#8A8FA3; }
  .ladder { background:var(--card); border:1px solid var(--line); padding:26px 22px 16px;
            margin-bottom:16px; position:relative; }
  .track { position:relative; height:104px; }
  .pbar { position:absolute; left:0; height:30px; top:0; display:flex; align-items:center;
          padding-left:11px; color:#fff; font-size:12px; font-weight:bold;
          font-variant-numeric:tabular-nums; }
  .pbar:nth-child(2) { top:34px; }
  .pbar:nth-child(3) { top:68px; }
  .tick { position:absolute; top:-14px; bottom:0; }
  .tickline { position:absolute; top:0; bottom:0; width:2px; background:var(--muted); opacity:.5; }
  .ticklab { position:absolute; top:-16px; left:4px; font-size:10.5px; color:var(--muted);
             white-space:nowrap; }
  .ticklab b { color:var(--text); font-variant-numeric:tabular-nums; }
  .legend { display:flex; flex-wrap:wrap; gap:16px; font-size:12px; color:var(--muted);
            margin-bottom:20px; align-items:center; }
  .legend i { display:inline-block; width:13px; height:13px; border-radius:50%; margin-right:5px;
              vertical-align:-2px; }
  .callout { background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
             padding:15px 19px; font-size:13.5px; margin-bottom:20px; }
  .callout b { color:var(--gold); }
  .gap { border-left-color:#C4576B; }
  .tablewrap { overflow-x:auto; margin-bottom:18px; }
  table { border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
          font-size:13px; min-width:420px; }
  td + td, th + th { font-variant-numeric:tabular-nums; }
  th,td { padding:9px 13px; border-bottom:1px solid var(--line); text-align:left; }
  th { background:var(--navy); color:#fff; font-size:11px; text-transform:uppercase;
       letter-spacing:.6px; }
  tr:last-child td { border-bottom:none; }
  footer { padding:30px 24px; text-align:center; color:var(--muted); font-size:12px; }
"""

tier_rows = "".join(
    f'<tr><td><b>{t["screens"]} screens</b></td><td>${t["monthly_rate"]:,.0f}/mo</td>'
    f'<td>${t["cost_per_screen"]:.2f}</td><td>{t["plays_per_month"]}</td></tr>'
    for t in tiers
)

body_html = f"""
<header class="top">
  <h1>Strategic Market Maps</h1>
  <p>Memphis / DeSoto County expansion &middot; Tupelo densification &middot;
     MCTV Elite Advertising &middot; updated {meta['updated']}</p>
  <span class="badge">Internal &mdash; not for n-Compass</span>
</header>
<div class="wrap">

  <div class="stats">
    <div class="stat"><b>{desoto_total}</b><span>DeSoto target</span></div>
    <div class="stat"><b>+{tupelo['target']}</b><span>Tupelo densification</span></div>
    <div class="stat"><b>{existing_network}</b><span>Network today</span></div>
    <div class="stat"><b>{existing_network + desoto_total + tupelo['target']}</b><span>Network after</span></div>
    <div class="stat"><b>{sum(len(m['nodes']) for m in markets)}</b><span>Nodes mapped</span></div>
  </div>

  <div class="nav">{nav}</div>

  <div class="callout">
    <b>Screens sell by node, not by city.</b> A node is a commercial cluster tight enough that one
    rep can walk it and one advertiser buy feels local. Every target below is a node, sized to the
    venues that actually exist there. Circle size = screen count; color = phase.
  </div>

  <h2>Phase lines sit on pricing tiers</h2>

  <div class="callout">
    Our rate card charges by screen count, so a phase that ends <i>between</i> tiers means screens we
    hang but cannot bill. Phase 1 ends at <b>40</b> and Phase 2 at <b>75</b> &mdash; exactly on the
    $800 and $1,300 thresholds &mdash; so a DeSoto-only advertiser buy unlocks the top tier a full
    phase earlier than the original ranges allowed. Phase 3 adds headroom above 75 for sell-through.
  </div>

  <div class="ladder">
    <div class="track">
      {phase_bars}
      {tier_marks}
    </div>
  </div>

  <div class="tablewrap"><table>
    <tr><th>Tier</th><th>Monthly</th><th>Cost / screen</th><th>Plays / month</th></tr>
    {tier_rows}
  </table></div>

  <h2>DeSoto County &mdash; corridor overview</h2>
  <div class="legend">
    <span><i style="background:{PHASE_COLOR[1]}"></i>Phase 1 &mdash; Olive Branch + Hernando</span>
    <span><i style="background:{PHASE_COLOR[2]}"></i>Phase 2 &mdash; Southaven</span>
    <span><i style="background:{PHASE_COLOR[3]}"></i>Phase 3 &mdash; Horn Lake / Walls / Nesbit</span>
    <span><i style="background:{PHASE_COLOR[0]}"></i>Tupelo densification</span>
  </div>
  <div class="mapbox">{county_svg}</div>

  <div class="callout gap">
    <b>Byhalia is on the map but gets no screens.</b> Marshall County has ~3,300 announced jobs
    (Jabil $119M/2,200, Amazon ~1,000, Baxter 105) but Byhalia is a town of 1,417 and Holly Springs
    is shrinking at -1.83%/yr. Those workers commute in and spend in DeSoto. Take the territory
    rights on paper; place the hardware on the <b>Craft Rd / I-22</b> node in Olive Branch, which is
    where that money actually lands.
  </div>

  <h2>Markets</h2>
  <div class="filters">
    <button data-filter="all" aria-pressed="true">All phases</button>
    <button data-filter="1" aria-pressed="false">Phase 1 &mdash; 40</button>
    <button data-filter="2" aria-pressed="false">Phase 2 &mdash; 75</button>
    <button data-filter="3" aria-pressed="false">Phase 3 &mdash; 90</button>
    <button data-filter="0" aria-pressed="false">Tupelo</button>
  </div>

  {market_blocks}

  <h2>Competitive overlay &mdash; the gap in this map</h2>
  <div class="callout gap">
    Node flags marked <b>assumed contested</b> or <b>unknown</b> are exactly that &mdash; assumptions.
    We know the incumbent (Desoto Local, Inc., an N-Compass&ndash;NTV360 dealer) but not which venues
    they hold, how many licenses, or when contracts expire, and it is not publicly discoverable.
    The working assumption is that a small operator building DeSoto started in <b>Southaven</b> and
    worked outward along Goodman Road &mdash; which is why Olive Branch and Hernando go first.
    <br><br>
    <b>The NTV360 license export from n-Compass closes this in one file.</b> Every flag on this page
    gets re-cut the moment it lands.
  </div>

  <div class="callout">
    <b>Schematic, not to scale.</b> {esc(meta['schematic_notice'])}
  </div>

</div>
<footer>MCTV Digital, Inc. &mdash; internal planning document. Generated from markets.json.</footer>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const nodes = document.querySelectorAll('.node');
  const cards = document.querySelectorAll('.node-card');
  const markets = document.querySelectorAll('.market');
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    const f = btn.dataset.filter;
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    const show = el => {{
      const on = (f === 'all' || el.dataset.phase === f);
      el.classList.toggle('dim', !on);
      return on;
    }};
    nodes.forEach(show);
    cards.forEach(show);
    markets.forEach(m => {{
      const any = [...m.querySelectorAll('.node-card')].some(c => !c.classList.contains('dim'));
      m.style.display = any ? '' : 'none';
    }});
  }}));
</script>
"""

# Full standalone document for the repo.
html = (
    "<!doctype html>\n<html lang=\"en\">\n<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    f"<title>{PAGE_TITLE}</title>\n"
    f"<style>{CSS}</style>\n</head>\n<body>\n"
    + body_html
    + "</body>\n</html>\n"
)

# Artifact fragment: the publisher supplies doctype/head/body, so emit only the
# style block, the page content, and the script.
artifact_html = f"<title>{PAGE_TITLE}</title>\n<style>{CSS}</style>\n" + body_html


with open(f"{OUT}/market-maps.html", "w") as f:
    f.write(html)
with open(f"{OUT}/market-maps.artifact.html", "w") as f:
    f.write(artifact_html)

node_count = sum(len(m["nodes"]) for m in markets)
print(f"market-maps.html written: {len(markets)} markets, {node_count} nodes, {len(html):,} bytes")
print(f"  DeSoto target {desoto_total} (phases 40/75/90) + Tupelo +{tupelo['target']}")
print(f"  network {existing_network} -> {existing_network + desoto_total + tupelo['target']}")
