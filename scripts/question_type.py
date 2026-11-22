"""Review check R20 (docs/REVIEW_EXPERIMENTS.md, Amendment 7): do the main results hold on finding-specific questions?

Every main-test case is put in one of two strata by its closed question: "finding-specific" (the question names a
finding, e.g. "Is there a polyp in this image?") or "generic" (it asks about an abnormality, or whether the image is
healthy or normal; the rule of scripts/freetext.py). Erasing one lesion mask does not make "an abnormality" absent, so
the erased-lesion label is safest on finding-specific questions. Stored answers only; nothing is run.

    python scripts/question_type.py --views TEST_VIEWS TEST_NEG --results RESULTS \
        --runs MedScope-4B=v4_final_test gemini-4-argon=v2_gemini_test ... --ref MedScope-4B --out FILE.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from edit_visibility import boot, case_esg  # noqa: E402
from freetext import GENERIC  # noqa: E402

STRATA = ("finding-specific", "generic")


def question_type(question: str) -> str:
    return "generic" if GENERIC.search(question or "") else "finding-specific"


def lesion_free_claims(rows: list[dict]) -> dict[str, float]:
    """case id -> 1.0 if the finding is claimed on an unedited lesion-free image, else 0.0."""
    return {r["case_id"]: float(r["action"] == "answer" and not r.get("correct"))
            for r in rows if r["kind"] == "natural_negative"}


def stratum_table(per_run: dict[str, list[dict]], cases: set[str], ref: str) -> list[str]:
    """Rows of the table for one set of cases (lesion cases and lesion-free cases mixed; each is used where it applies)."""
    per = {name: {c: v for c, v in case_esg(rows).items() if c in cases} for name, rows in per_run.items()}
    neg = {name: {c: v for c, v in lesion_free_claims(rows).items() if c in cases} for name, rows in per_run.items()}
    ref_esg = {c: v[0] - v[1] for c, v in per.get(ref, {}).items()}
    out = []
    for name in per_run:
        les, free = per[name], neg[name]
        if not les:
            out.append(f"| {name} | 0 | -- | -- | {len(free)} | -- | -- |")
            continue
        esg = {c: v[0] - v[1] for c, v in les.items()}
        e, lo, hi, _ = boot(esg)
        claims = float(np.mean([v[2] for v in les.values()]))
        fc = f"{np.mean(list(free.values())):.1%}" if free else "--"
        cmp = "--"
        if name != ref and ref_esg:
            common = ref_esg.keys() & esg.keys()
            if common:
                d, dlo, dhi, p = boot({c: ref_esg[c] - esg[c] for c in common})
                cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f} (n = {len(common)})"
        out.append(f"| {name} | {len(les)} | {e:.3f} [{lo:.3f}, {hi:.3f}] | {claims:.1%} | {len(free)} | {fc} | {cmp} |")
    return out


def report(views: list[dict], per_run: dict[str, list[dict]], ref: str) -> str:
    qtype = {v["case_id"]: question_type(v["question"]) for v in views}
    from medscope.colab import dataset_of
    modality = {v["case_id"]: dataset_of(v["case_id"]) for v in views}
    lesion_cases = {v["case_id"] for v in views if v["kind"] == "target_removal"}
    free_cases = {v["case_id"] for v in views if v["kind"] == "natural_negative"}
    count = Counter((qtype[c], "lesion") for c in lesion_cases) + Counter((qtype[c], "lesion-free") for c in free_cases)
    head = ["| Model | Lesion cases | ESG [95% CI] | Erased-lesion claims | Lesion-free cases | Lesion-free claims | "
            f"{ref} minus model, ESG [95% CI], p |", "| --- | --- | --- | --- | --- | --- | --- |"]
    lines = ["Main-test cases by question type: " + "; ".join(
        f"{s}: {count[(s, 'lesion')]} lesion and {count[(s, 'lesion-free')]} lesion-free" for s in STRATA) + ".", ""]
    by_mod = Counter((modality[c], qtype[c]) for c in lesion_cases)
    lines += ["Lesion cases by imaging type (finding-specific / generic): " + "; ".join(
        f"{m or 'unknown'} {by_mod[(m, STRATA[0])]} / {by_mod[(m, STRATA[1])]}" for m in sorted({m for m, _ in by_mod})) + ".", ""]
    for s in STRATA:
        cases = {c for c, q in qtype.items() if q == s}
        lines += [f"### {s.capitalize()} questions", ""] + head + stratum_table(per_run, cases, ref) + [""]
    for m in sorted({m for m, _ in by_mod}):
        for s in STRATA:
            cases = {c for c, q in qtype.items() if q == s and modality[c] == m}
            if sum(c in lesion_cases for c in cases) >= 10:
                lines += [f"### {m or 'unknown'}: {s} questions", ""] + head + stratum_table(per_run, cases, ref) + [""]
    lines += ["Question type: generic if the closed question matches 'abnormal', 'healthy' or 'normal', else "
              "finding-specific. ESG = erasure answered 'absent' or referred minus intact lesion denied or referred after "
              "the control edit of the same case; 2,000 resamples of cases; strata with fewer than 10 lesion cases per "
              "imaging type are not shown separately."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="name=run_dir_name (under --results)")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from medscope.eval.runner import read_jsonl, scored_rows
    views = [r for f in args.views for r in read_jsonl(Path(f))]
    per_run = {}
    for spec in args.runs:
        name, run = spec.split("=", 1)
        d = Path(args.results) / run
        if d.exists():
            per_run[name] = scored_rows(d)
        else:
            print(f"  {run}: not found, left out")
    text = report(views, per_run, args.ref)
    Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
