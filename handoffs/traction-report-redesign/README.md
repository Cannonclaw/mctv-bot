# Advertiser Traction Report — Design Handoff Package

Redesign package for the **advertiser traction report** — the performance document MCTV Elite
Advertising sends to paying advertisers. Packaged for creative handoff.

**7 pages · Letter portrait · generated from `generators/advertiser_report.py` · navy/gold
"original" scheme**

Prompted by a live head-to-head: an advertiser asked for a report on his screens and already
had a competitor's (OnTarget) in hand. Ours has more behind it and does not look like it.

## Start here

1. **`DESIGN-BRIEF.md`** — the competitive situation, what is wrong with the current document,
   the data we have and are not showing, exact brand tokens, the probe-tested list of what the
   rendering pipeline can and cannot build, and what to send back. Read this first.
2. **`current-state/SAMPLE-report-as-it-ships-today.pdf`** — the report as it generates today,
   end to end. **The cover says SAMPLE — DEMO DATA and the play counts are invented.** Venue
   names, traffic, dwell times and impressions are real; plays are not. Do not send it to
   anyone.
3. **`current-state/p*.png`** — page renders for quick reference without opening the PDF:
   - `p1-cover-and-summary.png` — cover + the KPI banner
   - `p2-exec-summary.png` — shows the ~45% empty page
   - `p3-venue-table.png` — the 8-column venue table
   - `p6-analytics.png` — the five charts, including the clipped legends
   - `p7-team.png` — headshot row

## The one-line version

The report can say **"34 screens across 22 venue locations"** where the competitor says
**"17 locations"** — and it currently buries that in one cell of a five-across banner.

## Source of truth

Nothing here is the design system — it is a snapshot of one. The live values come from:

- `services/docx_service.py` — `COLOR_SCHEMES`, every type size, every layout primitive
- `services/chart_service.py` — chart palette and figure sizes (kept in sync by hand, not
  imported from the scheme)
- `generators/advertiser_report.py` — section order and what each one renders
- `config/config.json` — pricing tiers, media comparison, social proof, team
- `data/network_dashboard.json` — the 97 venues, **stamped 2026-02-24 and going stale**

If any of those change, the brief is the thing that goes out of date. Re-read the source rather
than trusting these numbers a year from now.

## Constraints worth knowing before you sketch

The output path is python-docx → .docx → LibreOffice → PDF. That sounds more limiting than it
is: gradients, rounded corners, absolute positioning, full-bleed art, overlapping elements and
rotated text all work and stay vector — all probe-tested, matrix in the brief. Patterns, cell
drop-shadows and web fonts do not.

The brief also argues for building this in **HTML instead**, since `static/rates.html` already
proves the print-quality CSS recipe in this repo and `server_routes.py` is three lines from
serving a `/report` route. That is a decision to make before drawing, not after.
