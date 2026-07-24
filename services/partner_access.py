# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Read-only evaluation access for outside partner organizations.

Backs the sandbox demo account issued to partners (e.g. NTV360) so they can
evaluate the client portal without reaching real client data and without being
able to change anything.

Three controls live here:

1. **Role gating** — the ``partner`` role is read-only everywhere. Pages hide
   write controls, but :func:`assert_writable` is the control that actually
   enforces it: every write path calls it and it stops the script for partners.
2. **Demo-tenant resolution** — :func:`resolve_access` runs at the shared
   ``load_portal_client()`` choke point so no page can forget to check.
3. **Provenance** — :func:`watermark_label` and :func:`canary_token` produce the
   per-viewer strings stamped into the UI and into every generated document, so
   a leaked file traces back to a specific session.

Schema backing this: ``scripts/024_partner_demo_access.sql``.
"""

import hashlib
from datetime import datetime, timezone

import streamlit as st

PARTNER_ROLE = "partner"

# Session keys written by resolve_access().
_SK_IS_PARTNER = "_partner_is_partner"
_SK_IS_DEMO = "_partner_is_demo"
_SK_ORG = "_partner_org"
_SK_EXPIRES = "_partner_expires_at"


# ── Role checks ─────────────────────────────────────────────────────────────

def is_partner_role() -> bool:
    """True if the logged-in portal user holds the read-only partner role."""
    return st.session_state.get("portal_role", "") == PARTNER_ROLE


def is_demo_session() -> bool:
    """True if the current session is on a synthetic sandbox tenant.

    Either the role is ``partner`` or the resolved client row is flagged
    ``is_demo``. Both are treated as read-only.
    """
    return bool(
        is_partner_role()
        or st.session_state.get(_SK_IS_PARTNER)
        or st.session_state.get(_SK_IS_DEMO)
    )


def partner_org() -> str:
    """Name of the organization this evaluation account was issued to."""
    return st.session_state.get(_SK_ORG, "") or ""


# ── Access resolution (called from the shared choke point) ──────────────────

def resolve_access(user: dict, client: dict) -> dict:
    """Resolve and cache demo/partner state for the current portal session.

    Called by ``services.portal_ui.load_portal_client()`` — the one function
    every guarded portal page already goes through — so individual pages cannot
    forget to check.

    Returns the client dict unchanged, for call-site convenience.
    """
    is_partner = (user or {}).get("role", "") == PARTNER_ROLE
    is_demo = bool((client or {}).get("is_demo"))

    st.session_state[_SK_IS_PARTNER] = is_partner
    st.session_state[_SK_IS_DEMO] = is_demo
    st.session_state[_SK_ORG] = (client or {}).get("partner_org", "") or ""
    st.session_state[_SK_EXPIRES] = (client or {}).get("portal_access_expires_at", "") or ""

    return client


def clear_access():
    """Drop cached partner state. Called on logout."""
    for key in (_SK_IS_PARTNER, _SK_IS_DEMO, _SK_ORG, _SK_EXPIRES):
        st.session_state.pop(key, None)


# ── Write enforcement ───────────────────────────────────────────────────────

def can_write() -> bool:
    """False for any read-only evaluation session."""
    return not is_demo_session()


def assert_writable(action: str = "make changes"):
    """Stop the page if the current session is read-only.

    This is the real control — hiding buttons is cosmetic. Call it inside every
    write handler (contract signing, renewal acceptance, creative submission,
    profile saves, NPS) *before* touching the database.
    """
    if can_write():
        return

    org = partner_org() or "your organization"
    st.warning(
        f"This is a read-only evaluation account issued to {org}. "
        f"You cannot {action} from a demo session."
    )
    st.stop()


# ── Provenance ──────────────────────────────────────────────────────────────

def canary_token(user: dict | None = None) -> str:
    """Short, stable, per-viewer trace token.

    Deterministic for a given portal user, so a token found in a leaked
    document can be matched back to the account (and to its rows in
    ``activity_log``) without embedding the raw user id in the file.
    """
    if user is None:
        user = {
            "user_id": st.session_state.get("portal_user_id", ""),
            "email": st.session_state.get("portal_email", ""),
        }

    seed = f"{user.get('user_id', '')}|{user.get('email', '')}".lower()
    if not seed.strip("|"):
        return ""

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10].upper()


def watermark_label(user: dict | None = None) -> str:
    """One-line confidentiality + provenance string.

    Stamped into the in-app banner and into generated document footers and
    metadata, so every artifact a partner can see identifies who saw it.
    """
    if not is_demo_session():
        return ""

    org = partner_org() or "Evaluation Partner"
    email = (user or {}).get("email") or st.session_state.get("portal_email", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    token = canary_token(user)

    parts = [f"CONFIDENTIAL - Evaluation Access - Licensed to {org}"]
    if email:
        parts.append(email)
    parts.append(today)
    if token:
        parts.append(f"ref {token}")

    return "  |  ".join(parts)


def render_partner_banner(user: dict | None = None):
    """Render the persistent evaluation-access banner at the top of a page.

    No-op for normal client sessions.
    """
    if not is_demo_session():
        return

    label = watermark_label(user)
    expires = st.session_state.get(_SK_EXPIRES, "")
    expiry_note = ""
    if expires:
        expiry_note = (
            f'<div style="font-size:0.75rem;opacity:0.85;margin-top:0.2rem;">'
            f'Access expires {str(expires)[:10]}</div>'
        )

    st.markdown(
        f"""
        <div style="background:#1B1F3B;border-left:5px solid #C5A55A;
                    padding:0.6rem 0.9rem;margin-bottom:1rem;border-radius:4px;">
          <div style="color:#C5A55A;font-size:0.8rem;font-weight:700;
                      letter-spacing:0.04em;">{label}</div>
          <div style="color:#fff;font-size:0.78rem;margin-top:0.25rem;">
            Sample data only. This account is read-only and is provided under a
            confidentiality and evaluation agreement.
          </div>{expiry_note}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Evaluation terms acceptance ─────────────────────────────────────────────

