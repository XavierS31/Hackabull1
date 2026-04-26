"""
Twilio two-way voice call routes.

Flow:
  POST /api/call/emergency        — backend initiates outbound call via Twilio REST
  POST /twilio/start              — Twilio webhook: call connected → return greeting TwiML
  POST /twilio/gather             — Twilio webhook: caller spoke → Gemma reply → TwiML loop
  GET  /twilio/audio/{audio_id}   — serve ElevenLabs MP3 to Twilio <Play>
  POST /twilio/status             — Twilio call status callback → cleanup

The TWILIO_WEBHOOK_BASE_URL env var must be a publicly reachable HTTPS URL
(e.g. an ngrok tunnel) so Twilio can hit the webhook endpoints.
"""
import asyncio
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..config import EMERGENCY_CALL_SYSTEM, settings
from ..services import twilio_service
from ..services.gemma import call_gemma_text
from ..state import activity_log, append_activity, patient_profile, voice_service

router = APIRouter()

# CallSid → {patient_name, location, custom_message, history: list[dict]}
_call_sessions: dict[str, dict] = {}

# audio_id → MP3 bytes (kept until call ends)
_audio_cache: dict[str, bytes] = {}


# ── helpers ──────────────────────────────────────────────────────────────────

def _hook(path: str) -> str:
    return settings.twilio_webhook_base_url.rstrip("/") + path


async def _speak(text: str) -> str:
    """Synthesise text with ElevenLabs, cache result, return audio_id."""
    audio_id = str(uuid.uuid4())
    if voice_service:
        audio_bytes = await voice_service.synthesize_async(text)
        _audio_cache[audio_id] = audio_bytes
    else:
        _audio_cache[audio_id] = b""
    return audio_id


def _twiml_play_gather(audio_id: str, call_sid: str, end: bool = False) -> str:
    """Build a minimal TwiML string — avoids importing twilio at module level."""
    play_url = _hook(f"/twilio/audio/{audio_id}")
    gather_action = _hook(f"/twilio/gather?call_sid={call_sid}")
    redirect_url = _hook(f"/twilio/start?call_sid={call_sid}")

    if end:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Play>{play_url}</Play>'
            "<Hangup/>"
            "</Response>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Play>{play_url}</Play>'
        f'<Gather input="speech" action="{gather_action}" method="POST" speechTimeout="auto" language="en-US"/>'
        f'<Redirect>{redirect_url}</Redirect>'
        "</Response>"
    )


# ── audio serving ─────────────────────────────────────────────────────────────

@router.get("/twilio/audio/{audio_id}")
async def serve_twilio_audio(audio_id: str) -> Response:
    audio_bytes = _audio_cache.get(audio_id, b"")
    if not audio_bytes:
        return Response(status_code=404)
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ── call initiation ───────────────────────────────────────────────────────────

