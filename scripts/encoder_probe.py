"""Does the frozen vision encoder already carry edit information? A linear probe on its features.

MedScope's vision encoder is never trained, so the LoRA adapter can only use what the encoder already produces.
The paper argues this limits edit detection; a reviewer rightly asked for a measurement. This script takes the
encoder's output for every view (the image features the language model receives), mean-pools them, fits a logistic
regression on training views and tests it on test views, for three pairs:

  random_removal vs original   edit detection: both show the lesion, one carries an inpainted patch elsewhere
  target_removal vs original   erasure detection: lesion gone, or its trace
  target_removal vs random_removal   both edited with the same tool and shape; only the lesion differs

A test AUC near 0.5 on the first pair means the features that reach the adapter do not tell an edited image from
an unedited one; a high AUC means an edit-detection shortcut is available to the adapter in principle, whether or
not the trained model uses it (that is what the ESG and the random-removal denial rate measure).

    python scripts/encoder_probe.py --model Qwen/Qwen3.5-4B --train TRAIN_VIEWS... --test TEST_VIEWS... --out DIR
        [--per-kind 600] [--seed 0]
    -> DIR/probe.md, DIR/probe.json, DIR/features_{train,test}.npz
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402

KINDS = ("original", "random_removal", "target_removal")
PAIRS = (("random_removal", "original", "edit detection (lesion in both)"),
         ("target_removal", "original", "erasure detection"),
         ("target_removal", "random_removal", "lesion gone vs intact (same edit)"))


def pick(views, per_kind: int, rng: random.Random):
    by = defaultdict(list)
    for v in views:
        if v.kind.value in KINDS and Path(v.image_path).exists():
            by[v.kind.value].append(v)
    out = []
    for k in KINDS:
        vs = by[k]
        rng.shuffle(vs)
        out += vs[:per_kind] if per_kind else vs
    return out


def extract(model_id: str, views, max_side: int = 768) -> np.ndarray:
    """Mean-pooled output of the vision module for each view's image."""
    import torch
    from medscope.train.hf_policy import VISION_MODULES, HFPolicy
    policy = HFPolicy(model_id, load_in_4bit=False, max_image_side=max_side)
    model = policy.model
    module = None
    for name, m in model.named_modules():
        last = name.split(".")[-1]
        if last in VISION_MODULES and last != "multi_modal_projector":
            module = m
            print("probing the output of", name)
            break
    if module is None:
        raise SystemExit("no vision module found: " + ", ".join(n for n, _ in model.named_modules() if "vis" in n)[:500])
    grabbed = {}

    def hook(_m, _i, out):
        t = out
        if hasattr(t, "last_hidden_state"):
            t = t.last_hidden_state
        elif isinstance(t, (tuple, list)):
            t = t[0]
        grabbed["x"] = t.detach().float().reshape(-1, t.shape[-1]).mean(0).cpu().numpy()

    handle = module.register_forward_hook(hook)
    feats = []
    with torch.no_grad():
        for i, v in enumerate(views):
            msgs = [{"role": "user", "content": [{"type": "image", "image": v.image_path}, {"type": "text", "text": "Describe the image."}]}]
            inputs = policy.encode(msgs)
            grabbed.clear()
            model(**inputs)
            feats.append(grabbed["x"])
            if i % 200 == 0:
                print(f"{i}/{len(views)} images", flush=True)
    handle.remove()
    return np.stack(feats)


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    pos, neg = scores[labels == 1], scores[labels == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def probe(xtr, ktr, xte, kte, cte, seed: int):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(seed)
    rows = []
    for pos, neg, what in PAIRS:
        mtr = np.isin(ktr, [pos, neg])
        mte = np.isin(kte, [pos, neg])
        sc = StandardScaler().fit(xtr[mtr])
        clf = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(xtr[mtr]), (ktr[mtr] == pos).astype(int))
        s = clf.decision_function(sc.transform(xte[mte]))
        y = (kte[mte] == pos).astype(int)
        cases = cte[mte]
        a = auc(s, y)
        uniq = np.unique(cases)
        boots = []
        for _ in range(1000):                                   # bootstrap over test cases (both views of a case together)
            chosen = uniq[rng.integers(0, len(uniq), len(uniq))]
            idx = np.concatenate([np.flatnonzero(cases == c) for c in chosen])
            boots.append(auc(s[idx], y[idx]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({"positive": pos, "negative": neg, "what": what, "n_train": int(mtr.sum()), "n_test": int(mte.sum()),
                     "auc": a, "ci_low": float(lo), "ci_high": float(hi)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-kind", type=int, default=600, help="training views per kind (0 = all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reference", default="", help="a line to print under the table, e.g. the ResNet-18 result")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    tr = pick([v for f in args.train for v in load_views(f)], args.per_kind, rng)
    te = pick([v for f in args.test for v in load_views(f)], 0, rng)
    print(f"train views: {len(tr)}, test views: {len(te)}")
    cache = {}
    for name, vs in (("train", tr), ("test", te)):
        f = out / f"features_{name}.npz"
        if f.exists():
            z = np.load(f, allow_pickle=True)
            cache[name] = (z["x"], z["kind"], z["case"])
        else:
            x = extract(args.model, vs)
            np.savez(f, x=x, kind=np.array([v.kind.value for v in vs]), case=np.array([v.case_id for v in vs]))
            cache[name] = (x, np.array([v.kind.value for v in vs]), np.array([v.case_id for v in vs]))
    (xtr, ktr, _), (xte, kte, cte) = cache["train"], cache["test"]
    rows = probe(xtr, ktr, xte, kte, cte, args.seed)
    md = [f"# Linear probe on the frozen vision encoder ({args.model})", "",
          f"Logistic regression on mean-pooled encoder features ({xtr.shape[1]} dims); trained on {len(xtr)} training views, "
          f"tested on {len(xte)} main-test views; AUC with 95% bootstrap CI over test cases.", "",
          "| Pair (positive vs negative) | What a high AUC means | Train | Test | Test AUC [95% CI] |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        md.append(f"| {r['positive']} vs {r['negative']} | {r['what']} | {r['n_train']} | {r['n_test']} | "
                  f"{r['auc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] |")
    if args.reference:
        md += ["", args.reference]
    (out / "probe.md").write_text("\n".join(md) + "\n")
    (out / "probe.json").write_text(json.dumps(rows, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    main()
