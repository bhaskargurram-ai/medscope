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


_THINK_END = ("</think>", "<unused95>")          # Qwen-style and Gemma/MedGemma-style thinking
_THINK_START = ("<think>", "<unused94>")
_SPECIAL = re.compile(r"<unused\d+>|<think>|</think>")
_OPEN = re.compile(r"<(tool|final|answer|clarify|refer|abstain)>")
_ACTION_TAGS = {"answer", "clarify", "refer", "abstain"}  # e.g. MedGemma's <clarify>{"question": ...}</clarify>
_TOOL_NAMES = {"zoom", "window"}


def strip_thinking(text: str) -> tuple[str, bool]:
    """(text after any thinking block, True if the thinking never finished)."""
    for end in _THINK_END:
        if end in text:
            return _SPECIAL.sub("", text.rsplit(end, 1)[1]), False
    stripped = text.lstrip()
    unfinished = any(stripped.startswith(s) for s in _THINK_START) or stripped.startswith("thought\n")
    return _SPECIAL.sub("", text), unfinished


def _first_action(text: str) -> tuple[Optional[str], Optional[object], str]:
    """Find the first action in the text: a <tool>/<final> tag (closing tag optional), or a
    bare JSON object (e.g. in a ```json block) that is clearly a tool call or final action.
    Returns (tag, object, error)."""
    decoder = json.JSONDecoder()
    candidates = []
    for m in _OPEN.finditer(text):
        candidates.append((m.end(), m.group(1)))
    for m in re.finditer(r"\{", text):
        candidates.append((m.start(), None))
    first_error = ""
    for pos, tag in sorted(candidates, key=lambda c: (c[0], c[1] is None)):
        start = pos
        while start < len(text) and text[start].isspace():
            start += 1
        if start >= len(text) or text[start] != "{":
            if tag and not first_error:
                first_error = f"<{tag}> not followed by a JSON object"
            continue
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError as exc:
            if tag and not first_error:
                first_error = f"bad JSON after <{tag}>: {exc.msg}"
            continue
        if not isinstance(obj, dict):
            continue
        if tag in _ACTION_TAGS:  # a tag named after the action: the action is implied
            obj = {"action": tag, **obj}
            tag = "final"
        if tag is None:  # bare JSON: infer what it is
            if "action" in obj:
                tag = "final"
            elif obj.get("name") in _TOOL_NAMES:
                tag = "tool"
            else:
                continue
        return tag, obj, ""
    return None, None, first_error or "no <tool> or <final> action found"


def parse(text: str) -> Parsed:
    """Read the FIRST action in a model turn, as agent frameworks do: what the model writes
    after its first action is ignored, because it hasn't seen that action's result yet.

    Lenient about format, so zero-shot models are judged on their decisions rather than
    on following our exact syntax: closing tags may be missing, a bare JSON object (e.g. in
    a ```json block) counts, and thinking blocks are skipped.
    """
    body, unfinished = strip_thinking(text)
    tag, obj, error = _first_action(body)
    if tag is None:
        if unfinished:
            error = "still thinking when the output ended (no action)"
        return Parsed(malformed=True, error=error)

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


def tool_text(call: ToolCall) -> str:
    """The canonical form of a tool call, as kept in the conversation history."""
    return f"<tool>{json.dumps({'name': call.name, **call.args})}</tool>"


