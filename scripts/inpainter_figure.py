"""Figure: the same lesion erased by each inpainting tool (one test case per imaging type).

    python scripts/inpainter_figure.py --views TEST_VIEWS... --variant telea=DIR/views.jsonl \
        --variant transplant=DIR/views.jsonl --out RESULTS/figures
Writes inpainters.png and inpainters.pdf.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.colab import dataset_of  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--variant", action="append", default=[], help='"name=views.jsonl" from reinpaint_views.py')
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", default="figure")
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    orig, lama = {}, {}
    for v in (v for f in args.views for v in load_views(f)):
        if v.kind.value == "original":
            orig[v.case_id] = v
        elif v.kind.value == "target_removal":
            lama[v.case_id] = v
    variants = []
    for spec in args.variant:
        name, path = spec.split("=", 1)
        if Path(path).exists():
            variants.append((name, {v.case_id: v for v in load_views(path) if v.kind.value == "target_removal"}))
    common = set(orig) & set(lama)
    for _, d in variants:
        common &= set(d)
    rows = []
    for ds in sorted({dataset_of(c) for c in common}):
        cs = sorted((c for c in common if dataset_of(c) == ds), key=lambda c: stable_index(c + args.seed, 10 ** 9))
        rows.append((ds, cs[0]))
    cols = [("Original", orig), ("LaMa (training tool)", lama)] + [(n.capitalize(), d) for n, d in variants]
    fig, axes = plt.subplots(len(rows), len(cols), figsize=(2.0 * len(cols), 2.0 * len(rows)), squeeze=False,
                             gridspec_kw={"wspace": 0.03, "hspace": 0.06})
    for r, (ds, case) in enumerate(rows):
        for c, (title, d) in enumerate(cols):
            ax = axes[r][c]
            ax.set_xticks([]), ax.set_yticks([])
            v = d[case]
            img = load_image(v.image_path)
            h, w = img.shape[:2]
            ax.imshow(img, aspect="auto")
            box = v.lesion_box if c == 0 else (v.meta or {}).get("edit_box")
            if box:
                x1, y1, x2, y2 = [b / 1000 for b in box]
                ax.add_patch(Rectangle((x1 * w, y1 * h), (x2 - x1) * w, (y2 - y1) * h, fill=False, lw=1.0,
                                       ls="-" if c == 0 else "--", ec="#ffcc00" if c == 0 else "#00e5ff"))
            if r == 0:
                ax.set_title(title, fontsize=9)
            if c == 0:
                ax.set_ylabel(ds.split(" (")[0], fontsize=8)
    fig.subplots_adjust(left=0.04, right=0.995, top=0.95, bottom=0.01)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"inpainters.{ext}", dpi=200)
    print(f"wrote {out}/inpainters.png and .pdf ({len(rows)} imaging types, {len(cols)} columns)")


if __name__ == "__main__":
    main()
