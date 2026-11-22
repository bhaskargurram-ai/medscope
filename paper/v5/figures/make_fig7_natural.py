"""Figure 7 of the manuscript: natural (unedited) same-patient colonoscopy pairs, R9 and R16.

Every number is copied from docs/RESULTS_LOG.md (entries of 21 and 22 Nov 2026: R9 result, R9 per-pair breakdown,
R16 result) and RESULTS/54b_v5_natural_pairs_in_training_(r16)_report.md. Nothing is estimated.
Style as the other figures (paper/v3/figures/make_figures.py): drawn at printed size, 7 pt sans-serif, Paul Tol
"bright" colours with the same colour per model as Figures 2 and 6; every model is also named next to its mark, so
no reading depends on colour.

    python paper/v5/figures/make_fig7_natural.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parent
W = 7.22  # elsarticle 5p text width, inches

C = {"MedScope": "#4477AA", "gemini-4-argon": "#EE6677", "Claude Opus 5.5": "#AA3377", "gpt-6-astra": "#66CCEE",
     "base": "#9A9A9A"}
INK, MUTED = "#222222", "#666666"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "axes.spines.top": False, "axes.spines.right": False,
    "grid.linewidth": 0.4, "grid.color": "#E6E6E6", "axes.axisbelow": True, "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
})

# name, colour key, marker, filled; 103 pairs: polyp not denied %, lesion-free safe %, natural ESG, lo, hi;
# 96 pairs with a context frame: natural ESG, lo, hi; called present, present with a correct box (of 103)
MODELS = [
    ("v5 (natural pairs, cross-validated)", "MedScope", "o", True, 63.1, 92.2, 0.553, 0.430, 0.670, 0.500, 0.367, 0.629, 65, 53),
    ("gemini-4-argon", "gemini-4-argon", "s", True, 68.0, 78.6, 0.466, 0.336, 0.581, 0.333, 0.211, 0.458, 69, 52),
    ("Claude Opus 5.5", "Claude Opus 5.5", "D", True, 70.9, 73.8, 0.447, 0.317, 0.579, 0.323, 0.177, 0.466, 73, 50),
    ("gpt-6-astra", "gpt-6-astra", "^", True, 64.1, 68.0, 0.320, 0.212, 0.437, 0.188, 0.033, 0.353, 66, 41),
    ("MedScope-4B (pre-registered)", "MedScope", "o", False, 37.9, 86.4, 0.243, 0.149, 0.340, 0.208, 0.089, 0.333, 36, 32),
    ("Qwen3.5-4B (untrained base)", "base", "v", True, 38.8, 85.4, 0.243, 0.143, 0.350, 0.188, 0.032, 0.346, 40, 13),
]


def label(ax, s, x=-0.14, y=1.05):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left")


def face(key, filled):
    return C[key] if filled else "white"


fig = plt.figure(figsize=(W, 2.15))
a = fig.add_axes([0.075, 0.20, 0.20, 0.66])
b = fig.add_axes([0.452, 0.20, 0.235, 0.66])
c = fig.add_axes([0.745, 0.20, 0.215, 0.66])

# (a) the two halves of natural ESG
for name, key, mk, filled, found, safe, *_ in MODELS:
    a.scatter(found, safe, s=26, marker=mk, facecolor=face(key, filled), edgecolor=C[key], linewidth=1.0, zorder=3)
a.annotate("", xy=(61.4, 91.8), xytext=(39.8, 87.0), zorder=2,
           arrowprops=dict(arrowstyle="-|>", color=C["MedScope"], lw=0.8, shrinkA=0, shrinkB=0))
NOTES = {"v5 (natural pairs, cross-validated)": ("v5", 0.0, 3.0, "center"),
         "gemini-4-argon": ("gemini-4-argon", -2.4, 0.0, "right"), "Claude Opus 5.5": ("Claude Opus 5.5", -2.4, 0.0, "right"),
         "gpt-6-astra": ("gpt-6-astra", -2.4, 0.0, "right"), "MedScope-4B (pre-registered)": ("MedScope-4B", 2.0, 3.6, "center"),
         "Qwen3.5-4B (untrained base)": ("base", 0.0, -3.2, "center")}
for name, key, mk, filled, found, safe, *_ in MODELS:
    text, dx, dy, ha = NOTES[name]
    a.text(found + dx, safe + dy, text, fontsize=6.5, color=INK, ha=ha, va="center")
a.set_xlim(28, 80)
a.set_ylim(60, 100)
a.set_xlabel("Real polyp: not denied (%)")
a.set_ylabel("Polyp-free frame: answered\nabsent or referred (%)")
a.grid(True)
a.set_title("Both halves of the gap")
label(a, "a", x=-0.34)

# (b) natural ESG with 95% intervals, against the paired frame and against the context frame
ys = list(range(len(MODELS)))[::-1]
SHORT = ["v5 (cross-validated)", "gemini-4-argon", "Claude Opus 5.5", "gpt-6-astra", "MedScope-4B", "Qwen3.5-4B (base)"]
for y, (name, key, mk, filled, _, _, e, lo, hi, e2, lo2, hi2, *_) in zip(ys, MODELS):
    b.plot([lo, hi], [y + 0.16, y + 0.16], color=C[key], lw=1.2, solid_capstyle="round", zorder=2)
    b.scatter(e, y + 0.16, s=22, marker=mk, facecolor=face(key, filled), edgecolor=C[key], linewidth=1.0, zorder=3)
    b.plot([lo2, hi2], [y - 0.18, y - 0.18], color=MUTED, lw=0.8, solid_capstyle="round", zorder=2)
    b.scatter(e2, y - 0.18, s=12, marker="x", color=MUTED, linewidth=0.9, zorder=3)
    b.text(hi + 0.02, y + 0.16, f"{e:.2f}", fontsize=6.5, color=INK, va="center", ha="left")
b.set_yticks(ys)
b.set_yticklabels(SHORT)
b.set_xlim(0, 0.8)
b.set_ylim(-0.6, len(MODELS) - 0.4)
b.set_xlabel("Natural ESG (95% CI)")
b.grid(True, axis="x")
b.tick_params(axis="y", length=0)
b.set_title("Natural ESG")
label(b, "b", x=-0.62)

# (c) grounded detection: called present, and present with a correct box (same rows as b)
for y, (name, key, mk, filled, *_rest, present, boxed) in zip(ys, MODELS):
    c.barh(y, present, height=0.58, color=C[key], alpha=0.30, linewidth=0, zorder=2)
    c.barh(y, boxed, height=0.58, color=C[key] if filled else "white", edgecolor=C[key], linewidth=0.8, zorder=3)
    c.text(present + 1.5, y, f"{boxed} / {present}", fontsize=6.5, color=INK, va="center", ha="left")
c.set_yticks(ys)
c.set_yticklabels([])
c.set_xlim(0, 103)
c.set_ylim(-0.6, len(MODELS) - 0.4)
c.set_xlabel("Polyp frames called present (of 103)")
c.grid(True, axis="x")
c.tick_params(axis="y", length=0)
c.set_title("Polyp found and located")
label(c, "c", x=-0.10)

fig.savefig(OUT / "fig7_natural_pairs.pdf")
fig.savefig(OUT / "fig7_natural_pairs.png", dpi=300)
print("wrote", OUT / "fig7_natural_pairs.pdf")
