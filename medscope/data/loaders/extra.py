"""More imaging types: chest X-ray, breast ultrasound and brain MRI.

All three come from public, ungated Hugging Face parquet mirrors that store an image, a
binary lesion mask and a flag for lesion-free images, so each dataset gives both
counterfactual cases (images with a lesion) and natural negatives (images without one)
from the same source:

  chestxdet  MedOtter/ChestX-Det       NIH ChestX-ray14 images, 13 finding masks (Apache-2.0
                                        annotations; cite Wang et al. CVPR 2017 for the images)
  busi       MedOtter/BUSI             breast ultrasound, benign/malignant masks + normals (CC BY 4.0)
  lgg        MedOtter/TCGA-LGG-Mask    brain MRI FLAIR slices, tumour masks (CC BY-NC-SA 4.0)

Splits are made over patients (chest X-ray, brain MRI) or groups of near-identical images
(ultrasound, which has known duplicates), so no patient or near-copy crosses splits.
"""

from __future__ import annotations

import io
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np
from PIL import Image

from ..schema import Case, View, ViewKind
from .common import SPLITS, assign_splits, near_duplicate_groups, stable_index

MAX_SIDE = 768
MIN_LESION_PIXELS = 20
MAX_LESION_FRACTION = 0.2          # same limit as SLAKE: erasing bigger lesions is not convincing

# chest X-ray findings with a local mask that can be erased; the rest (an enlarged heart,
# emphysema, diffuse nodules) cover too much of the image to remove
CXR_FOCAL = {
    "nodule": "a nodule", "mass": "a mass", "pneumothorax": "a pneumothorax", "fracture": "a rib fracture",
    "effusion": "a pleural effusion", "consolidation": "consolidation", "atelectasis": "atelectasis",
    "calcification": "calcification", "fibrosis": "fibrosis", "pleural_thickening": "pleural thickening",
}
CXR_DIFFUSE = ("cardiomegaly", "emphysema", "diffuse_nodule")
CXR_CRITICAL = {"pneumothorax", "mass"}
BUSI_CLASSES = ("benign", "malignant", "normal")


@dataclass
class Record:
    key: str
    dataset: str
    modality: str
    image_path: str
    mask_path: Optional[str]
    group: str                      # patient (or near-copy group) id: never split across sets
    label: str                      # dominant finding, or "normal"
    critical: bool = False
    negative: bool = False
    meta: dict = field(default_factory=dict)


# ---- decoding ---------------------------------------------------------------------------

def decode(cell) -> Optional[np.ndarray]:
    """A parquet image cell ({"bytes": ...}, raw bytes, or a PIL image) as an array."""
    if cell is None:
        return None
    if isinstance(cell, dict):
        cell = cell.get("bytes")
        if cell is None:
            return None
    if isinstance(cell, (bytes, bytearray)):
        cell = Image.open(io.BytesIO(cell))
    if isinstance(cell, Image.Image):
        return np.asarray(cell)
    return np.asarray(cell)


