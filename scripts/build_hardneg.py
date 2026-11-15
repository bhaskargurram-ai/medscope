"""Hard negatives for the CORAL-style comparator (review request; docs/REVIEW_EXPERIMENTS.md).

CORAL (Zafar et al., arXiv:2607.03647) trains a medical VLM to change its answer when the image is swapped for a
CLIP-retrieved hard negative. Its weights are not public, so we test its training signal inside our pipeline: for
every lesion case of the training triplets, the most similar *lesion-free* training image of the same source
(cosine similarity of CLIP image embeddings), excluding near-identical images and the same patient. The swap view keeps the original's
question, answer and box (so the two candidate replies are the same as on the original) and only replaces the image.

    python scripts/build_hardneg.py --views TRAIN_VIEWS... --negatives TRAIN_NEG... --out HN.jsonl
        [--clip openai/clip-vit-base-patch32] [--max-sim 0.995] [--batch 64]
    -> HN.jsonl: one line per case {"case_id", "swap": View dict, "negative_view_id", "similarity"}
       HN.md: counts and the similarity distribution per source

Needs a GPU for speed (CPU works, slowly) and `transformers`.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.schema import View, ViewKind  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def pick_hard_negatives(case_emb: dict[str, np.ndarray], case_src: dict[str, str], neg_emb: dict[str, np.ndarray],
                        neg_src: dict[str, str], max_sim: float = 0.995, case_pat: dict[str, str] | None = None,
                        neg_pat: dict[str, str] | None = None) -> dict[str, tuple[str, float]]:
    """case_id -> (negative view id, cosine similarity): the most similar lesion-free image of the same source whose
    similarity is below max_sim (near-identical images are left out) and, when patient ids are given, from another
    patient. Embeddings need not be normalised."""
    case_pat, neg_pat = case_pat or {}, neg_pat or {}
    by_src: dict[str, tuple[list[str], np.ndarray]] = {}
    for src in set(neg_src.values()):
        ids = sorted(i for i, s in neg_src.items() if s == src)
        m = np.stack([neg_emb[i] for i in ids]).astype(np.float64)
        by_src[src] = (ids, m / np.linalg.norm(m, axis=1, keepdims=True))
    out = {}
    for cid, e in case_emb.items():
        src = case_src[cid]
        if src not in by_src:
            continue
        ids, m = by_src[src]
        sims = m @ (e / np.linalg.norm(e))
        for j in np.argsort(-sims):
            same_patient = case_pat.get(cid) and case_pat.get(cid) == neg_pat.get(ids[j])
            if sims[j] < max_sim and not same_patient:
                out[cid] = (ids[j], float(sims[j]))
                break
    return out


def swap_view(original: View, negative: View, sim: float) -> View:
    """The original's question, answer and box on the negative's image: expected answer 'absent'."""
    return replace(original, view_id=f"{original.view_id}#hn", kind=ViewKind.TARGET_REMOVAL,
                   image_path=negative.image_path,
                   meta={**(original.meta or {}), "hard_negative": negative.view_id, "similarity": sim})


def embed(paths: list[str], model_id: str, batch: int) -> np.ndarray:
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_id).to(dev).eval()
    proc = CLIPProcessor.from_pretrained(model_id)
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            imgs = [Image.open(p).convert("RGB") for p in paths[i:i + batch]]
            x = proc(images=imgs, return_tensors="pt").to(dev)
            out.append(model.get_image_features(**x).float().cpu().numpy())
            if i % (batch * 20) == 0:
                print(f"  {i}/{len(paths)} images", flush=True)
    return np.concatenate(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--clip", default="openai/clip-vit-base-patch32")
    ap.add_argument("--max-sim", type=float, default=0.995)
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()
    from medscope.colab import dataset_of
    from medscope.train.cmcc import build_triplets
    triplets = build_triplets([v for f in args.views for v in load_views(f)])
    negs = [v for f in args.negatives for v in load_views(f) if v.kind is ViewKind.NATURAL_NEGATIVE
            and Path(v.image_path).exists()]
    print(f"{len(triplets)} triplet cases, {len(negs)} lesion-free images")
    origs = [t.original for t in triplets if Path(t.original.image_path).exists()]
    ce = embed([v.image_path for v in origs], args.clip, args.batch)
    ne = embed([v.image_path for v in negs], args.clip, args.batch)
    case_emb = {v.case_id: e for v, e in zip(origs, ce)}
    case_src = {v.case_id: dataset_of(v.case_id) for v in origs}
    neg_emb = {v.view_id: e for v, e in zip(negs, ne)}
    neg_src = {v.view_id: dataset_of(v.case_id) for v in negs}
    picks = pick_hard_negatives(case_emb, case_src, neg_emb, neg_src, args.max_sim,
                                {v.case_id: v.patient_id for v in origs}, {v.view_id: v.patient_id for v in negs})
    by_id = {v.view_id: v for v in negs}
    o_by = {v.case_id: v for v in origs}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for cid, (nid, sim) in sorted(picks.items()):
            f.write(json.dumps({"case_id": cid, "swap": swap_view(o_by[cid], by_id[nid], sim).to_dict(),
                                "negative_view_id": nid, "similarity": sim}) + "\n")
    lines = ["# Hard negatives (CORAL-style comparator)", "",
             f"{len(picks)} of {len(origs)} cases have a lesion-free image of the same source (CLIP `{args.clip}`, "
             f"similarity < {args.max_sim}).", "", "| Source | Cases | Median similarity | 10th-90th percentile |",
             "| --- | --- | --- | --- |"]
    for src in sorted(set(case_src.values())):
        sims = [s for c, (_, s) in picks.items() if case_src[c] == src]
        if sims:
            lines.append(f"| {src} | {len(sims)} | {np.median(sims):.3f} | {np.percentile(sims, 10):.3f}-"
                         f"{np.percentile(sims, 90):.3f} |")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
