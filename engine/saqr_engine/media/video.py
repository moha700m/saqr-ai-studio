"""Video processing with an FFmpeg raw-video pipe (OpenCV writer fallback).

Frames are streamed, never buffered to disk, so a 10-minute 1080p clip uses a
few megabytes of RAM. Audio is muxed back from the source when FFmpeg is
available; if it is not, the video is still exported without audio.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class VideoResult:
    ok: bool
    output: str
    frames: int
    fps: float
    width: int
    height: int
    elapsed_s: float
    cancelled: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class FFmpegWriter:
    """Write BGR frames to an H.264 MP4 through a subprocess pipe."""

    def __init__(self, path: str | Path, width: int, height: int, fps: float,
                 crf: int = 20, preset: str = "veryfast"):
        self.path = str(path)
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps) or 30.0
        self.proc: subprocess.Popen | None = None
        if shutil.which("ffmpeg"):
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "bgr24",
                "-s", f"{self.width}x{self.height}", "-r", f"{self.fps:.3f}",
                "-i", "-", "-an",
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", self.path,
            ]
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._cv = cv2.VideoWriter(self.path, fourcc, self.fps, (self.width, self.height))
            if not self._cv.isOpened():
                raise RuntimeError("no FFmpeg binary and OpenCV cannot open an MP4 writer")

    def write(self, frame: np.ndarray) -> None:
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        if self.proc is not None:
            assert self.proc.stdin is not None
            self.proc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
        else:
            self._cv.write(frame)

    def close(self) -> str | None:
        if self.proc is not None:
            if self.proc.stdin:
                self.proc.stdin.close()
            stderr = self.proc.stderr.read() if self.proc.stderr else b""
            code = self.proc.wait(timeout=60)
            if code != 0:
                return stderr.decode(errors="ignore")[-500:] or f"ffmpeg exited {code}"
            return None
        self._cv.release()
        return None


def probe_video(path: str | Path) -> dict:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"ok": False, "error": "cannot open video"}
    info = {
        "ok": True,
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": round(float(capture.get(cv2.CAP_PROP_FPS)) or 0.0, 3),
        "frames": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    capture.release()
    info["duration_s"] = round(info["frames"] / info["fps"], 2) if info["fps"] else None
    return info


def _has_audio(path: Path) -> bool:
    if not shutil.which("ffprobe"):
        return False
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=index", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        return bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _mux_audio(video: Path, source: Path) -> None:
    if not _has_audio(source) or not shutil.which("ffmpeg"):
        return
    merged = video.with_name(video.stem + ".mux.mp4")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
           "-i", str(source), "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-shortest", str(merged)]
    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        merged.replace(video)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("audio mux failed: %s", exc)
        merged.unlink(missing_ok=True)


def process_video(
    input_path: str | Path,
    output_path: str | Path,
    engine,
    swap: bool = True,
    max_frames: int | None = None,
    cancel: threading.Event | None = None,
    progress: Callable[[int, int], None] | None = None,
    audio: bool = True,
    crf: int = 20,
) -> VideoResult:
    source = Path(input_path)
    target = Path(output_path)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        return VideoResult(False, str(target), 0, 0, 0, 0, 0.0, error="cannot open video")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 30.0
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if max_frames:
        total = min(total, max_frames) if total else max_frames
    target.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp sibling so a cancelled job never leaves a half-playable file
    # at the destination path.
    handle, tmp_name = tempfile.mkstemp(suffix=".mp4", dir=str(target.parent))
    os.close(handle)  # Windows refuses to replace/delete a file with an open descriptor
    tmp_out = Path(tmp_name)
    writer: FFmpegWriter | None = None
    frames = 0
    started = time.perf_counter()
    cancelled = False
    error: str | None = None
    try:
        writer = FFmpegWriter(tmp_out, width, height, fps, crf=crf)
        while True:
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            ok, frame = capture.read()
            if not ok:
                break
            result = engine.process(frame, swap=swap)
            writer.write(result.frame)
            frames += 1
            if progress:
                progress(frames, total)
            if max_frames and frames >= max_frames:
                break
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    finally:
        capture.release()
        if writer is not None:
            close_error = writer.close()
            error = error or close_error
        if cancelled or error:
            tmp_out.unlink(missing_ok=True)
        else:
            tmp_out.replace(target)
            if audio:
                _mux_audio(target, source)

    elapsed = time.perf_counter() - started
    return VideoResult(
        ok=not cancelled and error is None, output=str(target), frames=frames, fps=round(fps, 2),
        width=width, height=height, elapsed_s=round(elapsed, 2), cancelled=cancelled, error=error,
    )
