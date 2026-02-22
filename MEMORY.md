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

---

## The Project

**MCTV Bot** — A Streamlit web app that generates AI-powered advertising proposals and traction reports for MCTV Elite Advertising, North Mississippi's indoor digital billboard network.

- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase REST API (leads/intake) — https://dtapevlfnekzepbtlabj.supabase.co
- **AI:** Anthropic Claude API (claude-opus-4-6 for proposal content)
- **Auth:** Simple shared password gate (APP_PASSWORD env var)

### Key Files
- `services/docx_service.py` — The big one. All Word document formatting and branding. ~760 lines.
- `generators/elite_advertiser.py` — The flagship proposal. Most heavily optimized.
- `generators/base_proposal.py` — Abstract base class all generators inherit from.
- `config/prompts.json` — Claude prompt templates per proposal type.
- `config/config.json` — Company info, pricing tiers, team, markets, venues.
- `SOUL.md` — Brand voice and identity guide.
- `HEARTBEAT.md` — Living changelog and project status.
- `CLAUDE.md` — Technical project documentation.

### Brand Identity
- **Colors:** Navy (#1B1F3B), Gold (#C5A55A), Cream (#F0EDE4), Dark Text (#333333)
- **Font:** Calibri throughout
- **Voice:** Professional but warm. Mississippi local. Partnership over salesmanship. Data-driven. Short and scannable.
- **Never:** Generic marketing jargon, markdown in proposals, paragraphs longer than 4 sentences, vague claims

### Team
- **T. Creed Cannon** — Owner/Managing Partner
- **Mary Michael Cannon** — Owner/Managing Partner
- **Swayze Hollingsworth** — Director of Sales

### Pricing Tiers
- 10 Screens: $350/month
- 20 Screens: $500/month
- 40 Screens: $800/month
- 75+ Screens: $1,300/month

### Markets
- Oxford (75 screens), Starkville (30), Tupelo (25)
- Expanding: Columbus, West Point

---

## Architecture Patterns

### Generator Pattern
All proposal generators inherit from `BaseProposal`:
1. `get_sections()` — ordered (key, title) tuples
2. `get_prompt_variables()` — template variables from input data
3. `build_section()` — dispatches to per-section builders
4. `generate()` — orchestrates: cover page -> Claude prompts -> sections -> save
5. Sections prefixed with `_` (e.g., `_pricing`, `_team`) skip Claude API calls

### Photo Distribution System
`PHOTO_DISTRIBUTION` class attribute scatters scraped photos across sections instead of one gallery page. Only implemented for Elite Advertiser so far. Others use legacy gallery.

### Document Formatting
All branding lives in `DocxService`. Key methods:
- `add_cover_page()` — cream background table cell, gold accent lines, logos
- `add_section_header()` — 20pt navy bold + gold accent bar
- `add_callout_box()` — colored background table (default cream)
- `add_metrics_banner()` — navy background, gold stats numbers
- `add_bullet_list()` — parses "- Title: Description" format
- `add_inline_photos()` — 1-2 photos within sections
- PDF conversion: LibreOffice headless (Docker) or docx2pdf (Windows)

### Prompt Engineering
- Strict word limits per section (150/100/75/80/60 for Elite Advertiser)
- Claude MAY use bullet dashes when prompt asks for them
- No markdown in output — clean plain text only
- Each proposal type has its own prompt keys in prompts.json

---

## What's Been Done (as of 2026-02-22)

### Elite Advertiser Proposal — Fully Redesigned
- Cut from 8-10 pages down to 7 pages
- Scannable format: callout boxes, bullet points, stats banner
- Photos scattered inline (no more gallery page)
- Cream cover page with gold accent lines
- Two-layer parsing for Why MCTV callout boxes (regex + fallback)
- 12 PDF iterations to get it right

### Working Features
- 6 proposal types + 2 report types
- Client intake form (public-facing, saves to Supabase)
- Leads dashboard
- Website image scraper (stdlib only — urllib)
- Photo uploads (venue screens, ad examples, custom images)
- Client logo on cover page (scraped or uploaded)
- PDF conversion (LibreOffice in Docker)
- Cover email generation
- Password authentication

### Known Issues / TODO
- Email notifications (SMTP configured but not verified end-to-end)
- Custom domain not set up (bot.mctvofms.com)
- Other generators still use old essay-style formatting
- Photo distribution only for Elite Advertiser
- No test suite

---

## Creatomate Integration (In Progress)

**What:** Auto-generate video ad mockups alongside proposals.
**Platform:** Creatomate (https://creatomate.com) — REST API, template-based video rendering
**Status:** User has API key, integration not yet built
**Plan:**
1. Design MCTV ad template in Creatomate editor (1920x1080)
2. Build `services/creatomate_service.py`
3. Add "Generate Video Ad" button to Proposals page
4. Template modifications via API: swap in client name, photos, branding

**Credit Math:** Essential plan ($41/mo) = 2000 credits. A 15-sec 1080p/30fps video ~ 9 credits = ~215 videos/month.

---

## Lessons Learned

1. **Spacing is everything** in python-docx. Removing one page break or spacer paragraph can save a whole page. Always test with a real PDF after formatting changes.
2. **Claude's output format varies.** Always build two-layer parsing: regex first, simple split fallback. Don't assume leading dashes, colons, or any specific format.
3. **python-docx has no native page background.** Use a full-width single-cell table with fill color as a workaround.
4. **Keep dependencies minimal.** Web scraper uses stdlib (urllib), Supabase uses raw REST API. Fewer dependencies = fewer deployment headaches.
5. **The user tests by generating real proposals and checking the PDF.** No automated tests exist. Visual verification is the workflow.
