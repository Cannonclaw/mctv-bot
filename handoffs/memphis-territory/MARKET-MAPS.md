# Strategic Market Maps — Memphis/DeSoto Expansion + Tupelo Densification

**Companion to:** `TERRITORY-BRIEF.md`
**Visual version:** `market-maps.html` (generated — run `python3 handoffs/memphis-territory/build_maps.py`)
**Data:** `markets.json` · **Status:** Iteration 2 — targets re-cut to pricing tiers
**Last updated:** 2026-08-04

---

## How to read these maps

MCTV screens don't sell by city, they sell by **node** — a commercial cluster where the right venue
categories sit close enough together that one rep can walk it and one advertiser buy feels local.
Every market below is broken into nodes, each with a screen target, the venue categories that
actually exist there, and why it ranks where it does.

Category names come from `config/config.json` → `venue_categories`, so these maps speak the same
language as proposals and `loop_items`.

Density benchmarks from our own network:

| Market | Screens | Population | Density |
| --- | --- | --- | --- |
| Oxford | 75 | 27,135 | **1 per 362** ← the proven ceiling |
| Starkville | 30 | ~25,000 | ~1 per 833 |
| Tupelo | 25 | 38,091 | **1 per 1,524** ← under-built |
| Columbus | 2 | — | unfinished |
| West Point | 1 | — | unfinished |

DeSoto County at Oxford density would be ~547 screens. That is the size of the prize, not a Phase 1
number.

---

## Why the phase lines sit where they do

`config/config.json` → `pricing.elite_tiers` charges by screen count:

| Tier | Screens | Monthly | Cost/screen |
| --- | --- | --- | --- |
| 1 | 10 | $350 | $35.00 |
| 2 | 20 | $500 | $25.00 |
| 3 | 40 | $800 | $20.00 |
| 4 | **75+** | **$1,300** | $17.33 |

A phase that ends *between* tiers means screens we hang but cannot bill. Iteration 1's ranges
(32–39 / 57–69 / 65–79) all landed in dead zones — at 39 DeSoto screens a county-only advertiser pays
the **20-screen rate** while we carry 19 unbilled screens.

Phase boundaries now sit **exactly on tier thresholds**:

| Phase | Markets | Adds | Cumulative | Tier unlocked |
| --- | --- | --- | --- | --- |
| **1** | Olive Branch + Hernando | 40 | **40** | $800 |
| **2** | + Southaven | 35 | **75** | **$1,300** |
| **3** | + Horn Lake / Walls / Nesbit | 15 | **90** | $1,300 + sell-through headroom |

This doesn't move any screens — only how many land per phase. It makes the top tier sellable as a
DeSoto-only buy a full phase earlier.

**The same logic applies to Tupelo.** It sits at 25 screens today (the 20-screen tier). Adding 50
puts it at **75** — the top tier, for a Tupelo-only buy, in a market we already own.

---

## MARKET 1 — Olive Branch (Phase 1 flagship)

**Pop 47,819 · Mississippi's #1 "boomtown" · highest-income slice of the highest-income county in MS**

Target: **24 screens**

| Node | Geography | Screens | Categories | Why |
| --- | --- | --- | --- | --- |
| **Goodman @ Pleasant Hill** | MS-302, businesses both sides, Target + shopping centers | **9** | Bar/Restaurant, Retail & Boutique, Health & Fitness, Medical & Dental, Barbershop/Salon | Primary retail spine of Olive Branch and northern DeSoto County. Anchor node — build here first. |
| **Craft Rd / I-22 corridor** | Craft Road exit off I-22, mixed-use + industrial-adjacent | **5** | Gas/Grocery, Bar/Restaurant, Auto Shop, Professional Services | Catches the **Marshall County commuter flow** — Jabil, Amazon, Baxter. These are the paychecks that don't get spent in Byhalia. |
| **Old Towne Main Street** | Between Hwy 305, Hwy 178, Goodman Rd | **6** | Retail & Boutique, Bar/Restaurant, Barbershop/Salon, Non-Profit/Community | Walkable historic district — gifts, collectibles, antiques, local restaurants. **The Oxford Square analog.** |
| **The Cascades** | New mixed-use: restaurant parcels, 100 townhomes, 58 cottage lots, 70-acre park | **4** | Bar/Restaurant, Retail & Boutique, Professional Services | Under construction. Sign hosts *before* tenants open — first-mover on a brand-new development is the cheapest inventory we will ever buy. |

**Why the flagship and not Southaven:** highest household income, fastest momentum, adjacent to the
job boom, and likely the *thinnest* incumbent presence — a small operator starting in DeSoto County
almost certainly started in Southaven.

---

## MARKET 2 — Hernando (Phase 1 co-launch)

**Pop 19,165 · +10.96% since the 2020 census (+1.81%/yr) — fastest-growing in the county · county seat**

Target: **16 screens**

