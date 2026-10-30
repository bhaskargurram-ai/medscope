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

from medscope.data.inpaint import get_inpainter  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.schema import Case  # noqa: E402
from medscope.data.views import build_views, load_image  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--inpainter", choices=["telea", "lama"], default="telea",
                    help="use lama for real builds (needs torch; fast on a GPU)")
    args = ap.parse_args()
    inpaint_fn = get_inpainter(args.inpainter)

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = [Case.from_dict(json.loads(line)) for line in open(args.manifest) if line.strip()]

    modalities = sorted({c.modality for c in cases})
    others = {m: [c for c in cases if c.modality != m] for m in modalities}

    def by_modality_except(m: str) -> list[Case]:
        return others[m]

    kept = dropped = 0
    with open(out / "views.jsonl", "w") as vf, open(out / "dropped.jsonl", "w") as df:
        for i, case in enumerate(cases):
            # A mismatch distractor: an image of a different imaging type (and patient), so the image
            # really cannot answer the question; without one, this case gets another degradation
            pool = by_modality_except(case.modality)
            other = pool[stable_index(case.case_id, len(pool))] if pool else None
            other_img = load_image(other.image_path) if other else None
            try:
                views = build_views(case, out, rng, other_image=other_img, inpaint_fn=inpaint_fn,
                                    other_modality=other.modality if other else None)
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
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(cases)} cases processed", flush=True)
    print(f"built views for {kept} cases, dropped {dropped}; output in {out}")


if __name__ == "__main__":
    main()
