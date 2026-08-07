# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Field Audit — build the packet a contractor takes into the field, and read
their findings back in.

Four tabs:

    Roster      every screen in the market, with its license number
    Gaps        what we already know is missing, and what to do about it
    Packet      generate the brief, the field sheet, and the label sheet
    Import      read a completed field sheet into screen_assets

The roster is assembled once per rerun and passed into every tab — same
convention as the Pipeline and Loop Inventory pages.

Drop into: mctv-bot/pages/26_Field_Audit.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.config_service import load_config, get_team_names
from services.field_audit_service import (
    audit_roster,
    build_workbook,
    parse_completed_workbook,
    roster_gaps,
    roster_summary,
    route_order,
    save_assets,
)
from services.loop_inventory_service import latest_sweep_date
from services.screen_inventory_service import MARKET_LABELS, market_label

st.set_page_config(
    page_title="Field Audit - MCTV Bot",
    page_icon="\U0001F4CB",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Markets the sweep actually covers, plus their label.
AUDITABLE_MARKETS = ["tupelo", "oxford", "starkville"]


# ---------------------------------------------------------------------------
# Shared data — fetched once per rerun and passed into every tab
# ---------------------------------------------------------------------------

st.markdown("## \U0001F4CB Field Audit")
st.caption(
    "Everything a contractor needs to walk the network: where each screen is, "
    "who to ask for, the license number of the Raspberry Pi driving it, and a "
    "label to stick on the unit so the number stays readable."
)

market = st.selectbox(
    "Market",
    AUDITABLE_MARKETS,
    format_func=lambda m: MARKET_LABELS.get(m, m.title()),
)

sweep = latest_sweep_date()
rows = route_order(audit_roster(market, sweep))
gaps = roster_gaps(rows)
summary = roster_summary(rows)

if not rows:
    st.warning(
        "No screens found for this market. The roster is built from the "
        "`screen_loops` whitelist sweep — if Supabase is unreachable or no "
        "sweep has been loaded, there is nothing to audit yet."
    )
    st.stop()

st.caption(
    f"Sweep: **{sweep or 'none loaded'}** · "
    f"{summary['screens']} screens across {summary['venues']} venues, "
    f"{summary['stops']} stops."
)

kpi = st.columns(5)
kpi[0].metric("Screens", summary["screens"])
kpi[1].metric("Venues", summary["venues"])
kpi[2].metric("Stops", summary["stops"])
kpi[3].metric("License unknown", summary["missing_license"],
              help="Screens with no license number on file. No label prints "
                   "for these — the number is recorded on site instead.")
kpi[4].metric("No host contact", summary["no_contact"],
              help="Venues with no named contact in the host list.")

tab_roster, tab_gaps, tab_packet, tab_import = st.tabs(
    ["Roster", "Gaps", "Packet", "Import findings"]
)


# ---------------------------------------------------------------------------
# Tab 1 — Roster
# ---------------------------------------------------------------------------

with tab_roster:
    st.markdown("#### Screens, in route order")
    st.caption(
        "One row per license. A venue with two screens has two rows and two "
        "labels — they are not interchangeable."
    )

    frame = pd.DataFrame([
        {
            "Stop": r["stop_no"],
            "Cluster": r["cluster"],
            "Venue": r["venue_name"],
            "Screen": r["screen_label"],
            "Short code": r["short_code"],
            "License number": r["license_id"] or "",
            "Address": r["address"],
            "Contact": r["contact_name"],
            "Phone": r["contact_phone"],
            "Loop": r["expected_loop_mmss"],
            "Spots": r["expected_items"],
            "Over target": r["over_target"],
            "Shared building": r["same_building"],
        }
        for r in rows
    ])
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "Over target": st.column_config.CheckboxColumn(disabled=True),
            "Shared building": st.column_config.CheckboxColumn(disabled=True),
            "License number": st.column_config.TextColumn(width="medium"),
        },
    )

    shared = sorted({r["venue_name"] for r in rows if r["same_building"]})
    if shared:
        st.info(
            "**One trip, several screens.** These venues share a building with "
            "another MCTV venue: " + ", ".join(shared) + "."
        )


