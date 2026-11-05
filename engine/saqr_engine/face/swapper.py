"""ONNX face swapper.

Supports the two families of swap graphs found in the wild:

* **inswapper-style**: a 128 px image input (``target``), an optional 512-d
  ``source`` latent input, and an ``emap`` output computed from the source
  image. The latent is produced once per source face.
* **dual-image-style**: two 128/256 px image inputs (source + target).

Graph roles are resolved by inspecting tensor names *and* shapes, because
different exports of the same weights rename their nodes.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

import cv2
import numpy as np
import onnxruntime as ort

log = logging.getLogger(__name__)


class SwapperError(RuntimeError):
    pass


@dataclass
class SwapOptions:
    strength: float = 1.0
    keep_mouth: bool = True
    keep_eyes: bool = False
    include_forehead: bool = True
    feather: int = 21
    output_order: str = "rgb"   # inswapper emits RGB; set to "bgr" for BGR exports
    blend: float = 1.0


@dataclass
class GraphInfo:
    image_inputs: list[str] = field(default_factory=list)
    latent_input: str | None = None
    image_size: int = 128
    emap_output: str | None = None
    image_output: str | None = None
    mode: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "image_inputs": self.image_inputs,
            "latent_input": self.latent_input,
            "image_size": self.image_size,
            "emap_output": self.emap_output,
            "image_output": self.image_output,
            "mode": self.mode,
        }


def _shape(value_info) -> list:
    return [dim if isinstance(dim, int) and dim > 0 else 0 for dim in value_info.shape]


def inspect_graph(session: ort.InferenceSession) -> GraphInfo:
    info = GraphInfo()
    for value in session.get_inputs():
        shape = _shape(value)
        if len(shape) == 4:
            info.image_inputs.append(value.name)
            if shape[2]:
                info.image_size = int(shape[2])
        elif len(shape) == 2 and (shape[1] in (0, 512, 1024)):
            info.latent_input = value.name
    outputs = session.get_outputs()
    for value in outputs:
        shape = _shape(value)
        if len(shape) == 4 and info.image_output is None:
            info.image_output = value.name
        elif len(shape) == 2 and info.emap_output is None:
            info.emap_output = value.name
    if info.emap_output is None and len(outputs) > 1:
        # Some exports expose the latent as a 4-D 1x512x1x1 tensor.
        for value in outputs:
            shape = _shape(value)
            if len(shape) == 4 and shape[1] in (512, 1024):
                info.emap_output = value.name
    if info.latent_input and info.emap_output:
        info.mode = "latent"
    elif len(info.image_inputs) >= 2:
        info.mode = "dual-image"
    elif len(info.image_inputs) == 1:
        info.mode = "single-image"
    if info.image_output is None:
        raise SwapperError("swap model has no 4-D image output")
    return info


class FaceSwapper:
    def __init__(self, session: ort.InferenceSession, options: SwapOptions | None = None):
        self.session = session
        self.options = options or SwapOptions()
        self.graph = inspect_graph(session)
        if self.graph.mode == "unknown":
            raise SwapperError(f"unsupported swap graph: {self.graph.to_dict()}")
        self.size = self.graph.image_size
        self._latent: np.ndarray | None = None
        self._source_key: str | None = None
        log.info("swapper mode=%s size=%d inputs=%s", self.graph.mode, self.size, self.graph.image_inputs)

    # ------------------------------------------------------------------ source
    @staticmethod
    def _key(aligned: np.ndarray) -> str:
        return hashlib.sha1(aligned.tobytes()).hexdigest()  # noqa: S324 - cache key only

    def set_source(self, aligned_source: np.ndarray) -> None:
        key = self._key(aligned_source)
        if key == self._source_key and self._latent is not None:
            return
        self._source_key = key
        if self.graph.mode == "latent":
            source_input = "source" if "source" in self.graph.image_inputs else self.graph.image_inputs[-1]
            feed = self._blank_feed()
            feed[source_input] = self._blob(aligned_source)
            try:
                self._latent = self.session.run([self.graph.emap_output], feed)[0]
            except Exception as exc:  # noqa: BLE001
                raise SwapperError(f"could not compute source latent: {exc}") from exc
        elif self.graph.mode == "dual-image":
            self._latent = aligned_source

    # ------------------------------------------------------------------ infer
    def _blank_feed(self) -> dict[str, np.ndarray]:
        """Every graph input, correctly shaped. ORT requires a feed for all of
        them even when the requested output does not depend on one."""
        feed: dict[str, np.ndarray] = {}
        for value in self.session.get_inputs():
            shape = [1 if not isinstance(dim, int) or dim <= 0 else dim for dim in value.shape]
            feed[value.name] = np.zeros(shape, dtype=np.float32)
        return feed

    def _blob(self, image: np.ndarray) -> np.ndarray:
        resized = image if image.shape[0] == self.size else cv2.resize(image, (self.size, self.size))
        blob = (resized.astype(np.float32) - 127.5) / 127.5
        return np.expand_dims(blob.transpose(2, 0, 1), 0).astype(np.float32)

    def _decode(self, raw: np.ndarray) -> np.ndarray:
        image = raw[0]
        if image.ndim == 3:
            image = image.transpose(1, 2, 0)
        low, high = float(image.min()), float(image.max())
        if low >= -1.05 and high <= 1.05:
            image = (image + 1.0) * 127.5
        elif low >= 0.0 and high <= 1.05:
            image = image * 255.0
        image = np.clip(image, 0, 255).astype(np.uint8)
        if self.options.output_order.lower() == "rgb":
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image

    def swap(self, aligned_target: np.ndarray) -> np.ndarray:
        if self.graph.mode == "latent":
            if self._latent is None:
                raise SwapperError("source face not set")
            target_input = "target" if "target" in self.graph.image_inputs else self.graph.image_inputs[0]
            feeds = self._blank_feed()
            feeds[target_input] = self._blob(aligned_target)
            feeds[self.graph.latent_input] = self._latent
        elif self.graph.mode == "dual-image":
            if self._latent is None:
                raise SwapperError("source face not set")
            names = self.graph.image_inputs
            source_name = "source" if "source" in names else names[0]
            target_name = "target" if "target" in names else names[-1]
            feeds = {source_name: self._blob(self._latent), target_name: self._blob(aligned_target)}
        else:
            feeds = {self.graph.image_inputs[0]: self._blob(aligned_target)}
        raw = self.session.run([self.graph.image_output], feeds)[0]
        return self._decode(raw)
