# MCTV Elite Advertising Bot

## Purpose
Streamlit web app that powers MCTV Elite Advertising's entire sales and client operations. Generates proposals, contracts, traction reports, invoices, video ads, and SMS campaigns. Includes a client-facing portal for hosts and advertisers. 125+ indoor digital billboard screens across Oxford, Starkville, Tupelo, Columbus, and West Point, Mississippi.

## Deployment
- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot (private)
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase (PostgreSQL + RLS + Storage + Realtime)
- **Auth:** Three-tier login — team password, host magic link, advertiser magic link

## How to Run Locally
```
cd MCTV-Bot
streamlit run app.py --server.port 8501
```
Or use the launcher: `~/.claude/start-mctv-bot.cmd`

## Project Structure
```
app.py                          # Entry point — three-tier login, nav, branding CSS

pages/                          # 13 internal + 8 portal pages
  0_Intake.py                   # Public lead intake form (no auth)
  1_Proposals.py                # Proposal generation UI (6 types)
  2_Reports.py                  # Traction report generation (advertiser + venue)
  3_Settings.py                 # Config viewer, action items checklist
  4_Leads.py                    # Lead management (scoring, bulk actions, follow-ups)
  5_Video_Ads.py                # Video ad generator via Creatomate
  6_Samples.py                  # Sample proposal/report gallery
  7_Research.py                 # Web research and scraping tool
  8_Clients.py                  # Client management dashboard
  9_Contracts.py                # Contract creation (5 types), lifecycle management
  10_Invoices.py                # Invoice generation and payment tracking
  11_Creative.py                # Creative request management
  12_Messaging.py               # SMS messaging (compose, templates, opt-in, history)
  14_Pipeline.py                # Sales pipeline (stages, deals, enrichment, nurture,
                                #   forecast, follow-up SLA, rep scoreboard)
  15_Prospector.py              # Outbound prospector (AI prospect lists, batch add)
  20_HostPipeline.py            # Host venue pipeline (deal_type='host', own stages)
  21_RepDashboard.py            # Per-rep MRR, commission accrual, payout ledger
  24_Loop_Inventory.py          # Screen inventory (what plays where) + loop length
                                #   per screen, reconciliation, dark content
  portal_login.py               # Client/host portal login
  portal_dashboard.py           # Portal dashboard (venue-specific or advertiser)
  portal_profile.py             # Profile management
  portal_reports.py             # Traction reports viewer
  portal_invoices.py            # Invoice history and payments
  portal_contract.py            # Contract viewer + click-to-sign
  portal_creative.py            # Creative request submission
  portal_terms.py               # Terms of service

generators/                     # Document generators
  base_proposal.py              # Abstract base class (all 6 proposals inherit this)
  elite_advertiser.py           # Flagship 5-6 page scannable proposal
  host_media_kit.py             # Free screen hosting pitch
  multi_brand_bundle.py         # Multi-business owner bundle (Buy 2 Get 1 Free)
  venue_partner.py              # Revenue-share venue partnership
  category_exclusivity.py       # Industry lockout proposal
  renewal_upgrade.py            # Existing client renewal/upgrade
  advertiser_report.py          # Advertiser traction report (NTV360 data)
  venue_report.py               # Venue partner report
  contract_generator.py         # Contract document generator (5 types)

services/                       # Business logic and integrations
  auth.py                       # Password + magic link auth, email allowlist
  claude_service.py             # Anthropic Claude API wrapper
  config_service.py             # Config/pricing/team/CPM lookups
  docx_service.py               # Word document builder (1600+ lines, all branding)
  excel_parser.py               # NTV360 Excel report parser
  chart_service.py              # Matplotlib chart generation for reports
  web_scraper.py                # Website scraper: images + text + multi-page
                                #   business info (contact, hours, socials; stdlib only)
  enrichment_service.py         # Website → prospect auto-fill (scraper + Claude
                                #   structured extraction); merge_enrichment() diffing
  pipeline_service.py           # Sales pipeline CRUD, stages, FOLLOW_UP_SLA,
                                #   analytics, rep scoreboard (Supabase + local fallback)
  nurture_service.py            # Automated email/SMS drip sequences for pipeline deals
  leads_service.py              # Lead CRUD + scoring (intake form submissions)
  loop_inventory_service.py     # Reads the n-compass whitelist sweep (screen_loops,
                                #   dark_content) — measured loop length per screen
  venue_events_service.py       # Venue schedules (venue_events) + the payload the
                                #   lobby feed board polls; masks private bookings
  screen_inventory_service.py   # Manual book of record: what creative plays where
                                #   (loop_items + per-screen overrides), plus the two
                                #   reconciliations (vs sweep, vs Encompass export)
  creatomate_service.py         # Creatomate video generation API
  supabase_client.py            # Supabase REST client (query, insert, update, delete)
  portal_service.py             # Portal business logic (clients, activity log)
  portal_ui.py                  # Portal UI components (shared sidebar, cards)
  contract_service.py           # Contract lifecycle (draft→sent→viewed→signed→active)
  invoice_service.py            # Invoice CRUD and payment tracking
  notification_service.py       # Email notifications (Microsoft 365 SMTP, shared mailbox)
  sms_service.py                # Twilio SMS integration
  storage_service.py            # Supabase Storage file uploads
  dashboard_service.py          # Dashboard data aggregation
  quickbooks_service.py         # QuickBooks API integration
  pdf_service.py                # PDF conversion utilities

models/
  proposal_data.py              # Dataclasses: ProposalInput, ProposalOutput
  report_data.py                # Dataclasses: TractionReportInput, VenueRecord

config/
  config.json                   # Company info, pricing tiers, team, markets, venues,
                                #   industry benchmarks, social proof, contract terms
  prompts.json                  # Claude prompt templates (system + per-section)

assets/
  branding/                     # 6 logo variants (original, white, navy, light, dark, pastel)
  team/                         # 3 headshots + 6 team cards (2 per person)
  screens/                      # Community screen photos by city (Oxford, Starkville, etc.)

static/                         # Public pages served outside Streamlit
  rates.html                    # Self-serve rate calculator (GET /rates)
  board.html                    # Venue lobby feed board (GET /board)
  mdot.html                     # MDOT traffic sponsorship mockup (GET /mdot)
  mslive.html                   # Mississippi LIVE Weather partnership one-pager (GET /mslive)
  mslive-looks.html             # Five alternate looks for the weather board (GET /mslive/looks)

handoffs/                       # Pitch packages and design handoffs (internal briefs
                                #   sit next to the public page they support)
  mdot-traffic-partnership/     # PITCH-BRIEF.md for the /mdot mockup
  mslive-weather-partnership/   # PITCH-BRIEF.md for the /mslive one-pager
  rafters-oxford/               # Photo packet handoff for design

scripts/
  setup_portal_schema.sql       # Supabase schema (8 tables + RLS + indexes)
  fix_rls_policies.sql          # RLS policy audit/fix
  apply_updates.sql             # Schema migration script
  seed_venue_events.py          # Sample Conference Center schedule for local dev
  contract_flow_test.py         # Contract lifecycle test
  integration_test.py           # Full integration test

output/                         # Generated files (gitignored)
  proposals/  reports/  contracts/  emails/  videos/  research/
```

