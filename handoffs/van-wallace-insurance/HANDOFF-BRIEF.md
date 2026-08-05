# Van Wallace Insurance Agency — Creative Handoff Brief

**Prepared for:** Claude Design
**Prepared by:** MCTV Elite Advertising
**Date:** 2026-08-05
**Status:** Concept storyboard drafted — needs client fact-check before production

---

## 1. The ask

Same play as the Tupelo Aviation Day spot: the client sent brand assets, we turn them into a
screen-ready :15 for the network. Jonathan Wallace sent his brand kit on July 30 and looped in
Madison Brandon, who followed up the same afternoon with eleven logo files. This package takes
that material and drafts the spot.

Difference worth naming up front: the aviation package had an **event** to advertise — a date, a
time, a place, a reason to look. Van Wallace is an always-on agency with no campaign, offer, or
deadline attached yet. So this storyboard is built on the agency's durable positioning
(independent, local, long-tenured, full-line) rather than a promotion. If Jonathan wants to push a
specific line of business or a seasonal hook, that changes frames 1–3 and should be asked before
production.

---

## 2. Client profile

| Field | Value |
| --- | --- |
| Business | Van Wallace Insurance Agency |
| Principal | Jonathan Wallace — `jonathan@vanwallace.net` |
| Marketing contact | Madison P. Brandon — `madisonpaige10@gmail.com` (sent the logo files) |
| Phone | 662-844-2884 |
| Website | vanwallace.net |
| Address | 499 Gloster Creek Village, Suite I-11, Tupelo, MS 38801 |
| Market | Tupelo |
| Lines written | Home, Auto, Life, Small Business, Annuities, Retirement |
| Licensed in | Mississippi, Alabama, Tennessee |
| Established | 1989 — **unverified, see Open items** |
| Structure | Independent agency (not captive to a single carrier) |

Deal status: no signed package. Creed's read is a small account, so the creative is built to work
at the entry tier and to scale up without a redesign.

---

## 3. Brand assets received

**From Jonathan (July 30, 18:32) — `VanWallaceAgency.png`, the brand kit sheet:**

| Element | Value |
| --- | --- |
| Primary green | `#629264` |
| Sage | `#A4B8A6` |
| Deep green | `#325B34` |
| Cream | `#F3EDE0` |
| Display / script face | Apricots |
| Primary faces | Now, Raleway |

**From Madison (July 30, 18:35) — eleven PNGs:**

`NEW LOGO.png` · `Square Logo.png` · `1.png` · `2.png` · `3.png` · `4.png` ·
`TRANS 1.png` · `TRANS 2.png` · `TRANS 3.png` · `TRANS 4.png` ·
`Screen Shot 2023-02-06 at 4.15.39 PM.png`

The `TRANS` files are the transparent-background variants — those are the ones production should
use. The logo is a wordmark ("VAN WALLACE" over letterspaced "INSURANCE AGENCY") laid over a sage
script `Vw` monogram.

**These files live in Outlook, not in this repo.** They were never downloaded to the working
environment, so nothing binary is committed here. Pull them from the July 30 thread
"Van Wallace Agency" before production.

### Font substitution

| Brand font | Status | What the storyboard uses |
| --- | --- | --- |
| Raleway | Available in Adobe Fonts | **Raleway** — used throughout |
| Now | Not available under this account | Raleway |
| Apricots | Not in Adobe Fonts at all | not used |

Raleway is one of the client's own three faces, so the storyboard is on-brand as drafted. The
script `Vw` monogram is **not** reproduced — that mark is their artwork and production should drop
in the supplied PNG rather than approximate it.

---

## 4. Creative spec

Straight from the network's own constraints (`pages/16_Simulator.py`, `config/config.json`):

| Constraint | Value |
| --- | --- |
| Canvas | 1920 × 1080 landscape |
| Runtime | 15 seconds |
| Audio | **None** — indoor screens are silent |
| Copy budget | 6–10 words per frame |
| Dwell | 30–60 min average — viewers see the loop repeatedly |
| CTA rule | Must read from across a room; phone numbers and short URLs work, long URLs do not |

Silence is the design driver. Every frame has to carry itself with no voiceover, and repeat
exposure means the spot should reward a second look rather than shout once.

---

## 5. The storyboard

Four frames, roughly 3–4 seconds each. Open `spot-storyboard.html` in a browser, or view the
rendered stills in `frames/`.

