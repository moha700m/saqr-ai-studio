"""Model catalogue and license metadata.

Model weights are NOT bundled with this repository. Each entry states where it
comes from, its license, whether commercial use is allowed, and a SHA-256 when
one could be computed from the official artifact. We never invent a hash: an
entry without one cannot be auto-downloaded, only imported from disk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    kind: str                      # detector | swapper | enhancer
    filename: str
    license_id: str
    license_name: str
    commercial_use: bool
    requires_acceptance: bool
    source_url: str
    download_url: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    input_size: int | None = None
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def downloadable(self) -> bool:
        return bool(self.download_url and self.sha256)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["downloadable"] = self.downloadable
        return data


CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="yunet-2023mar",
        name="YuNet face detector (2023mar)",
        kind="detector",
        filename="face_detection_yunet_2023mar.onnx",
        license_id="MIT",
        license_name="MIT License (Shiqi Yu / OpenCV Zoo)",
        commercial_use=True,
        requires_acceptance=False,
        source_url="https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
        download_url=(
            "https://github.com/opencv/opencv_zoo/raw/main/models/"
            "face_detection_yunet/face_detection_yunet_2023mar.onnx"
        ),
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        size_bytes=232589,
        input_size=640,
        notes="5-point landmarks, dynamic input shape, CPU-fast. Used for detection and alignment.",
        tags=("detection", "landmarks", "permissive"),
    ),
    ModelSpec(
        id="gfpgan-1.4",
        name="GFPGAN v1.4 face enhancement",
        kind="enhancer",
        filename="GFPGANv1.4.onnx",
        license_id="Apache-2.0",
        license_name="Apache License 2.0 (Tencent ARC)",
        commercial_use=True,
        requires_acceptance=False,
        source_url="https://github.com/TencentARC/GFPGAN",
        download_url=None,
        sha256=None,
        input_size=512,
        notes=(
            "Weights are not redistributed by SAQR. Export or download an ONNX build yourself "
            "and import it; the manager checks the graph signature before installing."
        ),
        tags=("enhancement", "user-supplied"),
    ),
    ModelSpec(
        id="inswapper-128",
        name="InsightFace inswapper_128",
        kind="swapper",
        filename="inswapper_128.onnx",
        license_id="LicenseRef-InsightFace-NC",
        license_name="InsightFace model license — non-commercial research use only",
        commercial_use=False,
        requires_acceptance=True,
        source_url="https://github.com/deepinsight/insightface",
        download_url=None,
        sha256=None,
        input_size=128,
        notes=(
            "Not downloadable from SAQR and not redistributed. The user must obtain it and "
            "confirm they accept the non-commercial license. Commercial builds must ship a "
            "licensed swap model instead (the engine is model-agnostic)."
        ),
        tags=("swap", "non-commercial", "gated"),
    ),
)

CATALOG_BY_ID = {spec.id: spec for spec in CATALOG}
CATALOG_BY_FILENAME = {spec.filename.lower(): spec for spec in CATALOG}


def find_spec(identifier: str) -> ModelSpec | None:
    key = identifier.lower()
    return CATALOG_BY_ID.get(key) or CATALOG_BY_FILENAME.get(key) or CATALOG_BY_ID.get(identifier)


def specs_for_kind(kind: str) -> list[ModelSpec]:
    return [spec for spec in CATALOG if spec.kind == kind]
