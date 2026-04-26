from pydantic import BaseModel, Field


class CameraConfig(BaseModel):
    url: str = Field(min_length=1)


class ToggleAgent(BaseModel):
    enabled: bool


class ChatRequest(BaseModel):
    message: str
    camera: str | None = None  # "glasses" | "glove" | None


class VisionRequest(BaseModel):
    camera: str = "glasses"


class TrackRequest(BaseModel):
    description: str


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
    notified: list[str] = []
