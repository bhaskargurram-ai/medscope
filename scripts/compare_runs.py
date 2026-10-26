"""Print and save a leaderboard of every run under a results folder.

Usage:
    python scripts/compare_runs.py --results /content/drive/MyDrive/medscope/results
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import compare_runs  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    args = ap.parse_args()
    table = compare_runs(args.results)
    (Path(args.results) / "leaderboard.md").write_text(table + "\n")
    print(table)


if __name__ == "__main__":
    main()
