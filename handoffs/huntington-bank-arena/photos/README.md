# Photo slots

Drop a file here, rerun `python handoffs/huntington-bank-arena/build_deck.py`, and the
deck picks it up. Empty is a valid state — each slot has a designed fallback, which is
what ships today.

| File | Where it lands | Wants |
|---|---|---|
| `cover.jpg` | Page 1, full bleed behind the headline | Landscape, 1920×1080 or larger. Arena exterior at dusk, or the concourse with people in it. A navy scrim is laid over the left two-thirds, so keep the subject right-of-centre. |
| `exterior.jpg` | Page 1, top-right corner fade — used only when `cover.jpg` is absent | **Filled.** The arena's front elevation with the Huntington Bank Arena sign, supplied by Creed (IMG_6251, 2026-08-16). Small source (330px square, upscaled to 660), which is why it runs near-native in a corner fade instead of full bleed. A `cover.jpg` at real resolution supersedes it. |
| `airport.jpg` | Page 3, beside the Tupelo Regional quote | A terminal screen in place. Landscape. |
| `concourse.jpg` | Page 6, beside the proposed zones | The arena concourse, lobby, or conference pre-function. Landscape. |

`.jpg`, `.jpeg` and `.png` all work; the slot name is what matters.

## Where the good ones already live

None of these could be pulled in automatically. This session runs behind an egress proxy
with a strict allowlist: Canva's CDN, SharePoint, `hbarena.com` and general web fetching
are all denied at the policy layer, so scraping the Arena's own site was not possible
from here either. Fetch them by hand from:

- **hbarena.com** — the Arena's own photography, and the most on-brand option for a kit
  addressed to them. `www.hbarena.com/p/about/seating` and the site map at
  `www.hbarena.com/sitemap.aspx` are the entry points. Using a prospect's own photos in a
  pitch to that prospect is normal; if this deck is ever reused for another venue or for
  general marketing, those images need to come out.
- **Visit Tupelo** — `tupelo.net/directory/huntington-bank-arena-and-conference-center-meeting-conventions/`
  carries venue photography intended for promotional use.

- **Canva → `CADENCE BANK ARENA PROPOSAL`** (design `DAGnt1jROqg`). Page 4 has six real
  photos of MCTV screens installed in venues; page 5 has Cadence Bank Arena event
  creative (Monster Jam, Trans-Siberian Orchestra, Badflower and others).
- **Canva → `Tupelo Territory Media Kit`** (design `DAHM-yFHfPQ`). Page 3 and page 5 carry
  the Tupelo Regional Airport install shots; page 1 is the Elvis statue cover.
- **SharePoint** — `CADENCE BANK ARENA PROPOSAL.pdf` (20 MB), linked from Creed's
  2025-06-03 email to shelby@cb-arena.com. Same photos at print resolution.

Photos of the Arena taken by the Arena are better than any of the above, and asking Alli
for a few is a reasonable second touch.

## Rights

In the deck today: the MCTV logo, the team's headshots, CSS renders of our own screens
and event board, and one photograph of the Arena's exterior supplied by Creed. Nothing
is stock and nothing is scraped. Keep it that way — the deck gets printed, so anything
dropped in here should be a photo MCTV took or one the Arena has given us permission to
use. As with any Arena imagery, the exterior shot comes out if this deck is ever reused
for another venue.
