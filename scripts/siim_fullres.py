"""Post-hoc analysis (not part of the pre-registered evaluation): the SIIM pneumothorax cases of the fresh external
test, rebuilt from the original full-resolution SIIM-ACR images (1024 x 1024 DICOM, run-length-encoded masks).

The fresh external test used a 256-pixel copy of SIIM (nwirandx/siim-pneumothorax-256-2400), on which every
Qwen-based model, MedScope included, missed nearly all pneumothoraxes. Rebuilding exactly the same images at their
original resolution tests whether resolution is the cause. No model is changed.

Images are matched by their SIIM image UID (kept as the patient id of every SIIM view). Case ids get the prefix
"siimfull" in place of "siimext"; questions, answers and the lesion-free images are the same.

    python scripts/siim_fullres.py --views EXT2_VIEWS... --siim DIR --out DIR
    DIR (--siim): the SIIM-ACR data with *.dcm files named by image UID and a train-rle.csv (ImageId, EncodedPixels)
    -> OUT/cases_test.jsonl, OUT/negatives/views_negatives_external.jsonl, OUT/report.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders.extra import save_pair  # noqa: E402
from medscope.data.schema import Case, ViewKind  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def rle_to_mask(rle: str, width: int, height: int) -> np.ndarray:
    """SIIM-ACR run-length encoding: relative starts, column-major (the competition's mask_functions.rle2mask)."""
    mask = np.zeros(width * height, dtype=np.uint8)
    nums = [int(x) for x in rle.split()]
    pos = 0
    for start, length in zip(nums[0::2], nums[1::2]):
        pos += start
        mask[pos:pos + length] = 1
        pos += length
    return mask.reshape(width, height).T.astype(bool)


def read_rle(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            keys = {k.strip().lower(): v for k, v in row.items()}
            uid, enc = keys.get("imageid"), (keys.get("encodedpixels") or "").strip()
            if uid and enc and enc != "-1":
                out[uid.strip()].append(enc)
    return out


def read_dicom(path: Path) -> np.ndarray:
    import pydicom
    a = pydicom.dcmread(str(path)).pixel_array.astype(np.float32)
    if a.max() > 255:
        a = (a - a.min()) / max(1.0, a.max() - a.min()) * 255
    return a.clip(0, 255).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True, help="fresh external views files (cases and negatives)")
    ap.add_argument("--siim", required=True, help="folder with the original SIIM-ACR DICOMs and train-rle.csv")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out, root = Path(args.out), Path(args.siim)
    dicoms = {p.stem: p for p in root.rglob("*.dcm")}
    rles = [p for p in root.rglob("*.csv") if "rle" in p.name.lower()]
    if not dicoms or not rles:
        raise SystemExit(f"need *.dcm files and a *rle*.csv under {root} (found {len(dicoms)} DICOMs, {len(rles)} csv)")
    masks: dict[str, list[str]] = {}
    for f in rles:                  # every RLE file found (some copies split the labels over several files)
        for uid, encs in read_rle(f).items():
            masks.setdefault(uid, [])
            masks[uid] += [e for e in encs if e not in masks[uid]]
    views = [v for f in args.views for v in load_views(f) if v.case_id.startswith("siimext")]
    stats: Counter = Counter()
    cases, negs = [], []
    for v in views:
        uid = v.patient_id.removeprefix("siim_")
        new_id = v.case_id.replace("siimext", "siimfull", 1)
        key = new_id.split("_")[0]
        if v.kind is ViewKind.ORIGINAL:
            if uid not in dicoms or uid not in masks:
                stats["lesion image: UID not found in the full-resolution data"] += 1
                continue
            img = read_dicom(dicoms[uid])
            m = np.zeros(img.shape[:2], bool)
            for enc in masks[uid]:
                m |= rle_to_mask(enc, img.shape[1], img.shape[0])
            ip, mp = save_pair(img, m, out / "images", key)
            cases.append(Case(case_id=new_id, patient_id=v.patient_id, dataset="external2_siim_full", modality="xray",
                              image_path=ip, question=v.question, answer=v.answer, answer_aliases=v.answer_aliases,
                              mask_path=mp, critical=v.critical))
            stats["lesion images"] += 1
        elif v.kind is ViewKind.NATURAL_NEGATIVE:
            if uid not in dicoms:
                stats["lesion-free image: UID not found in the full-resolution data"] += 1
                continue
            if uid in masks:
                stats["lesion-free image has a mask in the full data (left out)"] += 1
                continue
            ip, _ = save_pair(read_dicom(dicoms[uid]), None, out / "images", key)
            negs.append(replace(v, view_id=v.view_id.replace("siimext", "siimfull", 1), case_id=new_id, image_path=ip))
            stats["lesion-free images"] += 1
    (out / "negatives").mkdir(parents=True, exist_ok=True)
    (out / "cases_test.jsonl").write_text("".join(json.dumps(c.to_dict()) + "\n" for c in cases))
    (out / "negatives" / "views_negatives_external.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in negs))
    report = "\n".join(f"{k}: {n}" for k, n in sorted(stats.items()))
    (out / "report.txt").write_text(report + "\n")
    print(report)
    if not cases:
        raise SystemExit("no SIIM case matched the full-resolution data")


if __name__ == "__main__":
    main()
