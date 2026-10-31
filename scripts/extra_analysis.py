"""Extra analyses for the paper, computed from stored results (no model is run).

  1. Decisions per view kind and the strict ESG (only explicit "not there" answers count; referring
     does not), next to the standard ESG.
  2. Trivial policies (always claim the finding, always say it is absent, always refer, always ask to
     clarify) scored like a model: what the metrics give a model that ignores the image.
  3. Cost-matrix sensitivity: net utility of every run when the penalty for a wrong answer or the
     reward for referring on lesion-free images changes.
  4. Tool use: calls per view kind, zoom vs window, and how often the first zoom covers the lesion
     (on erased views: the place where the lesion was).
  5. Lesion size: metrics by quartile of the lesion's area (share of the image).

Usage:
    python scripts/extra_analysis.py --results RESULTS --views TEST_VIEWS... --runs v2_medscope3_test ... --out extra.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.actions import FinalAction, absent_reply, asks_health, parse  # noqa: E402
from medscope.data.schema import ActionKind, View, ViewKind  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402
from medscope.eval.runner import load_views, read_jsonl, scored_rows  # noqa: E402
from medscope.rewards import Outcome, load_config, rescore, score, with_vocab  # noqa: E402

KINDS = ["original", "random_removal", "target_removal", "natural_negative", "degraded"]
MAIN = ["ccr", "esg", "target_hallucination_rate", "natural_hallucination_rate", "net_utility"]


def outcomes_of(run_dir: Path) -> list[Outcome]:
    return [Outcome(**{k: v for k, v in r.items() if k != "vkey"}) for r in scored_rows(run_dir)]


def fmt(x) -> str:
    return "n/a" if x is None or x != x else f"{x:.3f}"


# ---- 1. decisions per view kind, strict ESG ------------------------------------------------------

def strict_esg(outs: list[Outcome]) -> float:
    t = [o.action == "answer" and bool(o.claims_absent) for o in outs if o.kind == "target_removal"]
    r = [o.action == "answer" and bool(o.claims_absent) for o in outs if o.kind == "random_removal"]
    return float(np.mean(t) - np.mean(r)) if t and r else float("nan")


def decisions_table(runs: dict[str, list[Outcome]]) -> str:
    rows = ["| Run | View kind | Views | Answers: finding present | Answers: finding absent | Refer | Clarify | Malformed |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, outs in runs.items():
        for k in KINDS:
            xs = [o for o in outs if o.kind == k]
            if not xs:
                continue
            n = len(xs)
            present = sum(o.action == "answer" and not o.claims_absent for o in xs) / n
            absent = sum(o.action == "answer" and bool(o.claims_absent) for o in xs) / n
            if k == "natural_negative":   # judged by correctness: a correct answer there says "absent"
                present = sum(o.action == "answer" and not o.correct for o in xs) / n
                absent = sum(o.action == "answer" and bool(o.correct) for o in xs) / n
            rows.append(f"| {name} | {k} | {n} | {present:.3f} | {absent:.3f} | "
                        f"{sum(o.action == 'refer' for o in xs) / n:.3f} | {sum(o.action == 'clarify' for o in xs) / n:.3f} | "
                        f"{sum(o.malformed for o in xs) / n:.3f} |")
    return "\n".join(rows)


def esg_table(runs: dict[str, list[Outcome]]) -> str:
    rows = ["| Run | ESG (absent or refer) | Strict ESG (absent answers only) |", "| --- | --- | --- |"]
    for name, outs in runs.items():
        rows.append(f"| {name} | {fmt(METRICS['esg'](outs))} | {fmt(strict_esg(outs))} |")
    return "\n".join(rows)


# ---- 2. trivial policies ---------------------------------------------------------------------------

def present_answer(v: View) -> str:
    if v.kind is ViewKind.NATURAL_NEGATIVE:
        return "No" if asks_health(v.question) else "Yes"
    return v.answer


def absent_answer(v: View) -> str:
    if v.kind is ViewKind.NATURAL_NEGATIVE:
        return v.answer
    return absent_reply(v.question, v.answer) or "No abnormality"


def trivial_policies(views: list[View], cfg: dict) -> dict[str, list[Outcome]]:
    pol = {
        "always claims the finding": lambda v: FinalAction(ActionKind.ANSWER, answer=present_answer(v)),
        "always says it is absent": lambda v: FinalAction(ActionKind.ANSWER, answer=absent_answer(v)),
        "always refers": lambda v: FinalAction(ActionKind.REFER, text="."),
        "always asks to clarify": lambda v: FinalAction(ActionKind.CLARIFY, text="."),
    }
    return {name: [score(v, f(v), cfg) for v in views] for name, f in pol.items()}


def metric_table(runs: dict[str, list[Outcome]], metrics=MAIN) -> str:
    rows = ["| Run | " + " | ".join(metrics) + " |", "| --- | " + " | ".join("---" for _ in metrics) + " |"]
    for name, outs in runs.items():
        rows.append(f"| {name} | " + " | ".join(fmt(METRICS[m](outs)) for m in metrics) + " |")
    return "\n".join(rows)


# ---- 3. cost-matrix sensitivity --------------------------------------------------------------------

def cost_variants(cfg: dict) -> dict[str, dict]:
    def with_(**ch):
        c = json.loads(json.dumps(cfg))
        for path, val in ch.items():
            sect, key = path.split("__")
            c[sect][key] = val
        return c
    return {
        "as published": cfg,
        "wrong answer -1": with_(answerable__wrong_answer=-1.0, answerable__wrong_answer_critical=-2.0,
                                 evidence_removed__answer=-1.0, natural_negative__hallucinated_finding=-1.0,
                                 degraded__wrong_answer=-1.0),
        "wrong answer -0.5": with_(answerable__wrong_answer=-0.5, answerable__wrong_answer_critical=-1.0,
                                   evidence_removed__answer=-0.5, natural_negative__hallucinated_finding=-0.5,
                                   degraded__wrong_answer=-0.5),
        "refer on lesion-free 0": with_(evidence_removed__refer=0.0, natural_negative__refer=0.0),
        "refer -0.3 everywhere": with_(evidence_removed__refer=-0.3, natural_negative__refer=-0.3, degraded__refer=-0.3),
    }


def sensitivity_table(runs: dict[str, list[Outcome]], by_id: dict[str, View], cfg: dict) -> str:
    variants = cost_variants(cfg)
    rows = ["| Run | " + " | ".join(variants) + " |", "| --- | " + " | ".join("---" for _ in variants) + " |"]
    for name, outs in runs.items():
        vals = []
        for c in variants.values():
            vals.append(fmt(np.mean([rescore(by_id[o.view_id], o, c).reward for o in outs if o.view_id in by_id])))
        rows.append(f"| {name} | " + " | ".join(vals) + " |")
    return "\n".join(rows)


# ---- 4. tool use -----------------------------------------------------------------------------------

def contains_center(box, target) -> bool:
    if not box or not target:
        return False
    cx, cy = (target[0] + target[2]) / 2, (target[1] + target[3]) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def tool_table(results: Path, names: dict[str, str], by_id: dict[str, View]) -> str:
    rows = ["| Run | View kind | Views | Tool calls per view | Zoom share | Window share | First zoom covers the lesion (site) |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for run, label in names.items():
        trs = read_jsonl(results / run / "transcripts.jsonl")
        per = defaultdict(lambda: {"n": 0, "calls": 0, "zoom": 0, "window": 0, "first": 0, "covers": 0})
        for t in trs:
            v = by_id.get(t["view_id"])
            if v is None:
                continue
            st = per[v.kind.value]
            st["n"] += 1
            first = None
            for turn in t["turns"]:
                if turn["role"] != "assistant":
                    continue
                tool = parse(turn["content"]).tool
                if tool is None:
                    continue
                st["calls"] += 1
                if tool.name in ("zoom", "window"):
                    st[tool.name] += 1
                if tool.name == "zoom" and first is None:
                    first = tool.args.get("box")
            if first is not None and v.lesion_box:
                st["first"] += 1
                st["covers"] += contains_center(first, v.lesion_box)
        for k in KINDS:
            st = per.get(k)
            if not st or not st["n"]:
                continue
            calls = st["calls"] or 1
            cover = f"{st['covers'] / st['first']:.2f} ({st['first']} zooms)" if st["first"] else "n/a"
            rows.append(f"| {label} | {k} | {st['n']} | {st['calls'] / st['n']:.2f} | {st['zoom'] / calls:.2f} | "
                        f"{st['window'] / calls:.2f} | {cover} |")
    return "\n".join(rows)


# ---- 5. lesion size --------------------------------------------------------------------------------

def lesion_fraction(v: View) -> float:
    mask = (v.meta or {}).get("lesion_mask")
    if mask and Path(mask).exists():
        from PIL import Image
        m = np.asarray(Image.open(mask).convert("L")) > 0
        return float(m.mean())
    b = v.lesion_box
    return (b[2] - b[0]) * (b[3] - b[1]) / 1e6 if b else float("nan")


def size_table(runs: dict[str, list[Outcome]], views: list[View]) -> str:
    cf = {v.case_id: lesion_fraction(v) for v in views if v.kind is ViewKind.ORIGINAL}
    vals = np.array([x for x in cf.values() if x == x])
    if len(vals) < 8:
        return "(not enough lesion sizes)"
    edges = np.quantile(vals, [0, 0.25, 0.5, 0.75, 1.0])
    q_of = {c: int(min(3, np.searchsorted(edges[1:-1], f, side="right"))) for c, f in cf.items() if f == f}
    labels = [f"Q{i + 1} ({edges[i]:.1%}-{edges[i + 1]:.1%} of image)" for i in range(4)]
    rows = ["| Run | Lesion size | Cases | CCR | ESG | Claims erased lesion |", "| --- | --- | --- | --- | --- | --- |"]
    for name, outs in runs.items():
        for q in range(4):
            xs = [o for o in outs if q_of.get(o.case_id) == q]
            if not xs:
                continue
            rows.append(f"| {name} | {labels[q]} | {len({o.case_id for o in xs})} | {fmt(METRICS['ccr'](xs))} | "
                        f"{fmt(METRICS['esg'](xs))} | {fmt(METRICS['target_hallucination_rate'](xs))} |")
    return "\n".join(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="run directories (name=label to rename)")
    ap.add_argument("--tool-runs", nargs="*", default=None, help="runs for the tool-use table (default: --runs)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    results = Path(args.results)
    views = [v for f in args.views for v in load_views(f)]
    by_id = {v.view_id: v for v in views}
    cfg = with_vocab(load_config(), views)

    def label_map(items):
        out = {}
        for r in items:
            run, _, label = r.partition("=")
            if (results / run / "outcomes.jsonl").exists():
                out[run] = label or run
            else:
                print(f"skip {run}: no results")
        return out

    names = label_map(args.runs)
    runs = {label: [o for o in outcomes_of(results / run) if o.view_id in by_id] for run, label in names.items()}
    trivial = trivial_policies(views, cfg)

    sections = [
        ("Decisions per view kind", decisions_table(runs)),
        ("ESG and strict ESG (explicit 'not there' answers only)", esg_table({**runs, **trivial})),
        ("Trivial policies that ignore the image", metric_table(trivial)),
        ("Net utility under other cost matrices", sensitivity_table({**runs, **trivial}, by_id, cfg)),
        ("Tool use", tool_table(results, label_map(args.tool_runs) if args.tool_runs is not None else names, by_id)),
        ("By lesion size (quartiles of lesion area)", size_table(runs, views)),
    ]
    md = "\n\n".join(f"## {t}\n\n{body}" for t, body in sections)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
