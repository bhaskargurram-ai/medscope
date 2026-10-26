"""Inpainting operators for counterfactual views.

`telea` (OpenCV) runs anywhere but leaves smooth, textureless patches. `lama`
(learned inpainting, needs a GPU and `pip install simple-lama-inpainting`) fills
regions with realistic tissue texture, which makes edits much harder to spot and
so removes a shortcut the model could otherwise learn. Use LaMa for real builds.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image

from .counterfactual import InpaintFn, telea_inpaint


@lru_cache(maxsize=1)
def _lama_model():
    try:
        from simple_lama_inpainting import SimpleLama
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise ImportError("LaMa needs `pip install simple-lama-inpainting` (run on Colab)") from exc
    return SimpleLama()


def lama_inpaint(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    model = _lama_model()
    result = model(Image.fromarray(image), Image.fromarray(mask.astype(np.uint8) * 255))
    out = np.asarray(result.convert("RGB"))
    if out.shape != image.shape:  # LaMa pads to a multiple of 8
        out = out[: image.shape[0], : image.shape[1]]
    # keep every pixel outside the mask exactly as it was
    return np.where(mask[..., None], out, image).astype(np.uint8)


def get_inpainter(name: str) -> InpaintFn:
    if name == "telea":
        return telea_inpaint
    if name == "lama":
        return lama_inpaint
    raise ValueError(f"unknown inpainter {name!r}; choose 'telea' or 'lama'")
