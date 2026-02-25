"""Branded contract document generator.

Produces professional MCTV advertising contracts as Word documents
with optional PDF conversion. Reuses DocxService for consistent branding.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

from services.docx_service import DocxService


# ── Config ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "config.json"
OUTPUT_DIR = ROOT / "output" / "contracts"


def _load_config() -> dict:
    """Load config.json."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Standard contract clauses ───────────────────────────────────────────────

STANDARD_CLAUSES = [
    {
        "title": "1. Services Provided",
        "body": (
            "MCTV Elite Advertising ('MCTV') agrees to display the Advertiser's "
            "digital content on the specified number of indoor digital billboard screens "
            "within the selected market(s). Content will play in rotation at a rate of "
            "4 plays per hour per screen during standard venue operating hours."
        ),
    },
    {
        "title": "2. Content Ownership",
        "body": (
            "All creative content produced by MCTV for this partnership remains the "
            "property of the Advertiser. The Advertiser may use any content created by "
            "MCTV on social media, websites, print, or any other medium at no additional "
            "cost. MCTV retains a non-exclusive right to display the content on the "
            "MCTV network for the duration of this agreement."
        ),
    },
    {
        "title": "3. Term and Renewal",
        "body": (
            "This agreement begins on the Start Date specified above and continues "
            "for the agreed term. Unless either party provides written notice of "
            "non-renewal at least 30 days before the end of the current term, this "
            "agreement will automatically renew for successive periods of equal length "
            "at the then-current rate."
        ),
    },
    {
        "title": "4. Payment Terms",
        "body": (
            "Invoices are issued monthly on the first business day of each month. "
            "Payment is due within 30 days of the invoice date. MCTV reserves the "
            "right to suspend ad display for accounts more than 45 days past due. "
            "A late fee of 1.5% per month may be applied to overdue balances."
        ),
    },
    {
        "title": "5. Content Guidelines",
        "body": (
            "All content must comply with applicable local, state, and federal laws. "
            "MCTV reserves the right to refuse or remove content that is offensive, "
            "misleading, or inappropriate for the venue environments in which screens "
            "are placed. The Advertiser will be notified promptly if any content is "
            "declined and given the opportunity to submit revised creative."
        ),
    },
    {
        "title": "6. Cancellation",
        "body": (
            "Either party may cancel this agreement with 60 days written notice. "
            "If the Advertiser cancels before the end of the agreed term, any prepay "
            "bonuses or discounts already applied will be prorated and billed. "
            "MCTV will make reasonable efforts to wind down ad display gracefully."
        ),
    },
    {
        "title": "7. Liability Limitation",
        "body": (
            "MCTV's total liability under this agreement shall not exceed the total "
            "fees paid by the Advertiser in the 12 months preceding the claim. "
            "MCTV shall not be liable for incidental, consequential, or indirect "
            "damages. MCTV makes no guarantee of specific business results from "
            "advertising display."
        ),
    },
    {
        "title": "8. Governing Law",
        "body": (
            "This agreement shall be governed by and construed in accordance with "
            "the laws of the State of Mississippi. Any disputes arising under this "
            "agreement shall be resolved in the courts of Hinds County, Mississippi."
        ),
    },
]


