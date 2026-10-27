"""Reinforcement learning (GRPO) for the agent, starting from an SFT/merged adapter.

Usage:
    python scripts/train_grpo.py --model Qwen/Qwen3.5-4B --init adapters/merged/best \
        --views views/train/views_clean.jsonl --out adapters/grpo --steps 150
Rerunning with the same --out resumes from the last checkpoint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views, select_cases  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402
from medscope.train.grpo import train_grpo  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--init", required=True, help="adapter to start from")
    ap.add_argument("--views", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--views-per-step", type=int, default=2)
    ap.add_argument("--group-size", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--beta", type=float, default=0.0, help="KL weight to the starting adapter (0 = off)")
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--save-every", type=int, default=10)
    ap.add_argument("--eval-views", default=None, help="validation views for periodic checks")
    ap.add_argument("--eval-every", type=int, default=0)
    ap.add_argument("--eval-cases", type=int, default=15)
    ap.add_argument("--results", default=None)
    args = ap.parse_args()

    from medscope.train.hf_policy import HFPolicy

    cfg = with_vocab(load_config(), load_views(args.views))
    policy = HFPolicy(args.model, adapter=args.init, trainable=True, max_new_tokens=args.max_new_tokens)

    eval_fn = None
    if args.eval_views and args.eval_every and args.results:
        eval_views = select_cases(load_views(args.eval_views), args.eval_cases, seed=2)

        def eval_fn(step: int) -> dict:
            return evaluate(policy, eval_views, cfg, Path(args.results) / f"grpo_val_step{step:04d}",
                            {"name": f"grpo_val_step{step}", "model": args.model, "split": "validation"},
                            n_bootstrap=200)

    train_grpo(policy, load_views(args.views), cfg, args.out, steps=args.steps,
               views_per_step=args.views_per_step, group_size=args.group_size, lr=args.lr,
               beta=args.beta, ref_adapter=args.init if args.beta > 0 else None,
               save_every=args.save_every, eval_every=args.eval_every, eval_fn=eval_fn)


if __name__ == "__main__":
    main()
