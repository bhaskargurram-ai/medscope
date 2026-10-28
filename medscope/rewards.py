"""Cost-matrix reward for RL, also used as the benchmark's net-utility metric."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from .actions import FinalAction, answer_matches
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

    def to_dict(self) -> dict:
        return asdict(self)


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
    overlap = 0.0
    if final.kind is ActionKind.ANSWER:
        correct = answer_matches(final.answer, view.answer, view.answer_aliases,
                                 rivals=set(cfg.get("answer_vocab", ())))
        overlap = iou(final.box, view.lesion_box)

    if view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL):
        c = cfg["answerable"]
        if final.kind is ActionKind.ANSWER:
            if correct:
                parts["action"] = c["correct_answer"]
                g = cfg["grounding"]
                if overlap >= g["iou_threshold"] and box_area_fraction(final.box) <= g["max_box_area"]:
                    parts["grounding"] = g["bonus"]
            else:
                parts["action"] = c["wrong_answer_critical"] if view.critical else c["wrong_answer"]
        else:
            parts["action"] = c[final.kind.value]
    elif view.kind is ViewKind.TARGET_REMOVAL:
        parts["action"] = cfg["evidence_removed"][final.kind.value]
    elif view.kind is ViewKind.NATURAL_NEGATIVE:
        c = cfg["natural_negative"]
        if final.kind is ActionKind.ANSWER:
            parts["action"] = c["correct_answer"] if correct else c["hallucinated_finding"]
        else:
            parts["action"] = c[final.kind.value]
    else:  # degraded
        c = cfg["degraded"]
        if final.kind is ActionKind.ANSWER:
            parts["action"] = c["correct_answer"] if correct else c["wrong_answer"]
        else:
            parts["action"] = c[final.kind.value]

    t = cfg["tools"]
    extra = max(0, tool_calls - t["free_calls"]) + refused_calls
    if extra:
        parts["tools"] = -t["per_extra_call"] * extra

    return Outcome(view.view_id, view.case_id, view.kind.value, final.kind.value, correct, overlap,
                   final.confidence, tool_calls, False, sum(parts.values()), parts)
