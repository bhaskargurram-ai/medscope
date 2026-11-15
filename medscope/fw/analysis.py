"""Framework stage 0 analysis (docs/FRAMEWORK_STAGE0.md): the decision tree, from the stored scores (CPU only).

Quantities, per model and tool (LaMa = the training tool, TELEA = held out), on the validation dev cases:

  denial(v)      share of views of variant v with s < 0 (the model prefers the 'absent' reply), among cases whose
                 unedited view it scores present (s(original) > 0), so perception misses do not enter
  site effect    denial(ring) - denial(original): does an edit right next to the lesion, lesion intact, make it say absent?
  far effect     denial(control) - denial(original): the same for the benchmark's control edit elsewhere
  ESG_far        P(s<0 | erased) - P(s<0 | control)      all cases (the benchmark's score, single-turn form)
  ESG_site       P(s<0 | erased) - P(s<0 | ring)         same tool, same site: only the lesion differs
  AUROC          of s for erased vs control, erased vs ring, erased vs restored (threshold-free discrimination)
  probes         logistic regression on hidden features (5-fold, grouped by case): erased vs ring trained on LaMa,
                 tested on TELEA, per layer; and ring vs original (can the model's features see the site edit?)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import numpy as np

SITE_SHORTCUT = 0.10       # site effect of the recipe at least this ...
OVER_FAR = 0.05            # ... and this much above its far effect ...
OVER_BASE = 0.05           # ... and this much above the untrained model's site effect
READOUT_GAP = 0.05         # best probe AUROC above the output's AUROC by at least this
MIN_AGREE = 0.80           # s(x) sign must agree with the agent's own answers this often for the score to stand


def auroc(pos: np.ndarray, neg: np.ndarray) -> float:
    """P(score of a positive > score of a negative), ties half."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    rp = ranks[:len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def table(scores: dict[str, dict]) -> dict[str, dict]:
    """case_id -> {'original': s, 'negative': s, 'lama/erased': s, 'telea/ring': s, ...}"""
    out: dict[str, dict] = {}
    for r in scores.values():
        key = r["variant"] if r["tool"] is None else f"{r['tool']}/{r['variant']}"
        out.setdefault(r["case_id"], {})[key] = r["s"]
    return out


def bootstrap_ci(values: list[tuple], stat, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    if not values:
        return float("nan"), float("nan")
    idx = np.arange(len(values))
    bs = []
    for _ in range(n):
        s = stat([values[i] for i in rng.choice(idx, len(idx))])
        if s == s:
            bs.append(s)
    return (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))) if bs else (float("nan"), float("nan"))


