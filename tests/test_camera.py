import time

import numpy as np

from saqr_engine.camera.stream import CameraStream
from saqr_engine.camera.virtualcam import detect_virtual_camera


class FakeCapture:
    """A camera that produces a numbered frame on every read."""

    def __init__(self):
        self.counter = 0
        self._open = True

    def isOpened(self):
        return self._open

    def set(self, *_args):
        return True

    def read(self):
        time.sleep(0.005)
        self.counter += 1
        frame = np.full((48, 64, 3), self.counter % 255, dtype=np.uint8)
        return True, frame

    def release(self):
        self._open = False


def test_stream_captures_and_stops():
    stream = CameraStream(index=0, capture_factory=lambda _i: FakeCapture(), max_queue=2)
    stream.start()
    time.sleep(0.15)
    item = stream.read(timeout=1.0)
    assert item is not None
    _, frame = item
    assert frame.shape == (48, 64, 3)
    stats = stream.stats()
    assert stats["frames_captured"] > 0
    assert stats["running"] is True
    stream.stop()
    assert stream.running is False


def test_slow_consumer_drops_old_frames():
    stream = CameraStream(index=0, capture_factory=lambda _i: FakeCapture(), max_queue=1)
    stream.start()
    time.sleep(0.25)
    stats = stream.stats()
    assert stats["frames_dropped"] > 0
    assert stats["queued"] <= 1
    stream.stop()


def test_camera_open_failure_is_reported():
    class Broken(FakeCapture):
        def isOpened(self):
            return False

    stream = CameraStream(index=4, capture_factory=lambda _i: Broken())
    stream.start()
    time.sleep(0.1)
    assert "could not be opened" in (stream.last_error or "")
    assert stream.running is False


def test_virtual_camera_detection_uses_device_names():
    class Device:
        def __init__(self, name):
            self.name = name

    status = detect_virtual_camera([Device("Integrated Camera"), Device("OBS Virtual Camera")])
    assert status.available is True
    assert status.device_name == "OBS Virtual Camera"
    missing = detect_virtual_camera([Device("Integrated Camera")])
    assert missing.available is False
