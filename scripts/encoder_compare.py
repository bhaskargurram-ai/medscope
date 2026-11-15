"""Is the perception limit specific to Qwen3.5-4B's frozen general-domain vision encoder? (review request;
docs/REVIEW_EXPERIMENTS.md, experiment R3)

The paper finds that the model's answers use about as much erased-vs-intact separation as its hidden states hold,
and calls perception the remaining limit. A reviewer asked whether that limit is a property of this encoder. This
script measures, with the same linear probe for every encoder, how well frozen image features separate

  E vs C   the erasure from the control edit of the same case (same tool, same shape; only the lesion differs)
  E vs O   the erasure from the unedited image
  C vs O   the control edit from the unedited image (edit detection with the lesion in both)

for Qwen3.5-4B's own vision encoder and three alternatives, on the whole image and on a lesion-centred crop (the
same crop box, from the unedited image's lesion box, for all three views of a case):

  qwen        Qwen/Qwen3.5-4B vision module (what MedScope-4B sees)
  biomedclip  microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224 (medical, image-text; needs open_clip_torch)
  raddino     microsoft/rad-dino (chest X-ray self-supervised)
  dinov2      facebook/dinov2-base (strong general self-supervised)

Probes are trained on training views (LaMa and tissue transplant) and tested on main-test views made with LaMa and
with the held-out tools (TELEA, Stable Diffusion; same masks). AUC with a case-bootstrap 95% interval, and the
paired AUC difference from qwen on the same test cases.

    python scripts/encoder_compare.py --train TRAIN_VIEWS... --test TEST_VIEWS... --tool telea=... --tool diffusion=... \\
        --encoders qwen biomedclip raddino dinov2 --out DIR [--per-kind 600] [--qwen-model Qwen/Qwen3.5-4B]
    -> DIR/encoders.md, DIR/encoders.json, DIR/features/<encoder>_<pooling>_<set>.npz (cached; reruns skip them)
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

from medscope.data.schema import box_to_pixels  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

KINDS = ("original", "target_removal", "random_removal")
PAIRS = (("target_removal", "random_removal", "E vs C (lesion gone vs intact, same edit)"),
         ("target_removal", "original", "E vs O (erasure detection)"),
         ("random_removal", "original", "C vs O (edit detection, lesion in both)"))
ENCODERS = ("qwen", "biomedclip", "raddino", "dinov2")


def crop_box(box, width: int, height: int, scale: float = 2.0, min_side: int = 64) -> tuple[int, int, int, int]:
    """A square crop centred on the lesion box, `scale` times its longer side (at least min_side px), inside the image."""
    x1, y1, x2, y2 = box_to_pixels(box, width, height)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    side = int(min(max(width, height), max(min_side, scale * max(x2 - x1, y2 - y1))))
    side = min(side, width, height) if min(width, height) >= min_side else min(width, height)
    left = int(np.clip(round(cx - side / 2), 0, width - side))
    top = int(np.clip(round(cy - side / 2), 0, height - side))
    return left, top, left + side, top + side


def images(views, boxes: dict, pooling: str):
    from PIL import Image
    for v in views:
        img = Image.open(v.image_path).convert("RGB")
        if pooling == "crop":
            img = img.crop(crop_box(boxes[v.case_id], *img.size))
        yield img


class Encoder:
    def __init__(self, name: str, qwen_model: str):
        import torch
        self.name, self.torch = name, torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        if name == "qwen":
            from medscope.train.hf_policy import VISION_MODULES, HFPolicy
            self.policy = HFPolicy(qwen_model, load_in_4bit=False, max_image_side=768)
            self.module = next(m for n, m in self.policy.model.named_modules()
                               if n.split(".")[-1] in VISION_MODULES and n.split(".")[-1] != "multi_modal_projector")
            self.grab = {}

            def hook(_m, _i, out):
                t = out.last_hidden_state if hasattr(out, "last_hidden_state") else (out[0] if isinstance(out, (tuple, list)) else out)
                self.grab["x"] = t.detach().float().reshape(-1, t.shape[-1]).mean(0).cpu().numpy()
            self.module.register_forward_hook(hook)
        elif name == "biomedclip":
            import open_clip
            self.model, self.prep = open_clip.create_model_from_pretrained(
                "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224")
            self.model = self.model.to(self.dev).eval()
        else:
            from transformers import AutoImageProcessor, AutoModel
            mid = {"raddino": "microsoft/rad-dino", "dinov2": "facebook/dinov2-base"}[name]
            self.prep = AutoImageProcessor.from_pretrained(mid)
            self.model = AutoModel.from_pretrained(mid).to(self.dev).eval()

    def __call__(self, img) -> np.ndarray:
        torch = self.torch
        with torch.no_grad():
            if self.name == "qwen":
                msgs = [{"role": "user", "content": [{"type": "image", "image": np.asarray(img)},
                                                     {"type": "text", "text": "Describe the image."}]}]
                self.grab.clear()
                self.policy.model(**self.policy.encode(msgs))
                return self.grab["x"]
            if self.name == "biomedclip":
                return self.model.encode_image(self.prep(img).unsqueeze(0).to(self.dev)).float().cpu().numpy()[0]
            h = self.model(**self.prep(images=img, return_tensors="pt").to(self.dev)).last_hidden_state.float()
            return torch.cat([h[0, 0], h[0, 1:].mean(0)]).cpu().numpy()       # CLS and mean patch token


def auc(s: np.ndarray, y: np.ndarray) -> float:
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def probe_scores(xtr, ktr, xte, kte, pos: str, neg: str):
    """Logistic-regression scores on the test views of the pair (fit on the training views of the pair)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    mtr, mte = np.isin(ktr, [pos, neg]), np.isin(kte, [pos, neg])
    if len(set(ktr[mtr])) < 2 or len(set(kte[mte])) < 2:
        return None, mte
    sc = StandardScaler().fit(xtr[mtr])
    clf = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(xtr[mtr]), (ktr[mtr] == pos).astype(int))
    return clf.decision_function(sc.transform(xte[mte])), mte


