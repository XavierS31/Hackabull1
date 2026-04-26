import threading
import time
from collections import deque

import cv2
import numpy as np


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
