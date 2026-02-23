# HEARTBEAT.md - Project Status & Changelog

## Current Status: Live on Render

**Last deploy:** 2026-02-22
**URL:** https://mctv-bot.onrender.com
**Branch:** main (auto-deploys on push)

---

## What's Working

- [x] Elite Advertiser proposal (5 pages, scannable, photos scattered inline)
- [x] Host Media Kit proposal
- [x] Multi-Brand Bundle proposal
- [x] Venue Partner proposal
- [x] Category Exclusivity proposal
- [x] Renewal/Upgrade proposal
- [x] Advertiser Traction Reports (from NTV360 Excel uploads)
- [x] Venue Partner Reports
- [x] Client intake form (public-facing, saves to Supabase)
- [x] Leads dashboard (view/manage submissions)
- [x] Website image scraper (pulls client photos for proposals)
- [x] Photo uploads (venue screens, ad examples, custom images)
- [x] Default community screen photos (auto-included from assets/screens/)
- [x] Client logo on cover page (scraped or uploaded)
- [x] PDF conversion (LibreOffice headless in Docker)
- [x] Cover email generation
- [x] Password authentication gate
- [x] Supabase lead storage (REST API)
- [x] Video ad generation (Creatomate API — renders from templates)
- [x] 4 color schemes (Original, Light & Airy, Dark & Sophisticated, Peaceful Pastels)
- [x] Gold bullet points, callout box borders, pricing table borders
- [x] Full-bleed cover page (own section, tight margins, pre-composited logo)
- [x] Public Samples page (no auth, iframe-friendly)
- [x] iframe embedding enabled (XSRF/CORS disabled in Streamlit config)
- [x] Sample PDF generator script (excludes pricing for public use)
- [x] WordPress iframe integration tested (Divi Fullwidth Code module)
- [x] Prospect Research tool (competitive intel briefs for sales calls)
- [x] Website text scraper (title, description, headings, phone, email, social links)
- [x] Research → Proposal pipeline ("Use in Proposal" pre-fills form from research)

## What Needs Attention

- [ ] **WordPress integration NOT live yet** — iframe tested, Creed holding off on publishing pages. Need to: add Samples page, nav menu links, Calendly booking, generate sample PDFs, configure subdomain
- [ ] Email notifications (SMTP configured but not confirmed working end-to-end)
- [ ] Custom domain (bot.mctvofms.com CNAME to Render — not yet set up)
- [ ] Other generators (Host Media Kit, Multi-Brand, etc.) still use old formatting — need v20 treatment
- [ ] Photo distribution only implemented for Elite Advertiser
- [ ] No test suite — all testing is manual (generate proposal, check PDF)
- [ ] Custom Creatomate template (currently using demo "Search Field Simple")
- [ ] Save 5 community screen photos to assets/screens/
- [ ] Test all 4 color schemes with real PDF generation
- [ ] **NEVER make pricing publicly available** — no rates/tiers on any public page

---

## Changelog

### 2026-02-22 — Prospect Research Tool

#### Competitive Intelligence for Sales Calls
- New `pages/7_Research.py` — password-protected prospect research page
- Sales rep enters business name, industry, city, website URL + any context they have
- Tool scrapes prospect's website (new `scrape_website_text()` in web_scraper.py)
- Claude generates 7-section competitive intelligence brief:
  1. Prospect Snapshot — who is this business
  2. Online Presence Assessment — current marketing gaps
  3. Local Advertising Landscape — their market
  4. Why MCTV Makes Sense — tailored to THIS business
  5. Sales Talking Points — conversation starters + rapport builders
  6. Objection Responses — likely pushbacks with natural responses
  7. Recommended Approach — best angle for the pitch
- Parsed into expandable sections with key sections auto-expanded
- Export: Download .txt, Download .json, "Use in Proposal →"
- "Use in Proposal" pre-fills the Elite Advertiser form (business name, industry, city, sales rep, notes)
- Single Claude API call (~5 seconds, ~800 words) — not 7 separate calls
- Prompt template added to `prompts.json` under `prospect_research.competitive_brief`
- Home page updated with 4-column feature cards (added Prospect Research)
- Navigation sidebar updated with Research link
- Inspired by @CodeswithClara Twitter post on using Claude for GBP competitive analysis

### 2026-02-22 — WordPress Integration

