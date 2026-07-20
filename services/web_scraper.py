# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Website scraper — grabs images and text content from client websites."""

import urllib.request
import urllib.error
import tempfile
import re
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse


def scrape_website_text(url: str, max_chars: int = 8000) -> dict:
    """Scrape a website and extract structured text content for prospect research.

    Returns dict with keys:
        title, description, headings, body_text, phone, email, address,
        social_links, raw_text
    """
    if not url:
        return {}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[web_scraper] Failed to fetch {url}: {e}")
        return {}

    result = {}

    # Page title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    result["title"] = title_match.group(1).strip() if title_match else ""

    # Meta description
    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if not desc_match:
        desc_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE,
        )
    result["description"] = desc_match.group(1).strip() if desc_match else ""

    # Headings (h1-h3)
    headings = []
    for tag in ["h1", "h2", "h3"]:
        for m in re.finditer(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.IGNORECASE | re.DOTALL):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if text and len(text) < 200:
                headings.append(text)
    result["headings"] = headings[:20]

    # Strip HTML tags for body text
    clean = re.sub(
        r'<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>',
        '', html, flags=re.IGNORECASE | re.DOTALL,
    )
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    result["body_text"] = clean[:max_chars]

    # Phone numbers
    phones = re.findall(r'[\(]?\d{3}[\)\-\.\s]?\s*\d{3}[\-\.\s]\d{4}', html)
    result["phone"] = phones[0] if phones else ""

    # Email addresses
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
    biz_emails = [
        e for e in emails
        if not any(x in e.lower() for x in
                   ["@sentry", "@google", "@facebook", "@example", "@wix", "@wordpress"])
    ]
    result["email"] = biz_emails[0] if biz_emails else ""

    # Social media links
    social_domains = [
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "youtube.com", "tiktok.com", "yelp.com",
    ]
    social = []
    for domain in social_domains:
        matches = re.findall(
            rf'href=["\']([^"\']*{re.escape(domain)}[^"\']*)["\']',
            html, re.IGNORECASE,
        )
        social.extend(matches[:1])
    result["social_links"] = social

    # Address (look near "address" or structured data)
    addr_match = re.search(
        r'(?:street|address)["\s:>]*([^<"]{10,100}(?:MS|Mississippi)\s+\d{5})',
        html, re.IGNORECASE,
    )
    result["address"] = addr_match.group(1).strip() if addr_match else ""

    return result


def _fetch_html(url: str, timeout: int = 10) -> str:
    """Fetch a URL and return decoded HTML, or '' on any failure."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[web_scraper] Failed to fetch {url}: {e}")
        return ""


# Days + time-range patterns for business-hours extraction
_DAY_PAT = (
    r"(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)"
    r"(?:day|sday|nesday|rsday|urday)?"
)
_TIME_PAT = r"\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?"
_HOURS_RE = re.compile(
    rf"({_DAY_PAT}(?:\s*[-–—&,]\s*{_DAY_PAT})*[\s:]{{1,5}}"
    rf"(?:{_TIME_PAT}\s*(?:-|–|—|to|until)\s*{_TIME_PAT}"
    rf"|closed|open\s*24(?:\s*hours|/7)?))",
    re.IGNORECASE,
)


def _extract_hours_candidates(text: str, max_lines: int = 14) -> list[str]:
    """Pull business-hours-looking snippets out of plain text."""
    seen = set()
    out = []
    for m in _HOURS_RE.finditer(text):
        snippet = re.sub(r"\s+", " ", m.group(1)).strip()
        key = snippet.lower()
        if key not in seen:
            seen.add(key)
            out.append(snippet)
        if len(out) >= max_lines:
            break
    return out


def _find_info_page_links(html: str, base_url: str, max_links: int = 2) -> list[str]:
    """Find same-site contact/about/hours page links in a homepage's HTML."""
    keywords = ("contact", "about", "hours", "location", "visit", "find-us")
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")

    found = []
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', html, re.IGNORECASE):
        href = m.group(1).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if not any(kw in href.lower() for kw in keywords):
            continue
        full = urljoin(base_url, href)
        host = urlparse(full).netloc.lower().removeprefix("www.")
        if host != base_host:
            continue
        if full.rstrip("/") == base_url.rstrip("/"):
            continue
        if full not in found:
            found.append(full)
        if len(found) >= max_links:
            break
    return found


