"""Control-matched counterfactual consistency pass (medscope/train/cmcc.py) from an existing adapter.

    python scripts/train_cmcc.py --model Qwen/Qwen3.5-4B --init ADAPTERS/v4_s1/final --views TRAIN_VIEWS... \\
        --cases 3000 --out ADAPTERS/v4q_cmcc_s0 [--tau 2.0 --l-did 0.5 --l-inv 0.5 --l-act 0.5 --lr 2e-5]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--init", default=None, help="adapter to continue from (None: a new LoRA on the base model)")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--cases", type=int, default=0, help="number of triplet cases (0 = all)")
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--l-did", type=float, default=0.5)
    ap.add_argument("--l-inv", type=float, default=0.5)
    ap.add_argument("--l-act", type=float, default=0.5)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from medscope.train.cmcc import build_triplets, train_cmcc
    import numpy as np
    triplets = build_triplets([v for f in args.views for v in load_views(f)])
    if args.cases and args.cases < len(triplets):
        rng = np.random.default_rng(args.seed)
        triplets = [triplets[i] for i in sorted(rng.permutation(len(triplets))[:args.cases])]
    print(f"{len(triplets)} triplet cases")
    import random, torch
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    from medscope.train.hf_policy import HFPolicy
    policy = HFPolicy(args.model, adapter=args.init, trainable=True) if args.init else HFPolicy(args.model, trainable=True, new_lora=True)
    train_cmcc(policy, triplets, args.out, lr=args.lr, grad_accum=args.grad_accum, tau=args.tau, l_did=args.l_did,
               l_inv=args.l_inv, l_act=args.l_act, seed=args.seed, max_steps=args.max_steps)


if __name__ == "__main__":
    main()
