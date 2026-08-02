# mTrade Park — Event Feed & Screen Brief

**Market:** Oxford  **Target:** CageTime indoor practice facility
**Status:** Prospect — feed built, calendar source not yet connected
**Researched:** August 2026

---

## Why this one

We've wanted screens in their batting cages for a while. The event feed is the
way in: it isn't an ad buy, so there's nothing for the Park Commission to
approve, budget, or take to a board. It's their own calendar, on their own wall,
maintained by us. The screens go in to carry it — the paid inventory around it
is the business.

## The facility

- **Address:** 328 Highway 314, Oxford, MS 38655
- **Size:** ~75 acres. Opened 2009 as FNC Park; renamed mTrade Park in 2020 on a
  naming-rights deal.
- **Fields:** 14 baseball/fastpitch fields with FieldTurf infields, 5 full-size
  soccer fields, 7v7 layouts, 1.7-mile paved walking trail.
- **Concessions:** four stands — one at each diamond quad, one at the soccer fields.
- **Operator:** Oxford Park Commission facility.
- **Credential:** named **2025 USSSA Facility of the Year** out of 1,200+
  facilities nationally.

## CageTime — the screen target

The reason this is worth doing:

- **7,500 sq ft** indoor practice facility with **6 retractable batting cages**
  on synthetic turf. Cages raise to the ceiling to open the floor for indoor soccer.
- **An observation deck** where parents and siblings sit and watch from above.
- **A concession stand** inside.
- **Reservation hours Monday–Thursday, 4–9pm**, booked through a third-party
  booking app, plus tournament weekends.

That combination is unusual for us. Most of our inventory is a screen someone
walks past. This is a room where a parent sits for an hour with nothing to do,
in line of sight of a screen, four evenings a week, plus every tournament
weekend from late winter through fall. Dwell time is the whole pitch.

## Audience

Youth baseball, fastpitch, and soccer families — regional travel teams from
across the Southeast for tournaments, plus Oxford Park Commission league play
locally. Two distinct buys sit on top of that:

- **Local Oxford advertisers** wanting the year-round league families.
- **Tournament-weekend advertisers** — hotels, restaurants, urgent care, tire and
  auto, sporting goods — reaching out-of-town families who are in Oxford for
  three days and deciding where to eat and stay.

The second is the more interesting sell and it's one almost nobody can offer,
because it needs a screen inside the facility those families are standing in.

## Calendar source — read this before you demo

Their site is `mtradepark.com`. Two calendar surfaces are published:

- `mtradepark.com/schedule/list/` — a **The Events Calendar** (WordPress) listing.
  That plugin normally exposes a clean REST endpoint at
  `/wp-json/tribe/events/v1/events`, which is what the feed's Discover targets first.
- `mtradepark.com/events-wYqgm` — a hand-maintained tournaments page.

They are also listed as a venue on Visit Oxford's calendar
(`visitoxfordms.com`), which runs the same plugin. That's a usable fallback
source — set the feed's **venue filter** to `mTrade Park` so it pulls only their
events out of the town-wide calendar.

**Unverified:** the automated pull has not been confirmed against the live site.
Every request from the environment this feed was built in was refused before it
reached them, so `mtradepark.com`, the Visit Oxford calendar, and the endpoints
above are all still untested. Run `scripts/seed_mtrade_feed.py` or hit
**Discover** from the office network and you'll know in one click.

If the site refuses automated requests from there too, it's behind a bot filter,
and the answer is not to fight it — ask them for an `.ics` export or a calendar
share link and use **Import by hand** on the Source tab. That's a reasonable ask
during a conversation where we're offering to run their calendar for free, and a
share link is more durable than scraping their site anyway.

## How to run the pitch

1. Connect the feed (Discover, or an `.ics` they send you).
2. Event Feeds → **Slides** → **Refresh now**.
3. Download the HTML preview, open it on a tablet.
4. Show them the board built from *their* calendar, in our brand, and ask where
   in CageTime it should hang.

Showing it beats describing it. The preview is the demo.

## Open questions for the first meeting

- Who controls CageTime's walls — the Park Commission, or a facility operator
  under contract to them?
- Does the naming-rights sponsor have any signage exclusivity inside the building?
- Power and mounting on the observation deck.
- Is the calendar behind `/schedule/` maintained by the same people who run the
  tournaments page? If not, we may need both sources.

## Sources

- [mTrade Park](https://www.mtradepark.com/) — official site
- [CageTime Batting Cages](https://www.mtradepark.com/cagetimebattingcages)
- [mTrade Park named 2025 USSSA Facility of the Year — The Oxford Eagle](https://oxfordeagle.com/2026/01/22/mtrade-park-named-the-2025-usssa-facility-of-the-year/)
- [mTrade Park — Visit Oxford](https://visitoxfordms.com/directory/mtrade-park/)
- [mTrade Park — Travel Sports](https://travelsports.com/facilities/mtrade-park)
- [Oxford Park Commission](https://www.oxfordms.net/park-commission)
