"""Lesion-insertion views for v4 training: a real lesion moved into a healthy image of the same kind.

Erasure views teach "edited and the lesion is gone -> absent". If every edit in training meant "absent",
a model could learn to answer from the edit itself. Insertion views carry an edit too, but the answer is
"present" with the inserted lesion's box, so an edit trace on its own says nothing about the answer.

For each training lesion case (up to --max-per-dataset per imaging type) the lesion, cut out with its expert
mask, is scaled to the same share of the image and Poisson-blended (OpenCV seamlessClone) into a random
tissue position of a lesion-free TRAINING image from the same source family. A view is kept only if the
inserted lesion stands out from its new surroundings (the same contrast measure the erasure check uses).
Used for training only; never for evaluation.

    python scripts/insert_lesions.py --views TRAIN_VIEWS... --negatives TRAIN_NEG... --out DIR
    -> DIR/views.jsonl (kind original, meta.inserted = true), DIR/<case>/inserted.png
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.colab import dataset_of  # noqa: E402
from medscope.data.counterfactual import dilate, foreground_mask  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.quality import region_contrast  # noqa: E402
from medscope.data.schema import View, ViewKind, mask_to_box  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def _mask(path: str, shape) -> np.ndarray:
    m = np.asarray(Image.open(path).convert("L"))
    if m.shape != tuple(shape):
        m = np.asarray(Image.fromarray(m).resize((shape[1], shape[0]), Image.NEAREST))
    return m > 127


def insert(src: np.ndarray, lesion: np.ndarray, host: np.ndarray, rng: np.random.Generator,
           min_contrast: float = 1.0, max_tries: int = 25, margin: int = 6):
    """(edited host image, placed lesion mask) or None if no position works.

    The lesion is cut out with a `margin`-pixel ring of its own surrounding tissue, so its edges travel
    with it; Poisson blending then matches that ring to the host while the lesion keeps its contrast."""
    ext = dilate(lesion, margin)
    ys, xs = np.nonzero(ext)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    patch, emask, lmask = src[y0:y1, x0:x1], ext[y0:y1, x0:x1], lesion[y0:y1, x0:x1]
    scale = np.sqrt(host.shape[0] * host.shape[1] / (src.shape[0] * src.shape[1]))
    ph, pw = max(4, round(patch.shape[0] * scale)), max(4, round(patch.shape[1] * scale))
    h, w = host.shape[:2]
    if ph >= h - 4 or pw >= w - 4:
        return None
    patch = cv2.resize(patch, (pw, ph), interpolation=cv2.INTER_LINEAR)
    emask = cv2.resize(emask.astype(np.uint8), (pw, ph), interpolation=cv2.INTER_NEAREST).astype(bool)
    lmask = cv2.resize(lmask.astype(np.uint8), (pw, ph), interpolation=cv2.INTER_NEAREST).astype(bool)
    if not lmask.any():
        return None
    tissue = foreground_mask(host)
    for _ in range(max_tries):
        ty, tx = int(rng.integers(2, h - ph - 1)), int(rng.integers(2, w - pw - 1))
        if (tissue[ty:ty + ph, tx:tx + pw] & emask).sum() < 0.9 * emask.sum():
            continue
        src_full = host.copy()
        src_full[ty:ty + ph, tx:tx + pw] = np.where(emask[..., None], patch, host[ty:ty + ph, tx:tx + pw])
        clone = np.zeros(host.shape[:2], bool)
        clone[ty:ty + ph, tx:tx + pw] = emask
        placed = np.zeros(host.shape[:2], bool)
        placed[ty:ty + ph, tx:tx + pw] = lmask
        bx, by, bw, bh = cv2.boundingRect(clone.astype(np.uint8))
        if bx < 1 or by < 1 or bx + bw > w - 1 or by + bh > h - 1:
            continue
        out = cv2.seamlessClone(src_full, host, clone.astype(np.uint8) * 255, (bx + bw // 2, by + bh // 2),
                                cv2.NORMAL_CLONE)
        out = np.where(clone[..., None], out, host)
        if region_contrast(out, placed) < min_contrast:
            continue
        if np.array_equal(host[..., 0], host[..., 1]) and np.array_equal(host[..., 1], host[..., 2]):
            g = np.round(out.astype(np.float32).mean(-1)).astype(np.uint8)
            out = np.stack([g] * 3, -1)
        return out, placed
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True, help="training views (originals with lesion masks are used)")
    ap.add_argument("--negatives", nargs="+", required=True, help="training natural negatives (host images)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-per-dataset", type=int, default=300)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    hosts = defaultdict(list)
    for v in (v for f in args.negatives for v in load_views(f)):
        if v.kind is ViewKind.NATURAL_NEGATIVE:
            hosts[dataset_of(v.case_id)].append(v)
    srcs = defaultdict(list)
    for v in (v for f in args.views for v in load_views(f)):
        if v.kind is ViewKind.ORIGINAL and (v.meta or {}).get("lesion_mask") and v.lesion_box:
            srcs[dataset_of(v.case_id)].append(v)
    views, stats = [], Counter()
    for ds, vs in sorted(srcs.items()):
        if not hosts.get(ds):
            stats[f"{ds}: no lesion-free training images to host insertions"] += len(vs)
            continue
        vs = sorted(vs, key=lambda v: stable_index(v.case_id + "ins", 10 ** 9))[:args.max_per_dataset]
        print(f"{ds}: inserting into up to {len(vs)} healthy images", flush=True)
        for n, v in enumerate(vs):
            if n and n % 25 == 0:
                print(f"  {ds}: {n}/{len(vs)} done, {stats[f'{ds}: inserted']} inserted", flush=True)
            host = hosts[ds][stable_index(v.case_id + "host", len(hosts[ds]))]
            case_id = f"ins_{v.case_id}"
            path = out / case_id / "inserted.png"
            mpath = out / case_id / "lesion_mask.png"
            rng = np.random.default_rng(stable_index(case_id, 2 ** 31))
            if not path.exists():
                src = load_image(v.image_path)
                res = insert(src, _mask(v.meta["lesion_mask"], src.shape[:2]), load_image(host.image_path), rng)
                if res is None:
                    stats[f"{ds}: no position where the inserted lesion stands out"] += 1
                    continue
                img, placed = res
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(img).save(path)
                Image.fromarray(placed.astype(np.uint8) * 255).save(mpath)
            placed = np.asarray(Image.open(mpath)) > 127
            views.append(View(view_id=f"{case_id}__original", case_id=case_id, patient_id=host.patient_id,
                              kind=ViewKind.ORIGINAL, image_path=str(path), question=v.question, answer=v.answer,
                              answer_aliases=v.answer_aliases, lesion_box=mask_to_box(placed), critical=v.critical,
                              meta={"inserted": True, "lesion_mask": str(mpath), "original_image": str(path),
                                    "source_case": v.case_id, "host": host.view_id}))
            stats[f"{ds}: inserted"] += 1
    (out / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in views))
    print(f"{len(views)} insertion views in {out / 'views.jsonl'}")
    for k, n in sorted(stats.items()):
        print(f"  {k}: {n}")


if __name__ == "__main__":
    main()
