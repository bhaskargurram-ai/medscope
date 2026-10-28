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

import shutil  # noqa: E402

from medscope.eval.runner import evaluate, load_views, remaining, select_cases  # noqa: E402
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

    import gc

    import torch

    def build(name, kind, weights, density):
        """Create a merged adapter. Built without gradients; deleted again after scoring so
        merged adapters never pile up in GPU memory (that ran an 80 GB A100 out of memory)."""
        torch.manual_seed(0)  # DARE prunes at random
        kw = {"density": density} if density is not None else {}
        if kind.endswith("svd"):
            kw["svd_rank"] = SVD_RANK
        with torch.no_grad():
            model.add_weighted_adapter(["default", "grounding"], weights, adapter_name=name,
                                       combination_type=kind, **kw)

    def drop(name):
        model.set_adapter("default")
        model.delete_adapter(name)
        gc.collect()
        torch.cuda.empty_cache()

    scores = {}
    for name, kind, weights, density in CANDIDATES:
        if args.only and name not in args.only:
            continue
        adapter = {"agentic_only": "default", "grounding_only": "grounding"}.get(name, name)
        run_dir = Path(args.results) / f"merge_{name}"
        meta = {"name": f"merge_{name}", "model": args.model, "split": "validation",
                "combination": kind, "weights": weights, "density": density,
                "svd_rank": SVD_RANK if kind and kind.endswith("svd") else None}
        todo = remaining(views, run_dir, meta.get("precision"))
        built = False
        if todo:  # only build and load what still has to be evaluated
            if adapter not in model.peft_config:
                build(adapter, kind, weights, density)
                built = True
            model.set_adapter(adapter)
            model.eval()
        print(f"=== {name}: {len(views) - len(todo)} views already scored, {len(todo)} to run ===")
        summary = evaluate(policy, views, cfg, run_dir, meta)
        scores[name] = summary["metrics"]["net_utility"]["value"]
        print(f"{name}: net utility {scores[name]:.3f}")
        if built:
            drop(adapter)

    best = max(scores, key=lambda k: scores[k])
    out = Path(args.out)
    dest = out / "best"
    if dest.exists():
        shutil.rmtree(dest)
    if best in ("agentic_only", "grounding_only"):  # an unmerged adapter wins: copy its files
        shutil.copytree(args.agentic if best == "agentic_only" else args.grounding, dest)
    else:
        name, kind, weights, density = next(c for c in CANDIDATES if c[0] == best)
        build(name, kind, weights, density)
        model.set_adapter(name)
        policy.save_adapter(str(dest), adapter_name=name)
    (out / "best.json").write_text(json.dumps({"best": best, "net_utility": scores[best], "all": scores}, indent=2))
    print(f"best: {best} (net utility {scores[best]:.3f}) -> saved to {dest}")


if __name__ == "__main__":
    main()
