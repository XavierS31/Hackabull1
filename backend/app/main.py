import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import agents, cameras, chat, events, hardware, onboarding, voice, ws

try:
    from .routes import twilio_call as _twilio_call_mod
except ImportError:
    _twilio_call_mod = None  # type: ignore[assignment]
    print("[Twilio] 'twilio' package not installed — call endpoints disabled. Run: pip install twilio")
from .services.imu import UdpImuProtocol
from .state import camera_manager

app = FastAPI(title="Medical Agentic AI Orchestrator", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Transcript", "X-Response"],
)

# Register all route modules
app.include_router(onboarding.router)
app.include_router(agents.router)
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(hardware.router)
if _twilio_call_mod:
    app.include_router(_twilio_call_mod.router)
app.include_router(ws.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


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
