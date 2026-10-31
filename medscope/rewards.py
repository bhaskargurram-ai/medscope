"""Cost-matrix reward for RL, also used as the benchmark's net-utility metric."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from .actions import FinalAction, answer_matches, claims_absence
from .data.schema import ActionKind, View, ViewKind, box_area_fraction, iou

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "reward.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def with_vocab(cfg: dict, views) -> dict:
    """Config copy carrying the benchmark's answer vocabulary, used to reject hedged answers."""
    from .actions import answer_vocabulary
    return {**cfg, "answer_vocab": sorted(answer_vocabulary(v.answer for v in views))}


@dataclass
class Outcome:
    """Everything the metrics need about one episode."""

    view_id: str
    case_id: str
    kind: str
    action: Optional[str]          # answer / clarify / refer, None if malformed
    correct: Optional[bool]        # only for answer actions
    iou: float
    confidence: Optional[float]
    tool_calls: int
    malformed: bool
    reward: float
    breakdown: dict
    claims_absent: Optional[bool] = None   # answer says the finding isn't there (answers only)
    box_ok: Optional[bool] = None          # answer's box overlaps the lesion enough for the grounding bonus
    answer_prob: Optional[float] = None    # the model's own probability of its answer tokens (greedy runs)
    free_text: Optional[bool] = None       # decision read from a plain-prose reply (no action tag)

    def to_dict(self) -> dict:
        return asdict(self)


def action_reward(view: View, action: str, correct: Optional[bool], cfg: dict) -> float:
    """The cost-matrix entry for taking `action` on this view (answer correctness given)."""
    if view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL):
        c = cfg["answerable"]
        if action == "answer":
            if correct:
                return c["correct_answer"]
            return c["wrong_answer_critical"] if view.critical else c["wrong_answer"]
        return c[action]
    if view.kind is ViewKind.TARGET_REMOVAL:
        c = cfg["evidence_removed"]
        if action == "answer":   # `correct` here means: says the finding is absent
            return c["absent_answer"] if correct else c["answer"]
        return c[action]
    if view.kind is ViewKind.NATURAL_NEGATIVE:
        c = cfg["natural_negative"]
        if action == "answer":
            return c["correct_answer"] if correct else c["hallucinated_finding"]
        return c[action]
    c = cfg["degraded"]
    if action == "answer":
        return c["correct_answer"] if correct else c["wrong_answer"]
    return c[action]


def judge(view: View, answer: Optional[str], cfg: dict) -> tuple[bool, bool]:
    """(correct, claims_absent) for an answer on this view.

    On lesion-removed views the evidence is gone, so the correct answer is the one that says
    the finding is absent ("No" to "Is there a polyp?"), exactly as on natural negatives,
    whose dataset answer already says so. Both kinds look alike by design and are judged
    alike, so detecting the edit earns nothing."""
    absent = claims_absence(answer, view.question, view.answer) if view.kind is not ViewKind.NATURAL_NEGATIVE else False
    if view.kind is ViewKind.TARGET_REMOVAL:
        return absent, absent
    correct = answer_matches(answer, view.answer, view.answer_aliases,
                             rivals=set(cfg.get("answer_vocab", ())), question=view.question)
    if view.kind is ViewKind.NATURAL_NEGATIVE:
        return correct, correct
    return correct, absent


def rejudge(view: View, outcome: Outcome, answer: Optional[str], cfg: dict) -> Outcome:
    """Recompute correctness from the stored answer text under the current matching rules."""
    if outcome.action != "answer":
        return outcome
    correct, absent = judge(view, answer, cfg)
    return Outcome(**{**outcome.to_dict(), "correct": correct, "claims_absent": absent})


def rescore(view: View, outcome: Outcome, cfg: dict) -> Outcome:
    """Recompute an outcome's reward under the current cost matrix (the model's decision,
    correctness and grounding are kept as recorded), so changing the matrix never needs a rerun."""
    if outcome.malformed or outcome.action is None:
        parts = {"format": cfg["format"]["malformed"]}
    else:
        parts = dict(outcome.breakdown)
        parts["action"] = action_reward(view, outcome.action, outcome.correct, cfg)
        box_ok = outcome.box_ok
        if box_ok is None:   # rows written before box_ok was stored
            box_ok = "grounding" in parts or outcome.iou >= cfg["grounding"]["iou_threshold"]
        parts.pop("grounding", None)
        if (view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL) and outcome.action == "answer"
                and outcome.correct and box_ok):
            parts["grounding"] = cfg["grounding"]["bonus"]
    return Outcome(**{**outcome.to_dict(), "reward": sum(parts.values()), "breakdown": parts})


def score(
    view: View,
    final: Optional[FinalAction],
    cfg: dict,
    tool_calls: int = 0,
    refused_calls: int = 0,
    malformed: bool = False,
) -> Outcome:
    parts: dict[str, float] = {}

    if malformed or final is None:
        parts["format"] = cfg["format"]["malformed"]
        return Outcome(view.view_id, view.case_id, view.kind.value, None, None, 0.0, None,
                       tool_calls, True, sum(parts.values()), parts)

    correct: Optional[bool] = None
    absent: Optional[bool] = None
    overlap = 0.0
    if final.kind is ActionKind.ANSWER:
        correct, absent = judge(view, final.answer, cfg)
        overlap = iou(final.box, view.lesion_box)

    parts["action"] = action_reward(view, final.kind.value, correct, cfg)
    box_ok = None
    if final.kind is ActionKind.ANSWER:
        g = cfg["grounding"]
        box_ok = bool(overlap >= g["iou_threshold"] and box_area_fraction(final.box) <= g["max_box_area"])
        if view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL) and correct and box_ok:
            parts["grounding"] = g["bonus"]

    t = cfg["tools"]
    extra = max(0, tool_calls - t["free_calls"]) + refused_calls
    if extra:
        parts["tools"] = -t["per_extra_call"] * extra

    return Outcome(view.view_id, view.case_id, view.kind.value, final.kind.value, correct, overlap,
                   final.confidence, tool_calls, False, sum(parts.values()), parts, absent, box_ok)
