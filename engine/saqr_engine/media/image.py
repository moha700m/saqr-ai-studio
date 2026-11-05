"""Still-image processing with format-preserving export."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import cv2

Processor = Callable[..., object]


@dataclass
class ImageResult:
    ok: bool
    output: str
    width: int
    height: int
    elapsed_ms: float
    faces: int
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def process_image(
    input_path: str | Path,
    output_path: str | Path,
    engine,
    swap: bool = True,
    jpeg_quality: int = 92,
) -> ImageResult:
    source = Path(input_path)
    target = Path(output_path)
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        return ImageResult(False, str(target), 0, 0, 0.0, 0, f"cannot read {source}")
    started = time.perf_counter()
    try:
        result = engine.process(image, swap=swap)
    except Exception as exc:  # noqa: BLE001
        return ImageResult(False, str(target), image.shape[1], image.shape[0], 0.0, 0, str(exc))
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    params = [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)] if suffix in {".jpg", ".jpeg"} else []
    if suffix == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
    if not cv2.imwrite(str(target), image, params):
        return ImageResult(False, str(target), image.shape[1], image.shape[0],
                           (time.perf_counter() - started) * 1000, len(result.faces), "write failed")
    return ImageResult(
        ok=True, output=str(target), width=image.shape[1], height=image.shape[0],
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        faces=len(result.faces), error=getattr(result, "error", None),
    )
