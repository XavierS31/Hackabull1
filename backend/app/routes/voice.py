"""
Voice endpoints — keyword-routed voice assistant via ElevenLabs TTS + STT.

POST /api/voice/chat
  Accepts mic audio → STT → detects intent from keywords → routes to the
  correct agent (Vision / Conversation / Tracking / Chatbot) → TTS → MP3.

  Intent keywords (detected in the transcript):
    vision  — scan, look, see, describe, surroundings, camera
    talk    — talk, converse, conversation, chat
    track   — track, remember, log, record, note
    chat    — everything else (Chatbot agent)

POST /api/voice/speak      text → MP3
POST /api/voice/transcribe audio → transcript text
GET  /api/voice/status     diagnose voice service configuration

WebSocket /ws/voice        server-push MP3 alerts (fall / IR / vision)
WebSocket /ws/conversation bidirectional audio conversation
"""
import time
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..config import CHATBOT_SYSTEM, CONVERSATION_SYSTEM, VISION_SYSTEM
from ..services.gemma import call_gemma_text
from ..state import agent_status, append_activity, frame_store, hub, voice_service

router = APIRouter()

# ── keyword → intent mapping ──────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, set[str]] = {
    "vision":  {"scan", "look", "see", "describe", "surroundings", "camera", "what's", "whats", "ahead"},
    "talk":    {"talk", "converse", "conversation", "chat"},
    "track":   {"track", "remember", "log", "record", "note", "save"},
}

def _detect_intent(transcript: str) -> str:
    words = set(transcript.lower().split())
    for intent, keywords in _INTENT_KEYWORDS.items():
        if words & keywords:
            return intent
    return "chat"


_VOICE_PREFIX = (
    "Keep your response to 1-2 short sentences. "
    "This is a spoken voice reply — be concise and clear.\n\n"
)

def _voice(system: str) -> str:
    return _VOICE_PREFIX + system


async def _route_to_agent(intent: str, transcript: str) -> tuple[str, str]:
    """
    Route the transcript to the correct agent based on intent.
    Returns (agent_name, response_text).
    """
    glasses = frame_store.get_latest_jpeg("glasses")

    if intent == "vision" and agent_status.get("Vision Agent", True):
        description = await call_gemma_text(
            _voice(VISION_SYSTEM),
            "Briefly describe the surroundings to help the patient navigate safely.",
            glasses,
        )
        append_activity({"ts": time.time(), "type": "vision", "description": description, "trigger": "voice"})
        return "Vision Agent", description

    if intent == "talk" and agent_status.get("Conversation Agent", True):
        prompt = (
            "Start a warm, encouraging conversation about what you see in this image."
            if glasses
            else transcript or "Greet the patient warmly and ask how they're feeling."
        )
        response = await call_gemma_text(_voice(CONVERSATION_SYSTEM), prompt, glasses)
        append_activity({"ts": time.time(), "type": "talk", "response": response})
        return "Conversation Agent", response

    if intent == "track" and agent_status.get("Tracking Dementia", True):
        append_activity({"ts": time.time(), "type": "track", "description": transcript})
        await hub.broadcast("thinking", {
            "type": "thinking",
            "line": f'Tracking Dementia: Logged via voice — "{transcript}"',
            "ts": time.time(),
        })
        return "Tracking Dementia", f"Noted — I've logged: {transcript}"

    # Fallback → Chatbot
    if agent_status.get("Chatbot", True):
        response = await call_gemma_text(_voice(CHATBOT_SYSTEM), transcript or "Hello", glasses)
        append_activity({"ts": time.time(), "type": "chat", "message": transcript, "agent": "Chatbot"})
        return "Chatbot", response

    return "System", "All agents are currently offline."


# ── helpers ───────────────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text: str


def _require_voice() -> None:
    if not voice_service:
        raise HTTPException(
            status_code=503,
            detail="Voice service not configured. Set ELEVENLABS_API_KEY in backend/.env and run: pip install -r requirements.txt",
        )


# ── REST endpoints ────────────────────────────────────────────────────────────

@router.get("/api/voice/status")
async def voice_status() -> JSONResponse:
    """Diagnose voice service configuration."""
    try:
        import elevenlabs  # noqa: F401
        pkg_installed = True
    except ImportError:
        pkg_installed = False

    from ..config import settings
    return JSONResponse({
        "configured": voice_service is not None,
        "key_set": bool(settings.elevenlabs_api_key),
        "package_installed": pkg_installed,
        "voice_id": settings.elevenlabs_voice_id,
        "model": settings.elevenlabs_model,
    })


