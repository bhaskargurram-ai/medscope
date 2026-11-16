"""Review check R6: a Med-CAP-style comparator, adaptive prior suppression (docs/REVIEW_EXPERIMENTS.md).

Med-CAP (MICCAI 2026) subtracts a question-only prior from the model's decision, weighted per sample by how
confident the prior is and how weak the image evidence is. Its other half (evidence-discard training from gradient
attribution) needs a classifier head and does not fit an agent that answers in text, so only the suppression is
tested. On the stage-0 validation views, with s(x) the recipe's single-turn decision log-odds and p(q) the same
score on a uniform grey image with the case's question and candidate replies (fw/stage0.score_prior):

  raw        x = s
  fixed      x = s - a * p                       (a chosen on half A)
  adaptive   x = s - a0 * c * (1 - e) * p,       c = tanh(|p| / t), e = tanh(|s - p| / t), t = median |s| (half A)
             (a0 chosen on half A)

The prior is the same for every view of a case, so it cannot change which of a case's views scores higher; it can
remove case-level offsets (such as the reply-length bias that made s unusable as a cross-case score), which is what
across-case discrimination and any fixed threshold depend on. Cases are split into halves by a hash; every choice
(a, a0, the threshold) is made on half A with LaMa views only, and everything is reported on half B, for LaMa and
the held-out TELEA views.
"""

from __future__ import annotations

import hashlib

import numpy as np

from .analysis import auroc

ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
ALPHA0S = (0.5, 1.0, 1.5, 2.0)


