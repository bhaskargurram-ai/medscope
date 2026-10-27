"""Inpainting operators for counterfactual views.

`telea` (OpenCV) runs anywhere but leaves smooth, textureless patches. `lama`
(learned inpainting, best on a GPU) fills regions with realistic tissue texture,
which makes edits much harder to spot and so removes a shortcut the model could
otherwise learn. Use LaMa for real builds.

LaMa is run directly from the public TorchScript export of Big-LaMa (the same file
the simple-lama-inpainting package uses), so the only dependency is torch. Set
MEDSCOPE_LAMA_PATH to a local copy (e.g. on Google Drive) to skip the download.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from .counterfactual import InpaintFn, telea_inpaint

LAMA_URL = "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
PAD_MODULO = 8


def lama_inputs(image: np.ndarray, mask: np.ndarray, modulo: int = PAD_MODULO) -> tuple[np.ndarray, np.ndarray]:
    """Image (1,3,H',W') float32 in [0,1] and mask (1,1,H',W') float32 in {0,1}.

    H' and W' are rounded up to a multiple of `modulo` by symmetric padding at the
    bottom and right, as Big-LaMa expects.
    """
    img = image.astype(np.float32) / 255.0
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    m = (mask > 0).astype(np.float32)
    h, w = m.shape
    ph, pw = (-h) % modulo, (-w) % modulo
    img = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="symmetric")
    m = np.pad(m, ((0, ph), (0, pw)), mode="symmetric")
    return img.transpose(2, 0, 1)[None], m[None, None]


def lama_output(result: np.ndarray, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Model output (3,H',W') in [0,1] -> uint8 HxWx3, cropped, original pixels kept outside the mask."""
    h, w = mask.shape
    out = np.clip(result.transpose(1, 2, 0)[:h, :w] * 255, 0, 255).astype(np.uint8)
    rgb = image if image.ndim == 3 else np.stack([image] * 3, axis=-1)
    return np.where(mask[..., None] > 0, out, rgb).astype(np.uint8)


@lru_cache(maxsize=1)
def _lama_model():
    import torch

    path = os.environ.get("MEDSCOPE_LAMA_PATH")
    if path:
        if not Path(path).exists():
            raise FileNotFoundError(f"MEDSCOPE_LAMA_PATH points to a missing file: {path}")
    else:
        path = str(Path.home() / ".cache" / "medscope" / "big-lama.pt")
        if not Path(path).exists():
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            print(f"downloading Big-LaMa to {path} ...")
            torch.hub.download_url_to_file(LAMA_URL, path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = torch.jit.load(path, map_location=device).eval()
    return model, device


def lama_inpaint(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    import torch

    model, device = _lama_model()
    img, m = lama_inputs(image, mask)
    with torch.inference_mode():
        result = model(torch.from_numpy(img).to(device), torch.from_numpy(m).to(device))
    return lama_output(result[0].float().cpu().numpy(), image, mask)


def get_inpainter(name: str) -> InpaintFn:
    if name == "telea":
        return telea_inpaint
    if name == "lama":
        return lama_inpaint
    raise ValueError(f"unknown inpainter {name!r}; choose 'telea' or 'lama'")
