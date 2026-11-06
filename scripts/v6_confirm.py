"""The pre-registered v6 comparisons (docs/PREREGISTRATION_v6.md), evaluated as written.

C3   recipe + DPO (v4q_cfdpo_s0) vs recipe (v4q_cf_s0): CCR and erased-lesion claims on the fresh external set and
     the pooled held-out tools, with the pass rule; ESG and net utility alongside.
C2   replicated over seeds: recipe seeds 0-2 vs DPO seeds 0-2, mean +- sd per arm, and the paired test per seed pair
     on the fresh external set (ESG, net utility); verdict upgraded only if all three pairs agree.
S4   stage-4 selection rule on the validation set, if v4_s4_val exists.

    python scripts/v6_confirm.py --results RESULTS --out RESULTS/v6_confirmation.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402

MIN_CCR, MAX_CLAIMS_RISE, MAX_DROP = 0.03, 0.03, 0.03
LABEL = {"ccr": "CCR (unedited lesions)", "target_hallucination_rate": "Erased-lesion claims", "esg": "ESG",
         "net_utility": "Net utility", "random_denial_rate": "Random-removal denial"}
HEAD = ["| Endpoint | Cases | A | B | A − B [95% CI] | p |", "| --- | --- | --- | --- | --- | --- |"]


def pooled(results: Path, runs: list[str]):
    outs = []
    for r in runs:
        if (results / r).exists():
            outs += load_outcomes(results / r)
    return outs


def row(a, b, m):
    r = paired_bootstrap(a, b, m)
    if "diff" not in r:
        return f"| {LABEL[m]} | (no results) | | | | |", r
    p = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
    return f"| {LABEL[m]} | {r['n_cases']} | {r['a']:.3f} | {r['b']:.3f} | {r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {p} |", r


def metric(results: Path, run: str, m: str):
    f = results / run / "summary.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())["metrics"].get(m, {}).get("value")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    R = Path(args.results)
    out = ["# Pre-registered v6 confirmation (docs/PREREGISTRATION_v6.md)", ""]

    # C3
    out += ["## C3. Recipe + DPO (A) vs recipe (B)", ""]
    sets = {"Fresh external": (["v4q_cfdpo_s0_ext2"], ["v4q_cf_s0_ext2"]),
            "Held-out tools, pooled": (["v4q_inp_telea_cfdpo_s0_test", "v4q_inp_diffusion_cfdpo_s0_test"],
                                       ["v4q_inp_telea_cf_s0_test", "v4q_inp_diffusion_cf_s0_test"]),
            "Main test (supporting)": (["v4q_cfdpo_s0_test"], ["v4q_cf_s0_test"]),
            "External centres (supporting)": (["v4q_cfdpo_s0_ext"], ["v4q_cf_s0_ext"])}
    checks = []
    for name, (ra, rb) in sets.items():
        a, b = pooled(R, ra), pooled(R, rb)
        out += [f"**{name}**", ""] + HEAD
        res = {}
        for m in ("ccr", "target_hallucination_rate", "esg", "net_utility", "random_denial_rate"):
            line, res[m] = row(a, b, m)
            out.append(line)
        out.append("")
        if "supporting" not in name and "diff" in res.get("ccr", {}):
            gain = res["ccr"]["diff"] >= MIN_CCR and res["ccr"]["ci_low"] > 0
            claims_ok = res["target_hallucination_rate"]["diff"] <= MAX_CLAIMS_RISE
            no_drop = res["esg"]["diff"] >= -MAX_DROP and res["net_utility"]["diff"] >= -MAX_DROP
            checks.append((name, gain, claims_ok, no_drop))
    if checks:
        if all(g and c and n for _, g, c, n in checks):
            v = "**C3 passes**: preference training adds sensitivity to the recipe without raising erased-lesion claims, on both sets."
        elif all(g and c for _, g, c, _ in checks):
            v = "**A trade, not a gain**: sensitivity rises without more erased claims, but ESG or net utility falls by more than 0.03 on at least one set."
        else:
            v = "**C3 fails**: " + "; ".join(f"{n}: CCR gain {'yes' if g else 'no'}, claims within margin {'yes' if c else 'no'}" for n, g, c, _ in checks) + "."
        out += ["Decision (rule fixed in advance): " + v, ""]

    # C2 over seeds
    out += ["## C2 replicated over seeds: recipe (A) vs removal-based DPO (B)", ""]
    for split, label in (("ext2", "Fresh external"), ("test", "Main test")):
        out += [f"**{label}: mean ± sd over seeds**", "", "| Endpoint | Recipe (n seeds) | DPO (n seeds) |", "| --- | --- | --- |"]
        for m in ("esg", "net_utility", "ccr", "target_hallucination_rate", "random_denial_rate"):
            va = [x for x in (metric(R, f"v4q_cf_s{s}_{split}", m) for s in range(3)) if x is not None]
            vb = [x for x in (metric(R, f"v4q_dpo_s{s}_{split}", m) for s in range(3)) if x is not None]
            fmt = lambda v: f"{np.mean(v):.3f} ± {np.std(v, ddof=1) if len(v) > 1 else 0:.3f} ({len(v)})" if v else "-"  # noqa: E731
            out.append(f"| {LABEL[m]} | {fmt(va)} | {fmt(vb)} |")
        out.append("")
    out += ["**Fresh external, paired test per seed pair**", "", "| Seed | ESG A − B [95% CI] | p | Net utility A − B [95% CI] | p |",
            "| --- | --- | --- | --- | --- |"]
    signs = {"esg": [], "net_utility": []}
    for s in range(3):
        a, b = pooled(R, [f"v4q_cf_s{s}_ext2"]), pooled(R, [f"v4q_dpo_s{s}_ext2"])
        cells = []
        for m in ("esg", "net_utility"):
            r = paired_bootstrap(a, b, m) if a and b else {}
            if "diff" in r:
                cells += [f"{r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]", "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"]
                signs[m].append(1 if r["ci_low"] > 0 else -1 if r["ci_high"] < 0 else 0)
            else:
                cells += ["(no results)", ""]
        out.append(f"| {s} | " + " | ".join(cells) + " |")
    out.append("")
    if len(signs["esg"]) == 3:
        if all(x == 1 for x in signs["esg"]) and all(x == 1 for x in signs["net_utility"]):
            v = "**Recipe better than DPO on new data** (all three seed pairs agree, both endpoints)."
        elif all(x == -1 for x in signs["esg"]) and all(x == -1 for x in signs["net_utility"]):
            v = "**DPO better than the recipe on new data** (all three seed pairs agree, both endpoints)."
        else:
            v = "**No difference shown** on new data over three seeds (" + f"ESG signs {signs['esg']}, net utility signs {signs['net_utility']}; +1 = recipe better with CI excluding zero, −1 = DPO better, 0 = CI includes zero)."
        out += ["Decision (rule fixed in advance): " + v, ""]

    # stage 4
    u3, h3 = metric(R, "v4_s3_val", "net_utility"), metric(R, "v4_s3_val", "natural_hallucination_rate")
    u4, h4 = metric(R, "v4_s4_val", "net_utility"), metric(R, "v4_s4_val", "natural_hallucination_rate")
    if u4 is not None and u3 is not None:
        sel = u4 >= u3 + 0.02 and h4 <= h3 + 0.02
        out += ["## Stage-4 selection (validation only)", "",
                f"Stage 3: net utility {u3:.3f}, healthy-image claims {h3:.3f}. Stage 4: {u4:.3f}, {h4:.3f}.",
                "Decision (rule fixed in advance): " + ("**stage 4 replaces stage 3** as the final model." if sel else "**stage 3 stays** the final model."), ""]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
