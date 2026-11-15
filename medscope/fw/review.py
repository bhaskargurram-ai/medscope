"""Rules for the experiments added after the external review (docs/REVIEW_EXPERIMENTS.md, fixed before any ran).

Both screens use the stage-1 comparison (medscope/fw/stage1.compare: generated agent answers on the validation dev
set, paired by case) and differ only in the comparator and the rule:

  R1 hard-negative swap (CORAL-style) vs the replay-only control `replay_control`: does a global image-swap signal
     raise held-out discrimination?
       TELEA ESG up >= 0.03; LaMa ESG not down > 0.02; found not down > 0.03; lesion-free claims not up > 0.03
  R2 vision adapters with layer-wise learning-rate decay vs the stage-1 recipe `recipe`: does adapting the vision
     encoder gently improve perception without losing discrimination?
       found up >= 0.03; LaMa ESG and TELEA ESG each not down > 0.02; lesion-free claims not up > 0.03
Point estimates decide (as in stage 1); intervals are reported.
"""

from __future__ import annotations

R1 = {"esg_telea_gain": 0.03, "esg_lama_loss": 0.02, "found_loss": 0.03, "neg_rise": 0.03}
R2 = {"found_gain": 0.03, "esg_loss": 0.02, "neg_rise": 0.03}


def passes_r1(r: dict) -> dict:
    checks = {
        "TELEA ESG up >= 0.03": r["esg_telea"][2] >= R1["esg_telea_gain"],
        "LaMa ESG not down > 0.02": r["esg_lama"][2] >= -R1["esg_lama_loss"],
        "found not down > 0.03": r["found"][2] >= -R1["found_loss"],
        "lesion-free claims not up > 0.03": r["neg_claims"][2] <= R1["neg_rise"],
    }
    return {"checks": checks, "pass": all(checks.values())}


def passes_r2(r: dict) -> dict:
    checks = {
        "found up >= 0.03": r["found"][2] >= R2["found_gain"],
        "LaMa ESG not down > 0.02": r["esg_lama"][2] >= -R2["esg_loss"],
        "TELEA ESG not down > 0.02": r["esg_telea"][2] >= -R2["esg_loss"],
        "lesion-free claims not up > 0.03": r["neg_claims"][2] <= R2["neg_rise"],
    }
    return {"checks": checks, "pass": all(checks.values())}


def report(title: str, comparator: str, results: dict[str, dict], rule) -> str:
    from .stage1 import ROWS
    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    lines = [f"# {title}", "", f"Comparator: `{comparator}`. Differences arm - comparator, paired by case, bootstrap "
             "95% intervals (validation dev set, generated agent answers).", ""]
    for arm, r in results.items():
        p = rule(r)
        lines += [f"## {arm}: {'PASSES' if p['pass'] else 'does not pass'}", "",
                  f"{r['n_cases']} lesion cases, {r['n_negatives']} lesion-free images.", "",
                  "| Quantity | arm | comparator | difference [95% CI] |", "| --- | --- | --- | --- |"]
        for k, name in ROWS:
            a, c, d, (lo, hi) = r[k]
            lines.append(f"| {name} | {f(a)} | {f(c)} | {f(d)} [{f(lo)}, {f(hi)}] |")
        lines += ["", "Rule: " + "; ".join(f"{k}: {'yes' if v else 'no'}" for k, v in p["checks"].items()), ""]
    return "\n".join(lines) + "\n"
