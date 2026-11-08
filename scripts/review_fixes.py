"""Analyses requested by the v0.16 review (docs/reviews/), from stored per-view outcomes; no model is run.

A. Overlap exclusion: every fresh-external run with and without the one image shared with the validation set
   (case siimext00119_ptx), plus SIIM-only denominators.
B. Errors by asked finding: false claims on erased lesions, misses on unedited lesions, referrals, healthy-image
   claims, for the named runs; so deferral cannot hide misses.
C. Error versus coverage: selective risk at fixed coverage (100 / 90 / 80 / 70 %) ranked by stated confidence, for
   the named runs; the AURC is already in each run's summary.
D. Crosswalk coverage: distinct image files behind the main-test cases (why 491 files for 507 cases).

    python scripts/review_fixes.py --results RESULTS --views TEST_VIEWS... --ext2-views EXT2_VIEWS... \\
        --runs v4_final_test v2_gpt6astra_test v2_claudeopus_test v2_gemini_test \\
        --ext2-runs v4_final_ext2 v2_gpt6astra_ext2 v2_claudeopus_ext2 v2_gemini_ext2 --out RESULTS/review_v016.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.actions import asked_finding  # noqa: E402
from medscope.eval.compare import load_outcomes  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

SHARED_CASE = "siimext00119_ptx"
KEYS = ("ccr", "esg", "target_hallucination_rate", "random_denial_rate", "natural_hallucination_rate", "net_utility")
LABEL = {"ccr": "CCR", "esg": "ESG", "target_hallucination_rate": "Erased claims", "random_denial_rate": "Control denial",
         "natural_hallucination_rate": "Healthy claims", "net_utility": "Net utility"}


def f(x):
    return "-" if x is None or x != x else f"{x:.3f}"


def metrics_row(outs):
    return [METRICS[k](outs) if outs else None for k in KEYS]


def section_a(R: Path, runs: list[str]) -> list[str]:
    out = ["## A. Fresh external with and without the image shared with the validation set", "",
           f"Case `{SHARED_CASE}` (a SIIM-ACR pneumothorax film that is also a ChestX-Det 'no finding' validation image) is "
           "removed; SIIM-only rows give the denominators behind the pneumothorax result.", "",
           "| Run | Cases | " + " | ".join(LABEL[k] for k in KEYS) + " |", "| --- | --- | " + " | ".join("---" for _ in KEYS) + " |"]
    for r in runs:
        if not (R / r).exists():
            out.append(f"| {r} | (no results) | " + " | ".join("" for _ in KEYS) + " |")
            continue
        outs = load_outcomes(R / r)
        cases = {o.case_id for o in outs}
        excl = [o for o in outs if o.case_id != SHARED_CASE]
        siim = [o for o in outs if o.case_id.startswith("siimext")]
        siim_x = [o for o in siim if o.case_id != SHARED_CASE]
        out.append(f"| {r}, all | {len(cases)} | " + " | ".join(f(x) for x in metrics_row(outs)) + " |")
        out.append(f"| {r}, shared image excluded | {len({o.case_id for o in excl})} | " + " | ".join(f(x) for x in metrics_row(excl)) + " |")
        out.append(f"| {r}, SIIM only | {len({o.case_id for o in siim})} | " + " | ".join(f(x) for x in metrics_row(siim)) + " |")
        out.append(f"| {r}, SIIM only, excluded | {len({o.case_id for o in siim_x})} | " + " | ".join(f(x) for x in metrics_row(siim_x)) + " |")
        pos = [o for o in siim if o.kind == "original"]
        det = sum(1 for o in pos if o.action == "answer" and o.correct)
        out.append(f"| {r}, SIIM unedited positives detected | {det}/{len(pos)} | " + " | ".join("" for _ in KEYS) + " |")
    return out + [""]


def section_b(R: Path, runs: list[str], views: dict, title: str) -> list[str]:
    out = [f"## B. Errors by asked finding: {title}", "",
           "False claim = still claims the finding after erasure; miss = denies or refers on an unedited lesion image; "
           "healthy claim = claims the finding on a lesion-free image. Referrals counted separately so deferral is visible.", ""]
    for r in runs:
        if not (R / r).exists():
            continue
        outs = load_outcomes(R / r)
        tab = defaultdict(lambda: {"n_orig": 0, "miss": 0, "refer_orig": 0, "n_erased": 0, "false": 0, "refer_erased": 0,
                                   "n_neg": 0, "healthy": 0, "refer_neg": 0})
        for o in outs:
            v = views.get(o.view_id)
            fnd = (asked_finding(v.question) if v else None) or "other"
            t = tab[fnd]
            if o.kind == "original":
                t["n_orig"] += 1
                t["miss"] += not (o.action == "answer" and o.correct)
                t["refer_orig"] += o.action == "refer"
            elif o.kind == "target_removal":
                t["n_erased"] += 1
                t["false"] += o.action == "answer" and not o.correct
                t["refer_erased"] += o.action == "refer"
            elif o.kind == "natural_negative":
                t["n_neg"] += 1
                t["healthy"] += o.action == "answer" and not o.correct
                t["refer_neg"] += o.action == "refer"
        out += [f"**{r}**", "", "| Finding | Unedited (n) | Misses | Referrals | Erased (n) | False claims | Referrals | Lesion-free (n) | Healthy claims | Referrals |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for fnd, t in sorted(tab.items(), key=lambda kv: -(kv[1]["n_orig"] + kv[1]["n_neg"])):
            pct = lambda a, n: f"{a} ({100 * a / n:.0f}%)" if n else "-"  # noqa: E731
            out.append(f"| {fnd} | {t['n_orig']} | {pct(t['miss'], t['n_orig'])} | {t['refer_orig']} | {t['n_erased']} | "
                       f"{pct(t['false'], t['n_erased'])} | {t['refer_erased']} | {t['n_neg']} | {pct(t['healthy'], t['n_neg'])} | {t['refer_neg']} |")
        out.append("")
    return out


def section_c(R: Path, runs: list[str], title: str) -> list[str]:
    out = [f"## C. Error at fixed coverage (stated confidence): {title}", "",
           "Answerable views (unedited lesion and control-edit images) ranked by stated confidence; non-answers count as "
           "confidence 0 and as errors when covered. Risk = error rate among the covered share.", "",
           "| Run | AURC | Risk @100% | @90% | @80% | @70% | Referral share |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in runs:
        if not (R / r).exists():
            continue
        outs = load_outcomes(R / r)
        items = [o for o in outs if o.kind in ("original", "random_removal")]
        if not items or any(o.action == "answer" and o.confidence is None for o in items):
            out.append(f"| {r} | (no confidence recorded) | | | | | |")
            continue
        conf = np.array([o.confidence if o.action == "answer" else 0.0 for o in items])
        err = np.array([0.0 if (o.action == "answer" and o.correct) else 1.0 for o in items])
        order = np.argsort(-conf, kind="stable")
        risks = np.cumsum(err[order]) / np.arange(1, len(items) + 1)
        at = lambda c: f"{risks[max(0, int(round(c * len(items))) - 1)]:.3f}"  # noqa: E731
        refer = np.mean([o.action == "refer" for o in items])
        out.append(f"| {r} | {METRICS['aurc'](outs):.3f} | {at(1.0)} | {at(0.9)} | {at(0.8)} | {at(0.7)} | {refer:.3f} |")
    return out + [""]


def section_d(views_files: list[str]) -> list[str]:
    views = [v for fp in views_files for v in load_views(fp)]
    cases = {v.case_id for v in views}
    orig = {v.case_id: v.image_path for v in views if v.kind.value in ("original", "natural_negative")}
    files = defaultdict(set)
    for c, p in orig.items():
        files[Path(p).name].add(c)
    shared = {k: sorted(v) for k, v in files.items() if len(v) > 1}
    out = ["## D. Crosswalk coverage of the main test", "",
           f"{len(cases)} cases; {len(orig)} with an unedited image; {len(files)} distinct image files. "
           f"{len(shared)} files carry more than one case (several questions on one image), accounting for the difference.", ""]
    for k, cs in sorted(shared.items())[:40]:
        out.append(f"- `{k}`: {', '.join(cs)}")
    return out + [""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True, help="main-test views files (with negatives)")
    ap.add_argument("--ext2-views", nargs="+", required=True, help="fresh-external views files (with negatives)")
    ap.add_argument("--runs", nargs="+", required=True, help="main-test runs for sections B and C")
    ap.add_argument("--ext2-runs", nargs="+", required=True, help="fresh-external runs for sections A, B and C")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    R = Path(args.results)
    test_views = {v.view_id: v for fp in args.views for v in load_views(fp)}
    ext2_views = {v.view_id: v for fp in args.ext2_views for v in load_views(fp)}
    out = ["# Analyses for the v0.16 review", ""]
    out += section_a(R, args.ext2_runs)
    out += section_b(R, args.runs, test_views, "main test")
    out += section_b(R, args.ext2_runs, ext2_views, "fresh external")
    out += section_c(R, args.runs, "main test")
    out += section_c(R, args.ext2_runs, "fresh external")
    out += section_d(args.views)
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
