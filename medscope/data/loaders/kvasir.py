"""Kvasir-SEG (1000 colonoscopy images with pixel-level polyp masks) -> MedScope cases.

Terms: research and educational use only; cite Jha et al., "Kvasir-SEG: A Segmented
Polyp Dataset", MMM 2020. Download: https://datasets.simula.no/kvasir-seg

Expected after unzipping: some folder containing `images/` and `masks/` with matching
file names (masks are JPEG, so they are thresholded). Images are downscaled to at most
`max_side` pixels on the long side to keep inpainting and model inputs fast.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from ..schema import Case

TEMPLATES = [
    ("polyp", "Is there a polyp in this image?", "Yes", []),
    ("abn", "Is there an abnormality in this colonoscopy image?", "Yes", []),
    ("what", "What abnormality is visible in this image?", "Polyp", ["a polyp", "polyps", "colon polyp"]),
]
IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def find_roots(path: str | Path) -> list[Path]:
    """Every folder that holds images/ and masks/ (the original zip has one; the Hugging Face
    mirror has one per split)."""
    path = Path(path)
    roots = [c for c in [path, *sorted(path.rglob("*"))]
             if c.is_dir() and (c / "images").is_dir() and (c / "masks").is_dir()]
    if not roots:
        raise FileNotFoundError(f"no folder with images/ and masks/ under {path}")
    return roots


def find_root(path: str | Path) -> Path:
    return find_roots(path)[0]


def export_hf_dataset(repo_id: str, out_dir: str | Path) -> Path:
    """Fallback when a Hugging Face copy only has image/mask columns: write them to images/ and masks/."""
    from datasets import load_dataset

    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    ds = load_dataset(repo_id)
    n = 0
    for split in ds:
        for row in ds[split]:
            row_id = f"{split}_{n:05d}"
            row["image"].convert("RGB").save(out / "images" / f"{row_id}.png")
            row["mask"].convert("L").save(out / "masks" / f"{row_id}.png")
            n += 1
    return out


@dataclass
class KvasirRecord:
    key: str
    image_path: str
    mask_path: str


def scan_kvasir(path: str | Path, out_dir: str | Path, max_side: int = 640,
                max_lesion_fraction: float = 0.25, min_lesion_pixels: int = 50) -> tuple[list[KvasirRecord], Counter]:
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    records = []
    pairs: dict[str, tuple[Path, Path]] = {}
    without_mask: set[str] = set()
    for root in find_roots(path):
        masks = {p.stem: p for p in (root / "masks").iterdir() if p.suffix.lower() in IMAGE_EXTS}
        for img_path in sorted(p for p in (root / "images").iterdir() if p.suffix.lower() in IMAGE_EXTS):
            mpath = masks.get(img_path.stem)
            if mpath is None:
                without_mask.add(img_path.stem)
            elif img_path.stem in pairs:
                stats["same file name in two folders (skipped)"] += 1
            else:
                pairs[img_path.stem] = (img_path, mpath)
    stats["no mask"] = len(without_mask - set(pairs))
    for img_path, mpath in pairs.values():
        stats["images"] += 1
        with Image.open(img_path) as im:
            img = im.convert("RGB")
        with Image.open(mpath) as mm:
            mask = mm.convert("L")
        scale = min(1.0, max_side / max(img.size))
        size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
        img = img.resize(size, Image.BICUBIC)
        binary = np.asarray(mask.resize(size, Image.NEAREST)) > 127
        if binary.sum() < min_lesion_pixels:
            stats["polyp too small"] += 1
            continue
        if binary.mean() > max_lesion_fraction:
            stats["polyp too large to erase"] += 1
            continue
        ip, mp = out / "images" / f"{img_path.stem}.png", out / "masks" / f"{img_path.stem}.png"
        img.save(ip)
        Image.fromarray((binary * 255).astype(np.uint8)).save(mp)
        records.append(KvasirRecord(img_path.stem, str(ip), str(mp)))
        stats["kept"] += 1
    return records, stats


def cases_for_image(rec: KvasirRecord, split: str, group: int) -> list[Case]:
    from .common import stable_index

    chosen = TEMPLATES if split == "train" else [TEMPLATES[stable_index(rec.key, len(TEMPLATES))]]
    return [Case(case_id=f"kvasir_{rec.key}_{tag}", patient_id=f"kvasir_g{group}", dataset="kvasir_seg",
                 modality="endoscopy", image_path=rec.image_path, question=q, answer=a, answer_aliases=al,
                 mask_path=rec.mask_path, critical=False)
            for tag, q, a, al in chosen]
