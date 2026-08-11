# HOTWORX Oxford — Advertiser Pitch (August 2026)

Proposal package for the HOTWORX Oxford lead (Alyssa Farrell, submitted via the
intake form 2026-08-10, lead id `20260810_190123`).

## Contents

- `HOTWORX-Advertiser-Pitch.pdf` — the deliverable. 10 slides, 1920×1080 (16:9), same
  deck format as the Oxford Conference Center pitch. Supports `?print=1` book mode
  (11×6.5in imposition) like the OCC deck.
- `HOTWORX-Advertiser-Pitch.html` — the source document. Self-contained except for
  the `assets/` folder next to it. Re-render after edits with:

  ```
  chromium --headless --no-sandbox --print-to-pdf=HOTWORX-Advertiser-Pitch.pdf \
      --no-pdf-header-footer "file://$PWD/HOTWORX-Advertiser-Pitch.html"
  ```

- `assets/img/` — curated photos: HOTWORX creative and sauna photography recovered
  from the April 2025 Canva deck ("HOTWORX PROPOSAL", design `DAGl8P_REjw`),
  MCTV in-the-wild venue shots, brands wall, team headshots, logos.
- `assets/fonts/` — Playfair Display + Work Sans variable TTFs (SIL OFL, from the
  Google Fonts repo). TTF on purpose: woff2 makes Chrome embed Type3 fonts in
  print PDFs.

## Design

Built on the **actual OCC deck chassis** (`reference/OCC-Advertiser-Pitch.html`,
"MCTV Elite Advertising — deck chassis per Design.md v1.0"): 1920×1080 canvas,
`--u:19.2px` unit system, cream `#FAF6EF` / navy `#00377E` / gold `#C9A227`,
Playfair Display + Work Sans, typographic MCTV wordmark, dash bullets, stat rows,
CPM comparison bars, price cards, photographic cover with dual scrims, dark navy
bookends. CSS lifted verbatim from the OCC pitch; only content differs.

## Facts baked into the copy (verified against `config/config.json`)

- Network: 125+ screens, 1.9M+ monthly impressions, 55-min average dwell,
  4 plays/hour on a 15-minute loop, 12 hrs/day. Oxford market: 75 screens.
- Pricing follows the OCC deck's current rate card (NOT config.json's older
  elite_tiers): 20/$500 · 40/$800 (recommended) · 80/$1,400 · 125+/$2,000 per
  month; $250 one-time ad-creation fee noted as waived (corporate creative ready).
- Team: T. Creed Cannon, Mary Michael Cannon, Swayze Hollingsworth.
- Messaging carried over from the 2025 Canva pitch: "Be seen. Be noticed. Be
  remembered.", unskippable/unpauseable/unblockable, per-location ad-play math.
