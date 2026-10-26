"""Build the four views for every case in a JSONL manifest.

Each manifest line is a Case (see medscope/data/schema.py). Output: one folder of
PNGs per case plus views.jsonl, and a dropped.jsonl listing cases skipped because
no valid random-removal control could be placed.

Usage:
    python scripts/build_views.py --manifest cases.jsonl --out data/views/slake --seed 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.schema import Case  # noqa: E402
from medscope.data.views import build_views, load_image  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = [Case.from_dict(json.loads(line)) for line in open(args.manifest) if line.strip()]

    kept = dropped = 0
    with open(out / "views.jsonl", "w") as vf, open(out / "dropped.jsonl", "w") as df:
        for i, case in enumerate(cases):
            # A mismatch distractor: an image from a different patient, if any.
            other = next((c for c in cases[i + 1:] + cases[:i] if c.patient_id != case.patient_id), None)
            other_img = load_image(other.image_path) if other else None
            try:
                views = build_views(case, out, rng, other_image=other_img)
            except ValueError as exc:
                views, reason = [], str(exc)
            else:
                reason = "no valid random-removal position"
            if not views:
                df.write(json.dumps({"case_id": case.case_id, "reason": reason}) + "\n")
                dropped += 1
                continue
            for v in views:
                vf.write(json.dumps(v.to_dict()) + "\n")
            kept += 1
    print(f"built views for {kept} cases, dropped {dropped}; output in {out}")


if __name__ == "__main__":
    main()
