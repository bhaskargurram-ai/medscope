"""Control-matched counterfactual consistency (CMCC): the control edit as a constraint, not only as data.

Every training case has three views of one image: the original (lesion present), the erasure (lesion gone) and the
control edit (the same edit, same shape and tool, elsewhere; lesion intact). Supervised training sees them as three
independent samples; nothing stops a model from satisfying the labels by noticing that an image was edited. This
objective puts the three views in one loss:

  decision log-odds   s(x) = log p(present reply | x) - log p(absent reply | x), single turn, same wording
  lesion effect       s(O) - s(E)     should be large
  edit effect         s(O) - s(C)     should be zero

  L_did = softplus(tau - [(s(O) - s(E)) - (s(O) - s(C))]) = softplus(tau - (s(C) - s(E)))   difference in differences
  L_inv = (s(O) - s(C))^2                                                                   control invariance
  L_act = mean over tokens (log p(first action | O) - log p(first action | C))^2            the first tool action
          (where the agent looks) must not be drawn to the control patch
  L     = L_sft(trajectories of O, E, C) + l_did * L_did + l_inv * L_inv + l_act * L_act

The difference-in-differences term rewards only lesion-specific sensitivity: any drop that an edited image produces
regardless of where the edit is cancels out. The trajectory loss is the same as supervised training, so a run with
all three weights at zero is plain SFT on the same cases.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..agent.prompts import start_messages
from ..agent.trajectories import _final, absent_text
from ..data.schema import View, ViewKind
from ..data.views import load_image
from .common import append_log, checkpoint_path, load_adapter_weights, load_optimizer, lr_at, read_state, save_optimizer, write_state
from .sft import samples_for

PREFIX = "From the image:"      # one neutral lead-in for both candidate replies, so only the decision differs


@dataclass
class Triplet:
    case_id: str
    original: View
    erased: View
    control: View


def build_triplets(views: list[View]) -> list[Triplet]:
    """Cases that have all three views and a yes/no-style question (the absent reply must be derivable)."""
    by: dict[str, dict[str, View]] = {}
    for v in views:
        if v.kind in (ViewKind.ORIGINAL, ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL):
            by.setdefault(v.case_id, {})[v.kind.value] = v
    out = []
    for cid, d in sorted(by.items()):
        if len(d) == 3 and d["original"].lesion_box is not None:
            o = d["original"]
            if absent_text(o) == "No abnormality" and o.answer.strip().lower() not in ("yes", "no"):
                continue                                           # open question: no clean present/absent pair
            out.append(Triplet(cid, o, d["target_removal"], d["random_removal"]))
    return out


def candidates(view: View) -> tuple[str, str]:
    """The 'present' and 'absent' final replies for this case, in the agent's format."""
    present = f"{PREFIX} {_final(action='answer', answer=view.answer, box=view.lesion_box, confidence=0.85)}"
    absent = f"{PREFIX} {_final(action='answer', answer=absent_text(view), confidence=0.85)}"
    return present, absent


