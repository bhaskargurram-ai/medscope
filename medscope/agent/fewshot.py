"""Few-shot examples for frontier models: solved cases from the TRAINING split shown before each test case.

A trained model saw thousands of counterfactual views; a frontier model sees none. This gives a
frontier model the same lesson in context, with four solved examples from other patients:

  1. a lesion image, answered "present" with the lesion box          (original)
  2. the same image with the lesion erased, answered "absent"         (target_removal)
  3. another image edited elsewhere, lesion intact, "present" + box   (random_removal)
  4. an unedited healthy image, answered "absent"                     (natural_negative)

Examples come only from training views, so no test patient is shown. The choice is deterministic.
"""

from __future__ import annotations

import json

from ..actions import absent_reply
from ..data.loaders.common import stable_index
from ..data.schema import View, ViewKind
from ..data.views import load_image
from .prompts import assistant_message, first_user_message

# preferred source per example (case-id prefixes); falls back to any source with the right view
PREFER = {"original": ("kvasir",), "random_removal": ("busi", "lgg", "chestxdet"),
          "natural_negative": ("lgg", "chestxdet", "busi", "slakeneg", "hkneg")}


def _final(**obj) -> str:
    return f"<final>{json.dumps(obj)}</final>"


def _yes_no(v: View) -> bool:
    """A presence question whose erased version has a clear "absent" answer."""
    return v.lesion_box is not None and absent_reply(v.question, v.answer) is not None


def _pick(cands: list[View], prefixes: tuple[str, ...], seed: str) -> View:
    for p in prefixes:
        pool = [v for v in cands if v.case_id.startswith(p)]
        if pool:
            return sorted(pool, key=lambda v: stable_index(v.view_id + seed, 10 ** 9))[0]
    if not cands:
        raise ValueError("no training view of the needed kind for the few-shot examples")
    return sorted(cands, key=lambda v: stable_index(v.view_id + seed, 10 ** 9))[0]


def pick_examples(views: list[View], negatives: list[View], seed: str = "fewshot") -> list[View]:
    by_case: dict[str, dict[ViewKind, View]] = {}
    for v in views:
        by_case.setdefault(v.case_id, {})[v.kind] = v
    pairs = [d[ViewKind.ORIGINAL] for d in by_case.values()
             if ViewKind.ORIGINAL in d and ViewKind.TARGET_REMOVAL in d and _yes_no(d[ViewKind.ORIGINAL])]
    first = _pick(pairs, PREFER["original"], seed)
    erased = by_case[first.case_id][ViewKind.TARGET_REMOVAL]
    controls = [v for v in views if v.kind is ViewKind.RANDOM_REMOVAL and _yes_no(v) and v.case_id != first.case_id]
    control = _pick(controls, PREFER["random_removal"], seed)
    healthy = _pick([v for v in negatives if v.kind is ViewKind.NATURAL_NEGATIVE], PREFER["natural_negative"], seed)
    return [first, erased, control, healthy]


def reply(v: View) -> str:
    """The correct reply to an example, in the benchmark's action format."""
    if v.kind is ViewKind.TARGET_REMOVAL:
        return ("I looked at the relevant area and there is no visible abnormality. "
                + _final(action="answer", answer=absent_reply(v.question, v.answer), confidence=0.9))
    if v.kind is ViewKind.NATURAL_NEGATIVE:
        return ("Nothing in this image shows the finding, so it is not present. "
                + _final(action="answer", answer=v.answer, confidence=0.9))
    return "The finding is clearly visible here. " + _final(action="answer", answer=v.answer, box=v.lesion_box,
                                                            confidence=0.9)


def example_messages(examples: list[View]) -> list[dict]:
    msgs = []
    for v in examples:
        msgs += [first_user_message(load_image(v.image_path), v.question), assistant_message(reply(v))]
    return msgs
