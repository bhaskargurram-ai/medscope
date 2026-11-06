"""Removal-based preference training (DPO on erased-lesion pairs): the closest established method, as a baseline.

Object-removal preference methods (oDPO and relatives) teach a vision-language model not to describe what is not
there by pairing, for an image with the object removed, a response that still mentions the object (rejected) with
one that does not (chosen), and training with direct preference optimisation. Adapted here to the same medical
cases, base model and answer format as MedScope:

  lesion erased (target_removal)   chosen: "the finding is absent"      rejected: the lesion claimed, with the box
                                   it had before erasure
  unedited lesion (original)       chosen: the answer with its box       rejected: "the finding is absent"
  lesion-free image (natural_negative, yes/no questions)
                                   chosen: "No"                          rejected: "Yes"

No control edits (random_removal), no degraded views and no tool turns: one prompt, two single-turn replies. The
reference policy is the adapter the run starts from (--init), or the base model when there is none. Reference
log-probabilities are computed once in a first pass and cached, so a resumed run never recomputes them. Loss is the
standard sigmoid DPO loss on summed response log-probabilities with temperature beta.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..actions import absent_reply, normalise_answer
from ..agent.prompts import start_messages
from ..agent.trajectories import NO_EVIDENCE, SEE_EVIDENCE, _final, absent_text
from ..data.schema import View, ViewKind
from ..data.views import load_image
from .common import append_log, checkpoint_path, load_adapter_weights, load_optimizer, lr_at, read_state, save_optimizer, write_state

PAIR_KINDS = ("original", "target_removal", "natural_negative")


@dataclass
class Pair:
    view_id: str
    kind: str
    image_path: str
    question: str
    chosen: str
    rejected: str


def build_pairs(views: list[View], seed: int = 0) -> list[Pair]:
    """One (chosen, rejected) pair per usable view. A lesion-erased view carries the case's original answer (the
    finding is present) and its lesion box, as every view of a case does; the absent reply is derived from it."""
    rng = np.random.default_rng(seed)
    pick = lambda opts: opts[int(rng.integers(len(opts)))]  # noqa: E731
    out = []
    for v in views:
        if v.kind.value not in PAIR_KINDS:
            continue
        conf = lambda: round(float(rng.uniform(0.75, 0.95)), 2)  # noqa: E731
        if v.kind is ViewKind.ORIGINAL:
            if v.lesion_box is None or absent_reply(v.question, v.answer) is None:
                continue
            chosen = f"{pick(SEE_EVIDENCE)} {_final(action='answer', answer=v.answer, box=v.lesion_box, confidence=conf())}"
            rejected = f"{pick(NO_EVIDENCE)} {_final(action='answer', answer=absent_text(v), confidence=conf())}"
        elif v.kind is ViewKind.TARGET_REMOVAL:
            if v.lesion_box is None or absent_reply(v.question, v.answer) is None:
                continue
            chosen = f"{pick(NO_EVIDENCE)} {_final(action='answer', answer=absent_text(v), confidence=conf())}"
            rejected = f"{pick(SEE_EVIDENCE)} {_final(action='answer', answer=v.answer, box=v.lesion_box, confidence=conf())}"
        else:                                                   # natural negative, yes/no questions only
            if normalise_answer(v.answer) != "no":
                continue
            chosen = f"{pick(NO_EVIDENCE)} {_final(action='answer', answer=v.answer, confidence=conf())}"
            rejected = f"{pick(SEE_EVIDENCE)} {_final(action='answer', answer='Yes', confidence=conf())}"
        out.append(Pair(v.view_id, v.kind.value, v.image_path, v.question, chosen, rejected))
    return out


def pair_order(pairs: list[Pair], n: Optional[int], seed: int) -> list[Pair]:
    """A fixed shuffle, cut to n pairs; the same share of every kind."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(pairs))
    if n and n < len(pairs):
        by_kind: dict[str, list[int]] = {}
        for i in idx:
            by_kind.setdefault(pairs[i].kind, []).append(int(i))
        share = n / len(pairs)
        keep = sorted(j for k, js in by_kind.items() for j in js[:round(share * len(js))])
        idx = rng.permutation(keep)
    return [pairs[int(i)] for i in idx]


def dpo_loss(torch, pc, pr, rc, rr, beta: float):
    """Sigmoid DPO loss from policy (pc, pr) and reference (rc, rr) summed log-probs of chosen and rejected."""
    margin = beta * ((pc - rc) - (pr - rr))
    return -torch.nn.functional.logsigmoid(margin), margin


