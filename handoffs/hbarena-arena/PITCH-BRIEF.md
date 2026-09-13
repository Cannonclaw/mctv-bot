# Huntington Bank Arena — pitch brief

**Internal only.** The page at `/hbarena-mockup` is safe to forward. This is not.

## Who

**Alli** — `alli@hbarena.com`. Marketing contact at Huntington Bank Arena,
375 East Main Street, Tupelo. No surname on file; the mailbox stores only the
bare address and she has never sent us anything. **Swayze has met her and was
Cc'd on the August email — ask him for her surname, title and direct line.**

Arena main line: 662.841.6528. General inbox: `info@hbarena.com`.

## Where this stands

- **Thu 13 Aug 2026** — Creed and Swayze toured the facility with her in Tupelo.
- **Fri 21 Aug 2026** — Creed emailed asking for a Tuesday or Thursday to come
  back and present a proposal, *"which will clearly illustrate the many ways in
  which this partnership would benefit the arena at no cost."* Swayze Cc'd.
- **No reply, and no call has ever connected** — that same email says
  "I have tried calling a few times but can't get through to your extension."
- The follow-up draft in Creed's Outlook replies on that thread. It is not sent.

Worth knowing: the same building was pitched in **June 2025**, as Cadence Bank
Arena, to **Shelby Ray** (`shelby@cb-arena.com`) — tour, proposal promised,
silence. This is attempt two on the same room. If it goes quiet again, the ask
probably needs to get smaller, not louder.

## What is agreed

Nothing is signed. What she was *promised* is a **no-cost partnership** — MCTV
screens hosted at the arena. Anything paid is a separate, optional conversation.

## What to say

- The arena announces constantly and none of it reaches a screen. Ten sends in
  eight weeks: Blackberry Smoke (Oct 23, with Michael Farris Smith & The
  Smokes), Disney On Ice (Nov 5-8), Anthony Hamilton (Nov 13, with Leela
  James), two Labor Day sales on back-to-back days.
- We run **25 screens in Tupelo**; Oxford (75) and Starkville (30) are there for
  shows worth a drive.
- The asks are small and cost her nothing: add us to the announcement list,
  forward the promoter's art, give us twenty minutes.

## What NOT to say

- **Never quote a discount or code for the Blackberry Smoke Labor Day sale.**
  Its terms live inside images in that email and we have never read them. The
  Disney one is safe and exact: *"up to 25% off the face value"*, code `LDTUP`,
  through Sept 13 — "up to" is load-bearing, her fine print says savings vary by
  performance and seat.
- **Never say the standing slide updates itself from her calendar.** It does
  not. `venue_events` is hand-entered and the mockup is static markup. We update
  it from her announcements, by hand, and that is still a good offer.
- **Never print hbarena.com as a ticketing URL.** It appears in her emails only
  as an address to write to; every buy link resolves to Ticketmaster, and the
  one web URL in the footer is still on the old `cb-arena.com` domain. Ask her
  what the real one is.
- **Do not claim none of her shows run anywhere.** We know what is on *our*
  screens, not what she buys on social or radio. "I haven't seen one on an
  indoor screen in Tupelo" is the defensible version.
- Anthony Hamilton's date came from Ticketmaster listings, not from anything the
  arena wrote in prose. Confirm it with her before it goes on a live screen.

## The page

`static/hbarena_mockup.html`, served at `GET /hbarena-mockup`. Facts on it come
from her own emails; the accuracy pass is recorded in PR #48.

- It is `noindex` and served `no-cache` — it carries her promo code and our
  rate card.
- It is **not live until PR #48 merges to `main` and Render redeploys.** Until
  then that path falls through to Streamlit and answers with the MCTV team login
  screen, which is a worse first impression than a 404. Check with a GET, not a
  HEAD, before sending the link.
- Footer carries a "Prepared Sept 3, 2026" stamp because the Labor Day slide
  expires. After mid-September that slide should be swapped rather than shown.
- The slides carry gradients where the tour art belongs. Drop real art into
  `art/` and run `python scripts/embed_hbarena_art.py` — the script's docstring
  says where to get it.
