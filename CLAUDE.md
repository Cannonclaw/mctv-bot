# MCTV Elite Advertising Bot

## Purpose
Streamlit web app that generates professional advertising proposals and traction reports for MCTV Elite Advertising, North Mississippi's indoor digital billboard network (125+ screens across Oxford, Starkville, and Tupelo).

## Deployment
- **Live URL:** https://mctv-bot.onrender.com
- **GitHub:** https://github.com/Cannonclaw/mctv-bot
- **Hosting:** Render (Docker, auto-deploys from `main` branch)
- **Database:** Supabase (leads/intake storage)
- **Auth:** Simple shared password gate (APP_PASSWORD env var)

## How to Run Locally
```
cd MCTV-Bot
streamlit run app.py
```
Or double-click `run.bat` on Windows.

## Project Structure
```
app.py                          # Main entry point and home page
Dockerfile                      # Docker config for Render deployment
requirements.txt                # Python dependencies

pages/
  0_Intake.py                   # Public-facing lead intake form
  1_Proposals.py                # Proposal generation UI (auth-gated)
  2_Reports.py                  # Traction report generation (auth-gated)
  3_Settings.py                 # Config viewer (auth-gated)
  4_Leads.py                    # Lead management dashboard (auth-gated)
  5_Video_Ads.py                # Video ad generator via Creatomate (auth-gated)

generators/
  base_proposal.py              # Abstract base class for all proposal generators
  elite_advertiser.py           # Flagship 7-page scannable proposal
  host_media_kit.py             # Free screen hosting pitch
  multi_brand_bundle.py         # Multi-business owner bundle
  venue_partner.py              # Revenue-share venue partnership
  category_exclusivity.py       # Industry lockout proposal
  renewal_upgrade.py            # Existing client renewal
  advertiser_report.py          # Advertiser traction report generator
  venue_report.py               # Venue partner report generator

services/
  auth.py                       # Shared password authentication
  claude_service.py             # Anthropic Claude API integration
  config_service.py             # Config/pricing/team lookups
  docx_service.py               # Word document builder (all formatting/branding)
  excel_parser.py               # NTV360 Excel report parser
  leads_service.py              # Supabase + email notification service
  web_scraper.py                # Client website image scraper
  creatomate_service.py         # Creatomate video generation API wrapper

models/
  proposal_data.py              # Dataclasses for proposal inputs
  report_data.py                # Dataclasses for report inputs

config/
  config.json                   # Company info, pricing tiers, team, markets, venues
  prompts.json                  # Claude prompt templates for each proposal section

assets/
  branding/                     # MCTV logo
  team/                         # Team headshot photos

output/                         # Generated files (gitignored)
  proposals/                    # .docx and .pdf proposals
  reports/                      # .docx and .pdf reports
  emails/                       # .txt cover emails
  videos/                       # .mp4 and .gif video ads
```

## Architecture

### Generator Pattern
All proposal generators inherit from `BaseProposal` (abstract base class):
1. `get_sections()` returns ordered `(section_key, title)` tuples
2. `get_prompt_variables()` extracts template variables from input data
3. `build_section()` dispatches to per-section builder methods
4. `generate()` orchestrates: cover page -> Claude prompts -> section building -> save

Sections prefixed with `_` (e.g., `_pricing`, `_team`) skip Claude and use config data directly.

### Photo Distribution System
The `PHOTO_DISTRIBUTION` class attribute on generators controls how scraped client photos are scattered throughout the proposal instead of dumped on one gallery page. Example from `elite_advertiser.py`:
```python
PHOTO_DISTRIBUTION = {
    "opportunity_hook": {"source": "extra", "max": 2},
    "whats_included":   {"source": "extra", "max": 1},
    "why_choose_mctv":  {"source": "extra", "max": 1},
}
```
Generators without `PHOTO_DISTRIBUTION` fall back to the legacy `EXTRA_PHOTO_SECTIONS` gallery behavior. Venue photos and ad examples have their own separate insertion points.

### Document Formatting (docx_service.py)
All MCTV branding lives in `DocxService`:
- **Brand colors:** Navy (#1B1F3B), Gold (#C5A55A), Dark Text (#333333)
- **Section headers:** 20pt navy bold + gold accent bar underneath
- **Callout boxes:** Colored background tables (default #F0EDE4)
- **Metrics banner:** Navy background with gold stats numbers
- **Pricing table:** Header row navy, alternating gray rows, gold rate text
- **Bullet points:** Bold navy title + description text
- **PDF conversion:** LibreOffice headless (Docker) or docx2pdf (Windows)

### Prompt Engineering (prompts.json)
Each proposal type has its own prompt keys. Prompts use `{variable}` placeholders filled by `get_prompt_variables()`. Key rules:
- Claude MAY use bullet dashes (-) when the prompt specifically asks for them
- Strict word limits per section (e.g., 150/100/75/80/60 words for Elite Advertiser)
- No markdown formatting in output (clean plain text only)
- Short paragraphs (2-4 sentences max)

## Proposal Types
1. **Elite Advertiser** - Flagship ~7-page scannable proposal with callout boxes, stats banner, bullet points, and scattered photos
2. **Host Media Kit** - Free screen hosting pitch (venue gets free ads in exchange for wall space)
3. **Multi-Brand Bundle** - Multi-business owner bundle with Buy 2 Get 1 Free deal
4. **Venue Partner / Revenue Share** - Revenue-sharing model with screen installation
5. **Category Exclusivity** - Industry lockout (no competitors can advertise)
6. **Renewal / Upgrade** - Existing client renewal with performance summary

## Report Types
1. **Advertiser Traction Report** - Play counts, venues, impressions from NTV360 Excel data
2. **Venue Partner Report** - Advertiser activity at a specific venue

## Configuration
- `config/config.json` - Company info, 4 pricing tiers, team members, 3 markets, venue categories
- `config/prompts.json` - Claude API prompt templates per proposal type per section
- Environment variables: `ANTHROPIC_API_KEY`, `APP_PASSWORD`, `CREATOMATE_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`

## Key Dependencies
- streamlit, anthropic, python-docx, openpyxl, pandas, python-dotenv, Pillow
- LibreOffice (Docker only, for PDF conversion)

## Important Notes
- The Elite Advertiser proposal has been heavily optimized for scannability (tight spacing, no wasted whitespace, callout boxes instead of paragraphs)
- Removing spacer paragraphs or changing margins affects page count significantly -- test with a real generation after any formatting changes
- Other generators (host_media_kit, multi_brand_bundle, etc.) still use the older formatting style and haven't been redesigned yet
- The web scraper uses only stdlib (urllib, no requests/beautifulsoup) to keep dependencies minimal
- Supabase integration uses raw REST API (urllib) rather than the supabase-py SDK