## Architecture

### Generator Pattern (Proposals)
All 6 proposal generators inherit from `BaseProposal` (ABC):
1. `get_sections()` — returns ordered `(section_key, title)` tuples
2. `get_prompt_variables()` — extracts template variables from input data
3. `build_section()` — dispatches to per-section builder methods
4. `generate()` — orchestrates: cover page → Claude prompts → section building → save

Sections prefixed with `_` (e.g., `_pricing`, `_competitive`, `_social_proof`, `_team`) skip Claude API calls and render directly from config data.

Every generator includes these standard sections:
- **Metrics banner** — navy background, gold stats numbers
- **Competitive comparison table** — MCTV vs 6 other media channels (Radio, Cable TV, Outdoor, Print, Digital, Social)
- **ROI projection** — daily cost, CPM, impressions per dollar
- **Social proof section** — network stats + trust points
- **Team section** — headshot cards with contact info

### Sales Pipeline System
The team's most-used tool (`pages/14_Pipeline.py` + `services/pipeline_service.py`).
Data lives in Supabase `pipeline_opportunities` + `pipeline_activity` with a local
JSON fallback (`data/pipeline/`) when Supabase is unreachable.

- **Stages** (with win probabilities): prospect 10% → outreach 15% → engaged 30% →
  discovery 45% → proposal_sent 60% → negotiation 75% → contract_sent 90% → won/lost.
  The host pipeline shares the table (`deal_type='host'`) but uses different stage
  names — always filter by `deal_type`.
