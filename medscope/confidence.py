"""Confidence from the model's own token probabilities.

Verbalised confidence ("confidence": 0.81) is easy to fake and fine-tuning tends to collapse it to
one value. For every model we also record the probability the model gave to the answer it wrote:
the geometric mean of the greedy probabilities of the tokens inside the final answer's "answer"
string. This is the standard sequence-likelihood confidence and works the same for every model.
"""

from __future__ import annotations

import math
import re
from typing import Optional, Sequence

_ANSWER = re.compile(r'"answer"\s*:\s*"([^"]*)"')


def answer_prob(pieces: Sequence[str], probs: Sequence[float]) -> Optional[float]:
    """Geometric-mean probability of the tokens spelling the answer value of the first final action.

    pieces[i] is the decoded text of generated token i and probs[i] its probability."""
    if not pieces or len(pieces) != len(probs):
        return None
    text = "".join(pieces)
    start = text.find("<final>")
    m = _ANSWER.search(text, max(start, 0))
    if not m or m.start(1) == m.end(1):
        return None
    lo, hi = m.start(1), m.end(1)
    logs, pos = [], 0
    for piece, p in zip(pieces, probs):
        end = pos + len(piece)
        if end > lo and pos < hi and p > 0:
            logs.append(math.log(p))
        pos = end
    return math.exp(sum(logs) / len(logs)) if logs else None


class GreedyProbRecorder:
    """Logits processor that records, at each step, the probability of the greedy (argmax) token
    for every row in the batch. It does not change the scores."""

    def __init__(self):
        self.steps: list = []

    def __call__(self, input_ids, scores):
        import torch
        self.steps.append(torch.softmax(scores.float(), dim=-1).max(dim=-1).values.cpu())
        return scores

    def row(self, i: int, n: int) -> list[float]:
        return [float(s[i]) for s in self.steps[:n]]
