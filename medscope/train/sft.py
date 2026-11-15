"""Supervised fine-tuning on synthetic trajectories.

Two adapters are trained from the same base and LoRA config so they can be merged:
  grounding - answerable views only, single turn, answer + evidence box, no tools
  agentic   - every view kind, multi-turn with zoom; says "No" when the lesion is absent,
              asks to clarify on unusable images

Loss is the mean token NLL of each assistant turn given exactly the context the
model sees at inference, so training and inference prompts match.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Iterator, Optional

import numpy as np

from ..agent.trajectories import SFTSample, build_trajectory, replay_samples
from ..rewards import load_config
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


SMALL_LESION = 0.02     # lesion box under 2% of the image


def lesion_fraction(view: View) -> Optional[float]:
    if not view.lesion_box:
        return None
    x1, y1, x2, y2 = view.lesion_box
    return max(0, x2 - x1) * max(0, y2 - y1) / 1e6


def samples_for(view: View, mode: str, seed: int, index: int,
                replays: Optional[dict[str, list[str]]] = None, cfg: Optional[dict] = None,
                window_prob: float = 0.0, small_zoom: bool = False) -> list[SFTSample]:
    """Synthetic trajectory for the view, or the model's own recorded episode for it if one
    was kept by rejection sampling (`replays`: view_id -> assistant turns).
    v4 options: window_prob (start grey-scale trajectories with a window call), small_zoom
    (always zoom before answering about a small lesion)."""
    if replays and view.view_id in replays:
        return replay_samples(view, replays[view.view_id], cfg)
    rng = np.random.default_rng([seed, index])
    frac = lesion_fraction(view)
    zoom_prob = 1.0 if small_zoom and frac is not None and frac < SMALL_LESION else 0.6
    return build_trajectory(view, rng, zoom_prob=zoom_prob, direct_only=(mode == "grounding"), window_prob=window_prob)


def estimate_samples(views: list[View], mode: str) -> float:
    if mode == "grounding":
        return float(len(views))
    # degraded and direct answers are 1 turn; zoomed trajectories (60% of the rest) are 2
    return sum(1.0 if v.kind.value == "degraded" else 1.6 for v in views)


def prepared_views(policy, order, start_view, mode, seed, replays, cfg, window_prob, small_zoom, stop, ahead=4,
                   sample_fn=None):
    """(view index, [(sample, target ids, tokenised inputs)]) in training order. A background thread builds and
    tokenises the next views (images included) while the GPU trains on the current one, so the GPU no longer waits
    for the CPU; the samples and their order are exactly those of the plain loop. MEDSCOPE_PREFETCH=0 turns it off."""
    def build(vi):
        out = []
        samples = sample_fn(order[vi], seed, vi) if sample_fn is not None else \
            samples_for(order[vi], mode, seed, vi, replays, cfg, window_prob, small_zoom)
        for s in samples:
            target = policy.target_ids(s.target)
            inputs = policy.encode_cpu(s.messages) if hasattr(policy, "encode_cpu") else None
            out.append((s, target, inputs))
        return out
    if os.environ.get("MEDSCOPE_PREFETCH", "1") == "0" or not hasattr(policy, "encode_cpu"):
        for vi in range(start_view, len(order)):
            yield vi, build(vi)
        return
    q: queue.Queue = queue.Queue(maxsize=ahead)

    def producer():
        try:
            for vi in range(start_view, len(order)):
                item = (vi, build(vi))
                while not stop.is_set():
                    try:
                        q.put(item, timeout=1)
                        break
                    except queue.Full:
                        continue
                if stop.is_set():
                    return
            q.put(None)
        except BaseException as e:  # noqa: BLE001 - handed to the training loop, which raises it
            q.put(e)
    threading.Thread(target=producer, daemon=True).start()
    while True:
        item = q.get()
        if item is None:
            return
        if isinstance(item, BaseException):
            raise item
        yield item


def is_vision_param(name: str) -> bool:
    """Is this parameter part of the vision encoder or projector (or an adapter on them)?"""
    from medscope.train.hf_policy import VISION_MODULES
    return any(v in name for v in VISION_MODULES)


_BLOCK = None


def vision_depth(name: str) -> Optional[int]:
    """Block index of a vision-encoder parameter (`...visual.blocks.7....` -> 7), None if it is not in a numbered block."""
    import re
    global _BLOCK
    if _BLOCK is None:
        _BLOCK = re.compile(r"\.(?:blocks|layers|layer)\.(\d+)\.")
    m = _BLOCK.search(name)
    return int(m.group(1)) if m else None


def lr_scales(names: list[str], vision_lr_scale: float = 1.0, vision_layer_decay: float = 1.0) -> dict[str, float]:
    """Learning-rate scale per trainable parameter name.

    Language-model parameters: 1. Vision encoder and projector: `vision_lr_scale`, and with layer-wise decay
    (`vision_layer_decay` < 1) the top vision block gets `vision_lr_scale`, each block below it a further factor
    `vision_layer_decay`, the patch embedding (below block 0) one factor less again; the projector/merger and
    any other un-numbered vision parameter above the blocks keep `vision_lr_scale`. Low layers hold the generic
    features the pretrained encoder is good at, so they move least (layer-wise learning-rate decay)."""
    vis = [n for n in names if is_vision_param(n)]
    depths = [d for d in (vision_depth(n) for n in vis) if d is not None]
    top = max(depths) if depths else 0
    out = {}
    for n in names:
        if not is_vision_param(n):
            out[n] = 1.0
            continue
        if vision_layer_decay == 1.0:
            out[n] = vision_lr_scale
            continue
        d = vision_depth(n)
        if d is not None:
            out[n] = vision_lr_scale * vision_layer_decay ** (top - d)
        elif any(k in n for k in ("patch_embed", "embeddings", "pos_embed", "patch_embedding")):
            out[n] = vision_lr_scale * vision_layer_decay ** (top + 1)
        else:
            out[n] = vision_lr_scale
    return out


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
    replays: Optional[dict[str, list[str]]] = None,
    window_prob: float = 0.0,
    small_zoom: bool = False,
    schedule_steps: Optional[int] = None,
    vision_lr_scale: float = 1.0,
    vision_layer_decay: float = 1.0,
    sample_fn: Optional[Callable] = None,   # (view, seed, index) -> [SFTSample]; replaces the synthetic trajectories
) -> Path:
    import torch

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    views = mode_views(views, mode)
    order = view_order(views, epochs, seed)
    cfg = load_config() if replays else None
    total_steps = schedule_steps or max_steps or max(1, int(estimate_samples(views, mode) * epochs / grad_accum))

    model = policy.model
    model.train()
    named = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    params = [p for _, p in named]
    # one group per learning-rate scale: adapters on the vision encoder and projector can be trained more gently,
    # optionally with layer-wise decay (lower vision blocks slower)
    scales = lr_scales([n for n, _ in named], vision_lr_scale, vision_layer_decay)
    by_scale: dict[float, list] = {}
    for n, p in named:
        by_scale.setdefault(round(scales[n], 12), []).append(p)
    groups = [{"params": ps, "lr": lr * sc, "scale": sc} for sc, ps in sorted(by_scale.items(), reverse=True)]
    if vision_lr_scale != 1.0 or vision_layer_decay != 1.0:
        n_vis = sum(1 for n, _ in named if is_vision_param(n))
        assert n_vis, "--vision-lr-scale / --vision-layer-decay need an adapter that includes the vision encoder (--lora-vision)"
        log("learning rate: " + ", ".join(f"{len(g['params'])} tensors at {lr * g['scale']:.1e}" for g in groups)
            + f" ({len(named) - n_vis} language-model tensors at the full rate; {n_vis} vision tensors in "
            + f"{len(groups) - 1} slower groups)")
    opt = torch.optim.AdamW(groups, lr=lr, weight_decay=0.0)

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
            g["lr"] = lr_at(step, total_steps, lr) * g.get("scale", 1.0)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1

    micro, running, t0 = 0, [], time.time()
    save_due = False
    stop = threading.Event()
    for vi, prepared in prepared_views(policy, order, start_view, mode, seed, replays, cfg, window_prob, small_zoom,
                                       stop, sample_fn=sample_fn):
        for s, target, inputs in prepared:
            lp = policy.token_logprobs(s.messages, target, inputs=inputs) if inputs is not None \
                else policy.token_logprobs(s.messages, target)
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
    stop.set()
    if micro % grad_accum:
        optimizer_step()  # leftover gradients from the last partial batch

    policy.save_adapter(str(final))
    write_state(out, {"views_done": len(order), "opt_step": step, "mode": mode, "total_steps": total_steps,
                      "finished": True})
    log(f"saved final adapter to {final}")
    return final
