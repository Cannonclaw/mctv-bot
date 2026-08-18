# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Evaluation Access Terms — the gate on every partner/demo portal session.

A partner cannot reach any portal page until they accept these on-screen and
the acceptance is written to portal_terms_acceptances (migration 024). The
passive "by using this you agree" wording on the client-facing terms page is
not evidence; a stored row with a timestamp and IP is.

These terms are deliberately stricter than the client terms in portal_terms.py:
they cover confidentiality, scope of use, non-derivation, non-circumvention,
term and termination, audit, and survival.
"""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user, portal_logout
from services.config_service import load_config
from services.partner_access import (
    PARTNER_TERMS_VERSION, has_accepted_terms, record_terms_acceptance,
    is_demo_session, partner_org, watermark_label,
)
from services.portal_ui import inject_portal_css, render_portal_footer

st.set_page_config(
    page_title="Evaluation Access Terms - MCTV",
    page_icon="\U0001F512",
    layout="centered",
)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
config = load_config()
company = config.get("company", {})
legal_name = company.get("legal_name", "MCTV Digital")
org = partner_org() or "your organization"

# A normal client landing here has nothing to accept.
if not is_demo_session():
    st.info("These terms apply to partner evaluation accounts.")
    st.page_link("pages/portal_dashboard.py", label="Back to Dashboard", icon="\U0001F3E0")
    st.stop()

already_accepted = has_accepted_terms(user)


# ── Header ──────────────────────────────────────────────────────────────────

st.markdown(f"## Evaluation Access Terms")
st.caption(f"Version {PARTNER_TERMS_VERSION}  |  Issued to {org}")

if already_accepted:
    st.success("You have accepted these terms. They remain in effect for this evaluation.")
    st.page_link("pages/portal_dashboard.py", label="Go to Dashboard", icon="\U0001F3E0")
    st.divider()
else:
    st.warning(
        "Please read and accept these terms to continue. Access to the platform "
        "is conditional on your agreement."
    )

st.markdown(f"""
This agreement governs {org}'s access to the {company.get('name', 'MCTV Elite Advertising')}
client portal and related materials (the "Platform"), operated by
{legal_name}, Inc. ("MCTV"). By accepting below, you agree to these terms on
behalf of yourself and your organization.

---

#### 1. Purpose and Scope of Access

Access is granted **solely to evaluate** the Platform for the purpose discussed
between the parties. It is a limited, revocable, non-exclusive, non-transferable
right to view. It is **not** a license to use, deploy, resell, sublicense, or
operate the Platform, and it grants no ownership interest of any kind.

The account issued to you is **read-only** and is populated with **sample data**.
Nothing you see in it represents an actual MCTV client, contract, or rate.

#### 2. Confidential Information

"Confidential Information" means everything you access, view, or learn through
the Platform or in connection with this evaluation, including its software,
user interface, workflows, client portal, proposal and report formats, pricing
models, rate cards, audience and impression methodology, venue and market data,
and any documentation or discussion relating to them.

You agree to:

- keep Confidential Information strictly confidential;
- use it only for the evaluation purpose in Section 1;
- disclose it only to those of your personnel who need it for that purpose and
  who are bound by confidentiality obligations at least as protective as these;
  and
- not disclose it to any affiliate, franchisee, licensee, contractor, or third
  party without MCTV's prior written consent.

These obligations do not apply to information you can show was already lawfully
known to you without obligation, is or becomes public through no act of yours,
or is independently developed by you without reference to the Confidential
Information.

#### 3. Proprietary Rights and Non-Derivation

The Platform is the exclusive property of {legal_name}, Inc. and contains trade
secrets protected under the Mississippi Uniform Trade Secrets Act
(Miss. Code Ann. 75-26-1 et seq.) and the federal Defend Trade Secrets Act
(18 U.S.C. 1836), as well as copyright.

You agree **not** to:

- copy, reproduce, screenshot, record, scrape, or export any part of the
  Platform or its data, except as MCTV expressly permits in writing;
