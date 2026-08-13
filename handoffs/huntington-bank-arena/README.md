# Huntington Bank Arena & Conference Center — Host Media Kit

Host partnership pitch for **Huntington Bank Arena and Conference Center**, Tupelo
(formerly Cadence Bank Arena), addressed to Alli Shackelford, Director of Marketing.
Met in person 2026-08-13.

**12 pages · free screens · 60/40 revenue split following whoever brings the advertiser**

## Start here

Depending on why you're in this folder:

| You are | Read |
| --- | --- |
| **Design** — finishing the kit | **`DESIGN-BRIEF.md`**, then `design-manifest.json` |
| **Sales** — sending it | **`HANDOFF-BRIEF.md`**, then the built PDF |
| **Writing copy** | **`copy.md`** — every string, page by page |
| Just looking | Open `deck.html` in a browser |

## The state of it

Sendable today. Copy is final and approved, all 12 pages are laid out, and the outreach
email is drafted with the deck attached.

**What's missing is photography.** Three slots are cut and sized (`photos/`), each with a
designed fallback so nothing breaks while they're empty — that's the shipped state. Filling
them is design's job and is the main open work. None could be fetched automatically: this
build runs behind an egress allowlist that denies Canva's CDN, SharePoint, `hbarena.com`
and general web fetching, so the source images have to be pulled by hand. `DESIGN-BRIEF.md`
§4 says exactly which Canva design and page each one is on.

Everything currently visible is ours — MCTV logo, the team's real headshots, and CSS renders
of our own screens and lobby event board. No stock, nothing scraped, and no photograph of
the Arena implied anywhere.

## Build

```
python handoffs/huntington-bank-arena/build_deck.py       # -> deck.html + PDF
python handoffs/huntington-bank-arena/build_copydeck.py   # -> copy.md
python handoffs/huntington-bank-arena/build_email.py      # -> .eml draft
```

Outputs land in `output/` (gitignored). The `.eml` carries `X-Unsent: 1`, so Outlook opens
it as an editable draft rather than a received message. Nothing sends itself.

Rendering is headless Chromium, already present in this environment. `deck.html` and
`copy.md` are generated — edit `build_deck.py`, not them.

## Files

| File | What it is |
| --- | --- |
| `DESIGN-BRIEF.md` | Design handoff — system, photo slots, what's locked, deliverables |
| `HANDOFF-BRIEF.md` | Sales handoff — deal context, every sourced fact, open items |
| `design-manifest.json` | The same spec, machine-readable |
| `copy.md` | Every string in the deck. Generated. |
| `build_deck.py` | The deck. Design tokens at the top. |
| `build_copydeck.py` | Regenerates `copy.md` |
| `build_email.py` | The outreach email |
| `deck.html` | Built deck, fonts embedded |
| `photos/` | Photo slots — drop files, rebuild |
| `_fonts.css` | Playfair Display + Inter, base64 |

## Before it goes out

Three things need a human call, all detailed in `HANDOFF-BRIEF.md`:

1. The airport pull-quote on page 3 was never cleared for outbound use.
2. Screen count and zones on page 6 are proposed without a walkthrough.
3. The page 8 revenue table is illustrative, and labeled as such on the page.
