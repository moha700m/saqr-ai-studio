import threading

import cv2
import numpy as np

from saqr_engine.media.image import process_image
from saqr_engine.media.video import FFmpegWriter, process_video, probe_video


class PassthroughEngine:
    def process(self, frame, swap=True):
        class Result:
            pass

        result = Result()
        result.frame = frame
        result.faces = []
        return result


def _write_clip(path, frames=20, size=(160, 120)):
    writer = FFmpegWriter(path, size[0], size[1], 20)
    for i in range(frames):
        frame = np.full((size[1], size[0], 3), 30 + i, dtype=np.uint8)
        cv2.circle(frame, (20 + i * 3, 60), 8, (0, 200, 255), -1)
        writer.write(frame)
    return writer.close()


def test_ffmpeg_writer_roundtrip(tmp_path):
    path = tmp_path / "clip.mp4"
    assert _write_clip(path) is None
    info = probe_video(path)
    assert info["ok"] is True
    assert info["width"] == 160 and info["height"] == 120
    assert info["fps"] == 20.0
    assert info["frames"] == 20


def test_video_processing_preserves_length(tmp_path):
    source = tmp_path / "in.mp4"
    _write_clip(source)
    result = process_video(source, tmp_path / "out.mp4", PassthroughEngine(), audio=False)
    assert result.ok is True, result.error
    assert result.frames == 20
    info = probe_video(result.output)
    assert info["frames"] == 20


def test_cancel_leaves_no_partial_output(tmp_path):
    source = tmp_path / "in.mp4"
    _write_clip(source)
    cancel = threading.Event()
    cancel.set()
    target = tmp_path / "cancelled.mp4"
    result = process_video(source, target, PassthroughEngine(), cancel=cancel)
    assert result.cancelled is True
    assert result.ok is False
    assert not target.exists()


def test_image_processing_writes_output(tmp_path):
    source = tmp_path / "in.png"
    cv2.imwrite(str(source), np.full((64, 64, 3), 120, dtype=np.uint8))
    result = process_image(source, tmp_path / "out.png", PassthroughEngine())
    assert result.ok is True
    assert (tmp_path / "out.png").exists()
    assert result.width == 64 and result.height == 64
