"""Three-seed vote (review check R25, docs/REVIEW_EXPERIMENTS.md Amendment 9): one decision per view from the stored
decisions of several training seeds of the same recipe. Nothing is run.

Each seed's decision on a view is put in one of four classes: "present" (answers and does not deny the finding),
"absent" (answers that the finding is not there), "refer", or "other" (asks for a better image, or malformed). The
vote is the class most seeds chose; the stored decision of the first seed in that class is kept as it is, with its
answer, box and reward. With no majority, the decision is the first seed's that refers, else the first that asks for
a better image, else the first seed's.

    python scripts/seed_vote.py --runs RESULTS/v6_test RESULTS/v6_seed1_test RESULTS/v6_seed2_test \
        --out RESULTS/v6_vote_test --name medscope-v6-vote --split test
    -> outcomes.jsonl, scored.jsonl and summary.json in --out, read by every table like any other run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.metrics import bootstrap  # noqa: E402
from medscope.eval.runner import scored_rows  # noqa: E402
from medscope.rewards import Outcome  # noqa: E402


def decision_class(row: dict) -> str:
    if row.get("action") == "answer":
        return "absent" if row.get("claims_absent") else "present"
    return "refer" if row.get("action") == "refer" else "other"


def vote(rows: list[dict]) -> dict:
    """The voted decision among one view's rows, in seed order (pure)."""
    classes = [decision_class(r) for r in rows]
    top, n = Counter(classes).most_common(1)[0]
    if n * 2 > len(rows):
        return rows[classes.index(top)]
    for fallback in ("refer", "other"):
        if fallback in classes:
            return rows[classes.index(fallback)]
    return rows[0]


def voted_rows(run_dirs: list[str]) -> tuple[list[dict], dict]:
    per = [{r["view_id"]: {k: v for k, v in r.items() if k != "vkey"} for r in scored_rows(d)} for d in run_dirs]
    common = sorted(set.intersection(*(set(p) for p in per)))
    rows = [vote([p[v] for p in per]) for v in common]
    agree = Counter(len({decision_class(p[v]) for p in per}) for v in common)
    info = {"views": len(common), "all seeds agree": agree.get(1, 0), "two classes": agree.get(2, 0),
            "three classes": agree.get(3, 0), "views not in every run": sum(len(p) for p in per) - len(per) * len(common)}
    return rows, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True, help="run folders of the seeds, in seed order")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="test")
    args = ap.parse_args()
    missing = [d for d in args.runs if not (Path(d) / "outcomes.jsonl").exists()]
    if missing:
        raise SystemExit(f"runs not found: {missing}")
    rows, info = voted_rows(args.runs)
    outcomes = [Outcome(**r) for r in rows]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(o.to_dict()) + "\n" for o in outcomes)
    (out / "outcomes.jsonl").write_text(text)
    (out / "scored.jsonl").write_text(text)
    summary = {"meta": {"name": args.name, "split": args.split, "vote_of": [Path(d).name for d in args.runs],
                        "agreement": info},
               "n_views": len(outcomes), "n_cases": len({o.case_id for o in outcomes}), "metrics": bootstrap(outcomes)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    m = summary["metrics"]
    print(f"{args.name}: {info}; ESG {m['esg']['value']}, lesion-free claims {m['natural_hallucination_rate']['value']}, "
          f"net utility {m['net_utility']['value']}")


if __name__ == "__main__":
    main()
