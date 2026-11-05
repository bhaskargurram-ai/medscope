"""Patient-level uncertainty: the paired comparisons again, resampling patients (or near-copy groups) instead of cases.

A case is one source image with all its views. Several cases can come from one patient (NIH chest X-ray patients,
TCGA-LGG and BraTS volumes, BUS-UCLM patients) or one near-copy group (colonoscopy, SLAKE), and a bootstrap over cases
treats them as independent. This script reruns the comparisons of the paper with whole patients resampled and prints
both results side by side, with the number of cases and of patients per test set, so a reader can see what the
dependence costs. Nothing else changes: same runs, same metrics, same 2,000 resamples.

    python scripts/cluster_bootstrap.py --results RESULTS --set "Main test=v4_final_test:v2_gemini_test,v2_claudeopus_test:VIEWS..." ... --out report.md

Each --set is NAME=REF:OTHER1,OTHER2,...:VIEWS_FILE [VIEWS_FILE ...] (the views files give the patient ids).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import case_groups, load_outcomes, paired_bootstrap  # noqa: E402

METRICS = ("esg", "target_hallucination_rate", "net_utility", "ccr", "natural_hallucination_rate")


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--set", action="append", required=True, metavar="NAME=REF:OTHERS:VIEWS")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = ["# Patient-level bootstrap", "",
           "Same runs and metrics as the paper; 95% CI and two-sided p from 2,000 paired resamples of cases (as published) "
           "and of patients or near-copy groups (every case of a patient drawn together). A wider patient-level interval "
           "means the cases of that set are not independent; a conclusion that changes between the two is flagged.", ""]
    flips = 0
    for spec in args.set:
        name, rest = spec.split("=", 1)
        ref, others, views = rest.split(":", 2)
        groups = case_groups(views.split())
        a = load_outcomes(Path(args.results) / ref)
        cases = {o.case_id for o in a}
        n_pat = len({groups.get(c, c) for c in cases})
        sizes = Counter(groups.get(c, c) for c in cases)
        out += [f"## {name}", "", f"{len(cases)} cases from {n_pat} patients or groups; largest group {max(sizes.values())} cases, "
                f"{sum(1 for v in sizes.values() if v > 1)} groups with more than one case.", "",
                "| Compared with | Metric | Difference | Case-level 95% CI | p | Patient-level 95% CI | p | |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for other in others.split(","):
            rb = Path(args.results) / other
            if not (rb / "outcomes.jsonl").exists():
                out.append(f"| {other} | (no results) | | | | | | |")
                continue
            b = load_outcomes(rb)
            for m in METRICS:
                rc = paired_bootstrap(a, b, m)
                rp = paired_bootstrap(a, b, m, groups=groups)
                if "diff" not in rc or "diff" not in rp:
                    continue
                flag = ""
                if (rc["p"] < 0.05) != (rp["p"] < 0.05):
                    flag, flips = "significance changes", flips + 1
                out.append(f"| {other} | {m} | {rc['diff']:+.3f} | [{rc['ci_low']:+.3f}, {rc['ci_high']:+.3f}] | {fmt_p(rc['p'])} | "
                           f"[{rp['ci_low']:+.3f}, {rp['ci_high']:+.3f}] | {fmt_p(rp['p'])} | {flag} |")
        out.append("")
    out.append(f"Comparisons whose significance at 0.05 changes with patient-level resampling: {flips}.")
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
