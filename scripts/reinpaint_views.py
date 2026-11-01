"""Remake the edited test views with an inpainting tool the model never saw in training.

Every training and test view was made with LaMa. This script takes the existing test views and
redoes only the two edited views of each case, lesion erased (target_removal) and the same-shape
edit elsewhere (random_removal), with another inpainter, on exactly the same edit masks: same
cases, same questions, same edit regions, only the tool differs. View ids are kept, so results
pair case by case with the LaMa runs.

    python scripts/reinpaint_views.py --views TEST_VIEWS... --inpainter transplant --out DIR
    -> DIR/views.jsonl (target_removal and random_removal views), DIR/dropped.jsonl, DIR/<case>/*.png

Inpainters: telea (OpenCV, classical), transplant (tissue copied from elsewhere in the same image,
Poisson-blended), diffusion (Stable Diffusion inpainting; needs a GPU and `pip install diffusers`).
A case is dropped (both views) if either edit cannot be made, or if it fails the same automatic check the
LaMa views passed (the lesion no longer stands out from its surroundings; the control leaves the lesion
untouched), so an incomplete erasure is never scored as a hallucination. Reruns skip finished images.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.counterfactual import dilate, telea_inpaint  # noqa: E402
from medscope.data.inpaint import diffusion_inpaint, transplant_inpaint  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.quality import check_case  # noqa: E402
from medscope.data.schema import View, ViewKind, box_to_pixels  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

EDITED = (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL)
MARGIN = 5          # the edit mask is the lesion mask dilated by this many pixels (as in build_views)


def _load_mask(path: str, shape: tuple[int, int]) -> np.ndarray:
    m = np.asarray(Image.open(path).convert("L"))
    if m.shape != shape:
        m = np.asarray(Image.fromarray(m).resize((shape[1], shape[0]), Image.NEAREST))
    return m > 127


def edit_mask(view: View, lesion: np.ndarray) -> np.ndarray:
    """The exact region the LaMa view edited: the stored edit mask, or (older builds) the dilated lesion
    mask, moved to the stored edit box for a random-removal view."""
    meta = view.meta or {}
    if meta.get("edit_mask") and Path(meta["edit_mask"]).exists():
        return _load_mask(meta["edit_mask"], lesion.shape)
    shape = dilate(lesion, MARGIN)
    if view.kind is ViewKind.TARGET_REMOVAL:
        return shape
    ys, xs = np.nonzero(shape)
    patch = shape[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = lesion.shape
    x1, y1, _, _ = box_to_pixels(meta["edit_box"], w, h)
    y1, x1 = min(y1, h - patch.shape[0]), min(x1, w - patch.shape[1])
    out = np.zeros_like(lesion)
    out[y1:y1 + patch.shape[0], x1:x1 + patch.shape[1]] = patch
    return out


def inpaint(name: str, image: np.ndarray, hole: np.ndarray, lesion: np.ndarray, seed: int) -> np.ndarray:
    if name == "telea":
        return telea_inpaint(image, hole)
    if name == "transplant":
        return transplant_inpaint(image, hole, avoid=lesion, seed=seed)
    if name == "diffusion":
        return diffusion_inpaint(image, hole, seed=seed)
    raise ValueError(f"unknown held-out inpainter {name!r}")


def remake(view: View, name: str, out: Path) -> View:
    meta = view.meta or {}
    original = load_image(meta["original_image"])
    lesion = _load_mask(meta["lesion_mask"], original.shape[:2])
    hole = edit_mask(view, lesion)
    path = out / view.case_id / f"{view.kind.value}.png"
    if not path.exists():
        img = inpaint(name, original, hole, lesion, seed=stable_index(view.view_id + name, 2 ** 31))
        keep = ~dilate(hole, 4)
        if not np.array_equal(img[keep], (original if original.ndim == 3 else np.stack([original] * 3, -1))[keep]):
            raise ValueError("the edit changed pixels outside the edit region")
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img).save(path)
    return replace(view, image_path=str(path), meta={**meta, "inpainter": name})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True, help="LaMa test views files")
    ap.add_argument("--inpainter", required=True, choices=["telea", "transplant", "diffusion"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    by_case: dict[str, dict] = {}
    for v in (v for f in args.views for v in load_views(f)):
        if v.kind in EDITED:
            by_case.setdefault(v.case_id, {})[v.kind] = v
    kept, dropped = [], []
    for i, (case, d) in enumerate(sorted(by_case.items())):
        if len(d) < 2:
            dropped.append({"case_id": case, "reason": "lesion-erased or control view missing"})
            continue
        try:
            pair = [remake(d[k], args.inpainter, out) for k in EDITED]
            meta = d[ViewKind.TARGET_REMOVAL].meta
            original = load_image(meta["original_image"])
            lesion = _load_mask(meta["lesion_mask"], original.shape[:2])
            qc = check_case(case, original, load_image(pair[0].image_path), load_image(pair[1].image_path),
                            lesion, edit_mask(d[ViewKind.RANDOM_REMOVAL], lesion))
            if not qc.passed:
                reason = "lesion still stands out after erasure" if not qc.lesion_removed else "control touched the lesion"
                dropped.append({"case_id": case, "reason": reason, "contrast_before": round(qc.contrast_before, 3),
                                "contrast_after": round(qc.contrast_after, 3)})
                continue
            kept += pair
        except (ValueError, KeyError, OSError) as exc:
            dropped.append({"case_id": case, "reason": str(exc)})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(by_case)} cases", flush=True)
    (out / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in kept))
    (out / "dropped.jsonl").write_text("".join(json.dumps(r) + "\n" for r in dropped))
    from collections import Counter
    why = Counter(r["reason"] if r["reason"] in ("lesion still stands out after erasure", "control touched the lesion")
                  else "edit could not be made" for r in dropped)
    print(f"{args.inpainter}: {len(kept) // 2} of {len(by_case)} cases kept ({len(kept)} views); dropped: {dict(why)}; "
          f"{out / 'views.jsonl'}")


if __name__ == "__main__":
    main()
