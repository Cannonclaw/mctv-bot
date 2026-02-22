"""Creatomate API wrapper for generating video ad mockups.

Uses stdlib urllib only (no requests dependency) to match project conventions.
API docs: https://creatomate.com/docs/api/introduction
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

API_BASE = "https://api.creatomate.com/v1"


class CreatomateService:
    """Handles all Creatomate API interactions for video ad generation."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    # ── Core API helpers ─────────────────────────────────────────────────────

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        """Make an authenticated API request and return parsed JSON."""
        url = f"{API_BASE}{path}"
        data = json.dumps(body).encode("utf-8") if body else None

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "MCTV-Bot/1.0")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Creatomate API error {e.code}: {error_body}"
            ) from e

    # ── Templates ────────────────────────────────────────────────────────────

    def list_templates(self) -> list[dict]:
        """Get all templates in the project."""
        return self._request("GET", "/templates")

    def get_template(self, template_id: str) -> dict:
        """Get a single template by ID."""
        return self._request("GET", f"/templates/{template_id}")

    # ── Render (create + poll) ───────────────────────────────────────────────

    def create_render(
        self,
        template_id: str,
        modifications: dict | None = None,
        output_format: str = "mp4",
        metadata: str | None = None,
    ) -> dict:
        """
        Start an async render job. Returns the first render object.

        The render will have status='planned' initially — poll with
        get_render_status() or use wait_for_render() to block until done.
        """
        payload = {
            "template_id": template_id,
            "output_format": output_format,
        }
        if modifications:
            payload["modifications"] = modifications
        if metadata:
            payload["metadata"] = metadata

        renders = self._request("POST", "/renders", payload)
        # API returns a list; we typically create one render at a time
        return renders[0] if isinstance(renders, list) else renders

    def get_render_status(self, render_id: str) -> dict:
        """Check the current status of a render job."""
        return self._request("GET", f"/renders/{render_id}")

    def wait_for_render(
        self,
        render_id: str,
        timeout: int = 180,
        poll_interval: int = 3,
        progress_callback=None,
    ) -> dict:
        """
        Poll until a render completes (succeeded/failed) or times out.

        Args:
            render_id: The render ID from create_render().
            timeout: Max seconds to wait (default 3 minutes).
            poll_interval: Seconds between polls.
            progress_callback: Optional callable(status_str, elapsed_secs).

        Returns:
            The final render object (with url, duration, file_size, etc.).

        Raises:
            RuntimeError: If the render fails.
            TimeoutError: If the render doesn't complete in time.
        """
        start = time.time()

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError(
                    f"Render {render_id} did not complete within {timeout}s"
                )

            render = self.get_render_status(render_id)
            status = render.get("status", "unknown")

            if progress_callback:
                progress_callback(status, int(elapsed))

            if status == "succeeded":
                return render
            elif status == "failed":
                msg = render.get("error_message", "Unknown error")
                raise RuntimeError(f"Render failed: {msg}")

            time.sleep(poll_interval)

    # ── Convenience: render and wait ─────────────────────────────────────────

    def render_video(
        self,
        template_id: str,
        modifications: dict | None = None,
        output_format: str = "mp4",
        timeout: int = 180,
        progress_callback=None,
    ) -> dict:
        """
        Create a render and wait for it to complete. Returns the final
        render object with the video URL.

        This is the main method you'll call from the Streamlit UI.
        """
        render = self.create_render(
            template_id=template_id,
            modifications=modifications,
            output_format=output_format,
        )
        render_id = render["id"]

        return self.wait_for_render(
            render_id,
            timeout=timeout,
            progress_callback=progress_callback,
        )

    def download_video(self, video_url: str, save_dir: str | Path) -> Path:
        """
        Download a rendered video to a local directory.

        Args:
            video_url: The CDN URL from a completed render.
            save_dir: Directory to save the file.

        Returns:
            Path to the downloaded file.
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Extract filename from URL or default
        filename = video_url.split("/")[-1].split("?")[0]
        if not filename or "." not in filename:
            filename = "mctv_ad.mp4"

        save_path = save_dir / filename

        req = urllib.request.Request(video_url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            save_path.write_bytes(resp.read())

        return save_path


# ── Helper: build MCTV ad modifications from proposal data ──────────────────

def build_mctv_modifications(
    business_name: str,
    industry: str,
    city: str,
    tagline: str | None = None,
    client_logo_url: str | None = None,
    background_image_url: str | None = None,
) -> dict:
    """
    Build a Creatomate modifications dict for an MCTV ad template.

    The keys here must match the element names in the Creatomate template.
    Update these once the MCTV template is designed in the Creatomate editor.
    """
    mods = {}

    # Text elements (keys match template element names)
    mods["Business-Name.text"] = business_name
    mods["Industry.text"] = industry
    mods["City.text"] = city

    if tagline:
        mods["Tagline.text"] = tagline
    else:
        mods["Tagline.text"] = f"Now Advertising on MCTV in {city}"

    # Image elements
    if client_logo_url:
        mods["Client-Logo.source"] = _ensure_url(client_logo_url)
    if background_image_url:
        mods["Background-Image.source"] = _ensure_url(background_image_url)

    return mods


def _ensure_url(url: str) -> str:
    """Make sure a URL starts with https://."""
    url = url.strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url