#### iframe Embedding (`ebd42f6`)
- New `pages/6_Samples.py` — public sample proposals page, no auth required
- `scripts/generate_samples.py` — batch-generates sample PDFs with pricing stripped out (SampleProposal subclass skips `_pricing` section)
- `.streamlit/config.toml` — enabled iframe embedding (XSRF/CORS disabled)
- `assets/samples/` directory for pre-generated sample PDFs
- WordPress iframe tested on mctvofms.com using Divi Fullwidth Code module
- MEMORY.md updated with WordPress embed code snippets and integration plan
- **Rule: pricing is NEVER exposed on any public-facing page**

### 2026-02-22 — 4 Color Schemes

#### Color Palette System (`a4ae795`)
- Added 4 selectable color schemes: Original Primary, Light Bright & Airy, Dark & Sophisticated, Peaceful Pastels
- `COLOR_SCHEMES` dict in docx_service.py — each with primary, accent, text, gray, white, light colors + hex strings + cover logo filename
- All 50+ hardcoded color references replaced with `self.c[...]` lookups
- Pre-composited logo variants for each scheme (mctv_logo_on_navy/light/dark/pastel.png)
- Horizontal radio selector on Proposals page, passed through all 6 generator calls

### 2026-02-22 — Default Screen Photos

#### Auto-include System (`86a373c`)
- `assets/screens/` directory for community screen photos
- When no venue or extra photos uploaded, auto-populates from assets/screens/
- Glob matching for png, jpg, jpeg, webp

### 2026-02-22 — Visual Polish (v20)

#### Borders & Bullets (`fc014b8`)
- Gold bullet characters (●) with hanging indent (0.6cm) on all bullet items
- Callout boxes: gold left border accent + thin gray sides
- Pricing table: thin gray borders on all cells
- Contract terms: gold left border + gray sides
- Metrics banner: gold top border accent
- `_set_cell_borders()` and `_set_table_borders()` helper methods
- Photo distribution restored with titled sections ("Our Screens in Your Community")

#### Full-bleed Cover & Orphan Fix (`2228095`)
- Cover page: own section with tight margins (0.8/0.5/1.3/1.3 cm)
- Section break after cover restores normal margins
- Cell height 14800 twips for near full-bleed
- Footer skips cover page section
- Consolidated photos to eliminate orphan floaters

### 2026-02-22 — Cover Page Logo Saga

#### Logo Fix (`915edce`)
- Discovered mctv_logo_white.png was actually Shaw Hardware's logo (wrong file!)
- Created proper MCTV white logo by inverting mctv_logo.png pixel-by-pixel
- RGBA transparency doesn't render in LibreOffice PDF conversion
- Created pre-composited mctv_logo_on_navy.png (RGB, navy background baked in)

#### Blank Page Fix (`e727c64`)
- Removed doc.add_page_break() after cover — full-page table naturally pushes to next page
- Fixed mctv_logo_white.png mode from LA to RGBA

### 2026-02-22 — Layout Condensing (v13-v16)

#### Tighter Layout (`fbcfa87`)
- Margins: 1.5cm top/bottom, 2.0cm sides
- Font sizes: body 10.5pt, headers 18pt, sub-headers 12pt
- Inline photos capped at 2.0 inches
- All spacing tightened throughout

### 2026-02-22 — Video Ad Generation

#### Creatomate Integration
- Built `services/creatomate_service.py` — stdlib-only Creatomate API wrapper (urllib, no requests)
- New `pages/5_Video_Ads.py` page with template selector, modification form, and render progress UI
- API is v1 (not v2 as docs suggest) — tested and confirmed working
- Full pipeline: list templates -> create render -> poll status -> download MP4/GIF
- Renders complete in ~6 seconds for the demo template
- Video preview + download button in Streamlit UI
- CDN-hosted videos for 30 days
- `build_mctv_modifications()` helper to map business data to template element names
- Added `CREATOMATE_API_KEY` to `.env` and sidebar status indicator

### 2026-02-22 — The Big Redesign Day

**Elite Advertiser Proposal: 10 pages down to 5**

Started the day with a dense 8-10 page essay-style proposal. Ended with a tight, scannable 5-page document that a business owner can flip through in 2-3 minutes.

