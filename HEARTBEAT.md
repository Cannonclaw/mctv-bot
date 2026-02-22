# HEARTBEAT.md - Project Status & Changelog

## Current Status: Live on Render

**Last deploy:** 2026-02-22
**URL:** https://mctv-bot.onrender.com
**Branch:** main (auto-deploys on push)

---

## What's Working

- [x] Elite Advertiser proposal (7 pages, scannable, photos scattered inline)
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
- [x] Client logo on cover page (scraped or uploaded)
- [x] PDF conversion (LibreOffice headless in Docker)
- [x] Cover email generation
- [x] Password authentication gate
- [x] Supabase lead storage (REST API)
- [x] Video ad generation (Creatomate API — renders from templates)

## What Needs Attention

- [ ] Email notifications (SMTP configured but not confirmed working end-to-end)
- [ ] Custom domain (bot.mctvofms.com CNAME to Render -- not yet set up)
- [ ] Other generators (Host Media Kit, Multi-Brand, etc.) still use old essay-style formatting -- could benefit from the same scannable redesign
- [ ] Photo distribution only implemented for Elite Advertiser -- other generators use legacy Gallery page
- [ ] No test suite -- all testing is manual (generate proposal, check PDF)

---

## Changelog

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

**Elite Advertiser Proposal: 10 pages down to 7**

Started the day with a dense 8-10 page essay-style proposal. Ended with a tight, scannable 7-page document that a business owner can flip through in 3-5 minutes.

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
- Added website image scraper (stdlib only -- urllib, no requests/beautifulsoup)
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

The Elite Advertiser proposal went through 12 PDF versions on 2026-02-22:

| Version | Pages | Key Change |
|---------|-------|------------|
| v1-v3 | 8-10 | Original essay-style format |
| v4 | 10 | First layout fixes (blank page, gallery, banner) |
| v5 | 11 | Cover page fix, but new blank pages from stale photos |
| v6 | 10 | Added path existence filter, still had Gallery header |
| v7 | 8 | Major redesign deployed -- scannable, bullet-style content |
| v8-v9 | 8 | Venue grid and contact card tightening |
| v10 | 8 | Callout box replacements for venue grid and contact |
| v11 | 8 | All spacing tightened, still 1 page over |
| v12 | 7 | Target hit -- removed pricing page break, tightened margins |
