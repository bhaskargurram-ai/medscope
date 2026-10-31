"""Standard medical VQA test sets as MedScope views, to check that training did not cost general ability.

  VQA-RAD   flaviagiammarino/vqa-rad  test split (all 451 questions)
  SLAKE     official English test questions (from the SLAKE files notebook 01 downloads)
  PathVQA   flaviagiammarino/path-vqa test split (random sample)

Every question becomes one "original" view scored with the same answer matching as the benchmark:
closed questions (yes/no) by polarity, open ones by mentioning the gold answer without a rival.
Referring or asking to clarify counts as not answering.

Usage:
    python scripts/build_vqa.py --out data/vqa [--slake data/raw/slake] [--per-set 300]
    # training replay set (general questions mixed into fine-tuning), with no image near-identical
    # to any evaluation image:
    python scripts/build_vqa.py --out data/vqa_train --split train --slake data/raw/slake \
        --exclude-images data/vqa/views_vqa.jsonl views/test/views_clean.jsonl ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.schema import View, ViewKind  # noqa: E402


def view(prefix: str, i: int, image_path: str, question: str, answer: str) -> View:
    case = f"{prefix}{i:05d}"
    return View(view_id=f"{case}__original", case_id=case, patient_id=case, kind=ViewKind.ORIGINAL,
                image_path=image_path, question=question.strip(), answer=str(answer).strip(), answer_aliases=[],
                lesion_box=None, critical=False, meta={"benchmark": prefix})


def save(img, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = img if isinstance(img, Image.Image) else Image.open(img)
    im.convert("RGB").save(path)
    return str(path)


def from_hf(repo: str, prefix: str, out: Path, limit: int | None, seed: int = 0, split: str = "test") -> list[View]:
    from datasets import load_dataset
    ds = load_dataset(repo, split=split)
    idx = list(range(len(ds)))
    if limit and limit < len(idx):
        idx = sorted(np.random.default_rng(seed).permutation(len(idx))[:limit].tolist())
    views = []
    for k, i in enumerate(idx):
        row = ds[i]
        views.append(view(prefix, k, save(row["image"], out / "images" / prefix / f"{k:05d}.png"),
                          row["question"], row["answer"]))
    return views


def from_slake(root: Path, out: Path, limit: int | None, seed: int = 0, split: str = "test",
               prefix: str = "slaketest", skip_keys: frozenset = frozenset()) -> list[View]:
    qs = [q for q in json.loads((root / f"{split}.json").read_text()) if str(q.get("q_lang", "")).lower() == "en"]
    qs = [q for q in qs if q["img_name"].split("/")[0] not in skip_keys]
    if limit and limit < len(qs):
        keep = sorted(np.random.default_rng(seed).permutation(len(qs))[:limit].tolist())
        qs = [qs[i] for i in keep]
    # images are copied next to the other sets, so the folder is self-contained
    return [view(prefix, k, save(root / "imgs" / q["img_name"], out / "images" / prefix / f"{k:05d}.png"),
                 q["question"], q["answer"]) for k, q in enumerate(qs)]


def eval_keys_and_hashes(files: list[str]) -> tuple[frozenset, list]:
    """SLAKE image ids (xmlabN) and perceptual hashes of every image used for evaluation."""
    import re
    from medscope.data.quality import dhash
    from medscope.data.views import load_image
    keys, hashes, seen = set(), [], set()
    for f in files:
        for line in Path(f).read_text().splitlines():
            if not line.strip():
                continue
            v = json.loads(line)
            keys.update(re.findall(r"xmlab\d+", f"{v['case_id']} {v['patient_id']} {v['image_path']}"))
            path = v.get("meta", {}).get("original_image") or v["image_path"]
            if v["kind"] in ("original", "natural_negative") and path not in seen and Path(path).exists():
                seen.add(path)
                hashes.append(dhash(load_image(path)))
    return frozenset(keys), hashes


def drop_near_copies(views: list[View], hashes: list) -> list[View]:
    from medscope.data.quality import dhash, hamming
    from medscope.data.views import load_image
    keep = []
    for v in views:
        h = dhash(load_image(v.image_path))
        if not any(hamming(h, e) <= 4 for e in hashes):
            keep.append(v)
    return keep


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slake", default=None, help="SLAKE folder with test.json/train.json and imgs/")
    ap.add_argument("--per-set", type=int, default=300, help="questions sampled from SLAKE and PathVQA")
    ap.add_argument("--split", choices=["test", "train"], default="test")
    ap.add_argument("--exclude-images", nargs="*", default=[],
                    help="views files whose images must not appear (or nearly appear) in the output")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.split == "train":
        keys, hashes = eval_keys_and_hashes(args.exclude_images)
        print(f"excluding {len(keys)} SLAKE images and near-copies of {len(hashes)} evaluation images")
        views = from_hf("flaviagiammarino/vqa-rad", "vqaradtr", out, None, split="train")
        if args.slake:
            views += from_slake(Path(args.slake), out, args.per_set, split="train", prefix="slaketr", skip_keys=keys)
        views += from_hf("flaviagiammarino/path-vqa", "pathvqatr", out, args.per_set, split="train")
        before = len(views)
        views = drop_near_copies(views, hashes)
        print(f"dropped {before - len(views)} questions on images near-identical to an evaluation image")
        name = "views_vqa_train.jsonl"
    else:
        views = from_hf("flaviagiammarino/vqa-rad", "vqarad", out, None)
        if args.slake:
            views += from_slake(Path(args.slake), out, args.per_set)
        views += from_hf("flaviagiammarino/path-vqa", "pathvqa", out, args.per_set)
        name = "views_vqa.jsonl"
    with open(out / name, "w") as f:
        for v in views:
            f.write(json.dumps(v.to_dict()) + "\n")
    closed = sum(v.answer.lower() in ("yes", "no") for v in views)
    print(f"{len(views)} questions ({closed} yes/no) -> {out / name}")


if __name__ == "__main__":
    main()
