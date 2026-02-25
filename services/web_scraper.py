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

    # Build results with classification
    results = []
    for img_url, alt_text in found.items():
        filename = _get_filename(img_url)
        category = classify_image(img_url, alt_text)
        if category == "skip":
            continue  # Filter out junk images entirely
        results.append({
            "url": img_url,
            "alt": alt_text,
            "filename": filename,
            "category": category,  # 'logo', 'ad_example', or 'product'
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


def classify_image(img_url: str, alt_text: str = "", file_size: int = 0) -> str:
    """Classify an image based on URL, alt text, and file size.

    Returns one of: 'logo', 'ad_example', 'product', 'skip'
    """
    url_lower = img_url.lower()
    alt_lower = (alt_text or "").lower()
    combined = url_lower + " " + alt_lower

    # Skip: tiny images, icons, UI elements
    skip_signals = [
        "icon", "button", "menu", "arrow", "chevron", "close",
        "hamburger", "spinner", "loading", "placeholder", "spacer",
        "widget", "avatar", "gravatar", "emoji", "payment",
        "visa", "mastercard", "amex", "paypal", "credit-card",
    ]
    for signal in skip_signals:
        if signal in combined:
            return "skip"

    # Skip very small files (< 10KB) — likely UI elements
    if file_size > 0 and file_size < 10000:
        return "skip"

    # Logo detection
    logo_signals = ["logo", "brand", "header-image", "site-logo", "navbar-brand"]
    for signal in logo_signals:
        if signal in combined:
            return "logo"

    # OG image is usually a logo or hero — treat as logo
    if "og:image" in alt_lower:
        return "logo"

    # Ad/promo detection
    ad_signals = [
        "ad", "banner", "promo", "promotion", "campaign",
        "advertisement", "flyer", "deal", "offer", "coupon",
        "special", "sale",
    ]
    for signal in ad_signals:
        if signal in combined:
            return "ad_example"

    # Everything else that passes size check is a product/content photo
    return "product"


def _get_filename(url: str) -> str:
    """Extract a clean filename from an image URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name or name == "/":
        return "image.jpg"
    return name[:60]  # Truncate long names
