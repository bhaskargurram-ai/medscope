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


# Ways a mask.png might store the class id of each pixel. SLAKE's exact encoding is
# detected from the data: the one whose values best match the ids in mask.txt wins.
ENCODINGS = ("single", "red", "green", "blue", "luma")
MIN_FIT = 0.95  # share of pixels whose decoded value is background (0) or a known id


def _raw(path: str | Path) -> np.ndarray:
    """Pixels as stored. Palette ('P') images give their index array, which is the label."""
    with Image.open(path) as img:
        return np.asarray(img).copy()


def _mode(path: str | Path) -> str:
    with Image.open(path) as img:
        return img.mode


def decode(arr: np.ndarray, encoding: str) -> np.ndarray:
    if arr.ndim == 2:
        return arr
    rgb = arr[..., :3]
    if encoding == "single":
        if not (np.array_equal(rgb[..., 0], rgb[..., 1]) and np.array_equal(rgb[..., 0], rgb[..., 2])):
            return np.full(rgb.shape[:2], -1, dtype=np.int32)  # not a grey image: fits nothing
        return rgb[..., 0]
    if encoding in ("red", "green", "blue"):
        return rgb[..., ("red", "green", "blue").index(encoding)]
    if encoding == "luma":
        return np.asarray(Image.fromarray(np.ascontiguousarray(rgb)).convert("L"))
    raise ValueError(f"unknown encoding {encoding!r}")


def fit(values: np.ndarray, known: set[int]) -> tuple[float, int]:
    """(share of pixels that are 0 or a known id, number of distinct known non-zero ids seen)."""
    ids, counts = np.unique(values, return_counts=True)
    ok = sum(int(c) for i, c in zip(ids, counts) if int(i) == 0 or int(i) in known)
    seen = sum(1 for i in ids if int(i) != 0 and int(i) in known)
    return ok / max(1, int(counts.sum())), seen


def colour_summary(arr: np.ndarray, top: int = 12) -> str:
    flat = arr.reshape(-1, arr.shape[-1]) if arr.ndim == 3 else arr.reshape(-1, 1)
    colours, counts = np.unique(flat, axis=0, return_counts=True)
    order = np.argsort(-counts)[:top]
    return ", ".join(f"{tuple(int(v) for v in colours[i])}: {int(counts[i])} px" for i in order)


def detect_encoding(mask_paths: list[Path], known: set[int]) -> tuple[str, str]:
    """Pick the encoding that fits a sample of masks best. Returns (encoding, explanation)."""
    if not mask_paths:
        raise ValueError("no mask.png files found to inspect")
    arrays = [_raw(p) for p in mask_paths]
    scores = {}
    for enc in ENCODINGS:
        fits = [fit(decode(a, enc), known) for a in arrays]
        # median, not mean: a few odd masks must not hide an encoding that fits the rest;
        # those odd masks are dropped one by one in load_slake
        scores[enc] = (float(np.median([f for f, _ in fits])), sum(s for _, s in fits))
    best = max(scores, key=lambda e: (scores[e][0] >= MIN_FIT, scores[e][1] > 0, scores[e][0], scores[e][1]))
    table = "; ".join(f"{e}: median {scores[e][0]:.1%} pixels fit, {scores[e][1]} ids seen" for e in ENCODINGS)
    if scores[best][0] < MIN_FIT or scores[best][1] == 0:
        raise ValueError(
            "could not work out how mask.png stores class ids.\n"
            f"  tried: {table}\n"
            f"  known ids from mask.txt: {sorted(known)}\n"
            f"  first mask {mask_paths[0]}: mode {_mode(mask_paths[0])}, shape {arrays[0].shape}\n"
            f"  its most common colours: {colour_summary(arrays[0])}")
    return best, f"mask encoding '{best}' ({table})"


def read_label_map(path: str | Path, encoding: str = "single") -> np.ndarray:
    return decode(_raw(path), encoding)


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
    encoding: str = ""

    def summary(self) -> str:
        lines = [self.encoding, f"questions seen: {self.questions_seen}",
                 f"kept per split: {dict(self.kept)}",
                 f"dropped by reason: {dict(self.dropped)}",
                 "lesion labels found (images): " + ", ".join(
                     f"{k}={v}" for k, v in self.lesion_pixels_by_label.most_common())]
        return "\n".join(lines)


PER_MASK_MIN_FIT = 0.9  # a mask whose decoded values mostly aren't known ids is skipped

# ---- question generation from masks ---------------------------------------------------

ORGAN_WORDS = ("Brain", "Liver", "Kidney", "Lung")
CRITICAL_WORDS = ("cancer", "tumor", "tumour")


def lesion_organ(name: str) -> str:
    for organ in ORGAN_WORDS:
        if organ.lower() in name.lower():
            return organ
    return name.split()[0].title()


def lesion_finding(name: str) -> str:
    n = name.lower()
    if "edema" in n or "oedema" in n:
        return "edema"
    if "cancer" in n or "tumor" in n or "tumour" in n:
        return "a tumor"
    return "a lesion"


def template_questions(main_label: str) -> list[tuple[str, str, list[str], str]]:
    """(tag, question, answer, aliases) generated from the dominant lesion label.

    Only questions whose correct answer depends on the lesion being visible, so that
    removing it removes the evidence."""
    organ, finding = lesion_organ(main_label), lesion_finding(main_label)
    return [
        ("abn", "Is there an abnormality in this image?", "Yes", []),
        ("organ", "Which organ shows an abnormality in this image?", organ, [f"the {organ.lower()}", f"{organ.lower()}s"]),
        ("finding", f"Is there {finding} in the {organ.lower()}?", "Yes", []),
    ]