def model_summary(scores: dict[str, dict]) -> dict:
    t = table(scores)
    res: dict = {"n_cases": sum("original" in d for d in t.values()),
                 "neg_denial": float(np.mean([d["negative"] < 0 for d in t.values() if "negative" in d]))
                 if any("negative" in d for d in t.values()) else float("nan")}
    lesion = {c: d for c, d in t.items() if "original" in d}
    res["found"] = float(np.mean([d["original"] > 0 for d in lesion.values()])) if lesion else float("nan")
    for tool in ("lama", "telea"):
        r: dict = {}
        found = [d for d in lesion.values() if d["original"] > 0 and f"{tool}/erased" in d]
        for v in ("erased", "control", "ring", "restored", "partial"):
            k = f"{tool}/{v}"
            xs = [d[k] < 0 for d in found if k in d]
            r[f"denial_{v}"] = float(np.mean(xs)) if xs else float("nan")
            r[f"n_{v}"] = len(xs)
        r["denial_original"] = 0.0
        pairs_site = [(d[f"{tool}/ring"] < 0) for d in found if f"{tool}/ring" in d]
        pairs_far = [(d[f"{tool}/control"] < 0) for d in found if f"{tool}/control" in d]
        r["site_effect"] = float(np.mean(pairs_site)) if pairs_site else float("nan")
        r["far_effect"] = float(np.mean(pairs_far)) if pairs_far else float("nan")
        both = [(d[f"{tool}/ring"] < 0, d[f"{tool}/control"] < 0) for d in found
                if f"{tool}/ring" in d and f"{tool}/control" in d]
        r["site_minus_far"] = float(np.mean([a - b for a, b in both])) if both else float("nan")
        r["site_minus_far_ci"] = bootstrap_ci(both, lambda xs: float(np.mean([a - b for a, b in xs])))
        allc = [d for d in lesion.values() if f"{tool}/erased" in d]
        trip = [(d[f"{tool}/erased"], d.get(f"{tool}/control"), d.get(f"{tool}/ring")) for d in allc]
        far = [(e < 0) - (c < 0) for e, c, _ in trip if c is not None]
        site = [(e < 0) - (g < 0) for e, _, g in trip if g is not None]
        r["esg_far"] = float(np.mean(far)) if far else float("nan")
        r["esg_site"] = float(np.mean(site)) if site else float("nan")
        r["auroc_far"] = auroc([c for _, c, _ in trip if c is not None], [e for e, c, _ in trip if c is not None])
        r["auroc_site"] = auroc([g for _, _, g in trip if g is not None], [e for e, _, g in trip if g is not None])
        rest = [(d[f"{tool}/restored"], d[f"{tool}/erased"]) for d in allc if f"{tool}/restored" in d]
        r["auroc_restored"] = auroc([a for a, _ in rest], [b for _, b in rest])
        part = [(d["original"], d[f"{tool}/partial"], d[f"{tool}/erased"]) for d in allc if f"{tool}/partial" in d]
        r["graded_order"] = float(np.mean([o > p > e for o, p, e in part])) if part else float("nan")
        r["mean_s"] = {v: float(np.mean([d[f"{tool}/{v}"] for d in allc if f"{tool}/{v}" in d]))
                       if any(f"{tool}/{v}" in d for d in allc) else float("nan")
                       for v in ("erased", "control", "ring", "restored", "partial")}
        res[tool] = r
    res["mean_s_original"] = float(np.mean([d["original"] for d in lesion.values()])) if lesion else float("nan")
    return res


# ---- agreement of the single-turn score with the agent's own answers ---------------------------------------------------

def agreement(scores: dict[str, dict], probes: dict[str, dict], views: dict) -> tuple[float, int]:
    """Share of dev views where sign(s) matches the recipe's agent answer from screening stage B (probes.jsonl
    'direct'; refer/clarify answers are skipped)."""
    from ..screen.stage_a import says_present
    hits = []
    for vid, r in scores.items():
        p = probes.get(vid)
        v = views.get(vid)
        if not p or v is None:
            continue
        sp = says_present(p.get("direct") or {}, v.question)
        if sp is None:
            continue
        hits.append((r["s"] > 0) == bool(sp))
    return (float(np.mean(hits)) if hits else float("nan")), len(hits)


# ---- linear probes on hidden features ----------------------------------------------------------------------------------

def _fold(case_id: str, k: int = 5) -> int:
    return int(hashlib.sha1(case_id.encode()).hexdigest()[:8], 16) % k


