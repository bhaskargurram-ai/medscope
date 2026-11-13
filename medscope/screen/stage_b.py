"""Screening stage B: decision policies that use new image evidence (the probes), on the dev set.

Same decision space and scoring as stage A (keep the recipe's answer, say absent, refer, say present). A policy passes
when it meets the stage-A rule against the recipe alone on half A and again on half B, on the benchmark's own
erasures (LaMa) **and** on the held-out-tool erasures (TELEA) separately (docs/SCREENING.md).
"""

from __future__ import annotations

import hashlib
import itertools
from typing import Callable

import numpy as np

from ..data.schema import View
from .stage_a import (ABSENT, FOLLOW, PRESENT, REFER, Features, banded, half_of, metrics, outcomes, passes,
                      says_present)
from .probes import subset_of

NAMES = ("d_pos", "d_conf", "d_prob", "tta_frac", "crop_pos", "crop_neg", "crop_ctrl_pos", "crop_specific",
         "caut_pos", "caut_neg", "m2_pos", "m2_neg", "s_peak")
SIGNALS = {
    "altered copies": ("tta_frac",),
    "close-up": ("crop_pos", "crop_neg", "crop_ctrl_pos", "crop_specific"),
    "cautious prompt": ("caut_pos", "caut_neg"),
    "second model": ("m2_pos", "m2_neg"),
    "answer probability": ("d_prob",),
    "specialist": ("s_peak",),
}


def features_b(view: View, pr: dict) -> Features:
    q = view.question
    d = pr.get("direct") or {}
    d_pos = says_present(d, q)
    tta = [says_present(t, q) for t in pr.get("tta") or []]
    crop, ctrl = says_present(pr.get("crop"), q), says_present(pr.get("crop_control"), q)
    caut, m2 = says_present(pr.get("cautious"), q), says_present(pr.get("second"), q)
    prob = d.get("answer_prob")
    prob = float(prob) if prob is not None else 0.5
    # the probability of the reply that says "present": the answer's own probability, or its complement
    p_present = prob if d_pos else (1 - prob if d_pos is False else 0.5)
    f = Features(view.view_id, view.case_id, q, d, d.get("action"), d_pos, float(d.get("confidence") or 0.5), None,
                 float(pr.get("specialist_peak") or 0.0), None, False, None, None, None)
    f.x = {"d_pos": float(d_pos is True), "d_conf": f.d_conf, "d_prob": p_present,
           "tta_frac": float(np.mean([t is True for t in tta])) if tta else 0.5,
           "crop_pos": float(crop is True), "crop_neg": float(crop is False), "crop_ctrl_pos": float(ctrl is True),
           "crop_specific": float(crop is True and ctrl is False), "caut_pos": float(caut is True),
           "caut_neg": float(caut is False), "m2_pos": float(m2 is True), "m2_neg": float(m2 is False),
           "s_peak": f.s_peak}
    f.vec = np.array([f.x[n] for n in NAMES])
    f.raw = {"tta": tta, "crop": crop, "ctrl": ctrl, "caut": caut, "m2": m2}
    return f


