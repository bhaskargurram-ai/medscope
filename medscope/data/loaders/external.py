"""External validation: the same tasks on data from other centres, never used for training.

  polyp      CVC-ClinicDB (Barcelona)        colonoscopy polyps     MedCLIPSeg mirror, ClinicDB.zip
  cxr        QaTa-COV19 (Qatar)              chest X-ray infection  MedCLIPSeg mirror, Covid19.zip
  breast     BUS-BRA (Brazil)                breast ultrasound      MedCLIPSeg mirror, BUSBRA.zip
  brain      BraTS-Africa 2023 (SSA)         brain MRI FLAIR        MedOtter/brats2023-ssa (3D, sliced here)

Training used Kvasir-SEG/HyperKvasir (Norway), ChestX-Det (NIH, USA), BUSI (Egypt) and TCGA-LGG (USA),
so every source here is a different institution and scanner population. Only the mirrors' test
folders are used. Masks are binarised with > 0.
"""

from __future__ import annotations

import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
from PIL import Image

from ..schema import Case, View, ViewKind
from .common import stable_index
from .extra import lesion_fraction_ok, save_pair

MEDCLIPSEG = "TahaKoleilat/MedCLIPSeg"
SOURCES = {
    "polyp": {"zip": "ClinicDB.zip", "modality": "endoscopy", "prefix": "cvcext",
              "questions": [("polyp", "Is there a polyp in this image?"),
                            ("abn", "Is there an abnormality in this colonoscopy image?")]},
    "cxr": {"zip": "Covid19.zip", "modality": "xray", "prefix": "qataext",
            "questions": [("abn", "Is there an abnormality in this chest X-ray?")]},
    "breast": {"zip": "BUSBRA.zip", "modality": "ultrasound", "prefix": "busbraext",
               "questions": [("lesion", "Is there a lesion in this breast ultrasound image?"),
                             ("mass", "Is there a breast mass in this ultrasound image?")]},
    "brain": {"modality": "mri", "prefix": "bratsext",
              "questions": [("tumor", "Is there a tumor in this brain MRI slice?"),
                            ("abn", "Is there an abnormality in this brain MRI slice?")]},
}
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def _key(stem: str) -> str:
    """Pairing key for image and mask file names: 'mask_0001-l' / '0001-l_mask' / 'bus_0001-l' -> '0001-l'."""
    s = stem.lower()
    s = re.sub(r"^(mask|label|seg|gt|bus|img|image)[_-]", "", s)
    s = re.sub(r"[_-](mask|label|seg|gt|segmentation)$", "", s)
    return s


def pair_files(img_dir: Path, mask_dir: Path) -> list[tuple[Path, Path]]:
    imgs = {_key(p.stem): p for p in sorted(img_dir.iterdir()) if p.suffix.lower() in IMAGE_EXTS}
    masks = {_key(p.stem): p for p in sorted(mask_dir.iterdir()) if p.suffix.lower() in IMAGE_EXTS}
    pairs = [(imgs[k], masks[k]) for k in sorted(imgs) if k in masks]
    if not pairs:
        raise FileNotFoundError(f"no image/mask pairs between {img_dir} ({list(imgs)[:3]}) and {mask_dir} ({list(masks)[:3]})")
    return pairs


def find_test_folder(root: Path) -> tuple[Path, Path]:
    """The test split's image and mask folders of an unpacked MedCLIPSeg zip
    (<DS>/Test_Folder/{img,label}); falls back to any folder holding img + label."""
    cands = [p for p in root.rglob("*") if p.is_dir() and p.name.lower().startswith("test")]
    cands += [p for p in root.rglob("*") if p.is_dir()]
    for d in cands:
        sub = {c.name.lower(): c for c in d.iterdir() if c.is_dir()}
        img = sub.get("img") or sub.get("images") or sub.get("image")
        lab = sub.get("label") or sub.get("labels") or sub.get("masks") or sub.get("mask")
        if img and lab:
            return img, lab
    raise FileNotFoundError(f"no test folder with images and masks under {root}")


def load_pairs(name: str, cache: Path) -> list[tuple[Path, Path]]:
    from huggingface_hub import hf_hub_download
    spec = SOURCES[name]
    zpath = Path(hf_hub_download(MEDCLIPSEG, spec["zip"], repo_type="dataset", cache_dir=str(cache / "hf")))
    root = cache / name
    if not root.exists():
        with zipfile.ZipFile(zpath) as z:
            z.extractall(root)
    return pair_files(*find_test_folder(root))