| Node | Geography | Screens | Categories | Why |
| --- | --- | --- | --- | --- |
| **Courthouse Square / Commerce St** | Historic downtown | **8** | Bar/Restaurant, Retail & Boutique, Barbershop/Salon, Professional Services, Non-Profit/Community | Boutiques, retailers and restaurants ringing a walkable square, plus the **Hernando Farmers Market every Saturday, May–October** with live music. Oxford's playbook on a smaller stage. |
| **McIngvale Rd / I-55** | Off I-55, south of E Commerce St | **5** | Bar/Restaurant, Retail & Boutique, Gas/Grocery, Medical & Dental | Existing 68,865 sq ft center plus **McIngvale Square** — 27,000 sq ft of retail/restaurant/office/residential on 4 acres, explicitly to pull high-end dining east toward the interstate. |
| **Hwy 51 corridor** | North–south through town | **3** | Auto Shop, Gas/Grocery, Health & Fitness | Fill-in. Service businesses and auto. |

**Why it co-launches:** small enough to *own outright* in one build. Owning a county seat's entire
square is a far better sales story than being 15% of Southaven, and it gives the rep a finished
reference market to show Olive Branch and Southaven prospects.

---

## MARKET 3 — Southaven (Phase 2)

**Pop 58,551 · largest city in DeSoto County · richest venue inventory · most contested**

Target: **35 screens** — takes the county to 75 and unlocks the $1,300 tier

| Node | Geography | Screens | Categories | Why |
| --- | --- | --- | --- | --- |
| **Silo Square** | S of Goodman, W of Getwell, E of Tchulahoma | **11** | Bar/Restaurant, Liquor/Wine/Beer, Retail & Boutique, Barbershop/Salon, Gas/Grocery | $200M town-square development, ~29 businesses. Wine bar, music hall, barber shop, South Point Grocery. **The single best venue cluster in the county.** |
| **Goodman Rd spine** | Primary retail corridor, seconds off I-55 | **10** | Bar/Restaurant, Retail & Boutique, Health & Fitness, Auto Shop, Medical & Dental | The city's main commercial artery and the deepest bench of independent service businesses. Most likely where the incumbent started. |
| **Snowden District** | BankPlus Amphitheater, Snowden Grove Park, Shoppes at Snowden Grove | **7** | Family Rec & Entertainment, Bar/Restaurant, Gas/Grocery, Retail & Boutique | **Sleeper node.** Youth baseball complex — tournament weekends park hundreds of families for hours between games. Highest captive dwell time in the county. |
| **Tanger Outlets / Airways @ Church** | I-55/I-69 at Church Rd | **4** | Bar/Restaurant, Travel & Tourism, Gas/Grocery, Barbershop/Salon | 70 stores, 330K sq ft, pulls shoppers from Tennessee — but tenants are national chains buying at corporate. **Target the surrounding service businesses.** |
| **Landers Center** | 4560 Venture Dr — 10,000-seat arena, Memphis Hustle | **3** | Family Rec & Entertainment, Bar/Restaurant, Travel & Tourism | Event-driven. Worth as much as a marquee host logo on the deck as for raw impressions. |

**Sequencing:** go here *second*, with Olive Branch and Hernando live. Walking into Southaven with two
finished networks and a real traction report beats walking in with a pitch deck.

---

## MARKET 4 — Horn Lake / Walls / Nesbit (Phase 3 fill-in)

**Horn Lake 26,738 (flat, -0.01%/yr) · Walls 1,437 · Nesbit unincorporated (~6,700–9,500)**

Target: **15 screens** — takes the county to 90, giving sell-through headroom above the 75 threshold

| Node | Screens | Categories |
| --- | --- | --- |
| **Goodman Rd West** | **5** | Bar/Restaurant, Retail & Boutique, Auto Shop, Gas/Grocery |
| **Church Road** | **4** | Health & Fitness, Medical & Dental, Barbershop/Salon |
| **Tulane Road** | **3** | Auto Shop, Gas/Grocery, Bar/Restaurant |
| **Walls / Nesbit** | **3** | Gas/Grocery, Bar/Restaurant, Auto Shop |

Real households, no growth story. Add once a rep is already driving the county weekly — marginal
servicing cost is near zero at that point.

---

## MARKET 5 — Tupelo densification (parallel track — no territory negotiation required)

**Pop 38,091 · larger than Oxford · 25 screens today (1 per 1,524) vs Oxford's 1 per 362**

Target: **+50 screens → 75 total**, which unlocks the $1,300 tier for a Tupelo-only buy

