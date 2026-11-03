"""Run one agent episode: the model alternates between thinking, tool calls and a final action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import numpy as np

from ..actions import FinalAction, parse, tool_text
from ..data.schema import View
from ..data.views import load_image
from ..env.tools import ToolEnv
from ..rewards import Outcome, score
from .prompts import assistant_message, start_messages, tool_result_message


@dataclass
class Generation:
    text: str
    extra: Any = None  # backend data, e.g. prompt inputs and generated token ids for RL


class Policy(Protocol):
    def generate(self, messages: list[dict], sample: bool = False) -> Generation: ...


@dataclass
class Turn:
    context_len: int        # number of messages the model saw before producing this turn
    text: str
    extra: Any = None


@dataclass
class Episode:
    view: View
    messages: list[dict]
    turns: list[Turn]
    final: Optional[FinalAction]
    malformed: bool
    error: str
    tool_calls: int
    refused_calls: int
    outcome: Outcome
    tool_log: list[dict] = field(default_factory=list)
    n_prefix: int = 1       # system prompt plus any few-shot example turns, before the case

    def transcript(self) -> list[dict]:
        """Text-only transcript for logging (images replaced by a placeholder); starts at the case,
        so few-shot examples never appear in it."""
        out = []
        for m in self.messages[self.n_prefix:]:
            parts = []
            for c in m["content"]:
                parts.append("[image]" if c["type"] == "image" else c["text"])
            out.append({"role": m["role"], "content": " ".join(parts)})
        return out


class _State:
    """One episode in progress."""

    def __init__(self, view: View, img: np.ndarray, budget: int):
        self.view, self.img = view, img
        self.env = ToolEnv(img, budget=budget)
        self.messages = start_messages(img, view.question)
        self.n_prefix = len(self.messages) - 1
        self.turns: list[Turn] = []
        self.final: Optional[FinalAction] = None
        self.malformed, self.error, self.done = False, "", False

    def step(self, gen: Generation) -> None:
        """Apply one model turn: a final action ends the episode, a tool call runs."""
        self.turns.append(Turn(len(self.messages), gen.text, gen.extra))
        self.messages.append(assistant_message(gen.text))
        if gen.text.startswith("[API error:"):      # a failed request is never read as the model's answer
            self.malformed, self.error, self.done = True, "API error", True
            return
        parsed = parse(gen.text)
        if parsed.malformed:
            self.malformed, self.error, self.done = True, parsed.error, True
            return
        if parsed.final is not None:
            self.final, self.done = parsed.final, True
            return
        # keep only the action that ran: anything the model wrote after it (e.g. an answer
        # guessed before seeing the zoom) must not sit in the history it reads next turn
        self.messages[-1] = assistant_message(tool_text(parsed.tool))
        result = self.env.call(parsed.tool.name, parsed.tool.args)
        self.messages.append(tool_result_message(result))

    def finish(self, cfg: dict) -> Episode:
        if not self.done:
            self.malformed, self.error = True, "no final action within the turn limit"
        outcome = score(self.view, self.final, cfg, tool_calls=self.env.calls, refused_calls=self.env.refused,
                        malformed=self.malformed or self.final is None)
        if outcome.action == "answer" and self.turns and isinstance(self.turns[-1].extra, dict):
            outcome.answer_prob = self.turns[-1].extra.get("answer_prob")
        return Episode(self.view, self.messages, self.turns, self.final, self.malformed, self.error,
                       self.env.calls, self.env.refused, outcome, self.env.log, self.n_prefix)


def generate_many(policy: Policy, conversations: list[list[dict]], sample: bool) -> list[Generation]:
    """One turn for several conversations, in a single batch when the policy supports it."""
    if len(conversations) > 1 and hasattr(policy, "generate_batch"):
        return policy.generate_batch(conversations, sample=sample)
    return [policy.generate(m, sample=sample) for m in conversations]


def run_episodes(
    policy: Policy,
    views: list[View],
    cfg: dict,
    sample: bool = False,
    images: Optional[list[np.ndarray]] = None,
    first_generations: Optional[list[Generation]] = None,
    max_turns: Optional[int] = None,
) -> list[Episode]:
    """Several episodes advanced in lockstep: every round, all unfinished episodes get their
    next turn in one batch. Each episode sees exactly what it would see if run alone."""
    budget = cfg["tools"]["budget"]
    # with tools switched off (budget 0) a refused call still leaves one turn to answer
    max_turns = max_turns or cfg["tools"].get("max_turns") or budget + 1
    imgs = images if images is not None else [load_image(v.image_path) for v in views]
    states = [_State(v, im, budget) for v, im in zip(views, imgs)]
    for turn_index in range(max_turns):
        active = [st for st in states if not st.done]
        if not active:
            break
        if turn_index == 0 and first_generations is not None:
            gens = first_generations
        else:
            gens = generate_many(policy, [st.messages for st in active], sample)
        for st, g in zip(active, gens):
            st.step(g)
    return [st.finish(cfg) for st in states]


def run_episode(
    policy: Policy,
    view: View,
    cfg: dict,
    sample: bool = False,
    max_turns: Optional[int] = None,
    image: Optional[np.ndarray] = None,
    first_generation: Optional[Generation] = None,
) -> Episode:
    return run_episodes(policy, [view], cfg, sample=sample, images=None if image is None else [image],
                        first_generations=None if first_generation is None else [first_generation],
                        max_turns=max_turns)[0]


def run_group(policy: Policy, view: View, cfg: dict, n: int, sample: bool = True,
              image: Optional[np.ndarray] = None) -> list[Episode]:
    """n episodes on the same view. First turns are sampled in one batch when the
    policy supports it (most episodes end within one or two turns)."""
    img = image if image is not None else load_image(view.image_path)
    if hasattr(policy, "generate_n"):
        firsts = policy.generate_n(start_messages(img, view.question), n, sample=sample)
    else:
        firsts = [policy.generate(start_messages(img, view.question), sample=sample) for _ in range(n)]
    return run_episodes(policy, [view] * n, cfg, sample=sample, images=[img] * n, first_generations=firsts)
