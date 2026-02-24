# MEMORY.md - Persistent Context for Claude

## The Human

**Creed Cannon** — Owner/Managing Partner of MCTV Elite Advertising. Hands-on builder. Runs the business with his wife Mary Michael Cannon. This is his passion project and he's deeply invested in making it great. He thinks fast, iterates fast, and gets excited about new capabilities.

### Working Style
- Prefers seeing results quickly — generate, check PDF, iterate
- Gives feedback by sharing PDFs and screenshots
- Likes concise explanations, not walls of text
- **Always include URLs/links when asking him to visit a website** (he specifically asked for this)
- Trusts the process — approves plans quickly and lets me run
- Says "back to the proposals" when he wants to refocus after tangents
- When he says a file name (like "MEMORY.md"), he means "update it" or "create it"
- Calls me "pup" when he's in a good mood and wants me to keep going
- "Anytime you can do a step, do it" — handle as much as possible programmatically, don't wait for permission on obvious next steps
- Says "IMPECCABLE.style" when extremely satisfied with results

### Important Corrections (DO NOT GET THESE WRONG)
- **Swayze Hollingsworth is a woman** — use she/her pronouns
- **MCTV does NOT do revenue sharing** with most venue partners — don't suggest or imply it
- **Walk through WordPress like user is 12** — step-by-step, no assumed knowledge

---

## The Project

**MCTV Bot** — A Streamlit web app that generates AI-powered advertising proposals, traction reports, and video ad mockups for MCTV Elite Advertising, North Mississippi's indoor digital billboard network.

- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase REST API (leads/intake) — https://dtapevlfnekzepbtlabj.supabase.co
- **AI:** Anthropic Claude API (claude-sonnet-4-5-20250929 for proposal content)
- **Video:** Creatomate API v1 (https://creatomate.com) — template-based video rendering
- **Auth:** Dual-mode — team password (APP_PASSWORD) for internal tools + Supabase Auth (email/password) for client portal
- **Portal:** Full client lifecycle platform (contracts, invoices, creative requests, reports) — Supabase Auth + RLS

### Key Files
- `services/docx_service.py` — The big one. All Word document formatting, branding, borders, photos.
- `services/creatomate_service.py` — Creatomate video generation API wrapper (stdlib only).
- `generators/elite_advertiser.py` — The flagship proposal. Most heavily optimized. PHOTO_DISTRIBUTION here.
- `generators/base_proposal.py` — Abstract base class all generators inherit from.
- `generators/multi_brand_bundle.py` — Multi-business bundle (Good Earth was built with this).
- `config/prompts.json` — Claude prompt templates per proposal type.
- `config/config.json` — Company info, pricing tiers, team, markets, venues.
- `services/auth.py` — Dual-mode auth: team password (APP_PASSWORD) + Supabase Auth (email/password) for client portal.
- `services/supabase_client.py` — Centralized Supabase client (Auth + Storage + DB REST helpers).
- `services/portal_service.py` — Client portal CRUD (dashboard data, profile updates, lead conversion, portal invites).
- `services/contract_service.py` — Contract lifecycle (create, send, sign, track, activate, cancel).
- `services/invoice_service.py` — Invoice CRUD, AR aging, batch generation, overdue scanning.
- `services/storage_service.py` — Supabase Storage wrapper (upload, signed URLs, delete).
- `services/notification_service.py` — Email notifications for all portal events (accounts, contracts, invoices, creative, reports).
- `generators/contract_generator.py` — Branded contract PDFs using DocxService (advertiser + host clauses).
- `pages/1_Proposals.py` — Main proposal generation page. Handles photo uploads (up to 4 page-2) + default screen photos.
- `pages/2_Reports.py` — Traction report generation + "Share with Client" button for portal.
- `pages/5_Video_Ads.py` — Video ad generator page.
- `pages/4_Leads.py` — Leads dashboard with "Convert to Client" button.
- `pages/8_Clients.py` — Internal client management (create, invite to portal, assign rep, status).
- `pages/9_Contracts.py` — Internal contract management (create, generate PDF, send, track signing).
- `pages/10_Invoices.py` — Internal invoicing (create, send, mark paid, AR aging, batch tools).
- `pages/11_Creative.py` — Internal creative request management (review, assign, status, notes).
- `pages/portal_login.py` — Client portal login (Supabase Auth email/password).
- `pages/portal_dashboard.py` — Client dashboard (role-aware: advertiser vs host).
- `pages/portal_contract.py` — Click-to-sign contract page (typed name + "I Agree" + timestamp).
- `pages/portal_invoices.py` — Client invoice viewer.
- `pages/portal_creative.py` — Client creative requests (submit photos/logos, track status).
- `pages/portal_reports.py` — Client traction report viewer.
- `pages/portal_profile.py` — Client profile editor + password reset.
- `scripts/setup_portal_schema.sql` — Supabase schema (8 tables + RLS + indexes).
- `scripts/integration_test.py` — Full CRUD lifecycle test (28 tests: auth, clients, contracts, invoices, creative, reports, activity, updates, queries, cleanup).
- `scripts/service_test.py` — Service layer test (14 tests: portal_service, contract_service, invoice_service).
- `scripts/setup_portal.py` — One-shot portal setup (prompts for service key, creates users, buckets, saves .env).
- `assets/branding/mctv_logo.png` — Dark MCTV logo (RGB, 1920×1080) — for login page, white backgrounds.
- `assets/branding/mctv_logo_on_navy.png` — White MCTV logo pre-composited on navy (RGB, 934×283) — for cover page.
- `assets/branding/mctv_logo_white.png` — White MCTV logo with transparency (RGBA, 934×283).
- `assets/screens/` — Default community screen photos. Auto-included when no user photos uploaded.
- `pages/6_Samples.py` — Public sample proposals page (no auth, iframe-friendly).
- `pages/7_Research.py` — Prospect Research page (password-protected). Generates competitive intel briefs.
- `scripts/generate_samples.py` — CLI script to batch-generate sample PDFs.
- `assets/samples/` — Pre-generated sample proposal PDFs for website.
- `SOUL.md` — Brand voice and identity guide.
- `HEARTBEAT.md` — Living changelog and project status.
- `CLAUDE.md` — Technical project documentation.

### Brand Identity
- **Colors:** Navy (#1B1F3B), Gold (#C5A55A), Cream (#F0EDE4), Dark Text (#333333)
- **Font:** Calibri throughout
- **Voice:** Professional but warm. Mississippi local. Partnership over salesmanship. Data-driven. Short and scannable.
- **Never:** Generic marketing jargon, markdown in proposals, paragraphs longer than 4 sentences, vague claims
- **NEVER make pricing publicly available.** No pricing tiers, rates, or dollar amounts on any public-facing page (Intake, Samples, website embeds). Pricing is only in password-protected proposals delivered to specific clients.

### Team
- **T. Creed Cannon** — Owner/Managing Partner — (601) 201-8202 — creed@mctvofms.com
- **Mary Michael Cannon** — Owner/Managing Partner — (662) 801-5677 — mmc@mctvofms.com
- **Swayze Hollingsworth** — Director of Sales — (662) 907-0404 — swayze@mctvofms.com

### Pricing Tiers
- 10 Screens: $350/month ($35/screen, 15K plays/mo)
- 20 Screens: $500/month ($25/screen, 30K plays/mo)
- 40 Screens: $800/month ($20/screen, 60K plays/mo)
- 75+ Screens: $1,300/month ($17.33/screen, 120K+ plays/mo)

### Markets
- Oxford (75 screens), Starkville (30), Tupelo (25)
- Expanding: Columbus, West Point

### Environment Variables (Render)
- `ANTHROPIC_API_KEY` — Claude API
- `APP_PASSWORD` — Login gate password (internal tools)
- `CREATOMATE_API_KEY` — Video generation API
- `SUPABASE_URL`, `SUPABASE_KEY` — Lead storage + portal (anon key for client auth)
- `SUPABASE_SERVICE_KEY` — Service role key (bypasses RLS for admin operations)
- `PORTAL_URL` — Portal base URL for email links (e.g., https://mctv-bot.onrender.com)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` — Email notifications

---

## Architecture Patterns

### Generator Pattern
All proposal generators inherit from `BaseProposal`:
1. `get_sections()` — ordered (key, title) tuples
2. `get_prompt_variables()` — template variables from input data
3. `build_section()` — dispatches to per-section builders
4. `generate()` — orchestrates: cover page → Claude prompts → sections → save
5. Sections prefixed with `_` (e.g., `_pricing`, `_team`) skip Claude API calls

### Cover Page Layout (v19+)
Navy (#1B1F3B) background table cell, own section with tight margins (0.8/0.5/1.3/1.3 cm), section break after restores normal margins (1.5/2.0 cm). No footer on cover page.

Content order (vertically centered):
- MCTV logo (mctv_logo_on_navy.png, 3.0 inches) — **must be RGB with navy baked in, NOT transparent**
- "Prepared for" (white italic 11pt)
- CLIENT NAME (white bold 24pt caps)
- Business Name (gold 14pt)
- Client logo (if uploaded, 1.8 inches)
- Gold accent line (─ × 30)
- "ADVERTISING PARTNERSHIP PROPOSAL" (gold bold 28pt)
- Gold accent line
- Date (white 12pt)
- Rep name | MCTV Elite Advertising (gold bold 10pt)
- email | phone (white 9pt)
- www.mctvofms.com (gold 9pt)

Cell height: 14800 twips (~10.3 inches). Vertical centering via `WD_ALIGN_VERTICAL.CENTER`.

### Photo Distribution System
`PHOTO_DISTRIBUTION` class attribute on each generator scatters photos across sections:
```python
PHOTO_DISTRIBUTION = {
    "opportunity_hook": {"source": "extra", "max": 2},                          # page 2: side-by-side
    "market_coverage":  {"source": "extra", "max": 2, "title": "Our Screens in Your Community"},  # page 3
    "getting_started":  {"source": "extra", "max": 1},                          # page 5: inline
}
```

Three photo pools:
- **venue_photo_paths** — uploaded venue/screen photos → after market_coverage with "Our Screens in Action"
- **ad_example_paths** — uploaded ad screenshots → after whats_included with "Ad Creative Examples"
- **extra_photo_paths** — scraped/uploaded/default photos → distributed via PHOTO_DISTRIBUTION

**Photo pool consumption:** `base_proposal.py` builds pools from docx_svc attributes, consumes photos via `del pool[:count]`. Pipeline caps: `[:4]` for page 2 photos.

**Default screen photos:** When no venue or extra photos uploaded, `assets/screens/*.{png,jpg,jpeg,webp}` auto-populate as extra photos. (Implemented in `pages/1_Proposals.py`.)

### Document Formatting (v21 — MUC Standard)
All branding lives in `DocxService`. Key methods and their current settings:
- `add_cover_page()` — full-page navy table, own section, tight margins, no footer
- `add_section_header()` — **full-width navy background bar** with white bold 16pt centered text + gold accent underline bar (matches MUC gold standard)
- `add_sub_header()` — 12pt navy bold with ❚ gold left accent
- `add_callout_box()` — cream background + **gold left border** + thin gray sides, 0.3cm left indent
- `add_accent_card(title, body)` — **NEW** — light bg + thick gold left border (sz=24) + thin gray other borders + bold primary title + body text. Used for What's Included and Why MCTV sections.
- `add_metrics_banner()` — navy background, gold stats (20pt), **gold top border accent**
- `add_bullet_point()` — **gold ● bullet** + hanging indent (0.6cm) + bold navy title + description
- `add_bullet_list()` — parses "- Title: Description" format, calls add_bullet_point
- `add_pricing_table()` — navy header row, alternating gray rows, **thin gray borders**
- `add_contract_terms()` — 6/12 month boxes with **gold left border** + gray sides
- `add_inline_photos()` — responsive 1-4 photo layouts: 1=centered 3.0", 2=side-by-side 2.8", 3=2+1 merged bottom row, 4=2×2 grid
- `add_photos_grid()` — max 2.5in per photo in 2-col grid, **compact spacing (Pt(0))**, keep_with_next on title, **optional `captions` list** (italic gray 8pt under each photo)
- `add_section_divider()` — thin gold horizontal rule (─ × 50, 6pt)
- `add_footer()` — **"MCTV Elite Advertising | Confidential Partnership Proposal | Page X"** center-aligned, 8pt, accent/gray colors. Optional `footer_text` param for reports.
- `add_body_text()` — 10.5pt, auto-detects numbered items for bold navy titles, **pre-splits single-newline numbered items** so all steps get bold formatting
- `add_team_section()` — team cards + **closing statement** (italic accent) + **MCTV logo** (2.0in) + website URL. Team reordered so **preparer (sales rep) appears first**. Optional `closing_text` param. Dark mode uses `mctv_logo_white.png` (white text, transparent bg) instead of `mctv_logo_on_navy.png`.

Border helpers:
- `_set_cell_borders(cell, left_color, left_sz, other_color, other_sz)` — per-cell borders
- `_set_table_borders(table, color, sz)` — uniform borders on all cells
- `_remove_table_borders(table)` — removes all borders (for layout tables)

PDF conversion: LibreOffice headless (Docker) or docx2pdf (Windows)

### Traction Report Pipeline (v4 — Current)
- `services/excel_parser.py` — NTV360 parser with 3 format auto-detection. `parse_per_content_report()` uses **header-name-based column mapping** (not hardcoded indices). Extracts city, playlist, play count, duration, dates. Demo venues auto-excluded.
- `classify_venue(name)` — 10-rule regex classifier (Restaurant, Salon, Medical, Auto, Fitness, Liquor, Education, Professional, Retail, Community). Applied automatically in `build_report_data()`.
- `services/chart_service.py` — 4 matplotlib charts: venue bar chart, category donut, scatter plot, market comparison. All in MCTV brand colors. `generate_all_charts(data, categories)` returns PNG paths.
- `generators/advertiser_report.py` — Full report pipeline: cover page → executive summary + KPIs → venue table (with city, category, bold top 3, totals row) → **page break** → category breakdown → analytics charts (2×2 grid) → AI insights → team section → footer
- `add_data_table()` now accepts `bold_rows=N` (bolds top N data rows) and `totals_row=[...]` (navy-styled summary row)
- `models/report_data.py` — `PlayRecord` has `city` field, `VenueRecord` has `city` + `business_category` + `monthly_traffic` + `dwell_time_minutes` + `monthly_impressions` + `screen_count`. `TractionReportInput` has `monthly_rate` for CPM.
- **Network Dashboard Integration** (V4): `parse_network_dashboard()` reads "All MCTV Hosts" sheet from MCTV Network Dashboard Excel. `enrich_report_with_dashboard()` matches venues by lowercase host_name and populates traffic, dwell time, impressions, screen count.
- **Impression formula**: `Impressions = Traffic × Dwell Time × License Count / 15` (the `/15` is the ad loop rotation — 15 ads, each gets 1/15th)
- **CPM per venue**: Uses proportional allocation: `venue_share = venue.impressions / total_impressions`, `venue_cost = monthly_rate × venue_share`, `CPM = (venue_cost / venue.impressions) × 1000`. Result: uniform CPM across all venues (mathematically correct for flat-rate campaigns).
- **Dynamic venue table columns**: Impressions + CPM columns appear only when dashboard data is loaded
- **KPI grid**: Shows impressions and avg dwell time when dashboard data available, falls back to avg plays and days active

### Prompt Engineering
- Strict word limits per section (150/100/75/80/60 for Elite Advertiser)
- Claude MAY use bullet dashes when prompt asks for them
- No markdown in output — clean plain text only
- Each proposal type has its own prompt keys in prompts.json

### Client Portal Architecture

**Dual-mode Authentication:**
- Internal tools: `APP_PASSWORD` gate (unchanged) — `st.session_state["auth_mode"] = "team"`
- Client portal: Supabase Auth (email/password) — `st.session_state["auth_mode"] = "portal"`
- Parallel paths: portal uses `portal_*` session state keys, zero impact on existing team login
- Portal roles: `advertiser`, `host`, `admin`, `sales_rep` (stored in `profiles` table)

**Supabase Schema (8 tables):**
- `profiles` — links Supabase Auth users to roles
- `clients` — business entities (advertisers + hosts), linked to portal_user_id
- `contracts` — service agreements with click-to-sign fields (signed_by, signed_at, signed_ip, signed_user_agent)
- `invoices` — billing records with auto-numbered IDs (MCTV-YYYYMM-XXXX)
- `creative_requests` — client asset submissions (5 types: new_ad, update_ad, logo_upload, photo_upload, general)
- `creative_files` — files attached to creative requests (stored in Supabase Storage)
- `client_reports` — traction reports shared with clients
- `activity_log` — audit trail with user_id, action, entity, details JSONB

**RLS (Row-Level Security):**
- All client-facing tables have RLS policies: clients only see their own data
- Admin operations use `SUPABASE_SERVICE_KEY` (service role) to bypass RLS
- Portal queries use anon key with authenticated user context

**Storage Buckets:**
- `contracts` — generated contract PDFs
- `reports` — shared traction report files
- `creative-uploads` — client-uploaded photos/logos
- `creative-deliveries` — finished assets delivered to clients

**Contract Signing Flow:**
1. Admin creates contract → `contract_generator.py` produces branded PDF → uploads to Storage
2. Email sent to client with portal link
3. Client views contract → `portal_contract.py` shows details + download
4. Client types full legal name, checks "I Agree", clicks Sign
5. System records: typed name, timestamp, IP address, user agent
6. Status → "signed", notification email to MCTV team

**Invoice Lifecycle:**
- Auto-numbered MCTV-YYYYMM-XXXX format
- Status flow: draft → sent → viewed → paid (or overdue → paid)
- `check_and_mark_overdue()` — batch scan for past-due invoices, sends reminder emails
- `generate_monthly_invoices()` — creates drafts from all active contracts (deduplicates by period)
- AR aging: 5 buckets (current, 1-30, 31-60, 61-90, 90+ days)

---

## The Gold Standard: Good Earth Proposal

The **Good Earth / Oxford Pools** proposal (`MCTV_Good_Earth_Proposal.pdf`) is the reference for what all proposals should feel like. It was a Multi-Brand Bundle, 7 pages:
1. Cover (navy bg, gold title, white client name)
2. The Opportunity (personal hook + stats banner)
3. Your Brands (each brand gets spotlight card with details)
4. The MCTV Network (market breakdown + venue categories + bottom banner)
5. The Partnership Package (clean pricing + what's included bullets + savings callout)
6. Partnership Benefits (bold sub-headers + body text — scannable!)
7. Getting Started (numbered steps + team contact cards)

**Key feel:** Professional, scannable, personal, data-backed. Short paragraphs. Bold section titles. No walls of text.

---

## What's Been Done (as of 2026-02-24)

### Elite Advertiser Proposal — v15 through v20
Massive formatting overhaul across 20+ PDF iterations:

**Layout condensing (v16):**
- Margins tightened: 1.5cm top/bottom, 2.0cm sides
- Font sizes reduced: body 10.5pt, headers 18pt, sub-headers 12pt
- All spacing tightened: sections, body, callouts, banners
- Inline photos capped at 2.0 inches (was 4.0)

**Cover page (v17-v19):**
- Full-page navy background with forced cell height (14800 twips)
- Own section with tight margins (0.8/0.5 cm) + section break after
- MCTV logo: created white version from dark logo, pre-composited on navy (RGB, no transparency) — **transparency doesn't work reliably in LibreOffice PDF conversion**
- No footer on cover page
- Blank page 2 eliminated by removing `doc.add_page_break()` after cover

**Logo saga:**
- `mctv_logo_white.png` was originally Shaw Hardware's logo (wrong file!)
- Created proper MCTV white logo by inverting `mctv_logo.png` pixel-by-pixel
- RGBA transparency not rendered by LibreOffice → use `mctv_logo_on_navy.png` (RGB with navy baked in)

**Visual polish (v20):**
- Gold ● bullet characters with hanging indent on all bullet items
- Callout boxes: gold left border accent + thin gray sides
- Pricing table: thin gray borders
- Contract terms: gold left border + gray sides
- Metrics banner: gold top border accent
- Photo distribution restored with titled sections ("Our Screens in Your Community")

**Default screen photos:**
- `assets/screens/` directory for community screen photos
- Auto-included in every proposal when no user photos uploaded
- User has 5 community screen photos to add (shared in chat, needs to save to assets/screens/)

### V3 Fixes — Proposal Photo Overhaul + Traction Report Polish (`fb4b743`)
- **Proposal photos**: Dedicated page 2 photo uploads (2 max at time), page 4 photos separate. Photo pools properly routed.
- **Cover page photo**: Client logo centered under client name
- **Traction report**: KPI word-boundary truncation (target ~18 chars), auto-scaling font sizes (>15 chars→14pt, >10 chars→16pt)
- **Venue name fix**: "Oxford Park Commissi on" broken mid-word → proper word-boundary truncation
- **Chart sizing**: Expanded 15-20% for better readability

### V4 Fixes — Dashboard Integration + Photo System Phase 1 (`75af231`)
**Traction Report:**
- **Table split fix**: Category/market summary tables were splitting across pages 5-6 with ~70% dead space. Added `doc.add_page_break()` before category table.
- **Team section logo**: Dark mode now uses `mctv_logo_white.png` (white text, transparent bg) instead of `mctv_logo_on_navy.png` (5.7KB, low-res baked navy).
- **Network Dashboard integration**: Upload MCTV Network Dashboard Excel → auto-populates impressions, dwell time, traffic, screen count for all matched venues. Shows match rate metric.
- **CPM by location**: Monthly rate input → calculates CPM per venue using proportional cost allocation.
- **Dynamic columns**: Venue table adds Impressions + CPM columns only when dashboard data loaded.
- **KPI grid enrichment**: Shows total impressions and avg dwell time when dashboard available.
- **AI insights**: Prompt now includes foot traffic, impressions, and CPM data when available.

**Photo System Phase 1:**
- Page 2 max photos increased from 2 → 4
- Responsive layouts: 1=centered 3.0", 2=side-by-side 2.8", 3=2+1 merged bottom row, 4=2×2 grid
- All 6 generators updated: `PHOTO_DISTRIBUTION` max: 2→4
- Pipeline caps updated in `pages/1_Proposals.py`: `[:2]` → `[:4]`
- UI labels updated: "up to 4 hero showcase photos"

### Creatomate Video Integration — Live
- `services/creatomate_service.py` — stdlib-only API wrapper (urllib, no requests)
- `pages/5_Video_Ads.py` — template selector, render form, progress bar, video preview + download
- API is **v1** (not v2 as docs suggest) — tested and confirmed working
- Renders complete in ~6 seconds for demo template
- Paste-key fallback when env var not set
- `CREATOMATE_API_KEY` added to Render env vars

### Working Features
- 6 proposal types + 2 report types
- Video ad generation via Creatomate
- Client intake form (public-facing, saves to Supabase)
- Leads dashboard with "Convert to Client" button
- Website image scraper (stdlib only — urllib)
- Photo uploads (venue screens, ad examples, custom images) — up to 4 page-2 photos with responsive layouts
- Default community screen photos from assets/screens/
- Client logo on cover page (scraped or uploaded)
- PDF conversion (LibreOffice in Docker)
- Cover email generation
- Dual-mode authentication: team password (internal) + Supabase Auth (client portal)
- Sidebar shows Claude API + Video API connection status
- 4 color schemes (Original, Light & Airy, Dark, Peaceful Pastels)
- Public Samples page (no auth) for WordPress iframe embedding
- iframe-friendly Streamlit config (XSRF + CORS disabled for embeds)
- Prospect Research tool (competitive intel briefs for sales calls)
- Website text scraper (scrape_website_text — extracts title, description, headings, phone, email, social links)
- Research → Proposal pipeline ("Use in Proposal" pre-fills proposal form from research data)
- **Network Dashboard integration** — upload MCTV dashboard Excel for impressions, dwell time, CPM enrichment in traction reports
- **Client Portal** — full lifecycle platform for advertisers and venue hosts:
  - Client management (internal): create clients, convert leads, invite to portal, assign reps
  - Contract system: generate branded PDFs, send to client, click-to-sign (typed name + "I Agree" + timestamp/IP)
  - Invoice management: auto-numbered (MCTV-YYYYMM-XXXX), send/track/mark paid, AR aging (5 buckets), batch generation
  - Creative request management: clients submit photos/logos, team reviews/assigns/updates status, file uploads to Supabase Storage
  - Report sharing: "Share with Client" button on traction reports → uploads to Storage + creates portal record
  - Portal pages: dashboard (role-aware), contract signing, invoice viewing, creative submissions, reports, profile editor
  - Supabase Auth with RLS (row-level security) for data isolation — clients only see their own data

### 4 Color Schemes — Live
Added 4 selectable color palettes via horizontal radio on Proposals page:
- **Original Primary** — Navy (#1B1F3B) + Gold (#C5A55A) + Cream (#F0EDE4)
- **Light, Bright & Airy** — Sky Blue (#2E5E86) + Warm Amber (#E89E3C) + Ice Blue (#F0F6FB)
- **Dark & Sophisticated** — Deep Charcoal (#1A1A2E) + Rich Gold (#D4AF37) + Warm Ivory (#F5F0E6)
- **Peaceful Pastels** — Sage Green (#5B7B7A) + Dusty Rose (#C48D78) + Blush (#F3EEED)

Architecture:
- `COLOR_SCHEMES` dict in `docx_service.py` — each scheme has `primary`, `accent`, `white`, `gray`, `text`, `light` (RGBColor) + `bg_hex`, `accent_hex`, `light_hex` (strings) + `cover_logo` (filename)
- `DocxService.__init__` accepts `color_scheme` param → stores as `self.c`
- All 50+ color references replaced from hardcoded constants to `self.c[...]` lookups
- Pre-composited logo variants for each scheme: `mctv_logo_on_navy.png`, `mctv_logo_on_light.png`, `mctv_logo_on_dark.png`, `mctv_logo_on_pastel.png`
- `pages/1_Proposals.py` — horizontal radio selector, passed through all 6 generator calls

### All 6 Generators Now v20
All proposal generators upgraded to v20 formatting pattern:
- ✅ Elite Advertiser (the flagship — done first)
- ✅ Host Media Kit (`d01c6e8`)
- ✅ Multi-Brand Bundle (`d01c6e8`)
- ✅ Venue Partner (`d01c6e8`)
- ✅ Category Exclusivity (`7fbfaa7`)
- ✅ Renewal/Upgrade (`7fbfaa7`)

Each has: `PHOTO_DISTRIBUTION`, paragraph+callout bullet parsing, `add_bullet_list()`, `add_callout_box()`, compact contact cards, page breaks only before pricing sections.

### SEO & Visibility Strategy — In Progress
MCTVofMS.com was **NOT indexed by Google** — `site:mctvofms.com` returned 0 results. Root cause: WordPress "Discourage search engines" was checked + never submitted to Search Console.

**Completed (2026-02-23):**
- ✅ SEO meta tags + OG tags + JSON-LD schema on bot pages (`57ac721`)
- ✅ 9 pages of WordPress content generated (`seo/wordpress_content.md`)
- ✅ Keyword map for 25 pages (`seo/keyword_map.md`)
- ✅ JSON-LD schema templates (`seo/schema_templates.json`)
- ✅ GA4 + Search Console setup guide (`seo/ga4_setup_guide.md`)
- ✅ 5 blog post drafts (`seo/blog_drafts/`)
- ✅ Google Search Console — verified (URL prefix), sitemap submitted, top 7 pages force-indexed
- ✅ WordPress "Discourage search engines" unchecked (Settings → Reading)
- ✅ Google Business Profile — name→"MCTV Elite Advertising", phone→(601)201-8202, category→Advertising Agency, description updated, service areas added (Oxford, Starkville, Tupelo, Columbus, West Point)
- ✅ Review request template drafted for venue partners/advertisers
- ✅ Homepage confirmed live with good title, meta description, and JSON-LD schema

**Pending (Creed does in WordPress/Google):**
- [ ] GBP services list — couldn't find where to edit. Look for Edit Profile → Services tab or "Products & Services" in GBP sidebar
- [x] Paste WordPress content into Divi pages — ALL 9 PAGES DONE (2026-02-23)
- [x] Set RankMath meta tags — done on all 9 pages (2026-02-23)
- [x] Create city landing pages — /oxford-advertising/, /starkville-advertising/, /tupelo-advertising/ CREATED (2026-02-23)
- [x] FAQ page created with 12 Q&As (2026-02-23)
- [x] Intake form iframe embedded on /get-started/ (2026-02-23)
- [x] Team headshots cropped from business cards + team photo added to About Us (2026-02-23)
- [ ] Fix Starkville/Tupelo SEO titles in RankMath (missing "| Indoor Digital Billboards | MCTV Elite Advertising")
- [ ] Add JSON-LD schemas via RankMath
- [ ] Set up GA4
- [ ] Publish 5 blog posts
- [ ] Get Google reviews from venue partners
- [ ] Directory listings (Tupelo Chamber, Yelp, Facebook, BBB)

### SEO Files
- `seo/wordpress_content.md` — 9 pages of paste-ready Divi content (screen-advertising, locations, venue-partner, get-started, about-us, 3 city pages, FAQ)
- `seo/keyword_map.md` — Focus keyword, SEO title, meta description, H1 for 25 pages
- `seo/schema_templates.json` — LocalBusiness, FAQPage, Service, Organization JSON-LD
- `seo/ga4_setup_guide.md` — Search Console + GA4 + GBP setup + 27-item priority checklist
- `seo/blog_drafts/` — 5 articles (800-1000 words each) targeting long-tail keywords

### Google Business Profile (Updated 2026-02-23)
- ✅ Name: "MCTV Elite Advertising" (was "MCTV DIGITAL, INC")
- ✅ Phone: (601) 201-8202 (was 601-405-5054)
- ✅ Category: Advertising Agency
- ✅ Description: Updated with indoor billboard network copy
- ✅ Service areas: Oxford, Starkville, Tupelo, Columbus, West Point
- 🔲 Services list: Still shows wrong services (Auto Repair, Business Cards). Creed couldn't find the Services tab.
- 🔲 Reviews: Zero — review request template was drafted

### Image Scraper Improvements (v21)
- `classify_image(url, alt_text, file_size)` in `web_scraper.py` — heuristic classification into `logo`, `ad_example`, `product`, or `skip`
- `scrape_website_images()` now auto-filters `skip` images (icons, buttons, UI elements, tiny files) and includes `category` key in results
- `1_Proposals.py` scraper UI upgraded: **slot-assignment dropdowns** ("Skip", "Client Logo", "Venue Photo", "Ad Example", "Extra Photo") with auto-suggested slots based on classification
- Routed images stored in session state: `scraped_logo_path`, `scraped_venue_paths`, `scraped_ad_paths`, `scraped_photo_paths`
- All 6 generator forms merge scraped routes with manual uploads

### Known Issues / TODO
- Email notifications (SMTP configured but not verified end-to-end)
- Custom domain not set up (bot.mctvofms.com)
- **Integration test suite**: 42/42 tests passing (28 CRUD lifecycle + 14 service layer) — `scripts/integration_test.py` + `scripts/service_test.py`. Proposal testing still manual (generate PDF, visual check).
- Need custom MCTV-branded Creatomate template (currently using demo "Search Field Simple")
- **User needs to save 5 community screen photos to `assets/screens/`** — they shared images in chat but files need to be placed manually
- Test all 4 color schemes with a real PDF generation
- **WordPress integration tested but NOT live yet** — Intake form iframe works on mctvofms.com (Divi Fullwidth Code module). Creed wants to wait before making pages public. Still need to: add Samples page, add pages to nav menu, set up Calendly booking, generate sample PDFs (no pricing), configure bot.mctvofms.com subdomain
- **Phase 3 Polish (complete):** Scraper preview UI (3A — done in 1B), photo captions (3B), cover logo verified (3C), dynamic presenter verified (3D), venue photo library by market (3E — `assets/screens/{Oxford,Starkville,Tupelo,Columbus,West Point}/` created, auto-include filters by selected markets)
- **Photo Handling Spec Phases 2-3**: Phase 1 done (4-photo layouts). Phase 2 (scraper preview panel polish — counter bar, validation warnings, overflow handling) and Phase 3 (smart classification pipeline) still pending.
- **Render deployment**: Auto-deploy from `main` branch may need verification. After `75af231` push, user reported "Not seeing anything on the render logs." May need manual deploy trigger at https://dashboard.render.com or webhook re-connection.
- **Client Portal — LIVE (2026-02-24):**
  - ✅ SQL schema deployed (8 tables + RLS + indexes verified via REST API)
  - ✅ Render env vars set (SUPABASE_SERVICE_KEY + PORTAL_URL)
  - ✅ 3 admin profiles created + backfilled (Creed, Mary Michael, Swayze)
  - ✅ 4 storage buckets created (contracts, reports, creative-uploads, creative-deliveries)
  - ✅ Portal login confirmed working at mctv-bot.onrender.com/portal_login
  - ✅ Integration tests: 42/42 passing (28 CRUD lifecycle + 14 service layer) — committed `62a9c40`
  - ✅ RLS policies verified (all 8 tables have row-level security enabled)
  - Still need: email notification end-to-end test (requires SMTP credentials configured)

---

## WordPress Integration Plan (mctvofms.com)

**Website:** mctvofms.com (WordPress)
**Goal:** Incorporate all MCTV Bot capabilities into the public-facing website.

### Features to Integrate (all 4 confirmed by Creed)

| Priority | Feature | Effort | Approach |
|----------|---------|--------|----------|
| 1 | **Book a Meeting** | 30 min | Calendly (or similar) embed on a WordPress page |
| 2 | **Sample Proposals** | 1 hour | Pre-generate 3-4 PDFs (restaurant, gym, salon, auto shop), upload to WP gallery page |
| 3 | **Client Intake Form** | 1-2 hrs | iframe embed → `mctvofms.com/get-started` pointing to Render intake page |
| 4 | **Custom Subdomain** | 1 hour | `bot.mctvofms.com` → Render (CNAME DNS + Render custom domain config) |
| 5 | **Self-Serve Proposals** | 2-3 hrs | iframe Streamlit app at `bot.mctvofms.com`, or build public API endpoint |

### Architecture Options
- **iframe embed** (fastest) — WordPress page with iframe to Render app. Works today.
- **Native WP form + API webhook** (cleaner) — WPForms/Gravity Forms → webhook POST to Render → Supabase. Looks fully native.
- **Public API endpoint** — Add `/api/generate` to Render app, returns PDF download link. WordPress form calls API.

### Quick Wins (do first)
1. Calendly embed for meeting booking
2. Generate sample proposal PDFs for 3-4 industries
3. iframe the existing intake form into WordPress

### Custom Subdomain Setup (bot.mctvofms.com)
1. Add CNAME record in WordPress/DNS host: `bot` → `mctv-bot.onrender.com`
2. Add custom domain in Render dashboard: https://dashboard.render.com → Service → Settings → Custom Domains
3. Render auto-provisions SSL certificate
4. Update iframe URLs to use `bot.mctvofms.com`

### WordPress Embed Code Snippets

**Intake Form (iframe embed):**
Add a Custom HTML block in WordPress page editor:
```html
<iframe
  src="https://mctv-bot.onrender.com/Intake"
  width="100%"
  height="900"
  style="border: none; border-radius: 8px;"
  title="MCTV Advertising Intake Form">
</iframe>
```

**Sample Proposals Page (iframe embed):**
```html
<iframe
  src="https://mctv-bot.onrender.com/Samples"
  width="100%"
  height="800"
  style="border: none; border-radius: 8px;"
  title="MCTV Sample Proposals">
</iframe>
```

**Calendly Booking (embed):**
```html
<div class="calendly-inline-widget"
  data-url="https://calendly.com/YOUR_CALENDLY_LINK"
  style="min-width:320px;height:700px;">
</div>
<script src="https://assets.calendly.com/assets/external/widget.js" async></script>
```

**After custom subdomain is set up**, replace `mctv-bot.onrender.com` with `bot.mctvofms.com` in all embed URLs.

### Streamlit iframe Config
- `.streamlit/config.toml` has `enableXsrfProtection = false` and `enableCORS = false` to allow iframe embedding
- Public pages (0_Intake.py, 6_Samples.py) hide sidebar and Streamlit chrome for clean embed appearance

### New Files for WordPress Integration
- `pages/6_Samples.py` — Public sample proposals page (no auth), shows downloadable industry sample PDFs
- `scripts/generate_samples.py` — CLI script to generate sample PDFs using existing generators
- `assets/samples/` — Directory for pre-generated sample PDF files

---

## Lessons Learned

1. **Spacing is everything** in python-docx. Removing one spacer paragraph can save a whole page. Always test with a real PDF.
2. **Claude's output format varies.** Parse line-by-line with fallbacks. The Why MCTV parser was rewritten 3 times.
3. **python-docx has no native page background.** Use a full-width single-cell table with fill color.
4. **Keep dependencies minimal.** Web scraper, Supabase, Creatomate all use stdlib urllib.
5. **The user tests by generating real proposals and checking the PDF.** Visual verification is the workflow.
6. **Creatomate API is v1, not v2.** Despite docs showing v2 in curl examples.
7. **Cloudflare blocks urllib without User-Agent.** Always add `User-Agent: MCTV-Bot/1.0`.
8. **Cover page title/subtitle semantics:** `title` = big center text, `subtitle` = business name, `prepared_for` = contact person.
9. **Page breaks before sections** prevent orphaned headers.
10. **The Good Earth proposal is the gold standard.** Always reference it.
11. **Be critical when reviewing PDFs.** Don't say "looks great" if there are issues. Creed will notice. Check page utilization, photo sizes, whitespace gaps, and logo visibility.
12. **PNG transparency doesn't work in LibreOffice.** Use pre-composited RGB images (bake the background color into the image) for guaranteed rendering.
13. **Section breaks vs page breaks:** `doc.add_page_break()` after a full-page table creates a blank page. Use `doc.add_section()` instead — it changes sections without extra blank space.
14. **Full-bleed in Word is impossible** but you can get close with tight margins (0.5-0.8cm).
15. **Photo distribution needs context.** Orphan photos floating between sections with no title feel disconnected. Always give distributed photos a title or attach them to a section.
16. **Streamlit `st.page_link` CSS is separate from `.stMarkdown`.** Sidebar nav labels use `[data-testid="stPageLink-NavLink"] span` — not covered by `.stMarkdown p/h1/h2/h3` selectors. Need explicit CSS with `!important` to override Streamlit defaults on navy backgrounds.
17. **Single Claude API call beats multiple.** For the Prospect Research tool, one well-structured prompt generates all 7 sections in ~5 seconds vs 7 separate calls at ~35 seconds and 3x token cost.
18. **Proportional CPM is uniform.** When allocating a flat monthly rate across venues by impression share, every venue gets the same CPM. This is mathematically correct — `(rate × share / impressions) × 1000 = rate / total_impressions × 1000` is constant.
19. **python-docx cell merge for layouts.** For 3-photo (2+1) layout, use `bottom_cell.merge(table.rows[1].cells[1])` to create a centered bottom row. Merged cells need explicit paragraph alignment.
20. **Bash quoting on Windows.** Python test scripts with single quotes in string literals (e.g., `"4 Corner's Chevron"`) cause `bad substitution` when passed via `python -c`. Write to a temp `.py` file instead.
21. **Integration tests against live Supabase.** Use service role key to create test data, verify operations, then clean up. All 42 tests create/read/update/delete real rows. Name test data obviously (e.g., `INTEGRATION_TEST_Coffee_Shop`) so orphans are easy to identify.
22. **Unicode in Windows terminal.** `sys.stdout.reconfigure(encoding='utf-8')` is required for emoji/unicode characters on Windows cp1252 terminals. ASCII fallbacks (`[PASS]`/`[FAIL]`) are more reliable than emoji (✅/❌).

---

## Licensing / Franchise Opportunity

Creed is interested in packaging this platform to sell to other NTV franchises. Key points discussed (2026-02-24):
- **Copyright**: Register at copyright.gov (~$65) — covers the source code, documentation, and generated content templates
- **Keep repo private**: GitHub private repo is sufficient IP protection for now
- **Trademark**: Consider trademarking the product name if it's branded separately from MCTV
- **License model**: White-label SaaS — each franchise gets their own instance with their branding, markets, venues
- **Pricing idea**: $500-1,000/month per franchise (they get proposal generator, client portal, video ads, lead management)
- **What makes it licensable**: Everything is data-driven (config.json, prompts.json) — swap out branding, markets, and pricing tiers and it's a new instance
- **Next steps**: Focus on operations first (get portal used by real clients), then productize

---

## MCP Servers (Model Context Protocol)

Configured in `~/.claude/.mcp.json` (user-level, applies to all projects). Set up 2026-02-24.
Reference guide: `C:\Users\msaac\Downloads\MCTV_Claude_Code_MCP_Setup_Guide.docx`
Node.js v24.13.1 installed via winget (required for all MCP servers).

### Active Servers
| Server | Package | Status | What It Does |
|--------|---------|--------|-------------|
| **memory** | `@modelcontextprotocol/server-memory` | ✅ Ready | Persistent knowledge graph — remembers MCTV branding, team, clients across sessions |
| **google-workspace** | `@presto-ai/google-workspace-mcp` | ✅ Ready (needs OAuth on first run) | Gmail, Sheets, Docs, Drive, Calendar — proposal delivery, client data, scheduling |
| **canva-dev** | `@canva/cli@latest mcp` | ✅ Ready | Canva design assistance — billboard content, social media, client mockups |

### Pending Servers
| Server | Package | Blocked By |
|--------|---------|-----------|
| **google-analytics** | `mcp-server-google-analytics` | Needs GCP service account + GA4 property ID |

### Memory Knowledge Graph
Pre-seeded with MCTV core data at `~/.claude/memory/memory.jsonl`:
- Company info (MCTV Elite Advertising — markets, screens, brand colors)
- Team profiles (Creed, Mary Michael, Swayze — contact info, roles, pronouns)
- Pricing tiers (NEVER public)
- Supabase project details
- MCTV Bot architecture
- Good Earth reference standard
- MSAAC cross-business context

### Key Notes
- **Windows requires `cmd /c` wrapper** when calling `npx` in MCP configs
- Google Workspace will prompt browser OAuth on first use — sign in with Creed's Google account
- GA4 MCP requires: Google Cloud project → enable Analytics Data API → create service account → download JSON key → add as Viewer to GA4 property
- Verify servers with `/mcp` command inside Claude Code

---

## Agent Teams

Claude Code's experimental Agent Teams feature is enabled. Config lives in `~/.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```
This allows multiple Claude Code instances to work in parallel on different parts of the project. Useful for upgrading multiple generators simultaneously.

---

## Recent Commits

- `ebd7b04` — Add Creatomate video ad generator + project docs
- `f0714d4` — Allow pasting Creatomate API key in Video Ads page
- `6720f1c` — Fix URL validation for video ad image fields
- `5bdeeb9` — Redesign cover page: navy background with gold/white text
- `943f425` — Add MCTV logo to login page
- `e239ee4` — Fix cover page layout, pricing orphan, and Why MCTV parsing
- `fbcfa87` — Condense proposal layout: full cover page, tighter spacing, smaller photos
- `e727c64` — Fix blank page 2 and white logo rendering
- `915edce` — Fix MCTV logo on cover page — use navy-background RGB version
- `2228095` — Polish: full-bleed cover, eliminate orphan photos, skip cover footer
- `fc014b8` — Add borders, bullet points, and restore photo distribution
- `86a373c` — Auto-include default community screen photos in proposals
- `a4ae795` — Add 4 color schemes: Original, Light & Airy, Dark, Peaceful Pastels
- `ebd42f6` — Add WordPress integration: Samples page, iframe config, no public pricing
- `4eefad6` — Add Prospect Research tool — competitive intel briefs for sales calls
- `665602e` — Fix sidebar nav link text invisible on navy background
- `d01c6e8` — Upgrade 3 generators to v20 formatting (Host Media Kit, Multi-Brand, Venue Partner)
- `7fbfaa7` — Upgrade category_exclusivity + renewal_upgrade to v20 formatting
- `57ac721` — Add SEO infrastructure — meta tags, schema, content strategy, blog drafts (11 files)
- `89bde56` — v21 MUC gold standard upgrade
- `c852480` — Fix duplicate .gitkeep key crash
- `dc0b858` — v2 traction reports (15 items)
- `a6254f9` — Proposal v2 fixes
- `3dadf11` — Traction report v2 fixes (10 items)
- `fb4b743` — V3 fixes: proposal photo system overhaul + traction report polish
- `75af231` — V4: dashboard impressions/CPM, table split fix, photo system upgrade (12 files, 357 insertions)
- `88d01cc` — Client Portal: full lifecycle platform (28 files, 5,822 insertions — auth, contracts, invoices, creative, reports, 7 portal pages, 4 internal pages, 7 services)
- `39ad15d` — Portal documentation updates (HEARTBEAT, MEMORY, CLAUDE)
- `d2dc9e3` — Fix portal login page routing
- `62a9c40` — Add integration tests (42/42 pass) + update portal checklist (integration_test.py, service_test.py, setup_portal.py)