def records_from_pairs(name: str, pairs: Iterable[tuple[Path, Path]], out: Path, cap: int,
                       stats: Counter) -> tuple[list[Case], list[View]]:
    """Lesion images become cases (one question each); images whose mask is empty become negatives."""
    spec = SOURCES[name]
    cases, negs = [], []
    pairs = sorted(pairs, key=lambda p: stable_index(p[0].name, 10 ** 9))
    for img_p, mask_p in pairs:
        if len(cases) >= cap and len(negs) >= cap:
            break
        img = np.asarray(Image.open(img_p).convert("RGB"))
        mask = np.asarray(Image.open(mask_p).convert("L")) > 0
        if mask.shape != img.shape[:2]:
            mask = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize(
                (img.shape[1], img.shape[0]), Image.NEAREST)) > 0
        key = f"{spec['prefix']}{len(cases) + len(negs):05d}"
        if not mask.any():
            if len(negs) < cap:
                ip, _ = save_pair(img, None, out / name, key)
                negs.append(_negative(name, key, ip))
                stats[f"{name}: negatives"] += 1
            continue
        if len(cases) >= cap:
            continue
        if not lesion_fraction_ok(mask):
            stats[f"{name}: lesion too small or too large to erase"] += 1
            continue
        ip, mp = save_pair(img, mask, out / name, key)
        cases.append(_case(name, key, ip, mp))
        stats[f"{name}: lesion images"] += 1
    return cases, negs


def _case(name: str, key: str, image_path: str, mask_path: str, group: Optional[str] = None) -> Case:
    spec = SOURCES[name]
    tag, q = spec["questions"][stable_index(key, len(spec["questions"]))]
    return Case(case_id=f"{key}_{tag}", patient_id=group or key, dataset=f"external_{name}",
                modality=spec["modality"], image_path=image_path, question=q, answer="Yes",
                answer_aliases=[], mask_path=mask_path, critical=name == "brain")


def _negative(name: str, key: str, image_path: str, group: Optional[str] = None) -> View:
    spec = SOURCES[name]
    tag, q = spec["questions"][stable_index(key + "n", len(spec["questions"]))]
    case_id = f"{key}neg_{tag}"
    return View(view_id=f"{case_id}__natural_negative", case_id=case_id, patient_id=group or key,
                kind=ViewKind.NATURAL_NEGATIVE, image_path=image_path, question=q, answer="No",
                answer_aliases=[], lesion_box=None, critical=False,
                meta={"modality": spec["modality"], "dataset": f"external_{name}"})


# ---- BraTS-Africa: 3D volumes -> 2D axial FLAIR slices -------------------------------------------

def to_uint8(slice_: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (np.clip((slice_ - lo) / max(hi - lo, 1e-6), 0, 1) * 255).astype(np.uint8)


def slices_from_volume(flair: np.ndarray, seg: np.ndarray) -> tuple[Optional[int], Optional[int]]:
    """(slice with the largest tumour area, slice far from the tumour with plenty of brain), axial."""
    tumour = (seg > 0).sum(axis=(0, 1))
    brain = (flair > np.percentile(flair[flair > 0], 5) if (flair > 0).any() else flair > 0).sum(axis=(0, 1))
    pos = int(tumour.argmax()) if tumour.max() > 0 else None
    ok = [z for z in range(flair.shape[2]) if tumour[z] == 0 and brain[z] >= 0.6 * brain.max()]
    if pos is not None:
        ok = [z for z in ok if abs(z - pos) >= 10]
    neg = min(ok, key=lambda z: -brain[z]) if ok else None
    return pos, neg


def brats_records(root: Path, out: Path, cap: int, stats: Counter) -> tuple[list[Case], list[View]]:
    import nibabel as nib
    cases, negs = [], []
    flairs = sorted(root.rglob("*t2f.nii.gz"))
    for f in flairs:
        if len(cases) >= cap and len(negs) >= cap:
            break
        seg_p = Path(str(f).replace("t2f.nii.gz", "seg.nii.gz"))
        if not seg_p.exists():
            continue
        flair = np.asarray(nib.load(str(f)).get_fdata(), dtype=np.float32)
        seg = np.asarray(nib.load(str(seg_p)).get_fdata())
        lo, hi = np.percentile(flair[flair > 0], [0.5, 99.5]) if (flair > 0).any() else (0, 1)
        pos, neg = slices_from_volume(flair, seg)
        case_name = f.name.replace("-t2f.nii.gz", "")
        if pos is not None and len(cases) < cap:
            img, mask = np.rot90(to_uint8(flair[:, :, pos], lo, hi)), np.rot90(seg[:, :, pos] > 0)
            if lesion_fraction_ok(mask):
                key = f"bratsext{len(cases):05d}"
                ip, mp = save_pair(img, mask, out / "brain", key)
                cases.append(_case("brain", key, ip, mp, group=case_name))
                stats["brain: lesion slices"] += 1
            else:
                stats["brain: tumour too large to erase"] += 1
        if neg is not None and len(negs) < cap:
            key = f"bratsext{len(flairs) + len(negs):05d}"
            ip, _ = save_pair(np.rot90(to_uint8(flair[:, :, neg], lo, hi)), None, out / "brain", key)
            negs.append(_negative("brain", key, ip, group=case_name))
            stats["brain: negative slices"] += 1
    return cases, negs


def download_brats(cache: Path) -> Path:
    from huggingface_hub import snapshot_download
    return Path(snapshot_download("MedOtter/brats2023-ssa", repo_type="dataset",
                                  allow_patterns=["*t2f.nii.gz", "*seg.nii.gz"],
                                  local_dir=str(cache / "brats_ssa")))
