"""Soft face masks in aligned space.

The mask decides how much of the swapped face is pasted back. Everything is
built at the model's 128 px resolution and feathered, so the seam is invisible
after the inverse warp even when the head moves quickly.
"""

from __future__ import annotations

import cv2
import numpy as np


def build_face_mask(
    size: int = 128,
    strength: float = 1.0,
    keep_mouth: bool = True,
    keep_eyes: bool = False,
    include_forehead: bool = True,
    feather: int = 21,
) -> np.ndarray:
    """Return a float32 HxW alpha mask in [0, 1]."""
    mask = np.zeros((size, size), dtype=np.float32)
    center = (size // 2, int(size * 0.52))
    axes = (int(size * 0.42), int(size * 0.50 if include_forehead else size * 0.44))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)

    # Preserve the wearer's mouth so speech keeps working (classic "mouth mask").
    if keep_mouth:
        mouth_center = (size // 2, int(size * 0.76))
        mouth_axes = (int(size * 0.19), int(size * 0.10))
        cv2.ellipse(mask, mouth_center, mouth_axes, 0, 0, 360, 0.0, -1)

    if keep_eyes:
        for cx in (int(size * 0.33), int(size * 0.67)):
            cv2.ellipse(mask, (cx, int(size * 0.42)), (int(size * 0.10), int(size * 0.06)),
                        0, 0, 360, 0.0, -1)

    kernel = max(3, feather | 1)
    mask = cv2.GaussianBlur(mask, (kernel, kernel), kernel / 5.0)
    mask = np.clip(mask * float(strength), 0.0, 1.0)
    return mask


def build_mouth_only_mask(size: int = 128, feather: int = 15) -> np.ndarray:
    mask = np.zeros((size, size), dtype=np.float32)
    cv2.ellipse(mask, (size // 2, int(size * 0.76)), (int(size * 0.19), int(size * 0.10)),
                0, 0, 360, 1.0, -1)
    kernel = max(3, feather | 1)
    return cv2.GaussianBlur(mask, (kernel, kernel), kernel / 5.0)
