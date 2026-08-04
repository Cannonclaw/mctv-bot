# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Convert press PDFs from RGB to DeviceCMYK for the printer.

Chromium only emits RGB, so the press PDFs come out of the packet
generators in RGB. Commercial printers usually want DeviceCMYK. This
runs the conversion through Ghostscript with settings chosen for offset
work, then verifies the result rather than trusting it:

  * every colour goes through the profile once, with Ghostscript's
    black-preservation flags OFF -- see the comment in convert() for why
  * no image downsampling, fonts stay embedded, page geometry (media box
    including bleed and crop marks) is preserved
  * the converted page is rendered back and the brand colours are compared
    against the source pixel for pixel, so "the navy survived" is measured
    rather than assumed
  * total area coverage (TAC) is measured across the page

TAC matters: a naive RGB->CMYK of a dark navy can exceed 300%% total ink,
which sheetfed presses reject. The report flags anything over the limit.

Usage:
    python scripts/convert_pdf_to_cmyk.py                    # all *_PRINT.pdf
    python scripts/convert_pdf_to_cmyk.py path/to/file.pdf
    python scripts/convert_pdf_to_cmyk.py --tac-limit 280
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "proposals"

# Brand colours as authored in RGB, for reporting the achieved CMYK
BRAND = {
    "Navy #1B1F3B": (0x1B, 0x1F, 0x3B),
    "Gold #C5A55A": (0xC5, 0xA5, 0x5A),
}

DEFAULT_TAC_LIMIT = 300.0   # typical sheetfed coated limit


def gs_bin():
    exe = shutil.which("gs")
    if not exe:
        sys.exit("Ghostscript not found. Install with: apt-get install -y ghostscript")
    return exe


def convert(src: Path, dst: Path) -> None:
    """RGB -> DeviceCMYK, preserving geometry, fonts, and brand colour."""
    cmd = [
        gs_bin(), "-dBATCH", "-dNOPAUSE", "-dSAFER", "-dQUIET",
        "-sDEVICE=pdfwrite",
        "-dPDFSETTINGS=/prepress",
        # the actual colour conversion
        "-sColorConversionStrategy=CMYK",
        "-dProcessColorModel=/DeviceCMYK",
        # -dBlackText and -dBlackVector are both deliberately OFF. They snap
        # *near*-black to K-only, not just pure black, and this design has no
        # pure black in it — body copy is #23273D and the brand navy is
        # #1B1F3B. With them on, the same navy separated two different ways:
        # C0 M0 Y0 K100 where it was text, C90 M85 Y47 K55 where it was a
        # fill, so navy headings printed black while navy bands printed navy.
        # Off, every colour goes through the profile once and stays consistent.
        # Trade-off: small type lands as a rich 4-colour dark rather than
        # 100% K, so the printer may want to apply their own black generation
        # — that is called out in the print instructions.
        # do not touch the artwork
        "-dDownsampleColorImages=false",
        "-dDownsampleGrayImages=false",
        "-dDownsampleMonoImages=false",
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        f"-sOutputFile={dst}",
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def page_geometry(pdf: Path):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    pages = size = None
    for line in out.splitlines():
        if line.startswith("Pages:"):
            pages = line.split()[-1]
        elif line.startswith("Page size:"):
            size = line.split(":", 1)[1].strip()
    return pages, size


def colorspaces(pdf: Path):
    """Which colour spaces the images in the file actually use."""
    out = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True).stdout
    spaces = {}
    for line in out.splitlines()[2:]:
        parts = line.split()
        if len(parts) > 5:
            spaces[parts[5]] = spaces.get(parts[5], 0) + 1
    return spaces


def fonts_embedded(pdf: Path):
    out = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout
    # columns are fixed-width; "CID TrueType" contains a space, so slice by
    # the header offsets rather than splitting on whitespace
    lines = [l for l in out.splitlines()[2:] if l.strip()]
    header = out.splitlines()[0]
    emb_at = header.index("emb")
    names = sorted({l[:36].strip().split("+")[-1] for l in lines})
    all_emb = all(l[emb_at:emb_at + 3].strip() == "yes" for l in lines)
    return names, all_emb


def sample_cmyk(pdf: Path, page: int = 1, dpi: int = 72):
    """Render a page to a CMYK raster and return the PIL image."""
    from PIL import Image
    tmp = pdf.with_suffix(f".cmyksample{page}.tif")
    subprocess.run([
        gs_bin(), "-dBATCH", "-dNOPAUSE", "-dSAFER", "-dQUIET",
        "-sDEVICE=tiff32nc",                 # 32-bit CMYK tiff
        f"-r{dpi}",
        f"-dFirstPage={page}", f"-dLastPage={page}",
        f"-sOutputFile={tmp}", str(pdf),
    ], check=True, capture_output=True)
    im = Image.open(tmp)
    im.load()
    tmp.unlink(missing_ok=True)
    return im


