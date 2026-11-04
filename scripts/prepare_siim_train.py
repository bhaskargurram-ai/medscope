"""Post-hoc remedy data (MedScope v4.1): SIIM-ACR pneumothorax cases for training, validation and a new test set,
from patients that appear nowhere in the existing evaluation.

Every SIIM image used by the fresh external test (all its views, lesion images and lesion-free images) is excluded
by image UID and by DICOM patient id, and the remaining patients are split once, at random with a fixed seed, into
train / validation / test. Pneumothorax images keep the fresh external test's question and size rule (masks under
0.46% of the image, the 300-pixel rule at 256 px, are left out; masks over 20% too, as everywhere in training).

    python scripts/prepare_siim_train.py --siim DIR --exclude-views EXT2_VIEWS... --out DIR \
        [--train 150 --val 50 --test 100] [--seed 0]
    -> OUT/{train,val,test}/cases.jsonl, OUT/{train,val,test}/negatives.jsonl, OUT/report.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from medscope.data.loaders.extra import MAX_LESION_FRACTION, save_pair  # noqa: E402
from medscope.data.schema import Case, View, ViewKind  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402
from siim_fullres import read_dicom, read_rle, rle_to_mask  # noqa: E402

QUESTION = "Is there a pneumothorax in this chest X-ray?"
MIN_FRACTION = 300 / 256 ** 2
PREFIX = {"train": "siimtr", "val": "siimva", "test": "siimte"}


def patient_of(path: Path) -> str:
    try:
        import pydicom
        pid = str(pydicom.dcmread(str(path), stop_before_pixels=True).get("PatientID", "") or "")
    except Exception:  # noqa: BLE001 - unreadable header: the image is its own patient
        pid = ""
    return pid or path.stem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--siim", required=True)
    ap.add_argument("--exclude-views", nargs="+", required=True, help="views files whose SIIM images must not be used")
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", type=int, default=150, help="pneumothorax images (and as many lesion-free) for training")
    ap.add_argument("--val", type=int, default=50)
    ap.add_argument("--test", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out, root = Path(args.out), Path(args.siim)
    dicoms = {p.stem: p for p in root.rglob("*.dcm")}
    masks: dict[str, list[str]] = {}
    for f in [p for p in root.rglob("*.csv") if "rle" in p.name.lower()]:
        for uid, encs in read_rle(f).items():
            masks.setdefault(uid, [])
            masks[uid] += [e for e in encs if e not in masks[uid]]
    labelled = {uid for f in [p for p in root.rglob("*.csv") if "rle" in p.name.lower()]
                for uid in _all_ids(f)}           # images with a label row (with or without pneumothorax)
    used = {v.patient_id.removeprefix("siim_") for f in args.exclude_views for v in load_views(f)
            if v.patient_id.startswith("siim_")}
    stats: Counter = Counter()
    pid = {uid: patient_of(dicoms[uid]) for uid in sorted(labelled & set(dicoms))}
    banned = {pid[u] for u in used if u in pid}
    pos, neg = [], []
    for uid, p in pid.items():
        if uid in used or p in banned:
            stats["left out: image or patient in the existing evaluation"] += 1
            continue
        (pos if uid in masks else neg).append(uid)
    rng = np.random.default_rng(args.seed)
    rng.shuffle(pos)
    rng.shuffle(neg)
    need = {"train": args.train, "val": args.val, "test": args.test}
    split_of_patient: dict[str, str] = {}      # a patient's images all go to one split

    chosen_pos, chosen_neg = {s: [] for s in need}, {s: [] for s in need}
    for uid in pos:                                   # size rule before assignment
        if all(len(chosen_pos[s]) >= need[s] for s in need):
            break
        p = pid[uid]
        s = split_of_patient.get(p) or next((s for s in need if len(chosen_pos[s]) < need[s]), None)
        if s is None or len(chosen_pos[s]) >= need[s]:
            continue
        img = read_dicom(dicoms[uid])
        img_shape = img.shape[:2]
        m = np.zeros(img_shape, bool)
        for enc in masks[uid]:
            m |= rle_to_mask(enc, img_shape[1], img_shape[0])
        frac = m.mean()
        if frac < MIN_FRACTION:
            stats["pneumothorax under 0.46% of the image (thin rim, left out)"] += 1
            continue
        if frac > MAX_LESION_FRACTION:
            stats["pneumothorax over 20% of the image (left out, as in training)"] += 1
            continue
        split_of_patient[p] = s
        key = f"{PREFIX[s]}{len(chosen_pos[s]):05d}"
        ip, mp = save_pair(img, m, out / s / "images", key)
        chosen_pos[s].append(Case(case_id=f"{key}_ptx", patient_id=f"siim_{uid}", dataset=f"siim_{s}", modality="xray",
                                  image_path=ip, question=QUESTION, answer="Yes", answer_aliases=[], mask_path=mp,
                                  critical=True))
    for uid in neg:
        p = pid[uid]
        s = split_of_patient.get(p) or next((s for s in need if len(chosen_neg[s]) < need[s]), None)
        if s is None or len(chosen_neg[s]) >= need[s]:
            continue
        split_of_patient[p] = s
        key = f"{PREFIX[s]}{len(chosen_neg[s]):05d}neg"
        ip, _ = save_pair(read_dicom(dicoms[uid]), None, out / s / "images", key)
        chosen_neg[s].append(View(view_id=f"{key}_ptx__natural_negative", case_id=f"{key}_ptx", patient_id=f"siim_{uid}",
                                  kind=ViewKind.NATURAL_NEGATIVE, image_path=ip, question=QUESTION, answer="No",
                                  answer_aliases=[], lesion_box=None, critical=False,
                                  meta={"modality": "xray", "dataset": f"siim_{s}"}))
    for s in need:
        (out / s).mkdir(parents=True, exist_ok=True)
        (out / s / "cases.jsonl").write_text("".join(json.dumps(c.to_dict()) + "\n" for c in chosen_pos[s]))
        (out / s / "negatives.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in chosen_neg[s]))
        stats[f"{s}: pneumothorax images"] = len(chosen_pos[s])
        stats[f"{s}: lesion-free images"] = len(chosen_neg[s])
    patients = {s: {pid[c.patient_id.removeprefix('siim_')] for c in chosen_pos[s]}
                   | {pid[v.patient_id.removeprefix('siim_')] for v in chosen_neg[s]} for s in need}
    overlap = sum(len(patients[a] & patients[b]) for a in need for b in need if a < b)
    stats["patients shared between splits (must be 0)"] = overlap
    report = "\n".join(f"{k}: {n}" for k, n in sorted(stats.items()))
    (out / "report.txt").write_text(report + "\n")
    print(report)
    if overlap or any(len(chosen_pos[s]) < need[s] for s in need):
        raise SystemExit("not enough SIIM patients, or a patient in two splits: see the report")


def _all_ids(path: Path) -> set[str]:
    import csv
    with open(path, newline="") as f:
        return {({k.strip().lower(): v for k, v in r.items()}.get("imageid") or "").strip()
                for r in csv.DictReader(f)} - {""}


if __name__ == "__main__":
    main()