def rule_policies_b() -> dict[str, Callable[[Features], str]]:
    P: dict[str, Callable[[Features], str]] = {}
    for need, act in itertools.product((1, 2, 3), (ABSENT, REFER)):
        P[f"veto: claim holds on fewer than {need} of 3 altered copies -> {act}"] = \
            lambda f, n=need, a=act: a if f.d_pos and sum(t is True for t in f.raw["tta"]) < n else FOLLOW
    for act in (ABSENT, REFER):
        P[f"veto: close-up does not confirm -> {act}"] = lambda f, a=act: a if f.d_pos and f.raw["crop"] is False else FOLLOW
        P[f"veto: close-up not specific (also 'present' elsewhere) -> {act}"] = \
            lambda f, a=act: a if f.d_pos and f.raw["ctrl"] is True else FOLLOW
        P[f"veto: close-up not confirmed or not specific -> {act}"] = \
            lambda f, a=act: a if f.d_pos and (f.raw["crop"] is False or f.raw["ctrl"] is True) else FOLLOW
        P[f"veto: cautious prompt says absent -> {act}"] = lambda f, a=act: a if f.d_pos and f.raw["caut"] is False else FOLLOW
        P[f"veto: second model says absent -> {act}"] = lambda f, a=act: a if f.d_pos and f.raw["m2"] is False else FOLLOW
    for p, act in itertools.product((0.6, 0.7, 0.8, 0.9, 0.95), (ABSENT, REFER)):
        P[f"veto: probability of 'present' < {p} -> {act}"] = \
            lambda f, p=p, a=act: a if f.d_pos and f.x["d_prob"] < p else FOLLOW
    for act in (PRESENT, REFER):
        P[f"upgrade: recipe says absent, all 3 altered copies say present -> {act}"] = \
            lambda f, a=act: a if f.d_pos is False and all(t is True for t in f.raw["tta"]) else FOLLOW
        P[f"upgrade: recipe says absent, second model and cautious prompt say present -> {act}"] = \
            lambda f, a=act: a if f.d_pos is False and f.raw["m2"] is True and f.raw["caut"] is True else FOLLOW
    for k, band in itertools.product((2, 3, 4, 5), (False, True)):
        def vote(f, k=k, band=band):
            if f.d_action != "answer":
                return FOLLOW
            v = (int(bool(f.d_pos)) + int(sum(t is True for t in f.raw["tta"]) >= 2) + int(f.raw["crop"] is True and f.raw["ctrl"] is not True)
                 + int(f.raw["caut"] is True) + int(f.raw["m2"] is True) + int(f.s_peak >= 0.9))
            if v >= k:
                return PRESENT
            return REFER if band and v == k - 1 else ABSENT
        P[f"vote: >= {k} of 6 signals for present{', refer one short' if band else ''}"] = vote
    return P


def learned_sets() -> dict[str, tuple]:
    sets = {"all signals": NAMES}
    for name, cols in SIGNALS.items():
        sets[f"recipe + {name}"] = ("d_pos", "d_conf") + cols
        sets[f"all but {name}"] = tuple(n for n in NAMES if n not in cols)
    return sets


def fit_b(kind: str, names: tuple, feats: list[Features], views: dict[str, View]):
    from .stage_a import presence_label
    idx = [NAMES.index(n) for n in names]
    X = np.array([f.vec[idx] for f in feats if presence_label(views[f.view_id]) is not None and f.d_action == "answer"])
    y = np.array([presence_label(views[f.view_id]) for f in feats if presence_label(views[f.view_id]) is not None and f.d_action == "answer"])
    if len(y) == 0 or len(set(y.tolist())) < 2:          # too few labelled views to fit: a constant guess
        const = float(np.mean(y)) if len(y) else 0.5
        return lambda f: const
    if kind == "logistic":
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=1.0, max_iter=2000)
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, random_state=0)
    m.fit(X, y)
    return lambda f: float(m.predict_proba(f.vec[idx][None])[0, 1])


def split_sets(feats: list[Features], views: dict[str, View]) -> dict[str, list[Features]]:
    """LaMa set (unedited, LaMa erasure and control, lesion-free) and TELEA set (unedited, TELEA erasure and control,
    lesion-free); unedited and lesion-free views are in both."""
    out = {"lama": [], "telea": []}
    for f in feats:
        s = subset_of(views[f.view_id])
        if s in ("lama", "shared"):
            out["lama"].append(f)
        if s in ("telea", "shared"):
            out["telea"].append(f)
    return out