@dataclass
class ImageRecord:
    key: str                 # e.g. "xmlab102"
    image_path: str
    mask_path: str           # binary lesion mask written by the loader
    main_label: str          # lesion class with the most pixels
    modality: str
    critical: bool
    slake_questions: list[dict] = field(default_factory=list)


def scan_lesion_images(root: str | Path, mask_out: str | Path, encoding: str = "red",
                       min_lesion_pixels: int = 20, max_lesion_fraction: float = 0.2) -> tuple[list[ImageRecord], Counter, str]:
    """Every SLAKE image whose mask contains lesion pixels, with SLAKE's own positive questions attached.

    Lesions covering more than `max_lesion_fraction` of the image are skipped: erasing a
    lesion that large cannot be done convincingly and makes edits easy to spot.
    """
    root, mask_out = Path(root), Path(mask_out)
    labels = parse_mask_labels(root / "mask.txt")
    lesion = lesion_ids(labels)
    known = set(labels)
    stats: Counter = Counter()
    unknown_values: Counter = Counter()

    questions: dict[str, list[dict]] = {}
    modality: dict[str, str] = {}
    for fname in SPLIT_FILES.values():
        p = root / fname
        if p.exists():
            for q in json.loads(p.read_text(encoding="utf-8")):
                key = Path(q["img_name"]).parent.name
                modality.setdefault(key, str(q.get("modality", "unknown")).lower())
                if keep_question(q):
                    questions.setdefault(key, []).append(q)

    records = []
    for mask_file in sorted((root / "imgs").glob("*/mask.png")):
        key = mask_file.parent.name
        stats["masks"] += 1
        lm = read_label_map(mask_file, encoding)
        share, _ = fit(lm, known)
        if share < PER_MASK_MIN_FIT:
            stats["mask values don't match mask.txt"] += 1
            vals, cnts = np.unique(lm, return_counts=True)
            for v, c in zip(vals, cnts):
                if int(v) != 0 and int(v) not in known:
                    unknown_values[int(v)] += int(c)
            continue
        binary = np.isin(lm, list(lesion))
        if binary.sum() < min_lesion_pixels:
            stats["no lesion"] += 1
            continue
        if binary.mean() > max_lesion_fraction:
            stats["lesion too large to erase"] += 1
            continue
        ids, counts = np.unique(lm[binary], return_counts=True)
        main = labels[int(ids[np.argmax(counts)])]
        dest = mask_out / f"{key}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray((binary * 255).astype(np.uint8)).save(dest)
        image_path = mask_file.parent / "source.jpg"
        if not image_path.exists():
            stats["no source image"] += 1
            continue
        records.append(ImageRecord(
            key=key, image_path=str(image_path), mask_path=str(dest), main_label=main,
            modality=modality.get(key, "unknown"),
            critical=any(any(w in labels[int(i)].lower() for w in CRITICAL_WORDS) for i in ids),
            slake_questions=questions.get(key, [])))
        stats[f"kept: {main}"] += 1
    note = ""
    if unknown_values:
        note = "values not in mask.txt (pixels): " + ", ".join(f"{v}={c}" for v, c in unknown_values.most_common(6))
    return records, stats, note


def cases_for_image(rec: ImageRecord, split: str, group: int, max_train_cases: int = 3) -> list[Case]:
    """Train: several questions per image. Validation/test: exactly one, chosen deterministically."""
    from .common import stable_index

    options = [(f"q{q.get('qid')}", q["question"], str(q["answer"]), []) for q in rec.slake_questions]
    options += template_questions(rec.main_label)
    if split == "train":
        chosen = (options[:1] if rec.slake_questions else []) + template_questions(rec.main_label)
        chosen = chosen[:max_train_cases]
    else:
        chosen = [options[stable_index(rec.key, len(options))]]
    return [Case(case_id=f"slake_{rec.key}_{tag}", patient_id=f"slake_g{group}", dataset="slake",
                 modality=rec.modality, image_path=rec.image_path, question=question, answer=answer,
                 answer_aliases=aliases, mask_path=rec.mask_path, critical=rec.critical)
            for tag, question, answer, aliases in chosen]


def load_slake(root: str | Path, mask_out: str | Path, min_lesion_pixels: int = 20,
               encoding: str = "auto") -> tuple[dict[str, list[Case]], SlakeReport]:
    """Return {split: [Case]} and a report. Binary lesion masks are written to mask_out."""
    root, mask_out = Path(root), Path(mask_out)
    labels = parse_mask_labels(root / "mask.txt")
    lesion = lesion_ids(labels)
    if not lesion:
        raise ValueError("mask.txt has no lesion classes; check LESION_WORDS against it")

    report = SlakeReport()
    if encoding == "auto":
        sample = sorted((root / "imgs").glob("*/mask.png"))[:40]
        encoding, report.encoding = detect_encoding(sample, set(labels))
    elif encoding in ENCODINGS:
        report.encoding = f"mask encoding '{encoding}' (set by hand)"
    else:
        raise ValueError(f"encoding must be 'auto' or one of {ENCODINGS}")
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
                    lm = read_label_map(label_path, encoding)
                    binary = np.isin(lm, list(lesion))
                    if fit(lm, set(labels))[0] < PER_MASK_MIN_FIT:
                        mask_cache[key] = "bad"
                    elif binary.sum() < min_lesion_pixels:
                        mask_cache[key] = None
                    else:
                        for lid in np.unique(lm[binary]):
                            report.lesion_pixels_by_label[labels.get(int(lid), str(lid))] += 1
                        dest = mask_out / f"{key}.png"
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        Image.fromarray((binary * 255).astype(np.uint8)).save(dest)
                        mask_cache[key] = str(dest)
            if mask_cache[key] == "bad":
                report.dropped["mask values don't match mask.txt"] += 1
                continue
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
