"""Framework stage 1 screen (docs/FRAMEWORK_STAGE1.md): tool-family arms against the replay-only control.

Generated agent answers on the validation dev set (the stage-0 views). For each arm and the control:
  found        share of unedited lesion images answered present (all cases)
  neg claims   share of lesion-free images answered present
  ESG (tool)   P(denied | erasure) - P(denied | control edit elsewhere), all cases, per tool (LaMa, TELEA)
  ctl denial   share denied after the control edit, among cases both the arm and the control find unedited
  ring denial  the same after the ring edit
Differences arm - control are paired by case, with bootstrap 95% intervals (4,000 resamples, seed 0).
"""

from __future__ import annotations

import numpy as np

from .analysis import table

# the rule (fixed in docs/FRAMEWORK_STAGE1.md before any arm was trained)
TELEA_ESG_GAIN = 0.03
TELEA_CTL_DROP = 0.03
LAMA_ESG_LOSS = 0.02
FOUND_LOSS = 0.03
NEG_RISE = 0.03


def _deny(x: float) -> float:
    return float(x < 0)


def _boot(diffs: list[float], n: int = 4000, seed: int = 0) -> tuple[float, float]:
    if not diffs:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    a = np.asarray(diffs, float)
    bs = [a[rng.integers(0, len(a), len(a))].mean() for _ in range(n)]
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def compare(arm: dict[str, dict], ctl: dict[str, dict]) -> dict:
    """Paired comparison of an arm's answers with the control's (both from stage0.read_answers)."""
    A, C = table(arm), table(ctl)
    out: dict = {}
    cases = [c for c in A if c in C and "original" in A[c] and "original" in C[c]]
    d = [float(A[c]["original"] > 0) - float(C[c]["original"] > 0) for c in cases]
    out["found"] = (float(np.mean([A[c]["original"] > 0 for c in cases])) if cases else float("nan"),
                    float(np.mean([C[c]["original"] > 0 for c in cases])) if cases else float("nan"),
                    float(np.mean(d)) if d else float("nan"), _boot(d))
    negs = [c for c in A if c in C and "negative" in A[c] and "negative" in C[c]]
    d = [float(A[c]["negative"] > 0) - float(C[c]["negative"] > 0) for c in negs]
    out["neg_claims"] = (float(np.mean([A[c]["negative"] > 0 for c in negs])) if negs else float("nan"),
                         float(np.mean([C[c]["negative"] > 0 for c in negs])) if negs else float("nan"),
                         float(np.mean(d)) if d else float("nan"), _boot(d))
    for tool in ("lama", "telea"):
        e, k, g = f"{tool}/erased", f"{tool}/control", f"{tool}/ring"
        both = [c for c in cases if all(x in A[c] and x in C[c] for x in (e, k))]
        esg = lambda T, c: _deny(T[c][e]) - _deny(T[c][k])  # noqa: E731
        d = [esg(A, c) - esg(C, c) for c in both]
        out[f"esg_{tool}"] = (float(np.mean([esg(A, c) for c in both])) if both else float("nan"),
                              float(np.mean([esg(C, c) for c in both])) if both else float("nan"),
                              float(np.mean(d)) if d else float("nan"), _boot(d))
        found = [c for c in both if A[c]["original"] > 0 and C[c]["original"] > 0]
        d = [_deny(A[c][k]) - _deny(C[c][k]) for c in found]
        out[f"ctl_denial_{tool}"] = (float(np.mean([_deny(A[c][k]) for c in found])) if found else float("nan"),
                                     float(np.mean([_deny(C[c][k]) for c in found])) if found else float("nan"),
                                     float(np.mean(d)) if d else float("nan"), _boot(d))
        fr = [c for c in found if g in A[c] and g in C[c]]
        d = [_deny(A[c][g]) - _deny(C[c][g]) for c in fr]
        out[f"ring_denial_{tool}"] = (float(np.mean([_deny(A[c][g]) for c in fr])) if fr else float("nan"),
                                      float(np.mean([_deny(C[c][g]) for c in fr])) if fr else float("nan"),
                                      float(np.mean(d)) if d else float("nan"), _boot(d))
        er = [c for c in both]
        d = [_deny(A[c][e]) - _deny(C[c][e]) for c in er]
        out[f"erased_denial_{tool}"] = (float(np.mean([_deny(A[c][e]) for c in er])) if er else float("nan"),
                                        float(np.mean([_deny(C[c][e]) for c in er])) if er else float("nan"),
                                        float(np.mean(d)) if d else float("nan"), _boot(d))
        out[f"n_{tool}"] = (len(both), len(found))
    out["n_cases"], out["n_negatives"] = len(cases), len(negs)
    return out


def passes(r: dict) -> dict:
    checks = {
        "TELEA ESG up >= 0.03": r["esg_telea"][2] >= TELEA_ESG_GAIN,
        "TELEA control denial down >= 0.03": r["ctl_denial_telea"][2] <= -TELEA_CTL_DROP,
        "LaMa ESG not down > 0.02": r["esg_lama"][2] >= -LAMA_ESG_LOSS,
        "found not down > 0.03": r["found"][2] >= -FOUND_LOSS,
        "lesion-free claims not up > 0.03": r["neg_claims"][2] <= NEG_RISE,
    }
    return {"checks": checks, "pass": all(checks.values())}


ROWS = (("found", "unedited lesions found"), ("neg_claims", "lesion-free images claimed"),
        ("esg_lama", "ESG, LaMa"), ("esg_telea", "ESG, TELEA (held out)"),
        ("erased_denial_lama", "erasure denied, LaMa"), ("erased_denial_telea", "erasure denied, TELEA"),
        ("ctl_denial_lama", "control edit denied (found), LaMa"), ("ctl_denial_telea", "control edit denied (found), TELEA"),
        ("ring_denial_lama", "ring edit denied (found), LaMa"), ("ring_denial_telea", "ring edit denied (found), TELEA"))


def report(results: dict[str, dict], control: str) -> str:
    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    lines = ["# Framework stage 1 screen: tool-family training vs the replay-only control (validation dev set)", "",
             f"Control: `{control}`. Differences arm - control paired by case, bootstrap 95% intervals.", ""]
    for arm, r in results.items():
        p = passes(r)
        lines += [f"## {arm}: {'PASSES' if p['pass'] else 'does not pass'}", "",
                  f"{r['n_cases']} lesion cases, {r['n_negatives']} lesion-free images; cases with both tools' views "
                  f"(all / found by both): LaMa {r['n_lama']}, TELEA {r['n_telea']}.", "",
                  "| Quantity | arm | control | difference [95% CI] |", "| --- | --- | --- | --- |"]
        for k, name in ROWS:
            a, c, d, (lo, hi) = r[k]
            lines.append(f"| {name} | {f(a)} | {f(c)} | {f(d)} [{f(lo)}, {f(hi)}] |")
        lines += ["", "Rule: " + "; ".join(f"{k}: {'yes' if v else 'no'}" for k, v in p["checks"].items()), ""]
    return "\n".join(lines) + "\n"
