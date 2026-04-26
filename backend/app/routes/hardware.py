"""
Hardware command endpoints — send HTTP commands back to ESP32 nodes.

Node B (glove) firmware must expose:
  GET http://<glove_ip>:81/buzz?freq=<hz>&dur=<ms>

Node A (glasses) is camera-only and has no command endpoint.
"""
import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings

router = APIRouter()

_NODE_URLS = {
    "glove": lambda: f"http://{settings.glove_ip}:81",
    "glasses": lambda: f"http://{settings.glasses_ip}:81",
}


@router.post("/api/hardware/glove/buzz")
async def buzz_glove(freq: int = 1100, dur: int = 500) -> JSONResponse:
    """
    Trigger the glove's I2S speaker to emit a beep tone.
    freq — frequency in Hz (default 1100)
    dur  — duration in milliseconds (default 500)
    """
    base = _NODE_URLS["glove"]()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base}/buzz?freq={freq}&dur={dur}")
        return JSONResponse({"sent": True, "status": resp.status_code, "node": "glove"})
    except Exception as exc:
        return JSONResponse({"sent": False, "error": str(exc), "node": "glove"}, status_code=502)


@router.get("/api/hardware/{node}/status")
async def node_status(node: str) -> JSONResponse:
    """Ping an ESP32 node's root HTTP endpoint to check if it's reachable."""
    if node not in _NODE_URLS:
        return JSONResponse({"error": f"Unknown node '{node}'"}, status_code=400)
    base = _NODE_URLS[node]()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(base)
        return JSONResponse({"online": True, "node": node, "http_status": resp.status_code})
    except Exception:
        return JSONResponse({"online": False, "node": node})
