"""Download and prepare chest X-ray, breast ultrasound and brain MRI data.

For each dataset: lesion images become question cases (the view builder then makes the
original / lesion-removed / random-edit / degraded views), lesion-free images become
natural-negative views. Splits keep each patient (or group of near-copies) in one split.

Outputs in --out:
  cases_{train,validation,test}.jsonl              for scripts/build_views.py
  negatives/views_negatives{,_train,_val}.jsonl    natural negatives (test / train / validation)
  extra_report.txt

Usage:
    python scripts/prepare_extra.py --out data/extra --cache data/raw/extra [--datasets chestxdet busi lgg]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders import extra  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402


def protected_keys(files: list[str]) -> dict[str, str]:
    """Record key -> image path of every unedited image (original or natural negative) in the views files.
    Case ids are '<key>_<tag>' for lesion cases and '<key>neg_<tag>' for lesion-free images."""
    import json
    out = {}
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            v = json.loads(line)
            if v["kind"] == "original":
                out[v["case_id"].rsplit("_", 1)[0]] = v["image_path"]
            elif v["kind"] == "natural_negative":
                out[v["case_id"].split("neg_")[0]] = v["image_path"]
    return out


def protect(name, recs, test_keys, seen_keys):
    """Drop every group holding an existing test image; return the groups of earlier images (kept out of fresh).
    Keys are row indices of the source parquet; each protected key is checked to be the same image."""
    import numpy as np
    from medscope.data.quality import correlation
    from medscope.data.views import load_image
    by_key = {r.key: r for r in recs}
    mine_test = {k: p for k, p in test_keys.items() if k.startswith(name) and k[len(name):].isdigit()}
    mine_seen = {k: p for k, p in seen_keys.items() if k.startswith(name) and k[len(name):].isdigit()}
    missing = [k for k in mine_test if k not in by_key]
    checked = [k for k in mine_test if k in by_key]
    differ = [k for k in checked if correlation(load_image(by_key[k].image_path), load_image(mine_test[k])) < 0.99]
    if len(missing) > 0.05 * max(1, len(mine_test)) or len(differ) > 0.02 * max(1, len(checked)):
        raise SystemExit(f"{name}: {len(missing)} existing test images are not in the source any more and {len(differ)} "
                         f"of {len(checked)} differ: the source data changed; stop and report this.")
    test_groups = {by_key[k].group for k in checked}
    seen_groups = {by_key[k].group for k in mine_seen if k in by_key} | test_groups
    kept = [r for r in recs if r.group not in test_groups]
    line = (f"{name}: {len(checked)} existing test images found ({len(differ)} differ, {len(missing)} no longer read); "
            f"their {len(test_groups)} patients/groups "
            f"({len(recs) - len(kept)} images) removed from every v4 split; {len(seen_groups)} groups seen before are "
            f"kept out of the fresh set")
    return kept, frozenset(seen_groups), line


# sources split by patient: unused test-split patients give a clean fresh set (BUSI is split by near-copy groups,
# so its leftover images could come from patients already in the test set)
FRESH_SOURCES = ("chestxdet", "lgg")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True, help="where the parquet files are downloaded")
    ap.add_argument("--datasets", nargs="+", default=list(extra.DATASETS), choices=list(extra.DATASETS))
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--v4", action="store_true",
                    help="v4 data: every training image, 100+100 validation images per dataset, the same test images, "
                         "and a fresh confirmatory test set (cases_fresh.jsonl) from test-split patients not yet used")
    ap.add_argument("--fresh", type=int, nargs=2, default=(60, 40), metavar=("LESION", "NEGATIVE"))
    ap.add_argument("--protect-test", nargs="*", default=[],
                    help="v4: views files of the EXISTING test set. Every patient (group) holding one of their images is "
                         "removed from the new splits, so v4 trains, selects and confirms on none of them")
    ap.add_argument("--protect-seen", nargs="*", default=[],
                    help="v4: views files of earlier training/validation images; their patients are kept out of the fresh set")
    args = ap.parse_args()
    test_keys, seen_keys = protected_keys(args.protect_test), protected_keys(args.protect_seen)

    out = Path(args.out)
    for p in [*out.glob("cases_*.jsonl"), out / "negatives"]:
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, name in enumerate(args.datasets):
        spec = extra.DATASETS[name]
        print(f"{name}: downloading {spec['repo']}", flush=True)
        files = extra.download(spec["repo"], Path(args.cache))
        recs, stats = extra.scan(name, extra.iter_parquet_rows(files), out / "images")
        kinds = __import__("collections").Counter(r.negative for r in recs)
        if not kinds[True] or not kinds[False]:
            raise SystemExit(f"{name}: {kinds[False]} lesion images and {kinds[True]} lesion-free images were found; "
                             f"the dataset layout may have changed ({dict(stats)})")
        # the split seed depends on the dataset name only, so preparing a subset gives the same splits
        excluded = frozenset()
        if test_keys or seen_keys:
            recs, excluded, line = protect(name, recs, test_keys, seen_keys)
            lines.append(line)
            print(line, flush=True)
        splits = extra.split_and_cap(recs, seed=args.seed + stable_index(name, 1000), fresh_exclude=excluded,
                                     caps=extra.CAPS_V4 if args.v4 else None,
                                     fresh=tuple(args.fresh) if args.v4 and name in FRESH_SOURCES else None)
        counts = extra.write_outputs(splits, out)
        lines += [f"{name} ({spec['repo']}): {dict(stats)}",
                  f"{name} labels: {dict(__import__('collections').Counter(r.label for r in recs))}",
                  f"{name} per split: {counts}"]
        print("\n".join(lines[-3:]), flush=True)
    (out / "extra_report.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
