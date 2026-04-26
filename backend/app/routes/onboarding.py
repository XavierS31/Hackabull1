import time

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from ..services.gemma import call_gemma_with_qr
from ..state import agent_status, hub, patient_profile

router = APIRouter()


@router.post("/api/onboarding/qr")
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
        if name in agent_status:
            agent_status[name] = bool(agent.get("enabled", False))

    await hub.broadcast("status", {"type": "agent_status", "data": agent_status})
    for line in thinking:
        await hub.broadcast("thinking", {"type": "thinking", "line": line, "ts": time.time()})

    return JSONResponse({
        "patient_profile": patient_profile,
        "active_agents": agent_status,
        "thinking": thinking,
    })
