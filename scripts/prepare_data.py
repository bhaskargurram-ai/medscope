"""Build train/validation/test case manifests from SLAKE and (optionally) Kvasir-SEG.

Questions come from every image that has a lesion mask: SLAKE's own positive
abnormality questions where they exist, plus questions generated from the mask
labels. Splits are made per dataset over groups of near-identical images (neighbouring
slices, consecutive video frames), so no near-copy crosses from train into test.

Usage:
    python scripts/prepare_data.py --slake data/raw/slake --kvasir data/raw/kvasir --out data/cases
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders import kvasir, slake  # noqa: E402
from medscope.data.loaders.common import SPLITS, assign_splits, near_duplicate_groups  # noqa: E402


def split_records(records, name, seed, lines):
    groups = near_duplicate_groups([r.image_path for r in records])
    split_of = assign_splits(groups, seed=seed)
    sizes = Counter(groups)
    per_split = Counter(split_of[g] for g in groups)
    lines.append(f"{name}: {len(records)} images in {len(sizes)} groups of near-copies "
                 f"(largest group {max(sizes.values()) if sizes else 0}); images per split {dict(per_split)}")
    return [(r, split_of[g], g) for r, g in zip(records, groups)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slake", default=None, help="unzipped SLAKE folder (train.json, mask.txt, imgs/)")
    ap.add_argument("--kvasir", default=None, help="unzipped Kvasir-SEG folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = {s: [] for s in SPLITS}
    lines = []

    if args.slake:
        recs, stats, note = slake.scan_lesion_images(args.slake, out / "masks" / "slake")
        lines.append(f"SLAKE masks: {dict(stats)}")
        if note:
            lines.append(f"SLAKE {note}")
        for rec, split, group in split_records(recs, "SLAKE", args.seed, lines):
            cases[split] += slake.cases_for_image(rec, split, group)
    if args.kvasir:
        recs, stats = kvasir.scan_kvasir(args.kvasir, out / "kvasir")
        lines.append(f"Kvasir-SEG: {dict(stats)}")
        for rec, split, group in split_records(recs, "Kvasir-SEG", args.seed + 1, lines):
            cases[split] += kvasir.cases_for_image(rec, split, group)

    for split in SPLITS:
        with open(out / f"cases_{split}.jsonl", "w") as f:
            for c in cases[split]:
                f.write(json.dumps(c.to_dict()) + "\n")
        by_ds = Counter(c.dataset for c in cases[split])
        lines.append(f"cases_{split}.jsonl: {len(cases[split])} cases {dict(by_ds)}")
    summary = "\n".join(lines)
    (out / "prepare_report.txt").write_text(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main()
