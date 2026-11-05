import numpy as np
import pytest

from tests.fixtures_onnx import dual_image_swapper, latent_swapper, not_a_swapper

pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")

from saqr_engine.face.swapper import (  # noqa: E402
    FaceSwapper, GraphInfo, SwapOptions, SwapperError, inspect_graph,
)


def _session(path):
    return ort.InferenceSession(path, providers=["CPUExecutionProvider"])


def test_inspect_latent_graph(tmp_path):
    graph = inspect_graph(_session(latent_swapper(tmp_path / "swap.onnx")))
    assert isinstance(graph, GraphInfo)
    assert graph.mode == "latent"
    assert graph.image_size == 128
    assert graph.latent_input == "source"
    assert graph.emap_output == "emap"


def test_latent_swap_runs_and_caches_source(tmp_path):
    swapper = FaceSwapper(_session(latent_swapper(tmp_path / "swap.onnx")))
    source = np.random.default_rng(0).integers(0, 255, (128, 128, 3), dtype=np.uint8)
    target = np.random.default_rng(1).integers(0, 255, (128, 128, 3), dtype=np.uint8)
    swapper.set_source(source)
    latent_first = swapper._latent.copy()
    swapper.set_source(source)
    assert np.array_equal(latent_first, swapper._latent)  # cache hit
    out = swapper.swap(target)
    assert out.shape == (128, 128, 3)
    assert out.dtype == np.uint8
    # decode maps normalized 0 -> 127.5, so a 0.5x graph lands halfway to grey.
    assert out.mean() == pytest.approx(target.mean() * 0.5 + 63.75, abs=2.5)


def test_dual_image_graph(tmp_path):
    swapper = FaceSwapper(_session(dual_image_swapper(tmp_path / "dual.onnx")))
    assert swapper.graph.mode == "dual-image"
    source = np.full((128, 128, 3), 100, dtype=np.uint8)
    target = np.full((128, 128, 3), 40, dtype=np.uint8)
    swapper.set_source(source)
    out = swapper.swap(target)
    assert out.shape == (128, 128, 3)


def test_swap_without_source_raises(tmp_path):
    swapper = FaceSwapper(_session(latent_swapper(tmp_path / "swap.onnx")))
    with pytest.raises(SwapperError):
        swapper.swap(np.zeros((128, 128, 3), dtype=np.uint8))


def test_bogus_graph_is_rejected(tmp_path):
    with pytest.raises(SwapperError):
        FaceSwapper(_session(not_a_swapper(tmp_path / "bogus.onnx")))


def test_invalid_output_order_falls_back_to_bgr(tmp_path):
    swapper = FaceSwapper(_session(latent_swapper(tmp_path / "swap.onnx")),
                          SwapOptions(output_order="bgr"))
    swapper.set_source(np.full((128, 128, 3), 200, dtype=np.uint8))
    out = swapper.swap(np.full((128, 128, 3), 100, dtype=np.uint8))
    assert out.shape == (128, 128, 3)