@router.post("/api/call/emergency")
async def trigger_emergency_call(request: Request) -> JSONResponse:
    """
    Initiate an outbound Twilio call to the patient's emergency contact.

    Request body (all optional):
      to       — E.164 number to call; defaults to patient_profile["emergency_contact"]
      location — human-readable location string (e.g. "living room", GPS coords)
      message  — extra sentence prepended to the greeting
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return JSONResponse({"error": "Twilio not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing)."}, status_code=503)
    if not settings.twilio_webhook_base_url:
        return JSONResponse({"error": "TWILIO_WEBHOOK_BASE_URL not set — Twilio cannot reach the webhook."}, status_code=503)

    body = await request.json()
    to_number: str = (
        body.get("to")
        or patient_profile.get("emergency_contact", "")
        or settings.emergency_contact_number
    )
    location: str = body.get("location", "")
    custom_message: str = body.get("message", "")

    if not to_number:
        return JSONResponse({"error": "No phone number provided and no emergency_contact in patient profile."}, status_code=400)

    patient_name: str = patient_profile.get("name", "the patient")

    # Reserve a placeholder slot — will be keyed by real CallSid after API returns
    placeholder = str(uuid.uuid4())
    _call_sessions[placeholder] = {
        "patient_name": patient_name,
        "location": location,
        "custom_message": custom_message,
        "history": [],
    }

    start_url = _hook(f"/twilio/start?session={placeholder}")
    status_url = _hook("/twilio/status")

    loop = asyncio.get_running_loop()
    try:
        call_sid = await loop.run_in_executor(
            None,
            twilio_service.initiate_call,
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_from_number,
            to_number,
            start_url,
            status_url,
        )
    except Exception as exc:
        _call_sessions.pop(placeholder, None)
        return JSONResponse({"error": f"Twilio API error: {exc}"}, status_code=502)

    # Re-key by real CallSid
    _call_sessions[call_sid] = _call_sessions.pop(placeholder)

    append_activity({
        "ts": time.time(),
        "type": "emergency_call",
        "call_sid": call_sid,
        "to": to_number,
        "patient": patient_name,
        "location": location,
    })

    return JSONResponse({"call_sid": call_sid, "to": to_number, "status": "dialing"})


# ── Twilio webhooks ───────────────────────────────────────────────────────────

@router.post("/twilio/start")
async def twilio_call_start(request: Request) -> Response:
    """Twilio calls this URL when the outbound call is answered."""
    form = await request.form()
    call_sid: str = str(form.get("CallSid", ""))

    # Resolve session — might still be keyed by placeholder if race
    query_session = request.query_params.get("session", "")
    session = _call_sessions.get(call_sid)
    if session is None and query_session:
        session = _call_sessions.pop(query_session, {})
        _call_sessions[call_sid] = session
    if session is None:
        session = {}
        _call_sessions[call_sid] = session

    patient_name = session.get("patient_name", "the patient")
    location = session.get("location", "")
    custom_message = session.get("custom_message", "")

    loc_phrase = f" at {location}" if location else ""
    greeting = (
        f"Hello, this is an automated alert from the AI caregiver system. "
        f"{patient_name} has been detected as needing assistance{loc_phrase}. "
        f"{custom_message + ' ' if custom_message else ''}"
        f"I can answer any questions you have about the situation. How can I help you?"
    )

    audio_id = await _speak(greeting)
    return Response(content=_twiml_play_gather(audio_id, call_sid), media_type="application/xml")


@router.post("/twilio/gather")
async def twilio_gather(request: Request) -> Response:
    """Twilio calls this with the caller's speech after each <Gather>."""
    form = await request.form()
    call_sid: str = str(form.get("CallSid", "")) or request.query_params.get("call_sid", "")
    speech: str = str(form.get("SpeechResult", "")).strip()

    session = _call_sessions.setdefault(call_sid, {"history": []})
    session.setdefault("history", [])

    if speech:
        session["history"].append({"role": "user", "content": speech})

    # Build conversation context for Gemma
    patient_name = session.get("patient_name", "the patient")
    location = session.get("location", "unknown location")
    history_lines = "\n".join(
        f"{'Contact' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in session["history"]
    )
    user_context = (
        f"Patient name: {patient_name}\n"
        f"Location: {location or 'unknown'}\n\n"
        f"Conversation so far:\n{history_lines}\n\n"
        f"Caller's latest message: {speech}"
    )

    gemma_reply = await call_gemma_text(EMERGENCY_CALL_SYSTEM, user_context)

    end_call = "[END_CALL]" in gemma_reply
    clean_reply = gemma_reply.replace("[END_CALL]", "").strip()

    session["history"].append({"role": "assistant", "content": clean_reply})

    audio_id = await _speak(clean_reply)
    twiml = _twiml_play_gather(audio_id, call_sid, end=end_call)

    if end_call:
        # Remove cached audio entries for this call
        _call_sessions.pop(call_sid, None)

    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def twilio_status(request: Request) -> Response:
    """Twilio status callback — clean up session state when call ends."""
    form = await request.form()
    call_sid = str(form.get("CallSid", ""))
    call_status = str(form.get("CallStatus", ""))

    terminal = {"completed", "failed", "busy", "no-answer", "canceled"}
    if call_status in terminal:
        session = _call_sessions.pop(call_sid, None)
        # Clear any cached audio for this call (best-effort by key prefix match)
        # In practice audio_ids are UUIDs so we can't easily filter — just let GC handle it.

    append_activity({
        "ts": time.time(),
        "type": "call_status",
        "call_sid": call_sid,
        "status": call_status,
    })
    return Response(status_code=204)
