"""PDF conversion utility for MCTV Bot.

Converts .docx files to PDF using either:
  1. LibreOffice CLI (soffice --headless) — best quality, preserves formatting
  2. docx2pdf library (uses MS Word COM automation on Windows)

Falls back gracefully if neither is available.
"""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_libreoffice() -> str | None:
    """Find the LibreOffice soffice executable on the system."""
    # Check PATH first
    soffice = shutil.which("soffice")
    if soffice:
        return soffice

    # Common Windows install paths
    common_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for path in common_paths:
        if Path(path).exists():
            return path

    return None


def convert_docx_to_pdf(docx_path: Path) -> Path | None:
    """Convert a .docx file to PDF.

    Tries LibreOffice first, then docx2pdf, then returns None if neither works.

    Returns:
        Path to the generated PDF file, or None if conversion failed.
    """
    docx_path = Path(docx_path)
    if not docx_path.exists():
        logger.error("DOCX file not found: %s", docx_path)
        return None

    pdf_path = docx_path.with_suffix(".pdf")

    # Method 1: LibreOffice CLI
    soffice = _find_libreoffice()
    if soffice:
        try:
            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(docx_path.parent),
                    str(docx_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and pdf_path.exists():
                logger.info("PDF created via LibreOffice: %s", pdf_path.name)
                return pdf_path
            else:
                logger.warning(
                    "LibreOffice conversion returned %d: %s",
                    result.returncode, result.stderr[:200]
                )
        except subprocess.TimeoutExpired:
            logger.warning("LibreOffice conversion timed out")
        except Exception as e:
            logger.warning("LibreOffice conversion failed: %s", e)

    # Method 2: docx2pdf (Windows-only, uses MS Word)
    try:
        from docx2pdf import convert
        convert(str(docx_path), str(pdf_path))
        if pdf_path.exists():
            logger.info("PDF created via docx2pdf: %s", pdf_path.name)
            return pdf_path
    except ImportError:
        logger.debug("docx2pdf not installed")
    except Exception as e:
        logger.warning("docx2pdf conversion failed: %s", e)

    logger.error(
        "PDF conversion not available. Install LibreOffice or docx2pdf. "
        "LibreOffice: https://www.libreoffice.org/download/"
    )
    return None


def is_pdf_available() -> bool:
    """Check if PDF conversion is possible on this system."""
    if _find_libreoffice():
        return True
    try:
        import docx2pdf  # noqa: F401
        return True
    except ImportError:
        pass
    return False