def run_screen_b(views: list[View], probes: dict[str, dict], cfg: dict, log=print) -> list[dict]:
    by_id = {v.view_id: v for v in views}
    feats = [features_b(v, probes[v.view_id]) for v in views if v.view_id in probes]
    halves = {h: [f for f in feats if half_of(f.case_id) == h] for h in "AB"}
    cells = {(h, s): fs for h in "AB" for s, fs in split_sets(halves[h], by_id).items()}
    log(f"stage B: {len(feats)} dev views; " + ", ".join(f"{h}/{s}: {len(fs)}" for (h, s), fs in cells.items()))
    base = {k: metrics(outcomes(lambda f: FOLLOW, fs, by_id, cfg)) for k, fs in cells.items()}
    rows = []

    def add(name, family, pol_for_cell):
        r = {"policy": name, "family": family}
        for k, fs in cells.items():
            r[k] = metrics(pol_for_cell(k, fs))
        rows.append(r)

    for name, pol in rule_policies_b().items():
        add(name, name.split(":")[0], lambda k, fs, pol=pol: outcomes(pol, fs, by_id, cfg))
    # learned: fit on all half-A views (both tools), evaluated on half B; half-A numbers by 2-fold cross-fitting in A
    fold = lambda f: int(hashlib.sha1(f.case_id.encode()).hexdigest()[8:16], 16) % 2  # noqa: E731
    for kind, (set_name, names), (lo, hi) in itertools.product(("logistic", "boosted trees"), learned_sets().items(),
                                                              ((0.5, 0.5), (0.4, 0.6), (0.3, 0.7), (0.2, 0.8))):
        probs = {kk: fit_b(kind, names, [f for f in halves["A"] if fold(f) != kk], by_id) for kk in (0, 1)}
        prob_all = fit_b(kind, names, halves["A"], by_id)

        def pol_cell(k, fs, probs=probs, prob_all=prob_all, lo=lo, hi=hi):
            if k[0] == "B":
                return outcomes(banded(prob_all, lo, hi), fs, by_id, cfg)
            return [o for kk in (0, 1) for o in outcomes(banded(probs[kk], lo, hi), [f for f in fs if fold(f) == kk], by_id, cfg)]
        add(f"learned {kind} ({set_name}), present >= {hi}, absent < {lo}", f"learned {kind}", pol_cell)
    for r in rows:
        r["pass_A"] = all(passes(r[("A", s)], base[("A", s)]) for s in ("lama", "telea"))
        r["pass_B"] = all(passes(r[("B", s)], base[("B", s)]) for s in ("lama", "telea"))
    rows.sort(key=lambda r: -np.nanmean([r[("A", s)]["net_utility"] for s in ("lama", "telea")]))
    return [{"policy": "baseline", "family": "baseline", **base, "pass_A": False, "pass_B": False}] + rows


def report_b(rows: list[dict]) -> str:
    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    base, rest = rows[0], rows[1:]
    pa = [r for r in rest if r["pass_A"]]
    pb = [r for r in pa if r["pass_B"]]
    out = ["# Screening stage B: new image evidence (validation dev set only)", "",
           f"{len(rest)} policies screened. Pass rule as in stage A (net utility +0.03, ESG +0.02, CCR not -0.03, "
           f"lesion-free claims not +0.03, against the recipe alone), required on the LaMa erasures **and** the TELEA "
           f"(held-out tool) erasures, on half A and again on half B.", "",
           f"**{len(pa)} pass on half A; {len(pb)} also pass on half B (shortlist).**", "",
           "| Policy | B LaMa: utility | B LaMa: ESG | B TELEA: utility | B TELEA: ESG | B TELEA: erased claims | B TELEA: CCR | Pass A | Pass B |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in [base] + pb + [x for x in rest if x not in pb][:25]:
        bl, bt = r[("B", "lama")], r[("B", "telea")]
        out.append(f"| {r['policy']} | {f(bl['net_utility'])} | {f(bl['esg'])} | {f(bt['net_utility'])} | {f(bt['esg'])} | "
                   f"{f(bt['target_hallucination_rate'])} | {f(bt['ccr'])} | {'yes' if r['pass_A'] else ''} | {'yes' if r['pass_B'] else ''} |")
    for s in ("lama", "telea"):
        best = max(rest, key=lambda r: r[("B", s)]["esg"] if r[("B", s)]["esg"] == r[("B", s)]["esg"] else -9)
        out.append(f"\nLargest half-B ESG on {s.upper()}: {f(best[('B', s)]['esg'])} ({best['policy']}); "
                   f"recipe alone {f(base[('B', s)]['esg'])}.")
    return "\n".join(out) + "\n"
