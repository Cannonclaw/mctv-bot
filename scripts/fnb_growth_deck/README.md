# FNB "Grow With Us" Deck + Market Ticker

Client-facing upsell materials for FNB Oxford Bank, built from their
Jan 31 – Jul 20, 2026 traction report. Two generations live here:

- **`build_story_deck.js`** — the current 12-slide story deck (dark navy/gold,
  full-bleed brand art, Market Ticker flagship offer). This is the one to use.
- **`build_deck.js`** — the original 11-slide light/dark deck (kept for reference;
  reads `fnb_data.json`).
- **`market_ticker.html`** — the animated Market Ticker product mock
  (1920×1080, screen-ready, CSS-animated scrolling tape). Open in any browser.
  Record it with Playwright or screenshot via `shot_product.js`.

## Story deck arc (build_story_deck.js)

1. Cover — full-bleed billboard art, "GROW WITH US."
2. Partners — FNB Oxford Bank + The Grove Collective panels
3. Results — 392,395 plays hero + KPI band
4. Daily life — moments art strip (monoline gold icons)
5. Receipts — top-venue table + market split + Starkville gap
6. $0.59 CPM vs. billboards/digital/social
7. Grow With Us map (5 markets, Starkville glowing open)
8. **Flagship: Market Ticker** — $3,000/mo exclusive, Oxford + Tupelo
9. Grove Collective tie-in — NIL give-back story
10. The ask — Market Sponsor $3,000/mo vs. Grow With Us Plan $10,000/yr
11. Why now — season timing, exclusivity, momentum
12. Close — team cards, "We're neighbors."

## Build

```bash
cd scripts/fnb_growth_deck
npm install pptxgenjs playwright   # playwright only needed to regenerate art
node build_story_deck.js           # → output/decks/FNB_GrowWithUs_Story_Deck.pptx
soffice --headless --convert-to pdf ../../output/decks/FNB_GrowWithUs_Story_Deck.pptx
```

## Regenerating the art

The deck composites pre-rendered PNGs (committed alongside): `art_cover.png`,
`art_map.png`, `art_moments.png` (from the matching `art_*.html` boards),
`frame_product.png` (a frozen frame of `market_ticker.html`), and matched-crop
team headshots (`team_*.png`). After editing any art board:

```bash
node render_art.js      # re-renders the three art boards
node shot_product.js    # re-freezes the ticker product frame
node build_story_deck.js
```

## Notes

- FNB and Grove Collective appear as typographic lockups; swap in their real
  logo files (drop-in slots on slides 2/8/9 and in `market_ticker.html`) once
  the logo assets are available.
- Pricing on slides 8–10 must stay in sync with `config/config.json`
  (`sponsorship_packages`, tiers) when rates change.
- All FNB performance numbers come from the NTV360 traction report for
  Jan 31 – Jul 20, 2026 (also captured in `fnb_data.json`).
