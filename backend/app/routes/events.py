import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from ..config import TRACKING_SYSTEM
from ..models import CriticalEvent
from ..services import firebase_service
from ..services.gemma import call_gemma_text
from ..state import activity_log, append_activity, event_recorder, events_dir, hub

router = APIRouter()


@router.get("/api/events")
async def list_events() -> list[CriticalEvent]:
    """
    Returns stored critical events.
    Prefers Firestore (persistent across restarts) when Firebase is configured;
    falls back to in-memory list otherwise.
    """
    firebase_events = firebase_service.list_firebase_events(limit=50)
    if firebase_events:
        return [CriticalEvent(**e) for e in firebase_events]
    return event_recorder.list_events()


@router.get("/api/events/media/{filename}")
async def event_media(filename: str) -> Response:
    """Serve locally-stored MP4 clip (fallback when Firebase is not configured)."""
    path = events_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media not found.")
    return Response(content=path.read_bytes(), media_type="video/mp4")


@router.post("/api/events/fall-test")
async def trigger_test_fall() -> dict[str, str]:
    event_id = event_recorder.trigger_fall(trigger="manual_test")
    append_activity({"ts": time.time(), "type": "fall", "trigger": "manual_test", "event_id": event_id})
    await hub.broadcast(
        "thinking",
        {
            "type": "thinking",
            "line": f"Falling Agent: Test fall triggered. Event {event_id} — capturing ±10s clip.",
            "ts": time.time(),
        },
    )
    return {"event_id": event_id}


@router.get("/api/events/ask")
async def ask_events(q: str = "") -> JSONResponse:
    """Tracking Dementia — natural-language query over the activity log."""
    if not q.strip():
        return JSONResponse({"answer": "Please provide a question.", "agent": "Tracking Dementia"})

    recent = activity_log[-100:] if activity_log else []
    if not recent:
        return JSONResponse({"answer": "No activity recorded yet.", "agent": "Tracking Dementia"})

    log_text = "\n".join([
        "[{type}] {detail} at {t}".format(
            type=e.get("type", "?"),
            detail=(
                e.get("message")
                or e.get("description")
                or e.get("trigger")
                or e.get("response")
                or ""
            ),
            t=time.strftime("%H:%M:%S", time.localtime(e["ts"])),
        )
        for e in recent
    ])

    answer = await call_gemma_text(TRACKING_SYSTEM, f"Activity log:\n{log_text}\n\nQuestion: {q}")
    return JSONResponse({"answer": answer, "agent": "Tracking Dementia"})
