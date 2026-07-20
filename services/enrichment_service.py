# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Website enrichment — auto-fill prospect details from a business website.

Two-tier engine used by the Sales Pipeline and Prospector:
  Tier 1: stdlib multi-page scrape (services/web_scraper.scrape_business_info)
  Tier 2: Claude structured extraction over the scraped text, which recovers
          contact names, business hours, and city from messy sites the
          regexes can't parse. Skipped silently if no API key is configured.

Main entry points:
    enrich_from_website(url)         -> dict of prospect fields + images
    merge_enrichment(deal, enrich)   -> {"updates": ..., "conflicts": ...}
"""

import json
import logging
import os
import re

from services.web_scraper import scrape_business_info, scrape_website_images

logger = logging.getLogger(__name__)

ENRICHMENT_MODEL = os.environ.get("ENRICHMENT_MODEL", "claude-haiku-4-5-20251001")

# Deal columns the enrichment engine is allowed to touch
MERGEABLE_FIELDS = (
    "contact_name", "contact_email", "contact_phone", "industry",
    "city", "address", "website", "business_hours", "social_links",
)

MS_MARKETS = ("Oxford", "Starkville", "Tupelo", "Columbus", "West Point")


def normalize_url(url: str) -> str:
    """Normalize a user-typed URL to https://host/path form."""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def enrich_from_website(url: str, include_images: bool = True) -> dict:
    """Scrape a business website and return auto-fill data for a deal.

    Returns dict:
        ok            — True if the site was reachable and yielded data
        error         — message when ok is False
        website       — normalized URL
        contact_name, contact_phone, contact_email, address, city,
        industry, description                       — strings ('' if unknown)
        business_hours — dict day->hours, or list of hour strings, or None
        social_links   — list of profile URLs
        images         — list of dicts from scrape_website_images()
        pages_fetched  — URLs actually scraped
        claude_used    — whether Tier 2 extraction ran
    """
    url = normalize_url(url)
    result = {"ok": False, "error": "", "website": url}
    if not url:
        result["error"] = "No URL provided"
        return result

    info = scrape_business_info(url)
    if not info:
        result["error"] = "Could not reach that website"
        return result

    # Tier 1 baseline from the scraper
    data = {
        "contact_name": "",
        "contact_phone": info.get("phone", ""),
        "contact_email": info.get("email", ""),
        "address": info.get("address", ""),
        "city": _guess_city(info),
        "industry": "",
        "description": info.get("description", ""),
        "business_hours": info.get("hours_candidates") or None,
        "social_links": info.get("social_links", []),
    }

    # Tier 2: Claude structured extraction (best-effort)
    extracted = _claude_extract(info)
    if extracted:
        for field in ("contact_name", "contact_phone", "contact_email",
                      "address", "city", "industry", "description"):
            value = str(extracted.get(field) or "").strip()
            if value and value.lower() not in ("unknown", "n/a", "none"):
                data[field] = value
        hours = extracted.get("business_hours")
        if isinstance(hours, dict) and hours:
            data["business_hours"] = hours
        socials = extracted.get("social_links")
        if isinstance(socials, list) and socials:
            merged = list(data["social_links"])
            for s in socials:
                if isinstance(s, str) and s and s not in merged:
                    merged.append(s)
            data["social_links"] = merged

    result.update(data)
    result["ok"] = True
    result["pages_fetched"] = info.get("pages_fetched", [])
    result["claude_used"] = bool(extracted)

    if include_images:
        try:
            result["images"] = scrape_website_images(url, max_images=8)
        except Exception as e:
            logger.warning("Image scrape failed for %s: %s", url, e)
            result["images"] = []

    return result


