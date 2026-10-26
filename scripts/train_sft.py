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
    ap.add_argument("--views", required=True)
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--save-every", type=int, default=50)
    args = ap.parse_args()

    from medscope.train.hf_policy import HFPolicy

    policy = HFPolicy(args.model, trainable=True, new_lora=True)
    trainable = sum(p.numel() for p in policy.model.parameters() if p.requires_grad)
    print(f"trainable LoRA parameters: {trainable / 1e6:.1f}M")
    train_sft(policy, load_views(args.views), args.mode, args.out, epochs=args.epochs, lr=args.lr,
              grad_accum=args.grad_accum, max_steps=args.max_steps, save_every=args.save_every)


if __name__ == "__main__":
    main()
