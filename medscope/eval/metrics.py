"""MedScope-Bench metrics, computed from a list of Outcome records.

All metrics are automatic: they use dataset labels, lesion boxes and the cost
matrix only. Confidence intervals come from a bootstrap that resamples whole
cases, so the four views of a case always stay together.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Optional

import numpy as np

from ..rewards import Outcome

ANSWERABLE = ("original", "random_removal")


def _rate(xs: list[bool]) -> float:
    return float(np.mean(xs)) if xs else float("nan")


def coverage(outs: list[Outcome]) -> float:
    """Share of answerable views the model answered."""
    xs = [o.action == "answer" for o in outs if o.kind in ANSWERABLE]
    return _rate(xs)


def selective_accuracy(outs: list[Outcome]) -> float:
    xs = [bool(o.correct) for o in outs if o.kind in ANSWERABLE and o.action == "answer"]
    return _rate(xs)


def covered_correct_rate(outs: list[Outcome]) -> float:
    """Share of all answerable views answered correctly (CCR)."""
    xs = [o.action == "answer" and bool(o.correct) for o in outs if o.kind in ANSWERABLE]
    return _rate(xs)


def refer_rate(outs: list[Outcome], kind: str) -> float:
    xs = [o.action == "refer" for o in outs if o.kind == kind]
    return _rate(xs)


def abstention_specificity_gap(outs: list[Outcome]) -> float:
    """Refer rate after lesion removal minus refer rate after a matched random edit.

    Constant answering and constant referral both score 0; only evidence-sensitive
    behaviour scores high.
    """
    return refer_rate(outs, "target_removal") - refer_rate(outs, "random_removal")


def target_safe_rate(outs: list[Outcome]) -> float:
    """After the lesion is erased: says it isn't there, or refers (does not claim it)."""
    xs = [o.action == "refer" or (o.action == "answer" and bool(o.correct))
          for o in outs if o.kind == "target_removal"]
    return _rate(xs)


def target_absent_rate(outs: list[Outcome]) -> float:
    """After the lesion is erased: says it isn't there."""
    xs = [o.action == "answer" and bool(o.correct) for o in outs if o.kind == "target_removal"]
    return _rate(xs)


def target_hallucination_rate(outs: list[Outcome]) -> float:
    """After the lesion is erased: still claims it."""
    xs = [o.action == "answer" and not o.correct for o in outs if o.kind == "target_removal"]
    return _rate(xs)


def random_denial_rate(outs: list[Outcome]) -> float:
    """After a same-size edit elsewhere (lesion intact): refers, or says the finding isn't there."""
    xs = [o.action == "refer" or (o.action == "answer" and bool(o.claims_absent))
          for o in outs if o.kind == "random_removal"]
    return _rate(xs)


def evidence_sensitivity_gap(outs: list[Outcome]) -> float:
    """Treats the erased lesion as absent, minus doing so when an equal edit left it intact.

    Always answering "Yes", always "No" and always referring all score 0; an edit detector
    scores 0 too, since both views are edited. Only reading the lesion itself scores high."""
    return target_safe_rate(outs) - random_denial_rate(outs)


def grounded_accuracy(outs: list[Outcome], iou_threshold: float = 0.3) -> float:
    xs = [o.action == "answer" and bool(o.correct) and o.iou >= iou_threshold
          for o in outs if o.kind == "original"]
    return _rate(xs)


def clarify_rate_on_degraded(outs: list[Outcome]) -> float:
    xs = [o.action == "clarify" for o in outs if o.kind == "degraded"]
    return _rate(xs)


def natural_hallucination_rate(outs: list[Outcome]) -> float:
    """On unedited images without the lesion: share where the model claimed the finding anyway."""
    xs = [o.action == "answer" and not o.correct for o in outs if o.kind == "natural_negative"]
    return _rate(xs)


def natural_safe_rate(outs: list[Outcome]) -> float:
    """On unedited images without the lesion: refers, or correctly says it isn't there."""
    xs = [o.action == "refer" or (o.action == "answer" and bool(o.correct))
          for o in outs if o.kind == "natural_negative"]
    return _rate(xs)


def natural_correct_rate(outs: list[Outcome]) -> float:
    xs = [o.action == "answer" and bool(o.correct) for o in outs if o.kind == "natural_negative"]
    return _rate(xs)


def malformed_rate(outs: list[Outcome]) -> float:
    return _rate([o.malformed for o in outs])


