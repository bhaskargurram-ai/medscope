"""Review check R7: could unrecorded same-patient images between training and the main test explain the results?
(docs/REVIEW_EXPERIMENTS.md)

Three main-test sources release no patient identifiers (SLAKE, Kvasir-SEG/HyperKvasir, BUSI), so a strict
subject-wise split cannot be made for them; their splits are by near-copy groups. This script asks what a leak
could change, in two steps:

1. Calibration, where patient ids exist (ChestX-Det, TCGA-LGG training images): how well does image similarity
   (DINOv2-base CLS embedding, cosine) tell two images of one patient from images of two patients? (AUROC of each
   image's most similar same-patient image vs its most similar other-patient image.)
2. Worst-case exclusion, in every source: each main-test case's most similar training image of the same source;
   within each source the test cases with the highest similarity (top 10%, 25%, 50%) are removed, and the main-test
   comparisons are recomputed on the rest (same stored per-view outcomes, no model rerun). A leak would favour only
   the trained model, so its advantage over the frontier models should shrink if leaked cases drove it.

    python scripts/leakage_similarity.py --train TRAIN_VIEWS... TRAIN_NEG... --test TEST_VIEWS... TEST_NEG... \
        --results RESULTS --ref v4_final_test --others v2_gemini_test v2_claudeopus_test v2_gpt6astra_test --out DIR
    -> DIR/leakage.md, DIR/leakage.json, DIR/emb_{train,test}.npz (cached)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402

KEEP_KINDS = ("original", "natural_negative")
NO_PATIENT_IDS = ("SLAKE", "Colonoscopy", "BUSI")      # substrings of dataset_of() labels
QUANTILES = (0.10, 0.25, 0.50)
METRICS = ("esg", "target_hallucination_rate", "net_utility", "ccr", "natural_hallucination_rate")


def unedited(views) -> dict[str, object]:
    """case id -> one unedited view (the original, or the lesion-free image) with an existing file."""
    out = {}
    for v in views:
        if v.kind.value in KEEP_KINDS and v.case_id not in out and Path(v.image_path).exists():
            out[v.case_id] = v
    return out


def embed(paths: list[str], batch: int = 32) -> np.ndarray:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    prep = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
    model = AutoModel.from_pretrained("facebook/dinov2-base").to(dev).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            x = prep(images=[Image.open(p).convert("RGB") for p in paths[i:i + batch]], return_tensors="pt").to(dev)
            out.append(model(**x).last_hidden_state[:, 0].float().cpu().numpy())
            if i % (batch * 25) == 0:
                print(f"  {i}/{len(paths)}", flush=True)
    e = np.concatenate(out)
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def nearest_same_source(test_e, test_src, train_e, train_src) -> np.ndarray:
    """For each test image, the highest cosine similarity to a training image of the same source (nan if none)."""
    out = np.full(len(test_e), np.nan)
    for src in set(test_src):
        ti = np.flatnonzero(np.array(test_src) == src)
        tr = np.flatnonzero(np.array(train_src) == src)
        if len(tr):
            out[ti] = (test_e[ti] @ train_e[tr].T).max(axis=1)
    return out


def calibration(e: np.ndarray, patients: list[str]) -> dict:
    """Each image with another image of its patient: most similar same-patient vs most similar other-patient image."""
    from medscope.fw.analysis import auroc
    pats = np.array(patients)
    sim = e @ e.T
    np.fill_diagonal(sim, -np.inf)
    same, diff = [], []
    for i in range(len(e)):
        m = pats == pats[i]
        m[i] = False
        if m.any() and (~m).sum() > 1:
            same.append(sim[i][m].max())
            other = sim[i][~m]
            diff.append(other[np.isfinite(other)].max())
    if not same:
        return {"n": 0}
    return {"n": len(same), "auroc": auroc(np.array(same), np.array(diff)),
            "same_median": float(np.median(same)), "other_median": float(np.median(diff)),
            "other_above_same_p25": float(np.mean(np.array(diff) >= np.percentile(same, 25)))}


def exclusion_sets(cases: list[str], sims: np.ndarray, sources: list[str], q: float,
                   only: tuple[str, ...] | None = None) -> set[str]:
    """Within each source (or only the sources matching `only`), the cases at or above the (1 - q) similarity quantile."""
    drop = set()
    by = defaultdict(list)
    for c, s, src in zip(cases, sims, sources):
        if s == s and (only is None or any(k in src for k in only)):
            by[src].append((c, s))
    for src, cs in by.items():
        cut = np.quantile([s for _, s in cs], 1 - q)
        drop |= {c for c, s in cs if s >= cut}
    return drop


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--ref", default="v4_final_test")
    ap.add_argument("--others", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from medscope.colab import dataset_of
    from medscope.eval.compare import load_outcomes, paired_bootstrap
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tr = unedited([v for f in args.train for v in load_views(f)])
    te = unedited([v for f in args.test for v in load_views(f)])
    trc, tec = sorted(tr), sorted(te)
    cache = {}
    for name, ids, d in (("train", trc, tr), ("test", tec, te)):
        f = out / f"emb_{name}.npz"
        if f.exists():
            z = np.load(f, allow_pickle=True)
            if list(z["ids"]) == ids:
                cache[name] = z["e"]
                continue
        e = embed([d[c].image_path for c in ids])
        np.savez(f, e=e, ids=np.array(ids))
        cache[name] = e
    tr_src = [dataset_of(c) for c in trc]
    te_src = [dataset_of(c) for c in tec]
    sims = nearest_same_source(cache["test"], te_src, cache["train"], tr_src)

    cal = {}
    for key in ("ChestX-Det", "LGG"):
        idx = [i for i, s in enumerate(tr_src) if key in s]
        if idx:
            cal[key] = calibration(cache["train"][idx], [tr[trc[i]].patient_id for i in idx])

    a = load_outcomes(Path(args.results) / args.ref)
    others = {o: load_outcomes(Path(args.results) / o) for o in args.others if (Path(args.results) / o).exists()}
    rows = []
    for scope, only in (("all sources", None), ("sources without patient ids", NO_PATIENT_IDS)):
        for q in (0.0,) + QUANTILES:
            drop = exclusion_sets(tec, sims, te_src, q, only) if q else set()
            keep_a = [o for o in a if o.case_id not in drop]
            rec = {"scope": scope, "q": q, "dropped": len(drop), "cases": len({o.case_id for o in keep_a})}
            from medscope.eval.metrics import METRICS as FN
            rec["ref"] = {m: FN[m](keep_a) for m in METRICS}
            rec["vs"] = {}
            for name, b in others.items():
                kb = [o for o in b if o.case_id not in drop]
                rec["vs"][name] = {m: paired_bootstrap(keep_a, kb, m) for m in ("esg", "target_hallucination_rate", "net_utility")}
            rows.append(rec)
            if not q and scope != "all sources":
                rows.pop()                  # q = 0 is the same for both scopes

    f = lambda x: "-" if x is None or x != x else f"{x:.3f}"  # noqa: E731
    md = ["# Could unrecorded same-patient images explain the main-test results?", "",
          "## 1. Does image similarity identify a patient? (training images with patient ids)", "",
          "| Source | Images with another image of their patient | AUROC same vs other patient | Median similarity, same / other patient | Other-patient pairs above the same-patient 25th percentile |",
          "| --- | --- | --- | --- | --- |"]
    for k, c in cal.items():
        if c.get("n"):
            md.append(f"| {k} | {c['n']} | {f(c['auroc'])} | {f(c['same_median'])} / {f(c['other_median'])} | {c['other_above_same_p25']:.1%} |")
    md += ["", "## 2. Main test without the test cases most similar to a training image of their source", "",
           f"Reference `{args.ref}`; differences reference minus comparator with 95% bootstrap CI (cases).", "",
           "| Removed | Cases kept | ESG | Erased claims | Net utility | " + " | ".join(f"ESG diff vs {o}" for o in others) + " |",
           "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in others) + " |"]
    for r in rows:
        label = "none" if not r["q"] else f"top {r['q']:.0%} per source ({r['scope']})"
        cells = []
        for o in others:
            d = r["vs"][o]["esg"]
            cells.append(f"{d.get('diff', float('nan')):+.3f} [{d.get('ci_low', float('nan')):+.3f}, {d.get('ci_high', float('nan')):+.3f}]")
        md.append(f"| {label} | {r['cases']} | {f(r['ref']['esg'])} | {f(r['ref']['target_hallucination_rate'])} | "
                  f"{f(r['ref']['net_utility'])} | " + " | ".join(cells) + " |")
    md += ["", "Test-case similarity to the nearest training image, median by source: " + "; ".join(
        f"{s}: {np.nanmedian([x for x, t in zip(sims, te_src) if t == s]):.3f}" for s in sorted(set(te_src)))]
    (out / "leakage.md").write_text("\n".join(md) + "\n")
    (out / "leakage.json").write_text(json.dumps({"calibration": cal, "rows": rows}, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
