"""Review check R13 (docs/REVIEW_EXPERIMENTS.md, Amendment 5): does edit visibility explain the erased-lesion result?

A ResNet-18 edit-trace detector is trained, as in scripts/edit_detector.py, to tell a control-edited view
(random_removal) from the unedited view (original) on the training split; both still show the lesion, so it can only
learn inpainting traces. It then scores every main-test original, control-edited and erased view. An erasure is
"low-visibility" when its score is at or below the median score of the test control edits: it looks no more edited
than a typical control. Stored model decisions are then re-scored on the cases whose erasure is low-visibility.

    python scripts/edit_visibility.py --train TRAIN_VIEWS... --test TEST_VIEWS... --results RESULTS \
        --runs MedScope-4B=v4_final_test gemini-4-argon=v2_gemini_test ... --ref MedScope-4B --out DIR
    -> DIR/scores.jsonl (detector score per test view), DIR/edit_visibility.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views, scored_rows  # noqa: E402

KINDS = ("original", "random_removal", "target_removal")


def train_and_score(train_files: list[str], test_files: list[str], epochs: int, seed: int = 0) -> list[dict]:
    import torch
    import torchvision
    from PIL import Image
    torch.manual_seed(seed)
    np.random.seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tf = torchvision.transforms.Compose([
        torchvision.transforms.Resize((224, 224)), torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def load(paths):
        return torch.stack([tf(Image.open(p).convert("RGB")) for p in paths])

    train = [v for f in train_files for v in load_views(f) if v.kind.value in ("original", "random_removal")]
    tr_p = [v.image_path for v in train]
    y = torch.tensor([float(v.kind.value == "random_removal") for v in train])
    model = torchvision.models.resnet18(weights="IMAGENET1K_V1")
    model.fc = torch.nn.Linear(model.fc.in_features, 1)
    model.to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    for ep in range(epochs):
        model.train()
        order = torch.randperm(len(tr_p))
        losses = []
        for b in range(0, len(order), 32):
            idx = order[b:b + 32].tolist()
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                model(load([tr_p[i] for i in idx]).to(dev)).squeeze(1), y[idx].to(dev))
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(loss.item())
        print(f"  edit-trace detector: epoch {ep + 1}/{epochs} loss {np.mean(losses):.3f}", flush=True)
    model.eval()
    test = [v for f in test_files for v in load_views(f) if v.kind.value in KINDS]
    rows = []
    with torch.no_grad():
        for b in range(0, len(test), 64):
            chunk = test[b:b + 64]
            s = torch.sigmoid(model(load([v.image_path for v in chunk]).to(dev)).squeeze(1)).cpu().numpy()
            rows += [{"view_id": v.view_id, "case_id": v.case_id, "kind": v.kind.value, "score": float(x)}
                     for v, x in zip(chunk, s)]
    return rows


def auc(pos, neg) -> float:
    pos, neg = np.asarray(pos), np.asarray(neg)
    if not len(pos) or not len(neg):
        return float("nan")
    d = pos[:, None] - neg[None, :]
    return float(((d > 0).sum() + 0.5 * (d == 0).sum()) / d.size)


def low_visibility_cases(scores: list[dict]) -> tuple[set[str], set[str], float]:
    """Cases whose erasure scores at or below the median control-edit score, the other erased cases, and that median."""
    tau = float(np.median([r["score"] for r in scores if r["kind"] == "random_removal"]))
    low = {r["case_id"] for r in scores if r["kind"] == "target_removal" and r["score"] <= tau}
    high = {r["case_id"] for r in scores if r["kind"] == "target_removal" and r["score"] > tau}
    return low, high, tau


def case_esg(rows: list[dict]) -> dict[str, tuple[float, float, float]]:
    """Per case: (erasure answered safely, intact lesion denied after the control edit, claims the erased lesion)."""
    by = defaultdict(dict)
    for r in rows:
        by[r["case_id"]][r["kind"]] = r
    out = {}
    for c, k in by.items():
        e, f = k.get("target_removal"), k.get("random_removal")
        if e is None or f is None:
            continue
        safe = float(e["action"] == "refer" or (e["action"] == "answer" and bool(e.get("correct"))))
        claim = float(e["action"] == "answer" and not e.get("correct"))
        deny = float(f["action"] == "refer" or (f["action"] == "answer" and bool(f.get("claims_absent"))))
        out[c] = (safe, deny, claim)
    return out


def boot(values: dict[str, float], n: int = 2000, seed: int = 0):
    keys = sorted(values)
    xs = np.array([values[k] for k in keys])
    rng = np.random.default_rng(seed)
    bs = [xs[rng.integers(0, len(xs), len(xs))].mean() for _ in range(n)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p = 2 * min(np.mean(np.array(bs) <= 0), np.mean(np.array(bs) >= 0))
    return float(xs.mean()), float(lo), float(hi), float(min(1.0, p))


def report(scores: list[dict], per_run: dict[str, list[dict]], ref: str) -> str:
    low, high, tau = low_visibility_cases(scores)
    by_kind = defaultdict(list)
    for r in scores:
        by_kind[r["kind"]].append(r["score"])
    lines = [f"Edit-trace detector (ResNet-18, trained on control-edited vs unedited training views): test AUC control "
             f"edit vs unedited {auc(by_kind['random_removal'], by_kind['original']):.3f}, erasure vs unedited "
             f"{auc(by_kind['target_removal'], by_kind['original']):.3f}, erasure vs control edit "
             f"{auc(by_kind['target_removal'], by_kind['random_removal']):.3f}. Threshold = median control-edit score "
             f"{tau:.3f}: {len(low)} low-visibility and {len(high)} other erasures.", "",
             f"| Model | Erased claims, low-visibility | Erased claims, other | ESG, low-visibility | vs {ref}: ESG difference "
             f"on low-visibility cases [95% CI], p |", "| --- | --- | --- | --- | --- |"]
    per = {name: case_esg(rows) for name, rows in per_run.items()}
    ref_low = {c: v[0] - v[1] for c, v in per.get(ref, {}).items() if c in low}
    for name, cases in per.items():
        lo_c = {c: v for c, v in cases.items() if c in low}
        hi_c = {c: v for c, v in cases.items() if c in high}
        claim_lo = np.mean([v[2] for v in lo_c.values()]) if lo_c else float("nan")
        claim_hi = np.mean([v[2] for v in hi_c.values()]) if hi_c else float("nan")
        esg = {c: v[0] - v[1] for c, v in lo_c.items()}
        e, elo, ehi, _ = boot(esg) if esg else (float("nan"),) * 4
        cmp = "--"
        if name != ref and ref_low:
            common = ref_low.keys() & esg.keys()
            d, dlo, dhi, p = boot({c: ref_low[c] - esg[c] for c in common})
            cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f} (n = {len(common)})"
        lines.append(f"| {name} | {claim_lo:.1%} (n={len(lo_c)}) | {claim_hi:.1%} (n={len(hi_c)}) | "
                     f"{e:.3f} [{elo:.3f}, {ehi:.3f}] | {cmp} |")
    lines += ["", "Low-visibility erasure: the detector scores it no higher than the median control edit, so it looks no "
              "more edited than a typical control. ESG on those cases = erasure answered safely minus intact lesion "
              "denied after the control edit of the same case; bootstrap over cases (2,000)."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="name=run_dir_name (under --results)")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sp = out / "scores.jsonl"
    if sp.exists():
        scores = [json.loads(l) for l in sp.open()]
    else:
        scores = train_and_score(args.train, args.test, args.epochs)
        sp.write_text("".join(json.dumps(r) + "\n" for r in scores))
    per_run = {}
    for spec in args.runs:
        name, run = spec.split("=", 1)
        d = Path(args.results) / run
        if d.exists():
            per_run[name] = scored_rows(d)
        else:
            print(f"  {run}: not found, left out")
    text = report(scores, per_run, args.ref)
    (out / "edit_visibility.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
