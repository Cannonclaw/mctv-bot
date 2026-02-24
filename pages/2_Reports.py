"""Traction Report Generator page - creates advertiser and venue reports."""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.config_service import load_config, get_team_names
from services.claude_service import ClaudeService
from services.docx_service import DocxService
from services.excel_parser import parse_excel, aggregate_by_host, build_report_data, format_duration, format_date_range, parse_network_dashboard, enrich_report_with_dashboard
from services.pdf_service import convert_docx_to_pdf, is_pdf_available
from models.report_data import TractionReportInput, VenueRecord
from generators.advertiser_report import AdvertiserReportGenerator
from generators.venue_report import VenueReportGenerator
from services.supabase_client import is_configured as supabase_configured, insert_row
from services.portal_service import get_all_clients
from services.storage_service import upload_from_path, BUCKET_REPORTS
from services.notification_service import notify_report_shared

st.set_page_config(page_title="Traction Reports - MCTV Bot", page_icon="\U0001F4CA", layout="wide")

from services.auth import check_password
if not check_password():
    st.stop()

st.markdown("## Traction Report Generator")
st.caption("Generate professional traction and ad performance reports.")

config = load_config()

# ── Pre-load client list for advertiser name dropdown ─────────────────────
_clients_cache = []
if supabase_configured():
    try:
        _clients_cache = get_all_clients() or []
    except Exception:
        pass  # If Supabase is down, fall back to manual entry

# Build separate lists for advertiser and host/venue clients
_advertiser_names = sorted(set(
    c.get("business_name", "") for c in _clients_cache
    if c.get("business_name") and c.get("client_type") != "host"
))
_venue_names = sorted(set(
    c.get("business_name", "") for c in _clients_cache
    if c.get("business_name")
))
_CUSTOM_OPTION = "— Type a custom name —"


# ── SHARE WITH CLIENT PORTAL ─────────────────────────────────────────────────

def _show_share_with_client(report_path, data: TractionReportInput):
    """Show a 'Share with Client Portal' section after report generation."""
    if not supabase_configured():
        return

    st.divider()
    st.markdown("#### Share with Client Portal")
    st.caption("Upload this report to a client's portal so they can view it anytime.")

    clients = get_all_clients()
    if not clients:
        st.info("No clients in the system yet. Add clients on the Client Management page.")
        return

    client_options = {
        f"{c.get('business_name', 'Unknown')} ({c.get('contact_name', '')})": c
        for c in clients
    }

    share_col1, share_col2 = st.columns([3, 1])

    with share_col1:
        selected_label = st.selectbox(
            "Share with Client",
            options=["-- Select a client --"] + list(client_options.keys()),
            key="share_client_select",
        )

    with share_col2:
        st.markdown("")  # spacer
        if selected_label != "-- Select a client --":
            if st.button("Share Report", type="primary", use_container_width=True,
                         key="share_report_btn"):
                selected_client = client_options.get(selected_label)
                if selected_client:
                    _do_share_report(report_path, data, selected_client)


def _do_share_report(report_path, data: TractionReportInput, client: dict):
    """Upload report to storage and create a client_reports record."""
    client_id = client.get("id", "")
    bname = client.get("business_name", "")

    with st.spinner("Sharing report with client portal..."):
        # Upload to Supabase Storage
        storage_path = f"{client_id}/{report_path.name}"
        uploaded = upload_from_path(BUCKET_REPORTS, storage_path, str(report_path))

        # Determine report title
        title = f"{bname} Traction Report"
        if hasattr(data, "campaign_period") and data.campaign_period:
            title += f" - {data.campaign_period}"
        elif hasattr(data, "report_period") and data.report_period:
            title += f" - {data.report_period}"

        # Get totals from data
        total_plays = None
        total_impressions = None
        total_venues = None
        if hasattr(data, "venue_records") and data.venue_records:
            total_venues = len(data.venue_records)
            total_plays = sum(v.total_plays for v in data.venue_records if hasattr(v, "total_plays"))

        # Create client_reports record
        report_data = {
            "client_id": client_id,
            "report_type": data.report_type if hasattr(data, "report_type") else "advertiser",
            "title": title,
            "document_url": storage_path if uploaded else str(report_path),
        }
        if hasattr(data, "campaign_period"):
            report_data["campaign_period"] = data.campaign_period
        elif hasattr(data, "report_period"):
            report_data["campaign_period"] = data.report_period
        if total_plays:
            report_data["total_plays"] = total_plays
        if total_impressions:
            report_data["total_impressions"] = total_impressions
        if total_venues:
            report_data["total_venues"] = total_venues

        result = insert_row("client_reports", report_data)

        if result:
            # Notify client
            notify_report_shared(
                client_email=client.get("contact_email", ""),
                client_name=client.get("contact_name", ""),
                report_title=title,
            )
            st.success(f"Report shared with **{bname}**. They've been notified by email.")
        else:
            st.error("Failed to share report. Check logs for details.")


