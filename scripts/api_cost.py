"""Total measured API spend over every run with a usage.json, by model and by test set, for the paper's compute statement.

    python scripts/api_cost.py --results RESULTS --out RESULTS/api_cost.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows, by_model, by_split = [], defaultdict(lambda: [0, 0, 0.0]), defaultdict(float)
    unknown = []
    for f in sorted(Path(args.results).glob("*/usage.json")):
        u = json.loads(f.read_text())
        run = f.parent.name
        cost = u.get("cost_usd")
        split = run.rsplit("_", 1)[-1]
        rows.append((run, u.get("model", "?"), u.get("requests", 0), u.get("input_tokens", 0), u.get("output_tokens", 0), cost))
        m = by_model[u.get("model", "?")]
        m[0] += u.get("input_tokens", 0)
        m[1] += u.get("output_tokens", 0)
        if cost is None:
            unknown.append(run)
        else:
            m[2] += cost
            by_split[split] += cost
    total = sum(r[5] or 0 for r in rows)
    out = ["# Measured API spend (provider token counts × list prices of 31 October 2026)", "",
           f"Total over {len(rows)} runs: **US${total:,.2f}**" + (f" ({len(unknown)} runs at unknown prices: {', '.join(unknown)})" if unknown else ""), "",
           "| Model | Input tokens | Output tokens | US$ |", "| --- | --- | --- | --- |"]
    for m, (i, o, c) in sorted(by_model.items(), key=lambda kv: -kv[1][2]):
        out.append(f"| {m} | {i:,} | {o:,} | {c:,.2f} |")
    out += ["", "| Test set | US$ |", "| --- | --- |"] + [f"| {s} | {c:,.2f} |" for s, c in sorted(by_split.items(), key=lambda kv: -kv[1])]
    out += ["", "| Run | Model | Requests | Input | Output | US$ |", "| --- | --- | --- | --- | --- | --- |"]
    out += [f"| {r} | {m} | {q:,} | {i:,} | {o:,} | {'-' if c is None else f'{c:,.2f}'} |" for r, m, q, i, o, c in rows]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out[:12]))


if __name__ == "__main__":
    main()