def analyse_inks(im, tac_limit):
    """Peak ink coverage and how much of the page breaches the TAC limit."""
    import collections
    px = im.convert("CMYK")
    data = list(px.getdata())  # noqa: PD011
    total = len(data)
    worst_tac = 0.0
    worst_mix = None
    over = 0
    mixes = collections.Counter()
    for c, m, y, k in data:
        tac = (c + m + y + k) / 255.0 * 100.0
        if tac > worst_tac:
            worst_tac, worst_mix = tac, (c, m, y, k)
        if tac > tac_limit:
            over += 1
        if c + m + y + k > 40:            # ignore paper white
            mixes[(c, m, y, k)] += 1
    dominant = mixes.most_common(1)[0] if mixes else (None, 0)
    return {
        "peak_tac": worst_tac,
        "peak_mix": worst_mix,
        "over_px": over,
        "over_pct": over / total * 100.0 if total else 0.0,
        "dominant_mix": dominant[0],
        "dominant_px": dominant[1],
    }


def brand_fidelity(src: Path, dst: Path, dpi: int = 110):
    """Render source and converted side by side and measure brand-colour drift.

    Guessing the navy from "most common non-white ink" is unreliable — on a
    text-heavy page the most common ink is the table rules, and on any page the
    sample is skewed by antialiased glyph edges. Comparing the same pixel
    locations before and after is the test that actually answers "did the brand
    colour survive the conversion".
    """
    from PIL import Image
    import collections

    def render(pdf, out):
        subprocess.run([
            gs_bin(), "-dBATCH", "-dNOPAUSE", "-dSAFER", "-dQUIET",
            "-sDEVICE=png16m", f"-r{dpi}", "-dFirstPage=1", "-dLastPage=1",
            f"-sOutputFile={out}", str(pdf),
        ], check=True, capture_output=True)
        im = Image.open(out)
        im.load()
        return im

    a = render(src, "/tmp/_fid_src.png")
    b = render(dst, "/tmp/_fid_dst.png")
    pa, pb = a.load(), b.load()
    w, h = a.size
    found = {k: collections.Counter() for k in BRAND}
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, bl = pa[x, y][:3]
            for name, (tr, tg, tb) in BRAND.items():
                if abs(r - tr) < 10 and abs(g - tg) < 10 and abs(bl - tb) < 10:
                    found[name][pb[x, y][:3]] += 1
                    break
    out = []
    for name, cnt in found.items():
        total = sum(cnt.values())
        if not total:
            continue
        col, _ = cnt.most_common(1)[0]
        tgt = BRAND[name]
        drift = max(abs(col[i] - tgt[i]) for i in range(3))
        # small type is mostly antialiased edge pixels, so allow more slack
        # when the colour only appears over a small area
        limit = 8 if total > 20000 else 14
        verdict = "faithful" if drift <= limit else "CHECK — shifted"
        out.append((name, drift, total, verdict))
    return out


def pct(v):
    return f"{v / 255.0 * 100.0:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*", help="PDFs to convert (default: all *_PRINT.pdf)")
    ap.add_argument("--tac-limit", type=float, default=DEFAULT_TAC_LIMIT)
    ap.add_argument("--suffix", default="_CMYK")
    args = ap.parse_args()

    targets = [Path(p) for p in args.pdfs] or sorted(OUTPUT_DIR.glob("*_PRINT.pdf"))
    if not targets:
        sys.exit("No *_PRINT.pdf files found in output/proposals/")

    print(f"Ghostscript: {subprocess.run([gs_bin(), '--version'], capture_output=True, text=True).stdout.strip()}")
    print(f"TAC limit:   {args.tac_limit:.0f}%\n")

    for src in targets:
        dst = src.with_name(src.stem + args.suffix + ".pdf")
        print("=" * 74)
        print(f"{src.name}  ->  {dst.name}")
        convert(src, dst)

        p_before, s_before = page_geometry(src)
        p_after, s_after = page_geometry(dst)
        geom_ok = (p_before == p_after) and (s_before == s_after)
        print(f"  pages/size   {p_before} @ {s_before}  ->  {p_after} @ {s_after}   "
              f"{'OK' if geom_ok else 'CHANGED — INVESTIGATE'}")

        names, emb = fonts_embedded(dst)
        print(f"  fonts        {', '.join(names) or '(none)'}   embedded={'yes' if emb else 'NO'}")

        print(f"  image spaces before={colorspaces(src)}  after={colorspaces(dst)}")

        im = sample_cmyk(dst, page=1, dpi=100)
        print(f"  raster mode  {im.mode} (expect CMYK)")
        a = analyse_inks(im, args.tac_limit)
        fmt = lambda mx: (f"C{pct(mx[0])} M{pct(mx[1])} Y{pct(mx[2])} K{pct(mx[3])}"
                          if mx else "n/a")
        print(f"  peak ink     {a['peak_tac']:.0f}% TAC ({fmt(a['peak_mix'])})   "
              f"over {args.tac_limit:.0f}%: {a['over_px']:,} px ({a['over_pct']:.3f}% of page)")
        for name, drift, area, verdict in brand_fidelity(src, dst):
            print(f"  {name:14s} drift {drift:>2} / 255 over {area:,} px   {verdict}")
        print(f"  size         {src.stat().st_size/1e6:.2f} MB -> {dst.stat().st_size/1e6:.2f} MB")

    print("=" * 74)
    print("\nNote: converted with Ghostscript's default CMYK profile (SWOP-like).")
    print("If the printer supplies their own press profile, reconvert against it")
    print("or hand them the RGB files and let them do it — their profile wins.")


if __name__ == "__main__":
    main()
