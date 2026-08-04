# What "Free Territory" Actually Costs

**Companion to:** `TERRITORY-BRIEF.md` · **Interactive version:** `cost-model.html`
(run `python3 handoffs/memphis-territory/build_cost_model.py`)
**Status:** Iteration 4 · **Last updated:** 2026-08-04

---

## The headline

**The franchise fee is not the price of this territory.**

n-Compass publishes a **$35,000** franchise fee. That is a one-time number, and it is the part Don
is offering to waive. It also publishes an ongoing royalty of **$500/month flat plus $75 per
billboard per month**.

At the 90-screen DeSoto build:

| | Amount |
| --- | --- |
| Franchise fee (waived) | **$35,000 once** |
| n-Compass royalty | **$87,000 per year** |
| Same royalty over 5 years | **$435,000** |

The waived fee is roughly **7%** of what the territory actually costs to hold over five years. The
gift is the small number. The subscription is the big one.

> **Verify this against our own agreement before acting on it.** These are n-Compass's published
> *franchise* terms. We already run 133 screens on NTV360, so we may be on dealer terms,
> grandfathered terms, or a different per-screen rate. If so, the published figures don't apply to
> us. Every input in `cost-model.html` is editable for exactly this reason.

---

## Fifth question for Don

The brief lists three questions. The metro map added a fourth. This adds a fifth:

> **Does the DeSoto territory come under our existing agreement, or a new one?**

Waiving a $35,000 fee while attaching $75/screen/month to 90 new screens is not a gift — it is a
subscription with a discounted signup. Both can still be worth it. But we should know which deal
we're signing.

---

## The model

Defaults, all editable in the interactive version:

| Input | Default | Basis |
| --- | --- | --- |
| Display + media player | $450/screen | Below the $1,800–$3,500 industry figure for fully installed *commercial-grade* panels — our venue screens are smaller consumer/light-commercial units |
| Mount + installation | $150/screen | Low end of the $150–$3,000 industry range |
| n-Compass royalty | $75/screen/mo | n-Compass published figure — **the input that matters most** |
| Connectivity / data | $15/screen/mo | Estimate |
| n-Compass flat fee | $500/mo | n-Compass published figure |
| Rep (base + commission) | $4,500/mo | 90 screens across DeSoto is not a remote-managed market |
| Advertisers sold | 20 | Steady-state assumption |

### Results by phase

| Phase | Screens | Rate card | Capex | Monthly cost | Break-even |
| --- | --- | --- | --- | --- | --- |
| 1 — Olive Branch + Hernando | 40 | $800/mo | $24,000 | $8,600 | **11 advertisers** |
| 2 — + Southaven | 75 | $1,300/mo | $21,000 | $11,750 | **10 advertisers** |
| 3 — + Horn Lake / Walls / Nesbit | 90 | $1,300/mo | $9,000 | $13,100 | **11 advertisers** |

### At full build

| | Monthly | Annual |
| --- | --- | --- |
| n-Compass royalty (90 × $75 + $500) | $7,250 | $87,000 |
| Connectivity | $1,350 | $16,200 |
| Rep | $4,500 | $54,000 |
| **Total cost** | **$13,100** | **$157,200** |
| 20 advertisers × $1,300 | $26,000 | $312,000 |
| **Margin** | **$12,900** | **$154,800** |

- **Total capex to 90 screens: $54,000** — which lands inside the $48,150–$120,405 range n-Compass
  publishes for a new franchise. That's a reasonable sanity check on the per-screen defaults.
- **Capex payback: ~5 months** at 20 advertisers.

---

## Two things the model shows that the spreadsheet intuition misses

**1. Break-even is in advertisers, not dollars — and it *improves* with scale.**

Phase 1 needs 11 advertisers. Phase 2 nearly doubles the screen count and needs **10**. Crossing 75
screens lifts the rate card from $800 to $1,300 per advertiser, so revenue per advertiser rises
faster than cost per screen. This is the arithmetic behind phasing to the tier lines instead of
stopping short of them — the same finding as the market maps, now with the cost side attached.

**2. Capex is the small problem; the royalty is the big one.**

Hardware is $54,000, once. The recurring n-Compass line is $87,000 *every year*. Set the royalty
input to $0 in the model and break-even drops from **11 advertisers to 5** — that single line is
more than half the cost of running the territory.

That is why the fifth question matters more than the first four.

---

## What this does not cover

- **Host acquisition cost** — the time to sign ~90 venue agreements. Real, and not modelled.
- **Creative production** — ad builds for new advertisers.
- **Ramp** — the model shows steady state, not the months spent selling into an empty network.
- **Category exclusivity premiums** — upside not counted here.
- **Our actual n-Compass terms** — the biggest unknown on the page.

---

## Sources

- [NTV360 franchise costs and fees — Franchise Gator](https://www.franchisegator.com/franchises/ntv360/)
- [NTV360 franchise analysis, FDD — Franzy](https://franzy.com/franchises/ntv360)
- [NTV360 franchise review 2026 — Franchise Chatter](https://www.franchisechatter.com/2026/02/20/ntv-360-franchise-review-2026-costs-fees-news-average-revenues-and-or-profits/)
- [N-Compass TV dealer opportunity — BizBuySell](https://www.bizbuysell.com/franchise-for-sale/n-compass-tv/)
- [Digital signage cost breakdown 2026 — Pickcel](https://www.pickcel.com/blog/what-is-the-cost-of-digital-signage-ownership/)
- [Digital signage total cost of ownership 2026 — Creation Networks](https://creationnetworks.net/blogs/audio-visual-technology-news/digital-signage-cost-a-complete-total-cost-of-ownership-guide-2026)
- Rate card: `config/config.json` → `pricing.elite_tiers`
