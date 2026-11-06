"""The two pre-registered comparisons of docs/PREREGISTRATION_v5.md, evaluated exactly as written.

C1  matched control (v4q_ctrl_s0) vs unmatched control (v4q_unm_s0): random-removal denial rate on the fresh
    external set and on the pooled held-out-tool sets (Telea + diffusion edits of the main test), with the
    erased-claim and CCR constraints; decision rule applied and printed.
C2  recipe (v4q_cf_s0) vs removal-based DPO (v4q_dpo_s0): ESG and net utility on the fresh external set (decisive),
    the held-out tools and the main test; secondary endpoints alongside.

Every difference is printed next to twice the stage-1 seed-to-seed standard deviation of the recipe (from
v4q_cf_s0/s1/s2 on the main test), as the plan requires.

    python scripts/v5_confirm.py --results RESULTS --out RESULTS/v5_confirmation.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402

MIN_DENIAL, MAX_CLAIMS_WORSE, MAX_CCR_WORSE, MIN_ESG, MIN_UTILITY = 0.05, 0.05, 0.03, 0.05, 0.05
LABEL = {"random_denial_rate": "Random-removal denial", "target_hallucination_rate": "Erased-lesion claims",
         "ccr": "CCR", "esg": "ESG", "net_utility": "Net utility"}


def pooled(results: Path, runs: list[str]):
    outs = []
    for r in runs:
        d = results / r
        if d.exists():
            outs += load_outcomes(d)
    return outs


def row(a, b, metric: str, seed_sd: dict) -> tuple[str, dict]:
    r = paired_bootstrap(a, b, metric)
    if "diff" not in r:
        return f"| {LABEL[metric]} | (no results) | | | | |", r
    sd2 = 2 * seed_sd.get(metric, float("nan"))
    noise = "within seed noise" if abs(r["diff"]) < sd2 else "beyond seed noise"
    p = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
    return (f"| {LABEL[metric]} | {r['n_cases']} | {r['a']:.3f} | {r['b']:.3f} | {r['diff']:+.3f} "
            f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {p} | 2 sd = {sd2:.3f}, {noise} |"), r


def seed_sds(results: Path) -> dict:
    vals: dict[str, list[float]] = {}
    for s in range(3):
        f = results / f"v4q_cf_s{s}_test" / "summary.json"
        if f.exists():
            m = json.loads(f.read_text())["metrics"]
            for k in LABEL:
                if m.get(k, {}).get("value") is not None:
                    vals.setdefault(k, []).append(m[k]["value"])
    return {k: float(np.std(v, ddof=1)) if len(v) > 1 else float("nan") for k, v in vals.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    R = Path(args.results)
    sd = seed_sds(R)
    head = ["| Endpoint | Cases | A | B | A − B [95% CI] | p | Seed noise |", "| --- | --- | --- | --- | --- | --- | --- |"]
    out = ["# Pre-registered v5 confirmation (docs/PREREGISTRATION_v5.md)", "",
           "Seed noise: twice the standard deviation of the recipe's three stage-1 seeds on the main test "
           f"({', '.join(f'{LABEL[k]} {v:.3f}' for k, v in sd.items())}).", ""]

    # C1
    out += ["## C1. Matched control (A) vs unmatched control (B)", ""]
    sets = {"Fresh external": (["v4q_ctrl_s0_ext2"], ["v4q_unm_s0_ext2"]),
            "Held-out tools, pooled (Telea + diffusion edits of the main test)":
                (["v4q_inp_telea_ctrl_s0_test", "v4q_inp_diffusion_ctrl_s0_test"],
                 ["v4q_inp_telea_unm_s0_test", "v4q_inp_diffusion_unm_s0_test"]),
            "Main test (supporting only)": (["v4q_ctrl_s0_test"], ["v4q_unm_s0_test"])}
    verdicts = []
    for name, (ra, rb) in sets.items():
        a, b = pooled(R, ra), pooled(R, rb)
        out += [f"**{name}**", ""] + head
        res = {}
        for m in ("random_denial_rate", "target_hallucination_rate", "ccr", "esg", "net_utility"):
            line, res[m] = row(a, b, m, sd)
            out.append(line)
        out.append("")
        if name != "Main test (supporting only)" and "diff" in res["random_denial_rate"]:
            d = res["random_denial_rate"]
            matters = d["diff"] <= -MIN_DENIAL and d["ci_high"] < 0
            claims_ok = res["target_hallucination_rate"].get("diff", 0) <= MAX_CLAIMS_WORSE
            ccr_ok = res["ccr"].get("diff", 0) >= -MAX_CCR_WORSE
            within = abs(d["diff"]) < MIN_DENIAL and claims_ok and ccr_ok
            verdicts.append((name, matters and claims_ok and ccr_ok, within))
    if verdicts:
        if all(v[1] for v in verdicts):
            verdict = "**Matching matters**: the matched control lowers denial by at least 5 points with the interval excluding zero on both sets, within the claim and CCR constraints."
        elif all(v[2] for v in verdicts):
            verdict = "**Matching not demonstrated**: the unmatched arm is within the pre-specified margins on both sets; the benefit belongs to control edits in general."
        else:
            verdict = "**Inconclusive** under the pre-specified rule (" + "; ".join(f"{n}: {'matters' if m else 'within margins' if w else 'neither'}" for n, m, w in verdicts) + ")."
        out += ["Decision (rule fixed in advance): " + verdict, ""]

    # C2
    out += ["## C2. Recipe (A) vs removal-based DPO (B)", ""]
    sets2 = {"Fresh external (decisive)": (["v4q_cf_s0_ext2"], ["v4q_dpo_s0_ext2"]),
             "Held-out tools, pooled": (["v4q_inp_telea_cf_s0_test", "v4q_inp_diffusion_cf_s0_test"],
                                        ["v4q_inp_telea_dpo_s0_test", "v4q_inp_diffusion_dpo_s0_test"]),
             "Main test": (["v4q_cf_s0_test"], ["v4q_dpo_s0_test"]),
             "External centres": (["v4q_cf_s0_ext"], ["v4q_dpo_s0_ext"])}
    decisive = None
    for name, (ra, rb) in sets2.items():
        a, b = pooled(R, ra), pooled(R, rb)
        out += [f"**{name}**", ""] + head
        res = {}
        for m in ("esg", "net_utility", "random_denial_rate", "target_hallucination_rate", "ccr"):
            line, res[m] = row(a, b, m, sd)
            out.append(line)
        out.append("")
        if name.startswith("Fresh external") and "diff" in res["esg"] and "diff" in res["net_utility"]:
            e, u = res["esg"], res["net_utility"]
            better = e["diff"] > 0 and e["ci_low"] > 0 and u["diff"] > 0 and u["ci_low"] > 0
            worthwhile = e["diff"] >= MIN_ESG and u["diff"] >= MIN_UTILITY
            decisive = (better, worthwhile)
    if decisive is not None:
        better, worthwhile = decisive
        if better and worthwhile:
            verdict = "**The recipe beats removal-based DPO** on new data: both ESG and net utility higher with intervals excluding zero and above the minimum worthwhile effect."
        elif better:
            verdict = "**Significant but too small to matter**: both intervals exclude zero, but at least one difference is below the pre-specified minimum (0.05)."
        else:
            verdict = "**Not shown to beat removal-based DPO on new data**: at least one fresh-external interval includes zero."
        out += ["Decision (rule fixed in advance): " + verdict, ""]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