| # | Time | Frame | Copy |
| --- | --- | --- | --- |
| 1 | 0:00–0:04 | Hook — cream field, deep green type | "Tupelo's had our number since 1989." |
| 2 | 0:04–0:08 | Coverage — deep green field, cream type | "Home. Auto. Life. Business." |
| 3 | 0:08–0:12 | Differentiator — cream field | "We're not tied to one company. We work for you." |
| 4 | 0:12–0:15 | CTA — deep green field | Logo lockup · **662-844-2884** · vanwallace.net |

### Why this copy

- **Frame 1** does double duty — "had our number" is both the phone-number nod and the
  been-here-forever claim. Longevity is the strongest asset a small independent agency has against
  a national carrier's ad budget.
- **Frame 2** is the scannable one. Four words, one per line. This is the frame that works when
  somebody glances up for half a second.
- **Frame 3** is the actual pitch. Most viewers do not know what "independent agent" means; this
  says it in plain words without jargon.
- **Frame 4** is phone-first. At a 30–60 minute dwell the phone number is the thing that has to
  survive being read from forty feet away, so it is the largest element on the screen.

### Deliberate omissions

No savings claims, no "lowest rate," no carrier logos. Insurance advertising invites scrutiny on
comparative and savings language, and we have nothing substantiated to stand behind. If Jonathan
wants a savings message he needs to supply the basis for it.

Note that "every major carrier" appears as a small eyebrow on frame 2. That is a common
independent-agency phrasing but it is still a claim about his appointments — confirm it or swap it
for "many of the nation's top carriers."

---

## 6. Contrast and legibility check

| Pairing | Use | Ratio | Verdict |
| --- | --- | --- | --- |
| `#325B34` on `#F3EDE0` | headlines, frames 1 & 3 | ~8.9:1 | Passes AA and AAA |
| `#F3EDE0` on `#325B34` | headlines, frames 2 & 4 | ~8.9:1 | Passes AA and AAA |
| `#A4B8A6` on `#325B34` | eyebrows, support | ~4.6:1 | Passes AA |
| `#629264` on `#F3EDE0` | eyebrows only, large | ~3.3:1 | Large-text only — never body copy |

Sage `#A4B8A6` on cream `#F3EDE0` fails badly and is used only as a decorative block and rule,
never behind text.

---

## 7. Open items

- [ ] **Verify "since 1989."** Sourced from third-party business directories, not from Jonathan.
      It is the headline of frame 1 and a wrong founding year on a screen in his own town is the
      kind of error that costs a relationship. Confirm before production, or cut frame 1 back to
      "Tupelo's had our number." which works without the date.
- [ ] **Confirm "every major carrier"** (frame 2 eyebrow) or soften it.
- [ ] **Confirm the lines listed on frame 2** are the ones he wants led with — annuities and
      retirement are currently demoted to the support line.
- [ ] **Pull the `TRANS` logo PNGs from Outlook** and drop the real mark into frame 4. The
      storyboard's lockup is typographic and is a stand-in, not final art.
- [ ] **Decide on the deal** before this ships. There is no signed package; runtime and market
      depend on the tier.
- [ ] Ask whether he wants a seasonal or line-specific hook instead of the always-on positioning.

---

## 8. What is in this package

| File | What it is |
| --- | --- |
| `spot-storyboard.html` | The four frames, 1920 × 1080 each. Self-contained; open in a browser. |
| `frames/frame1–4.png` | Rendered stills at full 1920 × 1080, for review and for pasting into email. |
| `HANDOFF-BRIEF.md` | This document. |
| `README.md` | Short orientation. |

The HTML is the source artifact. It is authored to the Adobe Express import contract
(`hz:slide-selector`, per-root `data-canvas-*`, single style block, no animation), so it can be
pushed to Express as an editable document, handed to Creatomate as the frame spec for the
:15 build, or exported straight to stills.

---

## 9. Provenance

Client facts came from two places, and they are not equally solid:

- **From the client directly** (brand kit and logo files, phone, website, principal, marketing
  contact) — taken from the July 30 "Van Wallace Agency" thread. Reliable.
- **From third-party directories** (street address, suite number, lines written, three-state
  licensing, 1989 founding) — the agency's own site could not be reached from this environment;
  `vanwallace.net` is blocked by the network policy here, so none of it was confirmed against
  their own pages. Treat all of it as needing a fact-check, the founding year most of all.

The creative spec is from the repo itself, not assumed: 1920 × 1080 and 15 seconds from
`config/config.json`, the silent / 6–10 words / room-legibility rules from `pages/16_Simulator.py`.
