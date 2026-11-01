"""Fresh external test set for v4: four public sources never used anywhere in this project before.

  etis     ETIS-LaribPolypDB (Clermont-Ferrand)  colonoscopy polyps     kinghoon/polyp-dataset (ETIS folder only)
  uclm     BUS-UCLM (Spain)                       breast ultrasound      MedOtter/BUS-UCLM
  men      BraTS 2023 meningioma                  brain MRI FLAIR        MedOtter/brats2023-men-dataset (3D, sliced)
  siim     SIIM-ACR pneumothorax                  chest X-ray            nwirandx/siim-pneumothorax-256-2400

None overlaps the training sources by institution, except that SIIM and ChestX-Det both draw on NIH ChestX-ray14:
near-copies of any training or existing test image are removed afterwards by check_views.py --dedup-against.
BraTS meningioma has no TCGA subjects (TCGA-LGG is a training source). BUS-UCLM images with on-screen calipers,
Doppler or combined modes are left out (marks would point to the erased lesion).

    python scripts/prepare_external2.py --out DIR --cache DIR --cap 50
    -> DIR/cases_test.jsonl, DIR/negatives/views_negatives_external.jsonl, DIR/external_report.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.loaders.extra import decode, lesion_fraction_ok, save_pair  # noqa: E402
from medscope.data.schema import Case, View, ViewKind  # noqa: E402

SOURCES = {
    "etis": {"modality": "endoscopy", "prefix": "etisext", "critical": False,
             "questions": [("polyp", "Is there a polyp in this image?"),
                           ("abn", "Is there an abnormality in this colonoscopy image?")]},
    "uclm": {"modality": "ultrasound", "prefix": "uclmext", "critical": False,
             "questions": [("lesion", "Is there a lesion in this breast ultrasound image?"),
                           ("mass", "Is there a breast mass in this ultrasound image?")]},
    "men": {"modality": "mri", "prefix": "bratsmenext", "critical": True,
            "questions": [("tumor", "Is there a tumor in this brain MRI slice?"),
                          ("abn", "Is there an abnormality in this brain MRI slice?")]},
    "siim": {"modality": "xray", "prefix": "siimext", "critical": True,
             "questions": [("ptx", "Is there a pneumothorax in this chest X-ray?"),
                           ("abn", "Is there an abnormality in this chest X-ray?")]},
}


def make_case(name: str, key: str, ip: str, mp: str, group: str) -> Case:
    s = SOURCES[name]
    tag, q = s["questions"][stable_index(key, len(s["questions"]))]
    return Case(case_id=f"{key}_{tag}", patient_id=group, dataset=f"external2_{name}", modality=s["modality"],
                image_path=ip, question=q, answer="Yes", answer_aliases=[], mask_path=mp, critical=s["critical"])


def make_negative(name: str, key: str, ip: str, group: str) -> View:
    s = SOURCES[name]
    tag, q = s["questions"][stable_index(key + "n", len(s["questions"]))]
    case_id = f"{key}neg_{tag}"
    return View(view_id=f"{case_id}__natural_negative", case_id=case_id, patient_id=group,
                kind=ViewKind.NATURAL_NEGATIVE, image_path=ip, question=q, answer="No", answer_aliases=[],
                lesion_box=None, critical=False, meta={"modality": s["modality"], "dataset": f"external2_{name}"})


def parquet_rows(repo: str, cache: Path):
    from huggingface_hub import snapshot_download
    import pyarrow.parquet as pq
    root = Path(snapshot_download(repo, repo_type="dataset", allow_patterns=["*.parquet", "**/*.parquet"],
                                  local_dir=str(cache / repo.replace("/", "__"))))
    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no parquet files in {repo}")
    for f in files:
        for batch in pq.ParquetFile(f).iter_batches(batch_size=64):
            yield from batch.to_pylist()


def binary_mask(cell, shape) -> np.ndarray | None:
    m = decode(cell)
    if m is None:
        return None
    m = np.asarray(m)
    if m.ndim == 3:
        m = m.max(axis=-1)
    m = m > 127 if m.max() > 1 else m > 0
    if m.shape != tuple(shape):
        m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.NEAREST)) > 127
    return m


def collect(name: str, items, out: Path, cap: int, stats: Counter):
    """items: (sort key, image, mask or None for a lesion-free image, group) -> cases and negatives."""
    pre = SOURCES[name]["prefix"]
    cases, negs = [], []
    for k, (_, img, mask, group) in enumerate(sorted(items, key=lambda t: stable_index(t[0], 10 ** 9))):
        if len(cases) >= cap and len(negs) >= cap:
            break
        key = f"{pre}{k:05d}"
        if mask is None:
            if len(negs) < cap:
                ip, _ = save_pair(img, None, out / name, key)
                negs.append(make_negative(name, key, ip, group))
            continue
        if len(cases) >= cap:
            continue
        if not lesion_fraction_ok(mask):
            stats[f"{name}: lesion too small or too large to erase"] += 1
            continue
        ip, mp = save_pair(img, mask, out / name, key)
        cases.append(make_case(name, key, ip, mp, group))
    return cases, negs


def uclm(cache: Path, stats: Counter):
    for row in parquet_rows("MedOtter/BUS-UCLM", cache):
        if row.get("has_marks") or row.get("has_doppler") or row.get("has_combined"):
            stats["uclm: calipers, Doppler or combined mode (left out)"] += 1
            continue
        img = np.asarray(decode(row["image"]))
        label = str(row.get("class_label", "")).lower()
        group = f"uclm_{row.get('patient_id', row.get('image_id'))}"
        if label == "normal":
            yield str(row.get("image_id")), img, None, group
            continue
        mask = binary_mask(row.get("mask"), img.shape[:2])
        if mask is None or not mask.any():
            stats["uclm: lesion image without a mask"] += 1
            continue
        yield str(row.get("image_id")), img, mask, group


def siim(cache: Path, stats: Counter, min_area: int = 300):
    for row in parquet_rows("nwirandx/siim-pneumothorax-256-2400", cache):
        img = np.asarray(decode(row["image"]))
        uid = str(row.get("image_id"))
        if not row.get("has_pneumo"):
            yield uid, img, None, f"siim_{uid}"
            continue
        if (row.get("mask_area") or 0) < min_area:
            stats["siim: pneumothorax under 300 pixels (thin rim, left out)"] += 1
            continue
        mask = binary_mask(row.get("mask"), img.shape[:2])
        if mask is None or not mask.any():
            continue
        yield uid, img, mask, f"siim_{uid}"


def etis(cache: Path, stats: Counter):
    from huggingface_hub import snapshot_download
    root = Path(snapshot_download("kinghoon/polyp-dataset", repo_type="dataset", allow_patterns=["ETIS-LaribPolypDB/*", "ETIS-LaribPolypDB/**"],
                                  local_dir=str(cache / "kinghoon_polyp")))
    imgs = {p.stem: p for p in root.rglob("*") if p.parent.name.lower() == "images" and p.suffix.lower() in (".png", ".jpg", ".tif")}
    masks = {p.stem: p for p in root.rglob("*") if p.parent.name.lower() == "masks" and p.suffix.lower() in (".png", ".jpg", ".tif")}
    pairs = [(imgs[k], masks[k]) for k in sorted(imgs) if k in masks]
    if not pairs:
        raise FileNotFoundError(f"no ETIS image/mask pairs under {root}")
    for ip, mp in pairs:
        img = np.asarray(Image.open(ip).convert("RGB"))
        mask = np.asarray(Image.open(mp).convert("L")) > 127
        if mask.shape != img.shape[:2]:
            mask = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((img.shape[1], img.shape[0]), Image.NEAREST)) > 127
        if mask.any():
            yield f"etis{ip.stem}", img, mask, f"etis_{ip.stem}"


def meningioma(cache: Path, stats: Counter, n_cases: int):
    """One tumour slice and one tumour-free slice per patient (first timepoint), from the 3D volumes."""
    import nibabel as nib
    from huggingface_hub import HfApi, hf_hub_download
    from medscope.data.loaders.external import slices_from_volume, to_uint8
    repo = "MedOtter/brats2023-men-dataset"
    files = HfApi().list_repo_files(repo, repo_type="dataset")
    flairs = sorted(f for f in files if f.endswith("t2f.nii.gz"))
    by_case: dict[str, str] = {}
    for f in flairs:                                  # the "-Fix" copy wins over the original of a case
        case = Path(f).name.replace("-t2f.nii.gz", "")
        if case not in by_case or "Fix" in f:
            by_case[case] = f
    patients: dict[str, str] = {}
    for case in sorted(by_case):                      # BraTS-MEN-00012-000 -> patient BraTS-MEN-00012, first timepoint
        patients.setdefault(case.rsplit("-", 1)[0], case)
    chosen = sorted(patients.values(), key=lambda c: stable_index(c, 10 ** 9))[:n_cases]
    for case in chosen:
        f = by_case[case]
        seg_f = f.replace("t2f.nii.gz", "seg.nii.gz")
        if seg_f not in files:
            continue
        local = [hf_hub_download(repo, x, repo_type="dataset", cache_dir=str(cache / "hf")) for x in (f, seg_f)]
        flair = np.asarray(nib.load(local[0]).get_fdata(), dtype=np.float32)
        seg = np.asarray(nib.load(local[1]).get_fdata())
        lo, hi = np.percentile(flair[flair > 0], [0.5, 99.5]) if (flair > 0).any() else (0, 1)
        pos, neg = slices_from_volume(flair, seg)
        group = f"men_{case.rsplit('-', 1)[0]}"
        if pos is not None:
            yield case, np.rot90(to_uint8(flair[:, :, pos], lo, hi)), np.rot90(seg[:, :, pos] > 0), group
        if neg is not None:
            yield case + "n", np.rot90(to_uint8(flair[:, :, neg], lo, hi)), None, group


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--cap", type=int, default=50, help="lesion images (and lesion-free images) per source")
    ap.add_argument("--sources", nargs="+", default=list(SOURCES), choices=list(SOURCES))
    args = ap.parse_args()
    out, cache = Path(args.out), Path(args.cache)
    out.mkdir(parents=True, exist_ok=True)
    stats: Counter = Counter()
    readers = {"uclm": lambda: uclm(cache, stats), "siim": lambda: siim(cache, stats),
               "etis": lambda: etis(cache, stats), "men": lambda: meningioma(cache, stats, n_cases=2 * args.cap)}
    cases, negs, lines = [], [], []
    for name in args.sources:
        print(f"{name}: preparing", flush=True)
        try:
            c, n = collect(name, list(readers[name]()), out / "images", args.cap, stats)
        except Exception as e:  # noqa: BLE001 - one unavailable source must not block the others
            lines.append(f"{name}: FAILED ({type(e).__name__}: {e})")
            print(lines[-1], flush=True)
            continue
        cases += c
        negs += n
        lines.append(f"{name}: {len(c)} lesion images, {len(n)} lesion-free images")
        print(lines[-1], flush=True)
    (out / "cases_test.jsonl").write_text("".join(json.dumps(c.to_dict()) + "\n" for c in cases))
    (out / "negatives").mkdir(exist_ok=True)
    (out / "negatives" / "views_negatives_external.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in negs))
    lines.append(f"details: {dict(stats)}")
    (out / "external_report.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not cases:
        raise SystemExit("no fresh external data could be prepared")


if __name__ == "__main__":
    main()
