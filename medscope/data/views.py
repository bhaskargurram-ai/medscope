"""Turn one Case into its four Views and save the images."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .counterfactual import (
    DEGRADATIONS,
    InpaintFn,
    make_degraded,
    make_random_removal,
    make_target_removal,
    telea_inpaint,
)
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


def _save_mask(mask: np.ndarray, path: Path) -> str:
    return _save((mask.astype(np.uint8) * 255), path)


def build_views(
    case: Case,
    out_dir: str | Path,
    rng: np.random.Generator,
    other_image: Optional[np.ndarray] = None,
    degradation: Optional[str] = None,
    inpaint_fn: InpaintFn = telea_inpaint,
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

    random_result = make_random_removal(image, mask, rng, inpaint_fn=inpaint_fn)
    if random_result is None:
        return []
    random_img, random_mask = random_result
    target_img, target_mask = make_target_removal(image, mask, inpaint_fn=inpaint_fn)

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
    lesion_mask_path = _save_mask(mask, base / "lesion_mask.png")
    original_path = _save(image, base / "original.png")

    def meta(**extra) -> dict:
        return {"lesion_mask": lesion_mask_path, "original_image": original_path, **extra}

    return [
        View(view_id=f"{case.case_id}__original", kind=ViewKind.ORIGINAL,
             image_path=original_path, meta=meta(), **common),
        View(view_id=f"{case.case_id}__target_removal", kind=ViewKind.TARGET_REMOVAL,
             image_path=_save(target_img, base / "target_removal.png"),
             meta=meta(edit_box=mask_to_box(target_mask),
                       edit_mask=_save_mask(target_mask, base / "target_edit_mask.png")),
             **common),
        View(view_id=f"{case.case_id}__random_removal", kind=ViewKind.RANDOM_REMOVAL,
             image_path=_save(random_img, base / "random_removal.png"),
             meta=meta(edit_box=mask_to_box(random_mask),
                       edit_mask=_save_mask(random_mask, base / "random_edit_mask.png")),
             **common),
        View(view_id=f"{case.case_id}__degraded", kind=ViewKind.DEGRADED,
             image_path=_save(degraded_img, base / "degraded.png"),
             meta=meta(degradation=degradation), **common),
    ]
