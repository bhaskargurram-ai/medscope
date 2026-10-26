"""Turn an unzipped SLAKE release into cases_{split}.jsonl manifests.

Usage:
    python scripts/prepare_slake.py --root data/raw/slake --out data/cases/slake
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders.slake import load_slake  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="folder with train.json, mask.txt and imgs/")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-lesion-pixels", type=int, default=20)
    args = ap.parse_args()

    out = Path(args.out)
    splits, report = load_slake(args.root, out / "masks", args.min_lesion_pixels)
    for split, cases in splits.items():
        with open(out / f"cases_{split}.jsonl", "w") as f:
            for c in cases:
                f.write(json.dumps(c.to_dict()) + "\n")
    print(report.summary())
    print(f"manifests written to {out}")


if __name__ == "__main__":
    main()
