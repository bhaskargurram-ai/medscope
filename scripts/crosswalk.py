"""Cross-set crosswalk: do any two sets share an image, a near-copy, a case id or a patient id?

Several sources share an origin (ChestX-Det and SIIM-ACR both come from NIH ChestX-ray14; Kvasir-SEG from
HyperKvasir; BraTS 2020/2021 from TCGA, which is why they were not used). Identifiers do not cross datasets, so this
script compares the images themselves: a 64-bit difference hash on every original or lesion-free image of every
set, hash matches confirmed by pixel correlation (the repository's near-copy test: Hamming distance <= 4 and
correlation >= 0.98 at 64 px), plus a looser tier (distance <= 8, correlation >= 0.90) that catches the same study
at another resolution or crop. It also reports case-id and patient/group-id overlap between every pair of sets.

    python scripts/crosswalk.py --set "Training=VIEWS... " --set "Main test=VIEWS..." ... --out crosswalk.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.quality import correlation, dhash  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

STRICT = (4, 0.98)
LOOSE = (8, 0.90)
UNEDITED = ("original", "natural_negative")


def images_of(files: list[str]) -> dict[str, dict]:
    """image path -> {case, patient} for every unedited image (originals and lesion-free) of the set."""
    out: dict[str, dict] = {}
    for f in files:
        for v in load_views(f):
            if v.kind.value in UNEDITED and v.image_path not in out and Path(v.image_path).exists():
                out[v.image_path] = {"case": v.case_id, "patient": v.patient_id}
    return out


def source(case_id: str) -> str:
    """The dataset prefix of a case id (letters before the first digit or underscore)."""
    head = case_id.split("_")[0]
    letters = head[:next((i for i, ch in enumerate(head) if not ch.isalpha()), len(head))]
    return letters or head


def candidate_pairs(ha: np.ndarray, hb: np.ndarray, max_distance: int, chunk: int = 512) -> list[tuple[int, int, int]]:
    """(i, j, distance) for every hash of A within max_distance bits of a hash of B, vectorised in chunks."""
    out = []
    for start in range(0, len(ha), chunk):
        x = ha[start:start + chunk, None] ^ hb[None, :]                                  # (chunk, m) uint64
        d = np.unpackbits(x.view(np.uint8).reshape(x.shape[0], x.shape[1], 8), axis=2).sum(axis=2)
        for i, j in zip(*np.nonzero(d <= max_distance)):
            out.append((start + int(i), int(j), int(d[i, j])))
    return out


def matches(sets: dict[str, dict[str, dict]], hashes: dict[str, int], a: str, b: str):
    pa_list, pb_list = list(sets[a]), list(sets[b])
    ha = np.array([hashes[p] for p in pa_list], dtype=np.uint64)
    hb = np.array([hashes[p] for p in pb_list], dtype=np.uint64)
    same, near = [], []
    if len(ha) and len(hb):
        for i, j, d in candidate_pairs(ha, hb, LOOSE[0]):
            pa, pb = pa_list[i], pb_list[j]
            if pa == pb:
                continue
            c = correlation(load_image(pa), load_image(pb))
            if d <= STRICT[0] and c >= STRICT[1]:
                same.append((pa, pb, d, c))
            elif c >= LOOSE[1]:
                near.append((pa, pb, d, c))
    return same, near


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", action="append", required=True, metavar="NAME=VIEWS_FILES")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sets: dict[str, dict[str, dict]] = {}
    for spec in args.set:
        name, files = spec.split("=", 1)
        sets[name] = images_of([f for f in files.split() if Path(f).exists()])
        print(f"{name}: {len(sets[name])} images", flush=True)
    hashes: dict[str, int] = {}
    for name, imgs in sets.items():
        for i, p in enumerate(imgs):
            if p not in hashes:
                hashes[p] = dhash(load_image(p))
            if i % 1000 == 999:
                print(f"  {name}: hashed {i + 1}", flush=True)
    names = list(sets)
    out = ["# Cross-set crosswalk", "",
           "Every unedited image of every set (originals and lesion-free images) compared with every image of every other set. "
           "Same image: difference hash within 4 bits and pixel correlation >= 0.98 at 64 px (the repository's near-copy "
           "test). Near: within 8 bits and correlation >= 0.90 (the same study at another size or crop, or a very similar "
           "image). Identifier overlap is the number of case ids and patient/group ids the two sets share.", "",
           "| Set | Images | Cases | Patients or groups |", "| --- | --- | --- | --- |"]
    for n in names:
        out.append(f"| {n} | {len(sets[n])} | {len({m['case'] for m in sets[n].values()})} | "
                   f"{len({m['patient'] for m in sets[n].values()})} |")
    out += ["", "| Set A | Set B | Same image | Near | Shared case ids | Shared patient/group ids |",
            "| --- | --- | --- | --- | --- | --- |"]
    details, pairs = [], []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            same, near = matches(sets, hashes, a, b)
            cases = {m["case"] for m in sets[a].values()} & {m["case"] for m in sets[b].values()}
            pats = {m["patient"] for m in sets[a].values()} & {m["patient"] for m in sets[b].values()}
            out.append(f"| {a} | {b} | {len(same)} | {len(near)} | {len(cases)} | {len(pats)} |")
            print(f"{a} vs {b}: {len(same)} same, {len(near)} near, {len(cases)} shared cases, {len(pats)} shared patients", flush=True)
            for pa, pb, d, c in same + near:
                pairs.append((a, b, pa, pb, d, c))
                details.append(f"| {a} | {b} | {sets[a][pa]['case']} ({sets[a][pa]['patient']}) | {sets[b][pb]['case']} "
                               f"({sets[b][pb]['patient']}) | {d} | {c:.3f} |")
    if details:
        by_src: dict[tuple[str, str], list[float]] = {}
        for a, b, pa, pb, d, c in pairs:
            by_src.setdefault((source(sets[a][pa]["case"]), source(sets[b][pb]["case"])), []).append(c)
        out += ["", "## Near-tier calibration by source", "",
                "Pairs of sources that cannot share a patient (different datasets from different hospitals, or different "
                "patients of one dataset split by patient id) show how high the correlation of two different images of the "
                "same anatomy gets at 64 px; a cross-dataset pair below that level is not evidence of a shared study.", "",
                "| Source A | Source B | Pairs | Highest correlation | Pairs at or above 0.95 |", "| --- | --- | --- | --- | --- |"]
        for (sa, sb), cs in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
            out.append(f"| {sa} | {sb} | {len(cs)} | {max(cs):.3f} | {sum(c >= 0.95 for c in cs)} |")
        out += ["", "## Matches", "",
                "| Set A | Set B | Image A: case (patient) | Image B: case (patient) | Hash distance | Correlation |",
                "| --- | --- | --- | --- | --- | --- |"] + details
    else:
        out += ["", "No image of any set matches an image of another set at either tier."]
    out += ["", "What this does and does not show: a match at the strict tier is the same picture; the near tier catches "
            "the same study re-sized or cropped. Different images of one patient taken on different days look different "
            "and are not caught; across datasets that re-identify the same hospital's patients under new ids (SIIM-ACR and "
            "ChestX-Det both draw on NIH ChestX-ray14), such overlap cannot be excluded without the source's own ids, "
            "which SIIM-ACR does not carry."]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
