"""Synthetic supervised trajectories built from view labels (no teacher model needed).

For every view we know the correct final action and, for answerable views, where
the evidence is. That is enough to write correct multi-turn examples:

  original / random_removal  ->  (sometimes) zoom on the evidence, then answer with its box
  target_removal             ->  (sometimes) zoom on the region, then say the finding is absent
  degraded                   ->  clarify, with a reason that matches the degradation

Each trajectory becomes one SFT sample per assistant turn: the context the model
would have seen, and the exact text it should produce.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from ..actions import ToolCall, absent_reply, tool_text
from ..data.schema import Box, View, ViewKind
from ..data.views import load_image
from ..env.tools import ToolEnv
from .prompts import assistant_message, start_messages, tool_result_message

LOOK_CLOSER = [
    "I should look more closely at the relevant region before deciding.",
    "Let me zoom in on the area that matters for this question.",
    "A closer look at this region will show whether the finding is there.",
]
SEE_EVIDENCE = [
    "The finding is clearly visible here.",
    "The zoomed view shows the abnormality.",
    "I can see the evidence for this in the image.",
]
NO_EVIDENCE = [
    "The image is of good quality and there is no sign of the finding asked about.",
    "I looked at the relevant area and there is no visible abnormality.",
    "Nothing in this image shows the finding, so it is not present.",
]


def absent_text(view: View) -> str:
    """The answer that says the finding is not there, phrased for this question."""
    return absent_reply(view.question, view.answer) or "No abnormality"
CLARIFY = {
    "blur": ("The image is too blurred to assess fine detail.",
             "Could you provide a sharper image of this region?"),
    "noise": ("The image is too noisy to assess reliably.",
              "Could you provide a less noisy acquisition of this image?"),
    "lowres": ("The image resolution is too low to assess this.",
               "Could you provide a higher-resolution image?"),
    "mismatch": ("This image does not seem to show the anatomy the question is about.",
                 "Could you confirm this is the correct image for the question?"),
}


def pad_box(box: Box, scale: float = 0.5, min_size: int = 150) -> Box:
    """Grow a box by `scale` of its size on each side (at least min_size wide/tall), clamped to 0-1000."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    px, py = max(w * scale, (min_size - w) / 2, 0), max(h * scale, (min_size - h) / 2, 0)
    nx1, ny1 = int(max(0, x1 - px)), int(max(0, y1 - py))
    nx2, ny2 = int(min(1000, x2 + px)), int(min(1000, y2 + py))
    return [nx1, ny1, nx2, ny2]


def _tool(name: str, **args) -> str:
    return f"<tool>{json.dumps({'name': name, **args})}</tool>"


def _final(**obj) -> str:
    return f"<final>{json.dumps(obj)}</final>"


@dataclass
class SFTSample:
    messages: list[dict]   # context the model sees
    target: str            # text it should produce
    view_id: str
    kind: str


def build_trajectory(view: View, rng: np.random.Generator, zoom_prob: float = 0.6,
                     direct_only: bool = False, image: np.ndarray | None = None) -> list[SFTSample]:
    """One correct trajectory for `view`, split into per-turn samples.

    direct_only=True gives single-turn samples without tools (used for the
    grounding-only adapter).
    """
    img = image if image is not None else load_image(view.image_path)
    messages = start_messages(img, view.question)
    samples: list[SFTSample] = []
    env = ToolEnv(img)

    def emit(text: str) -> None:
        samples.append(SFTSample(list(messages), text, view.view_id, view.kind.value))
        messages.append(assistant_message(text))

    pick = lambda opts: opts[int(rng.integers(len(opts)))]  # noqa: E731


    if view.kind is ViewKind.DEGRADED:
        reason, question = CLARIFY.get(view.meta.get("degradation", "blur"), CLARIFY["blur"])
        emit(f"{reason} {_final(action='clarify', question=question)}")
        return samples

    zoom = (not direct_only) and view.lesion_box is not None and rng.random() < zoom_prob
    if zoom:
        region = pad_box(view.lesion_box)
        emit(f"{pick(LOOK_CLOSER)} {_tool('zoom', box=region)}")
        messages[-1] = assistant_message(tool_text(ToolCall("zoom", {"box": region})))  # as run_episode keeps it
        messages.append(tool_result_message(env.call("zoom", {"box": region})))

    if view.kind in (ViewKind.TARGET_REMOVAL, ViewKind.NATURAL_NEGATIVE):
        # lesion-removed and natural negative images get the same reply: the finding isn't there
        answer = view.answer if view.kind is ViewKind.NATURAL_NEGATIVE else absent_text(view)
        conf = round(float(rng.uniform(0.75, 0.95)), 2)
        emit(f"{pick(NO_EVIDENCE)} {_final(action='answer', answer=answer, confidence=conf)}")
    else:
        conf = round(float(rng.uniform(0.75, 0.95)), 2)
        emit(f"{pick(SEE_EVIDENCE)} {_final(action='answer', answer=view.answer, box=view.lesion_box, confidence=conf)}")
    return samples


class _Replay:
    """Policy stand-in that replays recorded assistant turns."""

    def __init__(self, texts: list[str]):
        self.texts = list(texts)

    def generate(self, messages, sample=False):
        from .episode import Generation
        return Generation(self.texts.pop(0) if self.texts else "")


def replay_samples(view: View, texts: list[str], cfg: dict, image: np.ndarray | None = None) -> list[SFTSample]:
    """SFT samples from a recorded episode (rejection sampling): replay the model's own turns
    through the environment so every turn gets exactly the context the model saw."""
    from .episode import run_episode
    ep = run_episode(_Replay(texts), view, cfg, image=image)
    return [SFTSample(ep.messages[:t.context_len], t.text, view.view_id, view.kind.value) for t in ep.turns]