def scrape_business_info(url: str, max_extra_pages: int = 2) -> dict:
    """Scrape a business website for contact details, hours, and socials.

    Fetches the homepage plus up to `max_extra_pages` contact/about/hours
    pages discovered from homepage links (falling back to common paths),
    then aggregates everything found across pages.

    Returns dict with keys:
        title, description, headings, body_text, phone, phones, email,
        emails, address, social_links, hours_candidates, jsonld,
        pages_fetched
    Empty dict if the homepage can't be reached.
    """
    if not url:
        return {}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    base = scrape_website_text(url)
    if not base:
        return {}

    home_html = _fetch_html(url)
    combined_text = base.get("body_text", "")
    pages_fetched = [url]

    # Discover contact/about pages from links; fall back to common paths
    extra_urls = _find_info_page_links(home_html, url, max_links=max_extra_pages)
    if not extra_urls:
        extra_urls = [urljoin(url + "/", p) for p in ("contact", "contact-us", "about")]
        extra_urls = extra_urls[:max_extra_pages]

    phones, emails, socials = [], [], list(base.get("social_links", []))
    if base.get("phone"):
        phones.append(base["phone"])
    if base.get("email"):
        emails.append(base["email"])
    address = base.get("address", "")

    all_html = home_html
    for extra in extra_urls:
        info = scrape_website_text(extra, max_chars=4000)
        if not info or not info.get("body_text"):
            continue
        pages_fetched.append(extra)
        combined_text += "\n\n" + info["body_text"]
        if info.get("phone") and info["phone"] not in phones:
            phones.append(info["phone"])
        if info.get("email") and info["email"] not in emails:
            emails.append(info["email"])
        if not address and info.get("address"):
            address = info["address"]
        for s in info.get("social_links", []):
            if s not in socials:
                socials.append(s)
        all_html += "\n" + _fetch_html(extra)

    # Structured data (schema.org LocalBusiness) often has phone + hours
    jsonld = re.findall(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>',
        all_html, re.IGNORECASE | re.DOTALL,
    )
    jsonld = [j.strip()[:2000] for j in jsonld[:3]]

    hours = _extract_hours_candidates(combined_text)
    for block in jsonld:
        for m in re.finditer(r'"openingHours[^"]*"\s*:\s*("(?:[^"]*)"|\[[^\]]*\])', block):
            snippet = re.sub(r'[\[\]"]', " ", m.group(1))
            snippet = re.sub(r"\s+", " ", snippet).strip()
            if snippet and snippet.lower() not in {h.lower() for h in hours}:
                hours.append(snippet)

    return {
        "title": base.get("title", ""),
        "description": base.get("description", ""),
        "headings": base.get("headings", []),
        "body_text": combined_text[:12000],
        "phone": phones[0] if phones else "",
        "phones": phones,
        "email": emails[0] if emails else "",
        "emails": emails,
        "address": address,
        "social_links": socials,
        "hours_candidates": hours,
        "jsonld": jsonld,
        "pages_fetched": pages_fetched,
    }


