"""Apply the three pre-registered selection rules of docs/PREREGISTRATION_v8.md to a set of runs (one per candidate).

R1  erased-lesion claims alone (lower is better)
R2  the same, among candidates with CCR on unedited lesions >= FLOOR
R3  ESG (higher is better), among the same candidates
Ties within 0.005 are broken by net utility, then by name.

    python scripts/v8_select.py --results RESULTS --runs NAME=run ... --out RESULTS/v8_selection.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402

FLOOR, TIE = 0.75, 0.005


def ccr_unedited(outs) -> float:
    xs = [o.action == "answer" and bool(o.correct) for o in outs if o.kind == "original"]
    return sum(xs) / len(xs) if xs else float("nan")


def rank(cands: list[dict], key: str, lower_is_better: bool) -> list[dict]:
    """Stable ranking with the pre-registered tie rule: values within TIE are ordered by net utility, then name."""
    sign = 1 if lower_is_better else -1
    ordered = sorted(cands, key=lambda c: (sign * c[key], -c["net_utility"], c["name"]))
    # group near-ties and reorder inside each group by utility then name
    out: list[dict] = []
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and abs(ordered[j + 1][key] - ordered[i][key]) < TIE:
            j += 1
        out += sorted(ordered[i:j + 1], key=lambda c: (-c["net_utility"], c["name"]))
        i = j + 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="NAME=run_dir_name")
    ap.add_argument("--floor", type=float, default=FLOOR)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    R = Path(args.results)
    cands = []
    for spec in args.runs:
        name, run = spec.split("=", 1)
        if not (R / run).exists():
            print(f"missing: {run}")
            continue
        outs = load_outcomes(R / run)
        cands.append({"name": name, "run": run, "erased": METRICS["target_hallucination_rate"](outs), "esg": METRICS["esg"](outs),
                      "ccr_unedited": ccr_unedited(outs), "net_utility": METRICS["net_utility"](outs)})
    eligible = [c for c in cands if c["ccr_unedited"] >= args.floor]
    r1, r2, r3 = rank(cands, "erased", True), rank(eligible, "erased", True), rank(eligible, "esg", False)
    out = ["# Pre-registered v8 selection rules (docs/PREREGISTRATION_v8.md)", "",
           f"{len(cands)} candidates; {len(eligible)} pass the sensitivity floor (CCR on unedited lesions >= {args.floor}).", "",
           "| Candidate | Erased claims | ESG | CCR unedited | Net utility | Floor |", "| --- | --- | --- | --- | --- | --- |"]
    for c in sorted(cands, key=lambda c: c["name"]):
        out.append(f"| {c['name']} | {c['erased']:.3f} | {c['esg']:.3f} | {c['ccr_unedited']:.3f} | {c['net_utility']:.3f} | {'yes' if c['ccr_unedited'] >= args.floor else 'no'} |")
    for label, ranking in (("R1: erased claims alone", r1), ("R2: erased claims, with floor", r2), ("R3: ESG, with floor", r3)):
        out += ["", f"**{label}** selects **{ranking[0]['name'] if ranking else '(none)'}**; order: " + " > ".join(c["name"] for c in ranking[:8])]
    if r2 and r3:
        same = r2[0]["name"] == r3[0]["name"]
        out += ["", "R2 and R3 select " + ("the **same** model: the confirmation test is uninformative for this candidate set." if same else
                 f"**different** models ({r2[0]['name']} vs {r3[0]['name']}): the confirmation half decides, by net utility of the selected model.")]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
