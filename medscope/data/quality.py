"""Automated quality checks for counterfactual views. No human review involved.

Per case:
  1. lesion_removed   - after target removal, the lesion region no longer stands out
                        from the tissue ring around it.
  2. evidence_intact  - after random removal, every lesion pixel is unchanged and
                        the edit does not touch the lesion.
Across the dataset:
  3. shortcut_auc     - can a simple classifier tell target-removal edits from
                        random-removal edits by their texture alone? An AUC near 0.5
                        means no; well above 0.5 means the edits leak a shortcut.
  4. near_duplicates  - perceptual-hash matches between splits (test images that
                        also appear in training).

A learned detector can be plugged into check 1 through `detector_fn` once one is
available for the modality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np

from .counterfactual import dilate


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float32)
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)


def ring(mask: np.ndarray, inner: int, width: int) -> np.ndarray:
    return dilate(mask, inner + width) & ~dilate(mask, inner)


def region_contrast(image: np.ndarray, mask: np.ndarray, inner: int = 6, width: int = 8) -> float:
    """|mean inside - mean of surrounding ring| in units of the ring's std."""
    g = to_gray(image)
    r = ring(mask, inner, width)
    if not mask.any() or not r.any():
        return 0.0
    return float(abs(g[mask].mean() - g[r].mean()) / (g[r].std() + 1.0))


@dataclass
class CaseCheck:
    case_id: str
    contrast_before: float
    contrast_after: float
    lesion_removed: bool
    lesion_pixels_changed: int
    edit_overlaps_lesion: bool
    evidence_intact: bool
    detector_score: Optional[float] = None

    @property
    def passed(self) -> bool:
        return self.lesion_removed and self.evidence_intact


def check_case(
    case_id: str,
    original: np.ndarray,
    target: np.ndarray,
    random: np.ndarray,
    lesion_mask: np.ndarray,
    random_edit_mask: np.ndarray,
    max_contrast_after: float = 1.0,
    max_contrast_ratio: float = 0.35,
    detector_fn: Optional[Callable[[np.ndarray, np.ndarray], float]] = None,
    detector_threshold: float = 0.5,
) -> CaseCheck:
    before = region_contrast(original, lesion_mask)
    after = region_contrast(target, lesion_mask)
    removed = after <= max(max_contrast_after, max_contrast_ratio * before)

    det = None
    if detector_fn is not None:
        det = float(detector_fn(target, lesion_mask))
        removed = removed and det < detector_threshold

    changed = int((np.abs(original.astype(np.int16) - random.astype(np.int16)).max(axis=-1)[lesion_mask] > 0).sum())
    overlaps = bool((random_edit_mask & lesion_mask).any())
    return CaseCheck(case_id, before, after, removed, changed, overlaps,
                     changed == 0 and not overlaps, det)


# ---- shortcut check -------------------------------------------------------

def edit_features(image: np.ndarray, edit_mask: np.ndarray) -> np.ndarray:
    """How the edited region differs from the tissue just around it.

    Only relative features (inside vs surrounding ring) are used. Absolute
    brightness is left out on purpose: lesions sit in particular organs, so raw
    intensity would separate target from random edits by location even if the
    inpainting were perfect.
    """
    g = to_gray(image)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    grad = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    r = ring(edit_mask, 0, 6)
    seam = ring(edit_mask, 0, 2) | (edit_mask & ~ring(~edit_mask, 0, 2))  # pixels near the boundary
    if not edit_mask.any() or not r.any():
        return np.zeros(5)
    eps = 1.0
    return np.array([
        abs(g[edit_mask].mean() - g[r].mean()) / (g[r].std() + eps),     # brightness step
        np.log((g[edit_mask].std() + eps) / (g[r].std() + eps)),          # texture loss
        np.log((grad[edit_mask].mean() + eps) / (grad[r].mean() + eps)),  # edge energy
        np.log((lap[edit_mask].std() + eps) / (lap[r].std() + eps)),      # fine detail
        np.log((grad[seam].mean() + eps) / (grad[r].mean() + eps)),       # visible seam
    ])


def _auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC with tie handling."""
    order = np.argsort(scores, kind="stable")
    ranks = np.empty(len(scores))
    s = scores[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    pos = labels == 1
    n_pos, n_neg = pos.sum(), (~pos).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _fit_logreg(x: np.ndarray, y: np.ndarray, l2: float = 1e-2, steps: int = 800, lr: float = 0.1) -> np.ndarray:
    w = np.zeros(x.shape[1] + 1)
    xb = np.hstack([x, np.ones((len(x), 1))])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-xb @ w))
        grad = xb.T @ (p - y) / len(y) + l2 * np.r_[w[:-1], 0]
        w -= lr * grad
    return w


MIN_SHORTCUT_CASES = 50  # below this the AUC is too noisy to judge (0.9 seen at n=12 with no real leak)


def _cv_auc(x: np.ndarray, y: np.ndarray, case_fold: np.ndarray, folds: int) -> float:
    fold = np.r_[case_fold, case_fold]
    scores = np.zeros(len(y))
    for k in range(folds):
        tr, te = fold != k, fold == k
        mu, sd = x[tr].mean(0), x[tr].std(0) + 1e-6
        w = _fit_logreg((x[tr] - mu) / sd, y[tr])
        xt = (x[te] - mu) / sd
        scores[te] = np.hstack([xt, np.ones((len(xt), 1))]) @ w
    return _auc(scores, y)


def shortcut_auc(target_feats: np.ndarray, random_feats: np.ndarray, folds: int = 5,
                 repeats: int = 5, seed: int = 0) -> float:
    """Cross-validated AUC of telling target-removal edits from random-removal edits.

    Row i of both arrays must come from the same case, so each fold holds out whole
    cases. The AUC is averaged over `repeats` random fold assignments for stability.
    """
    n = min(len(target_feats), len(random_feats))
    if n < folds * 2:
        raise ValueError(f"need at least {folds * 2} cases for the shortcut check, got {n}")
    x = np.vstack([target_feats[:n], random_feats[:n]])
    y = np.r_[np.ones(n), np.zeros(n)]
    rng = np.random.default_rng(seed)
    return float(np.mean([_cv_auc(x, y, rng.permutation(n) % folds, folds) for _ in range(repeats)]))


# ---- duplicates -----------------------------------------------------------

def dhash(image: np.ndarray, size: int = 8) -> int:
    """64-bit difference hash; robust to resizing and mild compression."""
    small = cv2.resize(to_gray(image), (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def correlation(a: np.ndarray, b: np.ndarray, size: int = 64) -> float:
    """Pearson correlation of two images after resizing to size x size."""
    x = cv2.resize(to_gray(a), (size, size), interpolation=cv2.INTER_AREA).ravel()
    y = cv2.resize(to_gray(b), (size, size), interpolation=cv2.INTER_AREA).ravel()
    x, y = x - x.mean(), y - y.mean()
    denom = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / denom) if denom > 0 else 1.0


def near_duplicates(
    query: dict[str, int],
    reference: dict[str, int],
    max_distance: int = 4,
    confirm: Optional[Callable[[str, str], bool]] = None,
) -> dict[str, str]:
    """Map each query id to a reference id whose hash is within max_distance bits.

    Different patients' scans of the same anatomy can share a coarse hash, so pass
    `confirm` (e.g. a pixel-correlation test) to verify each hash match.
    """
    found = {}
    ref_items = list(reference.items())
    for qid, qh in query.items():
        for rid, rh in ref_items:
            if hamming(qh, rh) <= max_distance and (confirm is None or confirm(qid, rid)):
                found[qid] = rid
                break
    return found
