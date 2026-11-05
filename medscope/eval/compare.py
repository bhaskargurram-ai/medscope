"""Paired comparison of two runs on the same views: bootstrap over cases, or over patients.

Both runs are restricted to the cases they share, and each bootstrap sample draws the same cases
for both, so the difference reflects the models, not the sample. With `groups` (case id -> patient
or near-copy group), whole groups are resampled instead of cases, so several images of one patient
move together and the interval does not treat them as independent."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..rewards import Outcome
from .metrics import METRICS


def load_outcomes(run_dir: str | Path) -> list[Outcome]:
    from .runner import scored_rows
    return [Outcome(**{k: v for k, v in r.items() if k != "vkey"}) for r in scored_rows(run_dir)]


def paired_bootstrap(a: list[Outcome], b: list[Outcome], metric: str, n: int = 2000, seed: int = 0,
                     groups: dict[str, str] | None = None) -> dict:
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
    # the resampling unit: cases, or whole patient / near-copy groups of cases
    members: dict[str, list[str]] = defaultdict(list)
    for c in cases:
        members[(groups or {}).get(c, c)].append(c)
    units = sorted(members)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        pick = [c for u in (units[i] for i in rng.integers(0, len(units), len(units))) for c in members[u]]
        x, y = fn([o for c in pick for o in by_a[c]]), fn([o for c in pick for o in by_b[c]])
        if x is not None and y is not None and x == x and y == y:
            diffs.append(x - y)
    diffs = np.array(diffs)
    if da is None or db is None or len(diffs) == 0:
        return {"metric": metric, "n_cases": len(cases), "a": da, "b": db}
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"metric": metric, "n_cases": len(cases), "n_units": len(units), "a": da, "b": db, "diff": da - db,
            "ci_low": float(np.quantile(diffs, 0.025)), "ci_high": float(np.quantile(diffs, 0.975)),
            "p": float(min(1.0, p))}


def case_groups(views_files: list[str | Path]) -> dict[str, str]:
    """case id -> patient (or near-copy group) id, from the views files of a test set."""
    from .runner import load_views
    return {v.case_id: v.patient_id for f in views_files for v in load_views(f)}


def significance_table(results_dir: str | Path, ref: str, others: list[str],
                       metrics=("net_utility", "esg", "ccr", "target_hallucination_rate",
                                "natural_hallucination_rate"), groups: dict[str, str] | None = None) -> str:
    """Markdown: reference run vs each other run, difference with 95% CI and two-sided p.
    With `groups`, the bootstrap resamples patients (groups of cases) and the table says how many."""
    unit = "Patients" if groups else "Cases"
    rows = [f"| Compared with | Metric | Cases | {unit} | Reference | Other | Difference [95% CI] | p |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
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
            r = paired_bootstrap(a, b, m, groups=groups)
            if "diff" not in r:
                continue
            p = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
            rows.append(f"| {other} | {m} | {r['n_cases']} | {r['n_units']} | {r['a']:.3f} | {r['b']:.3f} | "
                        f"{r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {p} |")
    return "\n".join(rows)