def to_rgb(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    if img.shape[-1] == 4:
        img = img[..., :3]
    if img.dtype != np.uint8:
        lo, hi = float(img.min()), float(img.max())
        img = ((img - lo) / max(hi - lo, 1e-6) * 255).astype(np.uint8)
    return img


def binary(mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if mask is None:
        return None
    if mask.ndim == 3:
        mask = mask.max(axis=-1)
    return mask > 0


def save_pair(img: np.ndarray, mask: Optional[np.ndarray], out_dir: Path, key: str) -> tuple[str, Optional[str]]:
    """Save image (and mask) with the longer side capped at MAX_SIDE."""
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(to_rgb(img))
    scale = MAX_SIDE / max(im.size)
    if scale < 1:
        im = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.BICUBIC)
    ip = out_dir / f"{key}.png"
    im.save(ip)
    mp = None
    if mask is not None:
        m = Image.fromarray(mask.astype(np.uint8) * 255).resize(im.size, Image.NEAREST)
        mp = out_dir / f"{key}_mask.png"
        m.save(mp)
    return str(ip), (str(mp) if mp else None)


def lesion_fraction_ok(mask: np.ndarray) -> bool:
    n = int(mask.sum())
    return n >= MIN_LESION_PIXELS and n / mask.size <= MAX_LESION_FRACTION


# ---- per-dataset row readers: row dict -> (image, mask or None, group, label, critical, negative) or None

def chestxdet_row(row: dict, stats: Counter):
    img = decode(row["image"])
    image_id = str(row.get("image_id", ""))
    # NIH file names ("00000013_005.png") start with the patient id; otherwise near-copy groups are used
    group = "cxr_" + image_id.split("_")[0] if "_" in image_id else ""
    if bool(row.get("is_negative")):
        return img, None, group, "normal", False, True
    present = {c: binary(decode(row.get(f"{c}_mask"))) for c in list(CXR_FOCAL) + list(CXR_DIFFUSE)}
    present = {c: m for c, m in present.items() if m is not None and m.any()}
    if any(c in present for c in CXR_DIFFUSE):
        stats["chest X-ray: diffuse finding (cannot be erased)"] += 1
        return None
    if not present:
        stats["chest X-ray: no mask for a focal finding"] += 1
        return None
    union = np.zeros_like(next(iter(present.values())))
    for m in present.values():
        union |= m
    label = max(present, key=lambda c: present[c].sum())
    return img, union, group, label, label in CXR_CRITICAL, False


def busi_row(row: dict, stats: Counter):
    img = decode(row["image"])
    label = row.get("class_label", "")
    image_id = str(row.get("image_id", ""))
    if not isinstance(label, str) or label.lower() not in BUSI_CLASSES:
        # a class index, or missing: the file name ("benign (12)") says it
        label = next((c for c in BUSI_CLASSES if image_id.lower().startswith(c)), str(label))
    label = label.lower()
    group = "busi_" + image_id                                        # replaced by near-copy groups later
    if label == "normal":
        return img, None, group, "normal", False, True
    mask = binary(decode(row.get("mask")))
    if mask is None or not mask.any():
        stats["ultrasound: lesion image without a mask"] += 1
        return None
    return img, mask, group, label, label == "malignant", False


def lgg_row(row: dict, stats: Counter):
    rgb = decode(row["image"])
    flair = rgb[..., 1] if rgb.ndim == 3 else rgb                     # channels: pre-contrast, FLAIR, post-contrast
    group = "lgg_" + str(row.get("patient_id", ""))
    brain = (flair > 10).mean()
    if brain < 0.15:                                                  # top/bottom slices: little or no brain
        stats["brain MRI: slice with little brain (skipped)"] += 1
        return None
    if not bool(row.get("has_tumor")):
        return flair, None, group, "normal", False, True
    mask = binary(decode(row.get("mask")))
    if mask is None or not mask.any():
        return None
    return flair, mask, group, "tumor", True, False


DATASETS: dict[str, dict] = {
    "chestxdet": {"repo": "MedOtter/ChestX-Det", "modality": "xray", "reader": chestxdet_row, "group_by_copies": False},
    "busi": {"repo": "MedOtter/BUSI", "modality": "ultrasound", "reader": busi_row, "group_by_copies": True},
    "lgg": {"repo": "MedOtter/TCGA-LGG-Mask", "modality": "mri", "reader": lgg_row, "group_by_copies": False},
}

# per split: cap on lesion images and on negative images, so evaluation stays affordable
CAPS = {"train": (500, 250), "validation": (25, 25), "test": (50, 50)}
# v4: every training image the split holds, a larger validation set for model selection; test unchanged
CAPS_V4 = {"train": (10 ** 6, 10 ** 6), "validation": (100, 100), "test": (0, 0)}   # v4 keeps the existing test files
MAX_PER_PATIENT = {"lgg": (5, 3)}   # brain MRI: neighbouring slices are near-copies; keep a few per patient


def questions(dataset: str, label: str) -> list[tuple[str, str]]:
    """(tag, question) templates whose answer is "Yes" when the lesion is there."""
    if dataset == "chestxdet":
        finding = CXR_FOCAL.get(label, "an abnormality")
        return [("abn", "Is there an abnormality in this chest X-ray?"),
                ("finding", f"Is there {finding} in this chest X-ray?")]
    if dataset == "busi":
        return [("lesion", "Is there a lesion in this breast ultrasound image?"),
                ("mass", "Is there a breast mass in this ultrasound image?")]
    return [("tumor", "Is there a tumor in this brain MRI slice?"),
            ("abn", "Is there an abnormality in this brain MRI slice?")]


def negative_question(dataset: str, key: str) -> tuple[str, str]:
    """A question for a lesion-free image, phrased like the lesion images' questions."""
    if dataset == "chestxdet":
        options = [("abn", "Is there an abnormality in this chest X-ray?")] + \
                  [(f"f_{c}", f"Is there {t} in this chest X-ray?") for c, t in CXR_FOCAL.items()]
    else:
        options = questions(dataset, "normal")
    return options[stable_index(key, len(options))]


# ---- reading, splitting, writing ------------------------------------------------------------

def iter_parquet_rows(files: Iterable[str | Path]) -> Iterable[dict]:
    import pyarrow.parquet as pq
    for f in files:
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=64):
            yield from batch.to_pylist()


def download(repo: str, cache: Path) -> list[Path]:
    from huggingface_hub import snapshot_download
    root = Path(snapshot_download(repo, repo_type="dataset", allow_patterns=["data/*.parquet", "*.parquet"],
                                  local_dir=str(cache / repo.replace("/", "__"))))
    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no parquet files in {repo}")
    return files


