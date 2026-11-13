"""Screening stage B: new image evidence for every dev view (docs/SCREENING.md).

The dev set is a fixed sample of validation cases: the unedited lesion image, its LaMa erasure and control edit (as
built for the benchmark), the same erasure and control made with TELEA (a held-out tool), and validation lesion-free
images. For each view the probes record, without the gold answer:

  direct    the recipe's answer, with the probability of its answer tokens
  tta       the recipe's answer on three altered copies (mirror, 90% centre crop, contrast change)
  crop      the recipe's answer on a close-up of the region it marked, and on an equal close-up elsewhere on tissue
  cautious  the recipe's answer under the cautious prompt (the question may name an absent finding)
  second    a different model's answer (zero-shot, the benchmark prompt)
  specialist  the lesion segmenter's peak score
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from ..agent.episode import Episode, run_episodes
from ..agent.trajectories import pad_box
from ..data.counterfactual import foreground_mask, make_random_removal, make_target_removal, telea_inpaint
from ..data.schema import Box, View, ViewKind, box_to_pixels, iou, pixels_to_box
from ..data.views import load_image
from ..env.tools import zoom
from ..mas.reports import reader_report

PROBES_VERSION = "b1"


# ---- the dev set ------------------------------------------------------------------------------------------------------

def dev_views(views: list[View], negatives: list[View], n_cases: int, n_neg: int, out_dir: str | Path,
              seed: int = 0) -> list[View]:
    """A fixed sample of validation cases with their LaMa views, plus TELEA erasure and control views made here
    (saved under out_dir, meta inpainter='telea'), plus lesion-free validation images."""
    out = Path(out_dir)
    by_case: dict[str, dict[str, View]] = {}
    for v in views:
        if v.kind in (ViewKind.ORIGINAL, ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL) and not v.meta.get("benchmark"):
            by_case.setdefault(v.case_id, {})[v.kind.value] = v
    complete = sorted(c for c, d in by_case.items() if len(d) == 3 and d["original"].meta.get("lesion_mask"))
    rng = np.random.default_rng(seed)
    cases = sorted(rng.permutation(complete)[:n_cases].tolist())
    dev: list[View] = []
    for c in cases:
        d = by_case[c]
        dev += [d["original"], d["target_removal"], d["random_removal"]]
        o = d["original"]
        tdir = out / c
        paths = (tdir / "telea_target.png", tdir / "telea_control.png")
        if not all(p.exists() for p in paths):
            img = load_image(o.image_path)
            m = cv2.imread(o.meta["lesion_mask"], cv2.IMREAD_GRAYSCALE)
            if m.shape != img.shape[:2]:
                m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
            mask = m > 127
            tgt, _ = make_target_removal(img, mask, inpaint_fn=telea_inpaint)
            ctl = make_random_removal(img, mask, np.random.default_rng(int(hashlib.sha1(c.encode()).hexdigest()[:8], 16)),
                                      inpaint_fn=telea_inpaint)
            if ctl is None:
                continue
            tdir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(paths[0]), cv2.cvtColor(tgt, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(paths[1]), cv2.cvtColor(ctl[0], cv2.COLOR_RGB2BGR))
        dev.append(replace(d["target_removal"], view_id=f"{c}__telea_target", image_path=str(paths[0]),
                           meta={**d["target_removal"].meta, "inpainter": "telea"}))
        dev.append(replace(d["random_removal"], view_id=f"{c}__telea_control", image_path=str(paths[1]),
                           meta={**d["random_removal"].meta, "inpainter": "telea"}))
    negs = [v for v in negatives if v.kind is ViewKind.NATURAL_NEGATIVE]
    dev += [negs[i] for i in sorted(np.random.default_rng(seed + 1).permutation(len(negs))[:n_neg])]
    return dev


def subset_of(view: View) -> str:
    """'telea' for the held-out-tool views, 'lama' for the benchmark's own erasures, 'shared' for the rest."""
    if view.meta.get("inpainter") == "telea":
        return "telea"
    if view.kind in (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL):
        return "lama"
    return "shared"


# ---- altered copies and close-ups -------------------------------------------------------------------------------------

def tta_images(img: np.ndarray) -> list[np.ndarray]:
    h, w = img.shape[:2]
    flip = np.ascontiguousarray(img[:, ::-1])
    y0, x0 = int(0.05 * h), int(0.05 * w)
    crop = cv2.resize(img[y0:h - y0, x0:w - x0], (w, h), interpolation=cv2.INTER_CUBIC)
    contrast = np.clip((img.astype(np.float32) - 128) * 1.25 + 128, 0, 255).astype(np.uint8)
    return [flip, crop, contrast]


