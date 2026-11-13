"""Test the lead-4 system (docs/PREREGISTRATION_v10.md): the deciding agent on stored reports, with one of the
pre-registered ablations. Writes the same files as scripts/evaluate.py, so every table reads it.

    python scripts/eval_mas.py --model Qwen/Qwen3.5-4B --arbiter ADAPTERS/v4q_mas_s0/final --ablation full \
        --views VIEWS... --reports RESULTS/mas_reports/test.jsonl --out RESULTS/v4q_mas_s0_test --name v4q_mas_s0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views, select_cases  # noqa: E402
from medscope.mas.arbiter import ABLATIONS, ablation_key  # noqa: E402
from medscope.mas.reports import read_reports  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--arbiter", required=True)
    ap.add_argument("--ablation", choices=sorted(ABLATIONS), default="full")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--vocab-from", nargs="+", default=None)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--only-with-reports", action="store_true", help="test only the views that have reports (smoke test)")
    args = ap.parse_args()
    from medscope.mas.evaluate import arbiter_episodes
    from medscope.train.hf_policy import HFPolicy

    views = select_cases([v for f in args.views for v in load_views(f)], None)
    reports = read_reports(args.reports)
    if args.only_with_reports:
        views = [v for v in views if v.view_id in reports]
    cfg = with_vocab(load_config(), [v for f in (args.vocab_from or args.views) for v in load_views(f)])
    policy = HFPolicy(args.model, adapter=args.arbiter, max_new_tokens=384)
    precision = ("4bit" if policy.load_in_4bit else str(policy.dtype).replace("torch.", "")) + "|" + ablation_key(args.ablation)
    meta = {"name": args.name, "model": args.model, "adapter": args.arbiter, "split": args.split, "ablation": args.ablation,
            "reports": args.reports, "views_file": " ".join(args.views), "precision": precision}
    if args.vocab_from:
        meta["vocab_from"] = " ".join(args.vocab_from)
    summary = evaluate(policy, views, cfg, args.out, meta, batch_size=args.batch_size,
                       episodes=arbiter_episodes(policy, cfg, reports, ABLATIONS[args.ablation]))
    print((Path(args.out) / "report.md").read_text()[:2000])
    print("net utility:", summary["metrics"]["net_utility"]["value"])


if __name__ == "__main__":
    main()
