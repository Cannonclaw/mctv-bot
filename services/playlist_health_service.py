# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Playlist health checks — find items likely to wedge a player.

Motivation (Oxford, Aug 4 2026): screens across the Oxford playlist went
black mid-day. The reported behavior was a player that started the loop,
skipped a contiguous block of paid spots, then stopped rendering entirely;
a content update or reboot brought it back for under an hour before it
died again. That is the signature of a player hitting an item it cannot
decode and unwinding the loop — not a display or cable fault, and not
something a reboot fixes, because the bad item is still in the loop.

This module takes a playlist export and flags the items most likely to
cause that. It is deliberately conservative about severity: 'high' means
"this can stop a player", 'medium' means "this can misbehave", 'low' means
"worth cleaning up". Nothing here talks to Encompass — it reads an export.

The checks are ranked by how often they actually break signage players:

    container_mismatch  A file whose container/codec differs from the rest
                        of the playlist. The single most common cause of a
                        hard stop, because the player is provisioned for
                        one pipeline and silently fails on the other.
    bad_duration        Zero, missing, negative, or wildly out-of-band
                        durations. A 0s item can spin a player in a tight
                        loop; an absurd one looks like a freeze.
    dynamic_feed        Live/data-driven items (calendars, weather,
                        scoreboards). These can start failing AFTER publish
                        with nobody touching the playlist, which is what
                        makes them so confusing to chase.
    dark_item           Whitelisted to zero screens: present in the
                        playlist, playing nowhere.
    duplicate_file      Same creative twice in one playlist.
    risky_filename      Characters that break path handling downstream.
    missing_file        A row with no file at all.

Public API:
    parse_playlist_export(path) ..... read xlsx/csv into normalized rows
    check_playlist(rows, ...) ....... list[Finding] worst-first
    summarize(findings) ............. counts by severity + headline
    SEVERITY_ORDER .................. for stable sorting in the UI
"""
from __future__ import annotations

import csv
import os
import re
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Containers a signage player is normally provisioned for. A playlist should
# be internally consistent — mixing these is the risk, not any one of them.
VIDEO_EXTENSIONS = {"webm", "mp4", "mov", "avi", "wmv", "mpg", "mpeg", "mkv", "m4v"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}

# Substrings that mark an item as live/data-driven rather than a flat file.
# These are the items that can go bad after publish.
DYNAMIC_MARKERS = (
    "calendar", "events", "event_", "feed", "rss", "weather", "forecast",
    "news", "ticker", "scoreboard", "score", "athletics", "schedule",
    "twitter", "instagram", "facebook", "social", "live", "widget",
    "dynamic", "api", "http",
)

# Characters that routinely break path handling in signage toolchains.
RISKY_CHARS = set("'\"&%#?*|<>:\\;$`{}[]")

# Durations outside this band are suspect for a :15/:30 spot loop.
MIN_SANE_SECONDS = 3
MAX_SANE_SECONDS = 120

# Header aliases — Encompass exports do not use stable column names.
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "file_name": ("file", "file name", "filename", "content", "content name",
                  "asset", "asset name", "media", "media name", "creative",
                  "title", "name", "spot"),
    "duration_seconds": ("duration", "duration (s)", "duration seconds",
                         "length", "runtime", "secs", "seconds", "dur"),
    "item_type": ("type", "item type", "content type", "media type", "kind",
                  "category"),
    "licenses": ("licenses", "license count", "whitelisted", "whitelist",
                 "screens", "screen count", "players", "displays"),
    "bucket": ("bucket", "slot", "class"),
    "advertiser": ("advertiser", "client", "customer", "account", "brand"),
    "status": ("status", "state", "active"),
    "modified_at": ("modified", "last modified", "modified at", "updated",
                    "updated at", "date modified", "changed"),
}


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One problem with one playlist item (or the playlist as a whole)."""

    rule: str
    severity: str
    file_name: str
    detail: str
    action: str
    row_number: int | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extension_of(file_name: str | None) -> str:
    """Lowercase extension without the dot, or '' when there isn't one.

    Dynamic items often have no extension at all (a widget name, a URL),
    which is itself a useful signal — hence '' rather than a guess.
    """
    name = (file_name or "").strip().lower()
    name = name.split("?", 1)[0].rstrip("/")
    if "." not in name:
        return ""
    ext = name.rsplit(".", 1)[1]
    return ext if ext.isalnum() and len(ext) <= 5 else ""


