"""Spot-check of the "healthy" labels: show the lesion-free test images that most models say are abnormal,
so a person can flag labels that are plainly wrong, then re-run the main comparison without them.

  1. python scripts/label_check.py make --views TEST_NEG... --results RESULTS --runs RUN... --out RESULTS/label_check
     -> label_check.png (numbered grid) and label_check.json (the ids shown)
  2. write the numbers of plainly wrong labels into RESULTS/label_check/wrong_labels.json, e.g. [3, 11]
  3. python scripts/label_check.py apply --results RESULTS --runs RUN... --ref v2_medscope3_test --out RESULTS/label_check
     -> sensitivity.md: every metric with and without the flagged cases, and the paired tests again

This is a check of dataset labels, not clinical annotation: it only removes cases whose label is visibly wrong.

Automatic alternative with no human in the loop:
     python scripts/label_check.py consensus --views TEST_NEG... --results RESULTS --judges FRONTIER_RUNS... \
         --min-votes 7 --runs RUN... --ref v2_medscope3_test --out RESULTS/label_check
     -> lesion-free images that at least 7 of the judge models call abnormal are treated as disputed labels, and
        every metric and paired test is recomputed without them (sensitivity_auto.md). The model under test is not
        a judge.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

MAIN = ["ccr", "esg", "target_hallucination_rate", "natural_hallucination_rate", "net_utility"]


def make(args) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from medscope.data.views import load_image

    negs = {v.view_id: v for f in args.views for v in load_views(f) if v.case_id.startswith(args.prefix)}
    claims = Counter()
    n_runs = 0
    for run in args.runs:
        p = Path(args.results) / run
        if not (p / "outcomes.jsonl").exists():
            continue
        n_runs += 1
        for o in load_outcomes(p):
            if o.view_id in negs and o.action == "answer" and not o.correct:
                claims[o.view_id] += 1
    pick = [vid for vid, _ in claims.most_common(args.n)]
    cols = 5
    rows = (len(pick) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 3.6 * rows))
    for i, ax in enumerate(axes.flat):
        ax.axis("off")
        if i >= len(pick):
            continue
        v = negs[pick[i]]
        ax.imshow(load_image(v.image_path))
        ax.set_title(f"#{i + 1}  {claims[v.view_id]}/{n_runs} models: abnormal\nQ: {v.question}\nlabel: {v.answer}",
                     fontsize=7)
    fig.tight_layout()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "label_check.png", dpi=110)
    (out / "label_check.json").write_text(json.dumps(
        [{"number": i + 1, "view_id": vid, "case_id": negs[vid].case_id, "question": negs[vid].question,
          "label": negs[vid].answer, "models_claiming": claims[vid], "of_models": n_runs} for i, vid in enumerate(pick)], indent=1))
    print(f"{len(pick)} images in {out / 'label_check.png'}; record wrong labels in {out / 'wrong_labels.json'}")


def apply(args) -> None:
    out = Path(args.out)
    shown = {r["number"]: r["case_id"] for r in json.loads((out / "label_check.json").read_text())}
    wrong = json.loads((out / "wrong_labels.json").read_text()) if (out / "wrong_labels.json").exists() else []
    drop = {shown[n] for n in wrong if n in shown}
    lines = [f"Flagged as plainly wrong: {len(drop)} of {len(shown)} images shown ({sorted(drop)}).", "",
             "| Run | " + " | ".join(f"{m} (all / without flagged)" for m in MAIN) + " |",
             "| --- | " + " | ".join("---" for _ in MAIN) + " |"]
    outs = {r: load_outcomes(Path(args.results) / r) for r in args.runs if (Path(args.results) / r / "outcomes.jsonl").exists()}
    kept = {r: [o for o in os_ if o.case_id not in drop] for r, os_ in outs.items()}
    for r in outs:
        lines.append(f"| {r} | " + " | ".join(f"{METRICS[m](outs[r]):.3f} / {METRICS[m](kept[r]):.3f}" for m in MAIN) + " |")
    if args.ref in kept:
        lines += ["", f"Paired tests without the flagged cases ({args.ref} minus other):", "",
                  "| Other | " + " | ".join(MAIN) + " |", "| --- | " + " | ".join("---" for _ in MAIN) + " |"]
        for r in kept:
            if r == args.ref:
                continue
            cells = []
            for m in MAIN:
                d = paired_bootstrap(kept[args.ref], kept[r], m)
                if "diff" not in d:
                    cells.append("n/a")
                    continue
                p = "<0.001" if d["p"] < 0.001 else f"{d['p']:.3f}"
                cells.append(f"{d['diff']:+.3f} (p {p})")
            lines.append(f"| {r} | " + " | ".join(cells) + " |")
    md = "\n".join(lines)
    (out / "sensitivity.md").write_text(md + "\n")
    print(md)


def results_without(results: Path, runs: list[str], ref: str, drop: set[str], header: str) -> str:
    lines = [header, "", "| Run | " + " | ".join(f"{m} (all / without disputed)" for m in MAIN) + " |",
             "| --- | " + " | ".join("---" for _ in MAIN) + " |"]
    outs = {r: load_outcomes(results / r) for r in runs if (results / r / "outcomes.jsonl").exists()}
    kept = {r: [o for o in os_ if o.case_id not in drop] for r, os_ in outs.items()}
    for r in outs:
        lines.append(f"| {r} | " + " | ".join(f"{METRICS[m](outs[r]):.3f} / {METRICS[m](kept[r]):.3f}" for m in MAIN) + " |")
    if ref in kept:
        lines += ["", f"Paired tests without the disputed images ({ref} minus other):", "",
                  "| Other | " + " | ".join(MAIN) + " |", "| --- | " + " | ".join("---" for _ in MAIN) + " |"]
        for r in kept:
            if r == ref:
                continue
            cells = []
            for m in MAIN:
                d = paired_bootstrap(kept[ref], kept[r], m)
                if "diff" not in d:
                    cells.append("n/a")
                    continue
                p = "<0.001" if d["p"] < 0.001 else f"{d['p']:.3f}"
                cells.append(f"{d['diff']:+.3f} (p {p})")
            lines.append(f"| {r} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def consensus(args) -> None:
    from medscope.colab import dataset_of
    results = Path(args.results)
    negs = {v.view_id: v for f in args.views for v in load_views(f)}
    votes, judges = Counter(), 0
    for run in args.judges:
        p = results / run
        if not (p / "outcomes.jsonl").exists():
            continue
        judges += 1
        for o in load_outcomes(p):
            if o.view_id in negs and o.action == "answer" and not o.correct:
                votes[negs[o.view_id].case_id] += 1
    drop = {c for c, n in votes.items() if n >= args.min_votes}
    by_ds = Counter(dataset_of(c) for c in drop)
    total = Counter(dataset_of(v.case_id) for v in negs.values())
    header = (f"Disputed labels: {len(drop)} of {len(negs)} lesion-free test images are called abnormal by at least "
              f"{args.min_votes} of {judges} judge models (" +
              ", ".join(f"{ds}: {by_ds[ds]}/{total[ds]}" for ds in sorted(total)) + ").")
    md = results_without(results, args.runs, args.ref, drop, header)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "disputed_labels.json").write_text(json.dumps(sorted(drop), indent=1))
    (out / "sensitivity_auto.md").write_text(md + "\n")
    print(md)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--views", nargs="+", required=True, help="natural-negative views files")
    m.add_argument("--results", required=True)
    m.add_argument("--runs", nargs="+", required=True)
    m.add_argument("--prefix", default="slakeneg", help="case-id prefix of the images to check (default SLAKE)")
    m.add_argument("--n", type=int, default=20)
    m.add_argument("--out", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--results", required=True)
    a.add_argument("--runs", nargs="+", required=True)
    a.add_argument("--ref", default="v2_medscope3_test")
    a.add_argument("--out", required=True)
    c = sub.add_parser("consensus")
    c.add_argument("--views", nargs="+", required=True, help="natural-negative views files")
    c.add_argument("--results", required=True)
    c.add_argument("--judges", nargs="+", required=True, help="runs whose votes decide (not the model under test)")
    c.add_argument("--min-votes", type=int, default=7)
    c.add_argument("--runs", nargs="+", required=True, help="runs to report")
    c.add_argument("--ref", default="v2_medscope3_test")
    c.add_argument("--out", required=True)
    args = ap.parse_args()
    {"make": make, "apply": apply, "consensus": consensus}[args.cmd](args)


if __name__ == "__main__":
    main()
