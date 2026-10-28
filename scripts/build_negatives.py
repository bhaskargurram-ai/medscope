"""Build the natural-negative evaluation set: unedited SLAKE images without a lesion.

Each view is an original image plus SLAKE's own question whose answer says the abnormality
isn't there ("Does the picture contain liver cancer?" -> "No"). No editing is involved, so a
model that refers on lesion-removed images only because it detects the edit will instead
hallucinate the finding here.

Images that are near-copies of a training image are left out (--dedup-against).

Usage:
    python scripts/build_negatives.py --slake data/raw/slake --out data/views/negatives \
        --dedup-against data/views/train/views.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders.slake import scan_natural_negatives  # noqa: E402
from medscope.data.quality import correlation, dhash, hamming  # noqa: E402
from medscope.data.schema import View, ViewKind  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from PIL import Image  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slake", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dedup-against", default=None, help="training views.jsonl")
    ap.add_argument("--min-correlation", type=float, default=0.98)
    args = ap.parse_args()

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    items, stats = scan_natural_negatives(args.slake)

    train_hashes = []
    if args.dedup_against:
        for line in Path(args.dedup_against).read_text().splitlines():
            v = json.loads(line)
            if v["kind"] == "original":
                train_hashes.append((dhash(load_image(v["image_path"])), v["image_path"]))

    def near_copy_of_train(img) -> bool:
        h = dhash(img)
        return any(hamming(h, th) <= 4 and correlation(img, load_image(tp)) >= args.min_correlation
                   for th, tp in train_hashes)

    views, checked = [], {}
    for key, image_path, q in items:
        if key not in checked:
            img = load_image(image_path)
            checked[key] = not near_copy_of_train(img)
            if checked[key]:
                Image.fromarray(img).save(out / "images" / f"{key}.png")
        if not checked[key]:
            stats["near-copy of a training image (skipped)"] += 1
            continue
        case_id = f"slakeneg_{key}_q{q.get('qid')}"
        views.append(View(view_id=f"{case_id}__natural_negative", case_id=case_id, patient_id=f"slakeneg_{key}",
                          kind=ViewKind.NATURAL_NEGATIVE, image_path=str(out / "images" / f"{key}.png"),
                          question=q["question"], answer=str(q["answer"]), answer_aliases=[], lesion_box=None,
                          critical=False, meta={"modality": str(q.get("modality", "")).lower()}))

    with open(out / "views_negatives.jsonl", "w") as f:
        for v in views:
            f.write(json.dumps(v.to_dict()) + "\n")
    stats["views written"] = len(views)
    stats["by answer"] = dict(Counter(v.answer for v in views))
    summary = "\n".join(f"{k}: {v}" for k, v in stats.items())
    (out / "negatives_report.txt").write_text(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main()
