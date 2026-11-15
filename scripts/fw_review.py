"""Apply the review-experiment rules (docs/REVIEW_EXPERIMENTS.md) to generated answers (CPU).

    python scripts/fw_review.py --answers RESULTS/fw_stage0 --out RESULTS/fw_review \
        [--r1-arm hardneg --r1-control replay_control] [--r2-arm vision_lrd --r2-control recipe]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--r1-arm", default="hardneg")
    ap.add_argument("--r1-control", default="replay_control")
    ap.add_argument("--r2-arm", default="vision_lrd")
    ap.add_argument("--r2-control", default="recipe")
    args = ap.parse_args()
    from medscope.fw.review import passes_r1, passes_r2, report
    from medscope.fw.stage0 import read_answers
    from medscope.fw.stage1 import compare
    d, out = Path(args.answers), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md, js = [], {}
    for tag, arm, ctl, rule, title in (
            ("R1", args.r1_arm, args.r1_control, passes_r1, "R1: hard-negative image swap (CORAL-style) vs the replay-only control"),
            ("R2", args.r2_arm, args.r2_control, passes_r2, "R2: vision adapters with layer-wise learning-rate decay vs the stage-1 recipe")):
        a, c = read_answers(d / f"answers_{arm}.jsonl"), read_answers(d / f"answers_{ctl}.jsonl")
        if not a or not c:
            md.append(f"# {title}\n\nNo answers yet for `{arm}` or `{ctl}`.\n")
            continue
        r = compare(a, c)
        md.append(report(title, ctl, {arm: r}, rule))
        js[tag] = {"arm": arm, "comparator": ctl, "result": r, "rule": rule(r)}
    (out / "review_experiments.md").write_text("\n".join(md))
    (out / "review_experiments.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
