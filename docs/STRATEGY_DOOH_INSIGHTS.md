# DOOH Industry Insights → MCTV Operational Strategy

**Source:** Industry discussion on digital out-of-home (DOOH) buying, CTV
integration, full-funnel planning, and measurement (transcribed audio,
July 2026). This document translates those insights into concrete changes
to MCTV Elite Advertising's operational norms, sales strategy, and product.

**Status:** Living document. The source discussion was captured in part —
the segment on delivery verification / QC (the "Moat/IAS for out-of-home"
question) was cut off mid-answer and will be folded in when the remaining
audio arrives.

---

## The three questions every DOOH buyer conversation must answer

The discussion framed the entire DOOH buying problem as three questions.
These now become the backbone of how MCTV positions, proposes, and reports:

1. **Do they know what they're buying?** (transparency)
2. **How are they treating it against the rest of their spend?** (planning)
3. **How are they measuring it?** (measurement)

Every proposal, sales conversation, and traction report should be able to
answer all three without the client having to ask.

---

## Insight 1 — The transparency gap is the industry's biggest weakness. It is MCTV's biggest strength.

**What was said:** PMP (private marketplace) is the primary mode of
transacting in DOOH because buyers need trust and transparency about
"what the heck am I buying." A CTV network founder described a previous
company selling "CTV inventory" that was actually a sidebar display ad on
a TV in a bar the buyer had no idea they were in. That disconnect remains
industry-wide.

**Why this matters for MCTV:** Programmatic DOOH resellers sell
abstractions — audiences, impressions, "screens in your DMA." MCTV sells
named venues with photos. An advertiser buying from MCTV knows the exact
gym, restaurant, and coffee shop their ad runs in, in which city, and can
walk in and see it. In an industry where the flagship complaint is "the
buyer had no idea where their ad ran," radical venue-level transparency is
a category-defining differentiator, not just a feature.

**Operational changes:**

- **Proposals lead with named venues.** The Market Coverage section
  (page 4 photo grid) and venue lists are not decoration — they are the
  trust-building answer to question #1. Sales reps should never send a
  proposal without real venue photos assigned when they're available.
- **Add a "Full Transparency" trust point** to the social proof section
  (config.json `social_proof`): every screen has a name, an address, and
  a photo — no black-box inventory, no resold impressions, no "trust us"
  screens.
- **Sales talk track:** when a prospect mentions digital/programmatic
  spend, contrast directly: "With programmatic out-of-home you buy an
  audience estimate. With us you buy 20 specific screens you can drive
  past and walk into. Same accountability you'd expect from a billboard,
  with digital flexibility."
- **Never sell abstraction we can't show.** If we ever broker or extend
  inventory beyond our owned network, it gets the same venue-level
  disclosure or we don't sell it.

## Insight 2 — Treat DOOH as a full-funnel channel with its own line item, not an add-on.

**What was said:** No one has figured out integrating DOOH with CTV buys.
Best practice is to keep them as **separate line items with separate
KPIs**, and to think of DOOH as a **full-funnel channel**: large
high-impact formats for awareness, street-level placements for
consideration, 1:1 down-funnel placements (e.g., rideshare back seats).
Team segmentation (CTV team vs. OOH team vs. digital team) is what's
prohibiting growth. Picking formats/venues/regions is harder than "pick
an audience and press go" — it requires extra thinking, which is where a
good partner earns their keep.

**Why this matters for MCTV:** Our advertisers are local businesses, not
agency trading desks — but the same logic applies at local scale. MCTV's
venue categories map to funnel stages, and the pricing tiers map to funnel
breadth:

| Funnel stage | MCTV equivalent |
|---|---|
| Awareness | Broad screen count across all 5 markets (40 and 75+ screen tiers) — be everywhere your customers already go |
| Consideration | Long dwell-time venues (gyms, restaurants, waiting areas) where a 15-second spot gets watched, not skipped |
| Action | Category exclusivity + venue targeting near the point of decision (e.g., a realtor in coffee shops, a gym near its own neighborhood) |

**Operational changes:**

- **Position MCTV as a line item, not a substitute.** Stop framing MCTV
  as "instead of Facebook ads." Frame it as the physical-world layer of
  the client's plan with its own job and its own KPIs: unskippable local
  presence and frequency against a geographically perfect audience.
  This defuses the "we already do digital" objection — we're not asking
  them to move that budget, we're asking for our own line.
