"""
Voice endpoints — ElevenLabs TTS + STT + WebSocket push channel.

REST:
  POST /api/voice/speak        text → MP3 audio response
  POST /api/voice/transcribe   audio file → transcript text
  POST /api/voice/chat         audio file → STT → Gemma 4 → TTS (full loop)

WebSocket:
  /ws/voice        Server pushes MP3 bytes for fall/IR/vision alerts (subscribe-only)
  /ws/conversation Bidirectional: client sends audio bytes, server replies with TTS audio
"""
import time

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..config import CHATBOT_SYSTEM
from ..services.gemma import call_gemma_text
from ..state import append_activity, frame_store, hub, voice_service

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str


def _require_voice():
    if not voice_service:
        raise HTTPException(
            status_code=503,
            detail="Voice service not configured. Set ELEVENLABS_API_KEY in backend/.env.",
        )


# ---------- REST ----------

@router.post("/api/voice/speak")
async def speak(request: SpeakRequest) -> Response:
    """TTS: text → MP3 audio bytes."""
    _require_voice()
    audio_bytes = await voice_service.synthesize_async(request.text)  # type: ignore[union-attr]
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> JSONResponse:
    """STT: uploaded audio file → transcript text."""
    _require_voice()
    audio_bytes = await file.read()
    text = await voice_service.transcribe_async(audio_bytes, file.filename or "audio.webm")  # type: ignore[union-attr]
    return JSONResponse({"text": text})


@router.post("/api/voice/chat")
async def voice_chat(file: UploadFile = File(...)) -> Response:
    """
    Full voice loop: mic audio → STT → Gemma 4 (+ glasses camera frame) → TTS → MP3.
    Response headers carry X-Transcript and X-Response for the frontend to display.
    """
    _require_voice()
    audio_bytes = await file.read()

    # 1. Speech → text
    text = await voice_service.transcribe_async(audio_bytes, file.filename or "audio.webm")  # type: ignore[union-attr]

    # 2. Attach latest glasses frame if available
    image_bytes = frame_store.get_latest_jpeg("glasses")

    # 3. Gemma 4
    response_text = await call_gemma_text(CHATBOT_SYSTEM, text or "Hello", image_bytes)

    # 4. Log to activity
    append_activity({"ts": time.time(), "type": "voice_chat", "user": text, "agent": response_text})

    # 5. TTS
    audio_out = await voice_service.synthesize_async(response_text)  # type: ignore[union-attr]

    return Response(
        content=audio_out,
        media_type="audio/mpeg",
        headers={
            "X-Transcript": text[:500],
            "X-Response": response_text[:500],
            "Access-Control-Expose-Headers": "X-Transcript, X-Response",
        },
    )


# ---------- WebSockets ----------

@router.websocket("/ws/voice")
async def voice_push_ws(websocket: WebSocket) -> None:
    """
    Subscribe-only channel: server pushes MP3 audio bytes for fall/IR/vision alerts.
    Clients should play received bytes immediately using the Web Audio API.
    """
    await hub.subscribe(websocket, "voice")
    try:
        while True:
            await websocket.receive_text()  # Keep-alive; client sends pings
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "voice")


@router.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket) -> None:
    """
    Bidirectional voice conversation:
      client → binary audio bytes
      server → JSON {"type":"transcript","text":"..."} then binary MP3 bytes
    """
    await websocket.accept()
    if not voice_service:
        await websocket.send_json({"error": "Voice service not configured."})
        await websocket.close()
        return

    try:
        while True:
            # Expect binary audio from the client (WebM/Opus from MediaRecorder)
            audio_in = await websocket.receive_bytes()

            # STT
            text = await voice_service.transcribe_async(audio_in)
            await websocket.send_json({"type": "transcript", "text": text})

            # Gemma 4 with optional camera frame
            image_bytes = frame_store.get_latest_jpeg("glasses")
            response_text = await call_gemma_text(CHATBOT_SYSTEM, text or "Hello", image_bytes)
            await websocket.send_json({"type": "response", "text": response_text})

            append_activity({
                "ts": time.time(),
                "type": "voice_chat",
                "user": text,
                "agent": response_text,
            })

            # TTS → send MP3 bytes back
            audio_out = await voice_service.synthesize_async(response_text)
            await websocket.send_bytes(audio_out)

    except WebSocketDisconnect:
        pass