def scan(name: str, rows: Iterable[dict], out_dir: Path, log: Callable[[str], None] = print) -> tuple[list[Record], Counter]:
    spec = DATASETS[name]
    stats: Counter = Counter()
    recs: list[Record] = []
    for i, row in enumerate(rows):
        got = spec["reader"](row, stats)
        if got is None:
            continue
        img, mask, group, label, critical, negative = got
        if not negative and not lesion_fraction_ok(mask):
            stats["lesion too small or too large to erase"] += 1
            continue
        key = f"{name}{i:05d}"
        ip, mp = save_pair(img, mask, out_dir / name, key)
        recs.append(Record(key, name, spec["modality"], ip, mp, group, label, critical, negative))
        stats["negative images" if negative else "lesion images"] += 1
        if (i + 1) % 500 == 0:
            log(f"  {name}: {i + 1} rows read, {len(recs)} kept")
    if recs and (spec["group_by_copies"] or any(not r.group for r in recs)):
        groups = near_duplicate_groups([r.image_path for r in recs])
        for r, g in zip(recs, groups):
            r.group = f"{name}_g{g}"
    return recs, stats


def split_and_cap(recs: list[Record], seed: int, caps: Optional[dict] = None,
                  fresh: Optional[tuple[int, int]] = None, fresh_exclude: frozenset = frozenset()) -> dict[str, list[Record]]:
    """Assign whole groups to splits, then cap lesion and negative images per split (and per patient).

    The selection is deterministic, so raising the train or validation caps adds images without changing which
    images the test split holds. `fresh` = (lesion, negative) caps of a confirmatory "fresh" test set taken from
    test-split patients that the existing test set does not use: images nobody has evaluated before.
    """
    caps = caps or CAPS
    ids = {g: k for k, g in enumerate(sorted({r.group for r in recs}))}
    split_of = assign_splits([ids[r.group] for r in recs], seed=seed)
    out: dict[str, list[Record]] = {s: [] for s in SPLITS}
    if fresh:
        out["fresh"] = []
    by_split: dict[str, list[Record]] = defaultdict(list)
    for r in recs:
        by_split[split_of[ids[r.group]]].append(r)
    for split, rs in by_split.items():
        cap_pos, cap_neg = caps[split]
        per_patient = MAX_PER_PATIENT.get(rs[0].dataset) if rs else None
        leftovers = {}
        for negative, cap in ((False, cap_pos), (True, cap_neg)):
            pool = sorted((r for r in rs if r.negative == negative), key=lambda r: stable_index(r.key, 10 ** 9))
            if per_patient:
                limit = per_patient[1] if negative else per_patient[0]
                seen: Counter = Counter()
                kept = []
                for r in pool:
                    if seen[r.group] < limit:
                        kept.append(r)
                        seen[r.group] += 1
                pool = kept
            out[split] += pool[:cap]
            leftovers[negative] = pool[cap:]
        if fresh and split == "test":
            used = {r.group for r in out["test"]}          # patients the existing test set already shows
            for negative in (False, True):
                rest = [r for r in leftovers[negative] if r.group not in used and r.group not in fresh_exclude]
                out["fresh"] += rest[:fresh[1] if negative else fresh[0]]
    return out


def cases_for(rec: Record, split: str) -> list[Case]:
    qs = questions(rec.dataset, rec.label)
    chosen = [qs[stable_index(rec.key, len(qs))]]   # one question per image keeps training and evaluation affordable
    return [Case(case_id=f"{rec.key}_{tag}", patient_id=rec.group, dataset=rec.dataset, modality=rec.modality,
                 image_path=rec.image_path, question=q, answer="Yes", answer_aliases=[],
                 mask_path=rec.mask_path, critical=rec.critical)
            for tag, q in chosen]


def negative_view(rec: Record) -> View:
    tag, q = negative_question(rec.dataset, rec.key)
    case_id = f"{rec.key}neg_{tag}"
    return View(view_id=f"{case_id}__natural_negative", case_id=case_id, patient_id=rec.group,
                kind=ViewKind.NATURAL_NEGATIVE, image_path=rec.image_path, question=q, answer="No",
                answer_aliases=[], lesion_box=None, critical=False,
                meta={"modality": rec.modality, "dataset": rec.dataset})


NEG_FILES = {"test": "views_negatives.jsonl", "train": "views_negatives_train.jsonl",
             "validation": "views_negatives_val.jsonl", "fresh": "views_negatives_fresh.jsonl"}


def write_outputs(splits: dict[str, list[Record]], out: Path) -> dict:
    """cases_{split}.jsonl for the view builder, natural-negative views per split."""
    counts = {}
    (out / "negatives").mkdir(parents=True, exist_ok=True)
    for split in [*SPLITS, *(["fresh"] if "fresh" in splits else [])]:
        rs = splits.get(split, [])
        cases = [c for r in rs if not r.negative for c in cases_for(r, split)]
        negs = [negative_view(r) for r in rs if r.negative]
        with open(out / f"cases_{split}.jsonl", "a") as f:
            for c in cases:
                f.write(json.dumps(c.to_dict()) + "\n")
        with open(out / "negatives" / NEG_FILES[split], "a") as f:
            for v in negs:
                f.write(json.dumps(v.to_dict()) + "\n")
        counts[split] = {"lesion images": sum(not r.negative for r in rs), "cases": len(cases), "negatives": len(negs)}
    return counts