def probe_oof(feats: dict[str, np.ndarray], scores: dict[str, dict], pos_key: str, neg_key: str,
              train_tool: str, test_tool: str, layer: int, which: int, k: int = 5) -> dict:
    """Out-of-fold probe outputs. Train on (pos, neg) views of train_tool, test on test_tool, 5-fold grouped by case
    (a case is never in both). Returns per test view: case id, label, probability, and a hard call made with the
    threshold that maximises TPR - FPR on that fold's *training* predictions (so the call is out of sample).
    pos_key/neg_key are variants ('ring', 'erased', 'control', 'original'); 'original' has no tool."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def rows(tool, key):
        out = []
        for vid, r in scores.items():
            t_ok = (r["tool"] == tool) if key != "original" else r["tool"] is None
            if r["variant"] == key and t_ok and vid in feats:
                out.append((r["case_id"], feats[vid][layer, which].astype(np.float32)))
        return out
    tr = [(c, x, 1) for c, x in rows(train_tool, pos_key)] + [(c, x, 0) for c, x in rows(train_tool, neg_key)]
    te = [(c, x, 1) for c, x in rows(test_tool, pos_key)] + [(c, x, 0) for c, x in rows(test_tool, neg_key)]
    res = {"case": [], "y": [], "p": [], "call": []}
    if len({y for _, _, y in tr}) < 2 or len({y for _, _, y in te}) < 2:
        return res
    for f in range(k):
        a = [(x, y) for c, x, y in tr if _fold(c, k) != f]
        b = [(c, x, y) for c, x, y in te if _fold(c, k) == f]
        if not b or len({y for _, y in a}) < 2:
            continue
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=3000))
        xa, ya = np.stack([x for x, _ in a]), np.array([y for _, y in a])
        m.fit(xa, ya)
        thr = youden_threshold(m.predict_proba(xa)[:, 1], ya)
        p = m.predict_proba(np.stack([x for _, x, _ in b]))[:, 1]
        res["case"] += [c for c, _, _ in b]
        res["y"] += [y for _, _, y in b]
        res["p"] += [float(v) for v in p]
        res["call"] += [int(v >= thr) for v in p]
    return res


def youden_threshold(p: np.ndarray, y: np.ndarray) -> float:
    """Threshold t maximising P(p >= t | y=1) - P(p >= t | y=0) on these (training) predictions."""
    p, y = np.asarray(p, float), np.asarray(y, int)
    best, thr = -np.inf, 0.5
    for t in np.unique(p):
        j = (p[y == 1] >= t).mean() - (p[y == 0] >= t).mean()
        if j > best:
            best, thr = j, float(t)
    return thr


def probe_auroc(feats: dict[str, np.ndarray], scores: dict[str, dict], pos_key: str, neg_key: str,
                train_tool: str, test_tool: str, layer: int, which: int, k: int = 5) -> float:
    r = probe_oof(feats, scores, pos_key, neg_key, train_tool, test_tool, layer, which, k)
    y, p = np.asarray(r["y"]), np.asarray(r["p"])
    return auroc(p[y == 1], p[y == 0]) if len(y) else float("nan")


# ---- the abstention ceiling, measured: a lower bound on the total-variation distance --------------------------------
#
# Proposition 1: for any decision D computed from signals S, |P(D | erased) - P(D | ring)| <= TV(S | erased, S | ring).
# Any fixed event A gives TV >= |P(A | erased) - P(A | ring)|. The out-of-sample hard call of a probe is such an event
# (its threshold was chosen on other cases), so its TPR - FPR estimates a lower bound on TV for the hidden states.
# Comparing it with the model's own denial gap (its ESG against the ring, from the generated answers) shows how much
# of the separation that is linearly available in the hidden states the answers use.

def tv_lower_bound(res: dict, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float, int]:
    """TPR - FPR of the out-of-fold hard calls, with a case-bootstrap 95% interval; returns (j, lo, hi, n_cases)."""
    if not res["y"]:
        return float("nan"), float("nan"), float("nan"), 0
    by: dict[str, list[tuple[int, int]]] = {}
    for c, y, call in zip(res["case"], res["y"], res["call"]):
        by.setdefault(c, []).append((y, call))
    cases = sorted(by)

    def j(sample):
        pos = [call for c in sample for y, call in by[c] if y == 1]
        neg = [call for c in sample for y, call in by[c] if y == 0]
        return (np.mean(pos) - np.mean(neg)) if pos and neg else np.nan
    point = float(j(cases))
    rng = np.random.default_rng(seed)
    bs = [j([cases[i] for i in rng.integers(0, len(cases), len(cases))]) for _ in range(n_boot)]
    bs = [b for b in bs if b == b]
    return point, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(cases)


def tv_summary(feats: dict[str, np.ndarray], scores: dict[str, dict], n_layers: int,
               pairs: tuple = (("erased_vs_ring", "erased", "ring"), ("erased_vs_control", "erased", "control"))) -> dict:
    """Per pair, test tool and token: TV lower bound by layer and at the best layer (chosen by the bound itself, so
    the best-layer value is mildly optimistic; every layer is reported)."""
    out = {}
    for name, pos, neg in pairs:
        for test in ("lama", "telea"):
            for which, wname in ((0, "last"), (1, "image")):
                per = [tv_lower_bound(probe_oof(feats, scores, pos, neg, "lama", test, layer, which))
                       for layer in range(n_layers)]
                best = max(range(n_layers), key=lambda i: per[i][0] if per[i][0] == per[i][0] else -1)
                out[f"{name}/{test}/{wname}"] = {"by_layer": per, "best_layer": best, "best": per[best]}
    return out


def answer_gap(answers: dict[str, dict], tool: str, neg: str = "ring") -> tuple[float, float, float, int]:
    """The model's own denial gap P(denied | erased) - P(denied | neg) over cases with both views (all cases, as the
    probe uses all cases), with a case-bootstrap 95% interval. `answers` as from stage0.read_answers/table."""
    t = table(answers)
    e, g = f"{tool}/erased", f"{tool}/{neg}"
    cases = [c for c in t if e in t[c] and g in t[c]]
    if not cases:
        return float("nan"), float("nan"), float("nan"), 0
    d = np.array([float(t[c][e] < 0) - float(t[c][g] < 0) for c in cases])
    rng = np.random.default_rng(0)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(cases)


def tv_report(tv: dict, gaps: dict[str, tuple], n_layers: int) -> str:
    f = lambda x: "-" if x != x else f"{x:.3f}"  # noqa: E731
    lines = ["# The abstention ceiling, measured", "",
             "Proposition 1: any decision computed from signals S has a denial gap (ESG) at most TV(S | erased, S | "
             "other view). An out-of-sample linear probe on the hidden states gives a **lower bound** on that TV "
             "(its hard call is one fixed event). If the model's own denial gap is close to the bound, its answers "
             "already use about as much separation as the hidden states linearly hold; a large shortfall would be a "
             "read-out gap. The true TV can be higher than any linear bound.", "",
             "| Pair | Test tool | Token | TV lower bound, best layer [95% CI] (layer) | Model's denial gap [95% CI] | "
             "Bound minus gap |", "| --- | --- | --- | --- | --- | --- |"]
    for key, r in tv.items():
        name, test, which = key.split("/")
        j, lo, hi, n = r["best"]
        neg = "ring" if name == "erased_vs_ring" else "control"
        g = gaps.get(f"{test}/{neg}", (float("nan"),) * 4)
        lines.append(f"| {name.replace('_', ' ')} | {test} | {which} | {f(j)} [{f(lo)}, {f(hi)}] (layer {r['best_layer']}, "
                     f"{n} cases) | {f(g[0])} [{f(g[1])}, {f(g[2])}] ({g[3]} cases) | {f(j - g[0])} |")
    lines += ["", "By layer (TV lower bound, point estimates):", "",
              "| Pair / tool / token | " + " | ".join(str(i) for i in range(n_layers)) + " |",
              "| --- |" + " --- |" * n_layers]
    for key, r in tv.items():
        lines.append(f"| {key} | " + " | ".join(f(x[0]) for x in r["by_layer"]) + " |")
    return "\n".join(lines) + "\n"


def probe_summary(feats: dict[str, np.ndarray], scores: dict[str, dict], n_layers: int) -> dict:
    out = {}
    for name, (pos, neg) in {"erased_vs_ring": ("ring", "erased"), "erased_vs_control": ("control", "erased"),
                             "ring_vs_original": ("original", "ring")}.items():
        for test in ("lama", "telea"):
            for which, wname in ((0, "last"), (1, "image")):
                out[f"{name}/{test}/{wname}"] = [probe_auroc(feats, scores, pos, neg, "lama", test, layer, which)
                                                 for layer in range(n_layers)]
    return out


def load_feats(hidden_dir: str | Path) -> dict[str, np.ndarray]:
    d = Path(hidden_dir)
    return {p.stem: np.load(p) for p in sorted(d.glob("*.npy"))} if d.exists() else {}


# ---- the decision tree ---------------------------------------------------------------------------------------------

def decide(summ: dict[str, dict], probes: Optional[dict], agree: float, recipe: str = "recipe",
           base: str = "base") -> dict:
    """The pre-registered reading (docs/FRAMEWORK_STAGE0.md)."""
    r, b = summ[recipe], summ.get(base)
    out = {"score_valid": bool(agree == agree and agree >= MIN_AGREE), "agreement": agree}
    site, missing = {}, []
    for tool in ("lama", "telea"):
        rt = r[tool]
        bt = b[tool] if b else None
        first = rt["site_effect"] >= SITE_SHORTCUT and rt["site_minus_far"] >= OVER_FAR
        if first and (bt is None or bt["site_effect"] != bt["site_effect"]):
            missing.append(tool)                 # the comparison with the base model cannot be made yet
        site[tool] = bool(first and bt is not None and rt["site_effect"] - bt["site_effect"] >= OVER_BASE)
    out["site_shortcut"] = site
    out["missing_base"] = missing
    out["site_shortcut_any"] = any(site.values())
    gap = {}
    if probes:
        for which in ("last", "image"):
            curve = probes.get(f"erased_vs_ring/telea/{which}") or []
            best = max([x for x in curve if x == x], default=float("nan"))
            gap[which] = {"best_probe": best, "output": r["telea"]["auroc_site"],
                          "gap": best - r["telea"]["auroc_site"] if best == best else float("nan")}
    out["readout"] = gap
    out["readout_gap"] = any(g["gap"] >= READOUT_GAP for g in gap.values() if g["gap"] == g["gap"])
    s, g = out["site_shortcut_any"], out["readout_gap"]
    out["branch"] = ("A+B: footprint-balanced training with an evidence read-out" if s and g else
                     "A: footprint-balanced counterfactual training" if s else
                     "B: evidence read-out from internal features" if g else
                     "C: perception-limited; the gap is in what the model sees")
    if missing and not out["site_shortcut_any"]:
        out["branch"] = (f"undecided: the base model's answers on the ring views are missing ({', '.join(missing)}); "
                         "the rule cannot be applied until they are in")
    if not out["score_valid"]:
        out["branch"] = "invalid: the single-turn score does not track the agent's answers; rerun with generation"
    return out


def report(summ: dict[str, dict], probes: Optional[dict], decision: dict) -> str:
    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    lines = ["# Framework stage 0: where does the evidence sensitivity come from? (validation dev set)", "",
             f"Single-turn score agrees with the recipe's agent answers on {f(decision['agreement'])} of dev views "
             f"(needs {MIN_AGREE}); score {'valid' if decision['score_valid'] else 'NOT valid'}.", "",
             f"**Branch: {decision['branch']}**", "",
             "Denial = share scored 'absent' among cases whose unedited image the model scores 'present'.", "",
             "| Model | tool | found | denial: control (far) | ring (same site, lesion kept) | restored | partial | erased | "
             "site - far [95% CI] | ESG far | ESG site | AUROC far | AUROC site | AUROC restored | graded order |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m, s in summ.items():
        for tool in ("lama", "telea"):
            t = s[tool]
            lo, hi = t["site_minus_far_ci"]
            lines.append(f"| {m} | {tool} | {f(s['found'])} | {f(t['denial_control'])} | {f(t['denial_ring'])} | "
                         f"{f(t['denial_restored'])} | {f(t['denial_partial'])} | {f(t['denial_erased'])} | "
                         f"{f(t['site_minus_far'])} [{f(lo)}, {f(hi)}] | {f(t['esg_far'])} | {f(t['esg_site'])} | "
                         f"{f(t['auroc_far'])} | {f(t['auroc_site'])} | {f(t['auroc_restored'])} | {f(t['graded_order'])} |")
    lines += ["", "Lesion-free images scored 'absent': " + ", ".join(f"{m} {f(s['neg_denial'])}" for m, s in summ.items()), ""]
    lines.append("Site shortcut (rule: recipe site effect >= 0.10, >= 0.05 above its far effect and above the base "
                 "model's): " + ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in decision["site_shortcut"].items()))
    if probes:
        lines += ["", "## Linear probes on the recipe's hidden features (trained on LaMa views, 5-fold by case)", "",
                  "| Probe | test tool | features | AUROC per layer | best |", "| --- | --- | --- | --- | --- |"]
        for k, curve in probes.items():
            name, tool, which = k.split("/")
            best = max([x for x in curve if x == x], default=float("nan"))
            lines.append(f"| {name} | {tool} | {which} | {' '.join(f(x) for x in curve)} | {f(best)} |")
        for which, g in decision["readout"].items():
            lines.append(f"\nRead-out gap ({which} features, TELEA erased vs ring): best probe {f(g['best_probe'])} vs "
                         f"output {f(g['output'])} -> gap {f(g['gap'])} (rule: >= {READOUT_GAP}).")
    return "\n".join(lines) + "\n"


# ---- within-case differences of the single-turn score (descriptive; the reply text is identical within a case) -------

def within_case(scores: dict[str, dict]) -> dict:
    """Per tool and variant: mean of s(view) - s(original) over cases (bootstrap 95% interval) and as a share of the
    erasure's drop; paired concordance P(s(v) > s(erased)) within a case."""
    t = table(scores)
    out: dict = {}
    for tool in ("lama", "telea"):
        cases = [d for d in t.values() if "original" in d and f"{tool}/erased" in d]
        drop_e = [d[f"{tool}/erased"] - d["original"] for d in cases]
        me = float(np.mean(drop_e)) if drop_e else float("nan")
        r: dict = {"n": len(cases), "erased_drop": me}
        for v in ("control", "ring", "restored", "partial"):
            k = f"{tool}/{v}"
            ds = [d[k] - d["original"] for d in cases if k in d]
            if not ds:
                continue
            m = float(np.mean(ds))
            lo, hi = bootstrap_ci([(x,) for x in ds], lambda xs: float(np.mean([x[0] for x in xs])))
            conc = float(np.mean([d[k] > d[f"{tool}/erased"] for d in cases if k in d]))
            r[v] = {"drop": m, "ci": (lo, hi), "share_of_erasure": m / me if me else float("nan"), "above_erased": conc}
        pairs = [(d[f"{tool}/ring"] - d["original"], d[f"{tool}/control"] - d["original"]) for d in cases
                 if f"{tool}/ring" in d and f"{tool}/control" in d]
        if pairs:
            diff = [a - b for a, b in pairs]
            r["ring_minus_control"] = {"mean": float(np.mean(diff)),
                                       "ci": bootstrap_ci([(x,) for x in diff], lambda xs: float(np.mean([x[0] for x in xs])))}
        out[tool] = r
    return out


def within_report(w: dict[str, dict]) -> str:
    f = lambda x: "-" if x is None or x != x else f"{x:.2f}"  # noqa: E731
    lines = ["## Descriptive: within-case changes of the single-turn score (not used for the decision)", "",
             "s(view) - s(original) in nats, same reply text within a case; 'share' = as a fraction of the erasure's "
             "drop; 'above erased' = share of cases where the view still scores higher than the erasure.", "",
             "| Model | tool | erasure drop | control | ring | restored | partial | ring - control [95% CI] | ring above erased |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m, by in w.items():
        for tool, r in by.items():
            cell = lambda v: (f"{f(r[v]['drop'])} ({f(r[v]['share_of_erasure'])})" if v in r else "-")  # noqa: E731
            rc = r.get("ring_minus_control")
            rcs = f"{f(rc['mean'])} [{f(rc['ci'][0])}, {f(rc['ci'][1])}]" if rc else "-"
            lines.append(f"| {m} | {tool} | {f(r['erased_drop'])} | {cell('control')} | {cell('ring')} | {cell('restored')} | "
                         f"{cell('partial')} | {rcs} | {f(r['ring']['above_erased']) if 'ring' in r else '-'} |")
    return "\n".join(lines) + "\n"
