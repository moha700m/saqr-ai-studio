"""5-point face alignment (Umeyama similarity transform).

The target geometry is the ArcFace 112x112 template scaled to the model input
size. Implementing Umeyama directly keeps the dependency surface at numpy +
OpenCV and reproduces the alignment used by InsightFace's ``norm_crop``.
"""

from __future__ import annotations

import cv2
import numpy as np

ARCFACE_112 = np.array(
    [[38.2946, 51.6963],
     [73.5318, 51.5014],
     [56.0252, 71.7366],
     [41.5493, 92.3655],
     [70.7299, 92.2041]],
    dtype=np.float32,
)


def template(size: int = 128) -> np.ndarray:
    return ARCFACE_112 * (size / 112.0)


def umeyama(src: np.ndarray, dst: np.ndarray, estimate_scale: bool = True):
    """Least-squares similarity transform mapping ``src`` onto ``dst``.

    Returns a 2x3 affine matrix (same convention as cv2.warpAffine).
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    if src.shape != dst.shape or src.shape[1] != 2:
        raise ValueError(f"expected matching Nx2 point sets, got {src.shape} and {dst.shape}")
    num, dim = src.shape
    src_mean = src.mean(axis=0)
    dst_mean = dst.mean(axis=0)
    src_demean = src - src_mean
    dst_demean = dst - dst_mean

    cov = dst_demean.T @ src_demean / num
    u, s, vt = np.linalg.svd(cov)
    rank = np.linalg.matrix_rank(cov)
    d = np.ones(dim)
    if rank == dim - 1:
        if np.linalg.det(u) * np.linalg.det(vt) > 0:
            d[-1] = 1.0
        else:
            d[-1] = -1.0
    rotation = u @ np.diag(d) @ vt

    if estimate_scale:
        src_var = (src_demean ** 2).sum() / num
        scale = float((s @ d) / src_var) if src_var > 0 else 1.0
    else:
        scale = 1.0
    translation = dst_mean - scale * (rotation @ src_mean)
    matrix = np.zeros((2, 3), dtype=np.float64)
    matrix[:, :2] = scale * rotation
    matrix[:, 2] = translation
    return matrix


def align_face(frame: np.ndarray, landmarks: np.ndarray, size: int = 128) -> tuple[np.ndarray, np.ndarray]:
    """Warp a detected face into the model's canonical square crop.

    Returns ``(crop, matrix)`` where ``matrix`` maps frame coordinates to the
    aligned crop. Use :func:`invert` to paste results back.
    """
    matrix = umeyama(landmarks, template(size)).astype(np.float32)
    crop = cv2.warpAffine(frame, matrix, (size, size), borderMode=cv2.BORDER_REPLICATE)
    return crop, matrix


def invert(matrix: np.ndarray) -> np.ndarray:
    return cv2.invertAffineTransform(matrix)


def paste_back(frame: np.ndarray, patch: np.ndarray, matrix: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Warp ``patch`` and its alpha mask back onto ``frame`` in place."""
    height, width = frame.shape[:2]
    inverse = invert(matrix)
    warped = cv2.warpAffine(patch, inverse, (width, height), borderMode=cv2.BORDER_REPLICATE)
    mask = cv2.warpAffine(alpha, inverse, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if mask.ndim == 2:
        mask = mask[..., None]
    blended = frame.astype(np.float32) * (1.0 - mask) + warped.astype(np.float32) * mask
    frame[:] = np.clip(blended, 0, 255).astype(np.uint8)
    return frame
