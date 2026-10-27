"""Shared loader helpers: splitting by groups of near-identical images, and stable choices.

Public medical datasets often contain near-copies: neighbouring slices of one scan,
or consecutive frames of one endoscopy video. If those land in different splits, the
test set leaks. `group_split` clusters images whose perceptual hashes are close and
whose pixels correlate strongly, then assigns whole clusters to train/validation/test.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Sequence

import numpy as np

from ..quality import correlation, dhash, hamming
from ..views import load_image

SPLITS = ("train", "validation", "test")


def stable_index(key: str, n: int) -> int:
    """Deterministic pick in range(n) from a string (independent of Python's hash seed)."""
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest(), 16) % n


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def near_duplicate_groups(
    image_paths: Sequence[str | Path],
    max_hash_distance: int = 10,
    min_correlation: float = 0.95,
) -> list[int]:
    """Group id for each image; images in one group are near-copies of each other (transitively)."""
    images = [load_image(p) for p in image_paths]
    hashes = [dhash(img) for img in images]
    uf = _UnionFind(len(images))
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            if hamming(hashes[i], hashes[j]) <= max_hash_distance and uf.find(i) != uf.find(j):
                if correlation(images[i], images[j]) >= min_correlation:
                    uf.union(i, j)
    roots = [uf.find(i) for i in range(len(images))]
    relabel = {r: k for k, r in enumerate(sorted(set(roots)))}
    return [relabel[r] for r in roots]


def assign_splits(groups: Sequence[int], fractions=(0.7, 0.15, 0.15), seed: int = 2026) -> dict[int, str]:
    """Map each group id to a split, filling validation and test to their share of images."""
    sizes: dict[int, int] = {}
    for g in groups:
        sizes[g] = sizes.get(g, 0) + 1
    order = np.random.default_rng(seed).permutation(sorted(sizes)).tolist()
    total = len(groups)
    targets = {"validation": fractions[1] * total, "test": fractions[2] * total}
    filled = {"validation": 0, "test": 0}
    out = {}
    for g in order:
        for split in ("test", "validation"):
            if filled[split] + sizes[g] <= targets[split] + 0.5 * sizes[g]:
                out[g] = split
                filled[split] += sizes[g]
                break
        else:
            out[g] = "train"
    return out