- **Follow-up SLA** (`FOLLOW_UP_SLA` in pipeline_service): every stage entry
  auto-schedules the next action (e.g. proposal_sent → follow up in 2 days).
  `get_deals_needing_action()` flags overdue, unscheduled, and SLA-stale deals.
- **Rep attribution**: shared team login means no per-user auth — the "Working as"
  selector on the Pipeline page stamps `performed_by` on all activity, feeding
  `get_rep_scoreboard()` (touches, $/touch, MRR won, overdue counts per rep).
- **Website enrichment** (`services/enrichment_service.py`): Add Deal and Edit Deal
  can scan a prospect's website — multi-page stdlib scrape
  (`web_scraper.scrape_business_info`) + Claude structured extraction (Haiku,
  `ENRICHMENT_MODEL` env override) → contact info, hours, address, socials, images.
  Existing-deal merges fill blanks automatically; conflicts require per-field opt-in.
  Enrichment columns (migration 023): `website`, `address`, `business_hours`,
  `social_links`, `website_images`, `enrichment`.
- **Hand-offs**: "Draft Proposal →" sets `st.session_state["prefill_proposal"]`
  (same convention as Research page) and switches to the Proposals page.
- **Perf rule**: the Pipeline page fetches `get_all_opportunities()` once per rerun
  and passes the list into every tab and analytics helper (`opps=` params) — don't
  add per-tab fetches.

### Screen Inventory & Loop Tracking
`pages/24_Loop_Inventory.py` covers two halves of the same question, in four tabs:
**Screens**, **Inventory**, **Reconcile**, **Dark content**.

- **Measured side** (`loop_inventory_service` → `screen_loops`, `dark_content`):
  loaded by the n-compass per-screen whitelist sweep. Key model fact: playlist
  content is license-whitelisted, so a screen's real loop is the sum of the
  playlist items whitelisted to its license — NOT the playlist's row-sum. This
  side knows *how long* each screen's loop runs, not *what's in it*.
- **Book of record** (`screen_inventory_service` → `loop_items`,
  `loop_item_screens`, migration 024): entered by hand. One row per creative per
  market. Items are **run-of-network** by default — every screen in the market —
  and only exceptions get typed in via `loop_item_screens`
  (`mode='exclude'` pulls a spot off one venue, e.g. category exclusivity;
  `mode='include'` puts a non-ROn spot on specific screens, e.g. a host promo).
  `license_id NULL` on an override applies it to every screen at the venue;
  a license-specific row beats the venue-wide one. This mirrors n-compass
  (one playlist per market + per-license whitelist) and keeps entry to dozens of
  rows instead of thousands.
- **Expected loop** for a screen = active ROn items not excluded from it, plus
  items explicitly included on it. `expected_by_screen()` computes it;
  `inventory_summary()["base_loop_seconds"]` is the ROn total, which is what a
  screen with no exceptions should run.
