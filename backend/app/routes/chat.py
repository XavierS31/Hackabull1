import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import CHATBOT_SYSTEM, CONVERSATION_SYSTEM, VISION_SYSTEM
from ..models import ChatRequest, TrackRequest, VisionRequest
from ..services.gemma import call_gemma_text
from ..state import (
    activity_log,
    append_activity,
    ensure_agent_enabled,
    frame_store,
    hub,
    voice_service,
)

router = APIRouter()


@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> JSONResponse:
    """Chatbot agent — text message with optional camera frame."""
    ensure_agent_enabled("Chatbot")
    image_bytes: bytes | None = None
    if request.camera in ("glasses", "glove"):
        image_bytes = frame_store.get_latest_jpeg(request.camera)

    append_activity({"ts": time.time(), "type": "chat", "message": request.message})

    response_text = await call_gemma_text(CHATBOT_SYSTEM, request.message, image_bytes)

    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f"Chatbot: {response_text[:140]}",
        "ts": time.time(),
    })

    return JSONResponse({"response": response_text, "agent": "Chatbot"})


@router.post("/api/vision/analyze")
async def vision_analyze(request: VisionRequest) -> JSONResponse:
    """Vision Agent — describe the surroundings from the latest camera frame."""
    ensure_agent_enabled("Vision Agent")
    camera = request.camera if request.camera in ("glasses", "glove") else "glasses"
    image_bytes = frame_store.get_latest_jpeg(camera)

    if not image_bytes:
        return JSONResponse({
            "description": "No camera frame available. Start the camera stream first.",
            "camera": camera,
            "agent": "Vision Agent",
        })

    description = await call_gemma_text(VISION_SYSTEM, "Describe what you see in this image.", image_bytes)

    append_activity({"ts": time.time(), "type": "vision", "camera": camera, "description": description})

    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f"Vision Agent ({camera}): {description[:140]}",
        "ts": time.time(),
    })

    return JSONResponse({"description": description, "camera": camera, "agent": "Vision Agent"})


@router.post("/api/triggers/vision")
async def trigger_vision(camera: str = "glasses") -> JSONResponse:
    """
    Surroundings trigger — Vision Agent narrates the latest frame and pushes TTS.
    Use this for the manual "describe my surroundings" button on the glove.
    """
    ensure_agent_enabled("Vision Agent")
    if camera not in ("glasses", "glove"):
        camera = "glasses"

    image_bytes = frame_store.get_latest_jpeg(camera)
    if not image_bytes:
        return JSONResponse({
            "description": "No camera frame available yet.",
            "camera": camera,
            "agent": "Vision Agent",
        })

    description = await call_gemma_text(
        VISION_SYSTEM,
        "Briefly describe the surroundings to help the patient walk safely.",
        image_bytes,
    )

    append_activity({
        "ts": time.time(),
        "type": "vision",
        "camera": camera,
        "description": description,
        "trigger": "surroundings",
    })

    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f"Vision Agent (Surroundings/{camera}): {description[:140]}",
        "ts": time.time(),
    })

    if voice_service:
        try:
            audio = await voice_service.synthesize_async(description)
            await hub.broadcast_audio(audio)
        except Exception as exc:
            print(f"[Voice] Surroundings TTS failed: {exc}")

    return JSONResponse({
        "description": description,
        "camera": camera,
        "agent": "Vision Agent",
        "trigger": "surroundings",
    })


@router.post("/api/triggers/track")
async def trigger_track(request: TrackRequest) -> JSONResponse:
    """Tracking Dementia — TRACK manual input logs an event to memory."""
    ensure_agent_enabled("Tracking Dementia")
    entry: dict[str, Any] = {"ts": time.time(), "type": "track", "description": request.description}
    append_activity(entry)

    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f'Tracking Dementia: Manual log — "{request.description}"',
        "ts": entry["ts"],
    })

    return JSONResponse({"logged": True, "description": request.description, "agent": "Tracking Dementia"})


@router.post("/api/triggers/talk")
async def trigger_talk() -> JSONResponse:
    """Conversation Agent — TALK manual input starts a conversation about what the camera sees."""
    ensure_agent_enabled("Conversation Agent")
    image_bytes = frame_store.get_latest_jpeg("glasses")
    prompt = (
        "Start a friendly conversation about what you see in this image."
        if image_bytes
        else "Greet the patient warmly and ask how they're feeling today."
    )

    response_text = await call_gemma_text(CONVERSATION_SYSTEM, prompt, image_bytes)

    append_activity({"ts": time.time(), "type": "talk", "response": response_text})

    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f"Conversation Agent: {response_text[:140]}",
        "ts": time.time(),
    })

    return JSONResponse({"response": response_text, "agent": "Conversation Agent"})


@router.get("/api/activity")
async def get_activity() -> list[dict[str, Any]]:
    """Returns the 50 most recent activity log entries, newest first."""
    return list(reversed(activity_log[-50:]))