- **Funnel language in proposals.** The Elite Advertiser and Bundle
  generators should describe tier selection in funnel terms (breadth =
  awareness, venue selection = consideration/action) rather than screen
  counts alone. Candidate prompt/config update for `1_Proposals.py`
  section prompts.
- **We do the "extra thinking."** The discussion notes DOOH planning is
  harder than audience-and-go — that difficulty is our service. Reps
  hand-pick venue mixes per client category. Say so explicitly in
  proposals: "You don't pick from a dropdown. We build your screen list
  venue by venue for your customer."

## Insight 3 — Measurement: QR codes are the proof-in-the-wild; exposure data is the gold standard.

**What was said:** A QR scan is a high-intent conversion signal — the
person had to see the ad, be interested, take out their phone, and scan —
but it only captures a segment of the exposed universe. The **cleanest
way to measure OOH is exposure data**: who was exposed, and did something
happen afterward (web lift, conversions, foot traffic). The persistent
challenge is **education** — clients don't know what measurement is
available.

**Why this matters for MCTV:** Our traction reports (NTV360 plays/loops)
are exposure data — we should name them that and build the measurement
ladder around them.

**Operational changes:**

- **QR codes become a default, not an option.** Every ad creative —
  Creatomate video ads and static creatives — should include a QR code
  (or a memorable promo code for QR-hostile creative) pointing to a
  UTM-tagged URL or offer. Norm: no creative ships without a trackable
  response mechanism unless the client declines. Add a QR/tracking field
  to the creative request flow (`11_Creative.py` / portal creative form)
  and to the video ad generator checklist.
- **Frame traction reports as exposure reports.** NTV360 play counts ×
  venue traffic = exposed audience. Reports should present:
  1. **Exposure** — plays, screens, estimated views (already have this)
  2. **Response** — QR scans / promo code redemptions (new, once QR is standard)
  3. **Lift** — client-observed changes: web traffic, walk-ins, "how did
     you hear about us" tallies during the flight (structured prompt in
     the report input)
- **Add a measurement primer to reports.** One short "How to read this
  report" section educating the client on the exposure → response → lift
  ladder. The discussion is explicit that education is the bottleneck;
  a client who understands their report renews.
- **Renewal ammunition.** The Renewal/Upgrade generator should pull the
  strongest measurement artifacts from the flight (best QR month, lift
  anecdotes) as its opening argument.

## Insight 4 — Delivery assurance (verification / "Moat for OOH") — PENDING

The discussion turned to whether an equivalent of Moat/IAS exists for
out-of-home — ensuring delivery and QC (broken screens, defaced ads). The
answer was cut off mid-sentence ("it's less about the defaced things you
might notice, it's a little bit more about…").

**What we can already act on:** MCTV's answer to delivery assurance is
**proof-of-play**. NTV360 logs actual plays per screen. Operational norms:

- Treat proof-of-play data as a first-class trust asset — mention it in
  proposals ("every play is logged; your report shows exactly what ran,
  where, and how many times").
- Screen uptime is part of the product. A dark screen is undelivered
  inventory; venue check-ins / uptime monitoring protect the promise.

*To be completed when the remaining audio arrives.*

---

## Implementation backlog (proposed, in priority order)

| # | Change | Where | Effort |
|---|---|---|---|
| 1 | Add "Full Transparency — named venues, photos, proof-of-play" trust point | `config/config.json` social proof + trust points | Small |
| 2 | Sales talk tracks: line-item positioning, programmatic contrast, "we do the thinking" | This doc → team norms; optionally `6_Samples.py` or Settings reference | Small |
| 3 | QR/tracking mechanism field in creative requests + video ad flow | `11_Creative.py`, `portal_creative.py`, `5_Video_Ads.py` | Medium |
| 4 | Exposure → Response → Lift structure + measurement primer in traction reports | `generators/advertiser_report.py`, `2_Reports.py` input form | Medium |
| 5 | Funnel-stage framing in proposal prompts | `config/prompts.json` (pricing/opportunity sections) | Small |
| 6 | Proof-of-play language in proposals and contracts value recap | `config/prompts.json`, `generators/contract_generator.py` | Small |
| 7 | Delivery-assurance norms (uptime, venue checks) | Pending remainder of audio | TBD |

No application code has been changed yet — this document establishes the
strategy; items above land as separate changes once approved.
