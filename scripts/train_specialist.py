"""Train the specialist agent of lead 4 (docs/PREREGISTRATION_v10.md): a lesion segmenter on unedited training
images only (lesion masks of the original views, empty masks for natural negatives). Resumes by epoch.

    python scripts/train_specialist.py --views TRAIN_VIEWS... --negatives TRAIN_NEG... --out ADAPTERS/specialist_v10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.mas.specialist import train_specialist  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    views = [v for f in args.views + args.negatives for v in load_views(f)]
    train_specialist(views, args.out, epochs=args.epochs, batch_size=args.batch_size, workers=args.workers, seed=args.seed)


if __name__ == "__main__":
    main()
