"""Stage A of the screening funnel: decision policies on top of the stored lead-4 reports, scored on the validation
views only. No model is run: every policy reads the reports (direct reader, question-blind reader, specialist,
verifier) and decides, per view, to keep the direct reader's answer, say the finding is absent, refer, or (for yes/no
questions) say it is present.

Selection is on one half of the validation cases and confirmation on the other; a policy passes only if it meets the
rule on both halves. The rule asks for a gain in the evidence sensitivity gap, not only net utility, because every
failed method so far moved the answer threshold without separating erased from present lesions better.
"""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from ..actions import FinalAction, asked_finding, asks_health, polarity
from ..data.schema import ActionKind, View, ViewKind
from ..eval.metrics import METRICS
from ..mas.reports import BLIND_QUESTION
from ..rewards import Outcome, score

METRIC_KEYS = ("net_utility", "esg", "target_hallucination_rate", "ccr", "natural_hallucination_rate", "random_denial_rate")
# pass rule, fixed before the screen runs (docs/SCREENING.md): on BOTH halves, against keeping the direct reader
RULE = {"net_utility": 0.03, "esg": 0.02, "ccr_drop": 0.03, "healthy_rise": 0.03}

FOLLOW, ABSENT, REFER, PRESENT = "follow", "absent", "refer", "present"


# ---- reading the reports (never the gold answer) ------------------------------------------------------------------

def says_present(reply: Optional[dict], question: str) -> Optional[bool]:
    """True if a reader's answer claims the finding, False if it says it is not there, None for no answer."""
    if not reply or reply.get("action") != "answer" or not reply.get("answer"):
        return None
    a = reply["answer"]
    pol = polarity(a, question)
    if asks_health(question):
        return pol == "no"
    return pol != "no"


def is_yes_no(question: str) -> bool:
    q = question.strip().lower()
    return asks_health(question) or asked_finding(question) is not None or q.split(" ", 1)[0] in (
        "is", "are", "does", "do", "can", "was", "were", "has", "have")


def absent_text(question: str) -> str:
    if asks_health(question):
        return "Yes"
    return "No" if is_yes_no(question) else "No abnormality"


def present_text(question: str) -> Optional[str]:
    if asks_health(question):
        return "No"
    return "Yes" if is_yes_no(question) else None


@dataclass
class Features:
    view_id: str
    case_id: str
    question: str
    direct: dict
    d_action: Optional[str]
    d_pos: Optional[bool]
    d_conf: float
    b_pos: Optional[bool]
    s_peak: float
    s_box: Optional[list]
    v_tested: bool
    v_erased_pos: Optional[bool]
    v_control_pos: Optional[bool]
    v_source: Optional[str]
    vec: np.ndarray = field(default=None, repr=False)


FEATURE_NAMES = ("d_pos", "d_neg", "d_conf", "b_pos", "b_neg", "s_peak", "s_found", "v_tested", "v_erased_pos",
                 "v_erased_neg", "v_control_pos", "v_support", "v_from_direct")


def features(view: View, rep: dict) -> Features:
    q = view.question
    d = rep.get("direct") or {}
    s = rep.get("specialist") or {}
    v = rep.get("verify") or {}
    d_pos = says_present(d, q)
    b_pos = says_present(rep.get("blind"), BLIND_QUESTION)
    tested = v.get("erased") is not None
    e_pos = says_present(v.get("erased"), q) if tested else None
    c_pos = says_present(v.get("control"), q) if v.get("control") is not None else None
    f = Features(view.view_id, view.case_id, q, d, d.get("action"), d_pos, float(d.get("confidence") or 0.5), b_pos,
                 float(s.get("peak") or 0.0), (s.get("regions") or [{}])[0].get("box") if s.get("found") else None,
                 tested, e_pos, c_pos, v.get("source"))
    support = 1.0 if (e_pos is False and c_pos is True) else 0.0
    f.vec = np.array([d_pos is True, d_pos is False, f.d_conf, b_pos is True, b_pos is False, f.s_peak,
                      float(bool(s.get("found"))), tested, e_pos is True, e_pos is False, c_pos is True, support,
                      v.get("source") == "direct reader"], dtype=float)
    return f


