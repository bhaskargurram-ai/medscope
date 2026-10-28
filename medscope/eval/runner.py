"""Run a policy over benchmark views and write results that can be resumed."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..agent.episode import Policy, run_episode
from ..data.schema import View
from ..rewards import Outcome, with_vocab
from .metrics import bootstrap


def load_views(path: str | Path) -> list[View]:
    lines = Path(path).read_text().splitlines()
    return [View.from_dict(json.loads(line)) for line in lines if line.strip()]


def select_cases(views: list[View], limit_cases: Optional[int], seed: int = 0) -> list[View]:
    """Keep all views of a deterministic random subset of cases (all cases if limit is None)."""
    case_ids = sorted({v.case_id for v in views})
    if limit_cases is not None and limit_cases < len(case_ids):
        rng = np.random.default_rng(seed)
        case_ids = sorted(rng.choice(case_ids, size=limit_cases, replace=False).tolist())
    keep = set(case_ids)
    return [v for v in views if v.case_id in keep]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def evaluate(
    policy: Policy,
    views: list[View],
    cfg: dict,
    out_dir: str | Path,
    meta: dict,
    log: Callable[[str], None] = print,
    n_bootstrap: int = 2000,
) -> dict:
    """Greedy episodes on every view; appends to outcomes.jsonl so reruns resume."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    outcomes_path, transcripts_path = out / "outcomes.jsonl", out / "transcripts.jsonl"
    cfg = with_vocab(cfg, views)
    meta = {**meta, "scoring": SCORING_VERSION}

    # Each result row carries a key of the exact view (question, edits, degradation) and the
    # model's precision. Rows whose key no longer matches are set aside and redone, so a run
    # never mixes two setups; a pilot on a subset of cases carries over into the full run.
    keys = {v.view_id: view_key(v, meta.get("precision")) for v in views}
    rows, trows = _read_jsonl(outcomes_path), _read_jsonl(transcripts_path)
    stale = [r for r in rows if r["view_id"] in keys and r.get("vkey") != keys[r["view_id"]]]
    if stale:
        stale_ids = {r["view_id"] for r in stale}
        with open(out / "stale_outcomes.jsonl", "a") as f:
            for r in stale:
                f.write(json.dumps(r) + "\n")
        rows = [r for r in rows if r not in stale]
        trows = [t for t in trows if t["view_id"] not in stale_ids or t.get("vkey") == keys[t["view_id"]]]
        _write_jsonl(outcomes_path, rows)
        _write_jsonl(transcripts_path, trows)
        log(f"{len(stale)} earlier results used a different view or precision; set aside and redone")
    done = {r["view_id"] for r in rows if r["view_id"] in keys}
    todo = [v for v in views if v.view_id not in done]
    log(f"{len(done)} views already done, {len(todo)} to run")

    t0 = time.time()
    with open(outcomes_path, "a") as fo, open(transcripts_path, "a") as ft:
        for i, v in enumerate(todo):
            ep = run_episode(policy, v, cfg, sample=False)
            fo.write(json.dumps({**ep.outcome.to_dict(), "vkey": keys[v.view_id]}) + "\n")
            ft.write(json.dumps({"view_id": v.view_id, "vkey": keys[v.view_id], "kind": v.kind.value,
                                 "question": v.question, "gold": v.answer, "error": ep.error,
                                 "turns": ep.transcript()}) + "\n")
            fo.flush(), ft.flush()
            if (i + 1) % 20 == 0:
                rate = (time.time() - t0) / (i + 1)
                log(f"  {i + 1}/{len(todo)} views, {rate:.1f}s each, ~{rate * (len(todo) - i - 1) / 60:.0f} min left")

    outcomes = [Outcome(**{k: v for k, v in r.items() if k != "vkey"})
                for r in _read_jsonl(outcomes_path) if r["view_id"] in keys]
    summary = {"meta": meta, "n_views": len(outcomes), "n_cases": len({o.case_id for o in outcomes}),
               "metrics": bootstrap(outcomes, n_resamples=n_bootstrap)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    report = make_report(summary, outcomes, [t for t in _read_jsonl(transcripts_path) if t["view_id"] in keys])
    (out / "report.md").write_text(report)
    return summary


SCORING_VERSION = 3  # bump when parsing or answer matching changes, so old results are redone


def view_key(view: View, precision=None) -> str:
    """Fingerprint of everything that defines a view's result: the view, model precision, scoring rules."""
    payload = json.dumps(view.to_dict(), sort_keys=True) + f"|precision={precision}|scoring={SCORING_VERSION}"
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.replace(path)


HEADLINE = [
    ("ccr", "Covered-and-correct rate (higher is better)"),
    ("selective_accuracy", "Accuracy when answering"),
    ("coverage", "Coverage on answerable views"),
    ("asg", "Abstention specificity gap (higher is better)"),
    ("refer_rate_target_removal", "Refers when lesion removed"),
    ("refer_rate_random_removal", "Refers after random edit (lower is better)"),
    ("grounded_accuracy", "Grounded accuracy (IoU >= 0.3)"),
    ("clarify_rate_degraded", "Asks to clarify on degraded input"),
    ("net_utility", "Net clinical utility (mean reward)"),
    ("aurc", "AURC (lower is better)"),
    ("tool_calls_per_correct", "Tool calls per correct answer"),
    ("malformed_rate", "Malformed output rate"),
    ("natural_hallucination_rate", "Natural negatives: claims the absent finding (lower is better)"),
    ("natural_correct_rate", "Natural negatives: correctly says it isn't there"),
    ("natural_refer_rate", "Natural negatives: refers"),
]
KINDS = ("original", "random_removal", "target_removal", "degraded", "natural_negative")


def _fmt(m: dict) -> str:
    v = m["value"]
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if m.get("ci_low") is None:
        return f"{v:.3f}"
    return f"{v:.3f} [{m['ci_low']:.3f}, {m['ci_high']:.3f}]"


def make_report(summary: dict, outcomes: list[Outcome], transcripts: list[dict], n_examples: int = 3) -> str:
    meta = summary["meta"]
    lines = [f"# MedScope run: {meta.get('name', '?')}", ""]
    lines += [f"- {k}: {v}" for k, v in meta.items()]
    lines += [f"- views: {summary['n_views']}, cases: {summary['n_cases']}", "",
              "## Metrics (95% CI, bootstrap over cases)", "", "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {label} | {_fmt(summary['metrics'][k])} |" for k, label in HEADLINE]

    lines += ["", "## Actions taken per view kind", "", "| View kind | answer | clarify | refer | malformed | correct answers |",
              "| --- | --- | --- | --- | --- | --- |"]
    by_kind = defaultdict(list)
    for o in outcomes:
        by_kind[o.kind].append(o)
    for kind in KINDS:
        os_ = by_kind.get(kind, [])
        c = Counter(o.action or "malformed" for o in os_)
        correct = sum(1 for o in os_ if o.correct)
        lines.append(f"| {kind} | {c['answer']} | {c['clarify']} | {c['refer']} | {c['malformed']} | {correct} |")

    errors = Counter(t["error"] for t in transcripts if t.get("error"))
    if errors:
        lines += ["", "## Malformed output reasons", ""] + [f"- {e}: {n}" for e, n in errors.most_common(8)]

    by_id = {o.view_id: o for o in outcomes}
    lines += ["", "## Example failures (first few per view kind)", ""]
    for kind in KINDS:
        bad = [t for t in transcripts if t["kind"] == kind and t["view_id"] in by_id and by_id[t["view_id"]].reward <= 0]
        for t in bad[:n_examples]:
            lines.append(f"### {kind}: {t['question']} (gold: {t['gold']})")
            for turn in t["turns"]:
                if turn["role"] == "assistant":
                    c = turn["content"]
                    shown = c if len(c) <= 700 else f"{c[:250]} [...] {c[-400:]}"
                    lines.append(f"- assistant: {shown}")
            if t.get("error"):
                lines.append(f"- (scored as malformed: {t['error']})")
            lines.append("")
    return "\n".join(lines)


def compare_runs(results_dir: str | Path) -> str:
    """Markdown leaderboard across every run folder that has a summary.json."""
    rows = []
    for p in sorted(Path(results_dir).glob("*/summary.json")):
        s = json.loads(p.read_text())
        rows.append((s["meta"].get("name", p.parent.name), s))
    keys = ["ccr", "selective_accuracy", "asg", "grounded_accuracy", "clarify_rate_degraded",
            "natural_hallucination_rate", "net_utility", "malformed_rate"]
    lines = ["| Run | Split | Cases | " + " | ".join(keys) + " |", "| --- | --- | --- | " + " | ".join("---" for _ in keys) + " |"]
    def order(r):
        s = r[1]
        return (s["meta"].get("split", ""), -(s["metrics"]["net_utility"]["value"] or -99))
    for name, s in sorted(rows, key=order):
        vals = [_fmt(s["metrics"].get(k, {"value": None})) for k in keys]  # older runs lack newer metrics
        lines.append(f"| {name} | {s['meta'].get('split', '?')} | {s['n_cases']} | " + " | ".join(vals) + " |")
    return "\n".join(lines)