- reverse engineer, decompile, disassemble, or attempt to derive the source
  code, algorithms, prompt templates, or data models underlying the Platform;
- create derivative works from, or works substantially based on, the Platform;
  or
- use the Platform or Confidential Information to design, build, specify,
  commission, or assist any person in building a product or service that
  competes with it.

#### 4. Non-Circumvention

For the term of this agreement and **twenty-four months** afterward, you agree
not to use MCTV's Confidential Information or introductions to contract directly
with, or solicit, any venue, host, advertiser, or partner first made known to you
through this evaluation, in a manner that circumvents MCTV.

#### 5. Term, Termination, and Return

Access is time-limited and shown in the banner on each page. MCTV may suspend or
terminate access **at any time, for any reason, without notice**. On termination
or expiry you must stop all use and destroy or return any materials derived from
the Platform, and confirm in writing that you have done so if MCTV asks.

#### 6. Audit and Monitoring

Your use of this account is logged, including sign-ins, pages viewed, and
documents opened, together with timestamp and originating IP address. Documents
surfaced to this account carry identifying provenance markings. You consent to
this monitoring. MCTV may request written confirmation of your compliance with
these terms.

#### 7. No Warranty; No Obligation

The Platform is provided **as is** for evaluation, with no warranty of any kind.
Sample figures are illustrative and are not a representation of performance.
Nothing here obliges either party to enter any further agreement.

#### 8. Remedies

You acknowledge that a breach of Sections 2, 3, or 4 would cause MCTV harm that
money alone cannot remedy, and that MCTV is entitled to seek injunctive relief
in addition to any other remedy, without posting bond.

#### 9. Survival

Sections 2, 3, 4, 6, 8, 9, and 10 survive the expiry or termination of this
agreement. The confidentiality obligation in Section 2 survives for **three
years** after termination; obligations relating to trade secrets survive for as
long as the material remains a trade secret under applicable law.

#### 10. Governing Law

This agreement is governed by the laws of the State of Mississippi, without
regard to its conflict-of-laws rules. The parties consent to exclusive
jurisdiction and venue in the state and federal courts of Hinds County,
Mississippi.

#### 11. Relationship to Other Agreements

These terms supplement — and do not replace — any separately signed
non-disclosure or evaluation agreement between the parties. Where a signed
written agreement conflicts with these terms, the signed agreement controls.

---
""")


# ── Acceptance ──────────────────────────────────────────────────────────────

if not already_accepted:
    st.markdown("### Acceptance")
    st.caption(
        "Accepting records your name, email, IP address, and the time of "
        "acceptance as evidence of agreement."
    )

    with st.form("partner_terms_acceptance"):
        typed_name = st.text_input(
            "Type your full name",
            placeholder="Full legal name",
            help="This acts as your electronic signature.",
        )
        typed_org = st.text_input(
            "Organization you are accepting on behalf of",
            value=partner_org(),
        )
        agree = st.checkbox(
            "I have read these terms, I have authority to accept them for the "
            "organization named above, and I agree to be bound by them."
        )
        submitted = st.form_submit_button("Accept and Continue", type="primary",
                                          width='stretch')

    if submitted:
        if not typed_name.strip():
            st.error("Please type your full name.")
        elif not typed_org.strip():
            st.error("Please enter your organization.")
        elif not agree:
            st.error("Please confirm you agree to the terms.")
        else:
            with st.spinner("Recording your acceptance..."):
                ok = record_terms_acceptance(user)
            if ok:
                st.success("Acceptance recorded. Opening the portal...")
                st.switch_page("pages/portal_dashboard.py")
            else:
                st.error(
                    "We could not record your acceptance. Please try again, or "
                    "contact your MCTV representative."
                )

    st.divider()
    if st.button("Decline and Sign Out", width='stretch'):
        portal_logout()
        st.switch_page("app.py")

st.caption(watermark_label(user) or f"Copyright (c) 2026 {legal_name}, Inc. All rights reserved.")
render_portal_footer()
