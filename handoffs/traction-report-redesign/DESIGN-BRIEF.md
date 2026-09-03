# Traction Report Redesign — Design Brief

**Internal only — do not forward.** The report itself (`output/reports/*.docx`, converted to
PDF) is what goes to advertisers; this brief is not. The sample PDF in this folder is labeled
**SAMPLE — DEMO DATA** on its cover and carries invented play counts — safe to show a
designer, never safe to send a client.

**Trigger:** Lydia Moncrief, 3:49pm — *"Harrison Jefferis with Freeman Water Treatment is
requesting a report on his screens. I have generated one for his OnTarget screens. Can you
please provide one for his 17 locations with your networks?"* We are being read side by side
with a competitor's report, by a client who already has theirs in hand.

---

## The hook (one sentence)

**Our report has to be the one he shows people.**

Not the one he reads and files. Harrison is holding two documents about the same campaign. The
one that wins is the one he forwards to a partner, prints for a wall, or pulls up on his phone
when someone asks what he's doing with his marketing budget. That is a design problem, not a
data problem — we already have more data than they do.

## What we're up against

**I have not seen OnTarget's report.** Everything below assumes we should be excellent on our
own terms rather than reactive to theirs. If you can get a copy — even a photo of a page —
send it over and this brief gets sharper. Until then, two things we know:

- **They quoted "17 locations."** They count venues. We can count screens (34 across 22 venues
  in the sample), because our dashboard carries a per-venue licence count and theirs apparently
  does not surface one. That contrast is the single strongest visual moment available to us and
  the current design throws it away in an 8pt label.
- **Jackson is OnTargetTV's home turf** (per the MDOT brief). This is the same competitor we
  expect to meet again in expansion markets. A report that visibly out-classes theirs is an
  asset well past this one client.

## What is wrong with ours today

Look at `current-state/` alongside this list. These are defects, not taste:

- **The charts overflow the page and get clipped.** Five charts are placed 2-up at
  `max_width=3.8in` each. Two of those plus a gutter is 7.6in; the text column is 6.925in. The
  right-hand column overruns by 0.54in and stops 18pt from the paper edge, which is why the
  donut legend reads "Restaurant &…" and the scatter labels run off the sheet. Correct pair
  width is **≤3.40in**. (`generators/advertiser_report.py:613`, measured in the delivered PDF.)
- **Page 2 wastes its bottom 45%.** The executive summary ends and roughly 5.5in of white
  follows before the break. Nothing is positioned; pagination is pure reflow, so this moves
  around between LibreOffice versions — the same document rendered as 7 pages in one place and
  6 in another.
- **Five charts on one page, none with room to breathe.** Y-axis labels truncate
  ("Mississippi Asthma & Allergy C…"), value labels collide with bars, and "Market Comparison"
  is three subplots squeezed into a third of a row.
- **The KPI grid is ragged.** Row 1 has five cells, row 2 has four, and they do not align.
  "208h 11m" wraps to two lines while its neighbours sit on one; "Oxford & Starkville & Tupelo"
  wraps to three and throws the row's baseline out entirely.
- **One chart is a tautology.** "Engagement Distribution" plots screen time against plays. Air
  time *is* plays × spot length, so it is a straight line by construction. It looks analytical
  and says nothing.
- **The document is not actually set in Arial.** The Docker image installs
  `libreoffice-writer` and no MS fonts, so every run is remapped to Liberation Sans on
  conversion. Metric-compatible, so nothing shifts — but if we are choosing a typeface, we
  should choose one we actually ship.

## What we already have and are not using

This is where the upside is. All of it is populated on a normal run and rendered **zero
times** in the advertiser report:

- **Per-venue `address`** — every venue, real street addresses. A map is sitting right there.
- **Per-venue `screen_count`** — the licence count per venue. The "34 vs 17" story, per row.
- **Per-venue `dwell_time_minutes` and `monthly_traffic`** — average dwell is 55.7 minutes
  across the network. *Fifty-five minutes.* That number should be enormous on a page and it is
  currently invisible.
- **`first_aired` / `last_aired`** — a campaign timeline nobody is drawing.
- **`general_category`** — a clean 15-value grouping that exists for all 97 venues in the
  dashboard but is never copied onto the venue record, so the category table groups on a noisy
  60+-value field instead.
- **`data/venue_audience_profiles.json`** — age/income/education multipliers covering all 15
  categories. Audience composition, unused.
- **Network headline numbers from `config.json`** — the report never states them.

Real network figures a designer can typeset: **97 venues · 118 screens · 2,042,428 monthly
impressions · 430,691 monthly visits · 55.7 min average dwell**, across Oxford (45),
Starkville (25), Tupelo (24), Columbus (2), West Point (1).

## The brand system (exact, do not eyeball)

The report always renders in the **"original"** scheme. The other three palettes in the code
are proposal-only — do not design against them.

| Token | Hex | Used for |
|---|---|---|
| primary / `bg_hex` | `#1B1F3B` | navy — cover, section bars, KPI banner, table headers |
| accent / `accent_hex` | `#C5A55A` | gold — rules, KPI values, bullets, card borders |
| text | `#333333` | body |
| gray | `#808080` | captions, footer |
| `light_hex` | `#F0EDE4` | callout / accent-card background |
| alt-row fill | `#F5F5F5` | data-table striping (hard-coded, not theme-aware) |

Market colours (charts): Oxford `#1B1F3B` · Tupelo `#C5A55A` · Starkville `#5F7D6E` ·
Columbus `#C4836E` · West Point `#4A90B8`.

