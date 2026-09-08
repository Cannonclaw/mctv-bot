# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sales pipeline service for opportunity tracking and revenue forecasting.

Manages the full sales pipeline from prospect to close, with stage tracking,
revenue forecasting, and pipeline analytics. Uses Supabase REST API with
local JSON fallback.
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "pipeline"


# ── Shared helpers ────────────────────────────────────────────────────────────

def local_today() -> date:
    """Today in MCTV's timezone (America/Chicago), not the server's UTC.

    Render runs in UTC, so the plain stdlib "today" rolls over at 6-7 PM
    Central — a deal closed on a Tuesday evening would be dated Wednesday
    and land in the wrong month at a month boundary.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago")).date()
    except Exception:  # tzdata missing in the image — fall back to fixed CST
        return (datetime.now(timezone.utc) - timedelta(hours=6)).date()


def _num(value) -> float:
    """Coerce a money/count field to float, whatever the API handed back.

    PostgREST serialises Postgres `numeric` columns as JSON *strings*
    ("1300.00") to preserve precision, and blank form fields arrive as None
    or "". Every arithmetic site in this module goes through here, so a null
    or a string can never crash a total or silently drop a deal out of one.
    """
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _day(value) -> str:
    """Normalise a date/timestamp field to a bare YYYY-MM-DD string ("" if unset)."""
    if not value:
        return ""
    return str(value)[:10]


def month_start(d: date, offset: int = 0) -> date:
    """First day of the month `offset` months from `d`."""
    m = d.month - 1 + offset
    return date(d.year + m // 12, m % 12 + 1, 1)

# ── Stage Configuration ──────────────────────────────────────────────────────

STAGES = {
    "prospect":      {"label": "Prospect",       "probability": 10, "color": "#6c757d", "order": 0},
    "outreach":      {"label": "Outreach",        "probability": 15, "color": "#17a2b8", "order": 1},
    "engaged":       {"label": "Engaged",         "probability": 30, "color": "#007bff", "order": 2},
    "discovery":     {"label": "Discovery",       "probability": 45, "color": "#6610f2", "order": 3},
    "proposal_sent": {"label": "Proposal Sent",   "probability": 60, "color": "#C5A55A", "order": 4},
    "negotiation":   {"label": "Negotiation",     "probability": 75, "color": "#fd7e14", "order": 5},
    "contract_sent": {"label": "Contract Sent",   "probability": 90, "color": "#28a745", "order": 6},
    "won":           {"label": "Won",             "probability": 100, "color": "#155724", "order": 7},
    "lost":          {"label": "Lost",            "probability": 0,   "color": "#dc3545", "order": 8},
}

# Tier pricing for quick-select
TIERS = {
    "10 Screens":  {"screens": 10, "monthly": 350},
    "20 Screens":  {"screens": 20, "monthly": 500},
    "40 Screens":  {"screens": 40, "monthly": 800},
    "75+ Screens": {"screens": 75, "monthly": 1300},
}

# Stages where the deal is decided and the money is no longer "pipeline".
CLOSED_STAGES = ("won", "lost")

# Pricing modes. Most deals are a stock tier, but plenty of real submitted
# proposals never fit one — they have run $3,850, $4,950/mo, $2,000 flat for a
# project, and $21,000 for a political flight. `pricing_mode` says which fields
# are authoritative:
#   'tier'   → tier_name is a key of TIERS; monthly_value mirrors that tier
#   'custom' → tier_name is a free-text package name and monthly_value,
#              one_time_value, screen_count and term_months were entered by hand
PRICING_MODES = ("tier", "custom")

# ── Follow-up SLA (accountability) ───────────────────────────────────────────
# The strict follow-up schedule: max days between touches per stage, and the
# default next action scheduled automatically whenever a deal enters a stage.
# Every open deal always has a next action + date — no deal sits untouched.
FOLLOW_UP_SLA = {
    "prospect":      {"days": 7, "action": "Make first outreach"},
    "outreach":      {"days": 3, "action": "Follow up on outreach"},
    "engaged":       {"days": 3, "action": "Book discovery conversation"},
    "discovery":     {"days": 2, "action": "Send proposal"},
    "proposal_sent": {"days": 2, "action": "Follow up on proposal"},
    "negotiation":   {"days": 1, "action": "Close the negotiation"},
    "contract_sent": {"days": 1, "action": "Chase contract signature"},
}


# ── Supabase REST helpers ─────────────────────────────────────────────────────

def _sb_config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url, key
    return None, None


def _sb_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


class PipelineWriteError(RuntimeError):
    """A write to Supabase was rejected. Never swallow this on a live app.

    The local-JSON fallback below exists so the app runs on a dev box with no
    secrets. It must NOT catch production failures: on Render the container
    disk is ephemeral and get_all_opportunities() reads Supabase whenever it
    answers, so a row written to local JSON is gone on the next deploy while
    the UI has already said "Saved!". A rejected write has to be loud.
    """


def _sb_configured() -> bool:
    return bool(_sb_config()[0])


def _sb_request(method: str, endpoint: str, data: dict | None = None,
                raise_on_error: bool = False) -> list | None:
    """Call the Supabase REST API.

    Returns the decoded rows, or None when Supabase is unreachable/not
    configured. With raise_on_error=True a configured-but-failing request
    raises PipelineWriteError instead of returning None, so callers can tell
    "no database here" apart from "the database said no".
    """
    url, key = _sb_config()
    if not url:
        return None

    full_url = f"{url}/rest/v1/{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(full_url, data=body, headers=_sb_headers(key), method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:300]
        logger.error("Pipeline REST %s %s HTTP %s: %s", method, endpoint, e.code, err)
        if raise_on_error:
            raise PipelineWriteError(f"HTTP {e.code}: {err}") from e
        return None
    except Exception as e:
        logger.error("Pipeline REST %s %s failed: %s", method, endpoint, e)
        if raise_on_error:
            raise PipelineWriteError(str(e)) from e
        return None


# ── Local JSON fallback ───────────────────────────────────────────────────────

def _local_file() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "opportunities.json"


def _local_activity_file() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "activity.json"


def _load_local() -> list[dict]:
    path = _local_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_local(data: list[dict]):
    path = _local_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_local_activity() -> list[dict]:
    path = _local_activity_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_local_activity(data: list[dict]):
    path = _local_activity_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_opportunity(opp_data: dict) -> dict | None:
    """Create a new pipeline opportunity.

    Args:
        opp_data: Dict with business_name (required) and optional fields:
            contact_name, contact_email, contact_phone, industry, city,
            source, stage, monthly_value, screen_count, tier_name,
            expected_close_date, assigned_rep, notes, tags

    Backdating: pass `created_at` (and, for an already-decided deal,
    `closed_date` plus stage 'won'/'lost') to log a deal that happened months
    ago. Historical deals are entered exactly like current ones — the only
    difference is that the dates are yours instead of today's.

    Returns:
        The created opportunity dict, or None on failure.
    """
    # Backstop for every create path in the app (Add Deal, Prospector batch
    # paste, lead import, host forms). Enforced here so no call site can skip
    # it, and so the cleaned name is what actually gets stored.
    ok, cleaned, reason = validate_business_name(opp_data.get("business_name", ""))
    if not ok and not opp_data.pop("_force_name", False):
        raise ValueError(f"{reason}: {opp_data.get('business_name', '')!r}")
    opp_data.pop("_force_name", None)
    opp_data["business_name"] = cleaned

    now = datetime.now(timezone.utc).isoformat()
    opp_data.setdefault("stage", "prospect")
    opp_data.setdefault("source", "manual")
    opp_data.setdefault("probability", STAGES.get(opp_data["stage"], {}).get("probability", 10))
    opp_data.setdefault("assigned_rep", "Mary Michael")
    opp_data.setdefault("created_at", now)
    opp_data.setdefault("updated_at", now)

    # A deal entered straight into won/lost is history, not a live deal: date
    # the close, and never leave a phantom follow-up hanging off it.
    if opp_data["stage"] in CLOSED_STAGES:
        opp_data.setdefault("closed_date", _day(opp_data.get("created_at")) or local_today().isoformat())
        opp_data.setdefault("stage_entered_at", opp_data["closed_date"])
        opp_data["next_action"] = None
        opp_data["next_action_date"] = None

    # Accountability: every new OPEN deal starts with a scheduled follow-up
    sla = FOLLOW_UP_SLA.get(opp_data["stage"])
    if sla and not opp_data.get("next_action_date"):
        opp_data["next_action"] = opp_data.get("next_action") or sla["action"]
        opp_data["next_action_date"] = (local_today() + timedelta(days=sla["days"])).isoformat()

    # Try Supabase. A configured-but-failing write raises rather than
    # silently landing in local JSON that the next deploy throws away.
    result = _sb_request("POST", "pipeline_opportunities", opp_data,
                         raise_on_error=_sb_configured())
    if result and len(result) > 0:
        _log_activity(result[0]["id"], "created", details=f"Added to pipeline: {opp_data.get('business_name', '')}")
        return result[0]

    # Fallback: local JSON (dev box with no Supabase secrets)
    import uuid
    opp_data["id"] = str(uuid.uuid4())
    opps = _load_local()
    opps.insert(0, opp_data)
    _save_local(opps)
    _log_activity(opp_data["id"], "created", details=f"Added to pipeline: {opp_data.get('business_name', '')}")
    return opp_data


def get_all_opportunities(stage: str | None = None, city: str | None = None,
                          assigned_rep: str | None = None,
                          deal_type: str | None = "advertiser") -> list[dict]:
    """Get pipeline opportunities with optional filters.

    Defaults to the advertiser (sales) pipeline. The host pipeline shares the
    pipeline_opportunities table (deal_type='host') but uses a different stage
    vocabulary (e.g. 'identified'), so mixing the two breaks the sales views.
    Pass deal_type=None to fetch every deal type, or 'host' for host deals.
    """
    endpoint = "pipeline_opportunities?select=*&order=updated_at.desc"

    if stage:
        endpoint += f"&stage=eq.{stage}"
    if city:
        endpoint += f"&city=eq.{city}"
    if assigned_rep:
        endpoint += f"&assigned_rep=eq.{assigned_rep}"
    if deal_type:
        endpoint += f"&deal_type=eq.{deal_type}"

    result = _sb_request("GET", endpoint)
    if result is not None:
        return result

    # Fallback: local
    opps = _load_local()
    if stage:
        opps = [o for o in opps if o.get("stage") == stage]
    if city:
        opps = [o for o in opps if (o.get("city") or "").lower() == city.lower()]
    if assigned_rep:
        opps = [o for o in opps if o.get("assigned_rep") == assigned_rep]
    if deal_type:
        opps = [o for o in opps if (o.get("deal_type") or "advertiser") == deal_type]
    return opps


def get_opportunity(opp_id: str) -> dict | None:
    """Get a single opportunity by ID."""
    result = _sb_request("GET", f"pipeline_opportunities?id=eq.{opp_id}&limit=1")
    if result and len(result) > 0:
        return result[0]

    opps = _load_local()
    for o in opps:
        if o.get("id") == opp_id:
            return o
    return None


def update_opportunity(opp_id: str, updates: dict) -> dict | None:
    """Update fields on an opportunity."""
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = _sb_request("PATCH", f"pipeline_opportunities?id=eq.{opp_id}", updates,
                         raise_on_error=_sb_configured())
    if result and len(result) > 0:
        return result[0]

    # Fallback: local
    opps = _load_local()
    for o in opps:
        if o.get("id") == opp_id:
            o.update(updates)
            _save_local(opps)
            return o
    return None


# ── Deletion (with an undo trail) ────────────────────────────────────────────
# A duplicate or a junk row is not a lost deal. Marking it "lost" poisons the
# win rate and the lost-revenue total forever, so the pipeline deletes it
# instead. Every delete is snapshotted to `pipeline_deleted` first — including
# the activity trail, which the FK would otherwise cascade away — so a wrong
# delete is one click from coming back.

def delete_opportunity(opp_id: str, deleted_by: str = "MCTV Bot",
                       reason: str = "", archive: bool = True,
                       merged_into: str | None = None) -> bool:
    """Delete an opportunity outright, archiving it first so it can be restored.

    Args:
        opp_id: The opportunity to remove.
        deleted_by: Rep name recorded on the archive row.
        reason: Why it went ("duplicate", "junk row", "test data", ...).
        archive: Snapshot to `pipeline_deleted` before deleting. Only pass
            False when the caller has already archived the row itself.
        merged_into: When this row lost a merge, the id of the surviving deal.

    Returns:
        True only if a row was actually removed.

    The old version returned True unconditionally. Because every request
    sends `Prefer: return=representation`, a DELETE that matched nothing
    comes back as `[]` — not None — so the caller was told the delete
    succeeded when no row had been touched. The UI would have confirmed
    deletions that never happened. Count the returned rows instead.
    """
    opp = get_opportunity(opp_id)
    if not opp:
        return False

    # Archive FIRST, and refuse to delete if the archive did not take. A
    # delete that silently skipped its snapshot is unrecoverable, and the
    # undo list would look legitimately empty afterwards.
    if archive and not _archive_opportunity(
            opp, deleted_by=deleted_by, reason=reason, merged_into=merged_into):
        raise PipelineWriteError(
            "Could not archive this deal, so it was not deleted. "
            "Nothing was lost — try again."
        )

    if _sb_configured():
        result = _sb_request("DELETE", f"pipeline_opportunities?id=eq.{opp_id}",
                             raise_on_error=True)
        if not result:
            return False
        _cleanup_references(opp_id, opp)
        return True

    opps = _load_local()
    before = len(opps)
    opps = [o for o in opps if o.get("id") != opp_id]
    _save_local(opps)
    activity = [a for a in _load_local_activity() if a.get("opportunity_id") != opp_id]
    _save_local_activity(activity)
    return len(opps) < before


def _cleanup_references(opp_id: str, opp: dict) -> None:
    """Clear pointers that no foreign key would clean up on its own.

    Only pipeline_activity has an FK (ON DELETE CASCADE). Two other tables
    hold a bare uuid:

      tasks.source_id           — a stalled-deal task whose deal is gone would
                                  otherwise reappear in the 7am email forever.
      contract_requests.opportunity_id — a signed agreement would keep a
                                  dangling id; the row itself must survive, so
                                  the pointer is nulled, not the record.

    Best-effort: a failure here must never strand an already-deleted deal.
    """
    try:
        _sb_request("DELETE",
                    f"tasks?source=eq.stalled_deal&source_id=eq.{opp_id}")
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not clear tasks for deleted deal %s: %s", opp_id, e)

    try:
        _sb_request("PATCH",
                    f"contract_requests?opportunity_id=eq.{opp_id}",
                    {"opportunity_id": None})
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not clear contract_requests for %s: %s", opp_id, e)


def _archive_opportunity(opp: dict, deleted_by: str = "MCTV Bot",
                         reason: str = "", merged_into: str | None = None) -> bool:
    """Snapshot a deal and its activity into `pipeline_deleted`."""
    record = {
        "opportunity_id": opp.get("id"),
        "business_name": opp.get("business_name") or "(unnamed)",
        "deal_type": opp.get("deal_type") or "advertiser",
        "stage": opp.get("stage"),
        "monthly_value": _num(opp.get("monthly_value")),
        "deal_data": opp,
        "activity_data": get_activity(opp.get("id"), limit=500),
        "deleted_by": deleted_by,
        "deleted_reason": reason,
        "merged_into": merged_into,
    }
    result = _sb_request("POST", "pipeline_deleted", record)
    if result is not None:
        return True
    logger.warning("Could not archive opportunity %s before delete", opp.get("id"))
    return False


def get_deleted(limit: int = 100) -> list[dict]:
    """Recently deleted deals, newest first — the undo list."""
    result = _sb_request(
        "GET", f"pipeline_deleted?select=*&order=deleted_at.desc&limit={limit}")
    return result if result is not None else []


def restore_opportunity(archive_id: str, performed_by: str = "MCTV Bot") -> dict | None:
    """Put an archived deal back in the pipeline, activity trail and all.

    The original id is reused, so anything that still references the deal
    lines back up. Returns the restored opportunity, or None if the archive
    row is missing or the insert failed.
    """
    rows = _sb_request("GET", f"pipeline_deleted?id=eq.{archive_id}&limit=1")
    if not rows:
        return None

    archived = rows[0]
    deal = dict(archived.get("deal_data") or {})
    if not deal.get("id"):
        return None

    restored = _sb_request("POST", "pipeline_opportunities", deal)
    if not restored:
        return None

    # Activity rows carry their own ids; re-insert them so the history
    # survives the round trip. Best-effort — a failure here must not
    # strand the restored deal.
    for act in (archived.get("activity_data") or []):
        _sb_request("POST", "pipeline_activity", act)

    _sb_request("DELETE", f"pipeline_deleted?id=eq.{archive_id}")
    _log_activity(deal["id"], "restored",
                  details=f"Restored from deleted (was: {archived.get('deleted_reason') or 'no reason given'})",
                  performed_by=performed_by)
    return restored[0]


def purge_deleted(archive_id: str) -> bool:
    """Permanently drop an archived deal. There is no undo past this."""
    return bool(_sb_request("DELETE", f"pipeline_deleted?id=eq.{archive_id}",
                            raise_on_error=_sb_configured()))


def deleted_fingerprints() -> tuple[set, set]:
    """Name keys and lead ids of deals that were deliberately deleted.

    Cleaning up is pointless if the deleted rows walk straight back in. Both
    re-entry paths key off what is currently in the pipeline: Import Leads
    treats a lead as importable once its opportunity is gone, and the
    Prospector re-enables a prospect once its name is gone. Feeding these
    sets into both keeps a deletion deleted until someone restores it.

    Returns (name_keys, lead_ids). Rows deleted by a merge are excluded —
    the survivor is still in the pipeline under that name.
    """
    names, leads = set(), set()
    for row in get_deleted(limit=500):
        if row.get("merged_into"):
            continue
        key = normalize_name(row.get("business_name", ""))
        if key:
            names.add(key)
        lead_id = (row.get("deal_data") or {}).get("lead_id")
        if lead_id:
            leads.add(lead_id)
    return names, leads


# ── Data hygiene: duplicates, junk rows, merges ──────────────────────────────

# Words that only ever show up when a note or a contact line got pasted into
# the business-name box. Matched on the whole name, never inside one, so real
# businesses ("The Pants Store", "Something Southern") are never touched.
_JUNK_NAME_PREFIXES = (
    "pitched", "called", "emailed", "spoke", "left voicemail", "followed up",
    "follow up", "sent", "met with", "meeting", "note", "notes", "no answer",
    "contact", "owner", "manager", "director", "president",
)
_TITLE_LINE = re.compile(
    r"^(marketing|sales|general|managing|creative|operations|regional)?\s*"
    r"(director|manager|owner|president|vp|coordinator|contact|rep)\s*:",
    re.IGNORECASE,
)
_DATE_ISH = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b",
    re.IGNORECASE,
)


_LEGAL_SUFFIXES = {
    "inc", "incorporated", "llc", "llp", "lp", "ltd", "limited", "co",
    "company", "corp", "corporation", "pllc", "pc", "pa",
}


def normalize_name(name: str) -> str:
    """Reduce a business name to a canonical key for duplicate detection.

    Collapses the noise that makes one business look like two — case,
    punctuation, accents, curly quotes, trailing legal suffixes, and the
    stray trailing space that let "Enterprise tupelo " and "Enterprise
    Tupelo" both get created. Deliberately conservative:

      - city and descriptor words are KEPT, so "St. Jude Dream Home - Oxford"
        and "... - Tupelo" stay distinct rows;
      - only TRAILING legal suffixes are dropped, so "Enterprise" survives in
        "Enterprise Tupelo".
    """
    import unicodedata

    raw = unicodedata.normalize("NFKD", name or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    key = raw.casefold()
    key = key.replace("’", "'").replace("‘", "'")
    key = key.replace("–", "-").replace("—", "-")
    key = key.replace("&", " and ")
    key = key.replace("'", "")                 # joe's -> joes
    key = re.sub(r"[^a-z0-9]+", " ", key)      # fuse.cloud -> fuse cloud
    words = key.split()

    if words and words[0] == "the":
        words = words[1:]
    while len(words) > 1 and words[-1] in _LEGAL_SUFFIXES:
        words.pop()

    return " ".join(words)


# Labels and job titles that mean a contact line got pasted into the name box.
_LABEL_LINE = re.compile(
    r"(?i)^\s*(contact(\s+name)?|name|owner|manager|gm|general\s+manager|"
    r"marketing\s+director|director\s+of\s+marketing|marketing\s+manager|"
    r"e-?mail|phone|tel|telephone|cell|mobile|address|website|url|notes?|"
    r"follow[-\s]?up|next\s+steps?|status|budget|rep|source|title|position|"
    r"role|decision\s+maker|poc|point\s+of\s+contact)\s*:"
)
_TITLE_COLON = re.compile(
    r"(?i)^[A-Za-z][A-Za-z /&.\-]{2,40}"
    r"(director|manager|owner|president|vp|vice\s+president|ceo|cfo|cmo|coo|"
    r"partner|principal|coordinator|supervisor|administrator|officer|broker|"
    r"agent)\s*:"
)
_ACTIVITY_NOTE = re.compile(
    r"(?i)^(pitched|called|emailed|e-mailed|texted|spoke|talked|visited|"
    r"met\s+with|meeting\s+with|followed\s+up|follow\s+up\s+with|stopped\s+by|"
    r"dropped\s+by|left\s+(a\s+)?message|voicemail|no\s+answer|"
    r"waiting\s+(on|for)|needs?\s+to|needed\s+to|will\s+(call|follow)|"
    r"sent\s+(the\s+)?(proposal|contract|email|deck))\b"
)
_MONTH_DAY = re.compile(
    r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b"
)
_NUMERIC_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
# Deliberately a SHORT list. A full TLD list would reject "Fuse.Cloud".
_BARE_DOMAIN = re.compile(r"(?i)\.(com|net|org|biz|info)$")
_PLACEHOLDERS = {
    "unknown", "n/a", "na", "none", "tbd", "test", "testing", "asdf",
    "business name", "name", "owner", "home", "welcome", "index",
    "untitled", "-", "--", "?", "x",
}


def validate_business_name(name: str) -> tuple[bool, str, str]:
    """Gate the business-name field before a deal can be created.

    Junk rows like "drew@brockpartners.com", "Marketing Director: Drew
    Langford" and "Pitched to Drew July 22, 2026" reached the pipeline
    because the only check anywhere was "is the string non-empty" — then got
    marked lost, which is what poisoned the win rate.

    Returns (ok, cleaned, reason). `cleaned` has its whitespace collapsed, so
    saving through this permanently kills the trailing-space duplicates
    ("Enterprise tupelo " vs "Enterprise Tupelo") at the source.
    """
    cleaned = " ".join((name or "").split())

    if len(cleaned) < 2:
        return False, cleaned, "Business name is required"
    if not re.search(r"[A-Za-z]", cleaned):
        return False, cleaned, "A business name has to contain letters"
    if re.search(r"\S@[\w.-]+\.[A-Za-z]{2,}", cleaned):
        return False, cleaned, "That's an email address - put it in Contact Email"
    if re.match(r"(?i)^(https?://|www\.)", cleaned) or (
            " " not in cleaned and _BARE_DOMAIN.search(cleaned)):
        return False, cleaned, "That's a website - put it in the Website field"
    if re.fullmatch(r"[\d\s().+\-]{7,}", cleaned) and len(re.findall(r"\d", cleaned)) >= 7:
        return False, cleaned, "That's a phone number - put it in Contact Phone"
    if _LABEL_LINE.match(cleaned) or _TITLE_COLON.match(cleaned):
        return False, cleaned, "That's a contact detail, not a business name"
    if _ACTIVITY_NOTE.match(cleaned):
        return False, cleaned, "That's an activity note - put it in Notes"
    if _MONTH_DAY.search(cleaned) or _NUMERIC_DATE.search(cleaned):
        return False, cleaned, "That contains a date - put it in Notes"
    if cleaned.casefold() in _PLACEHOLDERS:
        return False, cleaned, f"'{cleaned}' isn't a real business name"
    if len(cleaned) > 80 or len(cleaned.split()) > 14:
        return False, cleaned, "Too long - that looks like a pasted sentence"

    return True, cleaned, ""


def looks_like_junk(name: str) -> str:
    """Explain why a business name looks like a pasted note, or "" if it's fine.

    Catches exactly the shapes that leaked in through the Prospector's
    line-splitting paste box — a bare email address, a "Marketing Director:
    Drew Langford" contact line, a "Pitched to Drew July 22, 2026" activity
    note. Legitimate names with punctuation and parentheses
    ("Neel-Schaffer, Inc.", "Natchez-Adams County Airport (Hardy-Anders
    Field / HEZ)", "Fuse.Cloud", "mTrade") pass clean.
    """
    raw = (name or "").strip()
    if not raw:
        return "Blank business name"
    if "@" in raw and " " not in raw:
        return "Looks like an email address, not a business"
    if raw.startswith(("http://", "https://", "www.")):
        return "Looks like a URL, not a business"
    if _TITLE_LINE.match(raw):
        return "Looks like a contact line (job title + name)"

    first = raw.split()[0].lower().rstrip(":,")
    if first in _JUNK_NAME_PREFIXES and len(raw.split()) > 2:
        return f"Starts with '{first}' — looks like an activity note"
    if _DATE_ISH.search(raw) and len(raw.split()) > 3:
        return "Contains a date — looks like a note, not a name"
    if len(raw) > 90:
        return "Unusually long — looks like a pasted sentence"
    return ""


def find_duplicate_groups(opps: list[dict] | None = None) -> list[dict]:
    """Group opportunities that are almost certainly the same business.

    Returns one dict per group, richest first:
        {key, name, deals: [...], has_conflict: bool}
    `has_conflict` is True when the group's rows disagree about stage — those
    need a human to pick the survivor, because one of them is the real
    outcome and the other is a stale copy.
    """
    if opps is None:
        opps = get_all_opportunities()

    groups: dict[str, list[dict]] = {}
    for o in opps:
        key = normalize_name(o.get("business_name", ""))
        if not key:
            continue
        groups.setdefault(key, []).append(o)

    out = []
    for key, deals in groups.items():
        if len(deals) < 2:
            continue
        stages = {d.get("stage") for d in deals}
        deals = sorted(deals, key=lambda d: (
            -STAGES.get(d.get("stage", ""), {}).get("order", 0),
            _day(d.get("created_at")),
        ))
        out.append({
            "key": key,
            "name": deals[0].get("business_name", key),
            "deals": deals,
            "has_conflict": len(stages) > 1,
        })

    out.sort(key=lambda g: (-len(g["deals"]), g["name"]))
    return out


def find_junk_rows(opps: list[dict] | None = None) -> list[dict]:
    """Opportunities whose business name looks like pasted note text.

    Each returned deal carries a `_junk_reason` explaining the call.
    """
    if opps is None:
        opps = get_all_opportunities()
    flagged = []
    for o in opps:
        reason = looks_like_junk(o.get("business_name", ""))
        if reason:
            o["_junk_reason"] = reason
            flagged.append(o)
    return flagged


def merge_opportunities(keep_id: str, merge_ids: list[str],
                        performed_by: str = "MCTV Bot",
                        fill_blanks: bool = True) -> dict | None:
    """Fold duplicate rows into one surviving deal.

    The losers' activity history is re-pointed at the survivor before they are
    deleted, so nothing about the relationship is lost — only the double
    counting is. With `fill_blanks`, any field the survivor left empty is
    filled from a duplicate, so merging never throws away a phone number.

    Returns the surviving opportunity, or None if it could not be found.
    """
    keeper = get_opportunity(keep_id)
    if not keeper:
        return None

    merge_ids = [mid for mid in merge_ids if mid and mid != keep_id]
    if not merge_ids:
        return keeper

    # Fields that describe the SURVIVOR's own identity and outcome. Copying
    # any of these off a duplicate would rewrite the deal: merging a lost
    # duplicate into a won deal must not import the loss reason or re-date
    # the win, and a $0 partnership must not inherit a junk row's price.
    _SKIP = {"id", "created_at", "updated_at", "deal_type", "stage",
             "probability", "stage_entered_at", "closed_date", "loss_reason",
             "business_name", "monthly_value", "one_time_value", "tier_name",
             "pricing_mode", "screen_count", "term_months",
             "excluded_from_stats", "exclusion_reason"}

    def _blank(v) -> bool:
        """Empty for merge purposes. Deliberately NOT a `v in (None,"",0,...)`
        test: in Python `0 == False`, so that would treat a real $0 value and
        a real `False` flag as missing and overwrite them."""
        return v is None or v == "" or v == [] or v == {}

    filled: dict = {}
    merged_names = []

    for mid in merge_ids:
        loser = get_opportunity(mid)
        if not loser:
            continue
        merged_names.append(loser.get("business_name", mid))

        if fill_blanks:
            for field, value in loser.items():
                if field in _SKIP or _blank(value):
                    continue
                if _blank(keeper.get(field)) and field not in filled:
                    filled[field] = value

        # Archive BEFORE re-pointing the activity, or the snapshot captures an
        # already-empty history and undoing the merge restores a bare row.
        if not _archive_opportunity(
                loser, deleted_by=performed_by,
                reason=f"Merged into {keeper.get('business_name', keep_id)}",
                merged_into=keep_id):
            raise PipelineWriteError(
                f"Could not archive {loser.get('business_name', mid)}, so the "
                "merge was stopped. Nothing was changed."
            )

        # Re-point the loser's history at the survivor BEFORE the delete —
        # the FK cascades, so anything still attached would be destroyed.
        _sb_request("PATCH", f"pipeline_activity?opportunity_id=eq.{mid}",
                    {"opportunity_id": keep_id})

        delete_opportunity(mid, deleted_by=performed_by, archive=False,
                           reason=f"Merged into {keeper.get('business_name', keep_id)}",
                           merged_into=keep_id)

    if filled:
        keeper = update_opportunity(keep_id, filled) or keeper

    _log_activity(keep_id, "merged",
                  details=f"Merged {len(merged_names)} duplicate(s): {', '.join(merged_names)}",
                  performed_by=performed_by)
    return keeper


# ── Pricing ───────────────────────────────────────────────────────────────────

def tier_payload(tier_name: str) -> dict:
    """The stock-tier pricing fields for a TIERS key."""
    tier = TIERS.get(tier_name) or {}
    return {
        "pricing_mode": "tier",
        "tier_name": tier_name,
        "screen_count": tier.get("screens", 0),
        "monthly_value": tier.get("monthly", 0),
        "one_time_value": 0,
    }


def custom_payload(package_name: str, monthly_value: float = 0,
                   one_time_value: float = 0, screen_count: int = 0,
                   term_months: int | None = None) -> dict:
    """Pricing fields for a proposal that doesn't fit a stock tier.

    `monthly_value` is recurring revenue; `one_time_value` is a flat project
    or flight fee that must never be counted as MRR.
    """
    return {
        "pricing_mode": "custom",
        "tier_name": (package_name or "Custom package").strip(),
        "screen_count": int(screen_count or 0),
        "monthly_value": float(monthly_value or 0),
        "one_time_value": float(one_time_value or 0),
        "term_months": int(term_months) if term_months else None,
    }


def total_contract_value(opp: dict) -> float:
    """Full value of the deal: monthly rate over the term, plus any flat fee.

    Falls back to a single month when no term is recorded, so a deal without
    a term is never counted as if it were free.
    """
    months = opp.get("term_months")
    try:
        months = int(months) if months else 1
    except (TypeError, ValueError):
        months = 1
    return _num(opp.get("monthly_value")) * max(months, 1) + _num(opp.get("one_time_value"))


def counted(opps: list[dict]) -> list[dict]:
    """Drop deals the team flagged as not-real-revenue before doing any math.

    Partnerships, barters and $0 placeholders can stay in the pipeline for
    visibility without dragging down win rate or average deal size.
    """
    return [o for o in opps if not o.get("excluded_from_stats")]


# ── Stage Management ──────────────────────────────────────────────────────────

def advance_stage(opp_id: str, new_stage: str, performed_by: str = "MCTV Bot") -> dict | None:
    """Move an opportunity to a new stage with automatic probability update."""
    opp = get_opportunity(opp_id)
    if not opp:
        return None

    old_stage = opp.get("stage", "prospect")
    if old_stage == new_stage:
        return opp

    stage_info = STAGES.get(new_stage, {})
    updates = {
        "stage": new_stage,
        "probability": stage_info.get("probability", 10),
        "stage_entered_at": datetime.now(timezone.utc).isoformat(),
    }

    if new_stage in CLOSED_STAGES:
        updates["probability"] = 100 if new_stage == "won" else 0
        # Stamp the close date once. "Won this month" reads this, never
        # updated_at, so editing an old deal can't re-date the win.
        if not opp.get("closed_date"):
            updates["closed_date"] = local_today().isoformat()
        # A decided deal has no next step — leaving one behind puts closed
        # deals in the Action Items list forever.
        updates["next_action"] = None
        updates["next_action_date"] = None
    elif old_stage in CLOSED_STAGES:
        # Reopening a deal: it is live again, so the close date is wrong.
        updates["closed_date"] = None

    # Accountability: entering a stage automatically schedules that stage's
    # follow-up per the SLA — reps never have to remember to set one.
    sla = FOLLOW_UP_SLA.get(new_stage)
    if sla:
        updates["next_action"] = sla["action"]
        updates["next_action_date"] = (local_today() + timedelta(days=sla["days"])).isoformat()

    result = update_opportunity(opp_id, updates)

    _log_activity(opp_id, "stage_change",
                  from_stage=old_stage, to_stage=new_stage,
                  details=f"Moved from {STAGES.get(old_stage, {}).get('label', old_stage)} to {stage_info.get('label', new_stage)}",
                  performed_by=performed_by)

    return result


def mark_lost(opp_id: str, reason: str = "", performed_by: str = "MCTV Bot",
              closed_date: str | None = None) -> dict | None:
    """Mark an opportunity as lost with an optional reason.

    A duplicate or a junk row is NOT a loss — deleting it keeps the win rate
    honest. Use this only for deals that were genuinely pitched and declined.
    """
    opp = get_opportunity(opp_id)
    if not opp:
        return None

    old_stage = opp.get("stage", "prospect")
    updates = {
        "stage": "lost",
        "probability": 0,
        "loss_reason": reason,
        "stage_entered_at": datetime.now(timezone.utc).isoformat(),
        "closed_date": closed_date or opp.get("closed_date") or local_today().isoformat(),
        "next_action": None,
        "next_action_date": None,
    }

    result = update_opportunity(opp_id, updates)

    _log_activity(opp_id, "stage_change",
                  from_stage=old_stage, to_stage="lost",
                  details=f"Lost: {reason}" if reason else "Marked as lost",
                  performed_by=performed_by)

    return result


# ── Activity Logging ──────────────────────────────────────────────────────────

def _log_activity(opp_id: str, action: str, from_stage: str = "",
                  to_stage: str = "", details: str = "",
                  performed_by: str = "MCTV Bot"):
    """Log an activity on a pipeline opportunity."""
    record = {
        "opportunity_id": opp_id,
        "action": action,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "details": details,
        "performed_by": performed_by,
        "created_at": datetime.now().isoformat(),
    }

    result = _sb_request("POST", "pipeline_activity", record)
    if result is not None:
        return

    if _sb_configured():
        # Configured but rejected — almost always an `action` value outside
        # the CHECK constraint. Do NOT fall through to local JSON: that hides
        # the audit trail on a disk the next deploy wipes, which is worst for
        # exactly the destructive actions we most want recorded.
        logger.error("Activity %r on %s was rejected by Supabase and not logged.",
                     action, opp_id)
        return

    # Fallback: local (dev box with no Supabase secrets)
    activity = _load_local_activity()
    import uuid
    record["id"] = str(uuid.uuid4())
    activity.insert(0, record)
    activity = activity[:1000]  # Keep last 1000
    _save_local_activity(activity)


def get_activity(opp_id: str, limit: int = 50) -> list[dict]:
    """Get activity history for an opportunity."""
    result = _sb_request(
        "GET",
        f"pipeline_activity?opportunity_id=eq.{opp_id}&order=created_at.desc&limit={limit}"
    )
    if result is not None:
        return result

    activity = _load_local_activity()
    return [a for a in activity if a.get("opportunity_id") == opp_id][:limit]


def log_note(opp_id: str, note: str, performed_by: str = "MCTV Bot"):
    """Add a note to an opportunity."""
    _log_activity(opp_id, "note_added", details=note, performed_by=performed_by)


def log_call(opp_id: str, notes: str = "", performed_by: str = "MCTV Bot"):
    """Log a phone call on an opportunity."""
    update_opportunity(opp_id, {"last_contact_date": datetime.now().isoformat()})
    _log_activity(opp_id, "call_logged", details=notes, performed_by=performed_by)


def log_event(opp_id: str, action: str, details: str = "",
              performed_by: str = "MCTV Bot"):
    """Log an arbitrary activity event (e.g. 'value_updated' after an edit)."""
    _log_activity(opp_id, action, details=details, performed_by=performed_by)


# ── Lead Conversion ──────────────────────────────────────────────────────────

def import_lead_to_pipeline(lead: dict, source: str = "intake_form") -> dict | None:
    """Convert a lead record into a pipeline opportunity."""
    from services.leads_service import calculate_lead_score

    score = calculate_lead_score(lead)

    # Map lead interest to initial stage
    interest = (lead.get("interest_level") or "").lower()
    if "ready" in interest:
        initial_stage = "discovery"
    elif "very" in interest:
        initial_stage = "engaged"
    elif "interested" in interest:
        initial_stage = "outreach"
    else:
        initial_stage = "prospect"

    # Estimate value based on city/industry
    estimated_monthly = 500  # Default to 20-screen tier
    city = (lead.get("city") or "").lower()
    if city in ("oxford", "starkville", "tupelo"):
        estimated_monthly = 500

    opp_data = {
        "lead_id": lead.get("id", ""),
        "business_name": lead.get("business_name", "Unknown"),
        "contact_name": lead.get("contact_name", ""),
        "contact_email": lead.get("contact_email", ""),
        "contact_phone": lead.get("contact_phone", ""),
        "industry": lead.get("industry", ""),
        "city": lead.get("city", ""),
        "source": source,
        "stage": initial_stage,
        "monthly_value": estimated_monthly,
        "screen_count": 20,
        "tier_name": "20 Screens",
        "expected_close_date": (date.today() + timedelta(days=30)).isoformat(),
        "notes": lead.get("goals", "") or lead.get("additional_notes", ""),
        "nurture_sequence": "new_lead",
        "nurture_step": 0,
    }

    return create_opportunity(opp_data)


# ── Pipeline Analytics ────────────────────────────────────────────────────────

def get_pipeline_summary(opps: list[dict] | None = None) -> dict:
    """Get a summary of the pipeline for the dashboard.

    Pass a pre-fetched opportunity list via `opps` to avoid a redundant
    Supabase round-trip (the Pipeline page fetches once per rerun).

    Returns:
        Dict with total_opportunities, total_pipeline_value,
        weighted_pipeline_value, by_stage (counts + values),
        avg_deal_size, conversion_rate, deals_won_this_month, mrr_won.
    """
    if opps is None:
        opps = get_all_opportunities()

    # Deals flagged "don't count me" never reach the math — that is the whole
    # point of the flag. They stay visible everywhere else.
    scored = counted(opps)

    # Exclude lost/won from active pipeline
    active = [o for o in scored if o.get("stage") not in CLOSED_STAGES]
    won = [o for o in scored if o.get("stage") == "won"]
    lost = [o for o in scored if o.get("stage") == "lost"]

    # By stage
    by_stage = {}
    for stage_key, stage_info in STAGES.items():
        stage_opps = [o for o in scored if o.get("stage") == stage_key]
        value = sum(_num(o.get("monthly_value")) for o in stage_opps)
        by_stage[stage_key] = {
            "count": len(stage_opps),
            "value": value,
            "weighted_value": value * stage_info["probability"] / 100,
            "label": stage_info["label"],
            "color": stage_info["color"],
        }

    total_value = sum(_num(o.get("monthly_value")) for o in active)
    weighted_value = sum(
        _num(o.get("monthly_value")) * _num(o.get("probability")) / 100
        for o in active
    )
    one_time_open = sum(_num(o.get("one_time_value")) for o in active)

    # This month's wins, keyed off the real close date. Using updated_at (as
    # this did before) meant any edit to an old won deal re-dated the win
    # into the current month and inflated the number.
    _today = local_today()
    this_month = month_start(_today).isoformat()
    next_month = month_start(_today, 1).isoformat()
    # Bounded on BOTH sides: an open-ended ">= this month" would let a
    # backdating typo (2027-01-15) count as won this month forever.
    # closed_date only — NO updated_at fallback. Falling back would reinstate
    # the exact bug this replaced, since updated_at moves on every edit. A won
    # deal with no close date is reported as undated instead of guessed at.
    won_this_month = [
        o for o in won
        if this_month <= _day(o.get("closed_date")) < next_month
    ]
    mrr_won = sum(_num(o.get("monthly_value")) for o in won_this_month)
    one_time_won = sum(_num(o.get("one_time_value")) for o in won_this_month)
    # A won deal with no close date can't be placed in a month — surface it
    # rather than letting it drop out of reporting unnoticed.
    undated_wins = [o for o in won if not _day(o.get("closed_date"))]

    # Conversion rate (won / (won + lost))
    total_decided = len(won) + len(lost)
    conversion_rate = (len(won) / total_decided * 100) if total_decided > 0 else 0

    # Average deal size — over deals that actually carry a price, so a $0
    # partnership placeholder can't drag the average down.
    priced = [o for o in active if _num(o.get("monthly_value")) > 0]
    avg_deal = (sum(_num(o.get("monthly_value")) for o in priced) / len(priced)
                if priced else 0)

    return {
        "total_opportunities": len(active),
        "total_pipeline_value": total_value,
        "weighted_pipeline_value": weighted_value,
        "one_time_pipeline_value": one_time_open,
        "by_stage": by_stage,
        "avg_deal_size": avg_deal,
        "conversion_rate": conversion_rate,
        "deals_won_this_month": len(won_this_month),
        "mrr_won_this_month": mrr_won,
        "one_time_won_this_month": one_time_won,
        "total_won": len(won),
        "total_lost": len(lost),
        "excluded_count": len(opps) - len(scored),
        "undated_wins": len(undated_wins),
    }


def get_revenue_forecast(months: int = 3, opps: list[dict] | None = None) -> list[dict]:
    """Forecast revenue for the next N months based on weighted pipeline.

    Returns list of dicts:
        [{month, expected_mrr, best_case, worst_case, deal_count, one_time}]

    Each month holds the deals whose expected close falls IN that month.
    Previously every bucket was cumulative ("closing on or before"), so one
    deal was counted again in every later month and the three numbers could
    not be read as three months of revenue.

    Deals with no expected close date, and deals already past due, cannot
    belong to a future month — they are reported separately rather than
    dropped silently, which is what used to happen to undated deals.
    """
    if opps is None:
        opps = get_all_opportunities()
    active = [o for o in counted(opps) if o.get("stage") not in CLOSED_STAGES]

    today = local_today()

    forecast = []
    for i in range(months):
        start = month_start(today, i + 1)
        end = month_start(today, i + 2)

        closing = [
            o for o in active
            if start.isoformat() <= _day(o.get("expected_close_date")) < end.isoformat()
        ]

        expected = sum(
            _num(o.get("monthly_value")) * _num(o.get("probability")) / 100
            for o in closing
        )
        best_case = sum(_num(o.get("monthly_value")) for o in closing)
        worst_case = sum(
            _num(o.get("monthly_value"))
            for o in closing
            if _num(o.get("probability")) >= 75
        )

        forecast.append({
            "month": start.strftime("%B %Y"),
            "expected_mrr": expected,
            "best_case": best_case,
            "worst_case": worst_case,
            "deal_count": len(closing),
            "one_time": sum(_num(o.get("one_time_value")) for o in closing),
        })

    return forecast


def get_forecast_gaps(opps: list[dict] | None = None) -> dict:
    """Open deals the month-by-month forecast cannot place.

    Returns counts and values for deals with no expected close date and for
    deals whose close date has already passed. Both are real pipeline that
    would otherwise be invisible on the Forecast tab.
    """
    if opps is None:
        opps = get_all_opportunities()
    active = [o for o in counted(opps) if o.get("stage") not in CLOSED_STAGES]
    today_iso = local_today().isoformat()

    undated = [o for o in active if not _day(o.get("expected_close_date"))]
    overdue = [o for o in active
               if _day(o.get("expected_close_date"))
               and _day(o.get("expected_close_date")) < today_iso]

    return {
        "undated": undated,
        "undated_value": sum(_num(o.get("monthly_value")) for o in undated),
        "overdue": overdue,
        "overdue_value": sum(_num(o.get("monthly_value")) for o in overdue),
    }


def get_deals_needing_action(opps: list[dict] | None = None) -> list[dict]:
    """Get opportunities violating the follow-up schedule.

    Flags, in priority order:
      1. Overdue next action (with days overdue)
      2. No follow-up scheduled at all (accountability rule: every open
         deal must have a next action + date)
      3. Untouched past the stage's SLA (per FOLLOW_UP_SLA)

    Sorted by monthly value descending — biggest dollars first.
    """
    if opps is None:
        opps = get_all_opportunities()
    today = local_today()
    today_iso = today.isoformat()
    needs_action = []

    for opp in opps:
        stage = opp.get("stage")
        if stage in CLOSED_STAGES:
            continue

        sla = FOLLOW_UP_SLA.get(stage, {"days": 7, "action": "Follow up"})
        reason = None

        next_date = opp.get("next_action_date")
        if next_date and next_date <= today_iso:
            try:
                overdue = (today - date.fromisoformat(next_date[:10])).days
                when = f"{overdue} day(s) overdue" if overdue else "due today"
            except ValueError:
                when = "overdue"
            reason = f"{when.capitalize()}: {opp.get('next_action', 'Follow up')}"
        elif not next_date:
            reason = f"No follow-up scheduled — set one ({sla['action']})"
        else:
            last_touch = _day(opp.get("last_contact_date") or opp.get("updated_at"))
            sla_cutoff = (today - timedelta(days=sla["days"])).isoformat()
            if last_touch and last_touch <= sla_cutoff:
                reason = (f"No touch in {sla['days']}+ days — "
                          f"{STAGES.get(stage, {}).get('label', stage)} deals "
                          f"need contact every {sla['days']} day(s)")

        if reason:
            opp["_action_reason"] = reason
            needs_action.append(opp)

    needs_action.sort(key=lambda o: -_num(o.get("monthly_value")))
    return needs_action


def get_all_activity(days: int = 30, limit: int = 1000) -> list[dict]:
    """Get all pipeline activity across deals for the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    result = _sb_request(
        "GET",
        f"pipeline_activity?created_at=gte.{since}&order=created_at.desc&limit={limit}"
    )
    if result is not None:
        return result

    activity = _load_local_activity()
    return [a for a in activity if (a.get("created_at") or "") >= since][:limit]