def scrape_website_images(url: str, max_images: int = 12) -> list[dict]:
    """Scrape a website for images and return info about each.

    Returns list of dicts: [{"url": ..., "alt": ..., "filename": ...}, ...]
    """
    if not url:
        return []

    # Ensure URL has scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[web_scraper] Failed to fetch {url}: {e}")
        return []

    # Find all image tags — src attribute
    img_pattern = re.compile(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?',
        re.IGNORECASE
    )
    # Also try reversed order (alt before src)
    img_pattern2 = re.compile(
        r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']+)["\']',
        re.IGNORECASE
    )
    # Lazy-loaded images: data-src, data-lazy-src, data-original
    lazy_pattern = re.compile(
        r'<img[^>]+data-(?:lazy-)?(?:src|original)=["\']([^"\']+)["\'][^>]*'
        r'(?:alt=["\']([^"\']*)["\'])?',
        re.IGNORECASE
    )
    # srcset: grab the largest resolution image
    srcset_pattern = re.compile(
        r'<img[^>]+srcset=["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    found = {}
    for match in img_pattern.finditer(html):
        src = match.group(1)
        alt = match.group(2) or ""
        full_url = urljoin(url, src)
        if _is_valid_image(full_url):
            found[full_url] = alt

    for match in img_pattern2.finditer(html):
        alt = match.group(1) or ""
        src = match.group(2)
        full_url = urljoin(url, src)
        if _is_valid_image(full_url):
            found[full_url] = alt

    # Lazy-loaded images (data-src, data-lazy-src, data-original)
    for match in lazy_pattern.finditer(html):
        src = match.group(1)
        alt = match.group(2) or ""
        full_url = urljoin(url, src)
        if full_url not in found and _is_valid_image(full_url):
            found[full_url] = alt

    # srcset: pick the largest image from each srcset
    for match in srcset_pattern.finditer(html):
        srcset_str = match.group(1)
        best_url, best_w = "", 0
        for entry in srcset_str.split(","):
            parts = entry.strip().split()
            if len(parts) >= 1:
                candidate = parts[0]
                w = int(parts[1].rstrip("w")) if len(parts) > 1 and parts[1].endswith("w") else 0
                if w > best_w:
                    best_url, best_w = candidate, w
        if best_url:
            full_url = urljoin(url, best_url)
            if full_url not in found and _is_valid_image(full_url):
                found[full_url] = ""

    # Also find OG image and favicon
    og_match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if og_match:
        og_url = urljoin(url, og_match.group(1))
        found[og_url] = "og:image (social sharing image)"

    # Build results with enhanced classification
    results = []
    for img_url, alt_text in found.items():
        filename = _get_filename(img_url)
        cls = classify_image(img_url, alt_text)
        if cls["category"] == "skip":
            continue  # Filter out junk images entirely
        results.append({
            "url": img_url,
            "alt": alt_text,
            "filename": filename,
            "category": cls["category"],
            "confidence": cls["confidence"],
            "alt_category": cls["alt_category"],
        })
        if len(results) >= max_images:
            break

    return results


def _normalize_cdn_url(img_url: str) -> str:
    """Rewrite CDN thumbnail URLs to request full-size images.

    Handles Wix, Squarespace, and Shopify CDN URL patterns that serve
    tiny placeholders or unsupported formats (AVIF) in the initial HTML.
    """
    # Wix: rewrite /v1/fill/... to request ~800px wide, JPEG format
    if "wixstatic.com/media/" in img_url and "/v1/fill/" in img_url:
        # Extract base: everything up to /v1/fill/
        base, _, params_and_name = img_url.partition("/v1/fill/")
        # Get the filename at the end (after the last /)
        filename = params_and_name.rsplit("/", 1)[-1] if "/" in params_and_name else ""
        if filename:
            return f"{base}/v1/fill/w_800,h_800,al_c,q_85,enc_auto/{filename}"
        return img_url

    # Squarespace: remove ?format=XXXw size constraint
    if "squarespace-cdn.com" in img_url or "sqspcdn.com" in img_url:
        if "?format=" in img_url:
            return img_url.split("?format=")[0] + "?format=1500w"

    # Shopify: request large size instead of thumbnail
    if "cdn.shopify.com" in img_url:
        # Replace _100x, _200x etc with _800x
        img_url = re.sub(r'_\d+x(\d+)?\.', '_800x.', img_url)

    return img_url


def download_image(img_url: str) -> str | None:
    """Download an image to a temp file. Returns the file path or None.

    Converts .webp images to .png so they embed correctly in Word documents
    (python-docx does not support .webp). Also validates minimum pixel
    dimensions to filter out thumbnails and spacers.
    """
    try:
        img_url = _normalize_cdn_url(img_url)
        parsed = urlparse(img_url)
        ext = Path(parsed.path).suffix.lower().split("?")[0] or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"):
            ext = ".jpg"

        req = urllib.request.Request(img_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

        # Skip tiny images (icons, spacers) — less than 3KB
        if len(data) < 3000:
            return None

        # Skip SVGs (they don't embed well in docx)
        if ext == ".svg" or b"<svg" in data[:500]:
            return None

        # Detect actual format from file header (CDNs often ignore extension)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ext = ".webp"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif data[:2] in (b"\xff\xd8",):
            ext = ".jpg"

        # Save raw download first
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(data)
        tmp.close()
        raw_path = tmp.name

        # Convert .webp to .png (python-docx doesn't support webp)
        if ext == ".webp":
            try:
                from PIL import Image
                with Image.open(raw_path) as img:
                    # Also validate pixel dimensions
                    w, h = img.size
                    if w < 50 or h < 50:
                        os.unlink(raw_path)
                        return None
                    png_path = raw_path.replace(".webp", ".png")
                    img.convert("RGB").save(png_path, "PNG")
                os.unlink(raw_path)
                return png_path
            except Exception as e:
                print(f"[web_scraper] webp conversion failed for {img_url}: {e}")
                os.unlink(raw_path)
                return None

        # Validate pixel dimensions for non-webp images
        try:
            from PIL import Image
            with Image.open(raw_path) as img:
                w, h = img.size
                if w < 50 or h < 50:
                    os.unlink(raw_path)
                    return None
        except Exception:
            pass  # If PIL can't read it, let docx try anyway

        return raw_path

    except Exception as e:
        print(f"[web_scraper] Failed to download {img_url}: {e}")
        return None


def _is_valid_image(url: str) -> bool:
    """Filter out tracking pixels, tiny icons, and non-image URLs."""
    url_lower = url.lower()

    # Skip common non-content images
    skip_patterns = [
        "pixel", "tracker", "beacon", "spacer", "blank",
        "1x1", "facebook", "google", "analytics", "twitter",
        ".svg", "gravatar", "wp-emoji", "s.w.org",
        "feeds.feedburner", "button", "badge", "icon",
    ]
    for pattern in skip_patterns:
        if pattern in url_lower:
            return False

    # Must look like an image
    valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Accept if it has an image extension
    if any(path.endswith(ext) for ext in valid_exts):
        return True

    # Accept if it looks like an image CDN URL (even without extension)
    if "image" in url_lower or "photo" in url_lower or "upload" in url_lower:
        return True

    return False


def classify_image(img_url: str, alt_text: str = "", file_size: int = 0,
                   page_position: str | None = None) -> dict:
    """Classify an image into one of 7 categories with confidence score.

    Categories: logo, product, venue, team, food, promo, skip

    Returns dict:
        category   — best-fit category string
        confidence — float 0.0-1.0 (how sure we are)
        alt_category — second-best category, or None
    """
    url_lower = img_url.lower()
    alt_lower = (alt_text or "").lower()
    combined = url_lower + " " + alt_lower
    _SKIP = {"category": "skip", "confidence": 0.95, "alt_category": None}

    # ── Hard skip: UI elements, icons, tracking pixels ──────────────────
    skip_signals = [
        "icon", "button", "arrow", "chevron", "close",
        "hamburger", "spinner", "loading", "placeholder", "spacer",
        "avatar", "gravatar", "emoji", "payment",
        "visa", "mastercard", "amex", "paypal", "credit-card",
    ]
    # Note: "menu" removed (conflicts with food menus)
    # Note: "widget" removed (too broad, catches product descriptions)
    for signal in skip_signals:
        if signal in combined:
            return _SKIP

    # Very small files are almost always UI chrome
    if 0 < file_size < 10_000:
        return {"category": "skip", "confidence": 0.80, "alt_category": None}

    # ── Score each non-skip category ────────────────────────────────────
    scores = {
        "logo": 0.0, "venue": 0.0, "team": 0.0,
        "food": 0.0, "promo": 0.0, "product": 0.10,  # base score
    }

    # — Logo signals —
    logo_kw = ["logo", "brand", "header-image", "site-logo", "navbar-brand"]
    for kw in logo_kw:
        if kw in combined:
            scores["logo"] += 0.40
    if "og:image" in alt_lower:
        scores["logo"] += 0.35
    # Root-level images more likely logos
    parsed = urlparse(img_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) <= 1:
        scores["logo"] += 0.10
    # Logos are typically 10-100 KB
    if 10_000 <= file_size <= 100_000:
        scores["logo"] += 0.10

    # — Venue / location signals —
    venue_kw = [
        "interior", "exterior", "office", "building", "store",
        "storefront", "restaurant", "lobby", "room", "space",
        "facility", "location", "outside", "inside", "shop",
        "clinic", "salon", "gym", "studio", "warehouse",
    ]
    for kw in venue_kw:
        if kw in combined:
            scores["venue"] += 0.35

    # — Team / people signals —
    team_kw = [
        "team", "staff", "about", "headshot", "portrait",
        "employee", "founder", "owner", "ceo", "manager",
        "our-team", "meet", "people", "crew", "doctor",
        "chef", "therapist", "instructor",
    ]
    for kw in team_kw:
        if kw in combined:
            scores["team"] += 0.35

    # — Food / menu signals —
    food_kw = [
        "menu", "dish", "food", "plate", "meal", "cuisine",
        "recipe", "appetizer", "entree", "dessert", "drink",
        "cocktail", "wine", "beer", "coffee", "breakfast",
        "lunch", "dinner", "brunch", "pizza", "burger",
        "sandwich", "salad", "soup", "sushi",
    ]
    for kw in food_kw:
        if kw in combined:
            scores["food"] += 0.35

    # — Promo / ad signals (word-boundary for short words) —
    promo_exact = ["ad", "sale", "deal", "offer"]
    for kw in promo_exact:
        if re.search(r'\b' + kw + r'\b', combined):
            scores["promo"] += 0.35
    promo_substr = [
        "banner", "promo", "promotion", "campaign",
        "advertisement", "flyer", "coupon", "special",
    ]
    for kw in promo_substr:
        if kw in combined:
            scores["promo"] += 0.35

    # — Product / content boost —
    # Larger images are more likely real content photos
    if file_size > 100_000:
        scores["product"] += 0.15
    # Deep-path images tend to be content, not logos
    if len(path_parts) >= 3:
        scores["product"] += 0.10

    # — Page-position boost —
    if page_position == "header":
        scores["logo"] += 0.20
    elif page_position == "content":
        scores["product"] += 0.10

    # ── Pick winner ─────────────────────────────────────────────────────
    scores = {k: min(v, 1.0) for k, v in scores.items()}
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    best_cat, best_score = ranked[0]
    alt_cat, alt_score = ranked[1]

    # Very low score → generic product photo
    if best_score < 0.15:
        return {"category": "product", "confidence": 0.25, "alt_category": None}

    return {
        "category": best_cat,
        "confidence": round(best_score, 2),
        "alt_category": alt_cat if alt_score > 0.15 else None,
    }


def score_image_quality(file_path: str) -> dict:
    """Score a downloaded image's quality based on pixel dimensions.

    Returns dict with keys:
        width, height, megapixels, aspect_ratio, orientation,
        quality_tier ('hd' | 'good' | 'low'), quality_label
    """
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            w, h = img.size
    except Exception:
        return {
            "width": 0, "height": 0, "megapixels": 0.0,
            "aspect_ratio": 1.0, "orientation": "unknown",
            "quality_tier": "low", "quality_label": "Unknown",
        }

    longest = max(w, h)
    mp = (w * h) / 1_000_000
    ar = w / h if h > 0 else 1.0

    if ar > 1.2:
        orientation = "landscape"
    elif ar < 0.8:
        orientation = "portrait"
    else:
        orientation = "square"

    if longest >= 1000:
        tier, label = "hd", f"{w}\u00d7{h} HD"
    elif longest >= 400:
        tier, label = "good", f"{w}\u00d7{h} OK"
    else:
        tier, label = "low", f"{w}\u00d7{h} Low Res \u26a0\ufe0f"

    return {
        "width": w, "height": h,
        "megapixels": round(mp, 2),
        "aspect_ratio": round(ar, 2),
        "orientation": orientation,
        "quality_tier": tier,
        "quality_label": label,
    }


def auto_assign_photos(classified_images: list[dict]) -> list[dict]:
    """Assign optimal default placements based on classification.

    Takes the list from scrape_website_images() (each dict has url, alt,
    filename, category, confidence, alt_category) and adds:
        default_placement — one of the placement option strings
        auto_assigned     — True if the engine chose a slot (vs. Skip)

    Logic:
      1. Highest-confidence logo  → Client Logo
      2. Top 4 remaining by score → The Opportunity (page 2)
      3. Next 6 by score          → Market Coverage (page 4)
      4. Rest                     → Skip

    Relevance score = confidence + category_bonus.
    """
    if not classified_images:
        return []

    # Category bonuses bias good content toward page 2
    _BONUS = {
        "venue": 0.20, "product": 0.10, "food": 0.10,
        "team": 0.05, "promo": -0.30, "logo": 0.0, "skip": -1.0,
    }

    # ── 1. Find best logo ──────────────────────────────────────────────
    best_logo_idx = None
    best_logo_conf = 0.0
    for i, img in enumerate(classified_images):
        if img.get("category") == "logo":
            conf = img.get("confidence", 0.5)
            if conf > best_logo_conf:
                best_logo_idx = i
                best_logo_conf = conf

    # ── 2. Rank remaining images by relevance score ────────────────────
    candidates = []
    for i, img in enumerate(classified_images):
        if i == best_logo_idx:
            continue
        cat = img.get("category", "product")
        if cat == "skip":
            continue
        conf = img.get("confidence", 0.5)
        bonus = _BONUS.get(cat, 0.0)
        candidates.append((i, conf + bonus))

    candidates.sort(key=lambda x: -x[1])

    page2_set = set()
    page4_set = set()
    for i, score in candidates:
        if score < 0.10:
            break  # too low to auto-assign
        if len(page2_set) < 4:
            page2_set.add(i)
        elif len(page4_set) < 6:
            page4_set.add(i)

    # ── 3. Build results preserving original order ─────────────────────
    results = []
    for i, img in enumerate(classified_images):
        entry = dict(img)  # shallow copy
        if i == best_logo_idx and best_logo_conf >= 0.30:
            entry["default_placement"] = "Client Logo"
            entry["auto_assigned"] = True
        elif i in page2_set:
            entry["default_placement"] = "The Opportunity (page 2)"
            entry["auto_assigned"] = True
        elif i in page4_set:
            entry["default_placement"] = "Market Coverage (page 4)"
            entry["auto_assigned"] = True
        else:
            entry["default_placement"] = "Skip"
            entry["auto_assigned"] = False
        results.append(entry)

    return results


def _get_filename(url: str) -> str:
    """Extract a clean filename from an image URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name or name == "/":
        return "image.jpg"
    return name[:60]  # Truncate long names