def paired_boot(scores: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]], ref: str, n: int = 1000, seed: int = 0):
    """AUC with case-bootstrap CI per encoder, and the AUC difference from `ref` on the same resampled cases.
    scores: encoder -> (score, label, case) on the same test views in the same order."""
    rng = np.random.default_rng(seed)
    any_e = next(iter(scores.values()))
    cases = any_e[2]
    uniq = np.unique(cases)
    rows = {c: np.flatnonzero(cases == c) for c in uniq}
    boots = defaultdict(list)
    for _ in range(n):
        idx = np.concatenate([rows[c] for c in uniq[rng.integers(0, len(uniq), len(uniq))]])
        a = {e: auc(s[idx], y[idx]) for e, (s, y, _) in scores.items()}
        for e in scores:
            boots[e].append(a[e])
            if ref in a:
                boots[e + "-diff"].append(a[e] - a[ref])
    out = {}
    for e, (s, y, _) in scores.items():
        point = auc(s, y)
        lo, hi = np.percentile(boots[e], [2.5, 97.5])
        d = (point - auc(*scores[ref][:2]),) + tuple(np.percentile(boots[e + "-diff"], [2.5, 97.5])) if ref in scores else (np.nan,) * 3
        out[e] = {"auc": point, "lo": float(lo), "hi": float(hi), "diff": float(d[0]), "diff_lo": float(d[1]), "diff_hi": float(d[2])}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True, help="main-test views (LaMa)")
    ap.add_argument("--tool", action="append", default=[], help="name=views.jsonl of held-out-tool test views")
    ap.add_argument("--encoders", nargs="+", default=list(ENCODERS), choices=ENCODERS)
    ap.add_argument("--poolings", nargs="+", default=["full", "crop"], choices=["full", "crop"])
    ap.add_argument("--qwen-model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--per-kind", type=int, default=600)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "features").mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    def usable(vs):
        return [v for v in vs if v.kind.value in KINDS and Path(v.image_path).exists()]
    train_all = usable([v for f in args.train for v in load_views(f)])
    boxes = {v.case_id: v.lesion_box for v in train_all if v.kind.value == "original" and v.lesion_box is not None}
    by = defaultdict(list)
    for v in train_all:
        if v.case_id in boxes:
            by[v.kind.value].append(v)
    train = []
    for k in KINDS:
        rng.shuffle(by[k])
        train += by[k][:args.per_kind] if args.per_kind else by[k]
    test_main = usable([v for f in args.test for v in load_views(f)])
    tboxes = {v.case_id: v.lesion_box for v in test_main if v.kind.value == "original" and v.lesion_box is not None}
    boxes.update(tboxes)
    originals = [v for v in test_main if v.kind.value == "original" and v.case_id in tboxes]
    sets = {"lama": [v for v in test_main if v.case_id in tboxes]}
    for spec in args.tool:
        name, _, path = spec.partition("=")
        tv = [v for v in usable(load_views(path)) if v.case_id in tboxes and v.kind.value != "original"]
        cases = {v.case_id for v in tv}
        sets[name] = tv + [v for v in originals if v.case_id in cases]
    print(f"train {len(train)} views; test sets: " + ", ".join(f"{k} {len(v)}" for k, v in sets.items()))

    feats: dict = {}
    for enc in args.encoders:
        model = None
        for pooling in args.poolings:
            for name, vs in [("train", train)] + list(sets.items()):
                f = out / "features" / f"{enc}_{pooling}_{name}.npz"
                if f.exists():
                    z = np.load(f, allow_pickle=True)
                    feats[(enc, pooling, name)] = (z["x"], z["kind"], z["case"])
                    continue
                if model is None:
                    try:
                        model = Encoder(enc, args.qwen_model)
                    except Exception as e:      # noqa: BLE001 - a missing package or model: skip this encoder, say so
                        print(f"{enc}: could not load ({e}); skipped")
                        break
                print(f"{enc} / {pooling} / {name}: {len(vs)} images", flush=True)
                x = np.stack([model(img) for img in images(vs, boxes, pooling)])
                kind, case = np.array([v.kind.value for v in vs]), np.array([v.case_id for v in vs])
                np.savez(f, x=x, kind=kind, case=case)
                feats[(enc, pooling, name)] = (x, kind, case)
        del model

    res: dict = {}
    for pooling in args.poolings:
        for name in sets:
            for pos, neg, what in PAIRS:
                sc = {}
                for enc in args.encoders:
                    if (enc, pooling, "train") not in feats or (enc, pooling, name) not in feats:
                        continue
                    xtr, ktr, _ = feats[(enc, pooling, "train")]
                    xte, kte, cte = feats[(enc, pooling, name)]
                    s, m = probe_scores(xtr, ktr, xte, kte, pos, neg)
                    if s is not None:
                        sc[enc] = (s, (kte[m] == pos).astype(int), cte[m])
                if sc:
                    res[f"{pooling}/{name}/{pos}-{neg}"] = {"what": what, **paired_boot(sc, "qwen", seed=args.seed)}
    f = lambda x: "-" if x != x else f"{x:.3f}"  # noqa: E731
    md = ["# Frozen image encoders compared (linear probes)", "",
          "Same probe (logistic regression, standardised features) for every encoder, trained on training views, "
          "tested on main-test views. AUC [case-bootstrap 95% CI]; Δ = AUC minus qwen's on the same cases [95% CI]. "
          "'full' = whole image, 'crop' = square crop around the lesion box (same box for all three views of a case).", ""]
    for key, r in res.items():
        pooling, name, _ = key.split("/")
        md += [f"## {r['what']}: {name} test views, {pooling} image", "", "| Encoder | AUC [95% CI] | Δ vs qwen [95% CI] |",
               "| --- | --- | --- |"]
        for enc in args.encoders:
            if enc in r:
                e = r[enc]
                md.append(f"| {enc} | {f(e['auc'])} [{f(e['lo'])}, {f(e['hi'])}] | "
                          + ("-" if enc == "qwen" else f"{f(e['diff'])} [{f(e['diff_lo'])}, {f(e['diff_hi'])}]") + " |")
        md.append("")
    (out / "encoders.md").write_text("\n".join(md) + "\n")
    (out / "encoders.json").write_text(json.dumps(res, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
