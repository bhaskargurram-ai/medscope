"""On-policy group-relative policy optimisation for the multi-turn agent.

Each step: pick a few views, run a group of sampled episodes per view (the agent
may zoom/window up to the tool budget), score them with the cost-matrix reward,
normalise rewards within each group into advantages, and push up the log-prob of
every token the agent generated in proportion to its episode's advantage.

Because each batch is used for exactly one update right after it is sampled, the
importance ratio is 1 and no clipping is needed. Groups where every episode got
the same reward carry no signal and are skipped. An optional KL penalty keeps the
policy near its starting adapter (loaded as a frozen "ref" adapter).

Dynamic sampling (max_draws > views_per_step, as in DAPO): a confident SFT policy often
makes the same choice in every episode of a group, so most groups carry no signal. Groups
are then drawn one view at a time until views_per_step of them have signal, or max_draws
groups have been rolled out; only the groups with signal are trained on.
"""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..agent.episode import Episode, run_group
from ..data.schema import View
from .common import (
    append_log,
    checkpoint_path,
    load_adapter_weights,
    load_optimizer,
    lr_at,
    read_state,
    save_optimizer,
    write_state,
)


def group_advantages(rewards: list[float], eps: float = 1e-4) -> list[float]:
    r = np.asarray(rewards, dtype=float)
    if r.std() < 1e-6:
        return [0.0] * len(r)
    return ((r - r.mean()) / (r.std() + eps)).tolist()


def episode_tokens(ep: Episode) -> int:
    return sum(len(t.extra["gen_ids"]) for t in ep.turns if t.extra is not None)


def collect_groups(rollout: Callable[[int], list], rewards: Callable[[list], list[float]],
                   cursor: int, want: int, max_draws: int = 0,
                   rollout_many: Optional[Callable[[list[int]], list[list]]] = None,
                   draw_batch: int = 1) -> tuple[list[tuple[list, list[float]]], int]:
    """Roll out groups for one step, starting at position `cursor` of the view order.

    max_draws <= want: exactly `want` groups (plain GRPO). Otherwise keep drawing until `want`
    groups have signal (non-zero advantages) or `max_draws` groups were drawn.
    Returns every drawn group with its advantages, and the next cursor.

    draw_batch > 1 with `rollout_many`: the same rule, but `draw_batch` views are rolled out in one generation
    batch. Groups are taken in order until `want` have signal; any rolled out past that point are dropped and the
    cursor stops right after the last group used, so the groups trained on and the cursor follow the one-at-a-time
    rule exactly (only the wasted generation differs)."""
    groups: list[tuple[list, list[float]]] = []
    if rollout_many is not None and draw_batch > 1 and max_draws > want:
        with_signal = 0
        while with_signal < want and len(groups) < max_draws:
            n = min(draw_batch, max_draws - len(groups))
            for eps_ in rollout_many(list(range(cursor, cursor + n))):
                cursor += 1
                advs = group_advantages(rewards(eps_))
                groups.append((eps_, advs))
                with_signal += any(a != 0 for a in advs)
                if with_signal >= want:
                    break
        return groups, cursor
    if max_draws <= want:
        for i in range(want):
            eps_ = rollout(cursor + i)
            groups.append((eps_, group_advantages(rewards(eps_))))
        return groups, cursor + want
    with_signal = 0
    while with_signal < want and len(groups) < max_draws:
        eps_ = rollout(cursor)
        cursor += 1
        advs = group_advantages(rewards(eps_))
        groups.append((eps_, advs))
        with_signal += any(a != 0 for a in advs)
    return groups, cursor


