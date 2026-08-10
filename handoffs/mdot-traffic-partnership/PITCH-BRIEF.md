# MDOT Traffic Sponsorship — Pitch Brief

**Internal only — do not forward.** The companion file `mockup.html` is the show-piece and is
safe to put in front of MDOT; this brief is not.

**Contact:** Mikey Flood, Mississippi Department of Transportation (personal friend of Creed's).
He most likely does not know the MCTV network exists. That is a feature, not a bug — the first
conversation is a reveal, not a sales call.

---

## The hook (one sentence)

**MDOT is already on our screens — we want to make it official.**

MCTV's content loop runs a live road-conditions segment built on MDOT's public traffic data, on
125+ screens, in every 15-minute loop, all day. That segment already reaches 1.9M+ monthly
impressions across five North Mississippi markets. The pitch is not "please buy ads." It's
"your data is already doing good work on our network — put your name on it and take the
message slot that comes with it."

## Why MDOT wins

- **Reach drivers minutes before they drive.** Restaurants, gyms, waiting rooms — average
  visit is 55+ minutes. Long enough to actually read a work-zone or seat-belt message, and
  everyone in the room is about to get in a car.
- **An owned safety-message slot, not just a logo.** Work zones, Click It or Ticket, move-over
  law, severe-weather alerts — MDOT controls the message, we handle the screens.
- **Branded bookends on every play.** The segment opens on an MDOT intro slate and closes on
  an MDOT outro ("Drive safe, Mississippi." + MDOTtraffic.com plug). The full 20-second
  segment (4s intro + 12s conditions + 4s outro) plays 4×/hour, 12 hours a day, on 125+
  screens — roughly **33+ hours of MDOT-branded airtime every day** across the network. Use
  the "Play full segment" button on the mockup to run it in real time for Mikey.
- **Zero infrastructure cost.** The screens are up, powered, and already showing this
  information. There is nothing to build, install, or maintain.
- **It grows statewide on its own.** Active: Oxford (75), Starkville (30), Tupelo (25).
  Opening: Columbus, West Point. Roadmap: Southaven/DeSoto County, Jackson metro, Hattiesburg,
  Gulf Coast. MDOT's branding extends to every new market automatically — a statewide agency
  ends up with statewide coverage without renegotiating.

## First touch (friend mode, not sales mode)

Keep it personal, short, and curiosity-driven. One text or email, one photo of a screen in a
real venue, the mockup link, and a 15-minute ask. Do **not** attach a proposal.

**Text draft:**

> Mikey! Great catching up, man. Random thing I wanted to show you — Mary Michael and I run a
> network of 125+ TV screens in restaurants, gyms, and waiting rooms across Oxford, Starkville,
> and Tupelo. Our screens already show live road conditions pulled from MDOT's traffic feed,
> and it got me thinking about something that could be good for y'all. Mocked up what it could
> look like: [mockup link]. Got 15 minutes this week for a call? No pitch deck, I promise.

**Email draft (if he's more of an email guy):**

> Subject: Your traffic data is already on 125 screens in North MS
>
> Mikey,
>
> Great reconnecting. Quick thing I've been chewing on since we talked.
>
> Mary Michael and I own MCTV — a network of 125+ indoor digital billboard screens in
> restaurants, gyms, clinics, and shops across Oxford, Starkville, and Tupelo. About 1.9
> million views a month. Here's the part that made me think of you: our content loop already
> includes a live road-conditions segment built on MDOT's public traffic feed. Your data is
> on our screens right now, every 15 minutes, all day.
>
> I put together a quick mockup of what it would look like if MDOT made it official — your
> name on the segment, plus a safety-message slot y'all would control (work zones, seat
> belts, weather): [mockup link]
>
> No idea if this fits anything MDOT does, honestly — that's why I'm coming to you first.
> Got 15 minutes this week?
>
> Creed

## Meeting flow (three beats, ~15 minutes)

1. **What MCTV is (60 seconds, pictures not stats).** "You know the TVs on the wall at
   [venue he knows]? That's us." One or two venue photos. Then the two numbers that matter:
   125+ screens, people sit in front of them for 55 minutes.
2. **Show the mockup.** Pull it up, flip between Oxford/Starkville/Tupelo. Point at the
   safety-message card: "That slot would be yours." Point at the roadmap: "And it follows us
   into every new city." Then stop talking and let him react.
   **Morning-of move:** swap the sample travel times and work-zone alert for that day's real
   conditions from MDOTtraffic.com (they're in the `MARKETS` object at the bottom of
   `mockup.html`). It turns the mockup from an illustration into proof: "this is your feed,
   on our screens, right now." MDOT staff know their active projects — a made-up work zone
   is the one detail that could break the spell mid-demo.
3. **The real ask.** Not "buy this." It's: **"Does this fit anything MDOT does? Who inside
   would care about it — public affairs, the safety office, a district engineer? Would you
   introduce us?"** Mikey's value is navigation, not a purchase order. If he leaves the
   meeting as our internal champion, the meeting was a win.

## The four packages on the mockup

The mockup's package toggle shows MDOT four ways to buy, each with its own scenic intro/outro
world and a localized conditions board:

- **Oxford** (75 screens) — flagship. Dusk-over-the-hills backdrop, Hwy 6 / Hwy 7 corridors.
- **Tupelo** (25 screens) — Natchez Trace dawn backdrop. I-22, US 45, 45 Alt corridors.
  Cheapest single-market pilot (~$700/mo anchor from the summer package).
- **Golden Triangle** (33 screens = Starkville 30 + Columbus 2 + West Point 1) — cotton-field
  dusk with the water tower. Sells the three-city footprint as one buy; MS 12 / US 82 /
  MS 50 / US 45 / MS 25 corridors.
- **Jackson** (expansion preview — clearly labeled, no live screens) — night skyline with
  I-55/I-20 light trails. This is the "come grow with us" card: MDOT HQ is in Jackson, their
  people will want to see their own city, and it shows the sponsorship arriving there on
  day one of our expansion. Never pitch it as current inventory.

**Production notes (internal):**
- The scenic backdrops are original MCTV concept art built into the mockup — no stock
  licensing needed for the pitch. For production, the intro/outro render as full-motion
  video through our existing Creatomate pipeline (`services/creatomate_service.py`), and we
  can commission real footage (Natchez Trace, the Square, Jackson skyline) once there's a
  signed deal to justify it.
- **The camera tile is a deliberate conversation starter.** MDOTtraffic.com runs live
  traffic cameras (heaviest in the Jackson metro). Ask Mikey: who manages camera feeds, and
  could feed access be part of the data partnership? A real MDOT camera on our screens makes
  the segment appointment viewing — and it's a reason MDOT *wants* this deal beyond the logo.

## Money framing

**Do not lead with a number.** Let Mikey tell us how MDOT spends on public outreach before
quoting anything. Two paths, in order of preference:

1. **Paid sponsorship.** Anchor internally against our own packages (network-wide holiday
   package runs $2,000/mo). A fair opening frame for a statewide agency: **$1,500–$2,500/mo,
   12-month term, all current markets + every expansion market included as it launches.**
   "Statewide coverage at today's network price" is the line. A single-market pilot
   (Oxford, ~$700–$1,300/mo, 3–6 months) is the fallback if budget is tight or procurement
   is slow — small enough to fit discretionary thresholds, and it gets the logo on air.
2. **In-kind partnership (door-opener).** If paid media is a dead end: an official data
   partnership — MDOT blesses the segment, provides the logo and safety messages, maybe a
   press release. Costs them nothing, makes us "official MDOT partner" in every future
   pitch, and keeps the paid conversation alive for next fiscal year.

**Public-agency reality (verify with Mikey, don't assert):**

- Agencies buy media through procurement — small pilots may fit under bid thresholds,
  bigger buys may need a process. Ask how they've bought outreach/media before.
- Mississippi's fiscal year starts **July 1** — we just entered FY, which cuts both ways:
  this year's budgets are set (an unspent line item could move fast), and planting the seed
  now positions us for next year's budget cycle.
- Some highway-safety campaign money (Click It or Ticket, etc.) flows through the **Office of
  Highway Safety under DPS**, not MDOT. If Mikey says "that's not our budget," that's not a
  no — it's a second door. Ask who runs those campaigns' media buys.
- Whoever the real buyer is, the ask of Mikey stays the same: navigation and an intro.

## Doors this opens (the bigger game)

An MDOT logo on the network is a credibility asset worth more than the first check:

- **Visit Mississippi / Tourism** — welcome-to-town and events content, sponsored.
- **MS Dept. of Health, MEMA** — public-health and emergency-alert messaging.
- **Universities** (Ole Miss, MSU) — campus alerts and athletics content.
- **Venue recruiting in expansion markets** — "our network carries official MDOT road
  conditions" is a strong line when signing hosts in Southaven, Jackson, Hattiesburg, and
  the Coast. (Note: Jackson is OnTargetTV's home turf — a state-agency partnership is
  exactly the kind of differentiator we'd want walking into that market. Never imply we
  have screens where we don't; the mockup labels those cities as roadmap.)
- **Other MDOT districts** — a North MS pilot that works is a template the agency can scale.

## Ground rules

- **The mockup now uses MDOT's real logo — only inside the screen frame.** It's the official
  mark (pulled from the public SVG on Wikimedia Commons, byte-identical to the source), shown
  strictly to illustrate the proposed sponsorship, with a caption saying final usage is
  subject to MDOT approval. Deliberately NOT used: a side-by-side MCTV × MDOT co-brand lockup
  in the page header — that reads as an *existing* partnership and is the kind of thing that
  gets a concept page forwarded to an agency's legal team instead of its comms team. Keep it
  that way, and don't use the logo in any public-facing material until MDOT approves it.
- The mockup is labeled "concept, sample data" — keep it that way until there's a signed
  agreement and real feed integration on the sponsor slot.
- The sample safety message avoids specific legal claims ("fines double") in MDOT's voice —
  if they engage, ask for their current campaign language rather than writing our own.
- Everything in "Public-agency reality" above is our homework, not verified fact. Frame those
  as questions for Mikey, not claims.
