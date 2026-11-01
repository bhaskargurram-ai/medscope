"""Training-seed variability: metrics of each seed and their mean and standard deviation, for runs
grouped by arm (for example stage-1 SFT with and without counterfactual views).

Usage:
    python scripts/seed_summary.py --results RESULTS --arm "With CF=v2_sft_v2_test,v2_sft_v2_s1_test,v2_sft_v2_s2_test" \
        --arm "Without CF=v2_nocf_test,v2_nocf_s1_test,v2_nocf_s2_test" --out RESULTS/seeds_test.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402

METRIC_NAMES = [("ccr", "CCR"), ("esg", "ESG"), ("target_hallucination_rate", "Erased-lesion claims"),
                ("natural_hallucination_rate", "Healthy-image claims"), ("net_utility", "Net utility")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--arm", action="append", required=True, help='"label=run1,run2,..." (same seed order in every arm)')
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = Path(args.results)

    arms = []
    for a in args.arm:
        label, _, runs = a.partition("=")
        present = [r for r in runs.split(",") if (res / r / "outcomes.jsonl").exists()]
        arms.append((label, runs.split(","), {r: load_outcomes(res / r) for r in present}))

    lines = ["| Arm | Seeds | " + " | ".join(n for _, n in METRIC_NAMES) + " |",
             "| --- | --- | " + " | ".join("---" for _ in METRIC_NAMES) + " |"]
    for label, runs, outs in arms:
        for r in runs:
            if r in outs:
                lines.append(f"| {label} | {r} | " + " | ".join(f"{METRICS[m](outs[r]):.3f}" for m, _ in METRIC_NAMES) + " |")
        vals = {m: [METRICS[m](o) for o in outs.values()] for m, _ in METRIC_NAMES}
        if len(outs) > 1:
            lines.append(f"| **{label}** | **mean ± sd ({len(outs)} seeds)** | " +
                         " | ".join(f"**{np.mean(v):.3f} ± {np.std(v, ddof=1):.3f}**" for v in vals.values()) + " |")

    if len(arms) == 2:
        (la, ra, oa), (lb, rb, ob) = arms
        lines += ["", f"Paired difference {la} minus {lb}, seed by seed (same seed index):", "",
                  "| Seed pair | " + " | ".join(n for _, n in METRIC_NAMES) + " |",
                  "| --- | " + " | ".join("---" for _ in METRIC_NAMES) + " |"]
        for a, b in zip(ra, rb):
            if a in oa and b in ob:
                cells = []
                for m, _ in METRIC_NAMES:
                    d = paired_bootstrap(oa[a], ob[b], m)
                    p = "<0.001" if d["p"] < 0.001 else f"{d['p']:.3f}"
                    cells.append(f"{d['diff']:+.3f} (p {p})")
                lines.append(f"| {a} vs {b} | " + " | ".join(cells) + " |")

    md = "\n".join(lines)
    Path(args.out).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
