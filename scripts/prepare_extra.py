"""Download and prepare chest X-ray, breast ultrasound and brain MRI data.

For each dataset: lesion images become question cases (the view builder then makes the
original / lesion-removed / random-edit / degraded views), lesion-free images become
natural-negative views. Splits keep each patient (or group of near-copies) in one split.

Outputs in --out:
  cases_{train,validation,test}.jsonl              for scripts/build_views.py
  negatives/views_negatives{,_train,_val}.jsonl    natural negatives (test / train / validation)
  extra_report.txt

Usage:
    python scripts/prepare_extra.py --out data/extra --cache data/raw/extra [--datasets chestxdet busi lgg]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders import extra  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True, help="where the parquet files are downloaded")
    ap.add_argument("--datasets", nargs="+", default=list(extra.DATASETS), choices=list(extra.DATASETS))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out = Path(args.out)
    for p in [*out.glob("cases_*.jsonl"), out / "negatives"]:
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, name in enumerate(args.datasets):
        spec = extra.DATASETS[name]
        print(f"{name}: downloading {spec['repo']}", flush=True)
        files = extra.download(spec["repo"], Path(args.cache))
        recs, stats = extra.scan(name, extra.iter_parquet_rows(files), out / "images")
        kinds = __import__("collections").Counter(r.negative for r in recs)
        if not kinds[True] or not kinds[False]:
            raise SystemExit(f"{name}: {kinds[False]} lesion images and {kinds[True]} lesion-free images were found; "
                             f"the dataset layout may have changed ({dict(stats)})")
        # the split seed depends on the dataset name only, so preparing a subset gives the same splits
        splits = extra.split_and_cap(recs, seed=args.seed + stable_index(name, 1000))
        counts = extra.write_outputs(splits, out)
        lines += [f"{name} ({spec['repo']}): {dict(stats)}",
                  f"{name} labels: {dict(__import__('collections').Counter(r.label for r in recs))}",
                  f"{name} per split: {counts}"]
        print("\n".join(lines[-3:]), flush=True)
    (out / "extra_report.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
