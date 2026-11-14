"""Framework stage 1: tool-family training views for the cases of the replay-only control (docs/FRAMEWORK_STAGE1.md).

    python scripts/build_toolfamily.py --views TRAIN_VIEWS... --cases 3000 --seed 0 --out WORK/toolfamily
    # writes OUT/views.jsonl (original, erasure and control per case) for scripts/train_cmcc.py --cases 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--cases", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from medscope.data.inpaint import lama_inpaint
    from medscope.fw.toolfamily import build_toolfamily, select_cases, tool_counts, write_views
    from medscope.train.cmcc import build_triplets
    triplets = select_cases(build_triplets([v for f in args.views for v in load_views(f)]), args.cases, args.seed)
    print(f"{len(triplets)} triplet cases (the replay-only control trained on 2,739)")
    views = build_toolfamily(triplets, Path(args.out) / "images", lama_inpaint)
    write_views(views, Path(args.out) / "views.jsonl")
    print("new controls by tool/site:", tool_counts(views))


if __name__ == "__main__":
    main()
