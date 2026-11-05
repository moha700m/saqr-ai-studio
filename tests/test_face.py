import numpy as np

from saqr_engine.face.align import align_face, invert, paste_back, template, umeyama
from saqr_engine.face.mask import build_face_mask, build_mouth_only_mask


def test_umeyama_recovers_identity():
    points = template(128)
    matrix = umeyama(points, points)
    assert np.allclose(matrix, [[1, 0, 0], [0, 1, 0]], atol=1e-6)


def test_umeyama_recovers_known_similarity():
    src = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [5, 5]], dtype=np.float32)
    theta = np.deg2rad(30)
    scale = 2.0
    rotation = scale * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    dst = src @ rotation.T + np.array([5.0, -3.0])
    matrix = umeyama(src, dst)
    assert np.allclose(matrix[:, :2], rotation, atol=1e-5)
    assert np.allclose(matrix[:, 2], [5.0, -3.0], atol=1e-5)


def test_align_face_returns_square_crop():
    frame = np.random.default_rng(3).integers(0, 255, (480, 640, 3), dtype=np.uint8)
    landmarks = template(128) + np.array([240, 160], dtype=np.float32)
    crop, matrix = align_face(frame, landmarks, 128)
    assert crop.shape == (128, 128, 3)
    assert matrix.shape == (2, 3)
    back = invert(matrix)
    assert back.shape == (2, 3)


def test_mask_keeps_mouth_and_is_soft():
    mask = build_face_mask(128, keep_mouth=True)
    assert mask.shape == (128, 128)
    assert float(mask[97, 64]) < 0.05          # mouth preserved
    assert float(mask[40, 64]) > 0.7           # forehead swapped
    assert mask.min() >= 0.0 and mask.max() <= 1.0

    no_mouth = build_face_mask(128, keep_mouth=False)
    assert float(no_mouth[97, 64]) > 0.5

    mouth = build_mouth_only_mask(128)
    assert float(mouth[97, 64]) > 0.5
    assert float(mouth[40, 64]) < 0.05


def test_strength_scales_mask():
    full = build_face_mask(128, strength=1.0)
    half = build_face_mask(128, strength=0.5)
    assert np.allclose(half, full * 0.5, atol=1e-6)


def test_paste_back_only_touches_face_region():
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    patch = np.full((128, 128, 3), 255, dtype=np.uint8)
    landmarks = template(128) + np.array([36, 30], dtype=np.float32)
    _, matrix = align_face(frame, landmarks, 128)
    alpha = build_face_mask(128, feather=3)
    paste_back(frame, patch, matrix, alpha)
    assert frame[100, 100].mean() > 20
    assert frame[1, 1].mean() == 0
