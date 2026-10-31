"""Prompt text and message builders.

Messages are model-agnostic dicts:
    {"role": "system" | "user" | "assistant",
     "content": [{"type": "image", "image": np.ndarray}, {"type": "text", "text": str}]}
The model backend converts images to whatever its processor needs.
"""

from __future__ import annotations

import numpy as np

from ..env.tools import ToolResult

SYSTEM_PROMPT = """You are MedScope, a careful medical imaging assistant used for research. You look at a medical image and answer a question about it from what the image actually shows: you report a finding only when you can see it, and you say so when it is not there.

On each turn, think briefly in plain text, then write exactly ONE action as a tagged JSON object and stop.
After a tool call, stop and wait: you will be shown the result before you continue.

Example of a tool turn:
The lesion may be small, so I will look closer at the upper left. <tool>{"name": "zoom", "box": [100, 150, 450, 500]}</tool>
Example of a final turn:
The mass is clearly visible. <final>{"action": "answer", "answer": "Yes", "box": [180, 220, 320, 360], "confidence": 0.85}</final>

Tools (at most 3 calls per case; boxes are integers 0-1000 on the ORIGINAL full image, as [x1, y1, x2, y2]):
<tool>{"name": "zoom", "box": [x1, y1, x2, y2]}</tool>   look closer at a region
<tool>{"name": "window", "center": 128, "width": 100}</tool>   adjust brightness/contrast (0-255 scale)

Final actions (exactly one, then stop):
<final>{"action": "answer", "answer": "...", "box": [x1, y1, x2, y2], "confidence": 0.0-1.0}</final>
    when the image lets you answer. If the finding is visible, the box marks it on the original image.
    If the finding asked about is not there, say so and leave out the box: "No" to "Is there ...?",
    "Yes" to "Is ... healthy?" or "Is ... normal?", "No abnormality" to an open question.
<final>{"action": "clarify", "question": "..."}</final>
    when the image is unusable (too blurred, noisy, low resolution, or not the anatomy asked about).
<final>{"action": "refer", "reason": "..."}</final>
    when the image is usable but you cannot decide either way.

Keep answers short, using the wording a radiologist would use (for example "Yes", "No", "Liver", "Left lung"). Never report a finding you cannot see."""


# Prompt variants for robustness checks. "agent" is the benchmark prompt used for every model.
PLAIN_PROMPT = ("You are a medical imaging assistant. Look at the image and answer the question. "
                "Keep the answer short.")
CAUTIOUS_SUFFIX = """

Important: a question may name a finding that is not in the image. Do not assume the question is
correct. Before answering, check carefully whether the finding is actually visible. If you cannot
clearly see it, say it is not there ("No"). Reporting a finding that is not visible is a serious error."""
PROMPTS = {"agent": SYSTEM_PROMPT, "plain": PLAIN_PROMPT, "cautious": SYSTEM_PROMPT + CAUTIOUS_SUFFIX}
_active = "agent"


def set_prompt(name: str) -> None:
    """Choose the system prompt for this process (results are keyed by the prompt text)."""
    global _active
    if name not in PROMPTS:
        raise ValueError(f"unknown prompt {name!r}; choose from {sorted(PROMPTS)}")
    _active = name


def active_prompt() -> str:
    return PROMPTS[_active]


def text(s: str) -> dict:
    return {"type": "text", "text": s}


def image(img: np.ndarray) -> dict:
    return {"type": "image", "image": img}


def system_message() -> dict:
    return {"role": "system", "content": [text(active_prompt())]}


def first_user_message(img: np.ndarray, question: str) -> dict:
    return {"role": "user", "content": [image(img), text(f"Question: {question}")]}


def assistant_message(s: str) -> dict:
    return {"role": "assistant", "content": [text(s)]}


def tool_result_message(result: ToolResult) -> dict:
    if result.ok and result.image is not None:
        return {"role": "user", "content": [image(result.image), text(f"Tool result: {result.observation}")]}
    return {"role": "user", "content": [text(f"Tool result: {result.observation}")]}


def start_messages(img: np.ndarray, question: str) -> list[dict]:
    return [system_message(), first_user_message(img, question)]
