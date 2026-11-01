"""Inpainting operators for counterfactual views.

`telea` (OpenCV) runs anywhere but leaves smooth, textureless patches. `lama`
(learned inpainting, best on a GPU) fills regions with realistic tissue texture,
which makes edits much harder to spot and so removes a shortcut the model could
otherwise learn. Use LaMa for real builds: every training and test view was made with it.

Two further operators exist only to test the trained model on erasures made by a tool it never
saw (held-out inpainters): `transplant` copies a same-shaped patch of tissue from elsewhere in the
same image into the hole and blends it with Poisson image editing (real texture, no generator);
`diffusion` fills the hole with a Stable Diffusion inpainting model (a generative model unrelated
to LaMa).

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


def _is_gray(rgb: np.ndarray) -> bool:
    return rgb.ndim == 2 or (np.array_equal(rgb[..., 0], rgb[..., 1]) and np.array_equal(rgb[..., 1], rgb[..., 2]))


def _match_gray(out: np.ndarray, source: np.ndarray) -> np.ndarray:
    """Keep a grayscale image grayscale (a filled region must not add colour)."""
    if _is_gray(source):
        g = np.round(out.astype(np.float32).mean(axis=-1)).astype(np.uint8)
        return np.stack([g] * 3, axis=-1)
    return out


def feather_paste(base: np.ndarray, fill: np.ndarray, mask: np.ndarray, grow: int = 2) -> np.ndarray:
    """`fill` inside the mask, `base` outside, with a soft edge `grow` pixels wide outside the mask.
    Pixels farther than `grow` from the mask are exactly `base`."""
    import cv2
    from .counterfactual import dilate
    m = mask.astype(bool)
    outer = dilate(m, grow)
    alpha = cv2.GaussianBlur(outer.astype(np.float32), (0, 0), sigmaX=max(grow / 2, 0.5))
    alpha = np.where(m, 1.0, np.where(outer, alpha, 0.0))[..., None]
    out = alpha * fill.astype(np.float32) + (1 - alpha) * base.astype(np.float32)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def transplant_inpaint(image: np.ndarray, mask: np.ndarray, avoid: np.ndarray | None = None, seed: int = 0,
                       keep_away: int = 10, min_foreground: float = 0.9, max_tries: int = 1000) -> np.ndarray:
    """Fill the hole with a same-shaped patch of tissue copied from elsewhere in the same image,
    blended into its surroundings by Poisson image editing (OpenCV seamlessClone).

    The donor patch avoids the hole and `avoid` (the lesion) plus a `keep_away` border, and lies
    mostly on tissue. Raises ValueError if no donor position exists.
    """
    import cv2
    from .counterfactual import _as_rgb, dilate, foreground_mask
    rgb = _as_rgb(image).copy()
    m = mask.astype(bool)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        raise ValueError("mask is empty")
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    patch = m[y0:y1, x0:x1]
    ph, pw = patch.shape
    h, w = m.shape
    if ph >= h or pw >= w:
        raise ValueError("hole too large for a donor patch")
    forbidden = dilate(m, keep_away)
    if avoid is not None:
        forbidden |= dilate(avoid.astype(bool), keep_away)
    tissue = foreground_mask(rgb)
    rng = np.random.default_rng(seed)
    for _ in range(max_tries):
        ty, tx = int(rng.integers(0, h - ph + 1)), int(rng.integers(0, w - pw + 1))
        if (forbidden[ty:ty + ph, tx:tx + pw] & patch).any():
            continue
        if (tissue[ty:ty + ph, tx:tx + pw] & patch).sum() < min_foreground * patch.sum():
            continue
        break
    else:
        raise ValueError("no donor position for a transplant patch")
    shifted = rgb.copy()
    shifted[y0:y1, x0:x1] = rgb[ty:ty + ph, tx:tx + pw]
    clone_mask = dilate(m, 2)
    bx, by, bw, bh = cv2.boundingRect(clone_mask.astype(np.uint8))
    try:
        if bx < 1 or by < 1 or bx + bw > w - 1 or by + bh > h - 1:
            raise cv2.error("mask touches the border")
        out = cv2.seamlessClone(shifted, rgb, clone_mask.astype(np.uint8) * 255, (bx + bw // 2, by + bh // 2),
                                cv2.NORMAL_CLONE)
        out = np.where(clone_mask[..., None], out, rgb)
    except cv2.error:
        out = feather_paste(rgb, shifted, m)        # near the border: plain copy with a soft edge
    return _match_gray(out, rgb)


DIFFUSION_MODELS = ("stable-diffusion-v1-5/stable-diffusion-inpainting", "stabilityai/stable-diffusion-2-inpainting")


@lru_cache(maxsize=1)
def _diffusion_pipe():
    import torch
    from diffusers import StableDiffusionInpaintPipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    errors = []
    for repo in DIFFUSION_MODELS:
        try:
            pipe = StableDiffusionInpaintPipeline.from_pretrained(
                repo, torch_dtype=torch.float16 if device == "cuda" else torch.float32, safety_checker=None)
        except Exception as exc:  # noqa: BLE001 - try the next checkpoint
            errors.append(f"{repo}: {exc}")
            continue
        pipe.set_progress_bar_config(disable=True)
        return pipe.to(device), repo, device
    raise RuntimeError("no Stable Diffusion inpainting checkpoint could be loaded:\n" + "\n".join(errors))


def diffusion_crop(mask: np.ndarray, context: float = 3.0, min_side: int = 256) -> tuple[int, int, int, int]:
    """Square window (y0, y1, x0, x1) around the hole with room for context, kept inside the image."""
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    side = int(max(min_side, context * max(ys.max() - ys.min() + 1, xs.max() - xs.min() + 1)))
    side = min(side, h, w)
    cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
    y0 = int(np.clip(cy - side // 2, 0, h - side))
    x0 = int(np.clip(cx - side // 2, 0, w - side))
    return y0, y0 + side, x0, x0 + side


def diffusion_inpaint(image: np.ndarray, mask: np.ndarray, seed: int = 0, steps: int = 30, size: int = 512) -> np.ndarray:
    """Fill the hole with Stable Diffusion inpainting (empty prompt), on a square window around it.
    Only the hole (with a 2-pixel soft edge) changes."""
    import torch
    from PIL import Image as _Image
    from .counterfactual import _as_rgb, dilate
    pipe, _, device = _diffusion_pipe()
    rgb = _as_rgb(image)
    m = mask.astype(bool)
    y0, y1, x0, x1 = diffusion_crop(m)
    crop, mcrop = rgb[y0:y1, x0:x1], dilate(m, 2)[y0:y1, x0:x1]
    img_in = _Image.fromarray(crop).resize((size, size), _Image.BICUBIC)
    mask_in = _Image.fromarray(mcrop.astype(np.uint8) * 255).resize((size, size), _Image.NEAREST)
    gen = torch.Generator(device=device).manual_seed(int(seed))
    res = pipe(prompt="", image=img_in, mask_image=mask_in, num_inference_steps=steps, guidance_scale=1.0,
               height=size, width=size, generator=gen).images[0]
    fill = np.asarray(res.convert("RGB").resize((x1 - x0, y1 - y0), _Image.BICUBIC))
    full = rgb.copy()
    full[y0:y1, x0:x1] = fill
    return _match_gray(feather_paste(rgb, full, m), rgb)


INPAINTERS = ("telea", "lama", "transplant", "diffusion")


def get_inpainter(name: str) -> InpaintFn:
    if name == "telea":
        return telea_inpaint
    if name == "lama":
        return lama_inpaint
    if name == "transplant":
        return transplant_inpaint
    if name == "diffusion":
        return diffusion_inpaint
    raise ValueError(f"unknown inpainter {name!r}; choose from {INPAINTERS}")
