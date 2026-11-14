"""Framework stage 1 (docs/FRAMEWORK_STAGE1.md): tool-family counterfactual views for training.

The same training cases as the replay-only control `v4q_sftc_s0` (scripts/train_cmcc.py, --cases 3000 = all 2,739 triplets, seed 0).
Each LaMa case gets one edit tool and one control site, assigned from its id: tool in {LaMa, blur, mean, shuffle}
(medscope/data/fills.py; TELEA and diffusion stay held out), control either elsewhere (far, as the benchmark) or in a
ring right around the lesion (lesion intact). The erasure and its control use the **same** tool, so neither the tool
nor the edit's site carries the label. LaMa cases with a far control keep their stored views; cases made with the
transplant tool are kept as they are.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from ..data.counterfactual import dilate, make_random_removal, make_target_removal
from ..data.fills import FILLS
from ..data.schema import View
from ..data.views import load_image
from .stage0 import MARGIN, load_lesion, ring_mask

TOOLS = ("lama", "blur", "mean", "shuffle")
SITES = ("far", "ring")


def case_hash(case_id: str) -> int:
    return int(hashlib.sha1(case_id.encode()).hexdigest()[:8], 16)


def assignment(case_id: str) -> tuple[str, str]:
    h = case_hash(case_id)
    return TOOLS[h % len(TOOLS)], SITES[(h // len(TOOLS)) % len(SITES)]


def select_cases(triplets: list, cases: int, seed: int) -> list:
    """The same subset scripts/train_cmcc.py takes."""
    if cases and cases < len(triplets):
        rng = np.random.default_rng(seed)
        triplets = [triplets[i] for i in sorted(rng.permutation(len(triplets))[:cases])]
    return triplets


def _fill_fn(tool: str, lama: Callable, seed: int) -> Callable:
    if tool == "lama":
        return lama
    fn = FILLS[tool]
    if tool in ("mean", "shuffle"):
        return lambda img, m: fn(img, m, seed=seed)
    return fn


def _save(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


def build_toolfamily(triplets: list, out_dir: str | Path, lama: Callable, log: Callable[[str], None] = print,
                     ) -> list[View]:
    """Original, erasure and control views for every triplet (images under out_dir; existing files reused)."""
    out = Path(out_dir)
    views: list[View] = []
    counts: dict[str, int] = {}
    for t in triplets:
        o, e, c = t.original, t.erased, t.control
        stored_tool = e.meta.get("inpainter", "lama")
        tool, site = assignment(t.case_id)
        if stored_tool != "lama" or not o.meta.get("lesion_mask") or (tool == "lama" and site == "far"):
            key = f"{stored_tool}/far (stored)"
            views += [o, e, c]
            counts[key] = counts.get(key, 0) + 1
            continue
        d = out / t.case_id
        pe, pc = d / f"{tool}_erased.png", d / f"{tool}_{site}_control.png"
        seed = case_hash(t.case_id)
        if not (pe.exists() and pc.exists()):
            img = load_image(o.image_path)
            lesion = load_lesion(o, img.shape[:2])
            if not lesion.any():
                views += [o, e, c]
                counts["no mask (stored)"] = counts.get("no mask (stored)", 0) + 1
                continue
            fill = _fill_fn(tool, lama, seed)
            if not pe.exists():
                if tool == "lama":
                    erased = load_image(e.image_path)
                else:
                    erased, _ = make_target_removal(img, lesion, margin=MARGIN, inpaint_fn=fill)
                _save(pe, erased)
            if not pc.exists():
                ctl = None
                if site == "ring":
                    ring = ring_mask(lesion, int(dilate(lesion, MARGIN).sum()))
                    ctl = fill(img, ring) if ring is not None else None
                else:
                    r = make_random_removal(img, lesion, np.random.default_rng(seed), margin=MARGIN, inpaint_fn=fill)
                    ctl = r[0] if r is not None else None
                if ctl is None:                     # no room for this control: keep the stored views for this case
                    views += [o, e, c]
                    counts["no room (stored)"] = counts.get("no room (stored)", 0) + 1
                    continue
                _save(pc, ctl)
        meta = {"tf_tool": tool, "tf_site": site}
        views += [o,
                  replace(e, view_id=f"{t.case_id}__tf_target", image_path=str(pe),
                          meta={**e.meta, **meta, "inpainter": tool}),
                  replace(c, view_id=f"{t.case_id}__tf_control", image_path=str(pc),
                          meta={**c.meta, **meta, "inpainter": tool})]
        key = f"{tool}/{site}"
        counts[key] = counts.get(key, 0) + 1
    log("tool-family views: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return views


def write_views(views: list[View], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(v.to_dict()) + "\n" for v in views))


def tool_counts(views: list[View]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in views:
        if "tf_tool" in v.meta and v.view_id.endswith("__tf_control"):
            k = f"{v.meta['tf_tool']}/{v.meta['tf_site']}"
            out[k] = out.get(k, 0) + 1
    return out