class TextChatRequest(BaseModel):
    text: str


@router.post("/api/voice/text-chat")
async def voice_text_chat(request: TextChatRequest) -> Response:
    """
    Text-in, audio-out. Browser Web Speech API handles STT; this endpoint
    routes to the correct agent and returns ElevenLabs TTS audio.
    Works even without ElevenLabs — returns empty audio but text in headers.
    """
    try:
        intent = _detect_intent(request.text)
        agent_name, response_text = await _route_to_agent(intent, request.text)

        await hub.broadcast("thinking", {
            "type": "thinking",
            "line": f"{agent_name} (voice/{intent}): {response_text[:140]}",
            "ts": time.time(),
        })

        audio_out = b""
        if voice_service:
            try:
                audio_out = await voice_service.synthesize_async(response_text)
            except Exception as tts_exc:
                print(f"[Voice] TTS failed: {tts_exc}")

        return Response(
            content=audio_out,
            media_type="audio/mpeg",
            headers={
                "X-Response": quote(response_text[:500], safe=""),
                "X-Agent": quote(agent_name, safe=""),
                "X-Intent": intent,
                "Access-Control-Expose-Headers": "X-Response, X-Agent, X-Intent",
            },
        )
    except Exception as exc:
        print(f"[Voice] voice_text_chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/voice/speak")
async def speak(request: SpeakRequest) -> Response:
    """TTS: text → MP3 audio bytes."""
    _require_voice()
    try:
        audio_bytes = await voice_service.synthesize_async(request.text)  # type: ignore[union-attr]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS error: {exc}")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> JSONResponse:
    """STT: uploaded audio → transcript text."""
    _require_voice()
    audio_bytes = await file.read()
    text = await voice_service.transcribe_async(audio_bytes, file.filename or "audio.webm")  # type: ignore[union-attr]
    return JSONResponse({"text": text})


@router.post("/api/voice/chat")
async def voice_chat(file: UploadFile = File(...)) -> Response:
    """
    Full voice loop with keyword-based agent routing:
      mic audio → STT → detect intent → route to agent → TTS → MP3

    Response headers:
      X-Transcript  — what the user said
      X-Response    — agent text reply
      X-Intent      — detected intent (vision / talk / track / chat)
      X-Agent       — which agent handled it
    """
    _require_voice()
    audio_bytes = await file.read()

    # 1. STT
    transcript = await voice_service.transcribe_async(audio_bytes, file.filename or "audio.webm")  # type: ignore[union-attr]

    # 2. Detect intent from keywords
    intent = _detect_intent(transcript)

    # 3. Route to correct agent
    agent_name, response_text = await _route_to_agent(intent, transcript)

    # 4. Broadcast to thinking feed
    await hub.broadcast("thinking", {
        "type": "thinking",
        "line": f"{agent_name} (voice/{intent}): {response_text[:140]}",
        "ts": time.time(),
    })

    # 5. TTS
    audio_out = await voice_service.synthesize_async(response_text)  # type: ignore[union-attr]

    return Response(
        content=audio_out,
        media_type="audio/mpeg",
        headers={
            "X-Transcript": quote(transcript[:500], safe=""),
            "X-Response": quote(response_text[:500], safe=""),
            "X-Intent": intent,
            "X-Agent": quote(agent_name, safe=""),
            "Access-Control-Expose-Headers": "X-Transcript, X-Response, X-Intent, X-Agent",
        },
    )


# ── WebSockets ────────────────────────────────────────────────────────────────

@router.websocket("/ws/voice")
async def voice_push_ws(websocket: WebSocket) -> None:
    """Server-push channel: receives MP3 bytes for fall / IR / vision alerts."""
    await hub.subscribe(websocket, "voice")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "voice")


@router.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket) -> None:
    """Bidirectional: client sends binary audio, server replies JSON + MP3."""
    await websocket.accept()
    if not voice_service:
        await websocket.send_json({"error": "Voice service not configured."})
        await websocket.close()
        return
    try:
        while True:
            audio_in = await websocket.receive_bytes()
            transcript = await voice_service.transcribe_async(audio_in)
            await websocket.send_json({"type": "transcript", "text": transcript})

            intent = _detect_intent(transcript)
            agent_name, response_text = await _route_to_agent(intent, transcript)
            await websocket.send_json({"type": "response", "text": response_text, "agent": agent_name, "intent": intent})

            audio_out = await voice_service.synthesize_async(response_text)
            await websocket.send_bytes(audio_out)
    except WebSocketDisconnect:
        pass
