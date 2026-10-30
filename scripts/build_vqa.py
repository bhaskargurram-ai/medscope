"""Standard medical VQA test sets as MedScope views, to check that training did not cost general ability.

  VQA-RAD   flaviagiammarino/vqa-rad  test split (all 451 questions)
  SLAKE     official English test questions (from the SLAKE files notebook 01 downloads)
  PathVQA   flaviagiammarino/path-vqa test split (random sample)

Every question becomes one "original" view scored with the same answer matching as the benchmark:
closed questions (yes/no) by polarity, open ones by mentioning the gold answer without a rival.
Referring or asking to clarify counts as not answering.

Usage:
    python scripts/build_vqa.py --out data/vqa [--slake data/raw/slake] [--per-set 300]
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


def from_hf(repo: str, prefix: str, out: Path, limit: int | None, seed: int = 0) -> list[View]:
    from datasets import load_dataset
    ds = load_dataset(repo, split="test")
    idx = list(range(len(ds)))
    if limit and limit < len(idx):
        idx = sorted(np.random.default_rng(seed).permutation(len(idx))[:limit].tolist())
    views = []
    for k, i in enumerate(idx):
        row = ds[i]
        views.append(view(prefix, k, save(row["image"], out / "images" / prefix / f"{k:05d}.png"),
                          row["question"], row["answer"]))
    return views


def from_slake(root: Path, out: Path, limit: int | None, seed: int = 0) -> list[View]:
    qs = [q for q in json.loads((root / "test.json").read_text()) if str(q.get("q_lang", "")).lower() == "en"]
    if limit and limit < len(qs):
        keep = sorted(np.random.default_rng(seed).permutation(len(qs))[:limit].tolist())
        qs = [qs[i] for i in keep]
    # images are copied next to the other sets, so the folder is self-contained
    return [view("slaketest", k, save(root / "imgs" / q["img_name"], out / "images" / "slaketest" / f"{k:05d}.png"),
                 q["question"], q["answer"]) for k, q in enumerate(qs)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slake", default=None, help="SLAKE folder with test.json and imgs/")
    ap.add_argument("--per-set", type=int, default=300, help="questions sampled from SLAKE and PathVQA")
    args = ap.parse_args()
    out = Path(args.out)
    views = from_hf("flaviagiammarino/vqa-rad", "vqarad", out, None)
    if args.slake:
        views += from_slake(Path(args.slake), out, args.per_set)
    views += from_hf("flaviagiammarino/path-vqa", "pathvqa", out, args.per_set)
    with open(out / "views_vqa.jsonl", "w") as f:
        for v in views:
            f.write(json.dumps(v.to_dict()) + "\n")
    closed = sum(v.answer.lower() in ("yes", "no") for v in views)
    print(f"{len(views)} questions ({closed} yes/no) -> {out / 'views_vqa.jsonl'}")


if __name__ == "__main__":
    main()
