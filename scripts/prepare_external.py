"""Prepare the external validation set: other centres, never used in training.

Outputs in --out:
  cases_test.jsonl                         lesion images -> scripts/build_views.py
  negatives/views_negatives_external.jsonl lesion-free images (natural negatives)
  external_report.txt

Usage:
    python scripts/prepare_external.py --out data/external --cache data/raw/external [--cap 50]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders import external  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--cap", type=int, default=50, help="lesion images (and negatives) per source")
    ap.add_argument("--sources", nargs="+", default=list(external.SOURCES), choices=list(external.SOURCES))
    args = ap.parse_args()
    out, cache = Path(args.out), Path(args.cache)
    out.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    cases, negs, lines = [], [], []
    for name in args.sources:
        print(f"{name}: preparing", flush=True)
        try:
            if name == "brain":
                c, n = external.brats_records(external.download_brats(cache), out / "images", args.cap, stats)
            else:
                c, n = external.records_from_pairs(name, external.load_pairs(name, cache), out / "images", args.cap, stats)
        except Exception as e:  # noqa: BLE001 - one unavailable source must not block the others
            lines.append(f"{name}: FAILED ({type(e).__name__}: {e})")
            print(lines[-1], flush=True)
            continue
        cases += c
        negs += n
        lines.append(f"{name}: {len(c)} lesion images, {len(n)} lesion-free images")
        print(lines[-1], flush=True)
    with open(out / "cases_test.jsonl", "w") as f:
        for c in cases:
            f.write(json.dumps(c.to_dict()) + "\n")
    (out / "negatives").mkdir(exist_ok=True)
    with open(out / "negatives" / "views_negatives_external.jsonl", "w") as f:
        for v in negs:
            f.write(json.dumps(v.to_dict()) + "\n")
    lines.append(f"details: {dict(stats)}")
    (out / "external_report.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not cases:
        raise SystemExit("no external data could be prepared")


if __name__ == "__main__":
    main()
