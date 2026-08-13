# Huntington Bank Arena & Conference Center — Host Media Kit

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
| `build_deck.py` | Generates the 12-page host media kit. Edit content here, rebuild. |
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

Typographic cover rather than a photo cover — we hold no rights to arena photography. Swap in a
licensed or self-shot image of the concourse before this goes to print.

## Page plan

| # | Page | Job |
|---|---|---|
| 01 | Upgrade the arena. We'll cover it. | Cover, prepared-for Alli |
| 02 | What we're proposing | The deal in three moves |
| 03 | We just did this at Tupelo Regional | Proof — same market, same structure, board-approved |
| 04 | The network & the value | Network stats + local CPM comparison |
| 05 | The company you'd keep | 28 Tupelo/Lee Co. host venues |
| 06 | Where your screens would go | Six proposed zones — explicitly a starting map |
| 07 | What it costs you: nothing | The free host package, four $0 cards |
| 08 | Sixty / forty | Revenue share economics + grandfathering |
| 09 | Your calendar, on every screen we own | Network-wide event promotion + lobby event board |
| 10 | Who we are | Company page |
| 11 | How this actually happens | Five-step path to live, ~30 days |
| 12 | Thank you | Team contacts + what we need from them |

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

## Open items before sending

1. **Confirm the 60/40 direction.** Written as 60% MCTV / 40% Arena, matching how the airport deal
   reads. If the airport split runs the other way, page 8 and the page 2 stat row both need
   flipping — they are the only two places the number appears.
2. **The airport pull-quote on page 3** is Dylan Meador's, from his 2026-04-23 go-live email,
   attributed by role rather than by name. He never cleared it for outbound use. Keep it, soften
   it, or drop it — Creed's call.
3. **Screen count (6–8) and the six zones on page 6** are proposed from the outside. They should
   survive a walkthrough, but nothing in the building has been surveyed.
4. **Revenue table on page 8** is illustrative at a $350/mo blended rate and labeled as such.

## Next step

Walkthrough at her convenience. Bring the Venue Partner Agreement and the COI naming the Arena as
additional insured — that combination is what moved the Airport Authority from interested to
signed inside of a week.
