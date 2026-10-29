"""HyperKvasir normal lower-GI landmarks as natural negatives for colonoscopy.

HyperKvasir (Borgli et al., Scientific Data 2020; CC BY 4.0, research and education) comes
from the same hospital and lab as Kvasir-SEG. Its labelled anatomical-landmark classes
("cecum", "retroflex-rectum", "ileum") are colonoscopy frames of normal anatomy:
unedited images where "Is there a polyp?" has the answer No.

`fetch_landmarks` runs on Colab (needs huggingface_hub). It works with either layout the
Hugging Face copy might use: loose image files in class folders, or a zip of labelled images.
"""

from __future__ import annotations

import shutil
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

REPO = "SimulaMet-HOST/HyperKvasir"
# folder names -> class; the Hugging Face copy names the cecum folder "cecum", the paper "normal-cecum"
FOLDERS = {"cecum": "cecum", "normal-cecum": "cecum", "retroflex-rectum": "retroflex-rectum", "ileum": "ileum"}
CLASSES = ("cecum", "retroflex-rectum", "ileum")
IMAGE_EXTS = (".jpg", ".jpeg", ".png")
QUESTIONS = [
    ("polyp", "Is there a polyp in this image?", "No"),
    ("abn", "Is there an abnormality in this colonoscopy image?", "No"),
]


def class_of(path: str) -> str | None:
    """The landmark class named by a folder in this path, if any."""
    for part in (p.lower() for p in Path(path).parts[:-1]):
        if part in FOLDERS:
            return FOLDERS[part]
        if "cecum" in part or "caecum" in part:
            return "cecum"
    return None


def folder_names(files: list[str]) -> list[str]:
    return sorted({p for f in files for p in Path(f).parts[:-1]})


def fetch_landmarks(out_dir: str | Path, max_per_class: int = 300, log=print) -> Path:
    """Download the landmark images into out_dir/<class>/. Returns out_dir."""
    from huggingface_hub import HfApi, hf_hub_download

    out = Path(out_dir)
    files = HfApi().list_repo_files(REPO, repo_type="dataset")
    loose = [f for f in files if f.lower().endswith(IMAGE_EXTS) and class_of(f)]
    # incremental: images already downloaded count toward each class's cap
    counts: Counter = Counter({c: len(list((out / c).glob("*"))) for c in CLASSES if (out / c).is_dir()})
    if all(counts[c] >= max_per_class for c in ("cecum", "retroflex-rectum")):
        log(f"already have {dict(counts)}")
        return out
    if loose:
        log(f"{len(loose)} landmark images stored as loose files")
        for f in sorted(loose):
            c = class_of(f)
            if counts[c] >= max_per_class:
                continue
            dest = out / c / Path(f).name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(hf_hub_download(REPO, f, repo_type="dataset"), dest)
                counts[c] += 1
        log(f"landmark images: {dict(counts)}")
        if not counts["cecum"]:
            # rectum views alone would teach "scope visible in a retroflex view -> no polyp"
            raise FileNotFoundError(
                "no cecum images found. Folder names in the repo: " + ", ".join(folder_names(files)[:80]))
        return out

    zips = [f for f in files if f.lower().endswith(".zip") and "label" in f.lower()]
    zips = zips or [f for f in files if f.lower().endswith(".zip")]
    for zname in zips:
        log(f"looking for landmark images inside {zname}")
        local = hf_hub_download(REPO, zname, repo_type="dataset")
        with zipfile.ZipFile(local) as z:
            members = [m for m in z.namelist() if m.lower().endswith(IMAGE_EXTS) and class_of(m)]
            for m in sorted(members):
                c = class_of(m)
                if counts[c] >= max_per_class:
                    continue
                dest = out / c / Path(m).name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(m))
                counts[c] += 1
        if counts:
            log(f"extracted {dict(counts)}")
            return out
    raise FileNotFoundError(
        f"no {CLASSES} images found in {REPO}. Its files include: " + ", ".join(files[:40]))


def scan_landmarks(root: str | Path, out_dir: str | Path, max_side: int = 640) -> tuple[list[tuple[str, str, str]], Counter]:
    """(key, downscaled image path, class) for every landmark image under root."""
    root, out = Path(root), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    items = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in IMAGE_EXTS or not class_of(str(p.relative_to(root))):
            continue
        c = class_of(str(p.relative_to(root)))
        with Image.open(p) as im:
            img = im.convert("RGB")
        scale = min(1.0, max_side / max(img.size))
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.BICUBIC)
        key = f"{c}_{p.stem}"
        dest = out / f"{key}.png"
        img.save(dest)
        items.append((key, str(dest), c))
        stats[c] += 1
    return items, stats


def question_for(key: str) -> tuple[str, str, str]:
    from .common import stable_index
    return QUESTIONS[stable_index(key, len(QUESTIONS))]


def is_dark_or_blank(path: str) -> bool:
    """Skip frames that are mostly black (endoscope transitions), which say nothing about polyps."""
    with Image.open(path) as im:
        a = np.asarray(im.convert("L"), dtype=np.float32)
    return a.mean() < 25 or a.std() < 8
