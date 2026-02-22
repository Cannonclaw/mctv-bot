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
            section.top_margin = Cm(1.8)
            section.bottom_margin = Cm(1.8)
            section.left_margin = Cm(2.3)
            section.right_margin = Cm(2.3)

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
            p.space_after = Pt(6)
            run = p.add_run()
            run.add_picture(str(mctv_logo), width=Inches(2.5))
        else:
            # Fallback: text header
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_after = Pt(6)
            run = p.add_run("MCTV ELITE ADVERTISING")
            run.font.size = Pt(14)
            run.font.color.rgb = GOLD
            run.font.bold = True
            run.font.name = "Calibri"

        # Client logo (if provided)
        if client_logo_path:
            logo_path = Path(client_logo_path)
            if logo_path.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.space_before = Pt(12)
                p.space_after = Pt(12)
                run = p.add_run()
                run.add_picture(str(logo_path), width=Inches(2.0))

        # Title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.space_before = Pt(24)
        p.space_after = Pt(4)
        run = p.add_run(title)
        run.font.size = Pt(36)
        run.font.color.rgb = NAVY
        run.font.bold = True

        # Subtitle
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.space_after = Pt(16)
        run = p.add_run(subtitle)
        run.font.size = Pt(16)
        run.font.color.rgb = GOLD

        # Date
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.space_after = Pt(24)
        run = p.add_run(date)
        run.font.size = Pt(12)
        run.font.color.rgb = GRAY

        # Prepared for (the client)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.space_after = Pt(16)
        run = p.add_run(f"Prepared for {prepared_for}")
        run.font.size = Pt(13)
        run.font.color.rgb = NAVY
        run.font.italic = True

        # Prepared by box
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.space_after = Pt(2)
        run = p.add_run(f"{prepared_by['name']}  |  MCTV Elite Advertising")
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = DARK_TEXT

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{prepared_by['email']}  |  {prepared_by['phone']}")
        run.font.size = Pt(9)
        run.font.color.rgb = GRAY

        doc.add_page_break()

    def add_section_header(self, doc: Document, text: str):
        """Add a styled section header with gold accent bar underneath."""
        p = doc.add_paragraph()
        p.space_before = Pt(2)
        p.space_after = Pt(1)
        run = p.add_run(text.upper())
        run.font.size = Pt(20)
        run.font.color.rgb = NAVY
        run.font.bold = True
        run.font.name = "Calibri"

        # Gold accent bar using a 1-row, 1-col table with gold background
        bar = doc.add_table(rows=1, cols=1)
        bar.alignment = WD_TABLE_ALIGNMENT.LEFT
        cell = bar.rows[0].cells[0]
        cell.height = Cm(0.15)
        # Set gold background
        tc_pr = cell._element.get_or_add_tcPr()
        shd = tc_pr.makeelement(qn("w:shd"), {
            qn("w:fill"): "C5A55A",
            qn("w:val"): "clear",
        })
        tc_pr.append(shd)
        # Set cell width to about 1/3 of page
        cell.width = Cm(6)
        p = cell.paragraphs[0]
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        run = p.add_run()
        run.font.size = Pt(2)
        self._remove_table_borders(bar)

        # Spacer after the bar
        spacer = doc.add_paragraph()
        spacer.space_before = Pt(0)
        spacer.space_after = Pt(4)

    def add_sub_header(self, doc: Document, text: str):
        """Add a bold sub-header with gold left accent."""
        p = doc.add_paragraph()
        p.space_before = Pt(8)
        p.space_after = Pt(2)
        run = p.add_run(f"\u275A  {text}")
        run.font.size = Pt(13)
        run.font.color.rgb = NAVY
        run.font.bold = True

    def add_callout_box(self, doc: Document, text: str, bg_color: str = "F0EDE4"):
        """Add a colored callout/highlight box for key information."""
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.rows[0].cells[0]

        # Set background color
        tc_pr = cell._element.get_or_add_tcPr()
        shd = tc_pr.makeelement(qn("w:shd"), {
            qn("w:fill"): bg_color,
            qn("w:val"): "clear",
        })
        tc_pr.append(shd)

        # Add padding via paragraph formatting
        p = cell.paragraphs[0]
        p.space_before = Pt(6)
        p.space_after = Pt(6)
        run = p.add_run(text)
        run.font.size = Pt(11)
        run.font.color.rgb = DARK_TEXT
        run.font.name = "Calibri"

        self._remove_table_borders(table)

    def add_body_text(self, doc: Document, text: str):
        """Add body paragraphs with proper spacing.

        Automatically detects numbered items (e.g., '1. Bold Title\\nBody text')
        and formats them with a bold navy title and normal body text.
        """
        import re
        paragraphs = text.strip().split("\n\n")
        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue

            # Detect numbered item: "1. Title\nBody..." or "1. Title: Body..."
            numbered = re.match(r"^(\d+)\.\s+(.+?)(?:\n(.+))?$", para_text, re.DOTALL)
            if numbered:
                num = numbered.group(1)
                first_line = numbered.group(2).strip()
                rest = (numbered.group(3) or "").strip()

                # Check if the first line has a title and inline body (split by newline)
                p = doc.add_paragraph()
                p.space_before = Pt(8)
                p.space_after = Pt(6)

                # Bold numbered title
                run = p.add_run(f"{num}. {first_line}")
                run.font.size = Pt(11)
                run.font.bold = True
                run.font.color.rgb = NAVY
                run.font.name = "Calibri"

                # Body text below the title
                if rest:
                    p = doc.add_paragraph()
                    p.space_after = Pt(8)
                    run = p.add_run(rest)
                    run.font.size = Pt(11)
                    run.font.color.rgb = DARK_TEXT
                    run.font.name = "Calibri"
            else:
                p = doc.add_paragraph()
                p.space_after = Pt(8)
                run = p.add_run(para_text)
                run.font.size = Pt(11)
                run.font.color.rgb = DARK_TEXT
                run.font.name = "Calibri"

    def add_bullet_point(self, doc: Document, title: str, description: str):
        """Add a bullet point with bold title and description."""
        p = doc.add_paragraph()
        p.space_after = Pt(3)

        run = p.add_run(f"{title}: ")
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = NAVY

        run = p.add_run(description)
        run.font.size = Pt(11)
        run.font.color.rgb = DARK_TEXT

    def add_bullet_list(self, doc: Document, text: str):
        """Parse dash-prefixed bullet items from Claude and render with bold navy titles.

        Expected format: '- Bold Title: Description sentence.'
        Falls back to add_body_text for non-matching lines.
        """
        import re
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match "- Title: Description" or "- Title -- Description"
            bullet_match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if bullet_match:
                title = bullet_match.group(1).strip()
                desc = bullet_match.group(2).strip()
                self.add_bullet_point(doc, title, desc)
            else:
                # Fallback: treat as regular body text
                self.add_body_text(doc, line)

    def add_inline_photos(self, doc: Document, photo_paths: list,
                          max_width: float = 2.5, cols: int = 2):
        """Add 1-2 photos inline within a section (no title, tight spacing).

        Single photo: centered at 4.0 inches.
        Multiple photos: side-by-side in a borderless table.
        """
        photo_paths = [p for p in (photo_paths or []) if Path(p).exists()]
        if not photo_paths:
            return

        # Single photo: center it larger
        if len(photo_paths) == 1:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_before = Pt(8)
            p.space_after = Pt(8)
            try:
                run = p.add_run()
                run.add_picture(photo_paths[0], width=Inches(4.0))
            except Exception:
                pass
            return

        # Multiple photos: grid layout
        table = doc.add_table(rows=1, cols=min(len(photo_paths), cols))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, photo_path in enumerate(photo_paths[:cols]):
            cell = table.rows[0].cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_before = Pt(6)
            p.space_after = Pt(6)
            try:
                run = p.add_run()
                run.add_picture(photo_path, width=Inches(max_width))
            except Exception:
                run = p.add_run("[Image]")
                run.font.size = Pt(9)
                run.font.color.rgb = GRAY

        self._remove_table_borders(table)

    def add_photos_grid(self, doc: Document, photo_paths: list, title: str = None,
                        max_width: float = 3.0, cols: int = 2):
        """Add a grid of photos to the document.

        Args:
            photo_paths: List of file paths to images.
            title: Optional sub-header above the photos.
            max_width: Max width per image in inches.
            cols: Number of columns in the grid.
        """
        # Filter to only paths that actually exist on disk
        photo_paths = [p for p in (photo_paths or []) if Path(p).exists()]
        if not photo_paths:
            return

        if title:
            self.add_sub_header(doc, title)

        # Build table grid for photos
        rows_needed = (len(photo_paths) + cols - 1) // cols
        table = doc.add_table(rows=rows_needed, cols=cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, photo_path in enumerate(photo_paths):
            row_idx = i // cols
            col_idx = i % cols
            cell = table.rows[row_idx].cells[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                run = p.add_run()
                run.add_picture(photo_path, width=Inches(max_width))
            except Exception:
                run = p.add_run("[Image could not be loaded]")
                run.font.size = Pt(9)
                run.font.color.rgb = GRAY

        self._remove_table_borders(table)

    def add_metrics_banner(self, doc: Document, metrics: dict):
        """Add a row of big metrics with navy background (e.g., 125+ Screens)."""
        table = doc.add_table(rows=2, cols=len(metrics))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, (value, label) in enumerate(metrics.items()):
            # Value row — navy background, gold text
            cell = table.rows[0].cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            tc_pr = cell._element.get_or_add_tcPr()
            shd = tc_pr.makeelement(qn("w:shd"), {
                qn("w:fill"): "1B1F3B",
                qn("w:val"): "clear",
            })
            tc_pr.append(shd)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_before = Pt(8)
            p.space_after = Pt(4)
            run = p.add_run(str(value))
            run.font.size = Pt(24)
            run.font.bold = True
            run.font.color.rgb = GOLD

            # Label row — navy background, white text
            cell = table.rows[1].cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            tc_pr = cell._element.get_or_add_tcPr()
            shd = tc_pr.makeelement(qn("w:shd"), {
                qn("w:fill"): "1B1F3B",
                qn("w:val"): "clear",
            })
            tc_pr.append(shd)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_before = Pt(0)
            p.space_after = Pt(8)
            run = p.add_run(label)
            run.font.size = Pt(9)
            run.font.color.rgb = WHITE

        # Remove borders
        self._remove_table_borders(table)

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
            rate = tier['monthly_rate']
            rate_str = f"${rate:,.0f}" if rate == int(rate) else f"${rate:,.2f}"
            cps = tier.get('cost_per_screen', 0)
            cps_str = f"${cps:,.0f}" if cps == int(cps) else f"${cps:,.2f}"
            values = [
                f"{rate_str}/mo",
                f"{tier['screens']} Screens",
                tier.get("plays_per_month", ""),
                cps_str,
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
        """Add the 'Where Your Ads Play' venue category grid — ultra-compact 2-row format."""
        categories = [
            "Restaurants & Bars", "Barbershops & Salons",
            "Medical & Dental", "Gyms & Fitness",
            "Auto & Service Shops", "Retail & Boutiques",
            "Professional Offices", "Community Venues",
        ]

        # 2 rows x 4 columns for maximum compactness
        table = doc.add_table(rows=2, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, name in enumerate(categories):
            row_idx = i // 4
            col_idx = i % 4
            cell = table.rows[row_idx].cells[col_idx]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.space_before = Pt(4)
            p.space_after = Pt(4)
            run = p.add_run(name)
            run.font.size = Pt(9)
            run.font.bold = True
            run.font.color.rgb = NAVY

        self._remove_table_borders(table)

    def add_footer(self, doc: Document):
        """Add branded footer with page numbers to all pages."""
        for section in doc.sections:
            footer = section.footer
            footer.is_linked_to_previous = False
            p = footer.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Footer text
            run = p.add_run(
                f"MCTV Elite Advertising  |  {self.company['website']}  |  "
                f"Oxford \u2022 Starkville \u2022 Tupelo \u2022 North Mississippi"
                f"          "
            )
            run.font.size = Pt(8)
            run.font.color.rgb = GRAY

            # Page number field
            run = p.add_run()
            fld_char_begin = run._element.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "begin"})
            run._element.append(fld_char_begin)

            run2 = p.add_run()
            instr = run2._element.makeelement(qn("w:instrText"), {})
            instr.text = " PAGE "
            run2._element.append(instr)
            run2.font.size = Pt(8)
            run2.font.color.rgb = GRAY

            run3 = p.add_run()
            fld_char_end = run3._element.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): "end"})
            run3._element.append(fld_char_end)

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
