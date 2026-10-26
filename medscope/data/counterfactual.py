"""Counterfactual view generation.

Target removal and random removal use the *same* inpainting operator on regions of
the *same* shape, so the only systematic difference between them is whether the
lesion was removed. That control is what lets the benchmark tell evidence-sensitive
abstention apart from a model that simply reacts to edited pixels.

The default operator is OpenCV Telea inpainting, which runs anywhere. A learned
inpainter (e.g. LaMa) can be swapped in through the `inpaint_fn` argument.
"""

from __future__ import annotations

from typing import Callable, Optional

import cv2
import numpy as np

InpaintFn = Callable[[np.ndarray, np.ndarray], np.ndarray]


def _as_rgb(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return np.stack([image] * 3, axis=-1)
    if image.shape[-1] == 4:
        return image[..., :3]
    return image


def dilate(mask: np.ndarray, pixels: int) -> np.ndarray:
    if pixels <= 0:
        return mask.astype(bool)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * pixels + 1, 2 * pixels + 1))
    return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)


def telea_inpaint(image: np.ndarray, mask: np.ndarray, radius: int = 7) -> np.ndarray:
    """Fill `mask` from surrounding pixels with OpenCV's Telea method."""
    rgb = _as_rgb(image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, mask.astype(np.uint8) * 255, radius, cv2.INPAINT_TELEA)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def make_target_removal(
    image: np.ndarray,
    lesion_mask: np.ndarray,
    margin: int = 5,
    inpaint_fn: InpaintFn = telea_inpaint,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove the lesion. Returns (edited image, the mask that was edited)."""
    if not lesion_mask.any():
        raise ValueError("lesion mask is empty")
    edit_mask = dilate(lesion_mask, margin)
    return inpaint_fn(image, edit_mask), edit_mask


def foreground_mask(image: np.ndarray, threshold: int = 15) -> np.ndarray:
    """Rough body/tissue region: pixels brighter than a near-black background."""
    gray = cv2.cvtColor(_as_rgb(image), cv2.COLOR_RGB2GRAY)
    return gray > threshold


def make_random_removal(
    image: np.ndarray,
    lesion_mask: np.ndarray,
    rng: np.random.Generator,
    margin: int = 5,
    keep_away: int = 10,
    min_foreground: float = 0.9,
    max_tries: int = 500,
    inpaint_fn: InpaintFn = telea_inpaint,
) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Apply the same edit, with the same shape, somewhere that avoids the lesion.

    The lesion's dilated mask is translated to a random position that (a) does not
    touch the lesion plus a `keep_away` border and (b) lies mostly on tissue rather
    than background. Returns None if no such position exists, so the caller can drop
    the case instead of producing an invalid control.
    """
    edit_shape = dilate(lesion_mask, margin)
    ys, xs = np.nonzero(edit_shape)
    if len(xs) == 0:
        raise ValueError("lesion mask is empty")
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    patch = edit_shape[y0:y1, x0:x1]
    ph, pw = patch.shape
    h, w = lesion_mask.shape
    if ph >= h or pw >= w:
        return None

    forbidden = dilate(lesion_mask, margin + keep_away)
    tissue = foreground_mask(image)
    patch_area = patch.sum()

    for _ in range(max_tries):
        ty = int(rng.integers(0, h - ph + 1))
        tx = int(rng.integers(0, w - pw + 1))
        if (forbidden[ty:ty + ph, tx:tx + pw] & patch).any():
            continue
        if (tissue[ty:ty + ph, tx:tx + pw] & patch).sum() < min_foreground * patch_area:
            continue
        edit_mask = np.zeros_like(lesion_mask, dtype=bool)
        edit_mask[ty:ty + ph, tx:tx + pw] = patch
        return inpaint_fn(image, edit_mask), edit_mask
    return None


DEGRADATIONS = ("blur", "noise", "lowres", "mismatch")


def make_degraded(
    image: np.ndarray,
    kind: str,
    rng: np.random.Generator,
    other_image: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Make an input the model should not answer from without asking for more.

    - blur: strong Gaussian blur, fine detail gone
    - noise: heavy Gaussian noise
    - lowres: downsample 8x, then back up
    - mismatch: swap in an image from a different case/body part (needs other_image)
    """
    rgb = _as_rgb(image)
    h, w = rgb.shape[:2]
    if kind == "blur":
        sigma = max(h, w) / 40
        return cv2.GaussianBlur(rgb, (0, 0), sigmaX=sigma)
    if kind == "noise":
        noisy = rgb.astype(np.float32) + rng.normal(0, 60, rgb.shape)
        return np.clip(noisy, 0, 255).astype(np.uint8)
    if kind == "lowres":
        small = cv2.resize(rgb, (max(1, w // 8), max(1, h // 8)), interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    if kind == "mismatch":
        if other_image is None:
            raise ValueError("mismatch degradation needs other_image")
        return cv2.resize(_as_rgb(other_image), (w, h), interpolation=cv2.INTER_AREA)
    raise ValueError(f"unknown degradation {kind!r}; choose from {DEGRADATIONS}")