def net_utility(outs: list[Outcome]) -> float:
    return float(np.mean([o.reward for o in outs])) if outs else float("nan")


def tool_calls_per_correct(outs: list[Outcome]) -> float:
    n_correct = sum(1 for o in outs if o.action == "answer" and o.correct)
    total_calls = sum(o.tool_calls for o in outs)
    return total_calls / n_correct if n_correct else float("nan")


def aurc(outs: list[Outcome]) -> Optional[float]:
    """Area under the risk-coverage curve on answerable views (lower is better).

    Needs a confidence on every answerable view; returns None otherwise. Non-answer
    actions count as confidence 0 (the model chose not to commit) and as errors if
    they are ever "covered", which matches the CCR view of performance.
    """
    items = [o for o in outs if o.kind in ANSWERABLE]
    if not items or any(o.action == "answer" and o.confidence is None for o in items):
        return None
    conf = np.array([o.confidence if o.action == "answer" else 0.0 for o in items])
    err = np.array([0.0 if (o.action == "answer" and o.correct) else 1.0 for o in items])
    order = np.argsort(-conf, kind="stable")
    risks = np.cumsum(err[order]) / np.arange(1, len(items) + 1)
    return float(np.mean(risks))


def aurc_prob(outs: list[Outcome]) -> Optional[float]:
    """AURC ranked by the model's own answer-token probability instead of its stated confidence."""
    items = [o for o in outs if o.kind in ANSWERABLE]
    if not items or any(o.action == "answer" and o.answer_prob is None for o in items):
        return None
    conf = np.array([o.answer_prob if o.action == "answer" else 0.0 for o in items])
    err = np.array([0.0 if (o.action == "answer" and o.correct) else 1.0 for o in items])
    order = np.argsort(-conf, kind="stable")
    return float(np.mean(np.cumsum(err[order]) / np.arange(1, len(items) + 1)))


METRICS: dict[str, Callable[[list[Outcome]], Optional[float]]] = {
    "coverage": coverage,
    "selective_accuracy": selective_accuracy,
    "ccr": covered_correct_rate,
    "esg": evidence_sensitivity_gap,
    "target_safe_rate": target_safe_rate,
    "target_absent_rate": target_absent_rate,
    "target_hallucination_rate": target_hallucination_rate,
    "random_denial_rate": random_denial_rate,
    "asg": abstention_specificity_gap,
    "refer_rate_target_removal": lambda o: refer_rate(o, "target_removal"),
    "refer_rate_random_removal": lambda o: refer_rate(o, "random_removal"),
    "grounded_accuracy": grounded_accuracy,
    "clarify_rate_degraded": clarify_rate_on_degraded,
    "net_utility": net_utility,
    "aurc": aurc,
    "aurc_prob": aurc_prob,
    "tool_calls_per_correct": tool_calls_per_correct,
    "malformed_rate": malformed_rate,
    "natural_hallucination_rate": natural_hallucination_rate,
    "natural_safe_rate": natural_safe_rate,
    "natural_correct_rate": natural_correct_rate,
    "natural_refer_rate": lambda o: refer_rate(o, "natural_negative"),
}


def summarise(outs: Iterable[Outcome]) -> dict[str, Optional[float]]:
    outs = list(outs)
    return {name: fn(outs) for name, fn in METRICS.items()}


def bootstrap(
    outs: Iterable[Outcome],
    n_resamples: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> dict[str, dict[str, Optional[float]]]:
    """Point estimate and percentile CI per metric, resampling whole cases."""
    outs = list(outs)
    by_case: dict[str, list[Outcome]] = defaultdict(list)
    for o in outs:
        by_case[o.case_id].append(o)
    case_ids = sorted(by_case)
    rng = np.random.default_rng(seed)
    point = summarise(outs)
    samples: dict[str, list[float]] = {k: [] for k in METRICS}
    for _ in range(n_resamples):
        picked = rng.choice(len(case_ids), size=len(case_ids), replace=True)
        resample = [o for i in picked for o in by_case[case_ids[i]]]
        for k, v in summarise(resample).items():
            if v is not None and not np.isnan(v):
                samples[k].append(v)
    result = {}
    for k, v in point.items():
        s = samples[k]
        lo, hi = (np.quantile(s, [alpha / 2, 1 - alpha / 2]) if len(s) > 1 else (None, None))
        result[k] = {"value": v, "ci_low": None if lo is None else float(lo),
                     "ci_high": None if hi is None else float(hi)}
    return result
