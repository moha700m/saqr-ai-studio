"""Threaded camera capture with a bounded, drop-oldest frame queue.

A slow consumer must never make the UI lag behind reality: when the queue is
full the oldest frame is discarded and counted. The capture thread only ever
does ``read()``; processing happens on the consumer thread.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Callable

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class CameraInfo:
    index: int
    name: str
    backend: str = ""
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _backend_for_platform() -> int:
    system = platform.system()
    if system == "Windows":
        return cv2.CAP_DSHOW
    if system == "Darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_V4L2


def enumerate_cameras(max_index: int = 6, probe: bool = True) -> list[CameraInfo]:
    """List cameras from the OS when possible, otherwise probe indices."""
    try:
        import cv2_enumerate_cameras  # type: ignore

        cameras = [
            CameraInfo(index=c.index, name=c.name or f"Camera {c.index}", backend=str(c.backend))
            for c in cv2_enumerate_cameras.enumerate_cameras(_backend_for_platform())
        ]
        if cameras:
            return cameras
    except Exception:  # noqa: BLE001 - optional helper
        pass

    if platform.system() == "Linux":
        from pathlib import Path

        cameras = [
            CameraInfo(index=int(path.name.replace("video", "")), name=f"/dev/{path.name}", backend="v4l2")
            for path in sorted(Path("/dev").glob("video*"))
            if path.name[5:].isdigit()
        ]
        if cameras:
            return cameras

    if not probe:
        return []
    found: list[CameraInfo] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, _backend_for_platform())
        if capture is not None and capture.isOpened():
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            found.append(CameraInfo(index=index, name=f"Camera {index}", width=width, height=height))
            capture.release()
    return found


class CameraStream:
    def __init__(
        self,
        index: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        max_queue: int = 2,
        capture_factory: Callable[[int], cv2.VideoCapture] | None = None,
    ):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.max_queue = max(1, max_queue)
        self._factory = capture_factory or (lambda i: cv2.VideoCapture(i, _backend_for_platform()))
        self._queue: deque[tuple[float, np.ndarray]] = deque(maxlen=self.max_queue)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: cv2.VideoCapture | None = None
        self.frames_captured = 0
        self.frames_dropped = 0
        self.capture_fps = 0.0
        self.last_error: str | None = None
        self.started_at: float | None = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> "CameraStream":
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"camera-{self.index}", daemon=True)
        self.started_at = time.time()
        self._thread.start()
        return self

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None
        with self._lock:
            self._queue.clear()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    # ------------------------------------------------------------------ capture
    def _run(self) -> None:
        cap = self._factory(self.index)
        if cap is None or not cap.isOpened():
            self.last_error = f"camera {self.index} could not be opened"
            log.error(self.last_error)
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._capture = cap
        count = 0
        window_start = time.perf_counter()
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    self.last_error = "frame read failed"
                    time.sleep(0.02)
                    continue
                with self._lock:
                    if len(self._queue) == self._queue.maxlen:
                        self.frames_dropped += 1
                    self._queue.append((time.perf_counter(), frame))
                self.frames_captured += 1
                count += 1
                now = time.perf_counter()
                if now - window_start >= 1.0:
                    self.capture_fps = round(count / (now - window_start), 1)
                    count = 0
                    window_start = now
        finally:
            cap.release()
            self._capture = None

    def read(self, timeout: float = 1.0, newest: bool = True) -> tuple[float, np.ndarray] | None:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            with self._lock:
                if self._queue:
                    item = self._queue.pop() if newest else self._queue.popleft()
                    if newest:
                        self._queue.clear()
                    return item
            if not self.running and not self._queue:
                return None
            time.sleep(0.005)
        return None

    def stats(self) -> dict:
        with self._lock:
            queued = len(self._queue)
        return {
            "running": self.running,
            "frames_captured": self.frames_captured,
            "frames_dropped": self.frames_dropped,
            "capture_fps": self.capture_fps,
            "queued": queued,
            "last_error": self.last_error,
            "index": self.index,
        }
