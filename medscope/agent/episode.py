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

    def transcript(self) -> list[dict]:
        """Text-only transcript for logging (images replaced by a placeholder)."""
        out = []
        for m in self.messages[1:]:  # skip system prompt
            parts = []
            for c in m["content"]:
                parts.append("[image]" if c["type"] == "image" else c["text"])
            out.append({"role": m["role"], "content": " ".join(parts)})
        return out


def run_episode(
    policy: Policy,
    view: View,
    cfg: dict,
    sample: bool = False,
    max_turns: Optional[int] = None,
    image: Optional[np.ndarray] = None,
    first_generation: Optional[Generation] = None,
) -> Episode:
    budget = cfg["tools"]["budget"]
    max_turns = max_turns or budget + 1
    img = image if image is not None else load_image(view.image_path)
    env = ToolEnv(img, budget=budget)
    messages = start_messages(img, view.question)
    turns: list[Turn] = []
    final: Optional[FinalAction] = None
    malformed, error = False, ""

    for turn_index in range(max_turns):
        if turn_index == 0 and first_generation is not None:
            gen = first_generation
        else:
            gen = policy.generate(messages, sample=sample)
        turns.append(Turn(len(messages), gen.text, gen.extra))
        messages.append(assistant_message(gen.text))
        parsed = parse(gen.text)
        if parsed.malformed:
            malformed, error = True, parsed.error
            break
        if parsed.final is not None:
            final = parsed.final
            break
        # keep only the action that ran: anything the model wrote after it (e.g. an answer
        # guessed before seeing the zoom) must not sit in the history it reads next turn
        messages[-1] = assistant_message(tool_text(parsed.tool))
        result = env.call(parsed.tool.name, parsed.tool.args)
        messages.append(tool_result_message(result))
    else:
        malformed, error = True, "no final action within the turn limit"

    outcome = score(view, final, cfg, tool_calls=env.calls, refused_calls=env.refused,
                    malformed=malformed or final is None)
    return Episode(view, messages, turns, final, malformed, error, env.calls, env.refused, outcome, env.log)


def run_group(policy: Policy, view: View, cfg: dict, n: int, sample: bool = True,
              image: Optional[np.ndarray] = None) -> list[Episode]:
    """n episodes on the same view. First turns are sampled in one batch when the
    policy supports it (most episodes end within one or two turns)."""
    img = image if image is not None else load_image(view.image_path)
    if hasattr(policy, "generate_n"):
        firsts = policy.generate_n(start_messages(img, view.question), n, sample=sample)
    else:
        firsts = [policy.generate(start_messages(img, view.question), sample=sample) for _ in range(n)]
    return [run_episode(policy, view, cfg, sample=sample, image=img, first_generation=g) for g in firsts]
