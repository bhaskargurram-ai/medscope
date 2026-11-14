"""Simple fill tools for the tool-family training views (docs/FRAMEWORK_STAGE1.md).

Each fills a mask from the pixels around it, without a learned model, and each leaves a different kind of trace:

  blur     normalised convolution: a smooth patch blending the surrounding pixels
  mean     the mean of a band around the mask plus noise with the band's spread: a flat, grainy patch
  shuffle  pixels drawn at random from the band around the mask, lightly smoothed: surrounding texture, scrambled

TELEA (OpenCV) and the diffusion inpainter are **not** in this family: they stay held out for testing. Grayscale
images stay grayscale.
"""

from __future__ import annotations

import cv2
import numpy as np

from .counterfactual import _as_rgb, dilate


def _band(mask: np.ndarray, width: int = 8) -> np.ndarray:
    return dilate(mask, width) & ~mask.astype(bool)


def _gray(rgb: np.ndarray) -> bool:
    return bool(np.array_equal(rgb[..., 0], rgb[..., 1]) and np.array_equal(rgb[..., 1], rgb[..., 2]))


def _finish(rgb: np.ndarray, fill: np.ndarray, mask: np.ndarray) -> np.ndarray:
    fill = np.clip(fill, 0, 255).astype(np.uint8)
    if _gray(rgb):
        g = np.round(fill.astype(np.float32).mean(axis=-1)).astype(np.uint8)
        fill = np.stack([g] * 3, axis=-1)
    return np.where(mask[..., None], fill, rgb).astype(np.uint8)


def blur_fill(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    rgb = _as_rgb(image)
    m = mask.astype(bool)
    if not m.any():
        return rgb.copy()
    ys, xs = np.nonzero(m)
    size = max(ys.max() - ys.min(), xs.max() - xs.min()) + 1
    sigma = max(3.0, size / 3.0)
    keep = (~m).astype(np.float32)
    num = cv2.GaussianBlur(rgb.astype(np.float32) * keep[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(keep, (0, 0), sigma)[..., None]
    fill = num / np.maximum(den, 1e-3)
    return _finish(rgb, fill, m)


def mean_fill(image: np.ndarray, mask: np.ndarray, seed: int = 0) -> np.ndarray:
    rgb = _as_rgb(image)
    m = mask.astype(bool)
    if not m.any():
        return rgb.copy()
    band = _band(m)
    px = rgb[band].astype(np.float32) if band.any() else rgb[~m].astype(np.float32)
    mu, sd = px.mean(axis=0), px.std(axis=0)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, size=rgb.shape[:2])[..., None] * sd       # one noise field for all channels
    return _finish(rgb, mu + noise, m)


def shuffle_fill(image: np.ndarray, mask: np.ndarray, seed: int = 0) -> np.ndarray:
    rgb = _as_rgb(image)
    m = mask.astype(bool)
    if not m.any():
        return rgb.copy()
    band = _band(m)
    px = rgb[band] if band.any() else rgb[~m]
    rng = np.random.default_rng(seed)
    fill = rgb.copy()
    fill[m] = px[rng.integers(0, len(px), int(m.sum()))]
    fill = cv2.GaussianBlur(fill, (0, 0), 1.0)
    return _finish(rgb, fill.astype(np.float32), m)


FILLS = {"blur": blur_fill, "mean": mean_fill, "shuffle": shuffle_fill}
