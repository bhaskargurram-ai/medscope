"""Erased-lesion claims split by how clean the erasure looks to an independent frontier rater.

A frontier model's probability that each lesion-erased image was edited (scripts/edit_guess.py) splits the
erased views into rated-unedited (probability <= --low) and rated-edited (>= --high). If a model's "absent"
answers came from visible edit traces, it would claim the lesion far more often on clean-looking erasures.

    python scripts/clean_split.py --scores RESULTS/edit_guess_gemini/scores.jsonl --results RESULTS \
        --runs v4_final_test=MedScope-4B v2_gpt6astra_test=gpt-6-astra ... --out RESULTS/clean_split.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes  # noqa: E402
from medscope.eval.runner import read_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="run=label")
    ap.add_argument("--low", type=float, default=0.2)
    ap.add_argument("--high", type=float, default=0.75)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    probs = {r["view_id"]: r["prob"] for r in read_jsonl(Path(args.scores))
             if r["kind"] == "target_removal" and r["prob"] is not None}
    scale = 100.0 if probs and max(probs.values()) > 1 else 1.0
    clean = {v for v, p in probs.items() if p / scale <= args.low}
    edited = {v for v, p in probs.items() if p / scale >= args.high}
    lines = [f"Lesion-erased views rated unedited (<= {args.low:.2f}): {len(clean)}; rated edited (>= {args.high:.2f}): "
             f"{len(edited)}; in between: {len(probs) - len(clean) - len(edited)}.", "",
             "| Model | Claims the erased lesion: rated unedited | rated edited |", "| --- | --- | --- |"]
    for spec in args.runs:
        run, _, label = spec.partition("=")
        p = Path(args.results) / run
        if not (p / "outcomes.jsonl").exists():
            continue
        outs = {o.view_id: o for o in load_outcomes(p) if o.kind == "target_removal"}

        def rate(ids):
            xs = [outs[v] for v in ids if v in outs]
            claims = [o.action == "answer" and not o.correct for o in xs]
            return f"{sum(claims) / len(xs):.0%} (n={len(xs)})" if xs else "n/a"
        lines.append(f"| {label or run} | {rate(clean)} | {rate(edited)} |")
    md = "\n".join(lines)
    Path(args.out).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
