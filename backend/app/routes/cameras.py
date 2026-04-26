from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..models import CameraConfig
from ..state import camera_manager, frame_store

router = APIRouter()


@router.post("/api/cameras/{camera}/start")
async def start_camera(camera: str, config: CameraConfig) -> dict[str, str]:
    if camera not in ("glasses", "glove"):
        raise HTTPException(status_code=400, detail="Camera must be 'glasses' or 'glove'.")
    camera_manager.start(camera, config.url)
    return {"camera": camera, "status": "started", "url": config.url}


@router.get("/api/stream/frame/{camera}")
async def latest_frame(camera: str) -> Response:
    jpeg = frame_store.get_latest_jpeg(camera)
    if not jpeg:
        raise HTTPException(status_code=404, detail=f"No frame available for camera '{camera}'.")
    return Response(content=jpeg, media_type="image/jpeg")
