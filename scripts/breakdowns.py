"""Two breakdowns a reviewer asks for, from stored results:

1. Net utility without the degraded views (MedScope was trained on degradations, so part of its net-utility gap
   could be an in-distribution "ask to clarify" skill): every run, and the reference minus each other run.
2. Asking to clarify on degraded input, by degradation type (blur, noise, low resolution, wrong image).

    python scripts/breakdowns.py --results RESULTS --views TEST_VIEWS... --ref v4_final_test \
        --runs v4_final_test=MedScope v2_gemini_test=gemini-4-argon ... --out RESULTS/breakdowns_test.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True, help="views files (for the degradation of each view)")
    ap.add_argument("--runs", nargs="+", required=True, help="run=label")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    degradation = {v.view_id: (v.meta or {}).get("degradation", "?") for f in args.views for v in load_views(f)
                   if v.kind.value == "degraded"}
    runs = []
    for spec in args.runs:
        run, _, label = spec.partition("=")
        if (Path(args.results) / run / "outcomes.jsonl").exists():
            runs.append((run, label or run, load_outcomes(Path(args.results) / run)))
    ref = next((o for r, _, o in runs if r == args.ref), None)

    def no_deg(outs):
        return [o for o in outs if o.kind != "degraded"]

    lines = ["Net utility with and without the degraded views:", "",
             "| Model | All views | Without degraded | Reference minus model, without degraded (p) |",
             "| --- | --- | --- | --- |"]
    for run, label, outs in runs:
        cell = ""
        if ref is not None and run != args.ref:
            d = paired_bootstrap(no_deg(ref), no_deg(outs), "net_utility")
            if "diff" in d:
                p = "<0.001" if d["p"] < 0.001 else f"{d['p']:.3f}"
                cell = f"{d['diff']:+.3f} ({p})"
        lines.append(f"| {label} | {METRICS['net_utility'](outs):.3f} | {METRICS['net_utility'](no_deg(outs)):.3f} | {cell} |")

    kinds = sorted(set(degradation.values()))
    lines += ["", "Asks to clarify on degraded input, by degradation:", "",
              "| Model | " + " | ".join(f"{k} (n)" for k in kinds) + " |", "| --- | " + " | ".join("---" for _ in kinds) + " |"]
    for run, label, outs in runs:
        by = defaultdict(list)
        for o in outs:
            if o.kind == "degraded":
                by[degradation.get(o.view_id, "?")].append(o.action == "clarify")
        lines.append(f"| {label} | " + " | ".join(f"{sum(by[k]) / len(by[k]):.0%} ({len(by[k])})" if by[k] else "n/a"
                                                 for k in kinds) + " |")
    md = "\n".join(lines)
    Path(args.out).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
