import threading
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from ..models import CriticalEvent
from ..services import firebase_service
from .frame_store import FrameStore


class EventRecorder:
    def __init__(self, frame_store: FrameStore, events_dir: Path, pre_seconds: int, post_seconds: int):
        self.frame_store = frame_store
        self.events_dir = events_dir
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.events: list[CriticalEvent] = []
        self.lock = threading.Lock()
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def trigger_fall(self, trigger: str, notified: list[str] | None = None) -> str:
        event_id = str(uuid.uuid4())
        trigger_ts = time.time()
        worker = threading.Thread(
            target=self._finalize_event,
            args=(event_id, trigger_ts, trigger, list(notified or [])),
            daemon=True,
        )
        worker.start()
        return event_id

    def list_events(self) -> list[CriticalEvent]:
        with self.lock:
            return list(self.events)

    def _finalize_event(
        self, event_id: str, trigger_ts: float, trigger: str, notified: list[str]
    ) -> None:
        time.sleep(self.post_seconds)
        start_ts = trigger_ts - self.pre_seconds
        end_ts = trigger_ts + self.post_seconds

        # Save clips locally first, then try Firebase upload
        local_paths: dict[str, Path] = {}
        media: dict[str, str] = {}

        for camera in ("glasses", "glove"):
            frames = self.frame_store.clip_frames(camera, start_ts, end_ts)
            if not frames:
                continue
            output_path = self.events_dir / f"{event_id}_{camera}.mp4"
            self._write_mp4(frames, output_path)
            local_paths[camera] = output_path
            media[camera] = f"/api/events/media/{output_path.name}"  # local fallback

        # Attempt Firebase Storage upload (overwrites URL with public CDN link)
        for camera, local_path in local_paths.items():
            firebase_url = firebase_service.upload_video(local_path, event_id, camera)
            if firebase_url:
                media[camera] = firebase_url

        event = CriticalEvent(
            id=event_id,
            type="fall",
            timestamp=trigger_ts,
            trigger=trigger,
            media=media,
            notified=notified,
        )

        # Persist metadata to Firestore
        firebase_service.save_event_metadata(event.model_dump())

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