# ---- turning a decision into a scored final action ---------------------------------------------------------------

def final_for(decision: str, f: Features) -> Optional[FinalAction]:
    d = f.direct
    if decision == FOLLOW or f.d_action in ("clarify", None, "malformed"):
        if f.d_action == "answer":
            return FinalAction(ActionKind.ANSWER, answer=d.get("answer"), box=d.get("box"), confidence=d.get("confidence"))
        if f.d_action == "clarify":
            return FinalAction(ActionKind.CLARIFY, text=d.get("text"))
        if f.d_action == "refer":
            return FinalAction(ActionKind.REFER, text=d.get("text"))
        return None
    if decision == ABSENT:
        return FinalAction(ActionKind.ANSWER, answer=absent_text(f.question), confidence=0.7)
    if decision == REFER:
        return FinalAction(ActionKind.REFER, text="reports disagree")
    if decision == PRESENT:
        if f.d_pos:                                   # already present: keep the reader's own wording and box
            return final_for(FOLLOW, f)
        txt = present_text(f.question)
        if txt is None:
            return FinalAction(ActionKind.REFER, text="present, but the finding cannot be named")
        return FinalAction(ActionKind.ANSWER, answer=txt, box=f.s_box or d.get("box"), confidence=0.7)
    raise ValueError(decision)


def outcomes(policy: Callable[[Features], str], feats: list[Features], views: dict[str, View], cfg: dict) -> list[Outcome]:
    out = []
    for f in feats:
        fin = final_for(policy(f), f)
        out.append(score(views[f.view_id], fin, cfg, malformed=fin is None))
    return out


def metrics(outs: list[Outcome]) -> dict:
    return {k: METRICS[k](outs) for k in METRIC_KEYS}


# ---- the policy space -----------------------------------------------------------------------------------------------

def rule_policies() -> dict[str, Callable[[Features], str]]:
    P: dict[str, Callable[[Features], str]] = {"baseline: keep the direct reader": lambda f: FOLLOW}
    for t, act in itertools.product((0.3, 0.5, 0.7, 0.9, 0.95, 0.98, 0.99), (ABSENT, REFER)):
        P[f"veto: direct claims, specialist peak < {t} -> {act}"] = \
            lambda f, t=t, a=act: a if f.d_pos and f.s_peak < t else FOLLOW
    for mode, act in itertools.product(("survives erasure", "survives erasure or control lost", "no support"), (ABSENT, REFER)):
        def pol(f, mode=mode, a=act):
            if not (f.d_pos and f.v_tested):
                return FOLLOW
            if mode == "survives erasure":
                bad = f.v_erased_pos is True
            elif mode == "survives erasure or control lost":
                bad = f.v_erased_pos is True or f.v_control_pos is False
            else:
                bad = not (f.v_erased_pos is False and f.v_control_pos is True)
            return a if bad else FOLLOW
        P[f"veto: verifier ({mode}) -> {act}"] = pol
    for act in (ABSENT, REFER):
        P[f"veto: blind reader sees nothing -> {act}"] = lambda f, a=act: a if f.d_pos and f.b_pos is False else FOLLOW
    for c in (0.6, 0.7, 0.8, 0.9):
        P[f"veto: direct claims with confidence < {c} -> refer"] = lambda f, c=c: REFER if f.d_pos and f.d_conf < c else FOLLOW
    for u, need_blind, act in itertools.product((0.9, 0.95, 0.98, 0.99), (False, True), (PRESENT, REFER)):
        P[f"upgrade: direct says absent, specialist peak >= {u}{' and blind sees something' if need_blind else ''} -> {act}"] = \
            lambda f, u=u, nb=need_blind, a=act: a if f.d_pos is False and f.s_peak >= u and (f.b_pos or not nb) else FOLLOW
    for t, u in itertools.product((0.3, 0.5, 0.7, 0.9, 0.95, 0.98, 0.99), (0.95, 0.98, 0.99)):
        def both(f, t=t, u=u):
            if f.d_pos and f.s_peak < t:
                return ABSENT
            if f.d_pos is False and f.s_peak >= u:
                return PRESENT
            return FOLLOW
        P[f"veto (specialist < {t}) + upgrade (specialist >= {u})"] = both
    for k, t, band in itertools.product((1, 2, 3, 4), (0.5, 0.9, 0.98), (False, True)):
        def vote(f, k=k, t=t, band=band):
            if f.d_action != "answer":
                return FOLLOW
            v = int(bool(f.d_pos)) + int(bool(f.b_pos)) + int(f.s_peak >= t) + int(f.v_erased_pos is False and f.v_control_pos is True)
            if v >= k:
                return PRESENT
            return REFER if band and v == k - 1 else ABSENT
        P[f"vote: >= {k} of 4 for present (specialist >= {t}){', refer one short' if band else ''}"] = vote
    return P


