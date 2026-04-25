import asyncio
import base64
import json
import os
import re
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemma_model: str = "gemma-4"
    allowed_origins: str = "http://localhost:5173"
    events_dir: str = "data/events"
    fall_threshold_g: float = 2.4
    pre_event_seconds: int = 10
    post_event_seconds: int = 10
    imu_udp_host: str = "0.0.0.0"
    imu_udp_port: int = 9002
    glasses_stream_url: str = ""
    glove_stream_url: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


class CameraConfig(BaseModel):
    url: str = Field(min_length=1)


class ToggleAgent(BaseModel):
    enabled: bool


class ImuPacket(BaseModel):
    x: float
    y: float
    z: float
    ir_triggered: bool = False
    timestamp: float | None = None


class CriticalEvent(BaseModel):
    id: str
    type: str
    timestamp: float
    trigger: str
    media: dict[str, str]


SYSTEM_PROMPT = """
You are an onboarding classifier for a medical agentic assistant system.
Return JSON only. Do not include markdown. Schema:
{
  "patient_profile": {
    "name": "string",
    "dob": "string",
    "conditions": ["string"],
    "allergies": ["string"],
    "medications": ["string"],
    "emergency_contact": "string"
  },
  "active_agents": [
    {
      "name": "Medication Monitor | Fall Guardian | Memory Cue Coach | Vision Navigator",
      "enabled": true,
      "reason": "string"
    }
  ],
  "thinking": [
    "Step-by-step reasoning sentence 1",
    "Step-by-step reasoning sentence 2"
  ]
}
Always include at least one active agent.
""".strip()


def extract_json(payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if payload.startswith("{"):
        return json.loads(payload)
    match = re.search(r"\{.*\}", payload, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


class FrameStore:
    def __init__(self, pre_seconds: int, post_seconds: int):
        self.latest_jpeg: dict[str, bytes] = {}
        self.buffers: dict[str, deque[tuple[float, np.ndarray]]] = {}
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.lock = threading.Lock()

    def add_frame(self, camera: str, frame: np.ndarray) -> None:
        now = time.time()
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok:
            return
        with self.lock:
            if camera not in self.buffers:
                self.buffers[camera] = deque()
            self.latest_jpeg[camera] = jpeg.tobytes()
            self.buffers[camera].append((now, frame.copy()))
            cutoff = now - (self.pre_seconds + self.post_seconds + 2)
            while self.buffers[camera] and self.buffers[camera][0][0] < cutoff:
                self.buffers[camera].popleft()

    def get_latest_jpeg(self, camera: str) -> bytes | None:
        with self.lock:
            return self.latest_jpeg.get(camera)

    def clip_frames(self, camera: str, start_ts: float, end_ts: float) -> list[np.ndarray]:
        with self.lock:
            buf = list(self.buffers.get(camera, []))
        return [frame for ts, frame in buf if start_ts <= ts <= end_ts]


class CameraManager:
    def __init__(self, frame_store: FrameStore):
        self.frame_store = frame_store
        self.threads: dict[str, threading.Thread] = {}
        self.stop_flags: dict[str, threading.Event] = {}
        self.urls: dict[str, str] = {}

    def start(self, camera: str, url: str) -> None:
        self.stop(camera)
        stop_event = threading.Event()
        self.stop_flags[camera] = stop_event
        self.urls[camera] = url
        thread = threading.Thread(target=self._run, args=(camera, url, stop_event), daemon=True)
        self.threads[camera] = thread
        thread.start()

    def stop(self, camera: str) -> None:
        stop_event = self.stop_flags.get(camera)
        if stop_event:
            stop_event.set()
        thread = self.threads.get(camera)
        if thread and thread.is_alive():
            thread.join(timeout=1.5)

    def stop_all(self) -> None:
        for camera in list(self.threads.keys()):
            self.stop(camera)

    def _run(self, camera: str, url: str, stop_event: threading.Event) -> None:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            return
        while not stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.1)
                continue
            self.frame_store.add_frame(camera, frame)
        cap.release()


class EventRecorder:
    def __init__(self, frame_store: FrameStore, events_dir: Path, pre_seconds: int, post_seconds: int):
        self.frame_store = frame_store
        self.events_dir = events_dir
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.events: list[CriticalEvent] = []
        self.lock = threading.Lock()
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def trigger_fall(self, trigger: str) -> str:
        event_id = str(uuid.uuid4())
        trigger_ts = time.time()
        worker = threading.Thread(
            target=self._finalize_event,
            args=(event_id, trigger_ts, trigger),
            daemon=True,
        )
        worker.start()
        return event_id

    def list_events(self) -> list[CriticalEvent]:
        with self.lock:
            return list(self.events)

    def _finalize_event(self, event_id: str, trigger_ts: float, trigger: str) -> None:
        time.sleep(self.post_seconds)
        start_ts = trigger_ts - self.pre_seconds
        end_ts = trigger_ts + self.post_seconds
        media: dict[str, str] = {}
        for camera in ("glasses", "glove"):
            frames = self.frame_store.clip_frames(camera, start_ts, end_ts)
            if not frames:
                continue
            output_path = self.events_dir / f"{event_id}_{camera}.mp4"
            self._write_mp4(frames, output_path)
            media[camera] = f"/api/events/media/{output_path.name}"

        event = CriticalEvent(
            id=event_id,
            type="fall",
            timestamp=trigger_ts,
            trigger=trigger,
            media=media,
        )
        with self.lock:
            self.events.insert(0, event)
            self.events = self.events[:150]

    @staticmethod
    def _write_mp4(frames: list[np.ndarray], output_path: Path) -> None:
        h, w = frames[0].shape[:2]
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            12.0,
            (w, h),
        )
        for frame in frames:
            writer.write(frame)
        writer.release()