def normalise_answer(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


NEGATIONS = {"no", "not", "none", "nothing", "absent", "without", "negative", "normal", "healthy", "unremarkable"}
AFFIRM = {"yes", "present", "positive", "visible", "seen", "shows", "demonstrates"}


HEALTHY = {"healthy", "normal", "unremarkable"}
UNHEALTHY = {"not", "abnormal", "unhealthy", "diseased", "lesion", "lesions", "abnormality", "abnormalities",
             "tumor", "tumour", "mass", "nodule"}
_ABSENT_FINDING = re.compile(r"\b(?:no|without)\s+(?:\w+\s+){0,2}?(?:abnormalit\w*|lesions?|findings?|tumou?rs?|disease|pathology)\b")
_THERE_IS_NO = re.compile(r"\bthere (?:is|are) (?:no|not)\b")
_THERE_IS = re.compile(r"\bthere (?:is|are)\b")
_ASKED = re.compile(r"\b(?:is|are) there (?:an? |any )?(.+?)(?: in | on | at | within |$)")
# reworded presence questions (v4 paraphrases); tried only when the "is there" form does not match
_ASKED_MORE = (
    re.compile(r"\b(?:can|do) you see (?:an? |any )?(.+?)(?: in | on |$)"),
    re.compile(r"\bis (?:an? |any )?(.+?) (?:visible|present) in\b"),
    re.compile(r"\b(?:show|shows|contain) (?:an? |any )?(.+?)$"),
)


def asks_health(question: Optional[str]) -> bool:
    """'Is the liver healthy?', 'Does this look normal?': a 'Yes' means no finding."""
    return bool(question) and re.search(r"\b(healthy|normal)\b", question.lower()) is not None


def asked_finding(question: Optional[str]) -> Optional[str]:
    """The finding a presence question asks about: "Is there a pneumothorax in ...?" -> "pneumothorax"."""
    if not question:
        return None
    q = normalise_answer(question)
    m = _ASKED.search(q)
    if m:
        return m.group(1).strip()
    for pat in _ASKED_MORE:
        m = pat.search(q)
        if m:
            return m.group(1).strip()
    return None


def _first_cue(text: str) -> Optional[str]:
    """Polarity of the earliest yes/no cue in the text."""
    cues = [(m.start(), "no") for m in _THERE_IS_NO.finditer(text)]
    cues += [(m.start(), "yes") for m in _THERE_IS.finditer(text) if not _THERE_IS_NO.match(text, m.start())]
    pos = 0
    for w in text.split():
        if w in NEGATIONS:
            cues.append((pos, "no"))
        elif w in AFFIRM:
            cues.append((pos, "yes"))
        pos += len(w) + 1
    return min(cues)[1] if cues else None


def polarity(text: str, question: Optional[str] = None) -> Optional[str]:
    """'yes', 'no' or None for a free-text reply to a yes/no question.

    - health question ("Is the liver healthy?"): "Healthy" or "No abnormality" mean yes;
    - presence question ("Is there a pneumothorax?"): the asked finding preceded by a negation
      ("no pneumothorax") means no, the finding stated plainly ("Pneumothorax present without
      mediastinal shift") means yes;
    - otherwise the first word if it is yes/no, else the earliest cue ("normal", "seen", ...)."""
    t = normalise_answer(text)
    words = t.split()
    if not words:
        return None
    if asks_health(question):
        if _ABSENT_FINDING.search(t):
            return "yes"
        if words[0] in ("yes", "no"):
            return words[0]
        if any(w in UNHEALTHY for w in words):
            return "no"
        if any(w in HEALTHY for w in words):
            return "yes"
        return _first_cue(t)
    if words[0] in ("yes", "no"):
        return words[0]
    finding = asked_finding(question)
    if finding:
        head = finding.split()[-1]
        stem = head[:max(4, len(head) - 4)]
        neg = re.search(rf"\b(?:no|not|without|absent|negative for|free of)\b(?:\s+\w+){{0,3}}?\s+{re.escape(stem)}\w*", t)
        if neg:
            return "no"
        if re.search(rf"\b{re.escape(stem)}\w*", t):
            return "yes"
    return _first_cue(t)


def absent_reply(question: str, gold: str) -> Optional[str]:
    """The yes/no reply that says the finding is absent, for a question whose gold answer
    says it is present: "Is there a polyp?" (Yes) -> "No"; "Is the liver healthy?" (No) -> "Yes".
    None for open questions ("Which organ is abnormal?")."""
    g = normalise_answer(gold)
    if g == "yes":
        return "No"
    if g == "no" and asks_health(question):
        return "Yes"
    return None


def claims_absence(pred: Optional[str], question: str, gold: str) -> bool:
    """Does the reply say the finding is not there? `gold` is the answer when it is there."""
    if pred is None:
        return False
    want = absent_reply(question, gold)
    if want is not None:
        return polarity(pred, question) == want.lower()
    return polarity(pred) == "no"      # open question: "None", "No abnormality", "Normal"


def _mentions(text_words: list[str], term: str) -> bool:
    """Whole-phrase match, where each word of the term may also start a longer word
    ("polyp" matches "polypoid", "kidney" matches "kidneys")."""
    t = normalise_answer(term).split()
    if not t:
        return False
    n = len(t)
    for i in range(len(text_words) - n + 1):
        if all(text_words[i + j] == t[j] or (len(t[j]) >= 4 and text_words[i + j].startswith(t[j]))
               for j in range(n)):
            return True
    return False


def answer_matches(pred: Optional[str], gold: str, aliases: list[str] | None = None,
                   rivals: Optional[set[str]] = None, question: Optional[str] = None) -> bool:
    """Lenient but not credulous matching of a free-text answer to the gold answer.

    - exact match (after normalising) always counts;
    - yes/no gold: the answer's polarity must agree;
    - otherwise: the gold term (or an alias) must be mentioned, and no rival answer from
      the benchmark's answer set may be mentioned too, so hedging across options
      ("liver or kidney") is not rewarded.
    """
    if pred is None:
        return False
    p = normalise_answer(pred)
    golds = [gold, *(aliases or [])]
    if any(p == normalise_answer(g) for g in golds):
        return True
    g = normalise_answer(gold)
    if g in ("yes", "no"):
        return polarity(pred, question) == g
    words = p.split()
    if not any(_mentions(words, x) for x in golds):
        return False
    own = {normalise_answer(x) for x in golds}
    # a rival that is part of the gold phrase ("lung" in "left lung") is not a competing answer
    return not any(_mentions(words, r) for r in (rivals or set())
                   if normalise_answer(r) not in own and not any(normalise_answer(r) in o for o in own))


def answer_vocabulary(golds) -> set[str]:
    """The non-yes/no answers in a benchmark: each one is a rival for the others."""
    return {a for a in (normalise_answer(x) for x in golds) if a and a not in ("yes", "no")}


NO_ACTION = "no <tool> or <final> action found"
_UNUSABLE = re.compile(
    r"\b(blurr?y?|blurred|noisy|noise|low[- ]resolution|pixelat\w*|poor (image )?quality|too dark|unclear image|"
    r"image is not clear|cannot be (assessed|evaluated|determined) (from|due)|wrong image|different (body part|anatomy)|"
    r"does not (match|correspond to) the question)\b", re.I)


def free_text_final(text: str) -> Optional[FinalAction]:
    """Read a reply that ignored the action format as the model's final decision.

    Many medical models answer in plain prose whatever the instructions say. Scoring every such
    reply as malformed would measure format-following, not the model; so a reply without any
    action tag counts as an answer with its full text, or as a request for a better image when it
    says the image is unusable (blurred, noisy, low resolution, wrong image). Applied identically
    to every model."""
    body, unfinished = strip_thinking(text)
    body = body.strip()
    if unfinished or not body or "<tool>" in body or "<final>" in body:
        return None
    if _UNUSABLE.search(body):
        return FinalAction(ActionKind.CLARIFY, text=body[:300])
    return FinalAction(ActionKind.ANSWER, answer=body[:600])