HOST_CLAUSES = [
    {
        "title": "1. Screen Hosting Agreement",
        "body": (
            "The Venue Host agrees to provide a suitable location for the installation "
            "and operation of MCTV indoor digital billboard screen(s). MCTV will provide, "
            "install, and maintain all hardware at no cost to the Venue Host. The screen(s) "
            "will display a mix of advertiser content and venue-specific content."
        ),
    },
    {
        "title": "2. Venue Benefits",
        "body": (
            "In exchange for hosting MCTV screen(s), the Venue Host receives complimentary "
            "advertising plays on all MCTV screens across the network. This includes free "
            "ad content creation by the MCTV creative team. Play frequency and screen count "
            "are specified in the Partnership Details section above."
        ),
    },
    {
        "title": "3. Screen Placement and Maintenance",
        "body": (
            "MCTV will work with the Venue Host to identify optimal screen placement for "
            "maximum visibility. MCTV is responsible for all hardware maintenance, repairs, "
            "and content updates. The Venue Host agrees to provide a standard electrical "
            "outlet and reliable WiFi connectivity for each screen."
        ),
    },
    {
        "title": "4. Term and Removal",
        "body": (
            "This agreement begins on the Start Date specified above and continues "
            "for the agreed term. Either party may terminate with 30 days written notice. "
            "Upon termination, MCTV will remove all hardware within 14 business days at "
            "no cost to the Venue Host."
        ),
    },
    {
        "title": "5. Content Control",
        "body": (
            "MCTV manages all content displayed on hosted screens. The Venue Host may "
            "request that specific advertiser categories be excluded from display in "
            "their venue (e.g., competitor ads). MCTV will make reasonable efforts to "
            "honor such requests. Venue Host content is subject to the same content "
            "guidelines as advertiser content."
        ),
    },
    {
        "title": "6. Liability and Insurance",
        "body": (
            "MCTV maintains liability insurance covering its equipment and operations. "
            "The Venue Host is not responsible for damage to MCTV equipment except in "
            "cases of gross negligence or intentional damage. MCTV shall not be liable "
            "for any loss of business or incidental damages arising from screen downtime."
        ),
    },
    {
        "title": "7. Governing Law",
        "body": (
            "This agreement shall be governed by and construed in accordance with "
            "the laws of the State of Mississippi. Any disputes arising under this "
            "agreement shall be resolved in the courts of Hinds County, Mississippi."
        ),
    },
]


HOST_ADVERTISING_CLAUSES = [
    {
        "title": "1. Host Advertising Partnership",
        "body": (
            "This agreement covers additional advertising screens for an existing "
            "MCTV Venue Host ('Host Advertiser'). As a current venue host, the Host "
            "Advertiser receives complimentary advertising on a specified number of "
            "screens across the MCTV network. This agreement provides advertising on "
            "additional screens beyond the complimentary allotment at a preferred "
            "discounted rate, as detailed in the Partnership Details section above."
        ),
    },
    {
        "title": "2. Complimentary Screens & Additional Screens",
        "body": (
            "The Host Advertiser's complimentary screen allotment (earned through "
            "the venue hosting agreement) remains unchanged by this agreement. The "
            "additional screens covered by this agreement are billed at the discounted "
            "monthly rate specified in the Partnership Details. The discount is applied "
            "as a courtesy to recognize the Host Advertiser's ongoing partnership with "
            "MCTV as a venue host."
        ),
    },
    {
        "title": "3. Content Ownership",
        "body": (
            "All creative content produced by MCTV for this partnership remains the "
            "property of the Host Advertiser. The Host Advertiser may use any content "
            "created by MCTV on social media, websites, print, or any other medium at "
            "no additional cost. MCTV retains a non-exclusive right to display the "
            "content on the MCTV network for the duration of this agreement."
        ),
    },
    {
        "title": "4. Term and Renewal",
        "body": (
            "This agreement begins on the Start Date specified above and continues "
            "for the agreed term. Unless either party provides written notice of "
            "non-renewal at least 30 days before the end of the current term, this "
            "agreement will automatically renew for successive periods of equal length "
            "at the then-current discounted rate."
        ),
    },
    {
        "title": "5. Payment Terms",
        "body": (
            "Invoices are issued monthly on the first business day of each month. "
            "Payment is due within 30 days of the invoice date. MCTV reserves the "
            "right to suspend additional ad display (beyond the complimentary allotment) "
            "for accounts more than 45 days past due. A late fee of 1.5% per month "
            "may be applied to overdue balances."
        ),
    },
    {
        "title": "6. Content Guidelines",
        "body": (
            "All content must comply with applicable local, state, and federal laws. "
            "MCTV reserves the right to refuse or remove content that is offensive, "
            "misleading, or inappropriate for the venue environments in which screens "
            "are placed. The Host Advertiser will be notified promptly if any content "
            "is declined and given the opportunity to submit revised creative."
        ),
    },
    {
        "title": "7. Cancellation",
        "body": (
            "Either party may cancel this agreement with 60 days written notice. "
            "Cancellation of this advertising add-on does not affect the underlying "
            "venue hosting agreement or the complimentary screen allotment. If the "
            "Host Advertiser cancels before the end of the agreed term, any prepay "
            "bonuses or discounts already applied will be prorated and billed."
        ),
    },
    {
        "title": "8. Liability Limitation",
        "body": (
            "MCTV's total liability under this agreement shall not exceed the total "
            "fees paid by the Host Advertiser in the 12 months preceding the claim. "
            "MCTV shall not be liable for incidental, consequential, or indirect "
            "damages. MCTV makes no guarantee of specific business results from "
            "advertising display."
        ),
    },
    {
        "title": "9. Governing Law",
        "body": (
            "This agreement shall be governed by and construed in accordance with "
            "the laws of the State of Mississippi. Any disputes arising under this "
            "agreement shall be resolved in the courts of Hinds County, Mississippi."
        ),
    },
]


