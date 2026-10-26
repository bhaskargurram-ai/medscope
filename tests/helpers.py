"""Synthetic test images: a grey 'body' on a black background with one bright lesion."""

import numpy as np


def synthetic_case(size: int = 256, lesion_center=(90, 100), lesion_radius: int = 14, seed: int = 0):
    """seed=0 gives the same body every time; other seeds vary body shape and texture
    so images from different 'patients' are not duplicates of each other."""
    h = w = size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.zeros((h, w, 3), dtype=np.uint8)
    ry, rx = (0.42, 0.42) if seed == 0 else rng.uniform(0.32, 0.46, 2)
    cy0, cx0 = (h / 2, w / 2) if seed == 0 else (h / 2 + rng.uniform(-15, 15), w / 2 + rng.uniform(-15, 15))
    body = ((yy - cy0) ** 2 / (ry * h) ** 2 + (xx - cx0) ** 2 / (rx * w) ** 2) <= 1
    base = 110 if seed == 0 else rng.uniform(80, 140)
    tissue = (base + rng.normal(0, 6, (h, w))).clip(0, 255)
    if seed:  # a darker 'organ' blob so anatomy differs between patients
        oy, ox = rng.uniform(0.35, 0.65, 2) * size
        organ = (yy - oy) ** 2 + (xx - ox) ** 2 <= (rng.uniform(0.08, 0.16) * size) ** 2
        tissue[organ] -= 35
    for c in range(3):
        image[..., c][body] = tissue.clip(0, 255).astype(np.uint8)[body]
    cy, cx = lesion_center
    lesion = (yy - cy) ** 2 + (xx - cx) ** 2 <= lesion_radius ** 2
    image[lesion] = 230
    return image, lesion