def get_rep_scoreboard(opps: list[dict] | None = None, days: int = 30) -> list[dict]:
    """Per-rep accountability and productivity-to-revenue metrics.

    Ties activity (touches: calls, notes, emails, stage moves) directly to
    revenue produced, and surfaces follow-up discipline per rep.

    Returns one row per rep:
        rep, open_deals, pipeline_value, weighted_value, overdue,
        no_followup, avg_days_since_touch, touches, touches_per_deal,
        mrr_won_month, revenue_per_touch, win_rate
    """
    if opps is None:
        opps = get_all_opportunities()
    opps = counted(opps)
    activities = get_all_activity(days=days)
    today = local_today()
    _month_from = month_start(today).isoformat()
    _month_to = month_start(today, 1).isoformat()

    reps: dict[str, dict] = {}

    def _rep(name: str) -> dict:
        name = (name or "Unassigned").strip() or "Unassigned"
        if name not in reps:
            reps[name] = {
                "rep": name, "open_deals": 0, "pipeline_value": 0.0,
                "weighted_value": 0.0, "overdue": 0, "no_followup": 0,
                "touches": 0, "mrr_won_month": 0.0,
                "won_total": 0, "lost_total": 0, "_touch_ages": [],
            }
        return reps[name]

    opp_to_rep = {}
    for o in opps:
        r = _rep(o.get("assigned_rep", ""))
        opp_to_rep[o.get("id")] = r["rep"]
        stage = o.get("stage")

        if stage == "won":
            r["won_total"] += 1
            # Real close date, not updated_at — otherwise editing an old won
            # deal moves its revenue into this month's credit.
            # closed_date only, matching get_pipeline_summary exactly — if
            # these two disagree, the KPI tile and this scoreboard show
            # different revenue for the same month on the same screen.
            if _month_from <= _day(o.get("closed_date")) < _month_to:
                r["mrr_won_month"] += _num(o.get("monthly_value"))
        elif stage == "lost":
            r["lost_total"] += 1
        else:
            r["open_deals"] += 1
            value = _num(o.get("monthly_value"))
            r["pipeline_value"] += value
            r["weighted_value"] += value * _num(o.get("probability")) / 100

            next_date = _day(o.get("next_action_date"))
            if not next_date:
                r["no_followup"] += 1
            elif next_date <= today.isoformat():
                r["overdue"] += 1

            last_touch = _day(o.get("last_contact_date") or o.get("updated_at")
                              or o.get("created_at"))
            if last_touch:
                try:
                    r["_touch_ages"].append(
                        (today - date.fromisoformat(last_touch)).days)
                except ValueError:
                    pass

    # Attribute activity: by performer name when it matches a rep,
    # otherwise by the deal's assigned rep (covers legacy 'MCTV Bot' rows)
    for act in activities:
        performer = (act.get("performed_by") or "").strip()
        rep_name = performer if performer in reps else opp_to_rep.get(act.get("opportunity_id"))
        if rep_name and rep_name in reps:
            reps[rep_name]["touches"] += 1

    rows = []
    for r in reps.values():
        ages = r.pop("_touch_ages")
        r["avg_days_since_touch"] = round(sum(ages) / len(ages), 1) if ages else 0.0
        r["touches_per_deal"] = round(r["touches"] / r["open_deals"], 1) if r["open_deals"] else 0.0
        r["revenue_per_touch"] = round(r["mrr_won_month"] / r["touches"], 2) if r["touches"] else 0.0
        decided = r["won_total"] + r["lost_total"]
        r["win_rate"] = round(r["won_total"] / decided * 100) if decided else 0
        rows.append(r)

    rows.sort(key=lambda x: -x["pipeline_value"])
    return rows


def get_stage_options() -> list[tuple[str, str]]:
    """Return stage options as [(key, label)] sorted by pipeline order."""
    return sorted(
        [(k, v["label"]) for k, v in STAGES.items()],
        key=lambda x: STAGES[x[0]]["order"]
    )
