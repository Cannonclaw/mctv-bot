# Huntington Bank Arena — Design Handoff Brief

**Prepared for:** Claude Design
**Prepared by:** MCTV Elite Advertising
**Date:** 2026-08-13
**Status:** Copy final, layout built, photography missing — ready for design

---

## 1. The ask

A 14-page host media kit exists and is sendable today. It was built in code
(`build_deck.py` → `deck.html` → PDF) because the sales meeting happened this morning and
Alli expects something before end of day.

**What design owns: the photography pass.** Every page currently uses a typographic or
CSS-rendered fallback where a photograph belongs. The kit reads well — it does not yet
*look* like the room it is describing. Three photo slots are cut, sized and waiting.

Secondary: if the kit is going to be printed and spiral-bound like the recent decks, it
needs a print-spec pass (bleed, margins, binding edge). See §7.

**What design does not own:** the copy, the numbers, or the page order. Those are approved.
§6 lists the handful of strings that may move and the ones that may not.

---

## 2. Who it goes to

| Field | Value |
| --- | --- |
| Venue | Huntington Bank Arena and Conference Center, Tupelo MS |
| Formerly | Cadence Bank Arena · BancorpSouth Arena |
| Recipient | Alli Shackelford, Director of Marketing |
| Contact | alli@hbarena.com · 662-841-6573 ext. 904 |
| Rep | Creed Cannon |
| Context | Met in person 2026-08-13. Warm. She is actively looking for ways to modernize the facility. |
| The offer | Free screens, and a 60/40 revenue split that follows whoever brings the advertiser |

The emotional job of the deck: *this upgrades your building and pays you, and it is not a
risk, because the airport across town already did it.*

---

## 3. Design system

Sampled from the Tupelo Territory Media Kit (Canva `DAHM-yFHfPQ`), which is the current
house style. Match it — this kit should sit in a stack with the others and look related.

### Palette

| Token | Hex | Use |
| --- | --- | --- |
| Navy | `#111C33` | Dark spread background |
| Navy deep | `#0C1526` | Cover gradient floor |
| Cream | `#F7F4EC` | Light spread background |
| Red | `#C3312A` | Eyebrows, italic accent, prices — **light spreads only** |
| Gold | `#C2A15C` | Eyebrows, italic accent — **dark spreads only** |
| Ink | `#16223A` | Body text on cream |
| HBA green | `#8DC63F` | The Arena's own green. Sample spot + the cover co-brand rule only. |

The red/gold split is load-bearing: red never appears on a navy page, gold never on cream.

### Type

Playfair Display (display) + Inter (everything else), both embedded in `_fonts.css`.

| Role | Spec |
| --- | --- |
| Page headline | Playfair Display 500, 50px, line-height 1.08, letter-spacing −0.014em |
| Headline accent clause | Same, italic, in red (cream) or gold (navy) |
| Cover headline | Playfair Display 500, 76px, line-height 1.06 |
| Eyebrow | Inter 600, 10px, letter-spacing 0.24em, uppercase |
| Body | Inter 400, 13.5px, line-height 1.92 |
| Stat number | Playfair Display 400, 40px |
| Stat label | Inter 500, 8px, letter-spacing 0.20em, uppercase |
| Footer | Inter 500, 8px, letter-spacing 0.22em, uppercase |

Every headline is a statement plus an italic clause — "Sixty / forty. *Whoever brings the
advertiser.*" Keep that rhythm if anything is reworded.

### Grid

- Page 1280 × 756 px. PDF exports at 792 × 468 pt = **11 × 6.5 in landscape** — the
  Chamber flip-book format, spiral/wire-o bound. 1280px wide preserves the type scale;
  756 = 1280 × 6.5/11.
- Margins 70px left/right, 52px top.
- Two-column body: 42% / remainder, 62px gutter.
- Stat rows anchor to `bottom: 74px`; footer to `bottom: 30px`. **The stat row is what
  stops these pages looking top-heavy** — it was the single biggest fix in the first pass.
  If a page has no stat row, it needs something else holding its bottom third.

---

## 4. Photo slots — the actual work

Drop files into `photos/`, rerun `build_deck.py`. Each slot has a designed fallback, so a
missing photo degrades gracefully rather than breaking.

| Slot | Page | Spec |
| --- | --- | --- |
| `cover.jpg` | 01, full bleed | Landscape, ≥1920×1080. A navy scrim runs left→right at 94% → 30% opacity, so **the subject must sit right of centre** and the left third must survive being nearly black. Arena exterior at dusk, or a full concourse. |
| `airport.jpg` | 03, beside the quote | A Tupelo Regional screen in place. Landscape. Proves the claim on that page. |
| `concourse.jpg` | 06, beside the zones | Arena concourse, west entry lobby, or the link corridor. Landscape. |

### Where the source images are

**None could be fetched automatically.** This build runs behind an egress proxy with a
strict allowlist that denies Canva's CDN, SharePoint, `hbarena.com`, and general web
fetching. Every route was tried. They have to be pulled by hand.

| Source | What's there |
| --- | --- |
| Canva `DAGnt1jROqg` — *CADENCE BANK ARENA PROPOSAL* | **Page 4:** six real photos of MCTV screens installed in venues. **Page 5:** Cadence Bank Arena event creative — Monster Jam, Trans-Siberian Orchestra, Badflower. |
| Canva `DAHM-yFHfPQ` — *Tupelo Territory Media Kit* | Pages 3 and 5 carry the Tupelo Regional Airport install shots. Page 1 is the Elvis statue cover. |
| SharePoint | `CADENCE BANK ARENA PROPOSAL.pdf`, 20 MB, print resolution. Linked from Creed's 2025-06-03 email to shelby@cb-arena.com. |
| hbarena.com | The Arena's own photography. Entry points: `/p/about/seating`, `/sitemap.aspx`. |
| Visit Tupelo | `tupelo.net/directory/huntington-bank-arena-and-conference-center-meeting-conventions/` |

