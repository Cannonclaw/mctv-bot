"""Supabase Storage wrapper for file upload, download, and management.

Handles client uploads (photos, logos), contract PDFs, reports, and deliveries.
Falls back gracefully when Supabase Storage is not configured.
"""

import os
import json
import urllib.request
import urllib.error
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


def _rest_ensure_buckets():
    """Create storage buckets via REST API if they don't exist."""
    url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        return

    try:
        # List existing buckets
        req = urllib.request.Request(
            f"{url}/storage/v1/bucket",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            buckets = json.loads(resp.read().decode("utf-8"))
        existing = {b["name"] for b in buckets} if isinstance(buckets, list) else set()

        for bucket_name in ALL_BUCKETS:
            if bucket_name not in existing:
                body = json.dumps({
                    "id": bucket_name,
                    "name": bucket_name,
                    "public": False,
                    "file_size_limit": 20 * 1024 * 1024,
                }).encode("utf-8")
                create_req = urllib.request.Request(
                    f"{url}/storage/v1/bucket",
                    data=body,
                    headers={
                        "apikey": service_key,
                        "Authorization": f"Bearer {service_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(create_req, timeout=15) as resp:
                    resp.read()
                print(f"[storage] Created bucket via REST: {bucket_name}")
    except Exception as e:
        print(f"[storage] REST ensure_buckets failed: {e}")


def ensure_buckets():
    """Create storage buckets if they don't exist. Call once at startup."""
    # Try SDK first
    client = get_admin_client()
    if client:
        try:
            existing = {b.name for b in client.storage.list_buckets()}
            for bucket_name in ALL_BUCKETS:
                if bucket_name not in existing:
                    client.storage.create_bucket(bucket_name, options={
                        "public": False,
                        "file_size_limit": 20 * 1024 * 1024,  # 20MB per file
                    })
                    print(f"[storage] Created bucket: {bucket_name}")
            return
        except Exception as e:
            print(f"[storage] SDK ensure_buckets failed: {e}")

    # REST fallback
    _rest_ensure_buckets()


def _rest_upload(bucket: str, path: str, file_bytes: bytes,
                 content_type: str = "application/octet-stream") -> str | None:
    """Upload a file via Supabase Storage REST API (no SDK needed)."""
    url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        return None

    try:
        req = urllib.request.Request(
            f"{url}/storage/v1/object/{bucket}/{path}",
            data=file_bytes,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return f"{bucket}/{path}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"[storage] REST upload failed ({e.code}): {body}")
        return None
    except Exception as e:
        print(f"[storage] REST upload failed: {e}")
        return None


def _rest_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str | None:
    """Get a signed download URL via Supabase Storage REST API (no SDK needed)."""
    url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        return None

    try:
        body = json.dumps({"expiresIn": expires_in}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/storage/v1/object/sign/{bucket}/{path}",
            data=body,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        signed_url = result.get("signedURL") or result.get("signedUrl", "")
        if signed_url and not signed_url.startswith("http"):
            signed_url = f"{url}/storage/v1{signed_url}"
        return signed_url or None
    except Exception as e:
        print(f"[storage] REST signed URL failed: {e}")
        return None


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
    # Try SDK first, fall back to REST
    client = get_admin_client()
    if client:
        try:
            client.storage.from_(bucket).upload(
                path,
                file_bytes,
                file_options={"content-type": content_type},
            )
            return f"{bucket}/{path}"
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e):
                try:
                    client.storage.from_(bucket).update(
                        path,
                        file_bytes,
                        file_options={"content-type": content_type},
                    )
                    return f"{bucket}/{path}"
                except Exception as e2:
                    print(f"[storage] SDK upload update failed: {e2}")
            else:
                print(f"[storage] SDK upload failed: {e}")

    # REST fallback
    return _rest_upload(bucket, path, file_bytes, content_type)


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
    # Try SDK first
    client = get_admin_client()
    if client:
        try:
            result = client.storage.from_(bucket).create_signed_url(path, expires_in)
            return result.get("signedURL") or result.get("signedUrl")
        except Exception as e:
            print(f"[storage] SDK signed URL failed: {e}")

    # REST fallback
    return _rest_signed_url(bucket, path, expires_in)


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


def _rest_delete(bucket: str, path: str) -> bool:
    """Delete a file via Supabase Storage REST API."""
    url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        return False

    try:
        body = json.dumps({"prefixes": [path]}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/storage/v1/object/{bucket}",
            data=body,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            method="DELETE",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True
    except Exception as e:
        print(f"[storage] REST delete failed: {e}")
        return False


def _rest_list_files(bucket: str, folder: str = "") -> list[dict]:
    """List files in a bucket/folder via Supabase Storage REST API."""
    url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        return []

    try:
        body = json.dumps({
            "prefix": folder,
            "limit": 100,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/storage/v1/object/list/{bucket}",
            data=body,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[storage] REST list failed: {e}")
        return []


def delete_file(bucket: str, path: str) -> bool:
    """Delete a file from storage. Returns True on success."""
    # Try SDK first
    client = get_admin_client()
    if client:
        try:
            client.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            print(f"[storage] SDK delete failed: {e}")

    # REST fallback
    return _rest_delete(bucket, path)


def list_files(bucket: str, folder: str = "") -> list[dict]:
    """List files in a storage bucket/folder.

    Returns list of dicts with 'name', 'id', 'created_at', 'metadata'.
    """
    # Try SDK first
    client = get_admin_client()
    if client:
        try:
            result = client.storage.from_(bucket).list(folder)
            return result if result else []
        except Exception as e:
            print(f"[storage] SDK list failed: {e}")

    # REST fallback
    return _rest_list_files(bucket, folder)


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