| Node | Geography | Screens | Categories | Why |
| --- | --- | --- | --- | --- |
| **NMMC medical district** | North Mississippi Medical Center + surrounding medical office buildings | **15** | Medical & Dental, Professional Services, Bar/Restaurant, Gas/Grocery | **The best untapped node in the whole network.** 640 beds; largest non-metro hospital in America; largest private not-for-profit hospital in Mississippi. Serves 730,000 people across 24 counties in MS, AL and TN. Wall-to-wall waiting rooms — **our highest dwell-time category** — with a *regional* catchment, not a local one. |
| **Barnes Crossing District** | Super-regional mall + strip centers, 1.5M+ sq ft retail | **12** | Retail & Boutique, Bar/Restaurant, Health & Fitness, Barbershop/Salon | Largest retail concentration in Northeast Mississippi. Strip-center independents, not mall anchors. |
| **North Gloster St** | Primary retail corridor | **10** | Bar/Restaurant, Auto Shop, Retail & Boutique, Medical & Dental | Steady daily traffic. Our own Tupelo marketing already names this corridor — the story is written, the screens just aren't there. |
| **Downtown Main / Fairpark** | Civic and dining core | **8** | Bar/Restaurant, Retail & Boutique, Non-Profit/Community, Professional Services | The walkable node. Oxford playbook again. |
| **Hwy 45 / W Main** | Service corridors | **5** | Auto Shop, Health & Fitness, Gas/Grocery | Fill-in. |

**This track needs no permission from anyone.** No territory grant, no new rep, no market education —
hosts already know the brand and traction reports already exist. If DeSoto is the land grab, Tupelo is
the money sitting on the table.

---

## Competitive overlay — DeSoto Local

**Status: unknown, and it is the single biggest gap in this map.**

We know the operator (Desoto Local, Inc. / Brandy Faulkner, an N-Compass–NTV360 dealer) and their
described footprint ("restaurants to gyms, doctors' offices to auto repair" across DeSoto County). We
do **not** know which venues, how many licenses, or when contracts expire — and it is not publicly
discoverable. Their site 403s automated fetches and no aggregator publishes N-Compass venue lists.

Nodes are flagged `clear` / `assumed contested` / `unknown` in `markets.json` and rendered on the
visual map. Those flags are assumptions, deliberately shown as such.

**Working assumption:** a small operator building DeSoto County starts in **Southaven** (largest city,
densest retail) and works outward along Goodman Road. That assumption is *why* Olive Branch and
Hernando go first.

**The NTV360 license export from n-Compass closes this in one file.** Every flag gets re-cut the
moment it lands.

---

## Network math

| | Screens |
| --- | --- |
| Network today (Oxford 75, Starkville 30, Tupelo 25, Columbus 2, West Point 1) | **133** |
| + DeSoto build (Phases 1–3) | +90 |
| + Tupelo densification | +50 |
| **Network after** | **273** |

---

## Open questions this map can't answer yet

1. **Venue-level competitive overlay** — needs the NTV360 license export from Don.
2. **Host economics in DeSoto** — our model is $0-cost hosting (`host_free_inside_plays_per_hour: 8`),
   not revenue share. Does that hold in a Memphis-DMA suburb where the incumbent may have offered
   rev-share?
3. **Rep coverage** — 90 DeSoto screens is not a remote-managed market. Who lives there?
4. **Hardware and install cost per screen** — the real price of "free" territory. Needed before
   agreeing to any build-out clause.

---

## Sources

- [Southaven commercial real estate corridors — Jones AUR](https://jonesaur.com/southaven-commercial-real-estate/)
- [Silo Square — official site](https://www.silosquarems.com/our-businesses) · [Visit DeSoto County](https://www.visitdesotocounty.com/venues/detail/silo-square)
- [Tanger Outlets Southaven — Wikipedia](https://en.wikipedia.org/wiki/Tanger_Outlets_Southaven)
- [Snowden District — City of Southaven](https://www.southaven.org/711/Snowden-District) · [Snowden Grove Park](https://en.wikipedia.org/wiki/Snowden_Grove_Park)
- [Landers Center — Wikipedia](https://en.wikipedia.org/wiki/Landers_Center)
- [Olive Branch city guide — Homes.com](https://www.homes.com/local-guide/olive-branch-ms/)
- [Olive Branch Old Towne Main Street — Visit Mississippi](https://visitmississippi.org/things-to-do/shopping/olive-branch-old-towne-main-street/)
- [The Cascades — Olive Branch](https://www.explorecascades.com/) · [DeSoto County News](https://desotocountynews.com/desoto-county-news/cascades-development-welcomed-in-olive-branch/)
- [Hernando Courthouse Square — Visit Mississippi](https://visitmississippi.org/things-to-do/shopping/hernando-courthouse-square/)
- [Hernando Farmers Market — City of Hernando](https://www.cityofhernando.org/departments/community-development/farmers-market)
- [McIngvale Square development — DeSoto County News](https://desotocountynews.com/desoto-county-news/mcingvale-square-development-planned-in-hernando/)
- [Mall at Barnes Crossing — Wikipedia](https://en.wikipedia.org/wiki/Mall_at_Barnes_Crossing) · [Barnes Crossing District — Visit Tupelo](https://www.tupelo.net/directory/barnes-crossing-district/)
- [North Mississippi Medical Center–Tupelo — NMHS](https://www.nmhs.net/locations/north-mississippi-medical-center-tupelo)
- [MCTV Tupelo advertising page](https://mctvofms.com/tupelo-advertising/)
