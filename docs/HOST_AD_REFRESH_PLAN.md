# Host Venue Ad Refresh — Operating Plan

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

Expect roughly 20% A, 50% B, 30% C. That split is what makes this finishable.

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

That is ~8 hours a week of focused work. At 10/week you clear 80 venues in
**8 weeks**, plus a 2-week buffer for stragglers = one quarter, done.

Batch by market so travel and context stay cheap:
Weeks 1–4 Oxford (75 screens) → Weeks 5–6 Starkville → Weeks 7–8 Tupelo →
Week 9 Columbus + West Point → Week 10 catch-up.

---

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
conversions a week → that alone justifies the whole program.

---

## 6. Tracking it

Do not build a new tool. Use what is there:

- **Production status** → `creative_requests` (draft → proof sent → approved →
  published).
- **What is live** → `loop_items` updated Friday. If the book of record does
  not get updated the same day, the reconcile reports rot within a month.
- **Upsell status** → host pipeline deals, `deal_type='host'`, one deal per
  venue, stage-moved on every call.
- **Weekly number that matters** → venues refreshed this week / 10, and upsell
  conversations held / 10. Two numbers. Post them Friday.

---

## 7. Make it a cycle, not a project

Set the refresh interval at **12 months**, staggered. Once the first pass is
done, roughly 7 venues come due per week forever — which is *less* than the
push rate, so the rhythm carries itself. Add a `last_creative_refresh` date to
the venue record and let the SLA logic surface what is due, same as follow-ups.

The panic is because it looks like one giant undefined pile. After Week 0 it is
a list of 80 rows, 10 get crossed off a week, and the thing ends on a date you
can point at on a calendar.

---

## 8. What to do tomorrow

1. Pull the venue list and tier it (half a day).
2. Pick the 10 Oxford venues for Week 1 — the 10 easiest, not the 10 most
   important. Momentum first.
3. Build the Business Promo template only. The other two can wait a week.
