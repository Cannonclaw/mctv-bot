# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Derived artwork for the letterhead templates.

Builds trimmed, transparent-background versions of the wordmark and circular
headshot crops so they drop cleanly onto white or cream paper. Outputs land in
assets/letterhead/ and are regenerated on demand (idempotent).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "letterhead"

# Colors sampled from the master logo so every rule and label matches the mark.
INK = (6, 8, 8)  # MCTV wordmark black
STEEL = (72, 107, 143)  # "ELITE ADVERTISING" blue
NAVY = (27, 31, 59)  # brand navy
GOLD = (197, 165, 90)  # brand gold


def _trim_to_ink(img: Image.Image, tolerance: int = 245) -> Image.Image:
    """Drop the white field around the wordmark and return a tight RGBA crop."""
    rgb = img.convert("RGB")
    alpha = rgb.convert("L").point(lambda v: 0 if v >= tolerance else 255)
    out = rgb.convert("RGBA")
    out.putalpha(_soft_alpha(rgb, tolerance))
    box = alpha.getbbox()
    return out.crop(box) if box else out


def _soft_alpha(rgb: Image.Image, tolerance: int) -> Image.Image:
    """Alpha channel that keeps anti-aliased letter edges instead of hard-cutting."""
    luma = rgb.convert("L")
    # White (255) -> transparent, ink -> opaque, with a smooth ramp between.
    return luma.point(lambda v: 0 if v >= tolerance else int(255 * (tolerance - v) / tolerance * 1.6 + 0.5) if v > tolerance - 60 else 255)


def build_wordmark_dark() -> Path:
    """Transparent wordmark for cream/white paper, with MCTV set in brand navy."""
    src = Image.open(ROOT / "assets" / "branding" / "mctv_logo.png")
    mark = _trim_to_ink(src)

    # Recolor the near-black letterforms to brand navy; leave the steel-blue
    # subtitle alone so the mark still reads exactly like the logo file.
    pixels = mark.load()
    width, height = mark.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if abs(r - g) < 24 and abs(g - b) < 24 and r < 150:
                shade = r / 150.0
                pixels[x, y] = (
                    int(NAVY[0] + (120 - NAVY[0]) * shade),
                    int(NAVY[1] + (124 - NAVY[1]) * shade),
                    int(NAVY[2] + (150 - NAVY[2]) * shade),
                    a,
                )

    path = OUT_DIR / "wordmark_navy.png"
    mark.save(path, optimize=True)
    return path


def build_wordmark_light() -> Path:
    """Reversed-out wordmark for the navy masthead."""
    src = Image.open(ROOT / "assets" / "branding" / "mctv_logo_white.png").convert("RGBA")
    path = OUT_DIR / "wordmark_white.png"
    src.save(path, optimize=True)
    return path


def build_headshot(name: str, source: Path, ring: tuple[int, int, int] | None = None) -> Path:
    """Circular, transparent-cornered headshot with an optional hairline ring."""
    # Matches the source headshots at 1:1 - roughly 650 DPI once placed at the
    # 0.64" the letterhead uses, so there is nothing to gain from upscaling.
    size = 400
    img = Image.open(source).convert("RGB")

    # Square center-crop, biased slightly toward the top so faces sit well.
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = max(0, int((h - side) * 0.35))
    img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)

    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    if ring:
        ring_layer = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
        ImageDraw.Draw(ring_layer).ellipse(
            (6, 6, size * 4 - 7, size * 4 - 7), outline=(*ring, 255), width=14
        )
        out.alpha_composite(ring_layer.resize((size, size), Image.LANCZOS))

    path = OUT_DIR / f"headshot_{name}.png"
    out.save(path, optimize=True)
    return path


def build_all() -> dict[str, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = {
        "wordmark_navy": build_wordmark_dark(),
        "wordmark_white": build_wordmark_light(),
    }
    team_dir = ROOT / "assets" / "team"
    for key, filename in (
        ("creed", "creed_headshot.png"),
        ("mary_michael", "mary_michael_headshot.png"),
        ("swayze", "swayze_headshot.png"),
    ):
        assets[f"headshot_{key}"] = build_headshot(key, team_dir / filename, ring=GOLD)
    return assets


if __name__ == "__main__":
    for key, path in build_all().items():
        print(f"{key:22} {path.relative_to(ROOT)}")
