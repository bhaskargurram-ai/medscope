"""The deciding agent (arbiter): reads the image, the question and the other agents' reports, gives the final action.

Training uses the gold final action for the view (the same targets the recipe was trained on) with the real stored
reports as input, leaving out each of the blind reader, specialist and verifier reports (and the verifier's control
half) with probability 0.25, so every ablation in docs/PREREGISTRATION_v10.md is an input it has seen.
"""

from __future__ import annotations

import json
from typing import Optional

import numpy as np

from ..agent.prompts import image, text
from ..agent.trajectories import SFTSample, build_trajectory
from ..data.schema import View
from ..data.views import load_image

ARBITER_PROMPT = """You are the deciding agent in a team that reads medical images for research. You see the image, the question, and reports from four team members. Decide the final answer from what the image actually shows: report a finding only when the evidence shows it is there, and say so when it is not.

The team members:
1. Direct reader: answered the question as asked. It can be misled by a question that names a finding.
2. Question-blind reader: was asked only whether anything in the image is abnormal, so the question could not suggest an answer to it.
3. Specialist: a lesion segmenter trained on real images. It reports regions it finds, with scores, or that nothing passed its threshold.
4. Verifier: took the one region the others pointed to, erased it, and asked the direct reader the question again; then made an equal edit somewhere else and asked again. A finding the image really shows disappears when its region is erased and stays after the edit elsewhere. A finding that stays after its region is erased came from the question, not the image. If the answer changes after any edit, the test says little.

Any of them can be wrong, and some reports may be missing. Weigh them against each other and against the image.

Give exactly ONE final action as a tagged JSON object and stop (boxes are integers 0-1000 on the image, as [x1, y1, x2, y2]):
<final>{"action": "answer", "answer": "...", "box": [x1, y1, x2, y2], "confidence": 0.0-1.0}</final>
    when the image lets you answer. If the finding is visible, the box marks it. If the finding asked about is not there, say so and leave out the box: "No" to "Is there ...?", "Yes" to "Is ... healthy?" or "Is ... normal?", "No abnormality" to an open question.
<final>{"action": "clarify", "question": "..."}</final>
    when the image is unusable (too blurred, noisy, low resolution, or not the anatomy asked about).
<final>{"action": "refer", "reason": "..."}</final>
    when the image is usable but the evidence does not decide it either way.

Keep answers short, using the wording a radiologist would use."""

PARTS = ("blind", "specialist", "verify", "control")
ABLATIONS: dict[str, frozenset] = {
    "full": frozenset(),
    "nob": frozenset({"blind"}),
    "nos": frozenset({"specialist"}),
    "nov": frozenset({"verify"}),
    "noc": frozenset({"control"}),
    "dir": frozenset({"blind", "specialist", "verify"}),
}
RUN_TAG = {"full": "mas", "nob": "masnob", "nos": "masnos", "nov": "masnov", "noc": "masnoc", "dir": "masdir"}


def run_tag(ablation: str, base: str = "mas") -> str:
    """Run tag of an ablation for a plan: base 'mas' (v10) or 'mas2' (v11)."""
    return base + ("" if ablation == "full" else ablation)
DROP_P = 0.25


def training_drop(rng: np.random.Generator, p: float = DROP_P) -> frozenset:
    return frozenset(part for part in PARTS if rng.random() < p)


def _box(b) -> str:
    return "[" + ", ".join(str(int(x)) for x in b) + "]"


def reader_line(r: Optional[dict]) -> str:
    if not r or r.get("action") == "malformed":
        return "gave no usable reply"
    a = r.get("action")
    if a == "answer":
        s = f'answered "{r.get("answer")}"'
        if r.get("box"):
            s += f" and marked {_box(r['box'])}"
        if r.get("confidence") is not None:
            s += f" (confidence {float(r['confidence']):.2f})"
        return s
    if a == "clarify":
        return "said the image is unusable" + (f' ("{r["text"]}")' if r.get("text") else "")
    if a == "refer":
        return "could not decide and referred" + (f' ("{r["text"]}")' if r.get("text") else "")
    return "gave no usable reply"


def specialist_line(s: dict) -> str:
    if s.get("found") and s.get("regions"):
        regs = "; ".join(f"{_box(r['box'])} score {float(r['score']):.2f}" for r in s["regions"])
        return f"found {len(s['regions'])} region(s): {regs}."
    return f"found nothing above its threshold (highest score {float(s.get('peak', 0)):.2f}, threshold {float(s.get('threshold') or 0):.2f})."


def verify_line(v: dict, with_control: bool = True) -> str:
    if not v.get("box"):
        return "had no region to test."
    if v.get("erased") is None:
        return f"could not test the region {_box(v['box'])} ({v.get('note') or 'no test'})."
    s = f"erased the region {_box(v['box'])} (pointed to by the {v.get('source')}); the direct reader then {reader_line(v['erased'])}."
    if with_control:
        if v.get("control") is not None:
            s += f" After an equal edit elsewhere on the image, it {reader_line(v['control'])}."
        else:
            s += " No place for an equal edit elsewhere was found."
    return s


def reports_text(rep: dict, drop: frozenset = frozenset()) -> str:
    lines = ["Team reports:", f"1. Direct reader: {reader_line(rep.get('direct'))}."]
    lines.append("2. Question-blind reader (asked whether anything is abnormal): "
                 + (f"{reader_line(rep.get('blind'))}." if "blind" not in drop else "report not available."))
    lines.append("3. Specialist: " + (specialist_line(rep["specialist"]) if "specialist" not in drop and rep.get("specialist")
                                      else "report not available."))
    lines.append("4. Verifier: " + (verify_line(rep["verify"], with_control="control" not in drop)
                                    if "verify" not in drop and rep.get("verify") else "report not available."))
    return "\n".join(lines)


def arbiter_messages(img: np.ndarray, question: str, rep: dict, drop: frozenset = frozenset()) -> list[dict]:
    return [{"role": "system", "content": [text(ARBITER_PROMPT)]},
            {"role": "user", "content": [image(img), text(f"Question: {question}\n\n{reports_text(rep, drop)}")]}]


def arbiter_sample(view: View, rep: dict, seed: int, index: int, img: Optional[np.ndarray] = None) -> SFTSample:
    """One training sample: stored reports (some left out at random) in, the gold final action out."""
    rng = np.random.default_rng([seed, index])
    img = img if img is not None else load_image(view.image_path)
    drop = training_drop(rng)
    target = build_trajectory(view, rng, direct_only=True, image=img)[-1].target
    return SFTSample(arbiter_messages(img, view.question, rep, drop), target, view.view_id, view.kind.value)


def stratified_subset(views: list[View], n: int, seed: int = 0) -> list[View]:
    """n training views with the view kinds in their training proportions (fixed seed)."""
    if n >= len(views):
        return list(views)
    rng = np.random.default_rng(seed)
    by_kind: dict[str, list[View]] = {}
    for v in views:
        by_kind.setdefault(v.kind.value, []).append(v)
    out = []
    for kind in sorted(by_kind):
        vs = by_kind[kind]
        k = round(n * len(vs) / len(views))
        out += [vs[i] for i in sorted(rng.permutation(len(vs))[:k])]
    return out


def ablation_key(name: str) -> str:
    return "mas:" + name + ":" + json.dumps(sorted(ABLATIONS[name]))
