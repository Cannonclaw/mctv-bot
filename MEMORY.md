# MEMORY.md - Persistent Context for Claude

## The Human

**Creed Cannon** — Owner/Managing Partner of MCTV Elite Advertising. Hands-on builder. Runs the business with his wife Mary Michael Cannon. This is his passion project and he's deeply invested in making it great. He thinks fast, iterates fast, and gets excited about new capabilities ("Yes, dream flow!!!").

### Working Style
- Prefers seeing results quickly — generate, check PDF, iterate
- Gives feedback by sharing PDFs and screenshots
- Likes concise explanations, not walls of text
- **Always include URLs/links when asking him to visit a website** (he specifically asked for this)
- Trusts the process — approves plans quickly and lets me run
- Says "back to the proposals" when he wants to refocus after tangents
- When he says a file name (like "MEMORY.md"), he means "update it" or "create it"

---

## The Project

**MCTV Bot** — A Streamlit web app that generates AI-powered advertising proposals, traction reports, and video ad mockups for MCTV Elite Advertising, North Mississippi's indoor digital billboard network.

- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase REST API (leads/intake) — https://dtapevlfnekzepbtlabj.supabase.co
- **AI:** Anthropic Claude API (claude-opus-4-6 for proposal content)
- **Video:** Creatomate API v1 (https://creatomate.com) — template-based video rendering
- **Auth:** Simple shared password gate (APP_PASSWORD env var)

### Key Files
- `services/docx_service.py` — The big one. All Word document formatting and branding.
- `services/creatomate_service.py` — Creatomate video generation API wrapper (stdlib only).
- `generators/elite_advertiser.py` — The flagship proposal. Most heavily optimized.
- `generators/base_proposal.py` — Abstract base class all generators inherit from.
- `generators/multi_brand_bundle.py` — Multi-business bundle (Good Earth was built with this).
- `config/prompts.json` — Claude prompt templates per proposal type.
- `config/config.json` — Company info, pricing tiers, team, markets, venues.
- `services/auth.py` — Login page with MCTV logo.
- `pages/5_Video_Ads.py` — Video ad generator page.
- `SOUL.md` — Brand voice and identity guide.
- `HEARTBEAT.md` — Living changelog and project status.
- `CLAUDE.md` — Technical project documentation.

### Brand Identity
- **Colors:** Navy (#1B1F3B), Gold (#C5A55A), Cream (#F0EDE4), Dark Text (#333333)
- **Font:** Calibri throughout
- **Voice:** Professional but warm. Mississippi local. Partnership over salesmanship. Data-driven. Short and scannable.
- **Never:** Generic marketing jargon, markdown in proposals, paragraphs longer than 4 sentences, vague claims

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
4. `generate()` — orchestrates: cover page -> Claude prompts -> sections -> save
5. Sections prefixed with `_` (e.g., `_pricing`, `_team`) skip Claude API calls

### Cover Page Layout (current)
Navy (#1B1F3B) background table cell with gold/white text:
- "Prepared for" (white italic) → CLIENT NAME (white bold caps) → Business Name (gold)
- Gold accent line (─ × 30)
- "ADVERTISING PARTNERSHIP PROPOSAL" (gold bold, 28pt)
- Gold accent line
- Date (white) → Rep name | MCTV (gold) → email | phone (white) → mctvofms.com (gold)

### Photo Distribution System
`PHOTO_DISTRIBUTION` class attribute scatters scraped photos across sections instead of one gallery page. Only implemented for Elite Advertiser so far. Others use legacy gallery.

### Document Formatting
All branding lives in `DocxService`. Key methods:
- `add_cover_page()` — navy background table cell, gold/white text, gold accent lines
- `add_section_header()` — 20pt navy bold + gold accent bar
- `add_sub_header()` — 13pt navy bold with ❚ gold left accent
- `add_callout_box()` — colored background table (default cream #F0EDE4)
- `add_metrics_banner()` — navy background, gold stats numbers
- `add_bullet_list()` — parses "- Title: Description" format
- `add_inline_photos()` — 1-2 photos within sections
- `add_footer()` — "X | Y" page numbers, right-aligned
- PDF conversion: LibreOffice headless (Docker) or docx2pdf (Windows)

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

### Elite Advertiser Proposal — Fully Redesigned
- Cut from 8-10 pages down to 7 pages
- Scannable format: sub-headers, bullet points, stats banner
- Photos scattered inline (no more gallery page)
- Navy cover page with gold/white text (matching Good Earth)
- Why MCTV uses bold sub-headers with descriptions (not callout boxes)
- Getting Started uses numbered steps
- Pricing gets its own page (page break before to prevent orphaned header)
- Footer shows "X | Y" page numbers
- 14+ PDF iterations to get it right

### Creatomate Video Integration — Live
- `services/creatomate_service.py` — stdlib-only API wrapper (urllib, no requests)
- `pages/5_Video_Ads.py` — template selector, render form, progress bar, video preview + download
- API is **v1** (not v2 as docs suggest) — tested and confirmed working
- Renders complete in ~6 seconds for demo template
- Paste-key fallback when env var not set
- `CREATOMATE_API_KEY` added to Render env vars
- Credit math: Essential plan ($41/mo) = 2000 credits. 15-sec 1080p/30fps = ~9 credits = ~215 videos/month

### Working Features
- 6 proposal types + 2 report types
- Video ad generation via Creatomate
- Client intake form (public-facing, saves to Supabase)
- Leads dashboard
- Website image scraper (stdlib only — urllib)
- Photo uploads (venue screens, ad examples, custom images)
- Client logo on cover page (scraped or uploaded)
- PDF conversion (LibreOffice in Docker)
- Cover email generation
- Password authentication with MCTV logo on login page
- Sidebar shows Claude API + Video API connection status

### Known Issues / TODO
- Email notifications (SMTP configured but not verified end-to-end)
- Custom domain not set up (bot.mctvofms.com)
- Other generators (Host Media Kit, Multi-Brand, etc.) still use older formatting — could benefit from the same scannable redesign as Elite Advertiser
- Photo distribution only implemented for Elite Advertiser
- No test suite — all testing is manual (generate proposal, check PDF)
- Need to design a custom MCTV-branded Creatomate template (currently using demo "Search Field Simple")
- v15 PDF pending — cover page title order fix, pricing orphan fix, Why MCTV parsing fix all deployed but not yet verified

---

## Lessons Learned

1. **Spacing is everything** in python-docx. Removing one page break or spacer paragraph can save a whole page. Always test with a real PDF after formatting changes.
2. **Claude's output format varies.** Parse line-by-line with fallbacks. Don't assume leading dashes, colons, or any specific format. The Why MCTV parser was rewritten 3 times.
3. **python-docx has no native page background.** Use a full-width single-cell table with fill color as a workaround.
4. **Keep dependencies minimal.** Web scraper uses stdlib (urllib), Supabase uses raw REST API, Creatomate uses urllib. Fewer dependencies = fewer deployment headaches.
5. **The user tests by generating real proposals and checking the PDF.** No automated tests exist. Visual verification is the workflow.
6. **Creatomate API is v1, not v2.** Despite their docs showing v2 in curl examples, the actual working endpoints are at `https://api.creatomate.com/v1/`.
7. **Cloudflare blocks urllib without User-Agent.** Always add `User-Agent: MCTV-Bot/1.0` header to API requests.
8. **Cover page title/subtitle semantics matter.** The `title` param is the big center text ("ADVERTISING PARTNERSHIP PROPOSAL"), `subtitle` is the business name, `prepared_for` is the contact person's name.
9. **Page breaks before sections** prevent orphaned headers (header on one page, content on next).
10. **The Good Earth proposal is the gold standard.** Always reference it when designing new layouts or evaluating quality.
