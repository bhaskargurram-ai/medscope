"""Evaluate a model (optionally with a LoRA adapter) on MedScope views.

Writes outcomes.jsonl, transcripts.jsonl, summary.json and report.md to --out.
Rerunning with the same --out resumes where it stopped.

Usage:
    python scripts/evaluate.py --model Qwen/Qwen3.5-4B --views views/test/views_clean.jsonl \
        --out results/qwen35_base_test --name qwen35-base --split test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views, select_cases  # noqa: E402
from medscope.rewards import load_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--views", required=True, nargs="+", help="one or more views files, evaluated together")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=1536,
                    help="per turn; generous because some models (MedGemma 1.5) think before answering")
    ap.add_argument("--quant", choices=["auto", "4bit", "none"], default="auto",
                    help="auto: 4-bit only on GPUs under 20 GB (T4); 16-bit on L4/A100")
    ap.add_argument("--batch-size", type=int, default=8,
                    help="episodes advanced together; each sees exactly what it would see alone")
    args = ap.parse_args()

    from medscope.train.hf_policy import HFPolicy

    views = select_cases([v for f in args.views for v in load_views(f)], args.limit_cases)
    policy = HFPolicy(args.model, adapter=args.adapter, load_in_4bit={"auto": None, "4bit": True, "none": False}[args.quant],
                      max_new_tokens=args.max_new_tokens)
    precision = "4bit" if policy.load_in_4bit else str(policy.dtype).replace("torch.", "")
    meta = {"name": args.name, "model": args.model, "adapter": args.adapter, "split": args.split,
            "views_file": " ".join(args.views), "precision": precision}
    summary = evaluate(policy, views, load_config(), args.out, meta, batch_size=args.batch_size)
    print((Path(args.out) / "report.md").read_text()[:3000])
    print("net utility:", summary["metrics"]["net_utility"]["value"])


if __name__ == "__main__":
    main()
