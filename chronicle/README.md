# The Cannon Chronicle

A daily personal newspaper for Creed, compiled each morning by a Claude Code
Routine and published as a private Claude artifact. This directory holds the
design system the daily job reads — **no edition content ever lives in this
repo** (editions contain personal, financial, and calendar details and are
published only to the private artifact).

- **Live edition (private artifact):** https://claude.ai/code/artifact/e9d119df-6492-4573-982c-61ae8904f563
- **Schedule:** daily at 11:30 UTC (6:30 AM Central during CDT), via a
  Claude Code Remote Routine bound to the standing newsroom session (NOT a
  fresh session — a cold session has no authenticated Gmail/Calendar/M365/
  GitHub connectors and produces an empty paper).
- **First edition:** Vol. I, No. 1 — Tuesday, July 7, 2026. Edition number =
  days since then + 1.

## How an edition is built

Four desks gather in parallel (background subagents), then the editor
compiles one page:

| Desk | Source | Beat |
|---|---|---|
| Gmail | Gmail MCP | Ole Miss, DOOH, Claude/Anthropic, action items, notable personal mail |
| Work | Microsoft 365 + Google Calendar MCP | Client/prospect/team activity, action items, week's calendar (Central), **and Sent Items — outbound proposals, decks, and outreach the publisher already sent** |
| Projects | Local repo + GitHub MCP | Recent commits, open PRs/issues, repo task signals, suggested priorities |
| News | WebSearch | Ole Miss football, DOOH industry, Claude Code/AI, north MS local business, sports business |
| Capital | WebSearch | **Standing beat:** new business credit lines & credit cards suited to a small MS media/advertising LLC — fintech corporate cards (Brex, Ramp, Divvy/BILL, Mercury), 0% intro-APR small-business cards (Amex, Chase Ink, Capital One), and SBA / bank / revenue-based lines of credit (e.g. tied to the ~$9.7k QB MRR). Report new/changed offers, rates, approval odds, and fit. |

## Sections (in order)

1. **Masthead + vitals bar** — folio line, title, tagline, key numbers.
2. **Front page** — one lead story (the most consequential item of the day)
   plus one or two sidebars.
3. **The Docket** — the to-do list, ranked; the numbering *is* the priority.
   HIGH/MED/LOW pills. Unresolved items carry forward day to day.
4. **The Ledger** — standing goals, numbered with roman numerals, updated as
   they move.
5. **The Wire** — three news columns: Ole Miss Football, Out-of-Home,
   Claude Code & AI. Every item links a real source; unconfirmed items are
   labeled.
6. **The Works** — state of the MCTV Bot: shipping narrative, PR/issue
   stats, open checklist.
7. **Prospect Intelligence** — names worth a call, from local and
   sports-business news plus the work inbox. Include a **"Sent This Week"**
   note summarizing the publisher's own outbound outreach (read from Sent
   Items) so active pipeline motion shows up as movement, not silence.
8. **The Homestead** — standing section (added 2026-07-17 at the publisher's
   request): the home renovation and related insurance claim, tracked until
   the work is complete. Read the contractor (Paul Davis) and insurer
   (Liberty Mutual) threads in Gmail — inbox AND Sent — each edition. Report:
   what's settled, what's open, and a **days-since-last-reply counter for
   every unanswered outbound thread** (silence is the story). Names, claim
   numbers, and dollar figures stay in the edition only, never in this repo.
9. **The Almanac** — the week's merged calendar, then "looking ahead."
10. **Colophon** — sourcing note.

## Design tokens

Defined in `template.html`. Newsprint ivory `#F2EDE3` / ink `#1C1A16`,
cardinal accent `#A3122E`, powder-blue secondary `#4E6E8A`; dark theme via
`prefers-color-scheme` plus `:root[data-theme]` overrides. Display face is
a Didot/Bodoni stack, body is Georgia, utility is a condensed sans.
Every edition carries art: a lead editorial cartoon (inline SVG, theme-aware), a spot cartoon above each Wire column, the Newsroom staff strip (grayscale team headshots from assets/team/ as base64 data URIs), and the MCTV logo in the colophon — see the ART comment block in template.html. Favicon is always 🗞️; artifact title format is
`The Cannon Chronicle — <date>`.

## The Radio Edition (standing, added 2026-07-19)

Every edition also ships as audio — a 4–5 minute drive-friendly narration
the publisher can play in the truck. After publishing the artifact:

