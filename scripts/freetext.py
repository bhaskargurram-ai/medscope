"""Review check R14 (docs/REVIEW_EXPERIMENTS.md, Amendment 5): is the effect tied to yes/no questions?

The same 150 main-test cases used for the robustness checks (select_cases, seed 0) are asked an open request instead
of the closed question, on the unedited lesion image and on its erasure: "Describe any abnormal findings in this
image." Cases whose closed question is generic ("an abnormality", "healthy", "normal") are left out, since there any
other finding makes a mention correct. Each model answers with the plain prompt (one reply, no tools). A text-only
judge, blind to the model and to which image was shown, reads each reply and says whether it reports the finding
named in the case's closed question.

    python scripts/freetext.py build --views TEST_VIEWS TEST_NEG --out DIR/views_freetext.jsonl
    python scripts/evaluate.py --prompt plain --views DIR/views_freetext.jsonl --out RESULTS/ft_<model> ...
    python scripts/freetext.py judge --views DIR/views_freetext.jsonl --results RESULTS \
        --runs MedScope-4B=ft_v4 gemini-4-argon=ft_gemini ... --ref MedScope-4B --out DIR
    -> DIR/judgments.jsonl (cached), DIR/freetext.md

Free-text ESG = share of unedited lesion images whose reply reports the finding minus the share of their erasures
whose reply still reports it (a model that always or never mentions it scores 0).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views, select_cases  # noqa: E402

OPEN_Q = "Describe any abnormal findings in this image."
GENERIC = re.compile(r"abnormal|healthy|normal", re.I)
JUDGE_SYSTEM = ("You read short replies from an assistant describing a medical image. You answer only 'yes' or 'no'.")
JUDGE_USER = ('Reply: """{reply}"""\n\nDoes this reply state that {finding} is present in the image? A reply that '
              'says it is absent, or does not mention it, means no. Answer yes or no.')


def finding_of(question: str) -> Optional[str]:
    """'Is there a polyp in this image?' -> 'a polyp'; None for generic questions."""
    if GENERIC.search(question):
        return None
    m = re.match(r"\s*(?:is|are) there (.+?)(?: (?:in|on|within|seen in|visible in) (?:this|the) .*)?\?\s*$", question, re.I) \
        or re.match(r"\s*(?:does|do) (?:the|this) (?:image|picture|scan|slice|x-ray)s? (?:contain|show) (.+?)\?\s*$", question, re.I)
    return m.group(1).strip() if m else None


def build(view_files: list[str], out: Path, limit_cases: int = 150) -> None:
    views = select_cases([v for f in view_files for v in load_views(f)], limit_cases, seed=0)
    rows, skipped = [], 0
    for v in views:
        if v.kind.value not in ("original", "target_removal"):
            continue
        f = finding_of(v.question)
        if f is None:
            skipped += 1
            continue
        d = v.to_dict()
        d["kind"] = v.kind.value
        d["view_id"] = v.view_id + "__freetext"
        d["meta"] = {**(v.meta or {}), "finding": f, "closed_question": v.question}
        d["question"] = OPEN_Q
        rows.append(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} views ({len({r['case_id'] for r in rows})} cases); {skipped} generic-question views left out")


def last_reply(turns: list[dict]) -> str:
    return next((t["content"] for t in reversed(turns) if t["role"] == "assistant"), "")


def parse_yes_no(text: str) -> Optional[bool]:
    t = text.strip().lower()
    m = re.search(r"\b(yes|no)\b", t)
    return None if m is None else m.group(1) == "yes"


def judge(view_file: Path, results: Path, runs: list[str], ref: str, out: Path, provider: str, model: str) -> None:
    from medscope.api_policy import api_policy
    views = {json.loads(l)["view_id"]: json.loads(l) for l in view_file.open()}
    out.mkdir(parents=True, exist_ok=True)
    cache_p = out / "judgments.jsonl"
    cache = {}
    if cache_p.exists():
        for l in cache_p.open():
            r = json.loads(l)
            cache[(r["run"], r["view_id"])] = r
    policy = api_policy(provider, model, workers=8)
    per = {}
    for spec in runs:
        name, run = spec.split("=", 1)
        tp = results / run / "transcripts.jsonl"
        if not tp.exists():
            print(f"  {run}: no transcripts, left out")
            continue
        todo, have = [], {}
        for l in tp.open():
            t = json.loads(l)
            if t["view_id"] not in views:
                continue
            key = (run, t["view_id"])
            if key in cache:
                have[t["view_id"]] = cache[key]["mentions"]
            else:
                todo.append((t["view_id"], last_reply(t["turns"])))
        convs = [[{"role": "system", "content": [{"type": "text", "text": JUDGE_SYSTEM}]},
                  {"role": "user", "content": [{"type": "text", "text": JUDGE_USER.format(
                      reply=reply[:4000], finding=views[vid]["meta"]["finding"])}]}] for vid, reply in todo]
        gens = policy.generate_batch(convs) if convs else []
        with cache_p.open("a") as f:
            for (vid, reply), g in zip(todo, gens):
                m = parse_yes_no(g.text)
                f.write(json.dumps({"run": run, "view_id": vid, "reply": reply[:2000], "judge": g.text[:200],
                                    "mentions": m}) + "\n")
                have[vid] = m
        per[name] = have
        print(f"  {name}: {len(have)} replies judged")
    text = report(per, views, ref, f"{provider} {model}")
    (out / "freetext.md").write_text(text)
    print(text)


def case_rows(judged: dict[str, Optional[bool]], views: dict[str, dict]) -> dict[str, tuple[float, float]]:
    by = defaultdict(dict)
    for vid, m in judged.items():
        if m is None:
            continue
        v = views[vid]
        by[v["case_id"]][v["kind"]] = float(m)
    return {c: (k["original"], k["target_removal"]) for c, k in by.items()
            if "original" in k and "target_removal" in k}


def boot(values: dict[str, float], n: int = 2000, seed: int = 0):
    keys = sorted(values)
    xs = np.array([values[k] for k in keys])
    rng = np.random.default_rng(seed)
    bs = [xs[rng.integers(0, len(xs), len(xs))].mean() for _ in range(n)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p = 2 * min(np.mean(np.array(bs) <= 0), np.mean(np.array(bs) >= 0))
    return float(xs.mean()), float(lo), float(hi), float(min(1.0, p))


def report(per: dict[str, dict], views: dict[str, dict], ref: str, judge_name: str) -> str:
    rows = {name: case_rows(j, views) for name, j in per.items()}
    lines = [f"| Model | Cases | Reports the finding: unedited | Reports it: erased | Free-text ESG [95% CI] | vs {ref}: "
             f"difference [95% CI], p |", "| --- | --- | --- | --- | --- | --- |"]
    for name, cases in rows.items():
        if not cases:
            continue
        esg = {c: o - e for c, (o, e) in cases.items()}
        e, lo, hi, _ = boot(esg)
        cmp = "--"
        if name != ref and ref in rows:
            common = rows[ref].keys() & cases.keys()
            d, dlo, dhi, p = boot({c: (rows[ref][c][0] - rows[ref][c][1]) - esg[c] for c in common})
            cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f} (n = {len(common)})"
        lines.append(f"| {name} | {len(cases)} | {np.mean([o for o, _ in cases.values()]):.1%} | "
                     f"{np.mean([x for _, x in cases.values()]):.1%} | {e:.3f} [{lo:.3f}, {hi:.3f}] | {cmp} |")
    lines += ["", f"Open request: \"{OPEN_Q}\" (plain prompt, one reply, no tools). Judge: {judge_name}, text only, blind "
              "to the model and the image. Bootstrap over cases (2,000)."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("build")
    a.add_argument("--views", nargs="+", required=True)
    a.add_argument("--limit-cases", type=int, default=150)
    a.add_argument("--out", required=True)
    a = sub.add_parser("judge")
    a.add_argument("--views", required=True)
    a.add_argument("--results", required=True)
    a.add_argument("--runs", nargs="+", required=True)
    a.add_argument("--ref", required=True)
    a.add_argument("--judge-provider", default="openai")
    a.add_argument("--judge-model", default="gpt-6-astra")
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.views, Path(args.out), args.limit_cases)
    else:
        judge(Path(args.views), Path(args.results), args.runs, args.ref, Path(args.out), args.judge_provider,
              args.judge_model)


if __name__ == "__main__":
    main()