# ── Contract Generator ──────────────────────────────────────────────────────

def _format_date(iso_date: str) -> str:
    """Convert ISO date (YYYY-MM-DD) to human-readable format (e.g., February 24, 2026)."""
    if not iso_date:
        return "TBD"
    try:
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")  # "February 04" → "February 4"
    except (ValueError, TypeError):
        return iso_date  # Return as-is if parsing fails


class ContractGenerator:
    """Generate branded MCTV contract documents."""

    def __init__(self, config: dict | None = None):
        self.config = config or _load_config()
        self.docx_service = DocxService(self.config, color_scheme="original")

    def generate(
        self,
        client_name: str,
        business_name: str,
        contract_type: str = "advertiser",
        tier_name: str = "",
        screen_count: int = 10,
        monthly_rate: float = 350.0,
        term_months: int = 6,
        markets: list[str] | None = None,
        start_date: str = "",
        auto_renew: bool = True,
        prepared_by: str = "",
        notes: str = "",
    ) -> tuple[Path, Path | None, bytes]:
        """Generate a contract document.

        Args:
            client_name: Contact person name
            business_name: Business/venue name
            contract_type: "advertiser" or "host"
            tier_name: Tier label (e.g., "20 Screens")
            screen_count: Number of screens
            monthly_rate: Monthly fee
            term_months: Contract length in months
            markets: List of market names
            start_date: Contract start date (YYYY-MM-DD), defaults to today
            auto_renew: Whether contract auto-renews
            prepared_by: Sales rep name
            notes: Additional notes/terms

        Returns:
            Tuple of (docx_path, pdf_path or None, docx_bytes).
            docx_bytes captured before PDF conversion to avoid file locking.
        """
        if not markets:
            markets = ["Oxford"]
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not tier_name:
            tier_name = f"{screen_count} Screens"

        # Calculate end date
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=term_months * 30)
        end_date = end_dt.strftime("%Y-%m-%d")

        # Find prepared_by rep info
        rep_info = self._get_rep_info(prepared_by)

        # ── Build the document ──────────────────────────────────────
        doc = self.docx_service.create_document()

        # Cover page
        contract_labels = {
            "advertiser": "Advertising Partnership Agreement",
            "host": "Venue Hosting Agreement",
            "host_advertising": "Host Advertising Agreement",
        }
        contract_label = contract_labels.get(contract_type, "Partnership Agreement")
        self.docx_service.add_cover_page(
            doc,
            title=contract_label,
            subtitle=business_name,
            prepared_for=f"{client_name}\n{business_name}",
            prepared_by=rep_info,
            date=datetime.now().strftime("%B %d, %Y"),
        )

        # Note: add_cover_page() already ends with a section break (new page),
        # so no additional page break is needed here.

        # ── Partnership Details section ─────────────────────────────
        self.docx_service.add_section_header(doc, "Partnership Details")

        if contract_type == "host_advertising":
            self._add_host_advertising_details(
                doc, business_name, client_name, tier_name, screen_count,
                monthly_rate, term_months, markets, start_date, end_date,
                auto_renew,
            )
        elif contract_type == "advertiser":
            self._add_advertiser_details(
                doc, business_name, client_name, tier_name, screen_count,
                monthly_rate, term_months, markets, start_date, end_date,
                auto_renew,
            )
        else:
            self._add_host_details(
                doc, business_name, client_name, screen_count, term_months,
                markets, start_date, end_date,
            )

        if notes:
            self.docx_service.add_body_text(doc, "")
            self.docx_service.add_callout_box(doc, f"Additional Notes: {notes}")

        # ── Terms & Conditions section ──────────────────────────────
        self.docx_service.add_section_header(doc, "Terms & Conditions", new_page=True)

        if contract_type == "host_advertising":
            clauses = HOST_ADVERTISING_CLAUSES
        elif contract_type == "advertiser":
            clauses = STANDARD_CLAUSES
        else:
            clauses = HOST_CLAUSES

        for clause in clauses:
            self.docx_service.add_sub_header(doc, clause["title"])
            self.docx_service.add_body_text(doc, clause["body"])
            self.docx_service.add_body_text(doc, "")  # spacer

        # ── Prepay bonuses (advertiser / host advertising) ────────────
        if contract_type in ("advertiser", "host_advertising"):
            pricing = self.config.get("pricing", {})
            contract_terms = pricing.get("contract_terms", {})
            bonus_6 = contract_terms.get("prepay_6mo_bonus", "")
            bonus_12 = contract_terms.get("prepay_12mo_bonus", "")

            if bonus_6 or bonus_12:
                self.docx_service.add_section_divider(doc)
                self.docx_service.add_sub_header(doc, "Prepayment Bonuses")
                if bonus_6:
                    self.docx_service.add_bullet_point(doc, "6-Month Prepay", bonus_6)
                if bonus_12:
                    self.docx_service.add_bullet_point(doc, "12-Month Prepay", bonus_12)
                self.docx_service.add_body_text(doc, "")

        # ── Signature section ───────────────────────────────────────
        self.docx_service.add_section_header(doc, "Agreement & Signature", new_page=True)
        self._add_signature_section(doc, business_name, client_name, contract_type)

        # ── Save ────────────────────────────────────────────────────
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in business_name)
        safe_name = safe_name.strip().replace(" ", "_")[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"MCTV_Contract_{safe_name}_{timestamp}.docx"

        docx_path = OUTPUT_DIR / filename
        doc.save(docx_path)

        # Read docx bytes immediately (before PDF conversion may lock the file)
        docx_bytes = docx_path.read_bytes()

        # Try PDF conversion
        pdf_path = self.docx_service._convert_to_pdf(docx_path)

        return docx_path, pdf_path, docx_bytes

    def _get_rep_info(self, rep_name: str) -> dict:
        """Get rep info from config, or return default."""
        team = self.config.get("team", [])
        for member in team:
            if rep_name and rep_name.lower() in member.get("name", "").lower():
                return member
        # Default to first team member
        if team:
            return team[0]
        return {
            "name": "MCTV Elite Advertising",
            "title": "",
            "email": "info@mctvofms.com",
            "phone": "",
        }

    def _add_advertiser_details(self, doc, business_name, client_name,
                                 tier_name, screen_count, monthly_rate,
                                 term_months, markets, start_date, end_date,
                                 auto_renew):
        """Add the advertiser partnership details table."""
        total_value = monthly_rate * term_months

        details = [
            ("Advertiser", business_name),
            ("Contact", client_name),
            ("Package", tier_name),
            ("Screen Count", str(screen_count)),
            ("Monthly Rate", f"${monthly_rate:,.2f}"),
            ("Term", f"{term_months} months"),
            ("Total Contract Value", f"${total_value:,.2f}"),
            ("Market(s)", ", ".join(markets)),
            ("Start Date", _format_date(start_date)),
            ("End Date", _format_date(end_date)),
            ("Auto-Renew", "Yes" if auto_renew else "No"),
            ("Content Creation", "Included at no additional cost"),
            ("Plays per Hour", "4 per screen"),
        ]

        self.docx_service.add_data_table(
            doc,
            headers=["Detail", "Value"],
            rows=details,
        )

    def _add_host_details(self, doc, business_name, client_name,
                           screen_count, term_months, markets,
                           start_date, end_date):
        """Add the host venue partnership details table."""
        pricing = self.config.get("pricing", {})
        free_inside = pricing.get("host_free_inside_plays_per_hour", 8)
        free_outside_plays = pricing.get("host_outside_plays_per_hour", 4)
        free_outside_screens = pricing.get("host_free_outside_screens", 10)

        details = [
            ("Venue", business_name),
            ("Contact", client_name),
            ("Screens Hosted", str(screen_count)),
            ("Term", f"{term_months} months"),
            ("Market(s)", ", ".join(markets)),
            ("Start Date", _format_date(start_date)),
            ("End Date", _format_date(end_date)),
            ("Venue Ad Plays (In-Store)", f"{free_inside} plays/hour across network"),
            ("Venue Ad Plays (Outside)", f"{free_outside_plays} plays/hour on {free_outside_screens} screens"),
            ("Content Creation", "Included at no additional cost"),
            ("Hardware & Installation", "Provided and maintained by MCTV"),
            ("Venue Cost", "$0 / Free"),
        ]

        self.docx_service.add_data_table(
            doc,
            headers=["Detail", "Value"],
            rows=details,
        )

    def _add_host_advertising_details(self, doc, business_name, client_name,
                                       tier_name, screen_count, monthly_rate,
                                       term_months, markets, start_date,
                                       end_date, auto_renew):
        """Add the host advertising partnership details table."""
        pricing = self.config.get("pricing", {})
        free_screens = pricing.get("host_free_outside_screens", 10)
        total_value = monthly_rate * term_months

        # Parse discount from tier_name (e.g., "Host Discount 10% - 10 Screens")
        discount_str = "N/A"
        standard_rate_str = ""
        if "Host Discount" in tier_name:
            import re
            match = re.search(r"(\d+)%", tier_name)
            if match:
                pct = int(match.group(1))
                discount_str = f"{pct}%"
                if pct > 0:
                    standard_rate = monthly_rate / (1 - pct / 100)
                    standard_rate_str = f"${standard_rate:,.2f}"

        details = [
            ("Host Advertiser", business_name),
            ("Contact", client_name),
            ("Complimentary Screens", f"{free_screens} (included with hosting agreement)"),
            ("Additional Paid Screens", str(screen_count)),
            ("Total Screens", str(free_screens + screen_count)),
        ]

        if standard_rate_str:
            details.append(("Standard Rate", f"{standard_rate_str}/mo"))
            details.append(("Host Discount", discount_str))
        details += [
            ("Discounted Monthly Rate", f"${monthly_rate:,.2f}"),
            ("Term", f"{term_months} months"),
            ("Total Contract Value", f"${total_value:,.2f}"),
            ("Market(s)", ", ".join(markets)),
            ("Start Date", _format_date(start_date)),
            ("End Date", _format_date(end_date)),
            ("Auto-Renew", "Yes" if auto_renew else "No"),
            ("Content Creation", "Included at no additional cost"),
            ("Plays per Hour", "4 per screen"),
        ]

        self.docx_service.add_data_table(
            doc,
            headers=["Detail", "Value"],
            rows=details,
        )

    def _add_signature_section(self, doc, business_name, client_name,
                                contract_type):
        """Add the signature and agreement block."""
        party_labels = {
            "advertiser": "Advertiser",
            "host": "Venue Host",
            "host_advertising": "Host Advertiser",
        }
        party_label = party_labels.get(contract_type, "Advertiser")

        agreement_text = (
            f"By signing below, {client_name} on behalf of {business_name} "
            f"('{party_label}') agrees to the terms and conditions outlined in this "
            f"agreement. This agreement is legally binding upon signature by both parties."
        )
        self.docx_service.add_body_text(doc, agreement_text)
        self.docx_service.add_body_text(doc, "")

        # Signature lines with spacing
        self.docx_service.add_callout_box(
            doc,
            f"{party_label} Signature\n\n"
            f"Signed By: ________________________________\n\n"
            f"Printed Name: ________________________________\n\n"
            f"Title: ________________________________\n\n"
            f"Date: ________________________________"
        )

        self.docx_service.add_body_text(doc, "")

        self.docx_service.add_callout_box(
            doc,
            "MCTV Elite Advertising\n\n"
            "Signed By: ________________________________\n\n"
            "Printed Name: ________________________________\n\n"
            "Title: ________________________________\n\n"
            "Date: ________________________________"
        )

        self.docx_service.add_body_text(doc, "")
        self.docx_service.add_section_divider(doc)

        # Electronic signature notice
        e_sign_notice = (
            "ELECTRONIC SIGNATURE NOTICE: This contract may also be signed "
            "electronically through the MCTV Client Portal. Electronic signatures "
            "made through the portal (typed name + 'I Agree' confirmation) are "
            "legally equivalent to handwritten signatures under the Mississippi "
            "Uniform Electronic Transactions Act."
        )

        para = doc.add_paragraph()
        run = para.add_run(e_sign_notice)
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
        run.italic = True