LEARNED_SETS = {
    "all reports": FEATURE_NAMES,
    "no verifier": tuple(n for n in FEATURE_NAMES if not n.startswith("v_")),
    "no specialist": tuple(n for n in FEATURE_NAMES if not n.startswith("s_")),
    "no blind reader": tuple(n for n in FEATURE_NAMES if not n.startswith("b_")),
    "direct + specialist": ("d_pos", "d_neg", "d_conf", "s_peak", "s_found"),
}
BANDS = ((0.5, 0.5), (0.4, 0.6), (0.3, 0.7), (0.2, 0.8))


def presence_label(view: View) -> Optional[int]:
    """Training target for learned combiners (dev data only): is the asked finding in the image?"""
    if view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL):
        return 1
    if view.kind in (ViewKind.TARGET_REMOVAL, ViewKind.NATURAL_NEGATIVE):
        return 0
    return None


def fit_combiner(kind: str, names: tuple, feats: list[Features], views: dict[str, View], seed: int = 0):
    idx = [FEATURE_NAMES.index(n) for n in names]
    X, y = [], []
    for f in feats:
        lab = presence_label(views[f.view_id])
        if lab is not None and f.d_action == "answer":
            X.append(f.vec[idx])
            y.append(lab)
    X, y = np.array(X), np.array(y)
    if kind == "logistic":
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=1.0, max_iter=2000)
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, random_state=seed)
    m.fit(X, y)
    return lambda f: float(m.predict_proba(f.vec[idx][None])[0, 1])


def banded(prob: Callable[[Features], float], lo: float, hi: float) -> Callable[[Features], str]:
    def pol(f):
        if f.d_action != "answer":
            return FOLLOW
        p = prob(f)
        return PRESENT if p >= hi else ABSENT if p < lo else REFER
    return pol


# ---- the screen -----------------------------------------------------------------------------------------------------

