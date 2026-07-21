# FNB "Grow With Us" $10K Deck

Client-facing upsell deck for FNB Oxford Bank, built from their Jan 31 – Jul 20, 2026
traction report. 11 slides, MCTV Original branding (navy `#1B1F3B` / gold `#C5A55A`, Arial),
16:9 widescreen.

## Story arc

1. Cover — Grow With Us
2. Six-month KPI grid (392,395 plays · 65 venues · $0.59 CPM)
3. Top venues + the Starkville gap
4. Category mix chart
5. CPM vs. billboards / digital / social
6. Network growth — FNB in 2 of 5 markets
7. The Starkville opening
8. Market sponsorship packages (from `config.json sponsorship_packages`)
9. **The ask: $10,000/yr** — Starkville year-round ($500/mo partner rate = $6,000)
   + Holiday Shopping sponsorship ($2,000 × 2 = $4,000)
10. Why now (season timing, rate protection)
11. Team + next steps

## Build

```bash
cd scripts/fnb_growth_deck
npm install pptxgenjs
node build_deck.js                       # writes output/decks/FNB_GrowWithUs_10K_Deck.pptx
soffice --headless --convert-to pdf ../../output/decks/FNB_GrowWithUs_10K_Deck.pptx
```

## Reuse for another client

Copy `fnb_data.json`, replace the numbers with the new client's traction report values
(KPIs, top venues, market split, categories, plan line items), and run:

```bash
node build_deck.js my_client_data.json
```

Pricing on slides 8–9 comes from the data file — keep it in sync with
`config/config.json` (`sponsorship_packages`, pricing tiers) when rates change.
