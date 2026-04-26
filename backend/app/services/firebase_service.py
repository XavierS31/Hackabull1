"""
Firebase Storage (video clips) + Firestore (event metadata).
All functions are safe no-ops when Firebase is not initialised.
"""
from pathlib import Path
from typing import Any

_initialized = False


def init_firebase(service_account_path: str, storage_bucket: str) -> bool:
    """Initialize Firebase Admin SDK. Returns True on success."""
    global _initialized
    if _initialized:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {"storageBucket": storage_bucket})
        _initialized = True
        print(f"[Firebase] Initialised — bucket: {storage_bucket}")
        return True
    except Exception as exc:
        print(f"[Firebase] Init failed: {exc}")
        return False


def upload_video(local_path: Path, event_id: str, camera: str) -> str | None:
    """Upload a local MP4 to Firebase Storage. Returns public URL or None."""
    if not _initialized:
        return None
    try:
        from firebase_admin import storage

        bucket = storage.bucket()
        blob = bucket.blob(f"events/{event_id}/{camera}.mp4")
        blob.upload_from_filename(str(local_path), content_type="video/mp4")
        blob.make_public()
        return blob.public_url
    except Exception as exc:
        print(f"[Firebase] Upload failed ({event_id}/{camera}): {exc}")
        return None


def save_event_metadata(event_data: dict[str, Any]) -> None:
    """Write event metadata dict to Firestore events collection."""
    if not _initialized:
        return
    try:
        from firebase_admin import firestore

        db = firestore.client()
        db.collection("events").document(event_data["id"]).set(event_data)
    except Exception as exc:
        print(f"[Firebase] Firestore write failed: {exc}")


def list_firebase_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return events from Firestore ordered by timestamp (newest first)."""
    if not _initialized:
        return []
    try:
        from firebase_admin import firestore

        db = firestore.client()
        query = (
            db.collection("events")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [doc.to_dict() for doc in query.stream()]
    except Exception as exc:
        print(f"[Firebase] Firestore list failed: {exc}")
        return []
