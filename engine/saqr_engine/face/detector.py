"""YuNet face detection with landmarks.

Wraps OpenCV's ``FaceDetectorYN``; the model file is resolved by the model
manager. Detection runs on a downscaled copy when the frame is large, then
boxes and landmarks are mapped back to full resolution.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class Face:
    bbox: np.ndarray           # x, y, w, h in frame pixels
    landmarks: np.ndarray      # 5x2 in frame pixels
    score: float
    track_id: int | None = None
    meta: dict = field(default_factory=dict)

    @property
    def center(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return x + w / 2.0, y + h / 2.0

    def to_dict(self) -> dict:
        x, y, w, h = [float(v) for v in self.bbox]
        return {
            "bbox": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)],
            "landmarks": [[round(float(px), 1), round(float(py), 1)] for px, py in self.landmarks],
            "score": round(float(self.score), 4),
            "track_id": self.track_id,
        }


class FaceDetector:
    def __init__(self, model_path: str | Path, input_size: int = 640,
                 score_threshold: float = 0.6, nms_threshold: float = 0.3, top_k: int = 50):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(path)
        self._raw = cv2.FaceDetectorYN.create(
            str(path), "", (input_size, input_size), score_threshold, nms_threshold, top_k
        )
        self.input_size = input_size
        self.score_threshold = score_threshold
        self._lock = threading.Lock()

    def _working_scale(self, frame: np.ndarray) -> float:
        longest = max(frame.shape[:2])
        return min(1.0, self.input_size / float(longest))

    def detect(self, frame: np.ndarray) -> list[Face]:
        if frame is None or frame.size == 0:
            return []
        scale = self._working_scale(frame)
        if scale < 1.0:
            work = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            work = frame
        height, width = work.shape[:2]
        with self._lock:
            self._raw.setInputSize((width, height))
            _, raw = self._raw.detect(work)
        if raw is None:
            return []
        inverse = 1.0 / scale
        faces: list[Face] = []
        for row in raw:
            score = float(row[-1])
            if score < self.score_threshold:
                continue
            bbox = row[:4].astype(np.float32) * inverse
            landmarks = row[4:14].reshape(5, 2).astype(np.float32) * inverse
            faces.append(Face(bbox=bbox, landmarks=landmarks, score=score))
        faces.sort(key=lambda f: float(f.bbox[2] * f.bbox[3]), reverse=True)
        return faces

    def detect_one(self, frame: np.ndarray) -> Face | None:
        faces = self.detect(frame)
        return faces[0] if faces else None


def largest_face(faces: list[Face]) -> Face | None:
    if not faces:
        return None
    return max(faces, key=lambda f: float(f.bbox[2] * f.bbox[3]))
