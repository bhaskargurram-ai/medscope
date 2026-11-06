"""Removal-based preference training (DPO) on the MedScope training cases: the closest-method baseline.

Pairs are built from the unedited lesion views, the lesion-erased views and the lesion-free images (see
medscope/train/dpo.py); no control edits, no degraded views, no tools. Starts from an SFT adapter (--init), whose
log-probabilities are the DPO reference, or from the base model.

    python scripts/train_dpo.py --model Qwen/Qwen3.5-4B --init ADAPTERS/v4q_nocf_s0/final \\
        --views TRAIN_VIEWS... --negatives TRAIN_NEG... --pairs 8000 --beta 0.1 --lr 2e-5 --out ADAPTERS/v4q_dpo_s0
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--init", default=None, help="SFT adapter to start from (also the DPO reference)")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="*", default=[])
    ap.add_argument("--pairs", type=int, default=0, help="number of preference pairs (0 = all)")
    ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from medscope.train.dpo import build_pairs, pair_order, train_dpo
    views = [v for f in args.views + args.negatives for v in load_views(f)]
    pairs = pair_order(build_pairs(views, seed=args.seed), args.pairs or None, args.seed)
    print(f"{len(pairs)} preference pairs: {dict(Counter(p.kind for p in pairs))}")

    import random
    import numpy as np
    import torch
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    from medscope.train.hf_policy import HFPolicy
    policy = HFPolicy(args.model, adapter=args.init, trainable=True) if args.init else \
        HFPolicy(args.model, trainable=True, new_lora=True)
    train_dpo(policy, pairs, args.out, reference=args.init, beta=args.beta, lr=args.lr, grad_accum=args.grad_accum,
              max_steps=args.max_steps, save_every=args.save_every, seed=args.seed)


if __name__ == "__main__":
    main()
