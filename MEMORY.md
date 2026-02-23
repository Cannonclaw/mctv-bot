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

---

## The Project

**MCTV Bot** — A Streamlit web app that generates AI-powered advertising proposals, traction reports, and video ad mockups for MCTV Elite Advertising, North Mississippi's indoor digital billboard network.

- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase REST API (leads/intake) — https://dtapevlfnekzepbtlabj.supabase.co
- **AI:** Anthropic Claude API (claude-sonnet-4-5-20250929 for proposal content)
- **Video:** Creatomate API v1 (https://creatomate.com) — template-based video rendering
- **Auth:** Simple shared password gate (APP_PASSWORD env var)

### Key Files
- `services/docx_service.py` — The big one. All Word document formatting, branding, borders, photos.
- `services/creatomate_service.py` — Creatomate video generation API wrapper (stdlib only).
- `generators/elite_advertiser.py` — The flagship proposal. Most heavily optimized. PHOTO_DISTRIBUTION here.
- `generators/base_proposal.py` — Abstract base class all generators inherit from.
- `generators/multi_brand_bundle.py` — Multi-business bundle (Good Earth was built with this).
- `config/prompts.json` — Claude prompt templates per proposal type.
- `config/config.json` — Company info, pricing tiers, team, markets, venues.
- `services/auth.py` — Login page with MCTV logo.
- `pages/1_Proposals.py` — Main proposal generation page. Handles photo uploads + default screen photos.
- `pages/5_Video_Ads.py` — Video ad generator page.
- `assets/branding/mctv_logo.png` — Dark MCTV logo (RGB, 1920×1080) — for login page, white backgrounds.
- `assets/branding/mctv_logo_on_navy.png` — White MCTV logo pre-composited on navy (RGB, 934×283) — for cover page.
- `assets/branding/mctv_logo_white.png` — White MCTV logo with transparency (RGBA, 934×283).
- `assets/screens/` — Default community screen photos. Auto-included when no user photos uploaded.
- `pages/6_Samples.py` — Public sample proposals page (no auth, iframe-friendly).
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
- `APP_PASSWORD` — Login gate password
- `CREATOMATE_API_KEY` — Video generation API
- `SUPABASE_URL`, `SUPABASE_KEY` — Lead storage
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

**Default screen photos:** When no venue or extra photos uploaded, `assets/screens/*.{png,jpg,jpeg,webp}` auto-populate as extra photos. (Implemented in `pages/1_Proposals.py`.)

### Document Formatting (v20+)
All branding lives in `DocxService`. Key methods and their current settings:
- `add_cover_page()` — full-page navy table, own section, tight margins, no footer
- `add_section_header()` — 18pt navy bold + gold accent bar (5cm wide, 0.12cm tall)
- `add_sub_header()` — 12pt navy bold with ❚ gold left accent
- `add_callout_box()` — cream background + **gold left border** + thin gray sides, 0.3cm left indent
- `add_metrics_banner()` — navy background, gold stats (20pt), **gold top border accent**
- `add_bullet_point()` — **gold ● bullet** + hanging indent (0.6cm) + bold navy title + description
- `add_bullet_list()` — parses "- Title: Description" format, calls add_bullet_point
- `add_pricing_table()` — navy header row, alternating gray rows, **thin gray borders**
- `add_contract_terms()` — 6/12 month boxes with **gold left border** + gray sides
- `add_inline_photos()` — single: 2.0in centered, multi: 2.0in side-by-side
- `add_photos_grid()` — max 2.5in per photo in 2-col grid
- `add_section_divider()` — thin gold horizontal rule (─ × 50, 6pt)
- `add_footer()` — "X | Y" page numbers, right-aligned, **skips cover page section**
- `add_body_text()` — 10.5pt, auto-detects numbered items for bold navy titles

Border helpers:
- `_set_cell_borders(cell, left_color, left_sz, other_color, other_sz)` — per-cell borders
- `_set_table_borders(table, color, sz)` — uniform borders on all cells
- `_remove_table_borders(table)` — removes all borders (for layout tables)

PDF conversion: LibreOffice headless (Docker) or docx2pdf (Windows)

### Prompt Engineering
- Strict word limits per section (150/100/75/80/60 for Elite Advertiser)
- Claude MAY use bullet dashes when prompt asks for them
- No markdown in output — clean plain text only
- Each proposal type has its own prompt keys in prompts.json

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

## What's Been Done (as of 2026-02-22)

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
- Leads dashboard
- Website image scraper (stdlib only — urllib)
- Photo uploads (venue screens, ad examples, custom images)
- Default community screen photos from assets/screens/
- Client logo on cover page (scraped or uploaded)
- PDF conversion (LibreOffice in Docker)
- Cover email generation
- Password authentication with MCTV logo on login page
- Sidebar shows Claude API + Video API connection status
- 4 color schemes (Original, Light & Airy, Dark, Peaceful Pastels)
- Public Samples page (no auth) for WordPress iframe embedding
- iframe-friendly Streamlit config (XSRF + CORS disabled for embeds)

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

### Known Issues / TODO
- Email notifications (SMTP configured but not verified end-to-end)
- Custom domain not set up (bot.mctvofms.com)
- Other generators (Host Media Kit, Multi-Brand, etc.) still use older formatting
- Photo distribution only implemented for Elite Advertiser
- No test suite — all testing is manual (generate proposal, check PDF)
- Need custom MCTV-branded Creatomate template (currently using demo "Search Field Simple")
- **User needs to save 5 community screen photos to `assets/screens/`** — they shared images in chat but files need to be placed manually
- Test all 4 color schemes with a real PDF generation

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

---

## Recent Commits (this session)

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
