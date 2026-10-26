"""Merge the grounding and agentic adapters several ways and keep the best.

Each candidate is evaluated on a validation subset; the one with the highest net
clinical utility is saved to --out/best and recorded in --out/best.json. Every
candidate's results stay in --results/<name> for the merging-vs-abstention analysis.

Usage:
    python scripts/merge_search.py --model Qwen/Qwen3.5-4B \
        --grounding adapters/sft_grounding/final --agentic adapters/sft_agentic/final \
        --views views/validation/views_clean.jsonl --out adapters/merged --results results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views, select_cases  # noqa: E402
from medscope.rewards import load_config  # noqa: E402

# name, PEFT combination_type, weights [agentic, grounding], density.
# For LoRA, PEFT's plain "linear"/"ties"/"dare_ties" combine the A and B factors separately,
# which mixes cross terms of two independently trained adapters. The *_svd variants merge
# the actual weight updates (delta W) and re-factorise them; "cat" is exact.
CANDIDATES = [
    ("agentic_only", None, None, None),
    ("grounding_only", None, None, None),
    ("svd_50_50", "svd", [0.5, 0.5], None),
    ("svd_70_30", "svd", [0.7, 0.3], None),
    ("cat_100_50", "cat", [1.0, 0.5], None),
    ("ties_svd_d50", "ties_svd", [1.0, 1.0], 0.5),
    ("dare_ties_svd_d50", "dare_ties_svd", [1.0, 1.0], 0.5),
]
SVD_RANK = 32


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--grounding", required=True)
    ap.add_argument("--agentic", required=True)
    ap.add_argument("--views", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--limit-cases", type=int, default=40)
    ap.add_argument("--only", nargs="*", default=None, help="run only these candidate names")
    args = ap.parse_args()

    from medscope.train.hf_policy import HFPolicy

    cfg = load_config()
    views = select_cases(load_views(args.views), args.limit_cases, seed=1)
    policy = HFPolicy(args.model, adapter=args.agentic)        # loaded as adapter "default"
    model = policy.model
    model.load_adapter(args.grounding, adapter_name="grounding")

    scores = {}
    for name, kind, weights, density in CANDIDATES:
        if args.only and name not in args.only:
            continue
        if name == "agentic_only":
            adapter = "default"
        elif name == "grounding_only":
            adapter = "grounding"
        else:
            adapter = name
            if adapter not in model.peft_config:
                import torch
                torch.manual_seed(0)  # DARE prunes at random
                kw = {"density": density} if density is not None else {}
                if kind.endswith("svd"):
                    kw["svd_rank"] = SVD_RANK
                model.add_weighted_adapter(["default", "grounding"], weights, adapter_name=adapter,
                                           combination_type=kind, **kw)
        model.set_adapter(adapter)
        model.eval()
        print(f"=== {name} (adapter {adapter}) ===")
        summary = evaluate(policy, views, cfg, Path(args.results) / f"merge_{name}",
                           {"name": f"merge_{name}", "model": args.model, "split": "validation",
                            "combination": kind, "weights": weights, "density": density,
                            "svd_rank": SVD_RANK if kind and kind.endswith("svd") else None})
        scores[name] = (summary["metrics"]["net_utility"]["value"], adapter)
        print(f"{name}: net utility {scores[name][0]:.3f}")

    best = max(scores, key=lambda k: scores[k][0])
    best_adapter = scores[best][1]
    out = Path(args.out)
    model.set_adapter(best_adapter)
    policy.save_adapter(str(out / "best"), adapter_name=best_adapter)
    (out / "best.json").write_text(json.dumps({"best": best, "net_utility": scores[best][0],
                                               "all": {k: v[0] for k, v in scores.items()}}, indent=2))
    print(f"best: {best} -> saved to {out / 'best'}")


if __name__ == "__main__":
    main()
