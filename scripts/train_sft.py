"""Train a grounding or agentic LoRA adapter on synthetic trajectories.

Usage:
    python scripts/train_sft.py --model Qwen/Qwen3.5-4B --views views/train/views_clean.jsonl \
        --mode agentic --out /content/drive/MyDrive/medscope/adapters/sft_agentic
Rerunning with the same --out resumes from the last checkpoint.
"""

from __future__ import annotations

import argparse
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.train.sft import MODES, train_sft  # noqa: E402


def v4_mix(views, args):
    """The v4 data options: paraphrases, small-lesion oversampling, 'absent' share, balanced health questions."""
    from collections import Counter
    from dataclasses import replace
    from medscope.actions import asks_health, normalise_answer
    from medscope.data.loaders.common import stable_index
    from medscope.data.paraphrase import TRAIN, paraphrase_view
    from medscope.data.schema import ViewKind
    from medscope.train.sft import SMALL_LESION, lesion_fraction
    if args.paraphrase_prob > 0:
        views = [paraphrase_view(v, TRAIN) if "#rft" not in v.view_id
                 and stable_index(v.case_id + "para", 1000) < 1000 * args.paraphrase_prob else v
                 for v in views]       # recorded episodes (#rft) keep the wording they were sampled with
    if args.balance_health:
        health = [v for v in views if (v.meta or {}).get("benchmark") and asks_health(v.question)]
        by = {a: [v for v in health if normalise_answer(v.answer) == a] for a in ("yes", "no")}
        n = min(len(by["yes"]), len(by["no"]))
        drop = {v.view_id for a in by for v in sorted(by[a], key=lambda v: stable_index(v.view_id, 10 ** 9))[n:]}
        views = [v for v in views if v.view_id not in drop]
        print(f"balanced health questions: kept {n} Yes and {n} No, dropped {len(drop)}")
    if args.oversample_small > 1:
        small = [v for v in views if (lesion_fraction(v) or 1) < SMALL_LESION]
        views = views + [replace(v, view_id=f"{v.view_id}#s{i}") for v in small for i in range(1, args.oversample_small)]
        print(f"small lesions: {len(small)} views repeated {args.oversample_small}x")
    if args.min_absent_share > 0:
        absent = [v for v in views if v.kind in (ViewKind.TARGET_REMOVAL, ViewKind.NATURAL_NEGATIVE)]
        share = len(absent) / max(1, len(views))
        if absent and share < args.min_absent_share:
            need = int((args.min_absent_share * len(views) - len(absent)) / (1 - args.min_absent_share)) + 1
            reps = [replace(absent[i % len(absent)], view_id=f"{absent[i % len(absent)].view_id}#a{i // len(absent) + 1}")
                    for i in range(need)]
            views = views + reps
            print(f"'absent' views: {share:.0%} -> {len(absent) + need} of {len(views)}")
    print("view kinds:", dict(Counter(v.kind.value for v in views)))
    return views


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--views", required=True, nargs="+", help="one or more views files")
    ap.add_argument("--negatives", nargs="*", default=[], help="natural-negative views files to add")
    ap.add_argument("--init", default=None, help="continue training this adapter instead of a new one")
    ap.add_argument("--lora-r", type=int, default=16, help="LoRA rank of a new adapter (alpha = 2r); the recipe uses 16")
    ap.add_argument("--lora-vision", action="store_true",
                    help="new adapter also adapts the vision encoder and projector (frozen in the recipe)")
    ap.add_argument("--vision-lr-scale", type=float, default=1.0,
                    help="with --lora-vision: learning rate of the vision adapters as a share of --lr (0.1 = a tenth)")
    ap.add_argument("--kinds", nargs="*", default=None,
                    help="train only on these view kinds (ablations), e.g. original natural_negative degraded")
    ap.add_argument("--subsample", type=int, default=None,
                    help="train on this many synthetic views (random, fixed seed) instead of all of them")
    ap.add_argument("--replays", default=None,
                    help="rejection-sampling episodes (jsonl from sample_rft.py): trained on as recorded")
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0,
                    help="training seed: LoRA initialisation, dropout, data order and trajectory jitter")
    # ---- v4 recipe options (all off by default, so earlier runs are reproduced exactly) ----
    ap.add_argument("--window-prob", type=float, default=0.0,
                    help="share of grey-scale trajectories that start with a window call")
    ap.add_argument("--small-zoom", action="store_true", help="always zoom before answering about a lesion under 2%% of the image")
    ap.add_argument("--oversample-small", type=int, default=1,
                    help="repeat every view of a case whose lesion is under 2%% of the image this many times")
    ap.add_argument("--paraphrase-prob", type=float, default=0.0,
                    help="share of cases whose templated question is reworded with a training paraphrase")
    ap.add_argument("--min-absent-share", type=float, default=0.0,
                    help="repeat 'absent' views (lesion erased, healthy images) until they are at least this share")
    ap.add_argument("--balance-health", action="store_true",
                    help="general-VQA replay: keep as many 'Is X healthy/normal?' questions answered Yes as No")
    ap.add_argument("--schedule-steps", type=int, default=None,
                    help="length of the learning-rate schedule (default: --max-steps, else the estimated steps); "
                         "an ablation arm uses the main arm's, so both follow the same schedule")
    ap.add_argument("--extra-views", nargs="*", default=[],
                    help="views added in full after subsampling (post-hoc v4.1: the SIIM pneumothorax training cases)")
    ap.add_argument("--hard-repeat", type=int, default=1,
                    help="rejection sampling: repeat episodes kept from views the model mostly failed this many times")
    return ap


