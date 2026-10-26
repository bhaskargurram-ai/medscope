"""Synthetic test images: a grey 'body' on a black background with one bright lesion."""

import numpy as np


def synthetic_case(size: int = 256, lesion_center=(90, 100), lesion_radius: int = 14):
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.zeros((h, w, 3), dtype=np.uint8)
    body = ((yy - h / 2) ** 2 / (0.42 * h) ** 2 + (xx - w / 2) ** 2 / (0.42 * w) ** 2) <= 1
    rng = np.random.default_rng(0)
    tissue = (110 + rng.normal(0, 6, (h, w))).clip(0, 255).astype(np.uint8)
    for c in range(3):
        image[..., c][body] = tissue[body]
    cy, cx = lesion_center
    lesion = (yy - cy) ** 2 + (xx - cx) ** 2 <= lesion_radius ** 2
    image[lesion] = 230
    return image, lesion
