"""Rejection sampling for fine-tuning (RFT): let the model try each training view several
times and keep its best successful episode.

Why not more RL: a confident SFT agent makes the same choice in nearly every sample, so
group-relative advantages vanish (see docs/RESULTS_LOG.md, RL runs 1 and 2). Rejection
sampling still learns from those views: whenever any one of k samples succeeds, that
episode, in the model's own words and tool use, becomes a training example.

Success means the right decision for the view: a correct answer when the lesion is there,
saying it is absent when it isn't (erased or naturally absent), asking to clarify on an
unusable image. Among successes the highest reward wins (grounded box, fewer tool calls).

Usage:
    python scripts/sample_rft.py --model Qwen/Qwen3.5-4B --adapter adapters/sft_v2/final \
        --views views/train/views_clean.jsonl --negatives neg/views_negatives_train.jsonl \
        --per-kind 150 --k 4 --out adapters/rft/samples.jsonl
Reruns skip views already sampled.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.schema import View, ViewKind  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402


def success(view: View, outcome) -> bool:
    if outcome.malformed:
        return False
    if view.kind is ViewKind.DEGRADED:
        return outcome.action == "clarify"
    return outcome.action == "answer" and bool(outcome.correct)


def pick_views(views: list[View], per_kind: int, seed: int = 0) -> list[View]:
    """Up to `per_kind` views of each kind, spread across datasets (case-id prefixes)."""
    rng = np.random.default_rng(seed)
    by_kind: dict[ViewKind, list[View]] = defaultdict(list)
    for v in views:
        by_kind[v.kind].append(v)
    picked = []
    for kind in sorted(by_kind, key=lambda k: k.value):
        vs = by_kind[kind]
        idx = rng.permutation(len(vs))[:per_kind]
        picked += [vs[i] for i in sorted(idx)]
    order = rng.permutation(len(picked))
    return [picked[i] for i in order]


def best_episode(view: View, episodes) -> dict:
    wins = [e for e in episodes if success(view, e.outcome)]
    rec = {"view_id": view.view_id, "kind": view.kind.value, "k": len(episodes), "successes": len(wins),
           "rewards": [round(e.outcome.reward, 3) for e in episodes], "kept": bool(wins)}
    if wins:
        best = max(wins, key=lambda e: e.outcome.reward)
        rec["turns"] = [t.text for t in best.turns]
        rec["reward"] = best.outcome.reward
    return rec


def summary(recs: list[dict]) -> str:
    by = defaultdict(list)
    for r in recs:
        by[r["kind"]].append(r)
    lines = ["| View kind | Views | Any success (kept) | Mean successes per view |", "| --- | --- | --- | --- |"]
    for k in sorted(by):
        rs = by[k]
        lines.append(f"| {k} | {len(rs)} | {np.mean([r['kept'] for r in rs]):.0%} | "
                     f"{np.mean([r['successes'] / r['k'] for r in rs]):.0%} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="*", default=[])
    ap.add_argument("--per-kind", type=int, default=150)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from medscope.agent.episode import run_group
    from medscope.train.hf_policy import HFPolicy

    views = [v for f in args.views + args.negatives for v in load_views(f)]
    todo = pick_views(views, args.per_kind)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["view_id"] for l in out.read_text().splitlines() if l.strip()} if out.exists() else set()
    todo = [v for v in todo if v.view_id not in done]
    print(f"{len(done)} views already sampled, {len(todo)} to go ({args.k} samples each)", flush=True)

    cfg = with_vocab(load_config(), views)
    policy = HFPolicy(args.model, adapter=args.adapter, max_new_tokens=args.max_new_tokens)
    t0, kept = time.time(), Counter()
    with open(out, "a") as f:
        for i, v in enumerate(todo):
            rec = best_episode(v, run_group(policy, v, cfg, args.k, sample=True))
            f.write(json.dumps(rec) + "\n")
            f.flush()
            kept[rec["kept"]] += 1
            if (i + 1) % 10 == 0 or i == 0:
                rate = (time.time() - t0) / (i + 1)
                print(f"  {i + 1}/{len(todo)} views, kept {kept[True]}, {rate:.1f}s each, "
                      f"~{rate * (len(todo) - i - 1) / 60:.0f} min left", flush=True)

    recs = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    table = summary(recs)
    (out.parent / "rft_summary.md").write_text(table + "\n")
    print(table)


if __name__ == "__main__":
    main()
