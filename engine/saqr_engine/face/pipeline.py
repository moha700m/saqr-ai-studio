"""The face engine: detection -> tracking -> swap -> enhancement -> paste."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..config import Settings
from ..hardware.backends import BackendDecision
from ..hardware.detection import HardwareProfile
from ..hardware.session import SessionInfo, create_session
from ..models.manager import ModelManager, ModelError
from .align import align_face
from .detector import Face, FaceDetector, largest_face
from .enhancer import FaceEnhancer
from .mask import build_face_mask
from .swapper import FaceSwapper, SwapOptions, SwapperError
from .tracker import FaceTracker

log = logging.getLogger(__name__)


class EngineError(RuntimeError):
    pass


@dataclass
class SourceFace:
    name: str
    aligned: np.ndarray
    thumbnail: np.ndarray
    path: str | None = None

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path,
                "thumbnail_size": list(self.thumbnail.shape[:2])}


@dataclass
class ProcessedFrame:
    frame: np.ndarray
    faces: list[Face] = field(default_factory=list)
    swapped_faces: int = 0
    metrics: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "faces": [f.to_dict() for f in self.faces],
            "swapped_faces": self.swapped_faces,
            "metrics": self.metrics,
            "error": self.error,
        }


class FaceEngine:
    """Owns model sessions; safe to reuse across frames and threads (one lock)."""

    def __init__(self, settings: Settings | None = None, decision: BackendDecision | None = None,
                 profile: HardwareProfile | None = None, manager: ModelManager | None = None):
        import threading

        self.settings = settings or Settings.load()
        self.decision = decision
        self.profile = profile
        self.manager = manager or ModelManager(self.settings)
        self._lock = threading.RLock()
        self.detector: FaceDetector | None = None
        self.swapper: FaceSwapper | None = None
        self.enhancer: FaceEnhancer | None = None
        self.tracker = FaceTracker(smoothing=0.5)
        self.sessions: dict[str, SessionInfo] = {}
        self.load_errors: list[str] = []
        self.source: SourceFace | None = None
        self.face_sources: dict[int, SourceFace] = {}
        self._mask_cache: dict[tuple, np.ndarray] = {}

    # ------------------------------------------------------------------ models
    def _open(self, kind: str, label: str):
        model = self.manager.resolve(kind)
        if model is None:
            self.load_errors.append(f"{kind}: no model installed")
            return None
        session, info = create_session(model.path, decision=self.decision, profile=self.profile)
        self.sessions[label] = info
        return session

    def load_models(self, want_swap: bool = True, want_enhance: bool = True) -> "FaceEngine":
        if self.detector is None:
            try:
                session = self._open("detector", "detector")
                if session is None:
                    raise EngineError("YuNet detector is required; install it from the Models page")
                self.detector = FaceDetector(self.manager.require("detector").path)
            except (ModelError, FileNotFoundError) as exc:
                raise EngineError(str(exc)) from exc

        if want_swap and self.swapper is None:
            try:
                session = self._open("swapper", "swapper")
                if session is not None:
                    self.swapper = FaceSwapper(session, SwapOptions(
                        strength=self.settings.swap_strength,
                        keep_mouth=self.settings.mouth_mask,
                        output_order="rgb",
                    ))
                    if self.source is not None:
                        self.swapper.set_source(self.source.aligned)
            except (ModelError, SwapperError) as exc:
                self.load_errors.append(f"swapper: {exc}")
                log.warning("swapper unavailable: %s", exc)

        if want_enhance and self.enhancer is None:
            try:
                session = self._open("enhancer", "enhancer")
                if session is not None:
                    self.enhancer = FaceEnhancer(session)
            except Exception as exc:  # noqa: BLE001
                self.load_errors.append(f"enhancer: {exc}")
                log.warning("enhancer unavailable: %s", exc)
        return self

    @property
    def can_swap(self) -> bool:
        return self.swapper is not None

    def status(self) -> dict:
        return {
            "detector": self.sessions.get("detector").__dict__ if self.sessions.get("detector") else None,
            "swapper": self.sessions.get("swapper").__dict__ if self.sessions.get("swapper") else None,
            "enhancer": self.sessions.get("enhancer").__dict__ if self.sessions.get("enhancer") else None,
            "can_swap": self.can_swap,
            "load_errors": self.load_errors,
            "source": self.source.to_dict() if self.source else None,
            "provider": self.decision.provider if self.decision else None,
        }

    # ------------------------------------------------------------------ source
    def set_source(self, path: str | Path, name: str | None = None) -> SourceFace:
        if self.detector is None:
            self.load_models(want_swap=False, want_enhance=False)
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise EngineError(f"cannot read image: {path}")
        face = largest_face(self.detector.detect(image))
        if face is None:
            raise EngineError("no face found in the source image")
        aligned, _ = align_face(image, face.landmarks, 128)
        thumbnail = cv2.resize(aligned, (160, 160))
        self.source = SourceFace(name=name or Path(path).stem, aligned=aligned,
                                 thumbnail=thumbnail, path=str(path))
        if self.swapper is not None:
            self.swapper.set_source(aligned)
        return self.source

    def set_source_from_array(self, bgr: np.ndarray, name: str = "capture") -> SourceFace:
        if self.detector is None:
            self.load_models(want_swap=False, want_enhance=False)
        face = largest_face(self.detector.detect(bgr))
        if face is None:
            raise EngineError("no face found in the captured image")
        aligned, _ = align_face(bgr, face.landmarks, 128)
        self.source = SourceFace(name=name, aligned=aligned, thumbnail=cv2.resize(aligned, (160, 160)))
        if self.swapper is not None:
            self.swapper.set_source(aligned)
        return self.source

    def map_face(self, track_id: int, source: SourceFace | None) -> None:
        if source is None:
            self.face_sources.pop(track_id, None)
        else:
            self.face_sources[track_id] = source

    # ------------------------------------------------------------------ process
    def _mask(self, options: SwapOptions) -> np.ndarray:
        key = (options.keep_mouth, options.keep_eyes, options.include_forehead,
               round(options.strength, 3), options.feather)
        if key not in self._mask_cache:
            self._mask_cache[key] = build_face_mask(
                128, strength=options.strength, keep_mouth=options.keep_mouth,
                keep_eyes=options.keep_eyes, include_forehead=options.include_forehead,
                feather=options.feather,
            )
        return self._mask_cache[key]

    def process(self, frame: np.ndarray, swap: bool = True, options: SwapOptions | None = None,
                max_faces: int = 4) -> ProcessedFrame:
        if self.detector is None:
            raise EngineError("detector not loaded")
        options = options or SwapOptions(
            strength=self.settings.swap_strength, keep_mouth=self.settings.mouth_mask,
        )
        started = time.perf_counter()
        with self._lock:
            faces = self.tracker.update(self.detector.detect(frame))
            detect_ms = (time.perf_counter() - started) * 1000.0
            swapped = 0
            swap_ms = 0.0
            error = None
            if swap and self.swapper is not None and (self.source or self.face_sources):
                for face in faces[:max_faces]:
                    source = self.face_sources.get(face.track_id or -1, self.source)
                    if source is None:
                        continue
                    try:
                        t0 = time.perf_counter()
                        aligned, matrix = align_face(frame, face.landmarks, self.swapper.size)
                        self.swapper.set_source(source.aligned)
                        result = self.swapper.swap(aligned)
                        if self.enhancer is not None and (options.enhance or self.settings.face_enhance):
                            result = self.enhancer.enhance(result, self.settings.enhancement_blend)
                        alpha = self._mask(options)
                        from .align import paste_back
                        paste_back(frame, result, matrix, alpha * float(options.blend))
                        face.meta["swapped"] = True
                        swapped += 1
                        swap_ms += (time.perf_counter() - t0) * 1000.0
                    except (SwapperError, ValueError, cv2.error) as exc:
                        error = str(exc)
                        log.warning("swap failed: %s", exc)
                        break
            total_ms = (time.perf_counter() - started) * 1000.0
        metrics = {
            "detect_ms": round(detect_ms, 2),
            "swap_ms": round(swap_ms, 2),
            "total_ms": round(total_ms, 2),
            "fps": round(1000.0 / total_ms, 2) if total_ms > 0 else 0.0,
            "faces": len(faces),
        }
        return ProcessedFrame(frame=frame, faces=faces, swapped_faces=swapped,
                              metrics=metrics, error=error)

    def analyze(self, frame: np.ndarray) -> list[Face]:
        if self.detector is None:
            raise EngineError("detector not loaded")
        faces = self.detector.detect(frame)
        return self.tracker.update(faces)
