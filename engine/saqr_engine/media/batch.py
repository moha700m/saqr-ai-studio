"""Sequential batch processing with a single cancellation flag."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .image import process_image
from .video import process_video

log = logging.getLogger(__name__)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


@dataclass
class BatchReport:
    total: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: bool = False
    outputs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total, "completed": self.completed, "failed": self.failed,
            "cancelled": self.cancelled, "outputs": self.outputs, "errors": self.errors,
        }


def collect_media(folder: str | Path) -> list[Path]:
    root = Path(folder)
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXT | VIDEO_EXT)


def process_batch(folder: str | Path, output_dir: str | Path, engine,
                  cancel: threading.Event | None = None,
                  progress=None) -> BatchReport:
    files = collect_media(folder)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    report = BatchReport(total=len(files))
    for index, path in enumerate(files):
        if cancel is not None and cancel.is_set():
            report.cancelled = True
            break
        target = out_root / path.relative_to(Path(folder))
        target = target.with_suffix(".mp4") if path.suffix.lower() in VIDEO_EXT else target
        if path.suffix.lower() in IMAGE_EXT:
            result = process_image(path, target, engine)
            ok, error = result.ok, result.error
        else:
            result = process_video(path, target, engine)
            ok, error = result.ok, result.error
        if ok:
            report.completed += 1
            report.outputs.append(str(target))
        else:
            report.failed += 1
            report.errors.append(f"{path.name}: {error}")
        if progress:
            progress(index + 1, report.total, path.name)
    return report
