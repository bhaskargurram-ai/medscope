"""Question paraphrases.

Every templated question has the form "Is there <finding> in this <image>?". v4 training sees it in several
wordings (TRAIN), so the model does not key on one sentence; the HELD_OUT wordings are never used in
training and serve only to test whether answers survive an unseen phrasing. Questions of any other form
(e.g. SLAKE's own questions) are left unchanged.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Optional

from ..data.loaders.common import stable_index
from ..data.schema import View

PATTERN = re.compile(r"^Is there (?P<finding>.+?) in (?P<image>this .+?)\?$")

TRAIN = (
    "Can you see {finding} in {image}?",
    "Does {image} show {finding}?",
    "Is {finding} visible in {image}?",
    "Do you see {finding} in {image}?",
)
HELD_OUT = (
    "Is {finding} present in {image}?",
    "Does {image} contain {finding}?",
    "Would you say {image} shows {finding}?",
)


def paraphrase(question: str, templates: tuple[str, ...], key: str) -> Optional[str]:
    """A deterministic rewording of a templated question, or None if the question is not templated."""
    m = PATTERN.match(question.strip())
    if not m:
        return None
    t = templates[stable_index(key, len(templates))]
    out = t.format(finding=m["finding"], image=m["image"])
    return out[0].upper() + out[1:]


def paraphrase_view(view: View, templates: tuple[str, ...], salt: str = "") -> View:
    q = paraphrase(view.question, templates, view.case_id + salt)   # one wording per case: all its views agree
    return view if q is None else replace(view, question=q, meta={**(view.meta or {}), "original_question": view.question})
