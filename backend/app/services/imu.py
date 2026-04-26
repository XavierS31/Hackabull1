import asyncio
import json
import time
from typing import Any

import httpx

from ..config import VISION_SYSTEM, settings
from ..models import ImuPacket
from ..services.gemma import call_gemma_text
from ..state import (
    agent_status,
    append_activity,
    event_recorder,
    frame_store,
    hub,
    patient_profile,
    voice_service,
)

# Cooldown timestamps to avoid flooding TTS/buzz on every UDP packet
_last_fall_alert_ts: float = 0.0
_last_ir_alert_ts: float = 0.0
FALL_ALERT_COOLDOWN = 30.0   # seconds between repeated fall TTS alerts
IR_ALERT_COOLDOWN = 5.0      # seconds between repeated IR TTS alerts


# ---------- Internal helpers ----------

async def _push_tts(text: str) -> None:
    """Synthesize text and push MP3 to all subscribed voice clients."""
    if not voice_service:
        return
    try:
        audio = await voice_service.synthesize_async(text)
        await hub.broadcast_audio(audio)
    except Exception as exc:
        print(f"[Voice] TTS push failed: {exc}")


async def _buzz_glove(freq: int = 1100, dur_ms: int = 800) -> None:
    """Hit the glove's /buzz endpoint (passive buzzer on GPIO 12). No-op on failure."""
    if not settings.glove_ip:
        return
    url = f"http://{settings.glove_ip}:81/buzz?freq={freq}&dur={dur_ms}"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.get(url)
    except Exception:
        pass


async def _handle_ir_alert(packet_ts: float) -> None:
    """
    IR proximity → call Vision Agent on the latest glove frame, log it,
    push thinking line + TTS, and buzz the glove.
    """
    image_bytes = frame_store.get_latest_jpeg("glove") or frame_store.get_latest_jpeg("glasses")

    if image_bytes:
        description = await call_gemma_text(
            VISION_SYSTEM,
            "An IR proximity sensor on the patient's glove just fired. "
            "Briefly describe the obstacle ahead and how to avoid it.",
            image_bytes,
        )
    else:
        description = "Obstacle detected ahead by glove sensor. Please slow down."

    append_activity({
        "ts": packet_ts,
        "type": "ir",
        "message": "IR proximity alert",
        "description": description,
    })

    await hub.broadcast(
        "thinking",
        {
            "type": "thinking",
            "line": f"Vision Agent (IR): {description[:140]}",
            "ts": packet_ts,
        },
    )

    asyncio.create_task(_push_tts(description))
    asyncio.create_task(_buzz_glove(freq=1500, dur_ms=200))


# ---------- Main packet handler ----------

async def handle_imu_packet(packet: ImuPacket) -> None:
    """Process one IMU/IR frame: detect falls, trigger alerts, log activity."""
    global _last_fall_alert_ts, _last_ir_alert_ts

    packet_ts = packet.timestamp or time.time()
    if packet_ts < 1_000_000_000:
        packet_ts = time.time()

    magnitude_g = float((packet.x**2 + packet.y**2 + packet.z**2) ** 0.5)

    # ---- Falling Agent ----
    if magnitude_g >= settings.fall_threshold_g and agent_status.get("Falling Agent", True):
        emergency_contact = patient_profile.get("emergency_contact", "emergency services")
        notified = ["911", emergency_contact]
        event_id = event_recorder.trigger_fall(trigger="imu", notified=notified)

        append_activity({
            "ts": packet_ts,
            "type": "fall",
            "magnitude_g": round(magnitude_g, 2),
            "event_id": event_id,
            "notified": notified,
        })

        await hub.broadcast(
            "thinking",
            {
                "type": "thinking",
                "line": (
                    f"Falling Agent: Fall detected ({magnitude_g:.2f}g). "
                    f"Notifying {', '.join(notified)}. Event {event_id} recording."
                ),
                "ts": packet_ts,
            },
        )

        # TTS alert + glove buzz (throttled to avoid spam)
        if time.time() - _last_fall_alert_ts > FALL_ALERT_COOLDOWN:
            _last_fall_alert_ts = time.time()
            alert_msg = (
                f"Alert! A fall has been detected. "
                f"Notifying {emergency_contact} and calling 911."
            )
            asyncio.create_task(_push_tts(alert_msg))
            asyncio.create_task(_buzz_glove(freq=1100, dur_ms=800))

    # ---- Vision Agent — IR obstacle ----
    if packet.ir_triggered and agent_status.get("Vision Agent", True):
        if time.time() - _last_ir_alert_ts > IR_ALERT_COOLDOWN:
            _last_ir_alert_ts = time.time()
            asyncio.create_task(_handle_ir_alert(packet_ts))


# ---------- UDP listener ----------

class UdpImuProtocol(asyncio.DatagramProtocol):
    """Receives UDP JSON packets from the glove node (Node B) at 10 Hz."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def datagram_received(self, data: bytes, addr: Any) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
            packet = ImuPacket(**payload)
        except Exception:
            return
        self.loop.create_task(handle_imu_packet(packet))
