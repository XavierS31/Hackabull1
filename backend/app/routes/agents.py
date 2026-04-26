from typing import Any

from fastapi import APIRouter

from ..models import ToggleAgent
from ..state import agent_status, hub, patient_profile

router = APIRouter()


@router.get("/api/patient")
async def get_patient_profile() -> dict[str, Any]:
    return patient_profile


@router.get("/api/agents")
async def get_agents() -> dict[str, bool]:
    return agent_status


@router.post("/api/agents/{agent_name}")
async def set_agent_status(agent_name: str, toggle: ToggleAgent) -> dict[str, Any]:
    agent_status[agent_name] = toggle.enabled
    await hub.broadcast("status", {"type": "agent_status", "data": agent_status})
    return {"name": agent_name, "enabled": toggle.enabled}
