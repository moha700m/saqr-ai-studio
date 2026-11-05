from pathlib import Path

import pytest

from saqr_engine.models.manifest import CATALOG
from saqr_engine.models.manager import ModelError, ModelManager, sha256_file


def test_catalog_licenses_are_explicit():
    assert CATALOG
    for spec in CATALOG:
        assert spec.license_id
        assert spec.source_url.startswith("https://")
        if spec.kind == "swapper":
            assert spec.requires_acceptance is True
            assert spec.downloadable is False


def test_gated_model_cannot_be_downloaded(settings, tmp_path):
    manager = ModelManager(settings)
    with pytest.raises(ModelError):
        manager.download("inswapper-128")


def test_import_requires_license_acceptance(settings, tmp_path):
    from tests.fixtures_onnx import dual_image_swapper

    model = dual_image_swapper(tmp_path / "inswapper_128.onnx")
    manager = ModelManager(settings)
    with pytest.raises(ModelError, match="license"):
        manager.install_file(model, kind="swapper", accept_license=False)
    record = manager.install_file(model, kind="swapper", accept_license=True)
    assert record.commercial_use is False
    assert manager.resolve("swapper").filename == "inswapper_128.onnx"


def test_import_rejects_non_swapper_graph(settings, tmp_path):
    from tests.fixtures_onnx import not_a_swapper

    model = not_a_swapper(tmp_path / "inswapper_128.onnx")
    manager = ModelManager(settings)
    with pytest.raises(ModelError, match="inswapper"):
        manager.install_file(model, kind="swapper", accept_license=True)


def test_checksum_verification_and_tamper_detection(settings, tmp_path):
    from tests.fixtures_onnx import dual_image_swapper

    model = dual_image_swapper(tmp_path / "inswapper_128.onnx")
    manager = ModelManager(settings)
    record = manager.install_file(model, kind="swapper", accept_license=True)
    assert manager.verify(record.id)["ok"] is True
    with open(record.path, "ab") as handle:
        handle.write(b"\x00")
    assert manager.verify(record.id)["ok"] is False


def test_remove_deletes_file(settings, tmp_path):
    from tests.fixtures_onnx import dual_image_swapper

    manager = ModelManager(settings)
    record = manager.install_file(dual_image_swapper(tmp_path / "inswapper_128.onnx"),
                                  kind="swapper", accept_license=True)
    assert manager.remove(record.id) is True
    assert not Path(record.path).exists()
    assert manager.resolve("swapper") is None


def test_real_yunet_download_is_checksum_verified(settings, yunet_path):
    manager = ModelManager(settings)
    record = manager.install_file(yunet_path, model_id="yunet-2023mar")
    assert record.sha256 == "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
    assert sha256_file(yunet_path) == record.sha256
    assert manager.verify("yunet-2023mar")["ok"]