def merge_enrichment(deal: dict, enrichment: dict) -> dict:
    """Diff enrichment data against an existing deal.

    Blank deal fields get auto-fill values in `updates`; fields where the
    deal already has a different value land in `conflicts` so the UI can
    let the user choose.

    Returns {"updates": {field: new}, "conflicts": {field: {"current", "new"}}}
    """
    updates, conflicts = {}, {}
    for field in MERGEABLE_FIELDS:
        new = enrichment.get(field)
        if new in (None, "", [], {}):
            continue
        current = deal.get(field)
        if current in (None, "", [], {}):
            updates[field] = new
        elif _norm(current) != _norm(new):
            conflicts[field] = {"current": current, "new": new}
    return {"updates": updates, "conflicts": conflicts}


def format_hours(hours) -> str:
    """Human-readable one-liner for a business_hours value (dict or list)."""
    if not hours:
        return ""
    if isinstance(hours, dict):
        return " | ".join(f"{day}: {val}" for day, val in hours.items() if val)
    if isinstance(hours, list):
        return " | ".join(str(h) for h in hours)
    return str(hours)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _norm(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    # Loose compare: ignore case, whitespace, and phone punctuation
    return re.sub(r"[\s\(\)\-\.]+", "", str(value)).lower()


def _guess_city(info: dict) -> str:
    """Cheap city guess: look for a known MCTV market in scraped text."""
    haystack = " ".join([
        info.get("address", ""), info.get("title", ""),
        info.get("description", ""), info.get("body_text", "")[:2000],
    ]).lower()
    for market in MS_MARKETS:
        if market.lower() in haystack:
            return market
    return ""


def _claude_extract(info: dict) -> dict:
    """Ask Claude to pull structured business details from scraped text.

    Returns {} on any failure (no API key, network error, bad JSON) so the
    caller can fall back to the regex-scraped values.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        return {}

    parts = []
    if info.get("title"):
        parts.append(f"Page title: {info['title']}")
    if info.get("description"):
        parts.append(f"Meta description: {info['description']}")
    if info.get("phones"):
        parts.append(f"Phone numbers found: {', '.join(info['phones'][:3])}")
    if info.get("emails"):
        parts.append(f"Emails found: {', '.join(info['emails'][:3])}")
    if info.get("address"):
        parts.append(f"Address found: {info['address']}")
    if info.get("hours_candidates"):
        parts.append("Hours snippets found: " + " || ".join(info["hours_candidates"]))
    if info.get("social_links"):
        parts.append("Social links: " + ", ".join(info["social_links"][:6]))
    for block in info.get("jsonld", [])[:2]:
        parts.append(f"Structured data: {block[:1200]}")
    if info.get("headings"):
        parts.append("Headings: " + " | ".join(info["headings"][:12]))
    if info.get("body_text"):
        parts.append(f"Website text:\n{info['body_text'][:5000]}")

    prompt = (
        "Extract business details from this scraped website content. "
        "Return ONLY a JSON object (no markdown, no prose) with exactly these keys:\n"
        '  "contact_name"  — owner/manager full name if stated, else ""\n'
        '  "contact_phone" — primary phone in (XXX) XXX-XXXX form, else ""\n'
        '  "contact_email" — best contact email, else ""\n'
        '  "address"       — full street address, else ""\n'
        '  "city"          — city name only (e.g. "Oxford"), else ""\n'
        '  "industry"      — short category like "Restaurant", "Salon & Spa", "Fitness", else ""\n'
        '  "description"   — one sentence describing the business, else ""\n'
        '  "business_hours"— object mapping days ("Mon".."Sun") to hours strings like '
        '"11:00 AM - 9:00 PM" or "Closed"; {} if unknown\n'
        '  "social_links"  — array of social profile URLs; [] if none\n'
        "Use only facts present in the content. Never invent values.\n\n"
        + "\n".join(parts)
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=ENRICHMENT_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            getattr(block, "text", "") for block in response.content
        ).strip()
    except Exception as e:
        logger.warning("Claude extraction failed: %s", e)
        return {}

    # Tolerate a code fence or stray prose around the JSON object
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fence.group(1).strip() if fence else None
    if not candidate:
        obj = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = obj.group(0) if obj else text
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Claude extraction returned unparseable JSON")
        return {}
