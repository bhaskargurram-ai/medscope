"""The pre-registered v7 comparison (docs/PREREGISTRATION_v7.md), evaluated as written.

C4   CMCC continuation (v4q_cmccn_s{0,1,2}) vs the matched-compute control (v4q_sftc_s{0,1,2}: same replay, no
     paired-view terms), paired per seed and pooled over seeds. Primary endpoint: erased-lesion claims on the pooled
     held-out tools (TELEA + diffusion). Guards: lesion-free claims on the main test, ESG and net utility on the fresh
     external set. Supporting: CMCC vs the recipe adapter at each seed, and vs C3 at seed 0.

    python scripts/v7_confirm.py --results RESULTS --out RESULTS/v7_confirmation.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402

MARGIN = 0.03
SEEDS = (0, 1, 2)
HELDOUT = ("telea", "diffusion")
LABEL = {"target_hallucination_rate": "Erased-lesion claims", "esg": "ESG", "random_denial_rate": "Control-edit denial",
         "net_utility": "Net utility", "ccr": "CCR (unedited lesions)", "natural_hallucination_rate": "Claims on lesion-free images"}
HEAD = ["| Endpoint | Cases | A | B | A − B [95% CI] | p |", "| --- | --- | --- | --- | --- | --- |"]


def runs(arm: str, seed: int, where: str) -> list[str]:
    """Run names of one arm at one seed on one set ('heldout' pools the two held-out tools)."""
    if where == "heldout":
        return [f"v4q_inp_{t}_{arm}_s{seed}_test" for t in HELDOUT]
    return [f"v4q_{arm}_s{seed}_{where}"]


def pooled(results: Path, names: list[str]):
    outs = []
    for r in names:
        if (results / r).exists():
            outs += load_outcomes(results / r)
    return outs


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def table(a, b, metrics) -> tuple[list[str], dict]:
    lines, res = list(HEAD), {}
    for m in metrics:
        r = paired_bootstrap(a, b, m) if a and b else {}
        res[m] = r
        if "diff" in r:
            lines.append(f"| {LABEL[m]} | {r['n_cases']} | {r['a']:.3f} | {r['b']:.3f} | {r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {fmt_p(r['p'])} |")
        else:
            lines.append(f"| {LABEL[m]} | (no results) | | | | |")
    return lines, res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", default="cmccn", help="CMCC arm tag (default cmccn)")
    ap.add_argument("--control", default="sftc", help="matched-compute control tag (default sftc)")
    args = ap.parse_args()
    R = Path(args.results)
    out = ["# Pre-registered v7 confirmation (docs/PREREGISTRATION_v7.md)", "",
           f"A = CMCC (`v4q_{args.arm}_s*`), B = matched-compute control (`v4q_{args.control}_s*`).", ""]

    # C4, per seed and pooled, held-out tools
    out += ["## C4. Held-out tools (TELEA + diffusion), CMCC (A) vs matched-compute control (B)", ""]
    per_seed_sign, pooled_a, pooled_b, seeds_done = [], [], [], []
    for s in SEEDS:
        a, b = pooled(R, runs(args.arm, s, "heldout")), pooled(R, runs(args.control, s, "heldout"))
        if not a or not b:
            out += [f"**Seed {s}:** not both arms tested yet.", ""]
            continue
        seeds_done.append(s)
        lines, res = table(a, b, ("target_hallucination_rate", "esg", "random_denial_rate", "net_utility", "ccr"))
        out += [f"**Seed {s}**", ""] + lines + [""]
        per_seed_sign.append(res["target_hallucination_rate"]["diff"] < 0)
        pooled_a += a
        pooled_b += b
    pooled_res = {}
    if seeds_done:
        lines, pooled_res = table(pooled_a, pooled_b, ("target_hallucination_rate", "esg", "random_denial_rate", "net_utility", "ccr"))
        out += [f"**Pooled over seeds {seeds_done}**", ""] + lines + [""]

    # guards
    out += ["## Guards", ""]
    ga, gb = [], []
    for s in seeds_done:
        ga += pooled(R, runs(args.arm, s, "test"))
        gb += pooled(R, runs(args.control, s, "test"))
    g_lines, g_test = table(ga, gb, ("natural_hallucination_rate", "esg", "target_hallucination_rate", "ccr", "net_utility"))
    out += [f"**Main test, pooled over seeds {seeds_done}**", ""] + g_lines + [""]
    ea, eb = [], []
    for s in seeds_done:
        ea += pooled(R, runs(args.arm, s, "ext2"))
        eb += pooled(R, runs(args.control, s, "ext2"))
    e_lines, g_ext = table(ea, eb, ("esg", "net_utility", "target_hallucination_rate", "random_denial_rate", "ccr"))
    out += [f"**Fresh external, pooled over seeds {seeds_done}**", ""] + e_lines + [""]

    # decision
    if len(seeds_done) == 3 and "diff" in pooled_res.get("target_hallucination_rate", {}):
        prim = pooled_res["target_hallucination_rate"]
        every_seed = all(per_seed_sign)
        ci_excl = prim["ci_high"] < 0
        esg_ok = pooled_res["esg"]["diff"] > -MARGIN
        guard_nat = "diff" in g_test.get("natural_hallucination_rate", {}) and g_test["natural_hallucination_rate"]["diff"] <= MARGIN
        guard_ext = ("diff" in g_ext.get("esg", {}) and g_ext["esg"]["diff"] > -MARGIN
                     and g_ext["net_utility"]["diff"] > -MARGIN)
        detail = (f"fewer erased claims in every seed pair: {'yes' if every_seed else 'no'}; pooled interval excludes zero: "
                  f"{'yes' if ci_excl else 'no'}; pooled ESG not lower: {'yes' if esg_ok else 'no'}; lesion-free guard: "
                  f"{'holds' if guard_nat else 'fails'}; fresh-external guard: {'holds' if guard_ext else 'fails'}")
        if every_seed and ci_excl and esg_ok and guard_nat and guard_ext:
            v = "**C4 passes**: the paired-view objective, not the extra training, reduces erased-lesion claims on unseen tools."
        elif every_seed and ci_excl and esg_ok:
            v = "**A trade, not a gain**: the primary endpoint holds but a guard fails."
        else:
            v = "**C4 fails**: the smoke-test gain is not attributable to the objective over three seeds."
        out += ["## Decision (rule fixed in advance)", "", v, "", detail + ".", ""]
    else:
        out += ["## Decision", "", f"Not all three seed pairs are tested yet ({len(seeds_done)} of 3); no verdict.", ""]

    # supporting
    out += ["## Supporting: CMCC (A) vs the recipe adapter (B), held-out tools, per seed", ""]
    for s in SEEDS:
        a, b = pooled(R, runs(args.arm, s, "heldout")), pooled(R, runs("cf", s, "heldout"))
        if a and b:
            lines, _ = table(a, b, ("target_hallucination_rate", "esg", "random_denial_rate", "net_utility"))
            out += [f"**Seed {s}**", ""] + lines + [""]
    out += ["## Supporting: matched-compute control (A) vs the recipe adapter (B), held-out tools, per seed", "",
            "The longer-training observation, paired by seed (needs the recipe's held-out tests at every seed, notebook 38).", ""]
    for s in SEEDS:
        a, b = pooled(R, runs(args.control, s, "heldout")), pooled(R, runs("cf", s, "heldout"))
        if a and b:
            lines, _ = table(a, b, ("target_hallucination_rate", "esg", "random_denial_rate", "ccr", "net_utility"))
            out += [f"**Seed {s}**", ""] + lines + [""]
        else:
            out += [f"**Seed {s}:** recipe held-out tests not available.", ""]
    a, b = pooled(R, runs(args.arm, 0, "heldout")), pooled(R, runs("cfdpo", 0, "heldout"))
    if a and b:
        lines, _ = table(a, b, ("target_hallucination_rate", "esg", "random_denial_rate", "net_utility"))
        out += ["## Supporting: CMCC (A) vs recipe + DPO, C3 (B), held-out tools, seed 0", ""] + lines + [""]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
