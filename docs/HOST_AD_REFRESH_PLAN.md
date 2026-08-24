# Host Venue Ad Refresh — Operating Plan

**Scope:** 100 host venues · **Duration:** 12 weeks (one quarter)
**Owner:** Swayze (production queue) · Creed & MMC (upsell calls)
**Goal:** every host venue running a current spot, on a repeating cycle, with an
upsell conversation attached to each refresh.

---

## 1. The reframe

This is not 80+ creative projects. It is **one template system run in batches**,
plus a phone call. Two things move independently:

- **Production** — templated, assembly-line, one person, batched by market.
- **Upsell** — the delivery of the new spot *is* the appointment. Never send a
  finished ad by email without a conversation attached to it.

Nothing here requires new software. It uses the loop inventory, host pipeline,
and creative request tables that already exist.

---

## 2. Week 0 — build the list (half a day, once)

You cannot plan against a number you do not have. Before any design work:

1. Pull the host list from `loop_items` / `loop_item_screens` +
   `24_Loop_Inventory.py` → **Inventory** tab. Every host promo is an
   `mode='include'` override or an ROn item — that is your book of record.
2. Cross-check against the Encompass content report (**Reconcile** tab,
   `reconcile_plays()`), which tells you what is *actually airing* today.
3. Build one row per venue in a sheet with five columns:
   `venue · market · current spot file · last updated · tier`.

**Tier each venue A/B/C:**

| Tier | Definition | Treatment |
|---|---|---|
| **A** | High-traffic, multi-screen, or already spends money | Custom-shot, on-site photos, personal delivery meeting |
| **B** | Solid single-screen host, engaged | Template + their existing brand assets, 15-min call |
| **C** | Low-engagement, unresponsive, or seasonal | Template + web-scraped assets, emailed with a one-click approve |

Across 100 venues, plan on roughly **20 A · 50 B · 30 C**. That split is what
makes this finishable: only 20 venues get real creative time, and the 30 C-tier
venues are close to push-button. Do not let the A list grow past 20 — every
venue promoted to A costs you most of a day.

---

## 3. The template system (one week, once)

Build **three master templates** in Canva or Creatomate — not more:

1. **Business promo** — logo, hero photo, 3 lines, offer, contact.
2. **Now hiring / seasonal** — the second-most-requested host spot.
3. **Event / schedule** — for venues with programming (Conference Center type).

Each template gets market-neutral MCTV branding, 15-second runtime to match
`content_loop_minutes`, and locked layout. **Only text, logo, and photo swap.**
The moment someone starts moving boxes, the throughput math breaks.

`services/enrichment_service.py` already scrapes a website for logo, images,
hours, and contact info. Run it once per venue to pre-fill the template inputs
so production starts from a filled form, not a blank page.

---

## 4. The weekly rhythm (this is the actual answer)

**10 venues per week.** That is the whole commitment. Do not raise it.

| Day | Work | Time |
|---|---|---|
| **Mon** | Enrich + draft 10 spots from templates | 3–4 hrs |
| **Tue** | Internal review, fix the 2–3 that need it | 1 hr |
| **Wed** | Send proofs via portal (`portal_creative.py`), request approval | 1 hr |
| **Thu** | **Upsell calls** on last week's approved batch | 2–3 hrs |
| **Fri** | Publish approved spots, update `loop_items`, log activity | 1 hr |

That is ~8 hours a week of focused work. At 10/week you clear 100 venues in
**10 weeks**, plus 2 weeks of buffer for stragglers and reshoots = **12 weeks,
one quarter, done.**

Batch by market so travel and context stay cheap. Venue counts below are
proportional to screen counts — replace them with real numbers after Week 0:

| Weeks | Market | Venues (est.) |
|---|---|---|
| 1–6 | Oxford (75 screens) | ~55 |
| 7–8 | Starkville (30 screens) | ~22 |
| 9–10 | Tupelo (25 screens) | ~19 |
| 10 | Columbus + West Point | ~3 (fold into the Tupelo trip) |
| 11–12 | Buffer — stragglers, reshoots, unresponsive C-tier | — |

Oxford is six straight weeks and it is the hard part. If the rhythm is going to
break, it breaks in week 4. Two ways to protect it: run Oxford as three 2-week
blocks with a named milestone at each, and put the buffer weeks on the calendar
now so slipping a week does not feel like failing.

## 5. The upsell, attached to every delivery

The refresh call has a fixed shape. It is not a pitch, it is a review:

1. **"Here's your new spot."** Show it. Get the yes.
2. **"Here's how the screen did."** Pull the venue traction report
   (`2_Reports.py` venue report). Real numbers, their venue.
3. **The ask** — one of three, chosen before you dial:
   - **Paid screen package** — they host free; adding paid screens across the
     network is the natural next step ($350/$500/$800/$1,300 tiers).
   - **Category exclusivity** — for venues whose competitors are on the network.
   - **DMS / Google Business Profile** — for the venues who say "we don't
     really do marketing." Lowest resistance, recurring, and it makes the ad
     you just built actually work for them.
4. **Never leave without a next date.** Stage-move the deal in
   `20_HostPipeline.py` so `FOLLOW_UP_SLA` schedules the follow-up for you.

Rule of thumb: expect 1 in 5 to take something. Ten venues a week → ~2
conversions a week → **~20 conversions across the quarter.** Even at half that
rate, and even if most land on the cheapest option, the program pays for the
production time several times over.

---

## 6. Tracking it

Do not build a new tool. Use what is there:

- **Production status** → `creative_requests` (draft → proof sent → approved →
  published).
- **What is live** → `loop_items` updated Friday. If the book of record does
  not get updated the same day, the reconcile reports rot within a month.
- **Upsell status** → host pipeline deals, `deal_type='host'`, one deal per
  venue, stage-moved on every call.
- **Weekly number that matters** → venues refreshed this week / 10, upsell
  conversations held / 10, and **cumulative / 100**. Three numbers. Post them
  Friday. The running total against 100 is the one that keeps the panic down —
  it turns an open-ended pile into a bar that visibly fills.

---

## 7. Make it a cycle, not a project

Set the refresh interval at **12 months**, staggered. Because the first pass
runs at 10/week, the venues come due in that same order a year later — which
means only **~2 venues per week** come due, forever. That is a fifth of the push
rate. Maintenance is roughly a two-hour Monday, and the spare capacity absorbs
new hosts as you sign them.

This is built. Migration 026 adds `last_creative_refresh` (a DATE) to the host
deal, and `get_hosts_needing_refresh()` in `services/pipeline_service.py`
surfaces what is due on the `HOST_REFRESH_SLA` cadence — 365 days, live venues
only. It shows up as the "Due for refresh" metric and the "Creative Refresh
Due" list on `pages/20_HostPipeline.py`. Set the date by hand on the venue
record every Friday when the new spot goes up. Nobody has to remember any of
this.

The panic is because it looks like one giant undefined pile. After Week 0 it is
a list of 100 rows, 10 get crossed off every Friday, and it ends on a date you
can circle on a calendar.

---

## 8. What to do tomorrow

1. Pull the 100-venue list and tier it A/B/C (half a day). Cap A at 20.
2. Put the 12 weeks on the calendar now, buffer weeks included, with the Oxford
   milestones at weeks 2, 4, and 6.
3. Pick the 10 Oxford venues for Week 1 — the 10 *easiest*, not the 10 most
   important. Momentum first.
4. Build the Business Promo template only. The other two can wait a week.