# Bump when the evaluation terms text changes — acceptance is recorded per
# version, so a change re-prompts rather than silently inheriting consent.
PARTNER_TERMS_VERSION = "2026-07-24"
_TERMS_KIND = "partner_evaluation"


def has_accepted_terms(user: dict | None = None,
                       version: str = PARTNER_TERMS_VERSION) -> bool:
    """True if this user has an acceptance row for the current terms version.

    Fails closed: if the record can't be read, the user is treated as not
    having accepted. Consent must be proven, not assumed.
    """
    user_id = (user or {}).get("user_id") or st.session_state.get("portal_user_id", "")
    if not user_id:
        return False

    cache_key = f"_terms_accepted_{version}"
    if st.session_state.get(cache_key):
        return True

    try:
        from services.supabase_client import query_table

        rows = query_table(
            "portal_terms_acceptances",
            select="id",
            filters={
                "user_id": user_id,
                "terms_kind": _TERMS_KIND,
                "terms_version": version,
            },
            limit=1,
        ) or []
    except Exception as e:
        print(f"[partner_access] Terms lookup failed: {e}")
        return False

    accepted = bool(rows)
    if accepted:
        st.session_state[cache_key] = True
    return accepted


def record_terms_acceptance(user: dict | None = None,
                            version: str = PARTNER_TERMS_VERSION) -> bool:
    """Persist proof that this user accepted the evaluation terms."""
    from services.auth import get_client_ip, log_portal_event

    user = user or {
        "user_id": st.session_state.get("portal_user_id", ""),
        "email": st.session_state.get("portal_email", ""),
    }
    user_id = user.get("user_id", "")
    if not user_id:
        return False

    try:
        from services.supabase_client import insert_row

        user_agent = ""
        try:
            headers = getattr(st.context, "headers", {}) or {}
            user_agent = headers.get("User-Agent", "")[:500]
        except Exception:
            pass

        row = insert_row("portal_terms_acceptances", {
            "user_id": user_id,
            "client_id": st.session_state.get("_portal_client_id", "") or None,
            "email": user.get("email", ""),
            "terms_version": version,
            "terms_kind": _TERMS_KIND,
            "ip_address": get_client_ip(),
            "user_agent": user_agent,
        })
    except Exception as e:
        print(f"[partner_access] Could not record terms acceptance: {e}")
        return False

    if row:
        st.session_state[f"_terms_accepted_{version}"] = True
        log_portal_event("partner_terms_accepted",
                         details={"terms_version": version, "org": partner_org()})
        return True
    return False


def require_terms_acceptance(user: dict | None = None):
    """Send un-accepted evaluation sessions to the terms page.

    No-op for normal client sessions and for partners who have already
    accepted the current version.
    """
    if not is_demo_session():
        return
    if has_accepted_terms(user):
        return

    st.switch_page("pages/portal_partner_terms.py")


# ── Demo performance figures ────────────────────────────────────────────────

# Synthetic network numbers shown to demo sessions in place of real NTV360
# snapshot data. Plausible for a demo, deliberately not MCTV's real figures.
_DEMO_MONTHLY_PLAYS = 48_000
_DEMO_IMPRESSIONS_PER_PLAY = 60


def demo_live_performance(total_screens: int = 0) -> dict:
    """Synthetic stand-in for ``_compute_live_performance``.

    Demo sessions must never see real network-wide NTV360 totals.
    """
    from datetime import date

    today = date.today()
    trend = []
    for offset in range(5, -1, -1):
        month = (today.month - offset - 1) % 12 + 1
        year = today.year + ((today.month - offset - 1) // 12)
        plays = _DEMO_MONTHLY_PLAYS + (offset * 1_400)
        trend.append({
            "month": f"{year:04d}-{month:02d}",
            "plays": plays,
            "impressions": plays * _DEMO_IMPRESSIONS_PER_PLAY,
        })

    last_month_plays = trend[-2]["plays"] if len(trend) > 1 else _DEMO_MONTHLY_PLAYS
    mtd = int(_DEMO_MONTHLY_PLAYS * min(today.day / 30, 1.0))

    return {
        "mtd_plays_estimated": mtd,
        "mtd_impressions_estimated": mtd * _DEMO_IMPRESSIONS_PER_PLAY,
        "last_month_plays": last_month_plays,
        "last_month_impressions": last_month_plays * _DEMO_IMPRESSIONS_PER_PLAY,
        "contract_to_date_plays": sum(t["plays"] for t in trend),
        "trend": trend,
        "snapshot_month": trend[-2]["month"] if len(trend) > 1 else "",
        "data_source": "demo",
    }
