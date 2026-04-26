from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..models import ImuPacket
from ..services.imu import handle_imu_packet
from ..state import agent_status, hub

router = APIRouter()


@router.websocket("/ws/thinking")
async def thinking_ws(websocket: WebSocket) -> None:
    await hub.subscribe(websocket, "thinking")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "thinking")


@router.websocket("/ws/status")
async def status_ws(websocket: WebSocket) -> None:
    await hub.subscribe(websocket, "status")
    try:
        await websocket.send_json({"type": "agent_status", "data": agent_status})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.unsubscribe(websocket, "status")


@router.websocket("/ws/imu")
async def imu_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    while True:
        payload = await websocket.receive_json()
        packet = ImuPacket(**payload)
        await handle_imu_packet(packet)
