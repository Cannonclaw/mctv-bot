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

| 4 | 2026-08-04 ~11:3x | **Build cost model** — `build_cost_model.py` → `cost-model.html`, an interactive calculator (every input editable), plus `COST-MODEL.md`. Found n-Compass's published terms: **$35,000 franchise fee, $48,150–$120,405 total investment, and a $500/mo flat + $75 per billboard per month royalty**. At 90 screens that royalty is **$87,000/yr — the waived fee is ~7% of the 5-year cost**. Capex to 90 screens models at $54,000 (inside n-Compass's own published range). Break-even is 11 advertisers at Phase 1 and **10 at Phase 2** — it improves with scale because the tier jump outruns the cost curve. Adds a fifth question for Don. | Rep coverage / drive-time routing |

| 5 | 2026-08-04 ~12:0x | **60-mile radius scan** — `radius_scan.json` + `build_radius_map.py` → `radius-map.html`, plus `EXPANSION-SCAN.md`. Great-circle distances from 31 candidate towns to all five current markets. **Tuscaloosa + Northport AL is 53 mi from Columbus** — 116,477 people + ~34,000 UA students, the only genuine second Oxford in range, but already contested by Impulse Digital Media running our exact free-host model. Bigger finding: **Columbus (2 screens) + West Point (1) sit against a $2.5B Steel Dynamics investment creating 1,000 jobs at $93K average** — finishing the Golden Triangle beats opening anything new. Builder validates current screen counts against `config.json`. | Rep coverage / drive-time routing |

| 6 | 2026-08-05 | **Incumbent footprint mapped** — Creed supplied DeSoto Local's own current location map. ~32–35 pins across **two states**. `INCUMBENT-FOOTPRINT.md` records the read; competitive flags in `markets.json` moved from assumption to observation (9 contested / 5 unknown / 7 clear), and Z1/Z2 in `metro_zones.json` reclassified. **Headline: she is operating in Bartlett, Lakeland and Germantown — Shelby County, TN** — the two zones the metro map had ranked #1 and #2 and labelled "not on the table." Southaven assumption confirmed (~12–14 pins on Goodman Rd) but Olive Branch (~3) and Hernando (~3–4) are not empty either. Build order unchanged; rationale changed from "empty ground" to "outbuild a toehold." Fixed status classification in `build_maps.py` to match on keyword. | Rep coverage / drive-time routing |

**Published artifact (iteration 5):** https://claude.ai/code/artifact/ae624d29-df75-408d-92ad-4d869d11702b

**Published artifact (iteration 4):** https://claude.ai/code/artifact/278f6c6a-079c-4f42-a0f3-f5c31195bd28

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
- [x] **60-mile expansion scan** — Tuscaloosa is the only real market in range; Golden Triangle first
- [ ] **Rep coverage plan** — drive-time routing across DeSoto nodes; one rep or two?
- [ ] **Venue category targeting model** — how many venues of each category actually exist per node
      (vs. which categories we'd *want*); ties to `loop_items`
- [ ] **Host economics check** — does $0-cost hosting hold in a Memphis-DMA suburb?
- [ ] **Marshall County trigger conditions** — what would have to be true to justify hardware in Byhalia
- [ ] **Competitive overlay** — blocked on the NTV360 license export from Don
