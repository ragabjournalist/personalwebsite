"""
Cloud Storage helper for persistent state on Cloud Run.
- Downloads SQLite DB from GCS on startup
- Uploads DB back to GCS after every write
- Serves images directly from GCS (public URLs)

Falls back to local files if GCS_BUCKET env var is not set (for local dev).
"""
import os
import threading
from pathlib import Path
from typing import Optional

BUCKET_NAME = os.environ.get("GCS_BUCKET")
DB_LOCAL_PATH = Path(__file__).parent / "investigations.db"
DB_GCS_KEY = "database/investigations.db"

_client = None
_bucket = None
_upload_lock = threading.Lock()


def _get_bucket():
    """Lazy-initialize GCS client only when GCS_BUCKET is set."""
    global _client, _bucket
    if not BUCKET_NAME:
        return None
    if _bucket is None:
        from google.cloud import storage
        _client = storage.Client()
        _bucket = _client.bucket(BUCKET_NAME)
    return _bucket


def download_db_from_gcs() -> bool:
    """Download the DB from GCS on startup. Returns True if downloaded."""
    bucket = _get_bucket()
    if not bucket:
        print("[storage] GCS_BUCKET not set — using local SQLite file")
        return False
    blob = bucket.blob(DB_GCS_KEY)
    if blob.exists():
        blob.download_to_filename(str(DB_LOCAL_PATH))
        print(f"[storage] Downloaded DB from gs://{BUCKET_NAME}/{DB_GCS_KEY}")
        return True
    print(f"[storage] No existing DB in gs://{BUCKET_NAME}/{DB_GCS_KEY} — will create fresh")
    return False


def upload_db_to_gcs() -> None:
    """Upload the DB back to GCS after a write. Thread-safe."""
    bucket = _get_bucket()
    if not bucket:
        return
    if not DB_LOCAL_PATH.exists():
        return
    with _upload_lock:
        blob = bucket.blob(DB_GCS_KEY)
        blob.upload_from_filename(str(DB_LOCAL_PATH))


def upload_image(local_path: str, remote_name: str) -> str:
    """
    Upload an image to GCS under uploads/<remote_name>.
    Returns the public HTTPS URL.

    Falls back to local path if GCS_BUCKET is not set.
    """
    bucket = _get_bucket()
    if not bucket:
        return f"/uploads/{remote_name}"
    blob = bucket.blob(f"uploads/{remote_name}")
    blob.upload_from_filename(local_path)
    # Bucket is expected to be publicly readable via IAM policy
    return f"https://storage.googleapis.com/{BUCKET_NAME}/uploads/{remote_name}"


def delete_image(url: str) -> None:
    """Delete an image given its public URL. No-op if URL isn't in our bucket."""
    bucket = _get_bucket()
    if not bucket or not url:
        return
    prefix = f"https://storage.googleapis.com/{BUCKET_NAME}/"
    if not url.startswith(prefix):
        return
    key = url[len(prefix):]
    blob = bucket.blob(key)
    try:
        blob.delete()
    except Exception as e:
        print(f"[storage] delete failed for {key}: {e}")
