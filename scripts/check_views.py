"""Run the automated quality checks on built views and write a clean manifest.

Per case: the lesion must really be gone after target removal, the evidence intact after
random removal, and the image not a near-copy of a reference split. Then, if a simple
classifier can tell lesion-removal edits from random edits (shortcut AUC above
--max-shortcut-auc), the most detectable cases are dropped adversarially until it can't,
dropping at most --max-filter-frac of cases.

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
    filter_shortcut,
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


def dataset_key(case_id: str) -> str:
    """'slake_xmlab12_abn' -> 'slake', 'chestxdet00012_abn' -> 'chestxdet'."""
    import re
    return re.match(r"[a-z]+", case_id.split("_")[0]).group(0) if re.match(r"[a-z]+", case_id) else case_id.split("_")[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", required=True)
    ap.add_argument("--dedup-against", default=None, help="views.jsonl of another split (e.g. train)")
    ap.add_argument("--max-shortcut-auc", type=float, default=0.6)
    ap.add_argument("--no-filter-shortcut", dest="filter_shortcut", action="store_false",
                    help="only measure the shortcut AUC; don't drop the most detectable edits")
    ap.add_argument("--max-filter-frac", type=float, default=0.3,
                    help="never drop more than this share of cases when filtering")
    ap.add_argument("--min-correlation", type=float, default=0.98,
                    help="pixel correlation needed to confirm a hash match as a duplicate")
    args = ap.parse_args()

    views_path = Path(args.views)
    groups = by_case(views_path)
    results, tfeats, rfeats = [], [], []

    feats: dict[str, tuple[np.ndarray, np.ndarray]] = {}
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
        feats[cid] = (edit_features(tgt, t_edit), edit_features(rnd, r_edit))

    passed = {r.case_id for r in results if r.passed}

    dupes = {}
    if args.dedup_against:
        ref_groups = by_case(Path(args.dedup_against))

        def same_image(qid: str, rid: str) -> bool:
            return correlation(load_image(groups[qid]["original"]["image_path"]),
                               load_image(ref_groups[rid]["original"]["image_path"])) >= args.min_correlation

        dupes = near_duplicates(original_hashes({c: groups[c] for c in passed}),
                                original_hashes(ref_groups), confirm=same_image)
        passed -= set(dupes)

    # shortcut check on the cases that survived so far, per dataset and overall,
    # then adversarial filtering of the most detectable edits
    def auc_of(ids):
        if len(ids) < MIN_SHORTCUT_CASES:
            return None
        return shortcut_auc(np.array([feats[c][0] for c in ids]), np.array([feats[c][1] for c in ids]))

    ids = sorted(passed)
    by_dataset = {}
    for c in ids:
        by_dataset.setdefault(dataset_key(c), []).append(c)
    auc_by_dataset = {d: auc_of(v) for d, v in by_dataset.items()}
    auc_before = auc_of(ids)
    auc, history, filtered = auc_before, [], []
    if auc_before is not None and args.filter_shortcut and auc_before > args.max_shortcut_auc:
        keep, history = filter_shortcut(np.array([feats[c][0] for c in ids]),
                                        np.array([feats[c][1] for c in ids]),
                                        target_auc=args.max_shortcut_auc, max_drop_frac=args.max_filter_frac)
        kept = {ids[i] for i in keep}
        filtered = sorted(set(ids) - kept)
        passed = kept
        auc = history[-1]

    report = {
        "cases_checked": len(results),
        "cases_passed": len(passed),
        "failed_lesion_removed": sum(not r.lesion_removed for r in results),
        "failed_evidence_intact": sum(not r.evidence_intact for r in results),
        "duplicates_of_reference": len(dupes),
        "shortcut_auc_before_filtering": auc_before,
        "shortcut_auc_by_dataset_before_filtering": auc_by_dataset,
        "shortcut_filtered_cases": len(filtered),
        "shortcut_filtered_by_dataset": {d: sum(1 for c in filtered if dataset_key(c) == d) for d in by_dataset},
        "shortcut_auc_history": history,
        "shortcut_auc": auc,
        "shortcut_ok": None if auc is None else auc <= args.max_shortcut_auc,
        "cases": [r.__dict__ | {"passed": r.case_id in passed} for r in results],
        "duplicates": dupes,
        "filtered": filtered,
    }
    (views_path.parent / "quality_report.json").write_text(json.dumps(report, indent=2))
    with open(views_path.parent / "views_clean.jsonl", "w") as f:
        for cid in sorted(passed):
            for v in groups[cid].values():
                f.write(json.dumps(v) + "\n")

    print(f"checked {len(results)} cases, {len(passed)} kept "
          f"(lesion not removed: {report['failed_lesion_removed']}, "
          f"evidence changed: {report['failed_evidence_intact']}, duplicates: {len(dupes)}, "
          f"easiest-to-spot edits filtered: {len(filtered)})")
    if auc is None:
        print(f"shortcut check skipped: needs at least {MIN_SHORTCUT_CASES} cases to be reliable")
    else:
        by_ds = ", ".join(f"{d} {a:.3f}" for d, a in auc_by_dataset.items() if a is not None)
        print(f"shortcut AUC before filtering: {auc_before:.3f} ({by_ds})")
        verdict = "OK" if report["shortcut_ok"] else "still above target after the filtering cap"
        print(f"shortcut AUC after filtering: {auc:.3f} -> {verdict}")


if __name__ == "__main__":
    main()