def control_box(img: np.ndarray, box: Box, rng: np.random.Generator, tries: int = 300) -> Optional[Box]:
    """A box of the same size elsewhere on tissue, not overlapping the given one."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box_to_pixels(box, w, h)
    bw, bh = x2 - x1, y2 - y1
    if bw < 2 or bh < 2 or bw >= w or bh >= h:
        return None
    tissue = foreground_mask(img)
    for _ in range(tries):
        tx, ty = int(rng.integers(0, w - bw + 1)), int(rng.integers(0, h - bh + 1))
        cand = pixels_to_box(tx, ty, tx + bw, ty + bh, w, h)
        if iou(cand, box) > 0 or tissue[ty:ty + bh, tx:tx + bw].mean() < 0.9:
            continue
        return cand
    return None


def says(ep: Episode) -> dict:
    r = reader_report(ep)
    r["answer_prob"] = ep.outcome.answer_prob
    return r


# ---- computing the probes -----------------------------------------------------------------------------------------------

def read_probes(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[r["view_id"]] = r
    return out


def compute_probes(policy, second, specialist, views: list[View], cfg: dict, out_path: str | Path,
                   batch_size: int = 12, log: Callable[[str], None] = print) -> dict[str, dict]:
    from ..agent.prompts import set_prompt
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    have = {k: r for k, r in read_probes(out).items() if r.get("version") == PROBES_VERSION}
    out.write_text("".join(json.dumps(r) + "\n" for r in have.values()))
    todo = [v for v in views if v.view_id not in have]
    log(f"probes: {len(have)} done, {len(todo)} to run")
    t0 = time.time()
    with open(out, "a") as f:
        for b in range(0, len(todo), batch_size):
            chunk = todo[b:b + batch_size]
            imgs = [load_image(v.image_path) for v in chunk]
            # direct answers and the three altered copies, one batch
            jobs_v, jobs_i = list(chunk), list(imgs)
            for v, im in zip(chunk, imgs):
                for t in tta_images(im):
                    jobs_v.append(v)
                    jobs_i.append(t)
            eps = run_episodes(policy, jobs_v, cfg, sample=False, images=jobs_i)
            n = len(chunk)
            direct = [says(e) for e in eps[:n]]
            tta = [[says(e) for e in eps[n + 3 * i:n + 3 * i + 3]] for i in range(n)]
            # close-ups: the region the recipe marked, and an equal region elsewhere on tissue
            cv_, ci_, owner = [], [], []
            for i, (v, im) in enumerate(zip(chunk, imgs)):
                box = direct[i].get("box") if direct[i].get("action") == "answer" else None
                if not box:
                    continue
                cb = control_box(im, pad_box(box), np.random.default_rng(int(hashlib.sha1(v.view_id.encode()).hexdigest()[:8], 16)))
                try:
                    cv_.append(v), ci_.append(zoom(im, pad_box(box))), owner.append((i, "crop"))
                    if cb:
                        cv_.append(v), ci_.append(zoom(im, cb)), owner.append((i, "crop_control"))
                except ValueError:
                    continue
            crops: list[dict] = [{} for _ in range(n)]
            if cv_:
                for (i, which), e in zip(owner, run_episodes(policy, cv_, cfg, sample=False, images=ci_)):
                    crops[i][which] = says(e)
            # the cautious prompt
            set_prompt("cautious")
            try:
                caut = [says(e) for e in run_episodes(policy, list(chunk), cfg, sample=False, images=list(imgs))]
            finally:
                set_prompt("agent")
            sec = [says(e) for e in run_episodes(second, list(chunk), cfg, sample=False, images=list(imgs))] if second else [None] * n
            spec = [specialist.report(im) for im in imgs] if specialist else [None] * n
            for i, v in enumerate(chunk):
                f.write(json.dumps({"view_id": v.view_id, "version": PROBES_VERSION, "direct": direct[i], "tta": tta[i],
                                    "crop": crops[i].get("crop"), "crop_control": crops[i].get("crop_control"),
                                    "cautious": caut[i], "second": sec[i],
                                    "specialist_peak": None if spec[i] is None else spec[i]["peak"]}) + "\n")
            f.flush()
            done = b + len(chunk)
            rate = (time.time() - t0) / done
            log(f"  probes {done}/{len(todo)}, {rate:.1f}s per view, ~{rate * (len(todo) - done) / 60:.0f} min left")
    return read_probes(out)