**Rights.** Everything in the deck today is ours: MCTV logo, the team's own headshots, and
CSS renders of our own products. Nothing is stock, nothing is scraped. The Arena's own
photos are fine in a kit addressed to the Arena — that is ordinary practice — but they come
out if this deck is ever reused for another venue or for general marketing. Event posters
on page 5 of the Cadence deck belong to promoters and artists, not the Arena; treat those as
unusable. Best outcome is asking Alli for a few facility shots on the next touch.

---

## 5. What is rendered, and must stay rendered

Three things in this deck are drawn in CSS, deliberately. They are not placeholders.

1. **The lobby event board (page 10)** — a faithful miniature of `static/board.html`, the
   real shipped product, down to the gold NOW card, the live dot, and a private booking
   masked to *"Private Event"*. It is the single most differentiating page for a conference
   center. If it gets rebuilt in another tool, it must keep matching the real board; check
   `static/board.html` for the tokens (`--navy:#0a1220`, `--gold:#d4a017`, `--live:#3fbf6a`).
2. **The sample Arena spot (pages 02 and 07)** — a mock event promo in *their* green, so Alli sees
   her own creative rather than ours. Captioned as a sample. Keep the caption.
3. **The content feed screens (page 07)** — weather, news and trivia panels drawn in CSS.
   They show the real content mix that makes the loop watchable; that argument is why the
   airport signed.
4. **The screen bezel** housing all of it — a wall-mounted display with mount plate and a soft
   gloss sweep.

**No photograph of the Arena's interior appears anywhere in the deck, and none is implied.**
Do not generate one, and do not substitute a stock arena that could read as theirs. A
fabricated photo of a building in a pitch to the people who own that building is the one
mistake this deck cannot make.

---

## 6. Copy rules

Full text in `copy.md`, generated from the deck so it cannot drift.

**Cannot change without Creed:**

- **The 60/40 split, and its direction.** 60% goes to whoever *brings* the advertiser, not
  to a fixed party. This was corrected once already. It appears in exactly four places:
  page 09 (headline, body, table, stat row), page 02 (item 02 and stat row), page 08
  (footer line, "up to 60%"), page 03 (the airport reference). Change one, change all.
- **The page 09 disclaimer.** "Illustrative only, at a $350/mo blended advertiser rate — not
  a guarantee of earnings." It stays, at its current prominence, on any redesign.
- **The page 06 hedge.** "A starting map, not a final one — drawn from the outside, before
  we've walked it with you." Nothing in that building has been surveyed.
- **Network figures:** 125+ screens, 28 Tupelo/Lee Co. venues, 1.9M+ monthly impressions,
  55+ min dwell, $2.63 blended CPM.

**Free to adjust for fit:** headline line breaks, stat-label wording, the venue list on
page 05, zone descriptions on page 06.

**Deliberately absent:** the building's square footages. Figures are available second-hand
but the venue has been renamed twice and stale numbers quoted back to their own marketing
director cost more than the specificity gains. Named spaces only.

---

## 7. Deliverables

1. **Photography pass** — three slots filled, or a written call that a given slot is better
   left as the fallback.
2. **Print spec.** Trim is already 11 × 6.5 in to match the Chamber flip book. Still needs
   0.125 in bleed added and a binding-edge safe margin proofed on the left of every page. The
   layout runs a 70px (0.73 in) left margin, which is probably enough, but nothing has been
   proofed against a real coil punch. Stock: 100 lb / 270 gsm silk or matte cover — not gloss,
   which flares the navy pages under room light.
3. **A Canva version**, if the team wants to hand-edit it later. The HTML is the source of
   truth today, which is fast for us and useless for Swayze on a phone. Worth a conversation
   rather than assuming.

**Acceptance:** it should sit in a stack next to the Tupelo Territory kit and read as the
same family — same palette, same headline rhythm, same anchored stat rows.

---

## 8. Files

| File | What it is |
| --- | --- |
| `DESIGN-BRIEF.md` | This document |
| `copy.md` | Every string in the deck, page by page. Generated. |
| `HANDOFF-BRIEF.md` | The sales/account brief — deal context, sourced facts, open items |
| `build_deck.py` | Reference implementation. Design tokens live at the top. |
| `build_copydeck.py` | Regenerates `copy.md` from the built deck |
| `build_email.py` | The outreach email as a reviewable `.eml` |
| `deck.html` | Built deck, fonts embedded — opens in any browser |
| `photos/README.md` | Slot specs and source locations |
| `_fonts.css` | Playfair Display + Inter, base64 |

Rebuild: `python build_deck.py && python build_copydeck.py && python build_email.py`.
Outputs land in `output/` (gitignored).

---

## 9. Open items design should know about

1. **The airport pull-quote on page 03** is Dylan Meador's, from his go-live email,
   attributed by role not name. Never cleared for outbound use. Creed's call; if it goes,
   page 03 needs a new right-hand element.
2. **Screen count (6–8) and the six zones on page 06** are proposed from outside the
   building. A walkthrough will change them.
3. **Elliot Davis has no headshot on file** and falls back to a monogram on page 12. The
   other three are real. If a headshot turns up, drop it at
   `assets/team/elliot_headshot.png` and it is picked up automatically.
