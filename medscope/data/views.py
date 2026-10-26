"""Turn one Case into its four Views and save the images."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .counterfactual import DEGRADATIONS, make_degraded, make_random_removal, make_target_removal
from .schema import Case, View, ViewKind, box_to_mask, mask_to_box


def load_image(path: str | Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def load_mask(case: Case, height: int, width: int) -> np.ndarray:
    """Lesion mask from the case's mask file, or from its box if there is no mask."""
    if case.mask_path:
        m = np.asarray(Image.open(case.mask_path).convert("L"))
        if m.shape != (height, width):
            m = np.asarray(Image.fromarray(m).resize((width, height), Image.NEAREST))
        return m > 127
    if case.lesion_box:
        return box_to_mask(case.lesion_box, width, height)
    raise ValueError(f"case {case.case_id} has neither mask_path nor lesion_box")


def _save(image: np.ndarray, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)
    return str(path)


def build_views(
    case: Case,
    out_dir: str | Path,
    rng: np.random.Generator,
    other_image: Optional[np.ndarray] = None,
    degradation: Optional[str] = None,
) -> list[View]:
    """Build original, target-removal, random-removal and degraded views.

    Returns an empty list if no valid random-removal control could be placed;
    a case without its control would make the abstention gap meaningless.
    """
    out_dir = Path(out_dir)
    image = load_image(case.image_path)
    h, w = image.shape[:2]
    mask = load_mask(case, h, w)
    lesion_box = case.lesion_box or mask_to_box(mask)

    random_result = make_random_removal(image, mask, rng)
    if random_result is None:
        return []
    random_img, random_mask = random_result
    target_img, target_mask = make_target_removal(image, mask)

    if degradation is None:
        choices = [d for d in DEGRADATIONS if d != "mismatch" or other_image is not None]
        degradation = str(rng.choice(choices))
    degraded_img = make_degraded(image, degradation, rng, other_image)

    common = dict(
        case_id=case.case_id,
        patient_id=case.patient_id,
        question=case.question,
        answer=case.answer,
        answer_aliases=case.answer_aliases,
        lesion_box=lesion_box,
        critical=case.critical,
    )
    base = out_dir / case.case_id
    return [
        View(view_id=f"{case.case_id}__original", kind=ViewKind.ORIGINAL,
             image_path=_save(image, base / "original.png"), **common),
        View(view_id=f"{case.case_id}__target_removal", kind=ViewKind.TARGET_REMOVAL,
             image_path=_save(target_img, base / "target_removal.png"),
             meta={"edit_box": mask_to_box(target_mask)}, **common),
        View(view_id=f"{case.case_id}__random_removal", kind=ViewKind.RANDOM_REMOVAL,
             image_path=_save(random_img, base / "random_removal.png"),
             meta={"edit_box": mask_to_box(random_mask)}, **common),
        View(view_id=f"{case.case_id}__degraded", kind=ViewKind.DEGRADED,
             image_path=_save(degraded_img, base / "degraded.png"),
             meta={"degradation": degradation}, **common),
    ]