def train_dpo(policy, pairs: list[Pair], out_dir: str | Path, reference: Optional[str] = None, beta: float = 0.1,
              lr: float = 2e-5, grad_accum: int = 8, max_steps: Optional[int] = None, save_every: int = 50,
              seed: int = 0, log: Callable[[str], None] = print) -> Path:
    """`reference`: adapter path the run started from (its log-probs are the reference); None = the base model."""
    import torch

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = policy.model
    state = read_state(out)
    final = out / "final"
    if state.get("finished") and final.exists():
        log(f"already finished; final adapter is at {final}")
        return final
    total_steps = max_steps or max(1, len(pairs) // grad_accum)

    def logps(pair: Pair):
        img = load_image(pair.image_path)
        messages = start_messages(img, pair.question)
        inputs = policy.encode_cpu(messages)
        pc = policy.token_logprobs(messages, policy.target_ids(pair.chosen), inputs=inputs).sum()
        pr = policy.token_logprobs(messages, policy.target_ids(pair.rejected), inputs=inputs).sum()
        return pc, pr

    # pass 1: reference log-probs, cached (resumable)
    ref_file = out / "reference_logps.json"
    ref = json.loads(ref_file.read_text()) if ref_file.exists() else {}
    todo = [p for p in pairs if p.view_id not in ref]
    if todo:
        log(f"reference pass: {len(todo)} of {len(pairs)} pairs")
        model.eval()
        if reference:
            model.load_adapter(reference, adapter_name="ref")
            model.set_adapter("ref")
        ctx = torch.no_grad() if reference else model.disable_adapter()
        with ctx, torch.no_grad():
            for i, p in enumerate(todo):
                pc, pr = logps(p)
                ref[p.view_id] = [float(pc), float(pr)]
                if (i + 1) % 100 == 0:
                    ref_file.write_text(json.dumps(ref))
                    log(f"  reference {i + 1}/{len(todo)}")
        ref_file.write_text(json.dumps(ref))
        if reference:
            model.set_adapter("default")
    model.train()
    params = [p for n, p in model.named_parameters() if p.requires_grad and ".ref." not in n]
    for n, p in model.named_parameters():
        if ".ref." in n:
            p.requires_grad_(False)
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    start, step = state.get("pairs_done", 0), state.get("opt_step", 0)
    if start and checkpoint_path(out).exists():
        load_adapter_weights(model, checkpoint_path(out))
        load_optimizer(opt, out)
        log(f"resuming from pair {start}, optimizer step {step}")

    def optimizer_step() -> None:
        nonlocal step
        for g in opt.param_groups:
            g["lr"] = lr_at(step, total_steps, lr)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1

    running, margins, t0 = [], [], time.time()
    for i in range(start, len(pairs)):
        p = pairs[i]
        pc, pr = logps(p)
        rc, rr = ref[p.view_id]
        loss, margin = dpo_loss(torch, pc, pr, rc, rr, beta)
        (loss / grad_accum).backward()
        running.append(float(loss))
        margins.append(float(margin))
        if (i + 1 - start) % grad_accum == 0:
            optimizer_step()
            if step % 10 == 0:
                rec = {"step": step, "loss": float(np.mean(running)), "margin": float(np.mean(margins)),
                       "accuracy": float(np.mean([m > 0 for m in margins])), "lr": opt.param_groups[0]["lr"],
                       "pairs_done": i + 1, "secs": round(time.time() - t0)}
                append_log(out, rec)
                log(f"step {step}/{total_steps} loss {rec['loss']:.4f} margin {rec['margin']:.2f} "
                    f"pref-acc {rec['accuracy']:.0%} ({i + 1}/{len(pairs)} pairs)")
                running, margins = [], []
            if step % save_every == 0:
                policy.save_adapter(str(checkpoint_path(out)))
                save_optimizer(opt, out)
                write_state(out, {"pairs_done": i + 1, "opt_step": step, "total_steps": total_steps, "beta": beta})
            if max_steps and step >= max_steps:
                break
    if (len(pairs) - start) % grad_accum and not (max_steps and step >= max_steps):
        optimizer_step()
    policy.save_adapter(str(final))
    write_state(out, {"pairs_done": len(pairs), "opt_step": step, "total_steps": total_steps, "beta": beta,
                      "reference": reference, "finished": True})
    log(f"saved final adapter to {final}")
    return final
