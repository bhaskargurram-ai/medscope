"""Screening stage A (docs/SCREENING.md): decision policies on the stored lead-4 reports, validation set only.

    python scripts/screen_a.py --views VAL_VIEWS... --reports RESULTS/mas_reports/val_*.jsonl --out RESULTS/screen_a
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.mas.reports import read_reports  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402
from medscope.screen.stage_a import report_md, run_screen  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--reports", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    views = [v for f in args.views for v in load_views(f)]
    reports = {}
    for f in args.reports:
        reports.update(read_reports(f))
    cfg = with_vocab(load_config(), views)
    rows = run_screen(views, reports, cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "screen_a.json").write_text(json.dumps(rows, indent=1, default=float))
    md = report_md(rows)
    (out / "screen_a.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