#### Proposal Redesign (`be8efa9`)
- Rewrote all Claude prompts with strict word limits (150/100/75/80/60 words per section)
- Switched from essay paragraphs to bullet-style content with callout boxes
- Built `PHOTO_DISTRIBUTION` system to scatter scraped photos across sections instead of one gallery page
- Added `add_bullet_list()` and `add_inline_photos()` methods to docx_service
- Changed system prompt to allow bullet dashes when prompts request them

#### Spacing Tightening (`d7d039d`)
- Removed page break after pricing section (biggest single space saver)
- Eliminated 6 spacer paragraphs after callout boxes, tables, and grids
- Tightened section headers (2+1pt instead of 6+2pt)
- Reduced margins (1.8cm top/bottom, 2.3cm left/right)
- Tighter bullet points (3pt instead of 6pt spacing)

#### Layout Fixes (`a092487`, `fde3605`, `f2ace16`)
- Replaced venue category grid with inline callout box (pipe-separated list)
- Merged contact card into single callout box sentence
- Iterated through 4-col grid, 2-col grid, and finally callout box approach

#### Parsing Fix (`ffcc92d`)
- Why MCTV section now parses callout boxes with or without leading dashes
- Opportunity hook bullets get clean `"- "` prefix formatting
- Two-layer fallback: regex first, then simple line-by-line split

#### Bug Fixes
- Fixed stale scraped photo paths causing "Gallery" header with no photos (`c1c81c2`)
- Fixed blank pages 9-10 from forced page break before Team section (`4867d56`)
- Fixed cover page overflow from too many spacer paragraphs (`5ddb449`)
- Fixed 3 proposal layout issues: blank page 9, gallery placement, banner spacing (`2da9817`)

#### Web Scraper & Design (`c1b1f22`)
- Added website image scraper (stdlib only — urllib, no requests/beautifulsoup)
- Scrapes client logo + photos for use in proposals
- Design upgrades to overall formatting

#### Formatting Fixes (`cbdbe5f`)
- Fixed 6 proposal formatting issues in a single pass

### 2026-02-21 — Launch Day

#### Initial Build (`6af896b`)
- Full Streamlit app with 6 proposal types and 2 report types
- Claude API integration for AI-generated section content
- python-docx document builder with MCTV branding (navy/gold)
- Cover page with MCTV logo
- Pricing table, contract terms, team section
- PDF conversion via LibreOffice/docx2pdf
- Dockerfile for Render deployment

#### Photo Uploads (`bde0f6d`)
- Venue screen photos, ad creative examples, custom images
- Photos inserted into proposals as grids

#### Intake & Leads (`1ba28e2`)
- Public-facing client intake form
- Leads dashboard for the sales team

#### Supabase Integration (`5d9a7d8`, `a67d4ee`)
- Added Supabase for permanent lead storage
- Switched from supabase-py SDK to direct REST API calls (urllib)

#### Email Notifications (`303a9c9`, `255ae9a`)
- SMTP configured for SSL on port 465
- Added debug logging to diagnose delivery issues
- Status: configured but not fully verified

---

## Version History (PDF iterations)

The Elite Advertiser proposal went through 20+ PDF versions on 2026-02-22:

| Version | Pages | Key Change |
|---------|-------|------------|
| v1-v3 | 8-10 | Original essay-style format |
| v4 | 10 | First layout fixes (blank page, gallery, banner) |
| v5 | 11 | Cover page fix, but new blank pages from stale photos |
| v6 | 10 | Added path existence filter, still had Gallery header |
| v7 | 8 | Major redesign deployed — scannable, bullet-style content |
| v8-v9 | 8 | Venue grid and contact card tightening |
| v10 | 8 | Callout box replacements for venue grid and contact |
| v11 | 8 | All spacing tightened, still 1 page over |
| v12 | 7 | Target hit — removed pricing page break, tightened margins |
| v13-v15 | 7 | Further condensing — smaller fonts, tighter margins |
| v16 | 6 | Blank page 2 discovered + wrong logo file |
| v17 | 5 | Blank page fixed, logo still not rendering (transparency) |
| v18 | 5 | MCTV logo working (pre-composited RGB), whitespace gaps |
| v19 | 5 | Full-bleed cover, orphan photos eliminated |
| v20 | 5 | Gold borders, bullets, photo distribution with titles |
