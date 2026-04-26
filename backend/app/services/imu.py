import asyncio
import json
import time
from typing import Any

import httpx

from ..config import settings
from ..models import ImuPacket
from ..state import activity_log, agent_status, append_activity, event_recorder, hub, patient_profile, voice_service

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
    """
    Send a GET request to the glove's /buzz endpoint.
    The firmware must expose: GET http://<glove_ip>:81/buzz?freq=<hz>&dur=<ms>
    """
    if not settings.glove_ip:
        return
    url = f"http://{settings.glove_ip}:81/buzz?freq={freq}&dur={dur_ms}"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.get(url)
    except Exception:
        pass  # Glove unreachable — graceful no-op


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
        event_id = event_recorder.trigger_fall(trigger="imu")
        emergency_contact = patient_profile.get("emergency_contact", "emergency services")

        append_activity({
            "ts": packet_ts,
            "type": "fall",
            "magnitude_g": round(magnitude_g, 2),
            "event_id": event_id,
        })

        await hub.broadcast(
            "thinking",
            {
                "type": "thinking",
                "line": (
                    f"Falling Agent: Fall detected ({magnitude_g:.2f}g). "
                    f"Alerting {emergency_contact} + 911. Event {event_id} recording."
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
        append_activity({"ts": packet_ts, "type": "ir", "message": "IR proximity alert"})

        await hub.broadcast(
            "thinking",
            {
                "type": "thinking",
                "line": "Vision Agent: IR proximity alert — obstacle detected by glove sensor.",
                "ts": packet_ts,
            },
        )

        if time.time() - _last_ir_alert_ts > IR_ALERT_COOLDOWN:
            _last_ir_alert_ts = time.time()
            asyncio.create_task(_push_tts("Warning: obstacle detected ahead. Please slow down."))


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
