"""Stored reports of the lead-4 agents (direct reader, question-blind reader, specialist, verifier) for a set of
views. Resumable: views already in --out with the same key are skipped.

    python scripts/mas_reports.py --model Qwen/Qwen3.5-4B --adapter ADAPTERS/v4_s1/final \
        --specialist ADAPTERS/specialist_v10 --views VIEWS... --out RESULTS/mas_reports/test.jsonl
    # training subset for the arbiter: --subsample 4000 (stratified by view kind, seed 0)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", required=True, help="the frozen recipe adapter the readers use")
    ap.add_argument("--specialist", required=True, help="folder with model.pt and specialist.json")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--vocab-from", nargs="+", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subsample", type=int, default=None, help="stratified subset of this many views (training)")
    ap.add_argument("--exclude-meta", nargs="*", default=["inserted", "benchmark"],
                    help="leave out views whose meta has any of these flags")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--inpainter", default="lama", help="the verifier's inpainter (the training tool)")
    args = ap.parse_args()
    from medscope.data.inpaint import get_inpainter
    from medscope.mas.arbiter import stratified_subset
    from medscope.mas.reports import compute_reports
    from medscope.mas.specialist import Specialist
    from medscope.train.hf_policy import HFPolicy

    views = [v for f in args.views for v in load_views(f)]
    views = [v for v in views if not any((v.meta or {}).get(k) for k in args.exclude_meta)]
    if args.subsample:
        views = stratified_subset(views, args.subsample, seed=0)
    kinds = {}
    for v in views:
        kinds[v.kind.value] = kinds.get(v.kind.value, 0) + 1
    print(f"{len(views)} views: {kinds}")
    cfg = with_vocab(load_config(), [v for f in (args.vocab_from or args.views) for v in load_views(f)])
    spec = Specialist(args.specialist)
    print(f"specialist threshold {spec.threshold}")
    from medscope.mas.reports import remaining_reports
    left = remaining_reports(views, args.out, args.adapter, {"threshold": spec.threshold})
    if left == 0:
        print(f"all {len(views)} reports already in {args.out}")
        return
    policy = HFPolicy(args.model, adapter=args.adapter, max_new_tokens=384)
    compute_reports(policy, spec, get_inpainter(args.inpainter), views, cfg, args.out, adapter=args.adapter,
                    batch_size=args.batch_size)


if __name__ == "__main__":
    main()
