# Market Mapping — Iteration Log

Driven by two **Routines** (persistent, server-side) firing 30 minutes apart:

| Routine | Cron | ID |
| --- | --- | --- |
| MCTV market maps — iteration (top of hour) | `7 * * * *` | `trig_011MDCD64iHrmHURtYMd4e4Y` |
| MCTV market maps — iteration (half past) | `37 * * * *` | `trig_01JSLEoDPKUPppm1FU2pQ8Xi` |

Delete both with `delete_trigger` when iteration 12 completes.

> **Why Routines and not `CronCreate`.** The loop originally ran on an in-memory cron job
> (`39fef93a`). Those are session-only — they die on any session restart, and this one died twice,
> costing roughly three iterations between 07:48 and 10:35. Routines are stored server-side and
> survive restarts. Routines have a one-hour minimum interval, so the 30-minute cadence comes from
> two hourly Routines offset by 30 minutes.

| # | Time | Work done | Next up |
| --- | --- | --- | --- |
| 1 | 2026-08-04 ~06:5x | Established corridor/node structure for all five markets (Olive Branch, Hernando, Southaven, Horn Lake fill-in, Tupelo densification). Node-level screen targets. Grounded every node in verified geography — Goodman Rd/Craft Rd/Old Towne/Cascades, Courthouse Sq/McIngvale, Silo Square/Snowden/Tanger/Landers, NMMC/Barnes Crossing/Gloster/Fairpark. Competitive overlay stubbed pending NTV360 export. | Visual map artifact |
| 2 | 2026-08-04 ~07:4x | **Visual maps built** — `markets.json` + `build_maps.py` → `market-maps.html`, mirroring the `rafters-oxford` handoff pattern (stdlib only, navy/gold, dark-mode aware, self-contained). Inline SVG corridor schematics per market with auto-placed road labels. **Re-cut every phase target onto a pricing-tier threshold (40 / 75 / 90)** after finding iteration 1's ranges landed in billing dead zones. Applied the same logic to Tupelo: 25 + 50 = 75 unlocks the top tier for a Tupelo-only buy. Categories now validate against `config/config.json`. | Build cost model — price the "free" territory |

| 3 | 2026-08-04 ~11:0x | **Metro zone map** — `metro_zones.json` + `build_metro_map.py` → `metro-map.html`. True-to-scale equirectangular projection (cos-lat corrected at 35.15N) with real county, river and interstate geography; 10 ranked zones drawn as lat/lon bounding boxes, solid outline = DeSoto (offered), dashed = separate n-Compass territory. Headline finding: **Germantown $149,920 / Collierville $134,319 / Arlington $135,105 vs DeSoto's $85,500** — the wealthiest ground in the metro is in Tennessee and is not ours to take. Corrected the BlueOval City claim in TERRITORY-BRIEF.md (Ford/SK JV dissolved, production slipped). | Build cost model — n-Compass franchise data found: $35K fee, $48,150–$120,405 total investment |

**Published artifact (iteration 3):** https://claude.ai/code/artifact/dd30a00e-8162-4263-a4ed-95b635bec81a

**Published artifact (iteration 2):** https://claude.ai/code/artifact/c356da53-40dd-4653-b7b8-80dfb03fde07
Republish by passing that URL as `url` to the Artifact tool, or from this conversation by
republishing `market-maps.artifact.html` — either keeps the same link.

## Notes for future iterations

- `build_maps.py` validates on every run: node sums vs market targets, phase cumulatives vs
  40/75/90, and every category against `config/config.json` → `venue_categories`. It exits non-zero
  on mismatch, so edit `markets.json` and re-run rather than hand-editing the HTML.
- Road labels auto-place at the point along each polyline farthest from any node *and* from
  previously-placed labels. Adding nodes near a corridor will move its label — that's intended.
- `build_maps.py` emits two files: `market-maps.html` (standalone, for the repo) and
  `market-maps.artifact.html` (fragment — the Artifact publisher supplies the document wrapper).
- Screenshot check: Chromium is at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. The pip
  `playwright` package expects a newer build, so pass `executable_path` rather than running
  `playwright install`.

## Backlog

- [x] **Visual market maps** — corridor diagrams per market, phase filter, tier ladder
- [x] **Tier-aligned phasing** — phase lines on 40 / 75 / 90
- [ ] **Build cost model** — hardware + install per screen × phase, so the build-out clause can be
      priced. This is the number that decides whether "free territory" is actually free.
- [ ] **Rep coverage plan** — drive-time routing across DeSoto nodes; one rep or two?
- [ ] **Venue category targeting model** — how many venues of each category actually exist per node
      (vs. which categories we'd *want*); ties to `loop_items`
- [ ] **Host economics check** — does $0-cost hosting hold in a Memphis-DMA suburb?
- [ ] **Marshall County trigger conditions** — what would have to be true to justify hardware in Byhalia
- [ ] **Competitive overlay** — blocked on the NTV360 license export from Don
