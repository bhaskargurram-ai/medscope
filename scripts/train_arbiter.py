"""Train the deciding agent of lead 4 (docs/PREREGISTRATION_v10.md) from the recipe adapter, on the training views
that have stored reports (scripts/mas_reports.py --subsample). Each report part is left out with probability 0.25.

    python scripts/train_arbiter.py --model Qwen/Qwen3.5-4B --init ADAPTERS/v4_s1/final \
        --views TRAIN_VIEWS... --reports RESULTS/mas_reports/train.jsonl --out ADAPTERS/v4q_mas_s0
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.mas.arbiter import arbiter_sample  # noqa: E402
from medscope.mas.reports import read_reports  # noqa: E402
from medscope.train.sft import train_sft  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--init", required=True, help="adapter to continue from (the recipe)")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=None, help="stop early (smoke test)")
    args = ap.parse_args()
    reports = read_reports(args.reports)
    views = [v for f in args.views for v in load_views(f) if v.view_id in reports]
    seen, unique = set(), []
    for v in views:                      # a view listed in two files trains once
        if v.view_id not in seen:
            seen.add(v.view_id)
            unique.append(v)
    views = unique
    if not views:
        raise SystemExit("no training view has a stored report: run scripts/mas_reports.py first")
    print(f"arbiter training on {len(views)} views with reports ({len(reports)} reports stored)")
    import random

    import numpy as np
    import torch

    from medscope.train.hf_policy import HFPolicy
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    policy = HFPolicy(args.model, adapter=args.init, trainable=True)
    steps = math.ceil(len(views) * args.epochs / args.grad_accum)

    def sample_fn(view, seed, index):
        return [arbiter_sample(view, reports[view.view_id], seed, index)]

    train_sft(policy, views, "agentic", args.out, epochs=args.epochs, lr=args.lr, grad_accum=args.grad_accum,
              save_every=args.save_every, seed=args.seed, schedule_steps=steps, sample_fn=sample_fn,
              max_steps=args.max_steps)


if __name__ == "__main__":
    main()
