"""Figure of real example views: for each imaging type, one test case shown as original, lesion erased,
same-size edit elsewhere, degraded, plus a lesion-free image of the same source. The lesion is outlined
on the original; the edited region is outlined (dashed) on the two edited views.

Usage:
    python scripts/example_figure.py --views TEST_VIEWS... --negatives TEST_NEG... --out RESULTS/figures/examples
Writes examples.png and examples.pdf.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.colab import dataset_of  # noqa: E402
from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.schema import ViewKind  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

COLUMNS = [("original", "Original"), ("target_removal", "Lesion erased"), ("random_removal", "Same-size edit elsewhere"),
           ("degraded", "Degraded"), ("natural_negative", "Lesion-free image")]


def draw_box(ax, box, w, h, dashed=False, color="#ffcc00"):
    from matplotlib.patches import Rectangle
    if not box:
        return
    x1, y1, x2, y2 = [c / 1000 for c in box]
    ax.add_patch(Rectangle((x1 * w, y1 * h), (x2 - x1) * w, (y2 - y1) * h, fill=False, lw=1.2,
                           ls="--" if dashed else "-", ec=color))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", default="figure")
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    views = [v for f in args.views for v in load_views(f)]
    negs = [v for f in args.negatives for v in load_views(f)]
    by_case: dict[str, dict] = {}
    for v in views:
        by_case.setdefault(v.case_id, {})[v.kind.value] = v
    complete = {c: d for c, d in by_case.items() if all(k in d for k, _ in COLUMNS[:4])}
    rows = []
    for ds in sorted({dataset_of(c) for c in complete}):
        cases = sorted((c for c in complete if dataset_of(c) == ds), key=lambda c: stable_index(c + args.seed, 10 ** 9))
        pool = sorted((n for n in negs if dataset_of(n.case_id) == ds), key=lambda n: stable_index(n.view_id + args.seed, 10 ** 9))
        if cases:
            rows.append((ds, complete[cases[0]], pool[0] if pool else None))

    fig, axes = plt.subplots(len(rows), len(COLUMNS), figsize=(2.0 * len(COLUMNS), 2.0 * len(rows)),
                             gridspec_kw={"wspace": 0.03, "hspace": 0.06})
    for r, (ds, d, neg) in enumerate(rows):
        for c, (kind, title) in enumerate(COLUMNS):
            ax = axes[r][c]
            ax.set_xticks([]), ax.set_yticks([])
            v = neg if kind == "natural_negative" else d.get(kind)
            if v is None:
                ax.axis("off")
                continue
            img = load_image(v.image_path)
            h, w = img.shape[:2]
            ax.imshow(img, cmap="gray" if img.ndim == 2 else None, aspect="auto")
            if v.kind is ViewKind.ORIGINAL:
                draw_box(ax, v.lesion_box, w, h)
            elif v.kind in (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL):
                draw_box(ax, (v.meta or {}).get("edit_box"), w, h, dashed=True, color="#00e5ff")
            if r == 0:
                ax.set_title(title, fontsize=9)
            if c == 0:
                ax.set_ylabel(ds.split(" (")[0], fontsize=8)
            if v.kind is ViewKind.DEGRADED:
                ax.text(0.02, 0.98, (v.meta or {}).get("degradation", ""), transform=ax.transAxes, fontsize=7,
                        va="top", color="white", bbox=dict(fc="black", alpha=0.5, lw=0))
        axes[r][0].text(0.02, 0.02, d["original"].question, transform=axes[r][0].transAxes, fontsize=6,
                        color="white", bbox=dict(fc="black", alpha=0.5, lw=0), wrap=True)
    fig.subplots_adjust(left=0.04, right=0.995, top=0.96, bottom=0.01)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"examples.{ext}", dpi=200)
    print(f"wrote {out}/examples.png and .pdf ({len(rows)} imaging types)")


if __name__ == "__main__":
    main()
