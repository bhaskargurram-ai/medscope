"""Framework stage 0 (docs/FRAMEWORK_STAGE0.md): where does the recipe's evidence sensitivity come from?

Validation cases only (the screening dev set of docs/SCREENING.md, the same 200 cases and their LaMa and TELEA
views). Three new views per case and tool make the edit's *site* independent of the label:

  ring      the same tool fills a ring of the erasure's area right around the lesion; the lesion stays (present)
  restored  the erasure with the lesion's own pixels put back inside the lesion mask; only the 5-pixel band that
            the erasure also edited stays filled (present)
  partial   half of the lesion erased with the same tool (LaMa only; graded evidence, present)

For each view and model the score is the decision log-odds s(x) = log p(present reply) - log p(absent reply),
single turn, the replies worded from the unedited view (as in medscope/train/cmcc.py), so every variant of a case is
scored on identical text. For the recipe and the untrained base model, hidden states at a few layers (last prompt
token and the mean over image tokens) are kept for linear probes.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable, Iterable, Optional

import cv2
import numpy as np

from ..data.counterfactual import dilate, telea_inpaint
from ..data.schema import View, ViewKind
from ..data.views import load_image

STAGE0_VERSION = "s0.1"
MARGIN = 5          # the erasure's dilation (make_target_removal default)
GAP = 2             # the ring starts this many pixels outside the lesion
VARIANTS = ("original", "erased", "control", "ring", "restored", "partial", "negative")
PRESENT = {"original": True, "control": True, "ring": True, "restored": True, "partial": True,
           "erased": False, "negative": False}


# ---- new views -------------------------------------------------------------------------------------------------------

def ring_mask(lesion: np.ndarray, area: int, gap: int = GAP, max_r: int = 400) -> Optional[np.ndarray]:
    """A ring around the lesion (starting `gap` pixels outside it) whose area reaches `area`, or None if the image
    cannot hold a ring of at least 70% of that area."""
    lesion = lesion.astype(bool)
    inner = dilate(lesion, gap)
    best = None
    lo, hi = gap + 1, max_r
    while lo <= hi:                                  # smallest radius whose ring reaches the area
        r = (lo + hi) // 2
        ring = dilate(lesion, r) & ~inner
        if ring.sum() >= area:
            best, hi = ring, r - 1
        else:
            lo = r + 1
    if best is None:
        ring = dilate(lesion, max_r) & ~inner
        return ring if ring.sum() >= 0.7 * area else None
    return best


def half_mask(lesion: np.ndarray) -> np.ndarray:
    """The half of the lesion on one side of its centroid along its longer axis (the erased part of 'partial')."""
    ys, xs = np.nonzero(lesion)
    if len(xs) == 0:
        return lesion.astype(bool)
    yy, xx = np.mgrid[:lesion.shape[0], :lesion.shape[1]]
    if xs.max() - xs.min() >= ys.max() - ys.min():
        side = xx < np.median(xs)
    else:
        side = yy < np.median(ys)
    return lesion.astype(bool) & side


def load_lesion(view: View, shape: tuple[int, int]) -> np.ndarray:
    m = cv2.imread(view.meta["lesion_mask"], cv2.IMREAD_GRAYSCALE)
    if m.shape != shape:
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return m > 127


def _save(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


def new_views(dev: list[View], out_dir: str | Path, lama: Callable, telea: Callable = telea_inpaint) -> list[View]:
    """Ring, restored and partial views for every dev case (files saved under out_dir; existing files reused)."""
    out = Path(out_dir)
    by: dict[str, dict[str, View]] = {}
    for v in dev:
        tool = v.meta.get("inpainter", "lama") if v.kind in (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL) else None
        key = v.kind.value + (f"/{tool}" if tool else "")
        by.setdefault(v.case_id, {})[key] = v
    made: list[View] = []
    for c in sorted(by):
        d = by[c]
        o = d.get("original")
        if o is None or not o.meta.get("lesion_mask"):
            continue
        img = None
        for tool, fn in (("lama", lama), ("telea", telea)):
            erased = d.get(f"target_removal/{tool}")
            if erased is None:
                continue
            paths = {k: out / c / f"{tool}_{k}.png" for k in ("ring", "restored", "partial")}
            if tool != "lama":
                paths.pop("partial")
            if not all(p.exists() for p in paths.values()):
                img = load_image(o.image_path) if img is None else img
                lesion = load_lesion(o, img.shape[:2])
                if not paths["ring"].exists():
                    ring = ring_mask(lesion, int(dilate(lesion, MARGIN).sum()))
                    if ring is not None:
                        _save(paths["ring"], fn(img, ring))
                if not paths["restored"].exists():
                    e = load_image(erased.image_path)
                    if e.shape == img.shape:
                        e = e.copy()
                        e[lesion] = img[lesion]
                        _save(paths["restored"], e)
                if "partial" in paths and not paths["partial"].exists():
                    half = half_mask(lesion)
                    if half.any() and (lesion & ~half).any():
                        _save(paths["partial"], fn(img, dilate(half, MARGIN) & ~lesion | half))
            for k, p in paths.items():
                if p.exists():
                    made.append(replace(o, view_id=f"{c}__{tool}_{k}", image_path=str(p), kind=ViewKind.RANDOM_REMOVAL,
                                        meta={**o.meta, "inpainter": tool, "stage0_variant": k}))
    return made


def variant_of(view: View) -> tuple[str, Optional[str]]:
    """(variant, tool) of a stage-0 view."""
    if "stage0_variant" in view.meta:
        return view.meta["stage0_variant"], view.meta["inpainter"]
    if view.kind is ViewKind.ORIGINAL:
        return "original", None
    if view.kind is ViewKind.NATURAL_NEGATIVE:
        return "negative", None
    tool = view.meta.get("inpainter", "lama")
    return ("erased" if view.kind is ViewKind.TARGET_REMOVAL else "control"), tool


# ---- scoring -----------------------------------------------------------------------------------------------------------

def read_scores(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("version") == STAGE0_VERSION:
                out[r["view_id"]] = r
    return out


def reference_view(view: View, originals: dict[str, View]) -> View:
    """The view whose answer words the two candidate replies: the case's unedited view (lesion-free images: their own,
    with the 'present' reply being the yes/no answer that names the finding)."""
    if view.kind is ViewKind.NATURAL_NEGATIVE:
        from ..actions import asks_health
        return replace(view, answer="No" if asks_health(view.question) else "Yes", lesion_box=None)
    return originals.get(view.case_id, view)


def scoreable(view: View, originals: dict[str, View]) -> bool:
    """Yes/no questions only (as medscope/train/cmcc.py): an open question has no clean present/absent reply pair."""
    from ..actions import normalise_answer
    from ..agent.trajectories import absent_text
    if view.kind is ViewKind.NATURAL_NEGATIVE:
        return normalise_answer(view.answer) in ("yes", "no")
    o = originals.get(view.case_id)
    if o is None:
        return False
    return not (absent_text(o) == "No abnormality" and normalise_answer(o.answer) not in ("yes", "no"))


def hidden_features(policy, inputs, layers: Iterable[int]) -> Optional[np.ndarray]:
    """[n_layers, 2, d] float16: last prompt token and the mean over image tokens, at each requested layer."""
    torch = policy.torch
    with torch.no_grad():
        out = policy.model(**inputs, use_cache=False, output_hidden_states=True)
    hs = getattr(out, "hidden_states", None)
    if hs is None:
        return None
    ids = inputs["input_ids"][0]
    img_id = None
    for obj in (policy.model, getattr(policy.model, "base_model", None), getattr(policy.model, "config", None)):
        cfg = getattr(obj, "config", obj)
        img_id = getattr(cfg, "image_token_id", None) or getattr(cfg, "image_token_index", None)
        if img_id is not None:
            break
    is_img = (ids == img_id) if img_id is not None else torch.zeros_like(ids, dtype=torch.bool)
    feats = []
    for layer in layers:
        h = hs[min(layer, len(hs) - 1)][0].float()
        last = h[-1]
        mean = h[is_img].mean(0) if bool(is_img.any()) else h.mean(0)
        feats.append(torch.stack([last, mean]))
    return torch.stack(feats).cpu().numpy().astype(np.float16)


def score_views(policy, views: list[View], originals: dict[str, View], out_path: str | Path,
                hidden_path: Optional[str | Path] = None, layers: Iterable[int] = (),
                log: Callable[[str], None] = print) -> dict[str, dict]:
    """s(x) for every view (resumable jsonl); with hidden_path, the hidden features too (one .npy per view under it)."""
    from ..agent.prompts import start_messages
    from ..train.cmcc import candidates
    torch = policy.torch
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    have = read_scores(out)
    out.write_text("".join(json.dumps(r) + "\n" for r in have.values()))
    hdir = Path(hidden_path) if hidden_path else None
    if hdir:
        hdir.mkdir(parents=True, exist_ok=True)
    todo = [v for v in views if v.view_id not in have or (hdir and not (hdir / f"{v.view_id}.npy").exists())]
    log(f"stage 0 scores: {len(have)} done, {len(todo)} to run")
    policy.model.eval()
    t0 = time.time()
    with open(out, "a") as f:
        for i, v in enumerate(todo):
            ref = reference_view(v, originals)
            present, absent = candidates(ref)
            inputs = policy.encode(start_messages(load_image(v.image_path), ref.question))
            with torch.no_grad():
                lp_p, lp_a = policy.token_logprobs_pair(None, policy.target_ids(present), policy.target_ids(absent),
                                                        inputs=inputs)
            if hdir and not (hdir / f"{v.view_id}.npy").exists():
                h = hidden_features(policy, inputs, layers)
                if h is not None:
                    np.save(hdir / f"{v.view_id}.npy", h)
            if v.view_id not in have:
                variant, tool = variant_of(v)
                f.write(json.dumps({"view_id": v.view_id, "case_id": v.case_id, "variant": variant, "tool": tool,
                                    "version": STAGE0_VERSION, "s": float(lp_p.sum() - lp_a.sum()),
                                    "lp_present": float(lp_p.sum()), "lp_absent": float(lp_a.sum())}) + "\n")
                f.flush()
            if (i + 1) % 50 == 0 or i + 1 == len(todo):
                rate = (time.time() - t0) / (i + 1)
                log(f"  {i + 1}/{len(todo)}, {rate:.2f}s per view, ~{rate * (len(todo) - i - 1) / 60:.0f} min left")
    return read_scores(out)


def case_seed(text: str) -> int:
    return int(hashlib.sha1(text.encode()).hexdigest()[:8], 16)