# ---------------------------------------------------------------------------
# Tab 2 — Gaps
# ---------------------------------------------------------------------------

with tab_gaps:
    st.markdown("#### What we already know is missing")
    st.caption(
        "These go into the packet as an appendix so the contractor is not "
        "chasing our own gaps. Anything fixed here disappears from the next "
        "packet automatically."
    )

    if not gaps:
        st.success("Nothing outstanding — the roster is complete.")
    else:
        by_kind: dict[str, list[dict]] = {}
        for gap in gaps:
            by_kind.setdefault(gap["kind"], []).append(gap)

        for kind, items in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
            with st.expander(f"{kind} ({len(items)})", expanded=len(items) <= 3):
                st.dataframe(
                    pd.DataFrame([
                        {"Venue": g["venue"], "Detail": g["detail"],
                         "What to do": g["action"]}
                        for g in items
                    ]),
                    width="stretch",
                    hide_index=True,
                )


# ---------------------------------------------------------------------------
# Tab 3 — Packet
# ---------------------------------------------------------------------------

with tab_packet:
    st.markdown("#### Generate the packet")
    st.caption(
        "Three files: a brief that says what to do, a spreadsheet to record "
        "findings in, and a sheet of labels for the Raspberry Pis."
    )

    config = load_config()

    left, right = st.columns(2)
    with left:
        prepared_for = st.text_input("Auditor / contractor", value="Exceed Technologies")
        prepared_by = st.selectbox("Prepared by", get_team_names(config))
    with right:
        copies = st.number_input(
            "Labels per license", min_value=1, max_value=4, value=1,
            help="Two is worth it when units are awkward to reach and the "
                 "first label goes on crooked.",
        )
        want_pdf = st.checkbox("Also convert the brief to PDF", value=False)

    if summary["missing_license"]:
        st.warning(
            f"{summary['missing_license']} screens have no license number on "
            f"file, so no label prints for them. The brief tells the "
            f"contractor to record those numbers on site. To fix it properly, "
            f"add the numbers to `data/audit/extra_licenses.json`."
        )

    if st.button("Build packet", type="primary", width="stretch"):
        from services.docx_service import DocxService
        from generators.field_audit import FieldAuditGenerator
        from generators.field_audit_labels import generate_labels

        progress = st.progress(0.0, text="Starting...")

        def on_progress(name, current, total):
            progress.progress(current / total, text=f"{name} ({current}/{total})")

        try:
            brief_path = FieldAuditGenerator(config, DocxService(config)).generate(
                rows, gaps, market,
                prepared_for=prepared_for,
                prepared_by_name=prepared_by,
                sweep_date=sweep,
                progress_callback=on_progress,
            )
            label_path, printed, skipped = generate_labels(rows, market, copies=int(copies))
            sheet_bytes = build_workbook(rows, gaps, market)
            progress.progress(1.0, text="Done")

            st.session_state["field_audit_packet"] = {
                "brief": (brief_path.name, brief_path.read_bytes()),
                "labels": (label_path.name, label_path.read_bytes()),
                "sheet": (
                    f"MCTV_FieldSheet_{market_label(market).replace(' ', '')}.xlsx",
                    sheet_bytes,
                ),
                "printed": printed,
                "skipped": len(skipped),
                "brief_path": str(brief_path),
            }
        except Exception as exc:
            progress.empty()
            st.error(f"Packet generation failed: {exc}")
            st.exception(exc)

    packet = st.session_state.get("field_audit_packet")
    if packet:
        sheets = -(-packet["printed"] // 10)  # 10 labels per Avery 5163 sheet
        st.success(
            f"Packet ready — {packet['printed']} labels across {sheets} "
            f"Avery 5163 sheets"
            + (f", {packet['skipped']} screens with no license number"
               if packet["skipped"] else "")
            + "."
        )

        cols = st.columns(3)
        with cols[0]:
            name, data = packet["brief"]
            st.download_button("\U0001F4C4 Audit brief (.docx)", data=data,
                               file_name=name, mime=DOCX_MIME,
                               width="stretch", key="dl_brief")
        with cols[1]:
            name, data = packet["sheet"]
            st.download_button("\U0001F4CA Field sheet (.xlsx)", data=data,
                               file_name=name, mime=XLSX_MIME,
                               width="stretch", key="dl_sheet")
        with cols[2]:
            name, data = packet["labels"]
            st.download_button("\U0001F3F7️ Label sheet (.docx)", data=data,
                               file_name=name, mime=DOCX_MIME,
                               width="stretch", key="dl_labels")

        st.caption(
            "Print the label sheet on Avery 5163 stock (4\" x 2\", ten per "
            "sheet). Run one page on plain paper and hold it against a sheet "
            "of stock before printing the rest."
        )

        if want_pdf:
            from services.pdf_service import convert_docx_to_pdf
            with st.spinner("Converting the brief to PDF..."):
                pdf_path = convert_docx_to_pdf(Path(packet["brief_path"]))
            if pdf_path and pdf_path.exists():
                st.download_button("\U0001F4D5 Audit brief (.pdf)",
                                   data=pdf_path.read_bytes(),
                                   file_name=pdf_path.name,
                                   mime="application/pdf",
                                   width="stretch", key="dl_brief_pdf")
            else:
                st.warning(
                    "PDF conversion is unavailable here — LibreOffice is not "
                    "installed. The .docx above is the same document."
                )


# ---------------------------------------------------------------------------
# Tab 4 — Import findings
# ---------------------------------------------------------------------------

with tab_import:
    st.markdown("#### Read a completed field sheet back in")
    st.caption(
        "Upload the spreadsheet the contractor returns. Rows are matched on "
        "license number, so re-importing a corrected sheet updates the same "
        "screen rather than duplicating it. Rows where nothing was recorded "
        "are ignored."
    )

    upload = st.file_uploader(
        "Completed field sheet", type=["xlsx", "xlsm"], key="audit_upload"
    )

    if upload is not None:
        try:
            records = parse_completed_workbook(upload, market=market)
        except Exception as exc:
            st.error(f"Could not read that file: {exc}")
            records = []

        if not records:
            st.info(
                "No completed rows found. Check that the sheet still has its "
                "**Field Sheet** tab and its original header row."
            )
        else:
            known = {r["license_id"] for r in rows if r["license_id"]}
            unmatched = [
                r for r in records
                if r.get("license_id") and r["license_id"] not in known
            ]
            no_license = [r for r in records if not r.get("license_id")]

            stat = st.columns(3)
            stat[0].metric("Rows with findings", len(records))
            stat[1].metric("New license numbers", len(no_license),
                           help="Rows the contractor filled in that had no "
                                "license number in the packet.")
            stat[2].metric("Unrecognised licenses", len(unmatched),
                           help="License numbers not in this market's roster. "
                                "Worth a look before saving.")

            st.dataframe(
                pd.DataFrame([
                    {
                        "Venue": r.get("venue_name", ""),
                        "Screen": r.get("screen_label", ""),
                        "Short code": r.get("short_code", ""),
                        "Screen on": r.get("screen_on", ""),
                        "Playing": r.get("content_playing", ""),
                        "Display": " ".join(filter(None, [
                            r.get("display_brand", ""),
                            str(r.get("display_size_in") or ""),
                        ])).strip(),
                        "Pi": r.get("pi_model", ""),
                        "Labelled": r.get("label_applied", ""),
                        "Condition": r.get("condition", ""),
                        "Issues": r.get("issues", ""),
                    }
                    for r in records
                ]),
                width="stretch",
                hide_index=True,
            )

            if unmatched:
                st.warning(
                    "Some license numbers are not in this market's roster: "
                    + ", ".join(sorted(
                        r["license_id"] for r in unmatched
                    )[:5])
                    + (" ..." if len(unmatched) > 5 else "")
                    + ". They will still be saved."
                )

            if st.button("Save to screen_assets", type="primary",
                         width="stretch"):
                saved, errors = save_assets(records)
                if saved:
                    st.success(f"Saved {saved} of {len(records)} screens.")
                if errors:
                    st.error("Some rows did not save:")
                    for message in errors[:10]:
                        st.write(f"- {message}")
                    st.caption(
                        "If every row failed, check that migration "
                        "`scripts/026_screen_assets.sql` has been applied."
                    )