class BroadcastHub:
    def __init__(self):
        self.thinking_clients: set[WebSocket] = set()
        self.status_clients: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def subscribe(self, socket: WebSocket, channel: str) -> None:
        await socket.accept()
        async with self.lock:
            if channel == "thinking":
                self.thinking_clients.add(socket)
            else:
                self.status_clients.add(socket)

    async def unsubscribe(self, socket: WebSocket, channel: str) -> None:
        async with self.lock:
            target = self.thinking_clients if channel == "thinking" else self.status_clients
            target.discard(socket)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> None:
        async with self.lock:
            targets = list(self.thinking_clients if channel == "thinking" else self.status_clients)
        for socket in targets:
            try:
                await socket.send_json(payload)
            except Exception:
                await self.unsubscribe(socket, channel)


settings = Settings()
backend_dir = Path(__file__).resolve().parents[1]
events_dir = Path(settings.events_dir)
if not events_dir.is_absolute():
    events_dir = backend_dir / events_dir
app = FastAPI(title="Medical Agentic AI Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frame_store = FrameStore(settings.pre_event_seconds, settings.post_event_seconds)
camera_manager = CameraManager(frame_store)
event_recorder = EventRecorder(
    frame_store=frame_store,
    events_dir=events_dir,
    pre_seconds=settings.pre_event_seconds,
    post_seconds=settings.post_event_seconds,
)
hub = BroadcastHub()

patient_profile: dict[str, Any] = {}
agent_status: dict[str, bool] = {
    "Medication Monitor": False,
    "Fall Guardian": True,
    "Memory Cue Coach": False,
    "Vision Navigator": True,
}


async def handle_imu_packet(packet: ImuPacket) -> None:
    packet_ts = packet.timestamp or time.time()
    if packet_ts < 1_000_000_000:
        packet_ts = time.time()
    magnitude_g = float((packet.x**2 + packet.y**2 + packet.z**2) ** 0.5)
    if magnitude_g >= settings.fall_threshold_g:
        event_id = event_recorder.trigger_fall(trigger="imu")
        await hub.broadcast(
            "thinking",
            {
                "type": "thinking",
                "line": f"IMU threshold exceeded ({magnitude_g:.2f}g). Event {event_id} recording started.",
                "ts": packet_ts,
            },
        )
    if packet.ir_triggered:
        await hub.broadcast(
            "thinking",
            {
                "type": "thinking",
                "line": "IR proximity trigger detected by glove node.",
                "ts": packet_ts,
            },
        )


class UdpImuProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def datagram_received(self, data: bytes, addr: Any) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
            packet = ImuPacket(**payload)
        except Exception:
            return
        self.loop.create_task(handle_imu_packet(packet))


async def call_gemma_with_qr(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing in backend/.env.")

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "parts": [
                    {"text": "Parse this medical onboarding QR image and classify active agents."},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemma_model}:generateContent?key={settings.gemini_api_key}"
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model response shape: {exc}") from exc
    try:
        return extract_json(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model returned invalid JSON: {exc}") from exc


@app.on_event("startup")
async def on_startup() -> None:
    loop = asyncio.get_running_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: UdpImuProtocol(loop),
        local_addr=(settings.imu_udp_host, settings.imu_udp_port),
    )
    app.state.imu_udp_transport = transport
    if settings.glasses_stream_url:
        camera_manager.start("glasses", settings.glasses_stream_url)
    if settings.glove_stream_url:
        camera_manager.start("glove", settings.glove_stream_url)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    transport = getattr(app.state, "imu_udp_transport", None)
    if transport:
        transport.close()
    camera_manager.stop_all()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/onboarding/qr")
async def parse_onboarding_qr(file: UploadFile = File(...)) -> JSONResponse:
    content = await file.read()
    result = await call_gemma_with_qr(content, file.content_type or "image/png")
    profile = result.get("patient_profile", {})
    agents = result.get("active_agents", [])
    thinking = result.get("thinking", [])

    patient_profile.clear()
    patient_profile.update(profile)
    for agent in agents:
        name = str(agent.get("name", "")).strip()
        if name:
            agent_status[name] = bool(agent.get("enabled", False))

    await hub.broadcast("status", {"type": "agent_status", "data": agent_status})
    for line in thinking:
        await hub.broadcast("thinking", {"type": "thinking", "line": line, "ts": time.time()})

    return JSONResponse(
        {
            "patient_profile": patient_profile,
            "active_agents": agent_status,
            "thinking": thinking,
        }
    )


@app.get("/api/patient")
async def get_patient_profile() -> dict[str, Any]:
    return patient_profile


@app.get("/api/agents")
async def get_agents() -> dict[str, bool]:
    return agent_status


@app.post("/api/agents/{agent_name}")
async def set_agent_status(agent_name: str, toggle: ToggleAgent) -> dict[str, Any]:
    agent_status[agent_name] = toggle.enabled
    await hub.broadcast("status", {"type": "agent_status", "data": agent_status})
    return {"name": agent_name, "enabled": toggle.enabled}


@app.post("/api/cameras/{camera}/start")
async def start_camera(camera: str, config: CameraConfig) -> dict[str, str]:
    if camera not in ("glasses", "glove"):
        raise HTTPException(status_code=400, detail="Camera must be 'glasses' or 'glove'.")
    camera_manager.start(camera, config.url)
    return {"camera": camera, "status": "started", "url": config.url}


@app.get("/api/stream/frame/{camera}")
async def latest_frame(camera: str) -> Response:
    jpeg = frame_store.get_latest_jpeg(camera)
    if not jpeg:
        raise HTTPException(status_code=404, detail=f"No frame available for camera '{camera}'.")
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/events")
async def list_events() -> list[CriticalEvent]:
    return event_recorder.list_events()


@app.get("/api/events/media/{filename}")
async def event_media(filename: str) -> Response:
    path = events_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media not found.")
    return Response(content=path.read_bytes(), media_type="video/mp4")


@app.post("/api/events/fall-test")
async def trigger_test_fall() -> dict[str, str]:
    event_id = event_recorder.trigger_fall(trigger="manual_test")
    await hub.broadcast(
        "thinking",
        {
            "type": "thinking",
            "line": f"Fall Guardian created event {event_id}. Capturing +/-10s clip.",
            "ts": time.time(),
        },
    )
    return {"event_id": event_id}


@app.websocket("/ws/thinking")
async def thinking_ws(websocket: WebSocket) -> None:
    await hub.subscribe(websocket, "thinking")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "thinking")


@app.websocket("/ws/status")
async def status_ws(websocket: WebSocket) -> None:
    await hub.subscribe(websocket, "status")
    try:
        await websocket.send_json({"type": "agent_status", "data": agent_status})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "status")


@app.websocket("/ws/imu")
async def imu_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        payload = await websocket.receive_json()
        packet = ImuPacket(**payload)
        await handle_imu_packet(packet)
