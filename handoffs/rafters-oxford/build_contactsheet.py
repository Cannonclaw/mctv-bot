#!/usr/bin/env python3
"""Render the Rafters contact sheet from manifest.json."""

import json

OUT = "/home/user/mctv-bot/handoffs/rafters-oxford"
NAVY, GOLD = "#1B1F3B", "#C5A55A"

meta = json.load(open(f"{OUT}/manifest.json"))
photos = meta["photos"]
sessions = {s["code"]: s for s in meta["sessions"]}

cards = []
for i, p in enumerate(photos, 1):
    cards.append(
        f'<figure class="card" data-session="{p["session"]}">'
        f'<a href="{p["view_url"]}" target="_blank" rel="noopener">'
        f'<img loading="lazy" src="{p["thumbnail_url"]}" alt="{p["filename"]}" '
        f'width="300" height="225">'
        f'</a>'
        f'<figcaption><b>{p["filename"]}</b>'
        f'<span>#{i} &middot; {p["session_label"]} &middot; {p["captured_local_cdt"][11:16]} &middot; {p["mb"]} MB</span>'
        f'<a class="dl" href="{p["download_url"]}">download original</a>'
        f'</figcaption></figure>'
    )

session_rows = "".join(
    f"<tr><td><b>Session {s['code']}</b></td><td>{s['label']}, {s['night']}</td>"
    f"<td>{s['count']} photos</td>"
    f"<td>{s['first_capture_local_cdt'][11:16]} &ndash; {s['last_capture_local_cdt'][11:16]} CDT</td></tr>"
    for s in meta["sessions"]
)

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rafters &mdash; Photo Contact Sheet ({meta['totals']['photo_count']} photos)</title>
<style>
  :root {{ --navy:{NAVY}; --gold:{GOLD}; --bg:#f7f7f9; --card:#fff; --text:#1a1a1a; --muted:#666; --line:#e3e3e8; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0d1117; --card:#161b22; --text:#e6e6e6; --muted:#9aa0a6; --line:#2a2f36; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Arial,Helvetica,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ background:var(--navy); color:#fff; padding:32px 24px; border-bottom:5px solid var(--gold); }}
  header h1 {{ margin:0 0 6px; font-size:26px; letter-spacing:.3px; }}
  header p {{ margin:0; color:#c9cbd6; font-size:14px; }}
  .wrap {{ max-width:1400px; margin:0 auto; padding:24px; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:14px; margin:0 0 22px; }}
  .stat {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--gold);
           padding:12px 16px; min-width:150px; }}
  .stat b {{ display:block; font-size:22px; color:var(--gold); }}
  .stat span {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }}
  table {{ border-collapse:collapse; width:100%; background:var(--card); border:1px solid var(--line);
           margin-bottom:22px; font-size:14px; }}
  td {{ padding:9px 14px; border-bottom:1px solid var(--line); }}
  tr:last-child td {{ border-bottom:none; }}
  .note {{ background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
           padding:14px 18px; font-size:13px; color:var(--muted); margin-bottom:22px; line-height:1.55; }}
  .note a {{ color:var(--gold); }}
  .filters {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px; }}
  .filters button {{ font:inherit; font-size:13px; padding:8px 16px; cursor:pointer;
    background:var(--card); color:var(--text); border:1px solid var(--line); }}
  .filters button[aria-pressed="true"] {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px; }}
  .card {{ margin:0; background:var(--card); border:1px solid var(--line); overflow:hidden; }}
  .card img {{ display:block; width:100%; height:auto; aspect-ratio:4/3; object-fit:cover; background:#222; }}
  .card figcaption {{ padding:9px 11px; font-size:12px; line-height:1.5; }}
  .card figcaption span {{ display:block; color:var(--muted); font-size:11px; }}
  .card .dl {{ display:inline-block; margin-top:5px; color:var(--gold); font-size:11px; }}
  footer {{ padding:28px 24px; text-align:center; color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Rafters Music and Food &mdash; Photo Contact Sheet</h1>
  <p>1006 E Jackson Ave, Oxford, MS 38655 &middot; MCTV Elite Advertising venue partner &middot;
     {meta['totals']['photo_count']} photos, {meta['totals']['total_gb']} GB</p>
</header>
<div class="wrap">

  <div class="stats">
    <div class="stat"><b>{meta['totals']['photo_count']}</b><span>Photos</span></div>
    <div class="stat"><b>{meta['totals']['total_gb']} GB</b><span>Total size</span></div>
    <div class="stat"><b>2</b><span>Shoot nights</span></div>
    <div class="stat"><b>94.6 min</b><span>Avg dwell time</span></div>
    <div class="stat"><b>27.9K</b><span>Monthly impressions</span></div>
  </div>

  <table>{session_rows}</table>

  <div class="note">
    <b>Thumbnails stream directly from Google Drive.</b> The source folder is link-shareable, so this
    page works for anyone with the link &mdash; but it does need an internet connection, and thumbnails
    will not render inside a sandboxed viewer that blocks external images. Open this file in a normal
    browser. Click any thumbnail for the full-resolution original in Drive.<br><br>
    Source folder: <a href="{meta['source']['google_drive_folder']}">{meta['source']['google_drive_folder']}</a>
  </div>

  <div class="filters">
    <button data-filter="all" aria-pressed="true">All ({meta['totals']['photo_count']})</button>
    <button data-filter="A" aria-pressed="false">Session A &mdash; Fri night ({sessions['A']['count']})</button>
    <button data-filter="B" aria-pressed="false">Session B &mdash; Sat night ({sessions['B']['count']})</button>
  </div>

  <div class="grid" id="grid">
    {"".join(cards)}
  </div>
</div>
<footer>MCTV Digital, Inc. &mdash; internal creative handoff. Photos supplied by the venue.</footer>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const cards = document.querySelectorAll('.card');
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    const f = btn.dataset.filter;
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
    cards.forEach(c => {{
      c.style.display = (f === 'all' || c.dataset.session === f) ? '' : 'none';
    }});
  }}));
</script>
</body>
</html>
"""

with open(f"{OUT}/contact-sheet.html", "w") as f:
    f.write(html)

print(f"contact-sheet.html written: {len(cards)} cards, {len(html):,} bytes")
