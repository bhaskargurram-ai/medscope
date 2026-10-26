"""Case and view records shared by data building, rewards and evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

Box = list[int]  # [x1, y1, x2, y2], ints normalised to 0-1000


class ViewKind(str, Enum):
    ORIGINAL = "original"
    TARGET_REMOVAL = "target_removal"
    RANDOM_REMOVAL = "random_removal"
    DEGRADED = "degraded"


class ActionKind(str, Enum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    REFER = "refer"


EXPECTED_ACTION: dict[ViewKind, ActionKind] = {
    ViewKind.ORIGINAL: ActionKind.ANSWER,
    ViewKind.RANDOM_REMOVAL: ActionKind.ANSWER,
    ViewKind.TARGET_REMOVAL: ActionKind.REFER,
    ViewKind.DEGRADED: ActionKind.CLARIFY,
}


@dataclass
class Case:
    """One image-question pair from a source dataset, before view generation."""

    case_id: str
    patient_id: str
    dataset: str
    modality: str
    image_path: str
    question: str
    answer: str
    answer_aliases: list[str] = field(default_factory=list)
    lesion_box: Optional[Box] = None       # normalised 0-1000
    mask_path: Optional[str] = None        # binary lesion mask, same size as image
    critical: bool = False                 # missing this finding is high-cost

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Case":
        return cls(**d)


@dataclass
class View:
    """A case rendered as one of the four views, ready for the model."""

    view_id: str
    case_id: str
    patient_id: str
    kind: ViewKind
    image_path: str
    question: str
    answer: str
    answer_aliases: list[str]
    lesion_box: Optional[Box]
    critical: bool
    meta: dict = field(default_factory=dict)

    @property
    def expected_action(self) -> ActionKind:
        return EXPECTED_ACTION[self.kind]

    @property
    def answerable(self) -> bool:
        return self.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "View":
        d = dict(d)
        d["kind"] = ViewKind(d["kind"])
        return cls(**d)


def box_to_pixels(box: Box, width: int, height: int) -> tuple[int, int, int, int]:
    """Convert a 0-1000 normalised box to clamped pixel coordinates."""
    x1, y1, x2, y2 = box
    px1 = int(np.clip(round(x1 / 1000 * width), 0, width))
    py1 = int(np.clip(round(y1 / 1000 * height), 0, height))
    px2 = int(np.clip(round(x2 / 1000 * width), 0, width))
    py2 = int(np.clip(round(y2 / 1000 * height), 0, height))
    return min(px1, px2), min(py1, py2), max(px1, px2), max(py1, py2)


def pixels_to_box(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> Box:
    return [
        int(round(x1 / width * 1000)),
        int(round(y1 / height * 1000)),
        int(round(x2 / width * 1000)),
        int(round(y2 / height * 1000)),
    ]


def mask_to_box(mask: np.ndarray) -> Optional[Box]:
    """Tight normalised box around a boolean mask, or None if the mask is empty."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    h, w = mask.shape
    return pixels_to_box(int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1, w, h)


def box_to_mask(box: Box, width: int, height: int) -> np.ndarray:
    x1, y1, x2, y2 = box_to_pixels(box, width, height)
    mask = np.zeros((height, width), dtype=bool)
    mask[y1:y2, x1:x2] = True
    return mask


def iou(a: Optional[Box], b: Optional[Box]) -> float:
    """Intersection over union of two normalised boxes; 0 if either is missing or empty."""
    if a is None or b is None:
        return 0.0
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def box_area_fraction(box: Optional[Box]) -> float:
    if box is None:
        return 0.0
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1) / 1_000_000
