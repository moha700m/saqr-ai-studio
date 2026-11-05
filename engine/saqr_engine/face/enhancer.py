"""Optional ONNX face enhancer (GFPGAN/GPEN class models).

Enhancement runs on the aligned 512 px crop after the swap and is blended by a
user-controlled factor. The graph's input size and normalization are read from
the model, so a compatible user-supplied export works without code changes.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
import onnxruntime as ort

log = logging.getLogger(__name__)


class EnhancerError(RuntimeError):
    pass


class FaceEnhancer:
    def __init__(self, session: ort.InferenceSession):
        self.session = session
        inputs = session.get_inputs()
        if not inputs:
            raise EnhancerError("enhancer has no inputs")
        self.input_name = inputs[0].name
        shape = [d if isinstance(d, int) and d > 0 else 0 for d in inputs[0].shape]
        if len(shape) != 4:
            raise EnhancerError(f"expected a 4-D image input, got {shape}")
        self.size = int(shape[2] or 512)
        self.output_name = session.get_outputs()[0].name
        log.info("enhancer ready size=%d", self.size)

    def enhance(self, aligned_face: np.ndarray, blend: float = 0.6) -> np.ndarray:
        rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.size, self.size), interpolation=cv2.INTER_LANCZOS4)
        blob = resized.astype(np.float32) / 127.5 - 1.0
        blob = np.expand_dims(blob.transpose(2, 0, 1), 0)
        raw = self.session.run([self.output_name], {self.input_name: blob})[0][0]
        raw = np.clip((raw.transpose(1, 2, 0) + 1.0) * 127.5, 0, 255).astype(np.uint8)
        enhanced = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
        enhanced = cv2.resize(enhanced, (aligned_face.shape[1], aligned_face.shape[0]),
                              interpolation=cv2.INTER_AREA)
        alpha = float(np.clip(blend, 0.0, 1.0))
        return cv2.addWeighted(enhanced, alpha, aligned_face, 1.0 - alpha, 0.0)
