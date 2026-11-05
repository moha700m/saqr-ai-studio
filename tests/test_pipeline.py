import numpy as np
import pytest

from tests.fixtures_onnx import latent_swapper

pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")

from saqr_engine.face.align import template  # noqa: E402
from saqr_engine.face.detector import Face  # noqa: E402
from saqr_engine.face.pipeline import EngineError, FaceEngine, SourceFace  # noqa: E402
from saqr_engine.face.swapper import FaceSwapper  # noqa: E402


class StubDetector:
    """Returns one deterministic face so the swap/paste path can be tested
    without a camera or a real portrait."""

    def __init__(self, offset=(200, 100)):
        self.offset = np.array(offset, dtype=np.float32)

    def detect(self, frame):
        landmarks = template(128) + self.offset
        bbox = np.array([self.offset[0] - 40, self.offset[1] - 40, 160, 200], dtype=np.float32)
        return [Face(bbox=bbox, landmarks=landmarks, score=0.99)]


@pytest.fixture()
def engine(settings, tmp_path):
    engine = FaceEngine(settings)
    engine.detector = StubDetector()
    session = ort.InferenceSession(latent_swapper(tmp_path / "swap.onnx"), providers=["CPUExecutionProvider"])
    engine.swapper = FaceSwapper(session)
    source = np.full((128, 128, 3), 210, dtype=np.uint8)
    engine.source = SourceFace(name="unit", aligned=source, thumbnail=source.copy())
    engine.swapper.set_source(source)
    return engine


def test_frame_swap_changes_pixels_and_reports_metrics(engine):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    result = engine.process(frame, swap=True)
    assert result.swapped_faces == 1
    assert result.error is None
    assert set(result.metrics) == {"detect_ms", "swap_ms", "total_ms", "fps", "faces"}
    assert result.metrics["total_ms"] > 0
    assert result.faces[0].track_id == 1
    changed = int((np.abs(result.frame.astype(int) - 90).sum(axis=2) > 0).sum())
    assert changed > 1000


def test_preview_mode_does_not_swap(engine):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    before = frame.copy()
    result = engine.process(frame, swap=False)
    assert result.swapped_faces == 0
    assert np.array_equal(before, result.frame)


def test_tracker_keeps_id_across_frames(engine):
    frame = np.full((480, 640, 3), 90, dtype=np.uint8)
    ids = [engine.process(frame, swap=False).faces[0].track_id for _ in range(5)]
    assert len(set(ids)) == 1


def test_source_without_face_is_rejected(engine):
    class EmptyDetector:
        def detect(self, frame):
            return []

    engine.detector = EmptyDetector()
    with pytest.raises(EngineError):
        engine.set_source_from_array(np.zeros((64, 64, 3), dtype=np.uint8))