# ── GENERATION ENGINE (must be defined before forms call it) ──────────────────

def _generate_report(data: TractionReportInput, output_format: str = "DOCX"):
    """Run the report generation pipeline.

    Args:
        data: Traction report input data.
        output_format: 'DOCX', 'PDF', or 'Both'.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    config = load_config()
    model = config["proposal_settings"].get("model", "claude-sonnet-4-5-20250929")

    claude = None
    if data.include_insights:
        if not api_key or api_key == "your-api-key-here":
            st.warning("API key not set. Generating report without AI insights.")
            data.include_insights = False
        else:
            claude = ClaudeService(api_key=api_key, model=model)

    docx = DocxService(config)

    if data.report_type == "venue":
        generator = VenueReportGenerator(config, claude, docx)
    else:
        generator = AdvertiserReportGenerator(config, claude, docx)

    progress_bar = st.progress(0, text="Generating report...")

    def on_progress(step_name, current, total):
        progress_bar.progress(current / total, text=f"{step_name} ({current}/{total})")

    try:
        report_path = generator.generate(data, progress_callback=on_progress)
        progress_bar.progress(1.0, text="Complete!")

        st.success("Report generated successfully!")
        if claude:
            st.caption(f"API Usage: {claude.usage_summary}")

        # DOCX download
        if output_format in ("DOCX", "Both"):
            with open(report_path, "rb") as f:
                st.download_button(
                    "\U0001F4C4 Download Report (.docx)",
                    data=f.read(),
                    file_name=report_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary" if output_format == "DOCX" else "secondary",
                    use_container_width=True,
                    key="dl_docx",
                )

        # PDF conversion + download
        if output_format in ("PDF", "Both"):
            with st.spinner("Converting to PDF..."):
                pdf_path = convert_docx_to_pdf(report_path)
            if pdf_path and pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "\U0001F4D5 Download Report (.pdf)",
                        data=f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key="dl_pdf",
                    )
            else:
                st.warning(
                    "PDF conversion not available. Install LibreOffice "
                    "(https://www.libreoffice.org/download/) or the docx2pdf "
                    "package (`pip install docx2pdf`) to enable PDF output."
                )
                # Still show DOCX download as fallback
                if output_format == "PDF":
                    with open(report_path, "rb") as f:
                        st.download_button(
                            "\U0001F4C4 Download Report (.docx instead)",
                            data=f.read(),
                            file_name=report_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="secondary",
                            use_container_width=True,
                            key="dl_docx_fallback",
                        )

        # ── Auto-generate email ──
        if claude and isinstance(generator, AdvertiserReportGenerator):
            st.divider()
            st.markdown("#### Send-Along Email")
            with st.spinner("Generating email..."):
                email_text = generator.generate_email(data)
            if email_text:
                st.text_area(
                    "Copy this email to send with the report:",
                    value=email_text,
                    height=250,
                    key="report_email_text",
                )
                st.caption("Tip: Copy the text above and paste into your email client.")
            else:
                st.info("Email generation not available. Set your API key to enable.")

        # ── Share with Client Portal ──
        _show_share_with_client(report_path, data)

    except Exception as e:
        progress_bar.empty()
        st.error(f"Error generating report: {str(e)}")
        st.exception(e)

# Report type selector
report_type = st.selectbox(
    "Report Type",
    ["Advertiser Traction Report", "Venue Partner Report"],
    help="Choose what kind of report to generate.",
)

st.divider()

# Data source tabs
tab_upload, tab_manual = st.tabs(["Upload NTV360 Excel", "Manual Data Entry"])


# ── EXCEL UPLOAD TAB ──────────────────────────────────────────────────────────
with tab_upload:
    st.markdown("### Upload NTV360 Export")
    st.caption("Upload one or more Excel files exported from the NTV360 dashboard.")

    uploaded_files = st.file_uploader(
        "Drop Excel files here",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        help="Supports all NTV360 export formats (content reports, per-content reports, pre-formatted traction reports)",
    )

    # Network Dashboard upload (optional — enriches report with impressions, dwell, traffic)
    st.markdown("##### Network Dashboard *(optional)*")
    st.caption(
        "Upload the MCTV Network Dashboard Excel for impression counts, "
        "dwell times, and foot traffic data. This adds Impressions and CPM "
        "columns to the venue table."
    )
    dashboard_file = st.file_uploader(
        "Network Dashboard (.xlsx)",
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        key="dashboard_upload",
        help="The 'MCTV - Network Dashboard' Excel file with Traffic, Dwell Time, and Impressions columns.",
    )

    # Parse dashboard if provided
    dashboard_lookup = {}
    if dashboard_file:
        try:
            dashboard_lookup = parse_network_dashboard(dashboard_file)
            st.success(f"Dashboard loaded: {len(dashboard_lookup)} venues with impression data")
        except Exception as e:
            st.error(f"Error parsing dashboard: {e}")

    if uploaded_files:
        all_records = []
        for uploaded_file in uploaded_files:
            try:
                records = parse_excel(uploaded_file)
                all_records.extend(records)
                st.success(f"Parsed {uploaded_file.name}: {len(records)} play records found")
            except Exception as e:
                st.error(f"Error parsing {uploaded_file.name}: {e}")

        if all_records:
            # Show summary — use build_report_data for demo exclusion + categorization
            preview_data = build_report_data(all_records, "Preview")
            total_plays = preview_data.total_plays
            total_hosts = preview_data.total_screen_count

            st.markdown("#### Data Summary")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Total Play Records", f"{len(all_records):,}")
            mc2.metric("Unique Venues", f"{total_hosts}")
            mc3.metric("Total Ad Plays", f"{total_plays:,}")

            # Show dashboard match rate if dashboard is loaded
            if dashboard_lookup:
                matched = sum(
                    1 for v in preview_data.venue_records
                    if v.host_name.lower() in dashboard_lookup
                )
                mc4.metric("Dashboard Matches", f"{matched}/{total_hosts}")
            else:
                mc4.metric("Dashboard", "Not loaded")

            # Show content names found
            content_names = set()
            for rec in all_records:
                if rec.content_name:
                    content_names.add(rec.content_name)

            if content_names:
                st.caption(f"Content pieces found: {', '.join(sorted(content_names)[:10])}")

            # Show cities detected
            cities = set(v.city for v in preview_data.venue_records if v.city)
            if cities:
                st.caption(f"Markets detected: {', '.join(sorted(cities))}")

            st.divider()

            # Auto-detect campaign period from data dates — formatted nicely
            auto_period = ""
            if preview_data.campaign_start and preview_data.campaign_end:
                auto_period = format_date_range(preview_data.campaign_start, preview_data.campaign_end)

            # Report configuration
            col1, col2 = st.columns(2)
            with col1:
                if report_type == "Advertiser Traction Report":
                    name_options = _advertiser_names + [_CUSTOM_OPTION]
                    selected_name = st.selectbox("Advertiser Name *", name_options,
                                                  index=0 if name_options[0] != _CUSTOM_OPTION else 0,
                                                  key="excel_adv_select")
                    if selected_name == _CUSTOM_OPTION:
                        advertiser_name = st.text_input("Custom Advertiser Name *",
                                                         placeholder="Rebel Body Fitness",
                                                         key="excel_adv_custom")
                    else:
                        advertiser_name = selected_name
                else:
                    name_options = _venue_names + [_CUSTOM_OPTION]
                    selected_name = st.selectbox("Venue Name *", name_options,
                                                  index=0 if name_options[0] != _CUSTOM_OPTION else 0,
                                                  key="excel_venue_select")
                    if selected_name == _CUSTOM_OPTION:
                        advertiser_name = st.text_input("Custom Venue Name *",
                                                         placeholder="Oxford Park Commission",
                                                         key="excel_venue_custom")
                    else:
                        advertiser_name = selected_name
                campaign_period = st.text_input("Campaign Period",
                                                 value=auto_period,
                                                 placeholder="November 2025 - February 2026")
            with col2:
                include_insights = st.toggle("Include AI-Generated Insights", value=True,
                                              help="Claude will analyze the data and write performance insights")
                sales_rep = st.selectbox("Sales Rep (for footer)", get_team_names(config))
                pdf_available = is_pdf_available()
                output_format = st.selectbox(
                    "Output Format",
                    ["PDF", "DOCX", "Both"] if pdf_available else ["DOCX", "PDF", "Both"],
                    help="PDF requires LibreOffice or docx2pdf. "
                         + ("PDF conversion is available." if pdf_available
                            else "Install LibreOffice to enable PDF."),
                )

            # Monthly rate (for CPM calculation) — only show if dashboard is loaded
            monthly_rate = 0.0
            if dashboard_lookup:
                monthly_rate = st.number_input(
                    "Advertiser Monthly Rate ($)",
                    min_value=0.0, value=0.0, step=50.0,
                    help="Enter the advertiser's monthly ad spend to calculate CPM (Cost Per Thousand Impressions) by venue. Leave at $0 to skip CPM.",
                )

            if st.button("Generate Report", type="primary", use_container_width=True):
                if not advertiser_name:
                    st.error("Please enter the advertiser/venue name.")
                else:
                    report_data = build_report_data(all_records, advertiser_name, campaign_period)
                    report_data.include_insights = include_insights
                    report_data.sales_rep = sales_rep
                    report_data.monthly_rate = monthly_rate
                    report_data.report_type = "advertiser" if report_type == "Advertiser Traction Report" else "venue"

                    # Enrich with dashboard data (impressions, dwell, traffic)
                    if dashboard_lookup:
                        enrich_report_with_dashboard(report_data, dashboard_lookup)

                    _generate_report(report_data, output_format=output_format)


# ── MANUAL ENTRY TAB ──────────────────────────────────────────────────────────
with tab_manual:
    st.markdown("### Manual Data Entry")
    st.caption("Enter performance data manually if you don't have an Excel export.")

    col1, col2 = st.columns(2)
    with col1:
        if report_type == "Advertiser Traction Report":
            name_options = _advertiser_names + [_CUSTOM_OPTION]
            selected_name = st.selectbox("Advertiser Name *", name_options,
                                          index=0 if name_options[0] != _CUSTOM_OPTION else 0,
                                          key="manual_adv_select")
            if selected_name == _CUSTOM_OPTION:
                name = st.text_input("Custom Advertiser Name *",
                                      placeholder="Rebel Body Fitness",
                                      key="manual_adv_custom")
            else:
                name = selected_name
        else:
            name_options = _venue_names + [_CUSTOM_OPTION]
            selected_name = st.selectbox("Venue Name *", name_options,
                                          index=0 if name_options[0] != _CUSTOM_OPTION else 0,
                                          key="manual_venue_select")
            if selected_name == _CUSTOM_OPTION:
                name = st.text_input("Custom Venue Name *",
                                      placeholder="Oxford Park Commission",
                                      key="manual_venue_custom")
            else:
                name = selected_name
        campaign_period = st.text_input("Campaign Period", key="manual_period",
                                         placeholder="6 Month Campaign")
    with col2:
        include_insights = st.toggle("Include AI Insights", value=True, key="manual_insights")
        sales_rep = st.selectbox("Sales Rep", get_team_names(config), key="manual_rep")

    st.markdown("#### Venue Performance Data")
    num_venues = st.number_input("Number of Venues", min_value=1, max_value=100, value=5, key="manual_num")

    venue_records = []
    for i in range(num_venues):
        with st.expander(f"Venue {i + 1}", expanded=(i < 3)):
            vc1, vc2, vc3 = st.columns(3)
            vname = vc1.text_input("Venue Name", key=f"mv_name_{i}", placeholder="Oxford Park Commission")
            vcategory = vc2.selectbox("Category", [""] + config["venue_categories"], key=f"mv_cat_{i}")
            vplays = vc3.number_input("Total Plays", min_value=0, value=0, step=1000, key=f"mv_plays_{i}")

            vc4, vc5, vc6 = st.columns(3)
            vscreens = vc4.number_input("Screens", min_value=1, value=1, key=f"mv_screens_{i}")
            vtraffic = vc5.number_input("Monthly Traffic", min_value=0.0, value=0.0, step=500.0, key=f"mv_traffic_{i}")
            vimpressions = vc6.number_input("Monthly Impressions", min_value=0.0, value=0.0, step=1000.0, key=f"mv_imp_{i}")

            if vname and vplays > 0:
                venue_records.append(VenueRecord(
                    host_name=vname,
                    business_category=vcategory,
                    screen_count=vscreens,
                    monthly_traffic=vtraffic,
                    monthly_impressions=vimpressions,
                    total_plays=vplays,
                ))

    if st.button("Generate Report", type="primary", use_container_width=True, key="manual_gen"):
        if not name:
            st.error("Please enter the advertiser/venue name.")
        elif not venue_records:
            st.error("Please enter data for at least one venue.")
        else:
            total_plays = sum(v.total_plays for v in venue_records)
            total_impressions = sum(v.monthly_impressions for v in venue_records)

            # Calculate percentages
            for v in venue_records:
                v.pct_of_total = round(v.total_plays / total_plays * 100, 1) if total_plays > 0 else 0

            report_data = TractionReportInput(
                advertiser_name=name,
                report_type="advertiser" if report_type == "Advertiser Traction Report" else "venue",
                campaign_period=campaign_period,
                venue_records=venue_records,
                total_plays=total_plays,
                total_screen_count=len(venue_records),
                total_impressions=total_impressions,
                include_insights=include_insights,
                sales_rep=sales_rep,
            )
            _generate_report(report_data)