def half_of(case_id: str) -> str:
    return "A" if int(hashlib.sha1(case_id.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


def passes(m: dict, base: dict) -> bool:
    vals = (m["net_utility"], m["esg"], m["ccr"], m["natural_hallucination_rate"],
            base["net_utility"], base["esg"], base["ccr"], base["natural_hallucination_rate"])
    if any(v is None or v != v for v in vals):
        return False
    return (m["net_utility"] - base["net_utility"] >= RULE["net_utility"]
            and m["esg"] - base["esg"] >= RULE["esg"]
            and base["ccr"] - m["ccr"] <= RULE["ccr_drop"]
            and m["natural_hallucination_rate"] - base["natural_hallucination_rate"] <= RULE["healthy_rise"])


def run_screen(views: list[View], reports: dict[str, dict], cfg: dict, log=print) -> list[dict]:
    by_id = {v.view_id: v for v in views}
    feats = [features(v, reports[v.view_id]) for v in views if v.view_id in reports]
    halves = {h: [f for f in feats if half_of(f.case_id) == h] for h in "AB"}
    log(f"stage A: {len(feats)} validation views with reports (A {len(halves['A'])}, B {len(halves['B'])})")
    rows = []
    base = {h: metrics(outcomes(lambda f: FOLLOW, halves[h], by_id, cfg)) for h in "AB"}
    for name, pol in rule_policies().items():
        rows.append({"policy": name, "family": name.split(":")[0].split(" (")[0],
                     "A": metrics(outcomes(pol, halves["A"], by_id, cfg)), "B": metrics(outcomes(pol, halves["B"], by_id, cfg))})
    # learned combiners: half-A numbers from 2-fold cross-fitting inside A, half-B numbers from a fit on all of A
    a_folds = [[f for f in halves["A"] if int(hashlib.sha1(f.case_id.encode()).hexdigest()[8:16], 16) % 2 == k] for k in (0, 1)]
    for kind, (set_name, names), (lo, hi) in itertools.product(("logistic", "boosted trees"), LEARNED_SETS.items(), BANDS):
        name = f"learned {kind} ({set_name}), present >= {hi}, absent < {lo}"
        cross = []
        for k in (0, 1):
            prob = fit_combiner(kind, names, a_folds[1 - k], by_id)
            cross += outcomes(banded(prob, lo, hi), a_folds[k], by_id, cfg)
        prob_all = fit_combiner(kind, names, halves["A"], by_id)
        rows.append({"policy": name, "family": f"learned {kind}", "A": metrics(cross),
                     "B": metrics(outcomes(banded(prob_all, lo, hi), halves["B"], by_id, cfg))})
    for r in rows:
        r["pass_A"], r["pass_B"] = passes(r["A"], base["A"]), passes(r["B"], base["B"])
        p = r["policy"]
        r["uses_verifier"] = (("verifier" in p and "no verifier" not in p) or p.startswith("vote")
                              or (p.startswith("learned") and "no verifier" not in p and "direct + specialist" not in p))
    rows.sort(key=lambda r: -(r["A"]["net_utility"] if r["A"]["net_utility"] == r["A"]["net_utility"] else -9))
    return [{"policy": "baseline", "A": base["A"], "B": base["B"], "pass_A": False, "pass_B": False,
             "family": "baseline", "uses_verifier": False}] + rows


def report_md(rows: list[dict]) -> str:
    base = rows[0]
    n = len(rows) - 1
    passed_a = [r for r in rows[1:] if r["pass_A"]]
    passed_both = [r for r in passed_a if r["pass_B"]]
    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    out = ["# Screening stage A: decision policies on stored reports (validation set only)", "",
           f"{n} policies screened. Pass rule (fixed before the screen): against keeping the direct reader, net utility "
           f"+{RULE['net_utility']} or more **and** ESG +{RULE['esg']} or more, CCR not lower by more than {RULE['ccr_drop']}, "
           f"claims on lesion-free images not higher by more than {RULE['healthy_rise']}; picked on half A, confirmed on half B.", "",
           f"**{len(passed_a)} pass on half A; {len(passed_both)} also pass on half B (shortlist).**", "",
           "Caution: the validation erasures were made with LaMa, the verifier's own tool, so policies that use the "
           "verifier (marked V) must also hold on held-out-tool erasures before they are trusted.", "",
           "| Policy | V | A: utility | A: ESG | A: erased claims | A: CCR | B: utility | B: ESG | B: erased claims | B: CCR | Pass A | Pass B |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    show = [base] + passed_both + [r for r in rows[1:] if r not in passed_both][:25]
    for r in show:
        a, b = r["A"], r["B"]
        out.append(f"| {r['policy']} | {'V' if r['uses_verifier'] else ''} | {f(a['net_utility'])} | {f(a['esg'])} | "
                   f"{f(a['target_hallucination_rate'])} | {f(a['ccr'])} | {f(b['net_utility'])} | {f(b['esg'])} | "
                   f"{f(b['target_hallucination_rate'])} | {f(b['ccr'])} | {'yes' if r['pass_A'] else ''} | {'yes' if r['pass_B'] else ''} |")
    best_esg = max(rows[1:], key=lambda r: (r["B"]["esg"] if r["B"]["esg"] == r["B"]["esg"] else -9))
    out += ["", f"Largest ESG on half B among all policies: {f(best_esg['B']['esg'])} ({best_esg['policy']}); "
                f"baseline {f(base['B']['esg'])}."]
    return "\n".join(out) + "\n"
