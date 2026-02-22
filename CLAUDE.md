# MCTV Elite Advertising Bot

## Purpose
Streamlit web app that generates professional advertising proposals and traction reports for MCTV Elite Advertising, North Mississippi's indoor digital billboard network.

## How to Run
```
cd MCTV-Bot
streamlit run app.py
```
Or double-click `run.bat` on Windows.

## Project Structure
- `app.py` - Main entry point and home page
- `pages/` - Streamlit pages (Proposals, Reports, Settings)
- `generators/` - Document generators (6 proposal types + 2 report types)
- `services/` - Core services (Claude API, Word doc builder, Excel parser, config)
- `models/` - Data models (dataclasses for inputs)
- `config/` - Configuration files (config.json, prompts.json)
- `output/` - Generated documents (proposals/, reports/, emails/)

## Proposal Types
1. Elite Advertiser (McGlawn/MS Urgent Care style)
2. Host Media Kit (Hotel Tupelo/Stouts style)
3. Multi-Brand Bundle (Good Earth/Hayden style)
4. Venue Partner / Revenue Share (Tupelo Airport style)
5. Category Exclusivity (Cannon Cleary McGraw style)
6. Renewal / Upgrade (existing client renewal)

## Report Types
1. Advertiser Traction Report (play counts, venues, impressions)
2. Venue Partner Report (advertiser activity at a venue)

## Configuration
- `config/config.json` - Company info, pricing, team, markets, venue categories
- `config/prompts.json` - Claude API prompt templates for each section
- `.env` - ANTHROPIC_API_KEY

## Key Dependencies
- streamlit, anthropic, python-docx, openpyxl, pandas, python-dotenv
