# Huntington Bank Arena & Conference Center — Host Media Kit

**Format:** 15-page flip book, 11 × 6.5 in landscape, spiral bound — same as the Chamber package.

**Prospect:** Huntington Bank Arena and Conference Center, Tupelo (formerly Cadence Bank Arena)
**Contact:** Alli Shackelford, Director of Marketing — alli@hbarena.com — 662-841-6573 ext. 904
**Mailing:** P.O. Box 7288, Tupelo, MS 38802
**Rep:** Creed Cannon
**Status:** Met in person 2026-08-13. Warm — she is actively looking for ways to update the
facility and this does it at zero capital cost. Pitched a revenue-share structure modeled on the
Tupelo Regional Airport deal.

## What's in this package

| File | What it is |
|---|---|
| `build_deck.py` | Generates the 15-page host media kit. Edit content here, rebuild. |
| `deck.html` | Generated deck — open in any browser. Fonts embedded, no network needed. |
| `build_email.py` | Assembles the outreach email as a reviewable `.eml` with the deck attached. |
| `_fonts.css` | Playfair Display + Inter, base64-embedded. Build input; keeps the deck offline-safe. |

Build both:

```
python handoffs/huntington-bank-arena/build_deck.py    # -> output/proposals/…pdf
python handoffs/huntington-bank-arena/build_email.py   # -> output/emails/…eml
```

Outputs land in `output/` (gitignored). The `.eml` carries `X-Unsent: 1`, so Outlook opens it as
an editable draft rather than a received message. **Nothing sends itself** — review, then hit Send.

## Design

Follows the current MCTV deck language, not the older DOCX generator in `generators/`:
cream (`#F7F4EC`) and navy (`#111C33`) spreads, Playfair Display headlines with a red (`#C3312A`)
or gold (`#C2A15C`) italic clause, Inter small-caps eyebrows, hairline-anchored stat rows,
numbered footers. Same system as the Tupelo Territory Media Kit (Canva `DAHM-yFHfPQ`).

Format follows the Chamber flip book: 11 x 6.5 in landscape, spiral bound, image-rich.
The cover carries the arena's front elevation (Huntington Bank Arena sign visible) as a
corner fade — supplied by Creed, 2026-08-16. It's a small source; a full-resolution
`photos/cover.jpg` upgrades the cover to full bleed automatically.

## Page plan

| # | Page | Job |
|---|---|---|
| 01 | Upgrade the arena. We'll cover it. | Cover, co-branded in their green, arena exterior corner fade |
| 02 | What we're proposing | The deal in three moves + a sample Arena spot on screen |
| 03 | We just did this at Tupelo Regional | Proof — same market, same structure, board-approved |
| 04 | Already live, across town | Real photos of the airport install — rotunda, live ad, counter |
| 05 | The network & the value | Network stats + local CPM comparison |
| 06 | The company you'd keep | 28 Tupelo/Lee Co. host venues |
| 07 | Where your screens would go | Six proposed zones — explicitly a starting map |
| 08 | Not a wall of ads | The real loop: weather, news, trivia, and her event spot |
| 09 | What it costs you: nothing | The free host package, four $0 cards |
| 10 | Sixty / forty | Revenue share economics + grandfathering |
| 11 | Your calendar, on every screen we own | Network-wide promotion + the lobby event board |
| 12 | Who we are | Company page |
| 13 | Owner-operated, and local | The team, with real headshots |
| 14 | How this actually happens | Five-step path to live, ~30 days |
| 15 | Thank you | Contacts + what we need from them |

## Facts used, and where they came from

- **60/40 revenue share, content approval, grandfathering** — the TAA Venue Partner Agreement
  thread (Creed → Dylan Meador, 2026-03-12).
- **Airport install** — five screens across lobby, center lobby, ticket counter, baggage and
  sterile zone; Exceed Technologies; live 2026-04-23; dedicated IPs locked to MACs, UPS +
  generator backing (Dylan Meador, 2026-04-23).
- **Board approved with no legal changes** — Dylan Meador, 2026-03-18.
- **Network stats** (125+ screens, 28 Tupelo/Lee Co., 1.9M+ impressions, 55+ min dwell) and the
  **CPM comparison** — Tupelo Territory Media Kit, the most recent published figures.
- **Lobby event board** — real shipped capability (`services/venue_events_service.py`,
  `static/board.html`), running for the Oxford Conference Center. Genuinely differentiating for a
  conference center and costs us nothing to extend.

## The revenue share

**60/40, and the 60 follows whoever brings the advertiser** (confirmed by Creed, 2026-08-13).
MCTV sources an advertiser → Arena takes 40%. The Arena sources one → Arena takes 60%. MCTV
produces, bills and services every spot either way. This is the deck's strongest page, because it
turns the Arena's existing sponsor relationships into something worth more than they were.

Page 10 carries the math, page 2's numbered item 02 and stat row carry the summary, and page 9's
footer says "up to 60%". Those are the only four places the split appears (plus the page 3
airport reference).

## Open items before sending

1. **The airport pull-quote on page 3** is Dylan Meador's, from his 2026-04-23 go-live email,
   attributed by role rather than by name. He never cleared it for outbound use. Keep it, soften
   it, or drop it — Creed's call.
2. **Screen count (6–8) and the six zones on page 7** are proposed from the outside. They should
   survive a walkthrough, but nothing in the building has been surveyed.
3. **Revenue table on page 10** is illustrative at a $350/mo blended rate and labeled as such.

## Imagery

Everything visual in the deck is either ours or drawn:

- **Team headshots** on page 13 and page 15 — hi-res crops from the 1050px team cards, kept in
  `team/` beside this file (the 400px `assets/team/` crops went soft in print).
- **The lobby event board** on page 11 is a faithful CSS render of `static/board.html` — real
  product, real behaviour, including a private booking masked to "Private Event".
- **The sample Arena spot** on pages 2 and 8 is a CSS render in Huntington Bank Arena's own green, so
  she sees her creative rather than ours. Clearly captioned as a sample.
- **Page 4 is real photography** — the Tupelo Regional gate rotunda with an MCTV screen live
  (supplied by Creed, 2026-08-16), plus a live advertiser spot and the ticket-counter screen
  extracted from the Tupelo Territory Media Kit through the Canva connector.
- **One photograph of the Arena appears: the exterior on the cover**, supplied by Creed
  (2026-08-16). No interior photograph of the Arena appears or is implied anywhere.

Remaining photography drops into `photos/` — see that folder's README for the open slots
(`concourse.jpg`, a full-res `cover.jpg`) and where the remaining source shots live.

## Next step

Walkthrough at her convenience. Bring the Venue Partner Agreement and the COI naming the Arena as
additional insured — that combination is what moved the Airport Authority from interested to
signed inside of a week.
