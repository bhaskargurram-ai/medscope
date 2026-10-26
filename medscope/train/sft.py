"""Supervised fine-tuning on synthetic trajectories.

Two adapters are trained from the same base and LoRA config so they can be merged:
  grounding - answerable views only, single turn, answer + evidence box, no tools
  agentic   - all four view kinds, multi-turn with zoom, refer and clarify

Loss is the mean token NLL of each assistant turn given exactly the context the
model sees at inference, so training and inference prompts match.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Iterator

import numpy as np

from ..agent.trajectories import SFTSample, build_trajectory
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

MODES = ("grounding", "agentic")


def mode_views(views: list[View], mode: str) -> list[View]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    return [v for v in views if v.answerable] if mode == "grounding" else list(views)


def view_order(views: list[View], epochs: int, seed: int) -> list[View]:
    rng = np.random.default_rng(seed)
    order = []
    for _ in range(epochs):
        order += [views[i] for i in rng.permutation(len(views))]
    return order


def samples_for(view: View, mode: str, seed: int, index: int) -> list[SFTSample]:
    rng = np.random.default_rng([seed, index])
    return build_trajectory(view, rng, direct_only=(mode == "grounding"))


def estimate_samples(views: list[View], mode: str) -> float:
    if mode == "grounding":
        return float(len(views))
    # degraded and direct answers are 1 turn; zoomed trajectories (60% of the rest) are 2
    return sum(1.0 if v.kind.value == "degraded" else 1.6 for v in views)


def train_sft(
    policy,
    views: list[View],
    mode: str,
    out_dir: str | Path,
    epochs: int = 1,
    lr: float = 2e-4,
    grad_accum: int = 8,
    max_steps: int | None = None,
    save_every: int = 50,
    seed: int = 0,
    log: Callable[[str], None] = print,
) -> Path:
    import torch

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    views = mode_views(views, mode)
    order = view_order(views, epochs, seed)
    total_steps = max_steps or max(1, int(estimate_samples(views, mode) * epochs / grad_accum))

    model = policy.model
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)

    final = out / "final"
    state = read_state(out)
    if state.get("finished") and final.exists():
        log(f"already finished; final adapter is at {final}")
        return final
    start_view, step = state.get("views_done", 0), state.get("opt_step", 0)
    if start_view and checkpoint_path(out).exists():
        load_adapter_weights(model, checkpoint_path(out))
        load_optimizer(opt, out)
        log(f"resuming from view {start_view}, optimizer step {step}")

    def optimizer_step() -> None:
        nonlocal step
        for g in opt.param_groups:
            g["lr"] = lr_at(step, total_steps, lr)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1

    micro, running, t0 = 0, [], time.time()
    save_due = False
    for vi in range(start_view, len(order)):
        for s in samples_for(order[vi], mode, seed, vi):
            target = policy.target_ids(s.target)
            lp = policy.token_logprobs(s.messages, target)
            loss = -lp.mean()
            (loss / grad_accum).backward()
            running.append(loss.item())
            micro += 1
            if micro % grad_accum == 0:
                optimizer_step()
                if step % 10 == 0:
                    rec = {"step": step, "loss": float(np.mean(running)), "lr": opt.param_groups[0]["lr"],
                           "views_done": vi + 1, "secs": round(time.time() - t0)}
                    append_log(out, rec)
                    log(f"step {step}/{total_steps} loss {rec['loss']:.4f} ({vi + 1}/{len(order)} views)")
                    running = []
                save_due = save_due or step % save_every == 0
        # checkpoint only between views, so a resume never skips half a trajectory
        if save_due and micro % grad_accum == 0:
            policy.save_adapter(str(checkpoint_path(out)))
            save_optimizer(opt, out)
            write_state(out, {"views_done": vi + 1, "opt_step": step, "mode": mode, "total_steps": total_steps})
            save_due = False
        if max_steps and step >= max_steps:
            break
    if micro % grad_accum:
        optimizer_step()  # leftover gradients from the last partial batch

    policy.save_adapter(str(final))
    write_state(out, {"views_done": len(order), "opt_step": step, "mode": mode, "total_steps": total_steps,
                      "finished": True})
    log(f"saved final adapter to {final}")
    return final
