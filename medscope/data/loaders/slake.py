"""Convert the SLAKE release into MedScope Case records.

Expected layout (as on huggingface.co/datasets/BoKelvin/SLAKE after unzipping imgs.zip):

    root/
      train.json  validation.json  test.json  mask.txt
      imgs/xmlab{N}/source.jpg
      imgs/xmlab{N}/mask.png          # label map: pixel value = class id from mask.txt

Only English questions about abnormalities are kept, and only when the image has
lesion pixels in its mask, because the counterfactual views need to know exactly
where the evidence is. Lesion classes are those whose mask.txt name mentions
cancer, tumor or edema; everything else (organs, bones) is anatomy.

SLAKE has no patient identifiers, so each image id stands in for a patient. Its
official train/validation/test split is kept so results stay comparable with
published SLAKE numbers.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from ..schema import Case

LESION_WORDS = ("cancer", "tumor", "tumour", "edema", "oedema", "lesion", "nodule", "mass")
SPLIT_FILES = {"train": "train.json", "validation": "validation.json", "test": "test.json"}
_LINE = re.compile(r"^\s*(\d+)\s*[:,\t ]\s*(.+?)\s*$")


def parse_mask_labels(path: str | Path) -> dict[int, str]:
    """Read mask.txt into {class id: name}. Tolerates ':', ',', tab or space separators."""
    labels = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = _LINE.match(line)
        if m:
            labels[int(m.group(1))] = m.group(2)
    if not labels:
        raise ValueError(f"no 'id name' lines found in {path}")
    return labels


def lesion_ids(labels: dict[int, str]) -> set[int]:
    return {i for i, name in labels.items() if any(w in name.lower() for w in LESION_WORDS)}


def read_label_map(path: str | Path) -> np.ndarray:
    arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        if not (np.array_equal(arr[..., 0], arr[..., 1]) and np.array_equal(arr[..., 0], arr[..., 2])):
            raise ValueError(f"{path} is a colour image, expected a single-channel label map")
        arr = arr[..., 0]
    return arr


def keep_question(q: dict) -> bool:
    """English abnormality questions whose answer asserts that an abnormality is present."""
    if str(q.get("q_lang", "")).lower() != "en":
        return False
    if not str(q.get("content_type", "")).lower().startswith("abnormal"):
        return False
    question = str(q.get("question", "")).lower()
    answer = str(q.get("answer", "")).strip().lower()
    asks_health = re.search(r"\b(healthy|normal)\b", question) is not None
    if asks_health:
        return answer == "no"          # "Is the liver healthy?" -> "No" means a lesion is there
    return answer != "no"              # "Is there a tumor?" -> "No" has no evidence to remove


@dataclass
class SlakeReport:
    questions_seen: int = 0
    kept: Counter = field(default_factory=Counter)
    dropped: Counter = field(default_factory=Counter)
    lesion_pixels_by_label: Counter = field(default_factory=Counter)

    def summary(self) -> str:
        lines = [f"questions seen: {self.questions_seen}",
                 f"kept per split: {dict(self.kept)}",
                 f"dropped by reason: {dict(self.dropped)}",
                 "lesion labels found (images): " + ", ".join(
                     f"{k}={v}" for k, v in self.lesion_pixels_by_label.most_common())]
        return "\n".join(lines)


def load_slake(root: str | Path, mask_out: str | Path, min_lesion_pixels: int = 20) -> tuple[dict[str, list[Case]], SlakeReport]:
    """Return {split: [Case]} and a report. Binary lesion masks are written to mask_out."""
    root, mask_out = Path(root), Path(mask_out)
    labels = parse_mask_labels(root / "mask.txt")
    lesion = lesion_ids(labels)
    if not lesion:
        raise ValueError("mask.txt has no lesion classes; check LESION_WORDS against it")

    report = SlakeReport()
    mask_cache: dict[str, str | None] = {}
    out: dict[str, list[Case]] = {}

    for split, fname in SPLIT_FILES.items():
        path = root / fname
        if not path.exists():
            continue
        cases = []
        for q in json.loads(path.read_text(encoding="utf-8")):
            report.questions_seen += 1
            if not keep_question(q):
                report.dropped["not an English positive abnormality question"] += 1
                continue
            img_rel = q["img_name"]                       # e.g. "xmlab102/source.jpg"
            img_dir = (root / "imgs" / img_rel).parent
            key = img_dir.name
            if key not in mask_cache:
                label_path = img_dir / "mask.png"
                if not label_path.exists():
                    mask_cache[key] = None
                else:
                    lm = read_label_map(label_path)
                    binary = np.isin(lm, list(lesion))
                    if binary.sum() < min_lesion_pixels:
                        mask_cache[key] = None
                    else:
                        for lid in np.unique(lm[binary]):
                            report.lesion_pixels_by_label[labels.get(int(lid), str(lid))] += 1
                        dest = mask_out / f"{key}.png"
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        Image.fromarray((binary * 255).astype(np.uint8)).save(dest)
                        mask_cache[key] = str(dest)
            if mask_cache[key] is None:
                report.dropped["no lesion pixels in mask"] += 1
                continue
            cases.append(Case(
                case_id=f"slake_{q.get('qid', len(cases))}",
                patient_id=f"slake_{key}",
                dataset="slake",
                modality=str(q.get("modality", "unknown")).lower(),
                image_path=str(root / "imgs" / img_rel),
                question=q["question"],
                answer=str(q["answer"]),
                mask_path=mask_cache[key],
            ))
            report.kept[split] += 1
        out[split] = cases
    return out, report