1. Write a ~750-word radio script from the edition: greeting/dateline →
   front page → the Docket (numbered, punchy) → Homestead counters → Wire
   in sixty seconds → Almanac (today + tomorrow) → sign-off ("Hotty Toddy,
   and drive safe"). Spell out numbers and abbreviations for the ear
   (e.g. "D M V", "ninety seven hundred dollars").
2. Synthesize offline — cloud TTS hosts are blocked by the container proxy;
   SVOX Pico (`pico2wave`, apt `libttspico-utils`) + `lameenc` (pip) is the
   proven pipeline at 1.07x tempo, 64 kbps mono MP3.
3. Deliver via SendUserFile alongside the paper, named
   `CannonChronicleRadio_YYYY-MM-DD.mp3`, captioned with the run time.

The container is ephemeral: reinstall `libttspico-utils` (apt) and
`lameenc` (pip) whenever a fresh container starts.

## Rules for the daily job

- Only report facts actually found; never fabricate stories, emails, or URLs.
- Label single-sourced/unconfirmed items — but don't over-hedge: if a quick
  second search confirms a claim, report it as confirmed with the source.
- Update the existing artifact URL above — never mint a new one.
- Personal/financial/medical details go only in the artifact, never into git.
- This job prints the paper; it does not push code changes.

## Accuracy discipline (this is a newspaper, not a rumor mill)

The publisher's standing instruction: *make this less "fake news."* Every
edition must be verifiable. Specific rules:

- **Verify business state against the systems of record, not email inference.**
  A contract is only "awaiting signature" if the `contracts` table says so
  (status `sent`/`viewed`); a deal's stage comes from `pipeline_opportunities`;
  overdue money comes from `invoices`. Do NOT infer "deal stalled / contract
  pending" from inbox silence — query the Supabase tables (via the Supabase
  MCP or the app's own briefing) and report what they actually hold.
- **Add a fifth gathering signal — the CRM/DB desk.** Before writing The Docket,
  The Works, or Prospect Intelligence, read `tasks`, `pipeline_opportunities`,
  `contracts`, and `invoices`. That is the ground truth for anything about the
  owner's to-dos, clients, deals, contracts, and collections. In particular,
  every `pending` row in `tasks` is a Docket item — fold them in, ranked by
  priority (`high` → HIGH pill) and due date, and check off completed ones.
- **Reconcile the Docket against Sent mail before ranking it.** The `tasks`
  board does NOT auto-close when the publisher emails the deliverable, so a
  finished item can sit `pending` for days. Before writing The Docket, search
  **Sent Items in both mailboxes** (Outlook `CREED@MCTVOFMS.COM` via the M365
  MCP `folderName: "Sent Items"`, and Gmail `in:sent`) for every open
  proposal / deck / renewal / contract task. If it already went out — a
  matching recipient and sent date, with an attachment where a deck is
  expected — mark it done and do NOT headline it as overdue. This exact miss
  produced a wrong edition on 2026-07-16: the Old Dominick (sent Jul 14) and
  Story Financial (sent Jul 13) decks were reported as still owed after they
  had shipped, because the desks read the inbox but never the Sent folder.
- **When a prior edition is proven wrong, print a Corrections & Amplifications
  box.** Don't silently edit history — own it on the page.
- **Cross-check numbers.** Dollar figures, day-counts, screen counts, and
  stats must trace to a source (an email, a table row, a linked article). If
  it can't be traced, cut it or label it clearly.

## Do NOT report (known non-facts / demo data)

These are seed/demo artifacts, not real business. Never surface them as news,
tasks, or alerts:

- **Oxford Coffee Co.** — a fictional company. Confirmed by the publisher and
  purged from the database on 2026-07-10 (3 demo contracts + 3 `MCTV-TEST`
  invoices). If it ever reappears in a briefing, it's stale cache — ignore it.
- **Any invoice numbered `MCTV-TEST-*`** — test data; not real overdue money.
- **A demo "MS Asthma & Allergy Clinic, Starkville" host-advertising contract**
  was also demo data and was purged. (The clinic is a real place in the
  publisher's life, but that *contract* was fake.)
- **Stouts Carpet & Flooring is REAL** — a current host and paying advertiser.
  Report it normally.

## Active projects the desks can't natively see

The four inbox/repo/web desks cannot see work done in other Claude sessions or
on the publisher's PC. Read these from the CRM instead so they're reported as
the live projects they are, not cold prospects:

- **Mississippi Live Weather / Matt Laubhan partnership** — a cross-network
  distribution deal (his storm-season audience ⇄ MCTV's 125+ screens). Logged
  in `pipeline_opportunities` at stage `negotiation`. Pitch deck and materials
  are in active production. Report deal state from the pipeline row; never
  frame it as "go open the thread."
