"""Rewarding the look (review check R21, docs/REVIEW_EXPERIMENTS.md, Amendment 7; a suggestion of S. Sharma).

On unedited colonoscopy frames MedScope-4B usually answers "absent" without inspecting the image, and finds most
polyps when it does zoom. Two ways to make it look before it decides:

- look-first training (SFT): `look_first_sample_fn` builds the usual synthetic trajectories, but zooms on the
  (former) lesion box with probability at least `look_first`, and inspects a lesion-free image (a zoom on a random
  region) with probability `look_first` before the answer "absent";
- a process reward (GRPO): `look_bonus` adds to the cost-matrix reward when a zoom covers the lesion box or the
  erased site, and a smaller amount when a lesion-free image is inspected before it is denied.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from ..actions import parse
from ..data.schema import View, ViewKind

HIT, INSPECT, MIN_SHARE = 0.5, 0.25, 0.5       # fixed in Amendment 7
BOXED = (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL, ViewKind.TARGET_REMOVAL)


def zoom_boxes(turn_texts: list[str]) -> list[list[int]]:
    """The boxes of every zoom call in an episode's assistant turns, in order."""
    out = []
    for text in turn_texts:
        tool = parse(text).tool
        if tool is not None and tool.name == "zoom" and isinstance(tool.args.get("box"), (list, tuple)) \
                and len(tool.args["box"]) == 4:
            out.append([int(v) for v in tool.args["box"]])
    return out


def covered_share(zoom: list[int], box: list[int]) -> float:
    """Share of `box` (area) that lies inside `zoom`; both in 0-1000 coordinates."""
    x1, y1, x2, y2 = max(zoom[0], box[0]), max(zoom[1], box[1]), min(zoom[2], box[2]), min(zoom[3], box[3])
    area = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    return (max(0, x2 - x1) * max(0, y2 - y1)) / area if area else 0.0


def look_bonus(view: View, turn_texts: list[str], action: Optional[str], claims_absent: Optional[bool],
               hit: float = HIT, inspect: float = INSPECT, min_share: float = MIN_SHARE) -> float:
    """The process reward of one episode.

    Lesion, control-edited and erased views carry the lesion's (or the erased site's) box: `hit` if any zoom covers
    at least `min_share` of it. A lesion-free view without a box: `inspect` if the model zoomed at all and then
    answered that the finding is absent. Nothing otherwise (degraded views, general VQA)."""
    zooms = zoom_boxes(turn_texts)
    if not zooms:
        return 0.0
    if view.kind in BOXED and view.lesion_box is not None:
        return hit if any(covered_share(z, list(view.lesion_box)) >= min_share for z in zooms) else 0.0
    if view.kind is ViewKind.NATURAL_NEGATIVE and view.lesion_box is None and "benchmark" not in view.meta:
        return inspect if action == "answer" and bool(claims_absent) else 0.0
    return 0.0


def episode_reward(hit: float = HIT, inspect: float = INSPECT) -> Callable:
    """Reward function for train_grpo: the cost-matrix reward plus the process reward."""
    def fn(ep) -> float:
        o = ep.outcome
        return float(o.reward) + look_bonus(ep.view, [t.text for t in ep.turns], o.action, o.claims_absent, hit, inspect)
    return fn


def random_region(rng: np.random.Generator) -> list[int]:
    """A square region, 30-50% of the image on a side, anywhere in the image (0-1000 coordinates)."""
    side = int(rng.integers(300, 501))
    x1, y1 = int(rng.integers(0, 1001 - side)), int(rng.integers(0, 1001 - side))
    return [x1, y1, x1 + side, y1 + side]


def look_first_sample_fn(mode: str, window_prob: float, small_zoom: bool, look_first: float) -> Callable:
    """sample_fn for train_sft: the synthetic trajectory of medscope.train.sft.samples_for with inspection made the
    rule (see the module text). With look_first = 0 it gives exactly the usual trajectories."""
    from ..agent.trajectories import build_trajectory
    from .sft import SMALL_LESION, lesion_fraction

    def fn(view: View, seed: int, index: int):
        rng = np.random.default_rng([seed, index])
        frac = lesion_fraction(view)
        zoom_prob = 1.0 if small_zoom and frac is not None and frac < SMALL_LESION else 0.6
        return build_trajectory(view, rng, zoom_prob=max(zoom_prob, look_first), direct_only=(mode == "grounding"),
                                window_prob=window_prob, look_first=look_first)
    return fn
