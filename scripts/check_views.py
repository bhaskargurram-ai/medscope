"""Run the automated quality checks on built views and write a clean manifest.

Outputs, next to the input views.jsonl:
  quality_report.json   per-case results + dataset-level shortcut AUC and duplicates
  views_clean.jsonl     only the cases that passed every per-case check
                        (and, with --dedup-against, are not duplicates of training images)

Usage:
    python scripts/check_views.py --views data/views/slake_test/views.jsonl \
        --dedup-against data/views/slake_train/views.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.quality import (  # noqa: E402
    MIN_SHORTCUT_CASES,
    check_case,
    correlation,
    dhash,
    edit_features,
    near_duplicates,
    shortcut_auc,
)
from medscope.data.views import load_image  # noqa: E402


def load_mask(path: str) -> np.ndarray:
    return load_image(path)[..., 0] > 127


def by_case(path: Path) -> dict[str, dict[str, dict]]:
    groups: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in open(path):
        if line.strip():
            v = json.loads(line)
            groups[v["case_id"]][v["kind"]] = v
    return groups


def original_hashes(groups: dict[str, dict[str, dict]]) -> dict[str, int]:
    return {cid: dhash(load_image(g["original"]["image_path"])) for cid, g in groups.items() if "original" in g}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", required=True)
    ap.add_argument("--dedup-against", default=None, help="views.jsonl of another split (e.g. train)")
    ap.add_argument("--max-shortcut-auc", type=float, default=0.6)
    ap.add_argument("--min-correlation", type=float, default=0.98,
                    help="pixel correlation needed to confirm a hash match as a duplicate")
    args = ap.parse_args()

    views_path = Path(args.views)
    groups = by_case(views_path)
    results, tfeats, rfeats = [], [], []

    for cid, g in groups.items():
        if not all(k in g for k in ("original", "target_removal", "random_removal")):
            continue
        orig = load_image(g["original"]["image_path"])
        tgt = load_image(g["target_removal"]["image_path"])
        rnd = load_image(g["random_removal"]["image_path"])
        lesion = load_mask(g["original"]["meta"]["lesion_mask"])
        t_edit = load_mask(g["target_removal"]["meta"]["edit_mask"])
        r_edit = load_mask(g["random_removal"]["meta"]["edit_mask"])
        res = check_case(cid, orig, tgt, rnd, lesion, r_edit)
        results.append(res)
        tfeats.append(edit_features(tgt, t_edit))
        rfeats.append(edit_features(rnd, r_edit))

    passed = {r.case_id for r in results if r.passed}

    auc = None
    if len(results) >= MIN_SHORTCUT_CASES:
        auc = shortcut_auc(np.array(tfeats), np.array(rfeats))

    dupes = {}
    if args.dedup_against:
        ref_groups = by_case(Path(args.dedup_against))

        def same_image(qid: str, rid: str) -> bool:
            return correlation(load_image(groups[qid]["original"]["image_path"]),
                               load_image(ref_groups[rid]["original"]["image_path"])) >= args.min_correlation

        dupes = near_duplicates(original_hashes({c: groups[c] for c in passed}),
                                original_hashes(ref_groups), confirm=same_image)
        passed -= set(dupes)

    report = {
        "cases_checked": len(results),
        "cases_passed": len(passed),
        "failed_lesion_removed": sum(not r.lesion_removed for r in results),
        "failed_evidence_intact": sum(not r.evidence_intact for r in results),
        "duplicates_of_reference": len(dupes),
        "shortcut_auc": auc,
        "shortcut_ok": None if auc is None else auc <= args.max_shortcut_auc,
        "cases": [r.__dict__ | {"passed": r.passed} for r in results],
        "duplicates": dupes,
    }
    (views_path.parent / "quality_report.json").write_text(json.dumps(report, indent=2))
    with open(views_path.parent / "views_clean.jsonl", "w") as f:
        for cid in sorted(passed):
            for v in groups[cid].values():
                f.write(json.dumps(v) + "\n")

    print(f"checked {len(results)} cases, {len(passed)} passed "
          f"(lesion not removed: {report['failed_lesion_removed']}, "
          f"evidence changed: {report['failed_evidence_intact']}, duplicates: {len(dupes)})")
    if auc is None:
        print(f"shortcut check skipped: needs at least {MIN_SHORTCUT_CASES} cases to be reliable")
    else:
        verdict = "OK" if report["shortcut_ok"] else "WARNING: edits leak a shortcut, improve the inpainter"
        print(f"shortcut AUC (target vs random edits): {auc:.3f} -> {verdict}")


if __name__ == "__main__":
    main()
