# Market Mapping — Iteration Log

Recurring job `39fef93a`, every 30 minutes, 12 iterations (~6 hours), started 2026-08-04.
Call `CronDelete` on `39fef93a` when iteration 12 completes.

| # | Time | Work done | Next up |
| --- | --- | --- | --- |
| 1 | 2026-08-04 ~06:5x | Established corridor/node structure for all five markets (Olive Branch, Hernando, Southaven, Horn Lake fill-in, Tupelo densification). Node-level screen targets. Grounded every node in verified geography — Goodman Rd/Craft Rd/Old Towne/Cascades, Courthouse Sq/McIngvale, Silo Square/Snowden/Tanger/Landers, NMMC/Barnes Crossing/Gloster/Fairpark. Competitive overlay stubbed pending NTV360 export. | Visual map artifact |
| 2 | 2026-08-04 ~07:4x | **Visual maps built** — `markets.json` + `build_maps.py` → `market-maps.html`, mirroring the `rafters-oxford` handoff pattern (stdlib only, navy/gold, dark-mode aware, self-contained). Inline SVG corridor schematics per market with auto-placed road labels. **Re-cut every phase target onto a pricing-tier threshold (40 / 75 / 90)** after finding iteration 1's ranges landed in billing dead zones. Applied the same logic to Tupelo: 25 + 50 = 75 unlocks the top tier for a Tupelo-only buy. Categories now validate against `config/config.json`. | Build cost model — price the "free" territory |

## Notes for future iterations

- `build_maps.py` validates on every run: node sums vs market targets, phase cumulatives vs
  40/75/90, and every category against `config/config.json` → `venue_categories`. It exits non-zero
  on mismatch, so edit `markets.json` and re-run rather than hand-editing the HTML.
- Road labels auto-place at the point along each polyline farthest from any node *and* from
  previously-placed labels. Adding nodes near a corridor will move its label — that's intended.
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
