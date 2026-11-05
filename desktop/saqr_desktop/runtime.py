"""Shared runtime: hardware profile, lazy engine, worker pool, camera thread, bridge."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import cv2
from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal

from saqr_engine.config import Settings
from saqr_engine.hardware.backends import BackendDecision, choose_backend, probe_providers
from saqr_engine.hardware.detection import HardwareProfile, detect_hardware
from saqr_engine.models.manager import ModelManager

log = logging.getLogger(__name__)


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)


class Worker(QRunnable):
    """Run a blocking engine call off the GUI thread."""

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:  # noqa: D401
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            log.exception("worker failed")
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)


class CameraThread(QThread):
    frame_ready = Signal(object)
    failed = Signal(str)
    stats_ready = Signal(dict)

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        super().__init__()
        self.index, self.width, self.height = index, width, height
        self._stop = threading.Event()
        self._capture: cv2.VideoCapture | None = None
        self.frames = 0
        self.fps = 0.0
        self.latest = None

    def run(self) -> None:  # noqa: D401
        self._capture = cv2.VideoCapture(self.index)
        if not self._capture.isOpened():
            self.failed.emit(f"تعذّر فتح الكاميرا رقم {self.index}")
            return
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        start, count = time.perf_counter(), 0
        while not self._stop.is_set():
            ok, frame = self._capture.read()
            if not ok:
                time.sleep(0.02)
                continue
            self.frames += 1
            self.latest = frame
            count += 1
            now = time.perf_counter()
            if now - start >= 1.0:
                self.fps = count / (now - start)
                self.stats_ready.emit({"fps": round(self.fps, 1), "frames": self.frames})
                start, count = now, 0
            self.frame_ready.emit(frame)
        self._capture.release()
        self._capture = None

    def stop(self) -> None:
        self._stop.set()
        self.wait(2000)


class BridgeService(QThread):
    """Run the local FastAPI bridge inside a Qt thread."""

    started = Signal(str)
    code_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.auth = None
        self._server = None

    def run(self) -> None:  # noqa: D401
        try:
            import uvicorn

            from saqr_engine.api.auth import BridgeAuth
            from saqr_engine.api.server import create_app

            self.auth = BridgeAuth(allowed_origins=self.settings.allowed_origins)
            app = create_app(settings=self.settings, auth=self.auth)
            config = uvicorn.Config(app, host=self.settings.api_host, port=self.settings.api_port, log_level="warning")
            self._server = uvicorn.Server(config)
            self.started.emit(f"http://{self.settings.api_host}:{self.settings.api_port}")
            self._server.run()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))

    def new_code(self) -> str:
        if self.auth is None:
            raise RuntimeError("الخادم لم يبدأ بعد")
        code = self.auth.issue_code()["code"]
        self.code_ready.emit(code)
        return code

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        self.wait(3000)


class Runtime(QObject):
    """Owns long-lived objects; pages talk to it instead of to globals."""

    profile_ready = Signal(object)
    decision_ready = Signal(object)
    engine_ready = Signal(object)
    engine_error = Signal(str)

    def __init__(self, settings: Settings | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings or Settings.load()
        self.settings.ensure_dirs()
        self.pool = QThreadPool.globalInstance()
        self.manager = ModelManager(self.settings)
        self.profile: HardwareProfile | None = None
        self.decision: BackendDecision | None = None
        self.engine = None
        self.camera: CameraThread | None = None
        self.bridge: BridgeService | None = None
        self._pending_frames: set[int] = set()

    # ------------------------------------------------------------------ hardware
    def detect(self) -> None:
        def job():
            profile = detect_hardware()
            decision = choose_backend(profile, probe_providers(profile),
                                      preferred=self.settings.preferred_provider,
                                      allow_fallback=self.settings.allow_fallback)
            return profile, decision

        worker = Worker(job)
        worker.signals.finished.connect(self._on_profile)
        worker.signals.failed.connect(self.engine_error.emit)
        self.pool.start(worker)

    def _on_profile(self, result) -> None:
        self.profile, self.decision = result
        self.profile_ready.emit(self.profile)
        self.decision_ready.emit(self.decision)

    # ------------------------------------------------------------------ engine
    def load_engine(self, want_swap: bool = True, want_enhance: bool = True) -> None:
        if self.engine is not None:
            self.engine_ready.emit(self.engine)
            return

        def job():
            from saqr_engine.face.pipeline import FaceEngine

            engine = FaceEngine(self.settings, decision=self.decision, profile=self.profile,
                                manager=self.manager)
            engine.load_models(want_swap=want_swap, want_enhance=want_enhance)
            return engine

        worker = Worker(job)
        worker.signals.finished.connect(self._on_engine)
        worker.signals.failed.connect(self.engine_error.emit)
        self.pool.start(worker)

    def _on_engine(self, engine) -> None:
        self.engine = engine
        self.engine_ready.emit(engine)

    def submit(self, fn, *args, on_done=None, on_error=None, **kwargs) -> Worker:
        worker = Worker(fn, *args, **kwargs)
        if on_done:
            worker.signals.finished.connect(on_done)
        if on_error:
            worker.signals.failed.connect(on_error)
        self.pool.start(worker)
        return worker

    # ------------------------------------------------------------------ bridge
    def start_bridge(self) -> None:
        if self.bridge and self.bridge.isRunning():
            return
        self.bridge = BridgeService(self.settings)
        self.bridge.start()

    # ------------------------------------------------------------------ cleanup
    def shutdown(self) -> None:
        if self.camera:
            self.camera.stop()
        if self.bridge:
            self.bridge.stop()
        self.pool.waitForDone(3000)
