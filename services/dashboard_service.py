"""Persistent Network Dashboard service.

Stores the parsed MCTV Network Dashboard as a JSON file so it only needs
to be uploaded once.  Report generation reads from the stored JSON instead
of requiring a per-report upload (though per-report override is supported).
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from services.excel_parser import parse_network_dashboard

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DASHBOARD_PATH = DATA_DIR / "network_dashboard.json"


def save_dashboard(file_path_or_obj) -> dict:
    """Parse an Excel dashboard file and persist as JSON.

    Args:
        file_path_or_obj: File path string or file-like object (Streamlit uploader).

    Returns:
        Status dict: {success, venue_count, updated_at, error?}
    """
    try:
        lookup = parse_network_dashboard(file_path_or_obj)
        if not lookup:
            return {"success": False, "error": "No venue data found in file."}

        # Build the JSON payload with metadata
        payload = {
            "updated_at": datetime.now().isoformat(),
            "venue_count": len(lookup),
            "venues": lookup,  # dict keyed by host_name.lower()
        }

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DASHBOARD_PATH.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )

        logger.info("Dashboard saved: %d venues", len(lookup))
        return {
            "success": True,
            "venue_count": len(lookup),
            "updated_at": payload["updated_at"],
        }
    except Exception as e:
        logger.error("Failed to save dashboard: %s", e)
        return {"success": False, "error": str(e)}


def load_dashboard() -> dict:
    """Load the stored dashboard JSON.

    Returns:
        Dict mapping host_name (lowercase) -> venue metadata,
        in the same format as parse_network_dashboard().
        Returns empty dict if no dashboard is stored.
    """
    if not DASHBOARD_PATH.exists():
        return {}

    try:
        data = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
        return data.get("venues", {})
    except Exception as e:
        logger.error("Failed to load dashboard: %s", e)
        return {}


def get_dashboard_status() -> dict:
    """Get the current dashboard status.

    Returns:
        {loaded: bool, venue_count: int, updated_at: str}
    """
    if not DASHBOARD_PATH.exists():
        return {"loaded": False, "venue_count": 0, "updated_at": ""}

    try:
        data = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
        return {
            "loaded": True,
            "venue_count": data.get("venue_count", 0),
            "updated_at": data.get("updated_at", ""),
        }
    except Exception:
        return {"loaded": False, "venue_count": 0, "updated_at": ""}