def training_views(args) -> tuple[list, list, Optional[dict]]:
    """Every view this run trains on (in order), the natural negatives among them, and the replayed episodes."""
    views = [v for f in args.views for v in load_views(f)]
    negs = [v for f in args.negatives for v in load_views(f)]
    if args.kinds:
        views = [v for v in views if v.kind.value in args.kinds]
        negs = [v for v in negs if v.kind.value in args.kinds]
        print(f"ablation: only {args.kinds} views")
    by_id = {v.view_id: v for v in views + negs}     # before subsampling: kept episodes may be on any view
    if args.subsample and args.subsample < len(views) + len(negs):
        import numpy as np
        rng = np.random.default_rng(7)
        share = args.subsample / (len(views) + len(negs))   # same share from both pools
        views = [views[i] for i in sorted(rng.permutation(len(views))[:round(share * len(views))])]
        negs = [negs[i] for i in sorted(rng.permutation(len(negs))[:round(share * len(negs))])]
    replays = None
    if args.replays:
        from medscope.eval.runner import read_jsonl
        recs = read_jsonl(Path(args.replays))
        from dataclasses import replace
        kept = [replace(by_id[r["view_id"]], view_id=r["view_id"] + "#rft")
                for r in recs if r.get("kept") and r["view_id"] in by_id]
        # a separate copy of each view carries the model's own episode; the original keeps its synthetic one
        replays = {r["view_id"] + "#rft": r["turns"] for r in recs if r.get("kept")}
        print(f"{len(kept)} self-generated episodes kept by rejection sampling")
        if args.hard_repeat > 1:      # an episode the model rarely gets right teaches the most: repeat it
            hard = {r["view_id"] + "#rft" for r in recs if r.get("kept") and r["successes"] / r["k"] <= 0.5}
            extra = [replace(v, view_id=f"{v.view_id}#{i}") for v in kept if v.view_id in hard
                     for i in range(1, args.hard_repeat)]
            for v in extra:
                replays[v.view_id] = replays[v.view_id.rsplit("#", 1)[0]]
            print(f"{len(hard)} of them from views it mostly failed: repeated {args.hard_repeat}x")
            kept = kept + extra
        views = views + kept          # their own episodes, on top of the synthetic set
    views += negs
    if args.extra_views:
        extra = [v for f in args.extra_views for v in load_views(f)]
        print(f"{len(extra)} extra views added in full")
        views += extra
    views = v4_mix(views, args)
    return views, negs, replays


def main() -> None:
    args = parser().parse_args()

    from medscope.train.hf_policy import HFPolicy

    views, negs, replays = training_views(args)
    print(f"training on {len(views)} views ({len(negs)} natural negatives)")

    import random
    import numpy as np
    import torch
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.init:
        policy = HFPolicy(args.model, adapter=args.init, trainable=True)
    else:
        policy = HFPolicy(args.model, trainable=True, new_lora=True, lora_r=args.lora_r, lora_vision=args.lora_vision)
    trainable = sum(p.numel() for p in policy.model.parameters() if p.requires_grad)
    print(f"trainable LoRA parameters: {trainable / 1e6:.1f}M")
    train_sft(policy, views, args.mode, args.out, epochs=args.epochs, lr=args.lr,
              grad_accum=args.grad_accum, max_steps=args.max_steps, save_every=args.save_every,
              replays=replays, seed=args.seed, window_prob=args.window_prob, small_zoom=args.small_zoom,
              schedule_steps=args.schedule_steps, vision_lr_scale=args.vision_lr_scale)


if __name__ == "__main__":
    main()