def _norm_header(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _to_seconds(value: Any) -> float | None:
    """Parse a duration cell. Handles 15, '15', '0:15', '00:00:15', '15s'."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace("sec", "").replace("s", "").strip()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            return None
        total = 0.0
        for n in nums:
            total = total * 60 + n
        return total
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _looks_dynamic(row: dict[str, Any]) -> bool:
    """True when the item is live/data-driven rather than a flat media file."""
    haystack = " ".join(
        str(row.get(k) or "").lower() for k in ("file_name", "item_type")
    )
    return any(marker in haystack for marker in DYNAMIC_MARKERS)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _map_headers(headers: Iterable[Any]) -> dict[int, str]:
    """Map column index -> canonical field name, longest alias winning.

    Exports vary between "Duration" and "Duration (s)" and "Length"; matching
    on the longest alias first stops "name" from stealing "file name".
    """
    normalized = [_norm_header(h) for h in headers]
    mapping: dict[int, str] = {}
    for canonical, aliases in _FIELD_ALIASES.items():
        best_idx, best_len = None, -1
        for idx, header in enumerate(normalized):
            if idx in mapping or not header:
                continue
            for alias in aliases:
                if header == alias or (alias in header and len(alias) > best_len):
                    exact = header == alias
                    score = 1000 if exact else len(alias)
                    if score > best_len:
                        best_idx, best_len = idx, score
        if best_idx is not None:
            mapping[best_idx] = canonical
    return mapping


def _rows_from_matrix(matrix: list[list[Any]]) -> list[dict[str, Any]]:
    """Find the header row, then build normalized dicts from the rest."""
    header_idx, mapping = None, {}
    for idx, row in enumerate(matrix[:25]):
        candidate = _map_headers(row)
        if "file_name" in candidate.values():
            header_idx, mapping = idx, candidate
            break
    if header_idx is None:
        return []

    out: list[dict[str, Any]] = []
    for offset, raw in enumerate(matrix[header_idx + 1:], start=header_idx + 2):
        if not any(str(c).strip() for c in raw if c is not None):
            continue
        item: dict[str, Any] = {"row_number": offset}
        for idx, canonical in mapping.items():
            item[canonical] = raw[idx] if idx < len(raw) else None
        item["duration_seconds"] = _to_seconds(item.get("duration_seconds"))
        item["licenses"] = _to_int(item.get("licenses"))
        item["file_name"] = str(item.get("file_name") or "").strip()
        out.append(item)
    return out


def parse_playlist_export(file_path) -> list[dict[str, Any]]:
    """Read an Encompass playlist export (.xlsx/.xlsm/.csv) into rows.

    Returns [] when no recognizable header row is found, so a wrong file
    shows the caller's empty state instead of raising.
    """
    path = str(getattr(file_path, "name", file_path) or "")
    ext = os.path.splitext(path)[1].lower()

    if ext in (".csv", ".tsv", ".txt"):
        delimiter = "\t" if ext == ".tsv" else ","
        handle = (
            file_path if hasattr(file_path, "read")
            else open(file_path, newline="", encoding="utf-8-sig", errors="replace")
        )
        try:
            data = handle.read()
            if isinstance(data, bytes):
                data = data.decode("utf-8-sig", errors="replace")
            matrix = [r for r in csv.reader(data.splitlines(), delimiter=delimiter)]
        finally:
            if handle is not file_path:
                handle.close()
        return _rows_from_matrix(matrix)

    import openpyxl

    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    try:
        for sheet in wb.worksheets:
            matrix = [list(r) for r in sheet.iter_rows(values_only=True)]
            rows = _rows_from_matrix(matrix)
            if rows:
                return rows
        return []
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_containers(rows: list[dict[str, Any]]) -> list[Finding]:
    """Flag files whose container differs from the playlist's dominant one.

    A playlist that is 95% .webm and 5% .mp4 is the classic wedge: the
    player is provisioned for one pipeline and hard-stops on the other.
    Only fires when there is a clear majority to deviate from.
    """
    media = [
        r for r in rows
        if extension_of(r.get("file_name")) in (VIDEO_EXTENSIONS | IMAGE_EXTENSIONS)
    ]
    if len(media) < 5:
        return []

    videos = [r for r in media if extension_of(r["file_name"]) in VIDEO_EXTENSIONS]
    if len(videos) < 5:
        return []

    counts: dict[str, int] = {}
    for r in videos:
        ext = extension_of(r["file_name"])
        counts[ext] = counts.get(ext, 0) + 1
    dominant, dominant_n = max(counts.items(), key=lambda kv: kv[1])
    if dominant_n / len(videos) < 0.7:
        return []  # genuinely mixed playlist; mismatch isn't meaningful

    findings = []
    for r in videos:
        ext = extension_of(r["file_name"])
        if ext == dominant:
            continue
        findings.append(Finding(
            rule="container_mismatch",
            severity="high",
            file_name=r["file_name"],
            row_number=r.get("row_number"),
            detail=(
                f"Encoded as .{ext} in a playlist that is "
                f"{dominant_n}/{len(videos)} .{dominant}. A player provisioned "
                f"for .{dominant} can hard-stop on this item."
            ),
            action=(
                f"Re-encode to .{dominant} and republish, or pull it from the "
                f"playlist until it is re-encoded."
            ),
            context={"extension": ext, "dominant": dominant,
                     "advertiser": r.get("advertiser")},
        ))
    return findings


def _check_durations(rows: list[dict[str, Any]]) -> list[Finding]:
    """Zero/missing/negative durations, plus out-of-band outliers."""
    findings = []
    known = [
        r["duration_seconds"] for r in rows
        if isinstance(r.get("duration_seconds"), (int, float))
        and r["duration_seconds"] > 0
    ]
    median = statistics.median(known) if known else None

    for r in rows:
        secs = r.get("duration_seconds")
        name = r.get("file_name") or "(unnamed)"

        if secs is None:
            if _looks_dynamic(r):
                continue  # dynamic items legitimately have no fixed duration
            findings.append(Finding(
                rule="bad_duration", severity="medium", file_name=name,
                row_number=r.get("row_number"),
                detail="No duration recorded for a flat media item.",
                action="Set an explicit duration in Encompass.",
            ))
            continue

        if secs <= 0:
            findings.append(Finding(
                rule="bad_duration", severity="high", file_name=name,
                row_number=r.get("row_number"),
                detail=(
                    f"Duration is {secs:g}s. A zero-length item can spin a "
                    f"player through the loop faster than it can render, "
                    f"which looks exactly like skipped spots then a black screen."
                ),
                action="Set a real duration or remove the item.",
                context={"duration_seconds": secs},
            ))
        elif secs > MAX_SANE_SECONDS:
            findings.append(Finding(
                rule="bad_duration", severity="medium", file_name=name,
                row_number=r.get("row_number"),
                detail=(
                    f"Duration is {secs:g}s"
                    + (f" against a playlist median of {median:g}s" if median else "")
                    + ". On screen this reads as a frozen display."
                ),
                action="Confirm the duration is intentional.",
                context={"duration_seconds": secs},
            ))
        elif secs < MIN_SANE_SECONDS:
            findings.append(Finding(
                rule="bad_duration", severity="medium", file_name=name,
                row_number=r.get("row_number"),
                detail=f"Duration is {secs:g}s — too short to render reliably.",
                action="Set a real duration or remove the item.",
                context={"duration_seconds": secs},
            ))
    return findings


def _check_dynamic(rows: list[dict[str, Any]]) -> list[Finding]:
    """Flag live/data-driven items — they fail after publish, not at publish."""
    findings = []
    for r in rows:
        if not _looks_dynamic(r):
            continue
        name = r.get("file_name") or "(unnamed)"
        findings.append(Finding(
            rule="dynamic_feed", severity="medium", file_name=name,
            row_number=r.get("row_number"),
            detail=(
                "Live or data-driven item. These can begin failing after "
                "publish with nobody touching the playlist — a stale source, "
                "an expired certificate, or a feed that stopped responding."
            ),
            action=(
                "Pull it from the loop temporarily and watch whether the "
                "screens stay up. This is the cheapest way to confirm or "
                "clear it."
            ),
            context={"item_type": r.get("item_type")},
        ))
    return findings


def _check_dark(rows: list[dict[str, Any]]) -> list[Finding]:
    """Items present in the playlist but whitelisted to zero screens."""
    findings = []
    for r in rows:
        licenses = r.get("licenses")
        if licenses is None or licenses > 0:
            continue
        name = r.get("file_name") or "(unnamed)"
        findings.append(Finding(
            rule="dark_item", severity="low", file_name=name,
            row_number=r.get("row_number"),
            detail="In the playlist but whitelisted to 0 screens — playing nowhere.",
            action="Whitelist it, or remove it from the playlist.",
            context={"advertiser": r.get("advertiser")},
        ))
    return findings


def _check_duplicates(rows: list[dict[str, Any]]) -> list[Finding]:
    """Same creative appearing more than once in one playlist."""
    seen: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = re.sub(r"[^a-z0-9]+", "", (r.get("file_name") or "").lower())
        if key:
            seen.setdefault(key, []).append(r)

    findings = []
    for group in seen.values():
        if len(group) < 2:
            continue
        rowlist = ", ".join(str(g.get("row_number")) for g in group if g.get("row_number"))
        findings.append(Finding(
            rule="duplicate_file", severity="low",
            file_name=group[0].get("file_name") or "(unnamed)",
            row_number=group[0].get("row_number"),
            detail=f"Appears {len(group)} times in this playlist (rows {rowlist}).",
            action="Remove the duplicate unless the double-play is intentional.",
            context={"count": len(group)},
        ))
    return findings


def _check_filenames(rows: list[dict[str, Any]]) -> list[Finding]:
    """Blank names, and characters that break path handling downstream."""
    findings = []
    for r in rows:
        name = (r.get("file_name") or "").strip()
        if not name:
            findings.append(Finding(
                rule="missing_file", severity="high", file_name="(blank)",
                row_number=r.get("row_number"),
                detail="Playlist row with no file attached.",
                action="Attach the creative or delete the row.",
            ))
            continue
        bad = sorted(set(name) & RISKY_CHARS)
        if bad:
            findings.append(Finding(
                rule="risky_filename", severity="low", file_name=name,
                row_number=r.get("row_number"),
                detail=f"File name contains {' '.join(repr(c) for c in bad)}.",
                action="Rename with letters, numbers, dash and underscore only.",
                context={"characters": bad},
            ))
        if not name.isascii():
            findings.append(Finding(
                rule="risky_filename", severity="low", file_name=name,
                row_number=r.get("row_number"),
                detail="File name contains non-ASCII characters.",
                action="Rename using ASCII characters only.",
            ))
    return findings


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def check_playlist(rows: list[dict[str, Any]]) -> list[Finding]:
    """Run every check. Returns findings worst-first, stable within severity."""
    findings: list[Finding] = []
    for check in (
        _check_containers,
        _check_filenames,
        _check_durations,
        _check_dynamic,
        _check_dark,
        _check_duplicates,
    ):
        findings.extend(check(rows))

    findings.sort(key=lambda f: (
        SEVERITY_ORDER.get(f.severity, 9),
        f.rule,
        f.row_number if f.row_number is not None else 10**6,
    ))
    return findings


def summarize(findings: list[Finding], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Counts by severity and rule, plus a one-line headline for the UI."""
    by_severity = {"high": 0, "medium": 0, "low": 0}
    by_rule: dict[str, int] = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_rule[f.rule] = by_rule.get(f.rule, 0) + 1

    if by_severity["high"]:
        headline = (
            f"{by_severity['high']} item(s) that can stop a player. "
            f"Start at the top of the list."
        )
    elif by_severity["medium"]:
        headline = (
            f"Nothing that hard-stops a player, but {by_severity['medium']} "
            f"item(s) can misbehave."
        )
    elif findings:
        headline = "Only cleanup-grade findings — nothing that explains a black screen."
    else:
        headline = "No problems found in this export."

    return {
        "items_checked": len(rows) if rows is not None else None,
        "findings": len(findings),
        "by_severity": by_severity,
        "by_rule": by_rule,
        "headline": headline,
    }
