"""Reports of the direct reader, the question-blind reader, the specialist and the counterfactual verifier.

These agents do not learn: the readers are the frozen recipe adapter and the specialist is the trained segmenter.
Their reports are therefore computed once per view and stored (one JSON line per view, resumable), and the
deciding agent is trained and tested on the stored reports; the ablations reuse them. No report ever uses the gold
answer or the view's kind.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..agent.episode import Episode, run_episodes
from ..data.counterfactual import make_random_removal, make_target_removal
from ..data.schema import Box, View, box_area_fraction, box_to_mask
from ..data.views import load_image

BLIND_QUESTION = "Is there any abnormality in this image?"
MAX_VERIFY_AREA = 0.4        # a region covering more than 40% of the image is not a region: not tested
REPORTS_VERSION = "v10.1"


def reader_report(ep: Episode) -> dict:
    """A reader's decision as the other agents see it: action, answer text, box, confidence."""
    f = ep.final
    if ep.malformed or f is None:
        return {"action": "malformed", "tool_calls": ep.tool_calls}
    return {"action": f.kind.value, "answer": f.answer, "box": f.box, "confidence": f.confidence,
            "text": f.text, "tool_calls": ep.tool_calls}


def candidate_box(direct: dict, specialist: Optional[dict], blind: Optional[dict]) -> tuple[Optional[Box], Optional[str]]:
    """The one region the verifier tests: the direct reader's box, else the specialist's top region, else the
    blind reader's box."""
    if direct.get("action") == "answer" and direct.get("box"):
        return list(direct["box"]), "direct reader"
    if specialist and specialist.get("found") and specialist.get("regions"):
        return list(specialist["regions"][0]["box"]), "specialist"
    if blind and blind.get("action") == "answer" and blind.get("box"):
        return list(blind["box"]), "question-blind reader"
    return None, None


def view_rng(view_id: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha1(view_id.encode()).hexdigest()[:8], 16))


def verify_images(image: np.ndarray, box: Box, inpaint_fn, rng: np.random.Generator):
    """(erased image, control image or None, note). The region is a rectangle from the box, erased with the same
    margin as the benchmark's erasures; the control is the same shape placed elsewhere on tissue by the rule that
    built the control views."""
    if box_area_fraction(box) > MAX_VERIFY_AREA:
        return None, None, "region too large to test"
    h, w = image.shape[:2]
    mask = box_to_mask(box, w, h)
    if not mask.any():
        return None, None, "empty region"
    erased, _ = make_target_removal(image, mask, inpaint_fn=inpaint_fn)
    ctrl = make_random_removal(image, mask, rng, inpaint_fn=inpaint_fn)
    if ctrl is None:
        return erased, None, "no place for an equal edit elsewhere"
    return erased, ctrl[0], ""


def report_key(view: View, adapter: str, specialist_meta: dict) -> str:
    payload = json.dumps(view.to_dict(), sort_keys=True) + f"|{adapter}|{json.dumps(specialist_meta, sort_keys=True)}|{REPORTS_VERSION}"
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def read_reports(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:      # a cut-off last line from an interrupted run
                continue
            out[r["view_id"]] = r
    return out


def compute_reports(policy, specialist, inpaint_fn, views: list[View], cfg: dict, out_path: str | Path,
                    adapter: str, batch_size: int = 16, log: Callable[[str], None] = print) -> dict[str, dict]:
    """Reports for every view, appended to out_path; views already there with the same key are skipped."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    spec_meta = {"threshold": getattr(specialist, "threshold", None)}
    keys = {v.view_id: report_key(v, adapter, spec_meta) for v in views}
    have = {k: r for k, r in read_reports(out).items() if r.get("key") == keys.get(k)}
    # rewrite without stale or cut-off lines before appending
    out.write_text("".join(json.dumps(r) + "\n" for r in have.values()))
    todo = [v for v in views if v.view_id not in have]
    log(f"reports: {len(have)} already done, {len(todo)} to run")
    t0 = time.time()
    with open(out, "a") as f:
        for b in range(0, len(todo), batch_size):
            chunk = todo[b:b + batch_size]
            imgs = [load_image(v.image_path) for v in chunk]
            blind_views = [replace(v, question=BLIND_QUESTION) for v in chunk]
            eps = run_episodes(policy, chunk + blind_views, cfg, sample=False, images=imgs + imgs)
            direct, blind = [reader_report(e) for e in eps[:len(chunk)]], [reader_report(e) for e in eps[len(chunk):]]
            spec = [specialist.report(im) for im in imgs]
            # the verifier: erase the candidate region, edit an equal region elsewhere, ask the direct reader again
            jobs, plans = [], []
            for i, (v, im) in enumerate(zip(chunk, imgs)):
                box, source = candidate_box(direct[i], spec[i], blind[i])
                plan = {"box": box, "source": source, "note": "" if box else "no region to test",
                        "erased": None, "control": None}
                if box:
                    erased, control, note = verify_images(im, box, inpaint_fn, view_rng(v.view_id))
                    plan["note"] = note
                    if erased is not None:
                        jobs.append((i, "erased", v, erased))
                    if control is not None:
                        jobs.append((i, "control", v, control))
                plans.append(plan)
            if jobs:
                veps = run_episodes(policy, [j[2] for j in jobs], cfg, sample=False, images=[j[3] for j in jobs])
                for (i, which, _, _), e in zip(jobs, veps):
                    plans[i][which] = reader_report(e)
            for i, v in enumerate(chunk):
                f.write(json.dumps({"view_id": v.view_id, "key": keys[v.view_id], "direct": direct[i], "blind": blind[i],
                                    "specialist": spec[i], "verify": plans[i]}) + "\n")
            f.flush()
            n = b + len(chunk)
            rate = (time.time() - t0) / n
            log(f"  reports {n}/{len(todo)}, {rate:.1f}s per view, ~{rate * (len(todo) - n) / 60:.0f} min left")
    return read_reports(out)
