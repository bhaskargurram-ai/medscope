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

The trajectory term replays one of the three views per case (round-robin), so it costs a third of supervised training
on the same cases; the two candidate replies of a view are scored in one forward pass of batch 2.

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
TRAINER = "cmcc-v2"              # batched candidates, one-view replay, prefetch; state.json records it


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
    if start and state.get("trainer") != TRAINER:
        log(f"checkpoint from trainer {state.get('trainer', 'v1')!r} discarded; starting over with {TRAINER}")
        start, step = 0, 0
        (out / "train_log.jsonl").unlink(missing_ok=True)
    if start and checkpoint_path(out).exists():
        load_adapter_weights(model, checkpoint_path(out))
        load_optimizer(opt, out)
        log(f"resuming from case {start}, optimizer step {step}")

    def prepare(i: int):
        """Everything the CPU can do for case i: images, the trajectory replay for one view (round-robin over the
        three, so the replay costs a third of plain SFT on the same cases), the three single-turn prompts with their
        candidate replies, and the first-action prompts on the original and the control view."""
        t = order[i]
        views = (t.original, t.erased, t.control)
        imgs = [load_image(v.image_path) for v in views]
        replay_view = views[i % 3]
        kw = dict(window_prob=0.3, small_zoom=True) if replay_view is t.original else {}
        replay = [(policy.target_ids(smp.target), policy.encode_cpu(smp.messages))
                  for smp in samples_for(replay_view, "agentic", seed, i, **kw)]
        prompts = []
        for v, img in zip(views, imgs):
            present, absent = candidates(v)
            prompts.append((policy.encode_cpu(start_messages(img, v.question)), policy.target_ids(present), policy.target_ids(absent)))
        first = samples_for(t.original, "agentic", seed, i, window_prob=0.3, small_zoom=True)[0]
        act_inputs = []
        for img in (imgs[0], imgs[2]):
            msgs = list(first.messages)
            msgs[-1] = start_messages(img, t.original.question)[-1]
            act_inputs.append(policy.encode_cpu(msgs))
        return replay, prompts, (policy.target_ids(first.target), act_inputs)

    def prepared(start_i: int):
        import os, queue, threading
        if os.environ.get("MEDSCOPE_PREFETCH", "1") == "0":
            for i in range(start_i, len(order)):
                yield i, prepare(i)
            return
        q: queue.Queue = queue.Queue(maxsize=3)
        stop = threading.Event()

        def producer():
            try:
                for i in range(start_i, len(order)):
                    item = (i, prepare(i))
                    while not stop.is_set():
                        try:
                            q.put(item, timeout=1)
                            break
                        except queue.Full:
                            pass
                    if stop.is_set():
                        return
                q.put(None)
            except BaseException as e:          # surface the error in the training thread
                q.put(e)
        th = threading.Thread(target=producer, daemon=True)
        th.start()
        try:
            while True:
                item = q.get()
                if item is None:
                    return
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            stop.set()

    def optimizer_step():
        nonlocal step
        for g in opt.param_groups:
            g["lr"] = lr_at(step, total_steps, lr)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1

    running, t0 = {"sft": [], "did": [], "inv": [], "act": [], "s_o": [], "s_e": [], "s_c": []}, time.time()
    # Per case: ~1.6 trajectory passes (one view), 3 batch-of-2 log-odds passes, 2 first-action passes; each term is
    # backpropagated on its own (same gradient as the summed loss, smaller peak memory).
    for i, (replay, prompts, (act_target, act_inputs)) in prepared(start):
        # 1. trajectory replay on one view, as in supervised training
        sft_vals = []
        for target, inputs in replay:
            l = -policy.token_logprobs(None, target, inputs=inputs).mean()
            (l / (len(replay) * grad_accum)).backward()
            sft_vals.append(float(l))
        l_sft = float(np.mean(sft_vals))
        # 2. decision log-odds on the three views: present and absent reply in one pass each
        s = []
        for inputs, present, absent in prompts:
            lp_p, lp_a = policy.token_logprobs_pair(None, present, absent, inputs=inputs)
            s.append(lp_p.sum() - lp_a.sum())
        s_o, s_e, s_c = s
        did = torch.nn.functional.softplus(tau - (s_c - s_e))
        inv = (s_o - s_c) ** 2
        if l_did or l_inv:
            ((l_did * did + l_inv * inv) / grad_accum).backward()
        # 3. the first action of the original's trajectory must be as likely on the control view
        lp_o = policy.token_logprobs(None, act_target, inputs=act_inputs[0]).mean()
        lp_c = policy.token_logprobs(None, act_target, inputs=act_inputs[1]).mean()
        act = (lp_o - lp_c) ** 2
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
                write_state(out, {"cases_done": i + 1, "opt_step": step, "total_steps": total_steps, "trainer": TRAINER})
            if max_steps and step >= max_steps:
                break
    if (len(order) - start) % grad_accum and not (max_steps and step >= max_steps):
        optimizer_step()
    policy.save_adapter(str(final))
    write_state(out, {"cases_done": len(order), "opt_step": step, "total_steps": total_steps, "finished": True,
                      "trainer": TRAINER, "tau": tau, "l_did": l_did, "l_inv": l_inv, "l_act": l_act})
    log(f"saved final adapter to {final}")
    return final
