"""Pure OpenCV image operations, extracted from datasheet_viewer (D2).

All functions take/return numpy arrays (BGR uint8) with no Qt/GUI or PDF
dependency, so they can be unit-tested headlessly and reused. CV tuning
constants live here (D1) instead of being scattered as magic numbers.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

# ── Tuning constants (centralized; D1) ──────────────────────────────────────
CLAHE_CLIP_LIMIT = 2.5
CLAHE_TILE_GRID = (8, 8)
BINARIZE_BLOCK_DIVISOR = 30  # adaptive blockSize ~ width/divisor (odd), D2/C2
BINARIZE_C = 10
DENOISE_H = 7
UNSHARP_RADIUS = 3.0
UNSHARP_AMOUNT = 1.5
DESKEW_MIN_LINES = 5
DESKEW_MAX_ANGLE_STD = 1.5
DESKEW_MAX_ANGLE = 15.0


def _odd(value: int, minimum: int = 3) -> int:
    value = max(value, minimum)
    return value if value % 2 == 1 else value + 1


def samples_to_bgr(samples: bytes, height: int, width: int, channels: int) -> np.ndarray:
    """Convert raw PyMuPDF pixmap samples to a BGR image (channel-safe, A4).

    Handles grayscale (1), RGB (3) and RGBA (4); raises on anything else
    instead of blindly reshaping to 3 channels (which crashed before).
    """
    arr = np.frombuffer(samples, dtype=np.uint8).reshape(height, width, channels)
    if channels == 1:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if channels == 3:
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    if channels == 4:
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    raise ValueError(f"unsupported channel count: {channels}")


def adaptive_block_size(width: int) -> int:
    """DPI/resolution-aware odd block size for adaptive threshold (C2)."""
    return _odd(width // BINARIZE_BLOCK_DIVISOR, minimum=11)


def unsharp(
    img_bgr: np.ndarray, radius: float = UNSHARP_RADIUS, amount: float = UNSHARP_AMOUNT
) -> np.ndarray:
    """Unsharp-mask sharpening (C1) — gentler/halo-controlled vs a raw Laplacian."""
    blur = cv2.GaussianBlur(img_bgr, (0, 0), radius)
    return cv2.addWeighted(img_bgr, 1.0 + amount, blur, -amount, 0)


def deskew_image(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=180)
    if lines is None:
        return img_bgr
    angles = []
    for line in lines[:40]:
        _rho, theta = line[0]
        angle = math.degrees(theta) - 90
        if -DESKEW_MAX_ANGLE <= angle <= DESKEW_MAX_ANGLE:
            angles.append(angle)
    if len(angles) < DESKEW_MIN_LINES:
        return img_bgr
    if float(np.std(angles)) > DESKEW_MAX_ANGLE_STD:
        return img_bgr
    angle = float(np.median(angles))
    if abs(angle) < 0.2:
        return img_bgr
    h, w = img_bgr.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(
        img_bgr, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def apply_filter(img_bgr: np.ndarray, mode: str) -> np.ndarray:
    if mode == "original":
        return img_bgr

    if mode == "auto":
        return apply_filter(apply_filter(img_bgr, "contrast"), "sharpen")

    if mode == "deskew":
        return deskew_image(img_bgr)

    if mode == "contrast":
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
        l_ch = clahe.apply(l_ch)
        return cv2.cvtColor(cv2.merge([l_ch, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

    if mode == "binarize":
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=adaptive_block_size(img_bgr.shape[1]),
            C=BINARIZE_C,
        )
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    if mode == "denoise":
        return cv2.fastNlMeansDenoisingColored(
            img_bgr,
            None,
            h=DENOISE_H,
            hColor=DENOISE_H,
            templateWindowSize=7,
            searchWindowSize=21,
        )

    if mode == "sharpen":
        return unsharp(img_bgr)

    return img_bgr
