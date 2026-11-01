"""Drop lesion-free test images that near-copy any image of other views files (training or test).

check_views.py de-duplicates the lesion cases; this does the same for a natural-negatives file, in place
(the original is kept as <file>.before_dedup). A match needs a close perceptual hash and a pixel correlation
of at least --min-correlation.

    python scripts/dedup_negatives.py --negatives NEG.jsonl --against TRAIN_VIEWS... TRAIN_NEG... TEST_VIEWS...
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.quality import correlation, dhash, near_duplicates  # noqa: E402
from medscope.data.views import load_image  # noqa: E402


def unedited_images(files: list[str]) -> dict[str, str]:
    """id -> image path of every original or natural-negative view in the files."""
    out = {}
    for f in files:
        for line in open(f):
            if line.strip():
                v = json.loads(line)
                if v["kind"] in ("original", "natural_negative"):
                    out[f"{f}::{v['view_id']}"] = v["image_path"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--negatives", required=True)
    ap.add_argument("--against", nargs="+", required=True)
    ap.add_argument("--min-correlation", type=float, default=0.98)
    args = ap.parse_args()
    path = Path(args.negatives)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    query = {r["view_id"]: r["image_path"] for r in rows}
    ref = {k: p for k, p in unedited_images(args.against).items() if p not in set(query.values())}
    qh = {k: dhash(load_image(p)) for k, p in query.items()}
    rh = {k: dhash(load_image(p)) for k, p in ref.items()}
    dupes = near_duplicates(qh, rh, confirm=lambda q, r: correlation(load_image(query[q]), load_image(ref[r]))
                            >= args.min_correlation)
    if not path.with_suffix(".before_dedup").exists():
        shutil.copy(path, path.with_suffix(".before_dedup"))
    kept = [r for r in rows if r["view_id"] not in dupes]
    path.write_text("".join(json.dumps(r) + "\n" for r in kept))
    print(f"{len(rows) - len(kept)} of {len(rows)} lesion-free images near-copy a reference image and were dropped; "
          f"{len(kept)} kept in {path}")


if __name__ == "__main__":
    main()
