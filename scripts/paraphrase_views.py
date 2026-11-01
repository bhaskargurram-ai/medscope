"""Test views with every templated question reworded in a phrasing never used in training.

All views of a case get the same rewording; view ids are kept, so results pair case by case with the
original-wording runs. Views whose question is not templated (SLAKE's own questions) are left out.

    python scripts/paraphrase_views.py --views TEST_VIEWS... TEST_NEG... --out DIR/views.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.paraphrase import HELD_OUT, paraphrase_view  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = []
    for v in (v for f in args.views for v in load_views(f)):
        p = paraphrase_view(v, HELD_OUT)
        if p is not v:
            out.append(p)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(json.dumps(v.to_dict()) + "\n" for v in out))
    print(f"{len(out)} views reworded ({len({v.case_id for v in out})} cases) -> {args.out}")


if __name__ == "__main__":
    main()