def train_cmcc(policy, triplets: list[Triplet], out_dir: str | Path, lr: float = 2e-5, grad_accum: int = 8,
               tau: float = 2.0, l_did: float = 0.5, l_inv: float = 0.5, l_act: float = 0.5, seed: int = 0,
               save_every: int = 50, max_steps: Optional[int] = None, log: Callable[[str], None] = print) -> Path:
    import torch
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = policy.model
    state = read_state(out)
    final = out / "final"
    if state.get("finished") and final.exists():
        log(f"already finished; final adapter is at {final}")
        return final
    rng = np.random.default_rng(seed)
    order = [triplets[i] for i in rng.permutation(len(triplets))]
    total_steps = max_steps or max(1, len(order) // grad_accum)
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    start, step = state.get("cases_done", 0), state.get("opt_step", 0)
    if start and checkpoint_path(out).exists():
        load_adapter_weights(model, checkpoint_path(out))
        load_optimizer(opt, out)
        log(f"resuming from case {start}, optimizer step {step}")

    def logodds(view: View, img):
        """s(x) and the two candidate log-probs, single-turn prompt."""
        msgs = start_messages(img, view.question)
        inputs = policy.encode_cpu(msgs)
        present, absent = candidates(view)
        lp_p = policy.token_logprobs(msgs, policy.target_ids(present), inputs=inputs).sum()
        lp_a = policy.token_logprobs(msgs, policy.target_ids(absent), inputs=inputs).sum()
        return lp_p - lp_a

    def first_action_logp(view: View, img, sample):
        """Mean token log-prob of the trajectory's first turn (the tool call, or the direct answer) given `img`."""
        msgs = [m for m in sample.messages]
        msgs[-1] = start_messages(img, view.question)[-1]        # same conversation, this image
        return policy.token_logprobs(msgs, policy.target_ids(sample.target)).mean()

    def optimizer_step():
        nonlocal step
        for g in opt.param_groups:
            g["lr"] = lr_at(step, total_steps, lr)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1

    running, t0 = {"sft": [], "did": [], "inv": [], "act": [], "s_o": [], "s_e": [], "s_c": []}, time.time()
    for i in range(start, len(order)):
        t = order[i]
        imgs = {k: load_image(v.image_path) for k, v in (("o", t.original), ("e", t.erased), ("c", t.control))}
        # The three terms are backpropagated separately (same gradient, smaller peak memory): the trajectory
        # samples one at a time, then the six log-odds passes together, then the two first-action passes.
        # 1. trajectory loss on the three views, as in supervised training (same jitter rules)
        samples_o = samples_for(t.original, "agentic", seed, i, window_prob=0.3, small_zoom=True)
        all_samples = samples_o + samples_for(t.erased, "agentic", seed, i) + samples_for(t.control, "agentic", seed, i)
        sft_vals = []
        for s in all_samples:
            lp = policy.token_logprobs(s.messages, policy.target_ids(s.target))
            l = -lp.mean()
            (l / (len(all_samples) * grad_accum)).backward()
            sft_vals.append(float(l))
        l_sft = float(np.mean(sft_vals))
        # 2. decision log-odds on the three views
        s_o, s_e, s_c = logodds(t.original, imgs["o"]), logodds(t.erased, imgs["e"]), logodds(t.control, imgs["c"])
        did = torch.nn.functional.softplus(tau - (s_c - s_e))
        inv = (s_o - s_c) ** 2
        if l_did or l_inv:
            ((l_did * did + l_inv * inv) / grad_accum).backward()
        # 3. the first action of the original's trajectory must be as likely on the control view
        first = samples_o[0]
        act = (first_action_logp(t.original, imgs["o"], first) - first_action_logp(t.control, imgs["c"], first)) ** 2
        if l_act:
            (l_act * act / grad_accum).backward()
        for k, v in (("sft", l_sft), ("did", did), ("inv", inv), ("act", act), ("s_o", s_o), ("s_e", s_e), ("s_c", s_c)):
            running[k].append(float(v))
        if (i + 1 - start) % grad_accum == 0:
            optimizer_step()
            if step % 10 == 0:
                rec = {"step": step, **{k: float(np.mean(v)) for k, v in running.items()}, "lr": opt.param_groups[0]["lr"],
                       "cases_done": i + 1, "secs": round(time.time() - t0)}
                append_log(out, rec)
                log(f"step {step}/{total_steps} sft {rec['sft']:.3f} did {rec['did']:.3f} inv {rec['inv']:.3f} act {rec['act']:.3f} "
                    f"| s(O) {rec['s_o']:.1f} s(E) {rec['s_e']:.1f} s(C) {rec['s_c']:.1f} ({i + 1}/{len(order)} cases)")
                running = {k: [] for k in running}
            if step % save_every == 0:
                policy.save_adapter(str(checkpoint_path(out)))
                save_optimizer(opt, out)
                write_state(out, {"cases_done": i + 1, "opt_step": step, "total_steps": total_steps})
            if max_steps and step >= max_steps:
                break
    if (len(order) - start) % grad_accum and not (max_steps and step >= max_steps):
        optimizer_step()
    policy.save_adapter(str(final))
    write_state(out, {"cases_done": len(order), "opt_step": step, "total_steps": total_steps, "finished": True,
                      "tau": tau, "l_did": l_did, "l_inv": l_inv, "l_act": l_act})
    log(f"saved final adapter to {final}")
    return final
