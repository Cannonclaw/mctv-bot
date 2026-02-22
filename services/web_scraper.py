"""Website image scraper — grabs logos and photos from a client's website."""

import urllib.request
import urllib.error
import tempfile
import re
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse


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

    # Find all image tags
    img_pattern = re.compile(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?',
        re.IGNORECASE
    )
    # Also try reversed order (alt before src)
    img_pattern2 = re.compile(
        r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']+)["\']',
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

    # Also find OG image and favicon
    og_match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if og_match:
        og_url = urljoin(url, og_match.group(1))
        found[og_url] = "og:image (social sharing image)"

    # Build results
    results = []
    for img_url, alt_text in found.items():
        filename = _get_filename(img_url)
        results.append({
            "url": img_url,
            "alt": alt_text,
            "filename": filename,
        })
        if len(results) >= max_images:
            break

    return results


def download_image(img_url: str) -> str | None:
    """Download an image to a temp file. Returns the file path or None."""
    try:
        parsed = urlparse(img_url)
        ext = Path(parsed.path).suffix or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"):
            ext = ".jpg"

        req = urllib.request.Request(img_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

        # Skip tiny images (icons, spacers) — less than 5KB
        if len(data) < 5000:
            return None

        # Skip SVGs (they don't embed well in docx)
        if ext == ".svg" or b"<svg" in data[:500]:
            return None

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(data)
        tmp.close()
        return tmp.name

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


def _get_filename(url: str) -> str:
    """Extract a clean filename from an image URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name or name == "/":
        return "image.jpg"
    return name[:60]  # Truncate long names
