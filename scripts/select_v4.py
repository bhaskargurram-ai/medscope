"""Apply the pre-registered v4 selection rule (docs/PREREGISTRATION_v4.md) to the validation results.

    python scripts/select_v4.py --results RESULTS --adapters ADAPTERS --out ADAPTERS/final_choice_v4.json

Reads v4_s1_val, v4_s2_val and v4_s3_val; writes the choice with the numbers it was based on.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STAGES = [("stage 1", "v4_s1_val", "v4_s1"), ("stage 2", "v4_s2_val", "v4_s2"), ("stage 3", "v4_s3_val", "v4_s3")]
MARGIN = 0.02


def choose(scores: dict[str, tuple[float, float]]) -> str:
    """scores: stage -> (validation net utility U, healthy-image claim rate H)."""
    (u1, h1), (u2, h2), (u3, h3) = scores["stage 1"], scores["stage 2"], scores["stage 3"]
    if u3 >= u2 - MARGIN and h3 <= h2 + MARGIN:
        return "stage 3"
    if u2 >= u1 - MARGIN and h2 <= h1 + MARGIN:
        return "stage 2"
    return "stage 1"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--adapters", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--incumbent", default=None,
                    help="amendment 1: validation run of the earlier final model (v3) on the same v4 validation set; "
                         "it stays the final model if the chosen v4 stage is more than 0.02 below it in net utility")
    ap.add_argument("--incumbent-adapter", default=None)
    args = ap.parse_args()
    scores, folders = {}, {}
    for stage, run, folder in STAGES:
        m = json.loads((Path(args.results) / run / "summary.json").read_text())["metrics"]
        scores[stage] = (m["net_utility"]["value"], m["natural_hallucination_rate"]["value"])
        folders[stage] = f"{args.adapters}/{folder}/final"
    chosen = choose(scores)
    rec = {"rule": "docs/PREREGISTRATION_v4.md", "chosen": chosen, "adapter": folders[chosen],
           "validation": {s: {"net_utility": u, "healthy_image_claims": h} for s, (u, h) in scores.items()}}
    if args.incumbent:
        m = json.loads((Path(args.results) / args.incumbent / "summary.json").read_text())["metrics"]
        u_old = m["net_utility"]["value"]
        rec["validation"]["v3 (incumbent)"] = {"net_utility": u_old,
                                               "healthy_image_claims": m["natural_hallucination_rate"]["value"]}
        if scores[chosen][0] < u_old - MARGIN:
            print(f"amendment 1: v4 {chosen} ({scores[chosen][0]:.3f}) is more than {MARGIN} below v3 ({u_old:.3f}) "
                  "on the same validation set -> v3 stays the final model")
            rec.update({"chosen": "v3 (incumbent)", "adapter": args.incumbent_adapter, "v4_candidate": folders[chosen]})
    Path(args.out).write_text(json.dumps(rec, indent=2))
    for s, (u, h) in scores.items():
        print(f"{s}: validation net utility {u:.3f}, healthy-image claims {h:.1%}")
    print(f"pre-registered rule -> final model: {rec['chosen']} ({rec['adapter']})")


if __name__ == "__main__":
    main()