- **Reconcile vs sweep** (`reconcile_sweep()`): expected item count / loop seconds
  vs what the sweep measured, per screen, with a tolerance slider. A negative
  `count_delta` means the screen runs more than the books know about.
- **Reconcile vs Encompass** (`reconcile_plays()`): upload the NTV360 **content
  report** (the format with a row per creative per host — `parse_excel` handles
  it) and join on `(venue_name, file_name)`. Surfaces booked-but-not-airing,
  airing-but-not-tracked, and tracked-but-playing-nowhere. `seed_from_plays()`
  bootstraps the inventory from an export so nobody starts at a blank page.
- **Name matching**: `normalize()` lowercases, strips punctuation and video file
  extensions, and collapses whitespace — the three systems spell venues and files
  differently. Venues missing from an export entirely are deliberately excluded
  from the findings (that's a screen-health question, see `18_ScreenHealth.py`).
- Sweep rows prefixed `CROSS-MARKET:` / `ORPHAN:` / `NOTE:` are sweep annotations,
  not real screens — `is_diagnostic()` filters them out of expected loop math.
- **Perf rule**: the page fetches items, overrides, and screens once per rerun and
  passes them into every tab (`items=` / `overrides=` / `screens=` params) — same
  convention as the Pipeline page.

### Venue Feed Board
The lobby schedule board for host venues that run programming — the Oxford
Conference Center is the first. An airport-style board on the MCTV screen in
the lobby: what is happening now, what is next, which room.

- **Public routes** (`server_routes.py`, installed from `run_server.py` before
  Streamlit boots — same Tornado/ASGI double patch as `/rates`):
  - `GET /board?venue=<slug>` — the board (`static/board.html`), default venue
    `oxford-conference-center`
  - `GET /board/events.json?venue=<slug>` — the schedule it polls, cached 30s
    per venue so a venue's screens share one Supabase read
- **Data** (`venue_events_service` → `venue_events`, migration 025): one row per
  event per venue, entered by hand. Supabase REST with a local JSON fallback
  (`data/venue_events/`, gitignored) so the board still renders offline.
- **Privacy rule**: `is_private` rows keep their room but render as
  "Private Event" — masking happens in `mask()` on the way out, never in the
  table, and the entered title is discarded rather than trusted. `venue_events`
  has no anon RLS policy for the same reason: the board reads through our route
  with the service key, so the raw schedule never leaves the server.
- **Timezone**: every label is formatted server-side in the venue's timezone
  (`America/Chicago`), and the board's clock uses `Intl` with that zone — a
  media player sitting on UTC must not move the 5:30 reception to 10:30.
- **Board behaviour**: polls every 60s, re-derives now/next locally every 10s
  (so the highlight moves on time), rotates pages every 14s when the day runs
  longer than 6 rows, reloads the page hourly. A failed fetch keeps the last
  good schedule on screen and raises the stale marker rather than going blank.
- **Adding a venue**: a `BOARD_VENUES` entry plus rows in `venue_events`. An
  unknown slug still renders, titled off the slug.
- `python scripts/seed_venue_events.py` fills the local file with a sample day;
  migration 025 seeds the same thing server-side (`created_by = 'sample'`).

### Pitch Pages (public, texted as links)
Concept pages for a specific prospect live in `static/` and are served by
`server_routes.py` alongside `/rates` and `/board`, so a rep can text a link
instead of an HTML attachment. Each one has an internal-only
`handoffs/<slug>/PITCH-BRIEF.md` next to it (contact, what is agreed, what to
say, what not to say). The page is safe to forward; the brief is not.

- `GET /mdot` — MDOT road-conditions sponsorship mockup (`static/mdot.html`).
- `GET /mslive` — Mississippi LIVE Weather (Matt Laubhan) partnership
  one-pager (`static/mslive.html`): the plain-English version of the two-page
  50/50 agreement — what each side gets, what a sponsor buys, how it goes live.
  Facts on it must match the agreement; the brief carries the guardrails
  (never "on the network" until Matt approves the board, never a Baron price,
  reach is modeled and shown as ranges).
- `GET /mslive/looks` — five looks for the same board (broadcast, tower cam,
  radar, clean, gameday) in one 16:9 frame with a look picker
  (`static/mslive-looks.html`). Sample readings; the tower-cam frame is drawn,
  not airport footage.
- Adding one: drop the HTML in `static/`, add a `<NAME>_PATH`/`_FILE` pair and
  an `HTML_PAGES` entry plus a Tornado rule in `server_routes.py`, extend
  `scripts/route_check.py`, and run it (`python scripts/route_check.py`).

### Contract System
5 contract types, each with dedicated clause sets:
- **Advertiser** (8 clauses) — standard advertising partnership
- **Host** (7 clauses) — venue hosting agreement ($0 cost)
- **Host Advertising** (9 clauses) — hosts buying extra paid screens
- **Category Exclusivity** (11 clauses) — exclusive category rights, breach remedy
- **Bundle** (10 clauses) — multi-brand under one contract

Contract document structure: Cover Page → Partnership Details → Value Recap (metrics banner + prepay callout) → Terms & Conditions (accent cards) → Signature (two-column layout) → Footer.

Lifecycle: `draft → sent → viewed → signed → active` (or `cancelled`). Click-to-sign via portal with e-signature notice (Mississippi Uniform Electronic Transactions Act).

### Photo Placement System
`PHOTO_DISTRIBUTION` class attribute controls intentional photo placement:
- **page2** = The Opportunity (max 4 hero photos, responsive grid)
- **page4** = Market Coverage (max 6 in a 2x3 grid with captions)

Scraped photos default to UNSELECTED (opt-in). Users assign each photo to a page via dropdown.

### Document Formatting (docx_service.py)
All MCTV branding lives in `DocxService` (1600+ lines). 4 color schemes:
- **Original** — Navy (#1B1F3B) + Gold (#C5A55A)
- **Light & Airy** — Sky blue (#2E5E86) + Warm amber (#E89E3C)
- **Dark & Sophisticated** — Deep charcoal (#1A1A2E) + Rich gold (#D4AF37)
- **Peaceful Pastels** — Sage green (#5B7B7A) + Dusty rose (#C48D78)

Key formatting methods:
- `add_cover_page()` — full-page navy background with logo, titles, rep info
- `add_section_header()` — 20pt bold + gold accent bar
- `add_metrics_banner()` — navy row with gold stat numbers
- `add_accent_card()` — thick accent left border, light background
- `add_selling_point()` — colored square bullet + bold title + body
- `add_callout_box()` — colored background with accent left border
- `add_competitive_comparison()` — 7-row media comparison table, MCTV row highlighted
- `add_roi_projection()` — investment breakdown callout
- `add_social_proof_section()` — stats banner + trust points
- `add_pricing_table()` — tier comparison with recommended highlight
- `add_data_table()` — general-purpose styled table
- `add_team_section()` — headshot cards with contact info
- `add_footer()` — branded footer with page numbers

Font: **Arial** everywhere. PDF conversion: LibreOffice headless (Docker) or local fallback.

### Prompt Engineering (prompts.json)
System prompt enforces:
- Forbidden words list (e.g., "leverage", "utilize", "cutting-edge")
- "Write like a fellow business owner at a diner" voice anchor
- "Every sentence must earn its place" rule
- No markdown formatting in output
- Short paragraphs (2-4 sentences max)

Per-section prompts use `{variable}` placeholders filled by `get_prompt_variables()`. Word limits reduced ~20% from initial versions for tighter copy.

### Database (Supabase)
Core tables (all RLS-enabled; migrations live in `scripts/0NN_*.sql` and are
applied by hand in the Supabase SQL editor):
- `clients` — business info, contact details, portal credentials
- `contracts` — contract records with lifecycle status
- `invoices` — billing and payment tracking
- `creative_requests` — creative request submissions
- `activity_log` — audit trail
- `leads` — intake form submissions
- `sms_messages` — SMS history
- `sms_opt_ins` — SMS consent tracking
- `pipeline_opportunities` — sales + host pipeline deals (stages, monthly_value,
  follow-up dates, enrichment columns; see migration 008 + 013 + 023)
- `pipeline_activity` — per-deal activity log (stage moves, calls, notes,
  `performed_by` rep attribution)
- `screen_loops` — per-license measured loop length + item count, one row per
  screen per sweep date (loaded by the n-compass whitelist sweep)
- `dark_content` — playlist items whitelisted to zero licenses, with revenue context
- `loop_items` — the manual inventory: one creative per market (migration 024).
  `(market, lower(file_name))` is unique, so the same file can live in two markets
  but not twice in one
- `loop_item_screens` — per-screen include/exclude overrides on `loop_items`
  (migration 024); cascades on item delete
- `venue_events` — venue schedules behind the lobby feed board (migration 025).
  `(venue_slug, starts_at, lower(title))` is unique to catch double entry;
  service_role + authenticated only, no anon policy (see Venue Feed Board)

Storage buckets: `contracts`, `invoices`, `creative-assets`

### Auth System
Three login paths in `app.py`:
1. **Team Member** — shared password (`APP_PASSWORD` env var), email allowlist
2. **Host Venue** — Supabase magic link (email OTP)
3. **Advertiser** — Supabase magic link (email OTP)

Portal access restricted to team emails only (configurable allowlist in `auth.py`).

## Configuration
- `config/config.json` — Company info, 4 pricing tiers (10/20/40/75+ screens), team members, 5 markets, venue categories, industry benchmarks (7 media channels), social proof, contract terms
- `config/prompts.json` — Claude API prompt templates (system + per-section per-type)
- Environment variables:
  - `ANTHROPIC_API_KEY` — Claude API
  - `APP_PASSWORD` — Team login password
  - `SUPABASE_URL`, `SUPABASE_KEY` — Database
  - `CREATOMATE_API_KEY` — Video generation
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` — SMS
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` — Email notifications (Microsoft 365, shared mailbox)
  - `NOTIFY_EMAILS` — Comma-separated team notification recipients

## Key Dependencies
```
streamlit>=1.40.0    anthropic>=0.79.0    python-docx>=1.2.0
openpyxl>=3.1.5      pandas>=2.2.0        python-dotenv>=1.0.0
Pillow>=10.0.0       matplotlib>=3.8.0    supabase>=2.5.0
twilio>=9.0.0
```

## Important Notes
- All proposal generators share the same premium formatting pattern: metrics banners, accent cards, competitive comparison, ROI projection, social proof, team section
- Contract T&C sections render as accent cards, not plain text — changing `add_accent_card()` affects both proposals and contracts
- Removing spacer paragraphs or changing margins affects page count significantly — test with a real generation after formatting changes
- The web scraper uses only stdlib (`urllib`, no requests/beautifulsoup) to keep dependencies minimal
- Supabase client uses raw REST API (`urllib`) rather than the supabase-py SDK for queries
- Copyright headers on all source files — `MCTV Digital, Inc.` proprietary notice
- `output/` directory is gitignored — all generated documents are ephemeral
- Pricing tiers: $350/mo (10 screens), $500/mo (20), $800/mo (40), $1,300/mo (75+)
- CPM calculations use `get_tier_impressions()` which pro-rates from 1.9M monthly network impressions
- Email sends from `portal@mctvofms.com` (shared mailbox) but authenticates as `creed@mctvofms.com` via Microsoft 365 SMTP. Three files have SMTP code: `notification_service.py`, `leads_service.py`, `briefing_service.py` — all use `SMTP_FROM` for the sender address
