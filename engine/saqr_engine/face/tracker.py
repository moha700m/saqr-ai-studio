"""Lightweight IoU tracker with temporal smoothing.

Stable track ids make multi-face source mapping possible and the smoothing cuts
the sub-pixel landmark jitter that otherwise shows up as a shimmering jawline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .detector import Face


def iou(a: np.ndarray, b: np.ndarray) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


@dataclass
class Track:
    track_id: int
    bbox: np.ndarray
    landmarks: np.ndarray
    score: float
    missed: int = 0
    hits: int = 1
    history: dict = field(default_factory=dict)


class FaceTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 12, smoothing: float = 0.55):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.smoothing = float(np.clip(smoothing, 0.0, 0.95))
        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    @property
    def tracks(self) -> list[Track]:
        return [t for t in self._tracks.values() if t.missed == 0]

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(self, faces: list[Face]) -> list[Face]:
        unmatched = list(range(len(faces)))
        used: set[int] = set()

        pairs: list[tuple[float, int, int]] = []
        for tid, track in self._tracks.items():
            for index in unmatched:
                pairs.append((iou(track.bbox, faces[index].bbox), tid, index))
        pairs.sort(reverse=True)
        for score, tid, index in pairs:
            if score < self.iou_threshold or index in used:
                continue
            track = self._tracks[tid]
            face = faces[index]
            w = self.smoothing
            track.bbox = track.bbox * w + face.bbox * (1 - w)
            track.landmarks = track.landmarks * w + face.landmarks * (1 - w)
            track.score = face.score
            track.missed = 0
            track.hits += 1
            face.track_id = tid
            face.bbox = track.bbox.astype(np.float32)
            face.landmarks = track.landmarks.astype(np.float32)
            used.add(index)

        for index in range(len(faces)):
            if index in used:
                continue
            face = faces[index]
            tid = self._next_id
            self._next_id += 1
            self._tracks[tid] = Track(tid, face.bbox.copy(), face.landmarks.copy(), face.score)
            face.track_id = tid

        for tid, track in list(self._tracks.items()):
            if tid not in {f.track_id for f in faces}:
                track.missed += 1
                if track.missed > self.max_missed:
                    self._tracks.pop(tid, None)
        return faces
