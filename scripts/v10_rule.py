"""The pre-registered lead-4 rule (docs/PREREGISTRATION_v10.md), applied as written, plus the agents' own behaviour.

Go signal (pooled held-out tools TELEA + diffusion, full system vs the replay-only continuation v4q_sftc_s0): net
utility +0.05 or more, erased-lesion claims not higher, CCR not lower by more than 0.03; guard-rails: healthy-image
claims on the main test not higher by more than 0.03, fresh-external CCR not more than 0.03 below the recipe's.
Contribution: an ablation that lowers pooled held-out net utility by 0.03 or more; for the control half, also
erased-lesion claims worse by 0.03 or more.

    python scripts/v10_rule.py --results RESULTS --out RESULTS/v10_rule.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.mas.arbiter import RUN_TAG  # noqa: E402
from medscope.mas.reports import read_reports  # noqa: E402

HELDOUT = ("telea", "diffusion")
GAIN, MARGIN, CONTRIB = 0.05, 0.03, 0.03
LABEL = {"net_utility": "Net utility", "target_hallucination_rate": "Erased-lesion claims", "ccr": "CCR (unedited lesions)",
         "esg": "ESG", "natural_hallucination_rate": "Claims on lesion-free images", "random_denial_rate": "Control-edit denial"}
HEAD = ["| Endpoint | Cases | A | B | A − B [95% CI] | p |", "| --- | --- | --- | --- | --- | --- |"]


def run_names(tag: str, where: str) -> list[str]:
    if where == "heldout":
        return [f"v4q_inp_{t}_{tag}_s0_test" for t in HELDOUT]
    return [f"v4q_{tag}_s0_{where}"]


def outcomes(R: Path, names: list[str]):
    outs = []
    for n in names:
        if (R / n).exists():
            outs += load_outcomes(R / n)
    return outs


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def compare(a, b, metrics) -> tuple[list[str], dict]:
    lines, res = list(HEAD), {}
    for m in metrics:
        r = paired_bootstrap(a, b, m) if a and b else {}
        res[m] = r
        if "diff" in r:
            lines.append(f"| {LABEL[m]} | {r['n_cases']} | {r['a']:.3f} | {r['b']:.3f} | {r['diff']:+.3f} "
                         f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | {fmt_p(r['p'])} |")
        else:
            lines.append(f"| {LABEL[m]} | (no results) | | | | |")
    return lines, res


def specialist_and_verifier(R: Path) -> list[str]:
    """How often the specialist finds something, and how often a direct-reader claim survives erasure of its own
    region, by view kind, on each reports file."""
    out = ["## The agents on their own (stored reports)", "",
           "Specialist: share of views where it found a region. Verifier: among views where the direct reader claimed "
           "with a box and the region was tested, the share still claimed after erasure and after the control edit "
           "(\"No\"-type answers counted as withdrawn).", "",
           "| Set | Kind | Views | Specialist found | Tested | Still claimed after erasure | Still claimed after control |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    absent = {"no", "none", "no abnormality", "absent", "normal", "not present"}

    def claimed(r):
        return bool(r) and r.get("action") == "answer" and str(r.get("answer", "")).strip().lower().rstrip(".") not in absent
    for f in sorted((R / "mas_reports").glob("*.jsonl")):
        reps = read_reports(f)
        by_kind: dict[str, list[dict]] = {}
        for vid, r in reps.items():
            kind = vid.rsplit("__", 1)[-1] if "__" in vid else "natural_negative"
            by_kind.setdefault(kind, []).append(r)
        for kind, rs in sorted(by_kind.items()):
            found = sum(bool((r.get("specialist") or {}).get("found")) for r in rs)
            tested = [r["verify"] for r in rs if (r.get("verify") or {}).get("source") == "direct reader"
                      and (r["verify"].get("erased") is not None)]
            still_e = sum(claimed(t["erased"]) for t in tested)
            ctrl = [t for t in tested if t.get("control") is not None]
            still_c = sum(claimed(t["control"]) for t in ctrl)
            pct = lambda a, n: f"{a}/{n} ({100 * a / n:.0f}%)" if n else "-"  # noqa: E731
            out.append(f"| {f.stem} | {kind} | {len(rs)} | {pct(found, len(rs))} | {len(tested)} | "
                       f"{pct(still_e, len(tested))} | {pct(still_c, len(ctrl))} |")
    return out + [""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    R = Path(args.results)
    full = RUN_TAG["full"]
    out = ["# Pre-registered lead-4 rule (docs/PREREGISTRATION_v10.md)", ""]
    metrics = ("net_utility", "target_hallucination_rate", "ccr", "esg", "random_denial_rate")

    out += ["## Go signal: full system (A) vs replay-only continuation `v4q_sftc_s0` (B), held-out tools pooled", ""]
    a, b = outcomes(R, run_names(full, "heldout")), outcomes(R, run_names("sftc", "heldout"))
    lines, res = compare(a, b, metrics)
    out += lines + [""]
    g_main = outcomes(R, run_names(full, "test")), outcomes(R, run_names("sftc", "test"))
    l2, r2 = compare(*g_main, ("natural_hallucination_rate", "ccr", "target_hallucination_rate", "net_utility"))
    out += ["Guard-rail, main test (A vs `v4q_sftc_s0`; erasures made with LaMa, the verifier's own tool):", ""] + l2 + [""]
    g_ext2 = outcomes(R, run_names(full, "ext2")), outcomes(R, run_names("cf", "ext2"))
    l3, r3 = compare(*g_ext2, ("ccr", "target_hallucination_rate", "net_utility", "esg"))
    out += ["Guard-rail, fresh external (A vs the recipe `v4q_cf_s0`):", ""] + l3 + [""]

    verdict = "not decided (results missing)"
    if all("diff" in res.get(m, {}) for m in ("net_utility", "target_hallucination_rate", "ccr")) and \
            "diff" in r2.get("natural_hallucination_rate", {}) and "diff" in r3.get("ccr", {}):
        checks = {
            f"net utility +{GAIN} or more": res["net_utility"]["diff"] >= GAIN,
            "erased-lesion claims not higher": res["target_hallucination_rate"]["diff"] <= 0,
            f"CCR not lower by more than {MARGIN}": res["ccr"]["diff"] >= -MARGIN,
            f"main-test healthy-image claims not higher by more than {MARGIN}": r2["natural_hallucination_rate"]["diff"] <= MARGIN,
            f"fresh-external CCR not more than {MARGIN} below the recipe": r3["ccr"]["diff"] >= -MARGIN,
        }
        out += ["| Condition | Met |", "| --- | --- |"] + [f"| {k} | {'yes' if v else 'no'} |" for k, v in checks.items()] + [""]
        verdict = "GO" if all(checks.values()) else "NO GO"
    out += [f"**Go signal: {verdict}.**", ""]

    out += ["## Which agent carries it: each ablation (B) against the full system (A), held-out tools pooled", "",
            f"An agent contributes if removing it lowers net utility by {CONTRIB} or more (A − B ≥ {CONTRIB}); the control "
            f"half also if erased-lesion claims rise by {CONTRIB} or more without it.", ""]
    for name in ("nob", "nos", "nov", "noc", "dir"):
        tag = RUN_TAG[name]
        bb = outcomes(R, run_names(tag, "heldout"))
        lines, rr = compare(a, bb, ("net_utility", "target_hallucination_rate", "ccr"))
        out += [f"### `{tag}`", ""] + lines
        if "diff" in rr.get("net_utility", {}):
            contrib = rr["net_utility"]["diff"] >= CONTRIB
            if name == "noc" and "diff" in rr.get("target_hallucination_rate", {}):
                contrib = contrib or -rr["target_hallucination_rate"]["diff"] >= CONTRIB
            out += ["", f"Contributes: **{'yes' if contrib else 'no'}**"]
        out += [""]
    for tag, label in ((full, "full system"), ("sftc", "replay-only continuation"), ("cf", "recipe")):
        bb = outcomes(R, run_names(tag, "ext2"))
        if bb:
            pos = [o for o in bb if o.case_id.startswith("siimext") and o.kind == "original"]
            det = sum(1 for o in pos if o.action == "answer" and o.correct)
            out.append(f"- SIIM pneumothorax detected on the fresh external set, {label}: {det}/{len(pos)}")
    out += [""] + specialist_and_verifier(R)
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
