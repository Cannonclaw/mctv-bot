# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Rendering primitives for full-screen network frames.

Layout helpers shared by anything that draws a 1920x1080 spot: font
resolution, text that fits the box it is given, and rules. Kept free of any
particular frame's content so the same primitives can back a City PSA, a host
promo, or a house ad.

Type is set in Liberation Sans, which is metric-compatible with Arial (the MCTV
brand font) and is what Linux render hosts actually have. Anything laid out here
will re-flow identically if rebuilt against real Arial.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS = (1920, 1080)

_FONT_DIR = Path("/usr/share/fonts/truetype/liberation")
_FONT_FILES = {
    "regular": "LiberationSans-Regular.ttf",
    "bold": "LiberationSans-Bold.ttf",
    "italic": "LiberationSans-Italic.ttf",
}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a brand-metric font at a pixel size."""
    path = _FONT_DIR / _FONT_FILES[weight]
    if not path.exists():
        raise SystemExit(
            f"Missing font {path}. Install fonts-liberation, or point _FONT_DIR "
            "at a directory holding Arial."
        )
    return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str,
              fnt: ImageFont.FreeTypeFont, tracking: int = 0) -> tuple[int, int]:
    """Rendered (width, height) of a single line, including any tracking."""
    if not text:
        return (0, 0)
    box = draw.textbbox((0, 0), text, font=fnt)
    width = box[2] - box[0]
    if tracking:
        width += tracking * (len(text) - 1)
    return (width, box[3] - box[1])


def draw_tracked(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
                 fnt: ImageFont.FreeTypeFont, fill, tracking: int = 0,
                 anchor_left_baseline_top: bool = True) -> int:
    """Draw text with optional letter-spacing. Returns the width drawn.

    Pillow has no tracking, so wide-set small caps (the eyebrow line on an
    alert frame) have to be stepped glyph by glyph.
    """
    if not tracking:
        draw.text(xy, text, font=fnt, fill=fill)
        return text_size(draw, text, fnt)[0]

    x, y = xy
    start = x
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return int(x - start - tracking)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont,
         max_width: int) -> list[str]:
    """Greedy word wrap to a pixel width."""
    if not text:
        return []
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


@dataclass
class FittedText:
    """A block of text sized to fill its box without overflowing it."""
    lines: list[str]
    fnt: ImageFont.FreeTypeFont
    line_height: int
    height: int


def fit_block(draw: ImageDraw.ImageDraw, text: str, weight: str,
              max_width: int, max_height: int, max_size: int,
              min_size: int = 24, line_spacing: float = 1.06,
              max_lines: int | None = None) -> FittedText:
    """Largest size at which `text` wraps inside (max_width, max_height).

    Steps down from max_size rather than solving analytically — wrapping is
    discontinuous in font size, so a computed size can still overflow.
    """
    size = max_size
    while size >= min_size:
        fnt = font(weight, size)
        lines = wrap(draw, text, fnt, max_width)
        line_height = int(size * line_spacing)
        height = line_height * len(lines)
        fits_lines = max_lines is None or len(lines) <= max_lines
        if height <= max_height and fits_lines:
            return FittedText(lines, fnt, line_height, height)
        size -= 2

    fnt = font(weight, min_size)
    lines = wrap(draw, text, fnt, max_width)
    line_height = int(min_size * line_spacing)
    return FittedText(lines, fnt, line_height, line_height * len(lines))


def draw_block(draw: ImageDraw.ImageDraw, block: FittedText, x: int, y: int,
               fill, center_width: int | None = None) -> int:
    """Draw a fitted block. Returns the y just past the last line."""
    for i, line in enumerate(block.lines):
        line_x = x
        if center_width is not None:
            line_x = x + (center_width - int(draw.textlength(line, font=block.fnt))) // 2
        draw.text((line_x, y + i * block.line_height), line, font=block.fnt, fill=fill)
    return y + block.height


def rule(draw: ImageDraw.ImageDraw, x: int, y: int, width: int,
         thickness: int, fill) -> int:
    """Horizontal rule. Returns the y just past it."""
    draw.rectangle([x, y, x + width, y + thickness], fill=fill)
    return y + thickness


def new_canvas(bg) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", CANVAS, bg)
    return img, ImageDraw.Draw(img)


def contact_sheet(paths: list[Path], out_path: Path, cols: int = 2,
                  thumb_width: int = 900, pad: int = 28,
                  bg=(24, 24, 28)) -> Path:
    """Tile rendered frames into one reviewable image."""
    if not paths:
        raise ValueError("contact_sheet needs at least one frame")

    thumbs = []
    for p in paths:
        im = Image.open(p)
        scale = thumb_width / im.width
        thumbs.append(im.resize((thumb_width, int(im.height * scale)), Image.LANCZOS))

    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(t.height for t in thumbs)
    sheet = Image.new(
        "RGB",
        (cols * thumb_width + pad * (cols + 1), rows * cell_h + pad * (rows + 1)),
        bg,
    )
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (thumb_width + pad), pad + r * (cell_h + pad)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path
