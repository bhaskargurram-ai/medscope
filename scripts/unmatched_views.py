"""Unmatched control edits: the same training cases, but the control edit no longer matches the erasure.

MedScope's control view (random_removal) applies the erasure's own edit, same shape and same tool, somewhere
that avoids the lesion. A reviewer asked whether matching matters, or whether any edit elsewhere would do. This
script makes an unmatched control for every training case: an ellipse of a different size (half or twice the
erasure's area, random aspect ratio and orientation) placed away from the lesion on tissue, filled with the
*other* training tool (tissue transplant for cases whose erasure used LaMa, LaMa for cases whose erasure used
transplant). Telea and diffusion stay unseen, so the held-out-tool tests remain held out for this arm.

The output manifest is the input manifest with every random_removal view replaced by its unmatched version (same
view id, same expected answer: the lesion is intact), so an arm trained on it is like-for-like with the matched
control arm: same cases, same other views, same steps; only the control differs.

    python scripts/unmatched_views.py --views TRAIN_VIEWS... --out DIR
    -> DIR/views.jsonl (the full arm manifest), DIR/dropped.jsonl, DIR/<case>/random_removal.png
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.counterfactual import dilate, foreground_mask  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.schema import View, ViewKind, mask_to_box  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

AREA_FACTORS = (0.5, 2.0)     # the unmatched edit is half or twice the erasure's area, never the same
MARGIN, KEEP_AWAY, MIN_FOREGROUND, MAX_TRIES = 5, 10, 0.9, 500


def _load_mask(path: str, shape: tuple[int, int]) -> np.ndarray:
    m = np.asarray(Image.open(path).convert("L"))
    if m.shape != shape:
        m = np.asarray(Image.fromarray(m).resize((shape[1], shape[0]), Image.NEAREST))
    return m > 127


def ellipse(area: float, aspect: float, angle: float, h: int, w: int) -> np.ndarray | None:
    """A filled ellipse of the given area (pixels), aspect ratio and orientation, as a tight boolean patch."""
    a = np.sqrt(area * aspect / np.pi)          # semi-axes: a * b * pi = area, a / b = aspect
    b = area / (np.pi * a)
    r = int(np.ceil(max(a, b))) + 1
    if 2 * r >= min(h, w):
        return None
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    c, s = np.cos(angle), np.sin(angle)
    u, v = c * xx + s * yy, -s * xx + c * yy
    patch = (u / a) ** 2 + (v / b) ** 2 <= 1.0
    ys, xs = np.nonzero(patch)
    return patch[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def place(patch: np.ndarray, lesion: np.ndarray, tissue: np.ndarray, rng: np.random.Generator) -> np.ndarray | None:
    ph, pw = patch.shape
    h, w = lesion.shape
    forbidden = dilate(lesion, MARGIN + KEEP_AWAY)
    for _ in range(MAX_TRIES):
        ty, tx = int(rng.integers(0, h - ph + 1)), int(rng.integers(0, w - pw + 1))
        if (forbidden[ty:ty + ph, tx:tx + pw] & patch).any():
            continue
        if (tissue[ty:ty + ph, tx:tx + pw] & patch).sum() < MIN_FOREGROUND * patch.sum():
            continue
        out = np.zeros_like(lesion, dtype=bool)
        out[ty:ty + ph, tx:tx + pw] = patch
        return out
    return None


def unmatched_mask(lesion: np.ndarray, image: np.ndarray, key: str) -> tuple[np.ndarray, float] | None:
    """An unmatched edit region for this case, or None if none fits: tries the two area factors in a
    case-dependent order, several aspect ratios and orientations, then gives up."""
    rng = np.random.default_rng(stable_index(key, 2 ** 31))
    base_area = float(dilate(lesion, MARGIN).sum())
    tissue = foreground_mask(image)
    h, w = lesion.shape
    factors = list(AREA_FACTORS) if rng.random() < 0.5 else list(AREA_FACTORS)[::-1]
    for factor in factors:
        for _ in range(6):
            patch = ellipse(base_area * factor, float(rng.uniform(0.6, 1.6)), float(rng.uniform(0, np.pi)), h, w)
            if patch is None:
                continue
            mask = place(patch, lesion, tissue, rng)
            if mask is not None:
                return mask, factor
    return None


def fill(tool: str, image: np.ndarray, hole: np.ndarray, lesion: np.ndarray, seed: int) -> np.ndarray:
    if tool == "transplant":
        from medscope.data.inpaint import transplant_inpaint
        return transplant_inpaint(image, hole, avoid=lesion, seed=seed)
    if tool == "lama":
        from medscope.data.inpaint import lama_inpaint
        return lama_inpaint(image, hole)
    raise ValueError(tool)


def other_tool(target_view: View) -> str:
    """The training tool the erasure did not use: transplant for LaMa erasures, LaMa for transplant ones."""
    used = (target_view.meta or {}).get("inpainter", "lama")
    return "lama" if used == "transplant" else "transplant"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True, help="training views files (the matched arm's)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    views = [v for f in args.views for v in load_views(f)]
    targets = {v.case_id: v for v in views if v.kind is ViewKind.TARGET_REMOVAL}
    kept, dropped, stats = [], [], Counter()
    n_ctrl = sum(v.kind is ViewKind.RANDOM_REMOVAL for v in views)
    done = 0
    for v in views:
        if v.kind is not ViewKind.RANDOM_REMOVAL:
            kept.append(v)
            continue
        done += 1
        meta = v.meta or {}
        tgt = targets.get(v.case_id)
        try:
            if tgt is None or not meta.get("original_image") or not meta.get("lesion_mask"):
                raise ValueError("no erasure view or no stored original/lesion mask")
            original = load_image(meta["original_image"])
            lesion = _load_mask(meta["lesion_mask"], original.shape[:2])
            tool = other_tool(tgt)
            png = out / v.case_id / "random_removal.png"
            mask_png = out / v.case_id / "random_edit_mask.png"
            if png.exists() and mask_png.exists():
                hole = _load_mask(str(mask_png), original.shape[:2])
                factor = float(json.loads((out / v.case_id / "meta.json").read_text())["area_factor"])
            else:
                got = unmatched_mask(lesion, original, v.view_id + "unmatched")
                if got is None:
                    raise ValueError("no room for an unmatched edit away from the lesion")
                hole, factor = got
                img = fill(tool, original, hole, lesion, seed=stable_index(v.view_id + tool, 2 ** 31))
                keep = ~dilate(hole, 4)
                if not np.array_equal(img[keep], original[keep]):
                    raise ValueError("the edit changed pixels outside the edit region")
                if (hole & dilate(lesion, MARGIN)).any():
                    raise ValueError("the unmatched edit touched the lesion")
                png.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(img).save(png)
                Image.fromarray(hole.astype(np.uint8) * 255).save(mask_png)
                (out / v.case_id / "meta.json").write_text(json.dumps({"area_factor": factor, "inpainter": tool}))
            kept.append(replace(v, image_path=str(png),
                                meta={**meta, "edit_box": mask_to_box(hole), "edit_mask": str(mask_png),
                                      "control": "unmatched", "area_factor": factor, "inpainter": tool}))
            stats[(tool, factor)] += 1
        except (ValueError, KeyError, OSError) as exc:
            dropped.append({"case_id": v.case_id, "view_id": v.view_id, "reason": str(exc)})
            kept.append(v)                                      # keep the matched control rather than lose the case
            stats["kept matched (no unmatched edit possible)"] += 1
        if done % 200 == 0:
            print(f"  {done}/{n_ctrl} controls", flush=True)
    (out / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in kept))
    (out / "dropped.jsonl").write_text("".join(json.dumps(r) + "\n" for r in dropped))
    summary = {str(k): n for k, n in stats.items()}
    (out / "summary.json").write_text(json.dumps({"controls": n_ctrl, "views": len(kept), **summary}, indent=1))
    print(f"{n_ctrl} controls: {summary}; {len(kept)} views -> {out / 'views.jsonl'}")


if __name__ == "__main__":
    main()
