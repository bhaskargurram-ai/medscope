"""Figure 4 of the manuscript (fig:natural): unedited same-video colonoscopy pairs.

Two panels, one point per model: x = share of lesion frames found, y = share of lesion-free frames answered
"absent" or referred. Natural ESG = y - (1 - x), so models on the same grey diagonal have the same natural ESG.

Every number below is copied, unchanged, from the consolidated report
    report60.md  ("MedScope report - 60 consolidated model v6 (R24-R27)")
The section and table row of each value are named in the data block. Nothing is computed, re-rounded or
estimated here; the diagonals are the definition of natural ESG, not data.

Drawn at the printed size (full text width, 7.16 in), 7 pt sans-serif, so LaTeX does not rescale it.

    python make_fig4_natural.py [--preview DIR]     # writes fig4_natural_pairs.pdf next to this script
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parent
W = 7.16  # full text width, inches

BLUE = "#4477AA"     # MedScope models (Paul Tol "bright" blue, as in Figures 2 and 3)
NEUTRAL = "#444444"  # reference models and the base model
INK, MUTED, ISO = "#222222", "#555555", "#C9C9C9"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})

# ----------------------------------------------------------------------------------------------------------------------
# DATA. Columns: lesion found (%), lesion-free image: says absent or refers (%), natural ESG, 95% CI low, high.
#
# Panel a. Source: report60.md, section "R27: REAL-Colon pairs, cross-validated", first table (103 pairs).
#   row "MedScope-4B-v6-CV" -> MedScope-4B-N (cross-validated: each pair answered by the copy trained without its video)
#   row "MedScope-4B"       -> MedScope-4B
#   row "Qwen3.5-4B"        -> Qwen3.5-4B (base)
#   rows "gemini-4-argon", "claude-opus-5-5", "gpt-6-astra" -> the three reference models
#   Not plotted: rows "MedScope-v5-CV" and "MedScope-v4.2".
REALCOLON = {
    "MedScope-4B-N":     (64.1, 89.3, 0.534, 0.394, 0.661),
    "MedScope-4B":       (37.9, 86.4, 0.243, 0.149, 0.340),
    "Qwen3.5-4B (base)": (38.8, 85.4, 0.243, 0.143, 0.350),
    "gemini-4-argon":    (68.0, 78.6, 0.466, 0.336, 0.581),
    "claude-opus-5-5":   (70.9, 73.8, 0.447, 0.317, 0.579),
    "gpt-6-astra":       (64.1, 68.0, 0.320, 0.212, 0.437),
}
# Panel b. Source: report60.md, section "R26: LDPolypVideo natural pairs (a hospital no model here has seen)",
# first table (116 pairs from 160 clips).
#   row "MedScope-4B-v6" -> MedScope-4B-N (the single model, seed 0)
#   row "v6-vote"        -> three-seed majority vote of MedScope-4B-N (small marker)
#   row "MedScope-4B"    -> MedScope-4B
#   row "Qwen3.5-4B"     -> Qwen3.5-4B (base)
#   rows "gemini-4-argon", "claude-opus-5-5", "gpt-6-astra" -> the three reference models
#   Not plotted: rows "v6-seed1", "v6-seed2" and "MedScope-v5".
LDPOLYP = {
    "MedScope-4B-N":     (62.1, 99.1, 0.612, 0.526, 0.698),
    "three-seed vote":   (61.2, 97.4, 0.586, 0.491, 0.673),
    "MedScope-4B":       (45.7, 96.6, 0.422, 0.328, 0.517),
    "Qwen3.5-4B (base)": (40.5, 95.7, 0.362, 0.276, 0.448),
    "gemini-4-argon":    (71.6, 81.0, 0.526, 0.422, 0.621),
    "claude-opus-5-5":   (62.9, 83.6, 0.466, 0.362, 0.569),
    "gpt-6-astra":       (55.2, 75.0, 0.302, 0.198, 0.405),
}
# ----------------------------------------------------------------------------------------------------------------------

# marker, size (pt^2), edge colour, filled?
STYLE = {
    "MedScope-4B-N":     ("o", 62, BLUE, True),
    "three-seed vote":   ("o", 13, BLUE, True),
    "MedScope-4B":       ("o", 34, BLUE, False),
    "Qwen3.5-4B (base)": ("v", 34, NEUTRAL, False),
    "gemini-4-argon":    ("s", 30, NEUTRAL, True),
    "claude-opus-5-5":   ("D", 26, NEUTRAL, True),
    "gpt-6-astra":       ("^", 34, NEUTRAL, True),
}
# label placement: (dx, dy) in points from the mark, horizontal alignment, vertical alignment
PLACE_A = {
    "MedScope-4B-N":     (0, 8, "center", "bottom"),
    "MedScope-4B":       (-1, 7, "center", "bottom"),
    "Qwen3.5-4B (base)": (0, -7, "center", "top"),
    "gemini-4-argon":    (-7, 0, "right", "center"),
    "claude-opus-5-5":   (-7, 0, "right", "center"),
    "gpt-6-astra":       (-7, 0, "right", "center"),
}
PLACE_B = {
    "MedScope-4B-N":     (7, 3, "left", "center"),
    "three-seed vote":   (0, -26, "center", "top"),
    "MedScope-4B":       (4, 6, "center", "bottom"),
    "Qwen3.5-4B (base)": (-4, -7, "center", "top"),
    "gemini-4-argon":    (0, -7, "center", "top"),
    "claude-opus-5-5":   (-7, 0, "right", "center"),
    "gpt-6-astra":       (-7, 0, "right", "center"),
}
XLIM, YLIM = (26, 84), (60, 104)
ISO_LEVELS = (0.2, 0.3, 0.4, 0.5, 0.6)  # natural ESG = (x + y) / 100 - 1
HALO = [pe.withStroke(linewidth=2.0, foreground="white")]


def iso_lines(ax):
    for e in ISO_LEVELS:
        s = 100 * (1 + e)  # x + y on this line
        x0 = max(XLIM[0], s - 100)  # no share exceeds 100%
        ax.plot([x0, XLIM[1]], [s - x0, s - XLIM[1]], color=ISO, lw=0.6, zorder=1, clip_on=True)
        # label near the lower right end of the line, inside the axes
        x = min(XLIM[1] - 2.2, s - YLIM[0] - 2.2)
        txt = f"natural ESG {e:.1f}" if e == ISO_LEVELS[-1] else f"{e:.1f}"
        ax.text(x, s - x, txt, rotation=-45, rotation_mode="anchor", ha="right", va="center", fontsize=7,
                color=MUTED, zorder=2, bbox=dict(facecolor="white", edgecolor="none", pad=0.8))


def panel(ax, data, place, letter, title):
    iso_lines(ax)
    for name, (found, safe, esg, lo, hi) in data.items():
        mk, size, col, filled = STYLE[name]
        ax.scatter(found, safe, s=size, marker=mk, facecolor=col if filled else "white", edgecolor=col,
                   linewidth=1.1 if not filled else 0.6, zorder=4 if name == "MedScope-4B-N" else 3)
        dx, dy, ha, va = place[name]
        bold = name == "MedScope-4B-N"
        shown = name + (", cross-validated" if (bold and letter == "a") else "")
        ax.annotate(f"{shown}\n{esg:.3f} [{lo:.3f}, {hi:.3f}]", (found, safe), xytext=(dx, dy),
                    textcoords="offset points", ha=ha, va=va, fontsize=7, color=INK, linespacing=1.15,
                    fontweight="bold" if bold else "normal", path_effects=HALO, zorder=5,
                    arrowprops=(dict(arrowstyle="-", lw=0.5, color=MUTED, shrinkA=0, shrinkB=2.5)
                                if name == "three-seed vote" else None))
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_aspect("equal")
    ax.set_xticks(range(30, 81, 10))
    ax.set_yticks(range(60, 101, 10))
    ax.spines["left"].set_bounds(60, 100)
    ax.set_xlabel("Polyp frames found (%)")
    ax.text(0.0, 1.03, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left")
    ax.text(0.065, 1.03, title, transform=ax.transAxes, fontsize=7, va="bottom", ha="left", color=INK)


def main():
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 3.05))
    fig.subplots_adjust(left=0.085, right=0.995, bottom=0.125, top=0.93, wspace=0.14)
    panel(a, REALCOLON, PLACE_A, "a", "REAL-Colon, 103 unedited same-video pairs")
    panel(b, LDPOLYP, PLACE_B, "b", "LDPolypVideo, 116 pairs, a hospital not used in training")
    a.set_ylabel("Polyp-free frames answered\nabsent or referred (%)")
    a.text(27.5, 61.2, "Under each name:\nnatural ESG [95% CI]", fontsize=7, color=MUTED, ha="left", va="bottom",
           linespacing=1.15)
    fig.savefig(OUT / "fig4_natural_pairs.pdf")
    if "--preview" in sys.argv:
        d = Path(sys.argv[sys.argv.index("--preview") + 1])
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / "fig4_natural_pairs.png", dpi=200)
    print("wrote", OUT / "fig4_natural_pairs.pdf")


if __name__ == "__main__":
    main()
