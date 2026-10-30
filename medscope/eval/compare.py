"""Paired comparison of two runs on the same views: bootstrap over cases.

Both runs are restricted to the cases they share, and each bootstrap sample draws the same cases
for both, so the difference reflects the models, not the sample."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..rewards import Outcome
from .metrics import METRICS


def load_outcomes(run_dir: str | Path) -> list[Outcome]:
    from .runner import read_jsonl
    return [Outcome(**{k: v for k, v in r.items() if k != "vkey"}) for r in read_jsonl(Path(run_dir) / "outcomes.jsonl")]


def paired_bootstrap(a: list[Outcome], b: list[Outcome], metric: str, n: int = 2000, seed: int = 0) -> dict:
    fn = METRICS[metric]
    by_a, by_b = defaultdict(list), defaultdict(list)
    for o in a:
        by_a[o.case_id].append(o)
    for o in b:
        by_b[o.case_id].append(o)
    cases = sorted(set(by_a) & set(by_b))
    if not cases:
        return {"metric": metric, "n_cases": 0}
    da, db = fn([o for c in cases for o in by_a[c]]), fn([o for c in cases for o in by_b[c]])
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        pick = [cases[i] for i in rng.integers(0, len(cases), len(cases))]
        x, y = fn([o for c in pick for o in by_a[c]]), fn([o for c in pick for o in by_b[c]])
        if x is not None and y is not None and x == x and y == y:
            diffs.append(x - y)
    diffs = np.array(diffs)
    if da is None or db is None or len(diffs) == 0:
        return {"metric": metric, "n_cases": len(cases), "a": da, "b": db}
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"metric": metric, "n_cases": len(cases), "a": da, "b": db, "diff": da - db,
            "ci_low": float(np.quantile(diffs, 0.025)), "ci_high": float(np.quantile(diffs, 0.975)),
            "p": float(min(1.0, p))}


def significance_table(results_dir: str | Path, ref: str, others: list[str],
                       metrics=("net_utility", "esg", "ccr", "target_hallucination_rate",
                                "natural_hallucination_rate")) -> str:
    """Markdown: reference run vs each other run, difference with 95% CI and two-sided p."""
    rows = ["| Compared with | Metric | Cases | Reference | Other | Difference [95% CI] | p |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    ra = Path(results_dir) / ref
    if not (ra / "outcomes.jsonl").exists():
        return f"(no results for {ref})"
    a = load_outcomes(ra)
    for other in others:
        rb = Path(results_dir) / other
        if not (rb / "outcomes.jsonl").exists():
            continue
        b = load_outcomes(rb)
        for m in metrics:
            r = paired_bootstrap(a, b, m)
            if "diff" not in r:
                continue
            p = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
            rows.append(f"| {other} | {m} | {r['n_cases']} | {r['a']:.3f} | {r['b']:.3f} | "
                        f"{r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {p} |")
    return "\n".join(rows)
