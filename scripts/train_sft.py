"""Train a grounding or agentic LoRA adapter on synthetic trajectories.

Usage:
    python scripts/train_sft.py --model Qwen/Qwen3.5-4B --views views/train/views_clean.jsonl \
        --mode agentic --out /content/drive/MyDrive/medscope/adapters/sft_agentic
Rerunning with the same --out resumes from the last checkpoint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.train.sft import MODES, train_sft  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--views", required=True, nargs="+", help="one or more views files")
    ap.add_argument("--negatives", nargs="*", default=[], help="natural-negative views files to add")
    ap.add_argument("--init", default=None, help="continue training this adapter instead of a new one")
    ap.add_argument("--kinds", nargs="*", default=None,
                    help="train only on these view kinds (ablations), e.g. original natural_negative degraded")
    ap.add_argument("--subsample", type=int, default=None,
                    help="train on this many synthetic views (random, fixed seed) instead of all of them")
    ap.add_argument("--replays", default=None,
                    help="rejection-sampling episodes (jsonl from sample_rft.py): trained on as recorded")
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--save-every", type=int, default=50)
    args = ap.parse_args()

    from medscope.train.hf_policy import HFPolicy

    views = [v for f in args.views for v in load_views(f)]
    negs = [v for f in args.negatives for v in load_views(f)]
    if args.kinds:
        views = [v for v in views if v.kind.value in args.kinds]
        negs = [v for v in negs if v.kind.value in args.kinds]
        print(f"ablation: only {args.kinds} views")
    by_id = {v.view_id: v for v in views + negs}     # before subsampling: kept episodes may be on any view
    if args.subsample and args.subsample < len(views) + len(negs):
        import numpy as np
        rng = np.random.default_rng(7)
        share = args.subsample / (len(views) + len(negs))   # same share from both pools
        views = [views[i] for i in sorted(rng.permutation(len(views))[:round(share * len(views))])]
        negs = [negs[i] for i in sorted(rng.permutation(len(negs))[:round(share * len(negs))])]
    replays = None
    if args.replays:
        from medscope.eval.runner import read_jsonl
        recs = read_jsonl(Path(args.replays))
        from dataclasses import replace
        kept = [replace(by_id[r["view_id"]], view_id=r["view_id"] + "#rft")
                for r in recs if r.get("kept") and r["view_id"] in by_id]
        # a separate copy of each view carries the model's own episode; the original keeps its synthetic one
        replays = {r["view_id"] + "#rft": r["turns"] for r in recs if r.get("kept")}
        print(f"{len(kept)} self-generated episodes kept by rejection sampling")
        views = views + kept          # their own episodes, on top of the synthetic set
    views += negs
    print(f"training on {len(views)} views ({len(negs)} natural negatives)")

    if args.init:
        policy = HFPolicy(args.model, adapter=args.init, trainable=True)
    else:
        policy = HFPolicy(args.model, trainable=True, new_lora=True)
    trainable = sum(p.numel() for p in policy.model.parameters() if p.requires_grad)
    print(f"trainable LoRA parameters: {trainable / 1e6:.1f}M")
    train_sft(policy, views, args.mode, args.out, epochs=args.epochs, lr=args.lr,
              grad_accum=args.grad_accum, max_steps=args.max_steps, save_every=args.save_every,
              replays=replays)


if __name__ == "__main__":
    main()
