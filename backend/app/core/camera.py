import threading
import time

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

from .frame_store import FrameStore


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
        if not _CV2:
            return
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