**Geometry.** US Letter portrait. Content pages: 1.5cm top/bottom, 2.0cm left/right →
**usable column 6.925in**. Cover page runs tighter margins but is *not* full bleed today —
there is a 0.51in white margin down each side of the navy.

**Type today:** Arial throughout. Cover client name 24pt bold; report title 28pt bold gold;
section bars 16pt bold white uppercase; body 10.5pt; table header 9pt bold (8pt over 6
columns); KPI value 20pt bold gold (auto-shrinking to 16pt/14pt on long values); KPI label 8pt;
footer 8pt.

**Glyph warning:** `❚` (U+275A) and `✓` (U+2713) are missing from Liberation Sans and fall back
to DejaVu mid-sentence. Safe: `─ ■ • ● █ ▲ ▼ →`.

## What the pipeline can actually build

This is the part that decides whether a design is buildable. Everything below was
probe-tested — a real .docx generated, converted through LibreOffice, and the PDF inspected.
Do not take the folklore that "python-docx can't do design" at face value:

| Effect | Verdict |
|---|---|
| Linear / radial gradients | **Yes — stays vector, costs nothing** |
| Rounded corners | **Yes** (on a shape, not on a table cell) |
| Absolute positioning | **Yes — landed exactly where requested** |
| Full-bleed edge-to-edge art | **Yes** (anchored, `behindDoc`) |
| Overlapping elements | **Yes** |
| Live text inside a shape | **Yes — stays selectable** |
| Rotated 90° text (side rails) | **Yes** |
| Two-column flow | **Yes** |
| Opacity / transparency | Yes, but flattens to a 300 DPI raster |
| Transparent PNG over a fill | **Yes** |
| Pattern / texture cell fill | **No** — flattened to solid grey |
| Rounded corner on a table cell | **No** — use a shape or PNG instead |
| Drop shadow on a cell | **No** |
| Web fonts | **No** — the font must be installed in the image |

**Golden rule: gradients and rounded corners are free and stay vector. Opacity costs a raster.
Textures must be PNGs.**

The escape hatch is wide. Charts are already matplotlib PNGs embedded at ~299 effective DPI. A
whole page can be composed as one 8.5×11in PNG and dropped in edge-to-edge. The sane split is
live text for headings, body and tables — PNG for anything matplotlib or PIL draws better than
OOXML.

## The call I'd make: design it in HTML

**Recommendation — design the report as an HTML page, not as a Word layout.** Reasons:

- **The ceiling is already being hit on the web side.** `static/rates.html` uses CSS gradients,
  Google Fonts (Playfair Display + Work Sans), and a working `@media print` block with
  `@page{size:letter;margin:0.55in}` and `print-color-adjust:exact`. That is a finished house
  recipe for a print-quality page, in this repo, today.
- **The route layer already exists.** `server_routes.py` serves `/rates`, `/board` and `/mdot`
  before Streamlit boots. Adding `/report` is about a three-line change to one dict.
- **A link beats an attachment.** Harrison opening a URL on his phone, on our domain, that
  looks like a product — versus OnTarget's emailed file. That is the forwardable artifact.
- **The .docx path stays.** Nobody has to rip anything out. We keep generating Word for people
  who want a file, and the HTML version is the one we lead with.

The cost is one renderer if we want server-side PDF (WeasyPrint is the light option; headless
Chromium is the faithful one, ~400MB of image). We may not need either at first — the browser's
own print dialog produces the PDF, exactly as `rates.html` already does.

**If you'd rather stay in Word,** the capability matrix above is real and the redesign is still
worth doing — gradients, full-bleed covers, positioned art and rounded panels are all
available. It is just slower to build and fragile across renderers.

## What I want back

Artboards at **letter portrait, 8.5×11in**, designing to a **6.925in live column** (or full
bleed where you want it). Cover the seven blocks the report emits today, and feel free to
re-cut them:

1. **Cover** — client name, campaign period, rep, MCTV mark
2. **Executive summary** — the KPI moment; this is where "34 screens" has to land like a punch
3. **Performance by venue** — currently an 8-column table, 22+ rows
4. **Performance by category**
5. **Performance analytics** — the five charts, with room to breathe
6. **What this means for your business** — narrative, optional
7. **Meet your team** — three headshots

Three things I care about most, in order:

1. **Make the screen count the hero.** "34 screens across 22 locations" is the whole argument
   against "17 locations." Today it is one cell in a five-across banner.
2. **Make dwell time land.** 55.7 minutes of average dwell is the most persuasive number we
   own and it is currently an 8pt label reading "Avg Dwell Time."
3. **Give the venue table a reason to be read.** 22 rows of 8 numeric columns is a spreadsheet.
   With addresses and screen counts available, it could be a map, or cards, or a ranked visual.

## Ground rules

- **Every number in this report goes to a paying client.** A figure we cannot source gets
  omitted, never estimated. The current code deliberately hides the screen count entirely when
  the dashboard cannot account for every venue — a design that assumes the number is always
  there needs an empty state.
- **Do not design around the sample's numbers.** The play counts in the sample PDF are
  invented. Venue names, traffic, dwell and impressions are real; plays are not.
- **Charts must fit 3.40in at 2-up**, or go full width at one per row. This is the bug that
  clips the current legends — don't inherit it.
- **Pick a typeface we can install.** Arial isn't in the image. Inter, Source Sans 3 and Barlow
  are all Debian-packaged and ship cleanly.
- **`data/network_dashboard.json` is stamped 2026-02-24** — about six months stale. Screen
  counts and venue names will shift before this ships. Design for a refresh, and don't hard-code
  a venue list.
- **No client logo usage beyond what a client has given us.** Same rule as the MDOT mockup:
  illustrating a partnership is not the same as claiming one.