def half(case_id: str) -> str:
    return "A" if int(hashlib.sha1(case_id.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


def rows(scores: dict[str, dict], priors: dict[str, float]) -> list[dict]:
    out = []
    for r in scores.values():
        if r["case_id"] in priors:
            out.append({**r, "p": priors[r["case_id"]], "half": half(r["case_id"])})
    return out


def transform(rs: list[dict], method: str, a: float, t: float = 1.0) -> np.ndarray:
    s = np.array([r["s"] for r in rs], float)
    p = np.array([r["p"] for r in rs], float)
    if method == "raw":
        return s
    if method == "fixed":
        return s - a * p
    c = np.tanh(np.abs(p) / t)
    e = np.tanh(np.abs(s - p) / t)
    return s - a * c * (1 - e) * p


def _key(r: dict) -> str:
    return r["variant"] if r["tool"] is None else f"{r['tool']}/{r['variant']}"


def site_auroc(rs: list[dict], x: np.ndarray, tool: str, neg: str = "ring") -> float:
    """AUROC of the other view (intact lesion) over the erasure: higher x = more 'present'."""
    pos = [xi for r, xi in zip(rs, x) if _key(r) == f"{tool}/{neg}"]
    era = [xi for r, xi in zip(rs, x) if _key(r) == f"{tool}/erased"]
    return auroc(np.array(pos), np.array(era)) if pos and era else float("nan")


def threshold(rs: list[dict], x: np.ndarray) -> float:
    """Youden-optimal cut on half-A LaMa views: present (original, control) vs erased."""
    pos = np.array([xi for r, xi in zip(rs, x) if _key(r) in ("original", "lama/control")])
    neg = np.array([xi for r, xi in zip(rs, x) if _key(r) == "lama/erased"])
    best, cut = -np.inf, 0.0
    for t in np.unique(np.concatenate([pos, neg])):
        j = (pos >= t).mean() - (neg >= t).mean()
        if j > best:
            best, cut = j, float(t)
    return cut


def rates(rs: list[dict], x: np.ndarray, cut: float, tool: str) -> dict:
    def share(key, present=True):
        v = [xi for r, xi in zip(rs, x) if _key(r) == key]
        return float(np.mean([(xi >= cut) == present for xi in v])) if v else float("nan")
    return {"found": share("original"), "neg_claims": share("negative"),
            "esg_ring": share(f"{tool}/erased", False) - share(f"{tool}/ring", False),
            "esg_control": share(f"{tool}/erased", False) - share(f"{tool}/control", False)}


def fit(rs_a: list[dict]) -> dict:
    """Choose a (fixed) and a0 (adaptive) on half A, LaMa views: the highest mean of the two site AUROCs."""
    t = float(np.median(np.abs([r["s"] for r in rs_a]))) or 1.0
    score = lambda x: np.nanmean([site_auroc(rs_a, x, "lama", "ring"), site_auroc(rs_a, x, "lama", "control")])  # noqa: E731
    a = max(ALPHAS, key=lambda v: score(transform(rs_a, "fixed", v)))
    a0 = max(ALPHA0S, key=lambda v: score(transform(rs_a, "adaptive", v, t)))
    return {"t": t, "a": a, "a0": a0}


def boot_diff(rs: list[dict], x: np.ndarray, x0: np.ndarray, tool: str, neg: str, n: int = 2000, seed: int = 0):
    cases = sorted({r["case_id"] for r in rs})
    idx = {c: [i for i, r in enumerate(rs) if r["case_id"] == c] for c in cases}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        sel = [i for c in rng.choice(cases, len(cases)) for i in idx[c]]
        sub = [rs[i] for i in sel]
        d = site_auroc(sub, x[sel], tool, neg) - site_auroc(sub, x0[sel], tool, neg)
        if d == d:
            out.append(d)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) if out else (float("nan"), float("nan"))


def evaluate(scores: dict[str, dict], priors: dict[str, float]) -> dict:
    rs = rows(scores, priors)
    A = [r for r in rs if r["half"] == "A"]
    B = [r for r in rs if r["half"] == "B"]
    f = fit(A)
    res = {"fit": f, "n_cases_B": len({r["case_id"] for r in B}), "methods": {}}
    x0B = transform(B, "raw", 0)
    for m, a in (("raw", 0.0), ("fixed", f["a"]), ("adaptive", f["a0"])):
        xA, xB = transform(A, m, a, f["t"]), transform(B, m, a, f["t"])
        cut = threshold(A, xA)
        r = {"cut": cut}
        for tool in ("lama", "telea"):
            for neg in ("ring", "control"):
                r[f"auroc_{tool}_{neg}"] = site_auroc(B, xB, tool, neg)
                r[f"diff_{tool}_{neg}"] = r[f"auroc_{tool}_{neg}"] - site_auroc(B, x0B, tool, neg)
                r[f"ci_{tool}_{neg}"] = boot_diff(B, xB, x0B, tool, neg) if m != "raw" else (0.0, 0.0)
            r[f"rates_{tool}"] = rates(B, xB, cut, tool)
        res["methods"][m] = r
    def score_a(m, a):                              # the variant the rule reads is chosen on half A too
        x = transform(A, m, a, f["t"])
        return np.nanmean([site_auroc(A, x, "lama", "ring"), site_auroc(A, x, "lama", "control")])
    best = max((("fixed", f["a"]), ("adaptive", f["a0"])), key=lambda ma: score_a(*ma))[0]
    d = res["methods"][best]
    res["rule"] = {"variant": best, "TELEA ring AUROC up >= 0.03": d["diff_telea_ring"] >= 0.03,
                   "interval above zero": d["ci_telea_ring"][0] > 0}
    res["rule"]["pass"] = res["rule"]["TELEA ring AUROC up >= 0.03"] and res["rule"]["interval above zero"]
    return res


def report(res: dict) -> str:
    f = lambda x: "-" if x != x else f"{x:.3f}"  # noqa: E731
    fit_ = res["fit"]
    lines = ["# R6: adaptive prior suppression (Med-CAP-style) on the recipe's decision scores", "",
             f"Validation dev set, half B ({res['n_cases_B']} cases); fitted on half A, LaMa views: fixed a = {fit_['a']}, "
             f"adaptive a0 = {fit_['a0']}, t = {fit_['t']:.2f}. AUROC of the intact-lesion view over the erasure; "
             "difference from the raw score [case-bootstrap 95% CI]. Rates at a threshold fixed on half A.", "",
             "| Method | AUROC LaMa ring | AUROC LaMa control | AUROC TELEA ring | AUROC TELEA control | "
             "TELEA ring vs raw [CI] | found | lesion-free claimed | ESG TELEA (ring) |", "| --- |" + " --- |" * 8]
    for m, r in res["methods"].items():
        lo, hi = r["ci_telea_ring"]
        rt = r["rates_telea"]
        lines.append(f"| {m} | {f(r['auroc_lama_ring'])} | {f(r['auroc_lama_control'])} | {f(r['auroc_telea_ring'])} | "
                     f"{f(r['auroc_telea_control'])} | {f(r['diff_telea_ring'])} [{f(lo)}, {f(hi)}] | {f(rt['found'])} | "
                     f"{f(rt['neg_claims'])} | {f(rt['esg_ring'])} |")
    rule = res["rule"]
    lines += ["", f"Rule (pre-registered; variant {rule['variant']}): TELEA ring AUROC up >= 0.03 with the interval "
              f"above zero: {'PASSES' if rule['pass'] else 'does not pass'}."]
    return "\n".join(lines) + "\n"
