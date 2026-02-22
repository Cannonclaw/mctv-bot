"""Word document builder with MCTV Elite Advertising branding."""

from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
import subprocess
import shutil


# MCTV Brand Colors
NAVY = RGBColor(0x1B, 0x1F, 0x3B)
GOLD = RGBColor(0xC5, 0xA5, 0x5A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x80, 0x80, 0x80)
LIGHT_GRAY = RGBColor(0xF5, 0xF5, 0xF5)
DARK_TEXT = RGBColor(0x33, 0x33, 0x33)

OUTPUT_DIR = Path(__file__).parent.parent / "output"
PROJECT_ROOT = Path(__file__).parent.parent


class DocxService:
    """Creates branded MCTV Word documents."""

    def __init__(self, config: dict):
        self.config = config
        self.company = config["company"]

    def create_document(self) -> Document:
        """Create a new document with MCTV default styles."""
        doc = Document()

        # Set default font
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Calibri"
        font.size = Pt(11)
        font.color.rgb = DARK_TEXT

        # Set narrow margins
        for section in doc.sections:
            section.top_margin = Cm(2.0)
            section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        return doc

    def add_cover_page(self, doc: Document, title: str, subtitle: str,
                       prepared_for: str, prepared_by: dict, date: str = None,
                       client_logo_path: str = None):
        """Add a branded cover page with optional MCTV logo and client logo."""
        if date is None:
            date = datetime.now().strftime("%B %Y")

        # MCTV Logo (if it exists)
        mctv_logo = PROJECT_ROOT / "assets" / "branding" / "mctv_logo.png"
        if mctv_logo.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(str(mctv_logo), width=Inches(2.5))
        else:
            # Fallback: text header
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("MCTV ELITE ADVERTISING")
            run.font.size = Pt(14)
            run.font.color.rgb = GOLD
            run.font.bold = True
            run.font.name = "Calibri"

        # Spacer
        for _ in range(3):
            doc.add_paragraph()

        # Client logo (if provided)
        if client_logo_path:
            logo_path = Path(client_logo_path)
            if logo_path.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(str(logo_path), width=Inches(2.0))
                doc.add_paragraph()  # spacer after logo

        # Spacer
        for _ in range(2):
            doc.add_paragraph()

        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title)
        run.font.size = Pt(36)
        run.font.color.rgb = NAVY
        run.font.bold = True

        # Subtitle
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(subtitle)
        run.font.size = Pt(16)
        run.font.color.rgb = GOLD

        # Date
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(date)
        run.font.size = Pt(12)
        run.font.color.rgb = GRAY

        # Spacer
        for _ in range(4):
            doc.add_paragraph()

        # Prepared by box
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{prepared_by['name']}  |  MCTV Elite Advertising")
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = DARK_TEXT

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{prepared_by['email']}  |  {prepared_by['phone']}")
        run.font.size = Pt(10)
        run.font.color.rgb = GRAY

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Prepared for {prepared_for}")
        run.font.size = Pt(10)
        run.font.color.rgb = GOLD
        run.font.italic = True

        doc.add_page_break()

    def add_section_header(self, doc: Document, text: str):
        """Add a styled section header with navy background appearance."""
        p = doc.add_paragraph()
        p.space_before = Pt(6)
        p.space_after = Pt(12)
        run = p.add_run(text.upper())
        run.font.size = Pt(20)
        run.font.color.rgb = NAVY
        run.font.bold = True
        run.font.name = "Calibri"

        # Add a thin gold line under the header
        p = doc.add_paragraph()
        p.space_before = Pt(0)
        p.space_after = Pt(12)
        run = p.add_run("_" * 60)
        run.font.color.rgb = GOLD
        run.font.size = Pt(6)

    def add_sub_header(self, doc: Document, text: str):
        """Add a bold sub-header."""
        p = doc.add_paragraph()
        p.space_before = Pt(12)
        p.space_after = Pt(4)
        run = p.add_run(text)
        run.font.size = Pt(13)
        run.font.color.rgb = NAVY
        run.font.bold = True

    def add_body_text(self, doc: Document, text: str):
        """Add body paragraphs with proper spacing."""
        paragraphs = text.strip().split("\n\n")
        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue
            p = doc.add_paragraph()
            p.space_after = Pt(8)
            run = p.add_run(para_text)
            run.font.size = Pt(11)
            run.font.color.rgb = DARK_TEXT
            run.font.name = "Calibri"

    def add_bullet_point(self, doc: Document, title: str, description: str):
        """Add a bullet point with bold title and description."""
        p = doc.add_paragraph()
        p.space_after = Pt(6)

        run = p.add_run(f"{title}: ")
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = NAVY

        run = p.add_run(description)
        run.font.size = Pt(11)
        run.font.color.rgb = DARK_TEXT

    def add_metrics_banner(self, doc: Document, metrics: dict):
        """Add a row of big metrics (e.g., 125+ Screens, 1.9M+ Impressions)."""
        table = doc.add_table(rows=2, cols=len(metrics))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, (value, label) in enumerate(metrics.items()):
            # Value row
            cell = table.rows[0].cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(value))
            run.font.size = Pt(24)
            run.font.bold = True
            run.font.color.rgb = GOLD

            # Label row
            cell = table.rows[1].cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(label)
            run.font.size = Pt(9)
            run.font.color.rgb = GRAY

        # Remove borders
        self._remove_table_borders(table)
        doc.add_paragraph()

    def add_pricing_table(self, doc: Document, tiers: list):
        """Add a formatted pricing comparison table."""
        table = doc.add_table(rows=1 + len(tiers), cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header row
        headers = ["Monthly Rate", "Screens", "Ad Plays/Mo", "Cost/Screen"]
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(header)
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = WHITE
            # Navy background
            shading = cell._element.get_or_add_tcPr()
            shading_elm = shading.makeelement(qn("w:shd"), {
                qn("w:fill"): "1B1F3B",
                qn("w:val"): "clear",
            })
            shading.append(shading_elm)

        # Data rows
        for row_idx, tier in enumerate(tiers):
            row = table.rows[row_idx + 1]
            values = [
                f"${tier['monthly_rate']:,}/mo",
                f"{tier['screens']} Screens",
                tier.get("plays_per_month", ""),
                f"${tier.get('cost_per_screen', 0):.2f}",
            ]
            for col_idx, value in enumerate(values):
                cell = row.cells[col_idx]
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(str(value))
                run.font.size = Pt(11)
                if col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = GOLD
                    run.font.size = Pt(14)

                # Alternating row color
                if row_idx % 2 == 0:
                    shading = cell._element.get_or_add_tcPr()
                    shading_elm = shading.makeelement(qn("w:shd"), {
                        qn("w:fill"): "F5F5F5",
                        qn("w:val"): "clear",
                    })
                    shading.append(shading_elm)

        doc.add_paragraph()

    def add_contract_terms(self, doc: Document, config: dict):
        """Add partnership terms section with 6-month and 12-month boxes."""
        terms = config["pricing"]["contract_terms"]
        table = doc.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, months in enumerate(terms["standard_months"]):
            cell = table.rows[0].cells[i]
            bonus = terms[f"prepay_{months}mo_bonus"]

            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"{months}-MONTH AGREEMENT")
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = GOLD

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            label = "Minimum commitment" if months == 6 else "Best value \u2014 lock in your rate"
            run = p.add_run(label)
            run.font.size = Pt(9)
            run.font.color.rgb = GRAY

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"PREPAY BONUS: {bonus}")
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = NAVY

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("1 extra month free when you pay upfront")
            run.font.size = Pt(9)
            run.font.color.rgb = GRAY

        self._remove_table_borders(table)
        doc.add_paragraph()

    def add_data_table(self, doc: Document, headers: list, rows: list):
        """Add a data table for traction reports."""
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header row
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(header)
            run.font.size = Pt(9)
            run.font.bold = True
            run.font.color.rgb = WHITE
            shading = cell._element.get_or_add_tcPr()
            shading_elm = shading.makeelement(qn("w:shd"), {
                qn("w:fill"): "1B1F3B",
                qn("w:val"): "clear",
            })
            shading.append(shading_elm)

        # Data rows
        for row_idx, row_data in enumerate(rows):
            row = table.rows[row_idx + 1]
            for col_idx, value in enumerate(row_data):
                cell = row.cells[col_idx]
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(str(value))
                run.font.size = Pt(9)
                run.font.color.rgb = DARK_TEXT

                if row_idx % 2 == 0:
                    shading = cell._element.get_or_add_tcPr()
                    shading_elm = shading.makeelement(qn("w:shd"), {
                        qn("w:fill"): "F5F5F5",
                        qn("w:val"): "clear",
                    })
                    shading.append(shading_elm)

        doc.add_paragraph()

    def add_team_section(self, doc: Document):
        """Add the Meet Your Team section with photos."""
        self.add_section_header(doc, "Meet Your Team")

        team = self.config["team"]
        table = doc.add_table(rows=1, cols=len(team))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, member in enumerate(team):
            cell = table.rows[0].cells[i]

            # Team photo
            photo_path = member.get("photo", "")
            if photo_path:
                full_path = PROJECT_ROOT / photo_path
                if full_path.exists():
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(str(full_path), width=Inches(1.5))
                    # Name goes in next paragraph
                    p = cell.add_paragraph()
                else:
                    p = cell.paragraphs[0]
            else:
                p = cell.paragraphs[0]

            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(member["name"])
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = NAVY

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(member["title"])
            run.font.size = Pt(10)
            run.font.color.rgb = GOLD
            run.font.italic = True

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(member["phone"])
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(member["email"])
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY

        self._remove_table_borders(table)

    def add_venue_categories(self, doc: Document):
        """Add the 'Where Your Ads Play' venue category grid."""
        categories = {
            "Restaurants & Bars": "55+ min meals \u2014 your brand plays repeatedly to a captive audience.",
            "Barbershops & Salons": "15-45 min dwell. Personal care clients are homeowners and decision-makers.",
            "Medical & Dental": "20-60 min wait. Patients actively watching screens.",
            "Gyms & Fitness": "Active professionals with disposable income.",
            "Auto & Service Shops": "Extended waits. Vehicle owners = homeowners.",
            "Retail & Boutiques": "Local shoppers investing in homes and lifestyles.",
            "Professional Offices": "Attorneys, real estate, insurance \u2014 high income decision-makers.",
            "Community Venues": "High foot traffic reaching diverse demographics.",
        }

        table = doc.add_table(rows=len(categories) // 2, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        items = list(categories.items())
        for i in range(0, len(items), 2):
            row = table.rows[i // 2]
            for j in range(2):
                if i + j < len(items):
                    name, desc = items[i + j]
                    cell = row.cells[j]
                    p = cell.paragraphs[0]
                    run = p.add_run(name)
                    run.font.size = Pt(11)
                    run.font.bold = True
                    run.font.color.rgb = NAVY

                    p = cell.add_paragraph()
                    run = p.add_run(desc)
                    run.font.size = Pt(9)
                    run.font.color.rgb = GRAY

        self._remove_table_borders(table)
        doc.add_paragraph()

    def add_footer(self, doc: Document):
        """Add branded footer to all pages."""
        for section in doc.sections:
            footer = section.footer
            footer.is_linked_to_previous = False
            p = footer.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(
                f"MCTV Elite Advertising  |  {self.company['website']}  |  "
                f"Oxford \u2022 Starkville \u2022 Tupelo \u2022 North Mississippi"
            )
            run.font.size = Pt(8)
            run.font.color.rgb = GRAY

    def save_proposal(self, doc: Document, filename: str, also_pdf: bool = True) -> Path:
        """Save a proposal document and optionally convert to PDF. Returns docx path."""
        output_path = OUTPUT_DIR / "proposals" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        if also_pdf:
            self._convert_to_pdf(output_path)
        return output_path

    def save_report(self, doc: Document, filename: str, also_pdf: bool = True) -> Path:
        """Save a report document and optionally convert to PDF. Returns docx path."""
        output_path = OUTPUT_DIR / "reports" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        if also_pdf:
            self._convert_to_pdf(output_path)
        return output_path

    def save_email(self, content: str, filename: str) -> Path:
        """Save a cover email and return the path."""
        output_path = OUTPUT_DIR / "emails" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _remove_table_borders(self, table):
        """Remove all borders from a table (for layout tables)."""
        for row in table.rows:
            for cell in row.cells:
                tc_pr = cell._element.get_or_add_tcPr()
                borders = tc_pr.makeelement(qn("w:tcBorders"), {})
                for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                    border = borders.makeelement(qn(f"w:{edge}"), {
                        qn("w:val"): "none",
                        qn("w:sz"): "0",
                        qn("w:space"): "0",
                        qn("w:color"): "auto",
                    })
                    borders.append(border)
                tc_pr.append(borders)

    @staticmethod
    def _convert_to_pdf(docx_path: Path) -> Path | None:
        """Convert .docx to PDF. Tries LibreOffice (Linux cloud) then docx2pdf (Windows).
        Returns the PDF path on success, or None if conversion is unavailable."""
        pdf_path = docx_path.with_suffix(".pdf")

        # Method 1: LibreOffice headless (works on Linux cloud servers)
        try:
            libreoffice_cmd = shutil.which("libreoffice") or shutil.which("soffice")
            if libreoffice_cmd:
                subprocess.run(
                    [libreoffice_cmd, "--headless", "--convert-to", "pdf",
                     "--outdir", str(docx_path.parent), str(docx_path)],
                    capture_output=True, timeout=60,
                )
                if pdf_path.exists():
                    return pdf_path
        except Exception:
            pass

        # Method 2: docx2pdf (requires Microsoft Word on Windows)
        try:
            from docx2pdf import convert
            convert(str(docx_path), str(pdf_path))
            if pdf_path.exists():
                return pdf_path
        except Exception:
            pass

        return None

    @staticmethod
    def get_pdf_path(docx_path: Path) -> Path | None:
        """Check if a PDF version exists for a given docx file."""
        pdf_path = docx_path.with_suffix(".pdf")
        return pdf_path if pdf_path.exists() else None