def train_grpo(
    policy,
    views: list[View],
    cfg: dict,
    out_dir: str | Path,
    steps: int = 150,
    views_per_step: int = 2,
    group_size: int = 4,
    lr: float = 1e-5,
    beta: float = 0.0,
    ref_adapter: Optional[str] = None,
    save_every: int = 10,
    seed: int = 0,
    log: Callable[[str], None] = print,
    eval_every: int = 0,
    eval_fn: Optional[Callable[[int], dict]] = None,
    max_draws: int = 0,
    draw_batch: int = 1,
) -> Path:
    import torch

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = policy.model
    use_kl = beta > 0
    if use_kl:
        if not ref_adapter:
            raise ValueError("beta > 0 needs ref_adapter (the starting adapter)")
        model.load_adapter(ref_adapter, adapter_name="ref", is_trainable=False)
        model.set_adapter("default")
    # deterministic log-probs (the samples came from the same weights); after loading "ref",
    # so its dropout modules are zeroed too
    for m in model.modules():
        if isinstance(m, torch.nn.Dropout):
            m.p = 0.0

    params = [p for n, p in model.named_parameters() if p.requires_grad and ".ref." not in n]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)

    state = read_state(out)
    final = out / "final"
    if state.get("step", 0) >= steps and final.exists():
        log(f"already finished {steps} steps; final adapter is at {final}")
        return final
    start = state.get("step", 0)
    if start and checkpoint_path(out).exists():
        load_adapter_weights(model, checkpoint_path(out))
        load_optimizer(opt, out)
        log(f"resuming GRPO at step {start}")

    rng = np.random.default_rng(seed)
    per_step = max(views_per_step, max_draws)
    order = rng.permutation(len(views)).tolist() * (steps * per_step // max(1, len(views)) + 2)
    cursor = state.get("cursor", start * views_per_step)

    def rollout(pos: int) -> list[Episode]:
        return run_group(policy, views[order[pos]], cfg, group_size, sample=True)

    def rollout_many(positions: list[int]) -> list[list[Episode]]:
        """Groups for several views in one generation batch (group_size episodes each)."""
        from ..agent.episode import run_episodes
        vs = [views[order[p]] for p in positions for _ in range(group_size)]
        eps_ = run_episodes(policy, vs, cfg, sample=True)
        return [eps_[i * group_size:(i + 1) * group_size] for i in range(len(positions))]

    for step in range(start, steps):
        t0 = time.time()
        groups, cursor = collect_groups(rollout, lambda eps_: [e.outcome.reward for e in eps_],
                                        cursor, views_per_step, max_draws,
                                        rollout_many=rollout_many if draw_batch > 1 else None, draw_batch=draw_batch)

        model.train()
        opt.zero_grad(set_to_none=True)
        active = [(e, a) for eps_, advs in groups for e, a in zip(eps_, advs) if a != 0.0 and episode_tokens(e) > 0]
        kl_total, n_tok_total = 0.0, 0
        for ep, adv in active:
            n_tok = episode_tokens(ep)
            for turn in ep.turns:
                ids = turn.extra["gen_ids"]
                if len(ids) == 0:
                    continue
                context = ep.messages[:turn.context_len]
                lp = policy.token_logprobs(context, ids)
                loss = -(adv * lp.sum()) / (n_tok * len(active))
                if use_kl:
                    model.set_adapter("ref")
                    with torch.no_grad():
                        ref_lp = policy.token_logprobs(context, ids)
                    model.set_adapter("default")
                    d = ref_lp - lp
                    kl = torch.exp(d) - d - 1
                    loss = loss + beta * kl.sum() / (n_tok * len(active))
                    kl_total += float(kl.sum())
                loss.backward()
                n_tok_total += len(ids)
        if active:
            for g in opt.param_groups:
                g["lr"] = lr_at(step, steps, lr, warmup_frac=0.05, min_frac=0.3)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()

        all_eps = [e for eps_, _ in groups for e in eps_]
        rec = {
            "step": step + 1,
            "reward": float(np.mean([e.outcome.reward for e in all_eps])),
            "reward_by_kind": {k: float(np.mean([e.outcome.reward for e in all_eps if e.view.kind.value == k]))
                               for k in {e.view.kind.value for e in all_eps}},
            "actions": dict(Counter(e.outcome.action or "malformed" for e in all_eps)),
            "tool_calls": float(np.mean([e.tool_calls for e in all_eps])),
            "groups_with_signal": sum(1 for _, a in groups if any(x != 0 for x in a)),
            "groups_drawn": len(groups),
            "tokens": n_tok_total,
            "kl": kl_total / max(1, n_tok_total) if use_kl else None,
            "secs": round(time.time() - t0, 1),
        }
        append_log(out, rec)
        log(f"step {rec['step']}/{steps} reward {rec['reward']:+.2f} actions {rec['actions']} "
            f"signal {rec['groups_with_signal']}/{len(groups)} ({rec['secs']}s)")

        if (step + 1) % save_every == 0 or step + 1 == steps:
            policy.save_adapter(str(checkpoint_path(out)))
            save_optimizer(opt, out)
            write_state(out, {"step": step + 1, "steps": steps, "cursor": cursor})
        if eval_fn and eval_every and (step + 1) % eval_every == 0:
            summary = eval_fn(step + 1)
            append_log(out, {"step": step + 1, "eval_net_utility": summary["metrics"]["net_utility"]["value"]})
            model.train()

    policy.save_adapter(str(final))
    log(f"saved final adapter to {final}")
    return final
