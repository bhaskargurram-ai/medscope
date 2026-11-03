"""List every evaluation run with episodes that ended in an API error (failed or refused request).

Such episodes are not the model's answers. Rerunning the same evaluate command redoes them
(medscope/eval/runner.py); this lists where that is still needed.

    python scripts/api_errors.py --results RESULTS
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import API_ERROR, read_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    args = ap.parse_args()
    bad = []
    for run in sorted(Path(args.results).iterdir()):
        t = run / "transcripts.jsonl"
        if not t.exists():
            continue
        rows = read_jsonl(t)
        n = sum(API_ERROR in json.dumps(r.get("turns", "")) for r in rows)
        if n:
            bad.append((run.name, n, len(rows)))
    if not bad:
        print("no run has episodes that ended in an API error")
    for name, n, total in bad:
        print(f"{name}: {n} of {total} episodes ended in an API error -> rerun its evaluate command")


if __name__ == "__main__":
    main()
