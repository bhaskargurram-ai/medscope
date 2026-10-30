"""Can a trained image classifier tell lesion-removed views from same-size random edits?

A ResNet-18 (ImageNet weights) is fine-tuned on the training split to separate target-removal
views from random-removal views, and tested on the test split. Both are edited with the same
inpainting operator and an edit of the same shape, so an AUC near 0.5 means the edits themselves
give nothing away: a model can only tell the two apart by checking whether the lesion is still
there. For reference it also reports original vs target-removal (is inpainting detectable at all?).

Usage:
    python scripts/edit_detector.py --train views/train/views_clean.jsonl ... --test views/test/views_clean.jsonl ... --out results/edit_detector
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC."""
    pos, neg = scores[labels == 1], scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    diff = pos[:, None] - neg[None, :]
    return float(((diff > 0).sum() + 0.5 * (diff == 0).sum()) / diff.size)


def pairs(files: list[str], neg_kind: str) -> tuple[list[str], list[int], list[str]]:
    views = [v for f in files for v in load_views(f)]
    paths, labels, cases = [], [], []
    for v in views:
        if v.kind.value == "target_removal":
            paths.append(v.image_path), labels.append(1), cases.append(v.case_id)
        elif v.kind.value == neg_kind:
            paths.append(v.image_path), labels.append(0), cases.append(v.case_id)
    return paths, labels, cases


def run(train_files, test_files, neg_kind: str, epochs: int, seed: int = 0) -> dict:
    import torch
    import torchvision
    from PIL import Image
    torch.manual_seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tf = torchvision.transforms.Compose([
        torchvision.transforms.Resize((224, 224)), torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def load(paths):
        return torch.stack([tf(Image.open(p).convert("RGB")) for p in paths])

    tr_p, tr_y, _ = pairs(train_files, neg_kind)
    te_p, te_y, te_c = pairs(test_files, neg_kind)
    model = torchvision.models.resnet18(weights="IMAGENET1K_V1")
    model.fc = torch.nn.Linear(model.fc.in_features, 1)
    model.to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    y = torch.tensor(tr_y, dtype=torch.float32)
    for ep in range(epochs):
        model.train()
        order = torch.randperm(len(tr_p))
        losses = []
        for b in range(0, len(order), 32):
            idx = order[b:b + 32].tolist()
            x = load([tr_p[i] for i in idx]).to(dev)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(x).squeeze(1), y[idx].to(dev))
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        print(f"  {neg_kind}: epoch {ep + 1}/{epochs} loss {np.mean(losses):.3f}", flush=True)
    model.eval()
    scores = []
    with torch.no_grad():
        for b in range(0, len(te_p), 64):
            scores.append(torch.sigmoid(model(load(te_p[b:b + 64]).to(dev)).squeeze(1)).cpu().numpy())
    s, lab = np.concatenate(scores), np.array(te_y)
    point = auc(s, lab)
    # bootstrap over cases
    rng = np.random.default_rng(0)
    cases = sorted(set(te_c))
    idx_by = {c: [i for i, cc in enumerate(te_c) if cc == c] for c in cases}
    boots = []
    for _ in range(1000):
        pick = [i for c in rng.choice(cases, len(cases)) for i in idx_by[c]]
        boots.append(auc(s[pick], lab[pick]))
    return {"comparison": f"target_removal vs {neg_kind}", "train_images": len(tr_p), "test_images": len(te_p),
            "auc": point, "ci_low": float(np.nanquantile(boots, 0.025)), "ci_high": float(np.nanquantile(boots, 0.975))}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=5)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = [run(args.train, args.test, k, args.epochs) for k in ("random_removal", "original")]
    (out / "edit_detector.json").write_text(json.dumps(results, indent=2))
    lines = ["| Learned detector (ResNet-18) | Train images | Test images | Test AUC [95% CI] |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['comparison']} | {r['train_images']} | {r['test_images']} | {r['auc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] |"
              for r in results]
    (out / "edit_detector.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
