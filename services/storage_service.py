"""Supabase Storage wrapper for file upload, download, and management.

Handles client uploads (photos, logos), contract PDFs, reports, and deliveries.
Falls back gracefully when Supabase Storage is not configured.
"""

import os
from pathlib import Path
from datetime import datetime

from services.supabase_client import get_admin_client, is_configured


# Storage bucket names
BUCKET_CONTRACTS = "contracts"
BUCKET_REPORTS = "reports"
BUCKET_CREATIVE_UPLOADS = "creative-uploads"
BUCKET_CREATIVE_DELIVERIES = "creative-deliveries"

ALL_BUCKETS = [BUCKET_CONTRACTS, BUCKET_REPORTS, BUCKET_CREATIVE_UPLOADS,
               BUCKET_CREATIVE_DELIVERIES]


def ensure_buckets():
    """Create storage buckets if they don't exist. Call once at startup."""
    client = get_admin_client()
    if not client:
        return

    try:
        existing = {b.name for b in client.storage.list_buckets()}
        for bucket_name in ALL_BUCKETS:
            if bucket_name not in existing:
                client.storage.create_bucket(bucket_name, options={
                    "public": False,
                    "file_size_limit": 20 * 1024 * 1024,  # 20MB per file
                })
                print(f"[storage] Created bucket: {bucket_name}")
    except Exception as e:
        print(f"[storage] Failed to ensure buckets: {e}")


def upload_file(bucket: str, path: str, file_bytes: bytes,
                content_type: str = "application/octet-stream") -> str | None:
    """Upload a file to Supabase Storage.

    Args:
        bucket: Bucket name (use constants above)
        path: Storage path within bucket (e.g., "client-id/filename.png")
        file_bytes: File content as bytes
        content_type: MIME type

    Returns:
        Storage path on success, None on failure.
    """
    client = get_admin_client()
    if not client:
        return None

    try:
        client.storage.from_(bucket).upload(
            path,
            file_bytes,
            file_options={"content-type": content_type},
        )
        return f"{bucket}/{path}"
    except Exception as e:
        # If file already exists, try to update it
        if "Duplicate" in str(e) or "already exists" in str(e):
            try:
                client.storage.from_(bucket).update(
                    path,
                    file_bytes,
                    file_options={"content-type": content_type},
                )
                return f"{bucket}/{path}"
            except Exception as e2:
                print(f"[storage] Upload update failed: {e2}")
                return None
        print(f"[storage] Upload failed: {e}")
        return None


def upload_from_path(bucket: str, storage_path: str,
                     local_path: str | Path) -> str | None:
    """Upload a local file to Supabase Storage.

    Args:
        bucket: Bucket name
        storage_path: Destination path in bucket
        local_path: Local file path to upload

    Returns:
        Storage path on success, None on failure.
    """
    local_path = Path(local_path)
    if not local_path.exists():
        print(f"[storage] Local file not found: {local_path}")
        return None

    # Guess content type
    suffix = local_path.suffix.lower()
    content_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    content_type = content_types.get(suffix, "application/octet-stream")

    with open(local_path, "rb") as f:
        return upload_file(bucket, storage_path, f.read(), content_type)


def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str | None:
    """Generate a temporary signed URL for file download.

    Args:
        bucket: Bucket name
        path: File path within the bucket
        expires_in: URL validity in seconds (default: 1 hour)

    Returns:
        Signed URL string, or None on failure.
    """
    client = get_admin_client()
    if not client:
        return None

    try:
        result = client.storage.from_(bucket).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signedUrl")
    except Exception as e:
        print(f"[storage] Signed URL failed: {e}")
        return None


def get_public_url(bucket: str, path: str) -> str | None:
    """Get the public URL for a file (only works if bucket is public).

    For private buckets, use get_signed_url() instead.
    """
    client = get_admin_client()
    if not client:
        return None

    try:
        result = client.storage.from_(bucket).get_public_url(path)
        return result
    except Exception as e:
        print(f"[storage] Public URL failed: {e}")
        return None


def delete_file(bucket: str, path: str) -> bool:
    """Delete a file from storage. Returns True on success."""
    client = get_admin_client()
    if not client:
        return False

    try:
        client.storage.from_(bucket).remove([path])
        return True
    except Exception as e:
        print(f"[storage] Delete failed: {e}")
        return False


def list_files(bucket: str, folder: str = "") -> list[dict]:
    """List files in a storage bucket/folder.

    Returns list of dicts with 'name', 'id', 'created_at', 'metadata'.
    """
    client = get_admin_client()
    if not client:
        return []

    try:
        result = client.storage.from_(bucket).list(folder)
        return result if result else []
    except Exception as e:
        print(f"[storage] List failed: {e}")
        return []


def build_storage_path(client_id: str, filename: str, prefix: str = "") -> str:
    """Build a consistent storage path for a client file.

    Format: {client_id}/{prefix}/{timestamp}_{filename}
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = [str(client_id)]
    if prefix:
        parts.append(prefix)
    parts.append(f"{timestamp}_{filename}")
    return "/".join(parts)
