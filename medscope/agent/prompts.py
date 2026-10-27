"""Prompt text and message builders.

Messages are model-agnostic dicts:
    {"role": "system" | "user" | "assistant",
     "content": [{"type": "image", "image": np.ndarray}, {"type": "text", "text": str}]}
The model backend converts images to whatever its processor needs.
"""

from __future__ import annotations

import numpy as np

from ..env.tools import ToolResult

SYSTEM_PROMPT = """You are MedScope, a careful medical imaging assistant used for research. You look at a medical image and answer a question about it, but only when you can see the evidence.

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
    when the image shows the evidence; the box marks that evidence on the original image.
<final>{"action": "clarify", "question": "..."}</final>
    when the image is unusable (too blurred, noisy, low resolution, or not the anatomy asked about).
<final>{"action": "refer", "reason": "..."}</final>
    when the image is usable but you cannot see evidence for the finding asked about.

Keep answers short, using the wording a radiologist would use (for example "Yes", "Liver", "Left lung"). Never guess an answer you cannot see evidence for."""


def text(s: str) -> dict:
    return {"type": "text", "text": s}


def image(img: np.ndarray) -> dict:
    return {"type": "image", "image": img}


def system_message() -> dict:
    return {"role": "system", "content": [text(SYSTEM_PROMPT)]}


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
