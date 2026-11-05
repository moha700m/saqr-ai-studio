import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SAQR_HOME", str(tmp_path / "home"))
    from saqr_engine.config import Settings

    return Settings.load()


@pytest.fixture(scope="session")
def yunet_path(tmp_path_factory):
    """A real YuNet file: env override, local cache, or the official URL."""
    env = os.environ.get("SAQR_TEST_YUNET")
    if env and Path(env).exists():
        return Path(env)
    cached = Path("/tmp/yunet.onnx")
    if cached.exists():
        return cached
    target = tmp_path_factory.mktemp("models") / "yunet.onnx"
    try:
        import urllib.request

        urllib.request.urlretrieve(  # noqa: S310 - official OpenCV Zoo URL
            "https://github.com/opencv/opencv_zoo/raw/main/models/"
            "face_detection_yunet/face_detection_yunet_2023mar.onnx", target
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"YuNet not available offline: {exc}")
    return target
