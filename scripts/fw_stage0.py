"""Framework stage 0 (docs/FRAMEWORK_STAGE0.md): site-matched edits, decision log-odds and probes, validation only.

    python scripts/fw_stage0.py --views VAL... --negatives VAL_NEG... --dev-dir RESULTS/screen_b/dev \
        --out RESULTS/fw_stage0 --base-model Qwen/Qwen3.5-4B \
        --model recipe=ADAPTERS/v4_s1/final --model base= --model nocf=ADAPTERS/v4q_nocf_s0/final ...
    # --stage views (LaMa on the GPU), score (one model at a time), analyse (CPU)
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402

HIDDEN_MODELS = ("recipe", "base")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="+", required=True)
    ap.add_argument("--cases", type=int, default=200)
    ap.add_argument("--negs", type=int, default=80)
    ap.add_argument("--dev-dir", required=True, help="the screening dev folder (TELEA views are reused or made there)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=["views", "score", "analyse", "all"], default="all")
    ap.add_argument("--base-model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--model", action="append", default=[], help="name=adapter (empty adapter = the base model)")
    ap.add_argument("--layers", default="4,8,12,16,20,24,28,32")
    ap.add_argument("--hidden-dir", default=None, help="where hidden features go (default OUT/hidden; local disk is faster)")
    ap.add_argument("--probes", default=None, help="screening stage B probes.jsonl (the agent's answers, to check the score)")
    args = ap.parse_args()

    from medscope.fw.stage0 import new_views
    from medscope.screen.probes import dev_views
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    views = [v for f in args.views for v in load_views(f)]
    negs = [v for f in args.negatives for v in load_views(f)]
    dev = dev_views(views, negs, args.cases, args.negs, args.dev_dir)
    originals = {v.case_id: v for v in dev if v.kind.value == "original"}
    layers = [int(x) for x in args.layers.split(",")]
    hidden_root = Path(args.hidden_dir) if args.hidden_dir else out / "hidden"

    if args.stage in ("views", "all", "score"):
        lama = None
        if args.stage != "score":
            from medscope.data.inpaint import lama_inpaint
            lama = lama_inpaint
        if lama is None:
            def lama(*_):      # score stage: views must already exist
                raise SystemExit("ring/partial LaMa views are missing: run --stage views first")
        extra = new_views(dev, out / "views", lama)
        (out / "views.json").write_text(json.dumps([v.to_dict() for v in extra]))
        kinds: dict[str, int] = {}
        for v in extra:
            k = f"{v.meta['inpainter']}/{v.meta['stage0_variant']}"
            kinds[k] = kinds.get(k, 0) + 1
        print(f"dev: {len(dev)} views; new: {len(extra)} {kinds}")
    from medscope.fw.stage0 import scoreable
    all_views = [v for v in dev + ([] if args.stage == "analyse" else extra) if scoreable(v, originals)]
    print(f"scoreable views (yes/no questions): {len(all_views)}")

    if args.stage in ("score", "all"):
        import torch

        from medscope.fw.stage0 import score_views
        from medscope.train.hf_policy import HFPolicy
        for spec in args.model:
            name, _, adapter = spec.partition("=")
            if adapter and not Path(adapter).exists():
                print(f"{name}: adapter {adapter} not found, skipped")
                continue
            print(f"== {name} ({adapter or 'no adapter'})")
            policy = HFPolicy(args.base_model, adapter=adapter or None, max_new_tokens=8)
            hidden = hidden_root / name if name in HIDDEN_MODELS else None
            score_views(policy, all_views, originals, out / f"scores_{name}.jsonl", hidden, layers)
            del policy
            gc.collect()
            torch.cuda.empty_cache()

    if args.stage in ("analyse", "all"):
        from medscope.fw.analysis import agreement, decide, load_feats, model_summary, probe_summary, report
        from medscope.fw.stage0 import read_scores
        from medscope.screen.probes import read_probes
        summ, scores = {}, {}
        for spec in args.model:
            name = spec.partition("=")[0]
            s = read_scores(out / f"scores_{name}.jsonl")
            if s:
                scores[name], summ[name] = s, model_summary(s)
        if "recipe" not in summ:
            raise SystemExit("no recipe scores yet")
        by_id = {v.view_id: v for v in dev}
        agree, n_agree = agreement(scores["recipe"], read_probes(args.probes) if args.probes else {}, by_id)
        print(f"score agreement with the recipe's agent answers: {agree:.3f} on {n_agree} views")
        probes = {}
        for name in HIDDEN_MODELS:
            feats = load_feats(hidden_root / name)
            if feats and name in scores:
                probes[name] = probe_summary(feats, scores[name], len(layers))
        decision = decide(summ, probes.get("recipe"), agree)
        md = report(summ, probes.get("recipe"), decision)
        if "base" in probes:
            md += "\n## Same probes on the untrained base model\n\n" + "\n".join(
                f"- {k}: best {max([x for x in v if x == x], default=float('nan')):.3f}" for k, v in probes["base"].items()) + "\n"
        (out / "stage0.md").write_text(md)
        (out / "stage0.json").write_text(json.dumps({"summary": summ, "probes": probes, "decision": decision,
                                                     "agreement_n": n_agree}, indent=1, default=float))
        print(md)


if __name__ == "__main__":
    main()
