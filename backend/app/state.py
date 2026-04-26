from pathlib import Path
from typing import Any

from .config import settings
from .core.camera import CameraManager
from .core.event_recorder import EventRecorder
from .core.frame_store import FrameStore
from .core.hub import BroadcastHub

# Resolve events directory relative to the backend/ folder
_backend_dir = Path(__file__).resolve().parents[1]
events_dir = Path(settings.events_dir)
if not events_dir.is_absolute():
    events_dir = _backend_dir / events_dir

# ---------- Core infrastructure singletons ----------

frame_store = FrameStore(settings.pre_event_seconds, settings.post_event_seconds)
camera_manager = CameraManager(frame_store)
event_recorder = EventRecorder(
    frame_store=frame_store,
    events_dir=events_dir,
    pre_seconds=settings.pre_event_seconds,
    post_seconds=settings.post_event_seconds,
)
hub = BroadcastHub()

# ---------- Mutable application state ----------

patient_profile: dict[str, Any] = {}

agent_status: dict[str, bool] = {
    "Chatbot": True,
    "Falling Agent": True,
    "Conversation Agent": True,
    "Vision Agent": True,
    "Tracking Dementia": True,
}

activity_log: list[dict[str, Any]] = []
MAX_ACTIVITY_LOG = 500


def append_activity(entry: dict[str, Any]) -> None:
    activity_log.append(entry)
    if len(activity_log) > MAX_ACTIVITY_LOG:
        activity_log.pop(0)


# ---------- Optional services ----------

# ElevenLabs voice (TTS + STT)
try:
    from .services.voice import VoiceService

    voice_service: VoiceService | None = (
        VoiceService(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model,
        )
        if settings.elevenlabs_api_key
        else None
    )
except ImportError:
    voice_service = None  # type: ignore[assignment]

if voice_service:
    print("[Voice] ElevenLabs service initialised.")
else:
    print("[Voice] ElevenLabs not configured — set ELEVENLABS_API_KEY to enable.")

# Firebase (Storage + Firestore)
from .services import firebase_service as _fb

firebase_ready: bool = (
    _fb.init_firebase(settings.firebase_service_account, settings.firebase_storage_bucket)
    if settings.firebase_service_account and settings.firebase_storage_bucket
    else False
)
if not firebase_ready:
    print("[Firebase] Not configured — events stored locally only.")
