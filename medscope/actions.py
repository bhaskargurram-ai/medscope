"""Parse model output into tool calls and final actions.

Protocol (one tagged JSON object per turn, after any free-text reasoning):
    <tool>{"name": "zoom", "box": [x1, y1, x2, y2]}</tool>
    <final>{"action": "answer", "answer": "...", "box": [...], "confidence": 0.8}</final>
    <final>{"action": "clarify", "question": "..."}</final>
    <final>{"action": "refer", "reason": "..."}</final>
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from .data.schema import ActionKind, Box

_TAG = re.compile(r"<(tool|final)>\s*(\{.*?\})\s*</\1>", re.DOTALL)


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class FinalAction:
    kind: ActionKind
    answer: Optional[str] = None
    box: Optional[Box] = None
    confidence: Optional[float] = None
    text: Optional[str] = None  # clarify question or referral reason


@dataclass
class Parsed:
    tool: Optional[ToolCall] = None
    final: Optional[FinalAction] = None
    malformed: bool = False
    error: str = ""


def _valid_box(box) -> Optional[Box]:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        b = [int(round(float(v))) for v in box]
    except (TypeError, ValueError):
        return None
    if not all(0 <= v <= 1000 for v in b) or b[2] <= b[0] or b[3] <= b[1]:
        return None
    return b


def parse(text: str) -> Parsed:
    """Use the LAST tagged object in the text; anything else is malformed."""
    matches = _TAG.findall(text)
    if not matches:
        return Parsed(malformed=True, error="no <tool> or <final> tag")
    tag, raw = matches[-1]
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return Parsed(malformed=True, error=f"bad JSON: {exc}")
    if not isinstance(obj, dict):
        return Parsed(malformed=True, error="tag content is not an object")

    if tag == "tool":
        name = obj.get("name")
        if not isinstance(name, str):
            return Parsed(malformed=True, error="tool call without a name")
        args = {k: v for k, v in obj.items() if k != "name"}
        if name == "zoom":
            box = _valid_box(args.get("box"))
            if box is None:
                return Parsed(malformed=True, error="zoom needs a valid 0-1000 box")
            args["box"] = box
        return Parsed(tool=ToolCall(name, args))

    action = str(obj.get("action", "")).lower().strip()
    if action == "abstain":
        action = "refer"
    if action not in {a.value for a in ActionKind}:
        return Parsed(malformed=True, error=f"unknown action {action!r}")
    kind = ActionKind(action)

    conf = obj.get("confidence")
    try:
        conf = None if conf is None else min(1.0, max(0.0, float(conf)))
    except (TypeError, ValueError):
        conf = None

    if kind is ActionKind.ANSWER:
        ans = obj.get("answer")
        if not isinstance(ans, str) or not ans.strip():
            return Parsed(malformed=True, error="answer action without an answer")
        return Parsed(final=FinalAction(kind, answer=ans, box=_valid_box(obj.get("box")), confidence=conf))
    text_field = obj.get("question") if kind is ActionKind.CLARIFY else obj.get("reason")
    return Parsed(final=FinalAction(kind, confidence=conf, text=text_field if isinstance(text_field, str) else None))


def normalise_answer(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def answer_matches(pred: Optional[str], gold: str, aliases: list[str] | None = None) -> bool:
    if pred is None:
        return False
    p = normalise_answer(pred)
    return any(p == normalise_answer(g) for g in [gold, *(aliases or [])])
