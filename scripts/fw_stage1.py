"""Framework stage 1 screen: apply the rule of docs/FRAMEWORK_STAGE1.md to the generated answers (CPU).

    python scripts/fw_stage1.py --answers RESULTS/fw_stage0 --control replay_control --arms tf_replay tf_cmcc \
        --out RESULTS/fw_stage1 [--reference recipe cmcc]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answers", required=True, help="folder with answers_<name>.jsonl")
    ap.add_argument("--control", default="replay_control")
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--reference", nargs="*", default=[], help="other models compared the same way (descriptive)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from medscope.fw.stage0 import read_answers
    from medscope.fw.stage1 import compare, passes, report
    d = Path(args.answers)
    ctl = read_answers(d / f"answers_{args.control}.jsonl")
    if not ctl:
        raise SystemExit(f"no answers for the control {args.control}")
    res = {}
    for name in args.arms + args.reference:
        a = read_answers(d / f"answers_{name}.jsonl")
        if not a:
            print(f"{name}: no answers yet, skipped")
            continue
        res[name + (" (reference, descriptive)" if name in args.reference else "")] = compare(a, ctl)
    md = report(res, args.control)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage1.md").write_text(md)
    (out / "stage1.json").write_text(json.dumps({k: {**v, "rule": passes(v)} for k, v in res.items()}, indent=1, default=float))
    print(md)


if __name__ == "__main__":
    main()
