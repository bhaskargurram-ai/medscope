"""Figures 2 and 3 and supplementary figures S (designs, site probes, readers and prompts) of manuscript v6.

This is make_figures_v3.py with the LABELS changed to the names fixed for v6. Every plotted number is the one in
make_figures_v3.py, unchanged (that script copied them from docs/RESULTS_LOG.md and the preprint; the source table
is named next to each block). Nothing is estimated, interpolated or re-rounded. Label changes are listed in
README.md.

Style: figures are drawn at their printed size (full text width, 7.16 in) so no scaling happens in LaTeX; 7 pt
sans-serif, 0.5 pt lines; Paul Tol's colour-blind-safe "bright" palette; bars start at zero; panel letters bold
lower case, 8 pt.

    python make_figures_v6.py [--preview DIR]      # PDFs are written next to this script; PNG previews to DIR
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = Path(__file__).resolve().parent
PREVIEW = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
W = 7.16  # full text width, inches

# Paul Tol "bright", keys kept from the earlier palette so every figure maps over
OK = {"orange": "#CCBB44", "sky": "#66CCEE", "green": "#228833", "yellow": "#CCBB44", "blue": "#4477AA",
      "verm": "#EE6677", "purple": "#AA3377", "black": "#000000", "grey": "#9A9A9A", "light": "#DDDDDD"}
MODEL_C = {"MedScope-4B": OK["blue"], "gemini-4-argon": OK["verm"], "claude-opus-5-5": OK["purple"],
           "gpt-6-astra": OK["sky"]}
FS = 7  # smallest type used anywhere

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "axes.spines.top": False, "axes.spines.right": False,
    "lines.markersize": 3, "grid.linewidth": 0.4, "grid.color": "#E6E6E6", "axes.axisbelow": True,
    "legend.handlelength": 1.2, "legend.borderaxespad": 0.3,
    "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 1.0,
})


def label(ax, s, x=-0.12, y=1.06):
    ax.text(x, y, s.lower(), transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left")


def save(fig, name):
    """Save at exactly the printed width W: the figure is widened until its drawn content (axes, labels, legends)
    spans W, so the type is not rescaled when LaTeX sets the file to the text width."""
    from matplotlib.transforms import Bbox
    pad = 0.02
    for _ in range(4):
        fig.canvas.draw()
        tb = fig.get_tightbbox(fig.canvas.get_renderer())
        w, h = fig.get_size_inches()
        fig.set_size_inches(w + (W - 2 * pad - tb.width), h)
    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())
    cx = (tb.x0 + tb.x1) / 2
    box = Bbox.from_extents(cx - W / 2, tb.y0 - pad, cx + W / 2, tb.y1 + pad)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches=box)
    if PREVIEW is not None:
        PREVIEW.mkdir(parents=True, exist_ok=True)
        fig.savefig(PREVIEW / f"{name}.png", dpi=200, bbox_inches=box)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------------------------
# Figure 2: main test (log Table 1) and by imaging type (log Table 2)
MAIN = [  # model, group, lesion images correct, ESG, erased-lesion claims %, lesion-free claims %, net utility
    ("MedScope-4B", "medscope", 0.849, 0.758, 9.6, 7.6, 0.732),
    ("gemini-4-argon", "comparison", 0.874, 0.470, 41.1, 9.0, 0.565),
    ("Claude Sonnet 5.5", "comparison", 0.870, 0.402, 48.4, 16.7, 0.381),          # names in this block are not drawn
    ("gemini-3.1-pro-preview", "comparison", 0.849, 0.384, 51.6, 26.7, 0.306),     # unless annotated in fig2()
    ("gpt-6-sol", "comparison", 0.829, 0.342, 51.6, 25.7, 0.261),
    ("Claude Fable 5.1", "comparison", 0.856, 0.342, 52.1, 23.3, 0.255),
    ("claude-opus-5-5", "comparison", 0.863, 0.329, 53.9, 23.6, 0.358),
    ("gpt-6.1-sol", "comparison", 0.888, 0.324, 58.9, 30.9, 0.276),
    ("gpt-6-astra", "comparison", 0.886, 0.306, 58.9, 27.8, 0.309),
    ("gemini-3.8-flash", "comparison", 0.868, 0.269, 61.6, 27.8, 0.263),
    ("Lingshu-7B", "open", 0.527, 0.416, 32.0, 12.5, -0.249),
    ("Qwen3.5-4B (base)", "open", 0.758, 0.338, 42.0, 19.4, 0.134),
    ("Qwen3-VL-8B", "open", 0.553, 0.297, 12.8, 12.5, 0.186),
    ("MedGemma 1.5 4B", "open", 0.674, 0.283, 54.3, 24.0, -0.255),
    ("HuatuoGPT-Vision-7B", "open", 0.498, 0.265, 30.1, 22.9, -0.426),
    ("Qwen2.5-VL-7B", "open", 0.144, 0.146, 5.5, 24.7, -0.742),
    ("Always claims", "constant", 1.0, 0.0, 100.0, 100.0, -0.478),
    ("Always absent", "constant", 0.0, 0.0, 0.0, 0.0, -0.848),
    ("Always refers", "constant", 0.0, 0.0, 0.0, 0.0, 0.110),
]
TYPES = ["Colono-\nscopy", "Brain\nMRI", "Breast\nUS", "Chest\nX-ray", "SLAKE\nCT/MRI"]
BYTYPE = {  # ESG, erased fraction (log Table 2)
    "MedScope-4B": ([0.95, 0.75, 0.74, 0.51, 0.47], [0.01, 0.14, 0.14, 0.17, 0.12]),
    "gemini-4-argon": ([0.69, 0.42, 0.40, 0.20, 0.35], [0.31, 0.47, 0.48, 0.49, 0.41]),
    "claude-opus-5-5": ([0.57, 0.31, 0.29, -0.05, 0.24], [0.40, 0.61, 0.62, 0.66, 0.59]),
    "gpt-6-astra": ([0.40, 0.50, 0.12, 0.15, 0.29], [0.58, 0.31, 0.83, 0.66, 0.47]),
}


def fig2():
    fig = plt.figure(figsize=(W, 2.75))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1], hspace=0.55, wspace=0.28)
    ax = fig.add_subplot(gs[:, 0])
    style = {"medscope": dict(marker="*", s=90, c=OK["blue"], zorder=5),
             "comparison": dict(marker="o", s=18, c=OK["verm"]),
             "open": dict(marker="D", s=14, c=OK["green"]), "constant": dict(marker="^", s=16, c=OK["grey"])}
    for g in style:
        pts = [(m[4], m[3]) for m in MAIN if m[1] == g]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], edgecolor="white", linewidth=0.4, **style[g])
    ax.errorbar(9.6, 0.758, yerr=[[0.758 - 0.701], [0.815 - 0.758]], xerr=[[9.6 - 6.1], [13.7 - 9.6]],
                fmt="none", ecolor=OK["blue"], elinewidth=0.7, capsize=1.5, zorder=4)
    ax.annotate("MedScope-4B", (9.6, 0.758), xytext=(15, 0.715), fontsize=FS, color=OK["blue"], fontweight="bold")
    ax.annotate("Qwen3.5-4B (base)", (42.0, 0.338), xytext=(19, 0.20), fontsize=FS,
                arrowprops=dict(arrowstyle="-", lw=0.4, color="0.4"))
    ax.annotate("Qwen2.5-VL-7B\n(lesion images correct 0.14)", (5.5, 0.146), xytext=(10, 0.058), fontsize=FS,
                linespacing=1.1, arrowprops=dict(arrowstyle="-", lw=0.4, color="0.4", relpos=(0.0, 1.0)))
    ax.annotate("gemini-4-argon", (41.1, 0.470), xytext=(22, 0.53), fontsize=FS,
                arrowprops=dict(arrowstyle="-", lw=0.4, color="0.4"))
    ax.text(64, 0.345, "nine comparison\nmodels", fontsize=FS, color="0.2", ha="left", va="center")
    ax.text(88, 0.035, "always\nclaims", fontsize=FS, color="0.35", ha="center")
    ax.text(3, 0.012, "always absent / refers", fontsize=FS, color="0.35", ha="left")
    ax.set_xlim(-3, 103)
    ax.set_ylim(-0.02, 0.84)
    ax.set_xlabel("Erased-lesion claims (% of 219 erased views)")
    ax.set_ylabel("Evidence sensitivity gap (ESG)")
    ax.legend(handles=[Line2D([], [], ls="", marker="*", ms=5.5, color=OK["blue"], label="MedScope-4B (95% CI)"),
                       Line2D([], [], ls="", marker="o", ms=4, color=OK["verm"], label="Comparison models (9)"),
                       Line2D([], [], ls="", marker="D", ms=3.5, color=OK["green"], label="Open-weight models (6)"),
                       Line2D([], [], ls="", marker="^", ms=4, color=OK["grey"], label="Constant strategies")],
              loc="upper right", bbox_to_anchor=(1.02, 1.0), handletextpad=0.3, borderaxespad=0.2)
    ax.set_title("Main test: 507 cases, 1,115 views", fontweight="normal")
    label(ax, "A")
    x = np.arange(len(TYPES))
    wdt = 0.2
    for r, (key, idx) in enumerate((("ESG", 0), ("Erased-lesion claims", 1))):
        a = fig.add_subplot(gs[r, 1])
        for k, (m, v) in enumerate(BYTYPE.items()):
            a.bar(x + (k - 1.5) * wdt, v[idx], wdt, color=MODEL_C[m], label=m, linewidth=0)
        a.axhline(0, color="0.2", lw=0.5)
        a.set_xticks(x)
        a.set_xticklabels(TYPES if r == 1 else [""] * 5, fontsize=FS)
        a.set_ylabel(key + (" (fraction)" if idx else ""))
        a.set_ylim(-0.1 if idx == 0 else 0, 1.0)
        if r == 0:
            a.legend(ncol=2, loc="upper right", bbox_to_anchor=(1.02, 1.36), columnspacing=0.8, handlelength=1)
            label(a, "B", x=-0.18, y=1.12)
    save(fig, "fig2_main_test")


# ---------------------------------------------------------------------------------------------------------------------
# Figure 3: editing tools (log Table 5), factorial (log Table 4), first-stage training variants (log Table 3)
TOOLS = ["LaMa\n(training)", "Transplant\n(training)", "TELEA\n(held out)", "Diffusion\n(held out)"]
BYTOOL = [  # ESG on 125 cases
    ("MedScope-4B", [0.752, 0.720, 0.664, 0.640]),
    ("gemini-4-argon", [0.536, 0.488, 0.560, 0.392]),
    ("claude-opus-5-5", [0.376, 0.264, 0.296, 0.352]),
    ("gpt-6-astra", [0.312, 0.240, 0.256, 0.256]),
    ("all CF views", [0.720, 0.744, 0.696, 0.568]),
    ("control edits only", [0.712, 0.736, 0.768, 0.704]),
    ("insertions only", [0.696, 0.664, 0.512, 0.600]),
    ("erasures only", [0.688, 0.656, 0.544, 0.712]),
    ("no CF views", [0.272, 0.200, 0.144, 0.232]),
]
N_MODELS = 4  # the first four rows of BYTOOL are models; the rest are first-stage training variants
FACT = [("Erasures only", 43.2, 0.708), ("+ insertions", 43.2, 0.735), ("+ control edits", 16.0, 0.744),
        ("+ both", 23.2, 0.735)]
ARMS = [  # name, ESG mean, sd (None = single seed), erased %, lesion-free %, colour key
    ("Qwen3.5-4B, with CF views (3 seeds)", 0.741, 0.019, 13.2, 13.9, "with"),
    ("Qwen3.5-4B, without CF views (3 seeds)", 0.279, 0.107, 67.6, 35.9, "without"),
    ("… without, ‘absent’ share matched", 0.215, None, 73.5, 31.6, "without"),
    ("… without, then preference\noptimisation (3 seeds)", 0.661, 0.037, 24.2, 19.4, "dpo"),
    ("MedGemma 1.5 4B, with CF views", 0.721, None, 7.8, 5.9, "with"),
    ("MedGemma 1.5 4B, without CF views", 0.374, None, 57.5, 31.6, "without"),
    ("MedGemma 1.5 4B, not fine-tuned", 0.283, None, 54.3, 24.0, "without"),
]


def fig3():
    fig = plt.figure(figsize=(W, 3.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1], height_ratios=[1, 1.65], hspace=0.60, wspace=1.02)
    ax = fig.add_subplot(gs[:, 0])
    marks = ["o", "s", "^", "D"]
    cols = [OK["blue"], OK["sky"], OK["verm"], OK["purple"]]
    n = len(BYTOOL) + 1  # one extra row holds the heading of the training variants
    ys, names = [], []
    for i, (m, v) in enumerate(BYTOOL):
        y = n - 1 - i - (1 if i >= N_MODELS else 0)
        ys.append(y)
        names.append(m)
        ax.plot([min(v), max(v)], [y, y], color="0.75", lw=0.8, zorder=1)
        for t in range(4):
            ax.scatter(v[t], y, marker=marks[t], s=16, color=cols[t], edgecolor="white", linewidth=0.3, zorder=3)
    yh = n - 1 - N_MODELS  # heading row
    ax.axhline(yh + 0.5, color="0.6", lw=0.5, ls=":")
    ax.set_yticks(ys + [yh])
    ax.set_yticklabels(names + ["First stage only, trained with:"], fontsize=FS)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.get_yticklabels()[-1].set_fontstyle("italic")
    ax.get_yticklabels()[-1].set_color("0.25")
    ax.yaxis.get_major_ticks()[-1].tick1line.set_visible(False)
    ax.text(0.12, yh, "CF: counterfactual", fontsize=FS, color="0.35", va="center", ha="left")
    ax.set_xlim(0.1, 0.82)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_xlabel("ESG (125 main-test cases)")
    ax.legend(handles=[Line2D([], [], ls="", marker=marks[t], color=cols[t], ms=4, label=TOOLS[t].replace("\n", " "))
                       for t in range(4)], loc="upper center", bbox_to_anchor=(0.30, -0.12), ncol=2, columnspacing=0.6,
              handletextpad=0.2)
    label(ax, "A", x=-0.72, y=1.01)
    a = fig.add_subplot(gs[0, 1])
    y = np.arange(len(FACT))[::-1]
    a.barh(y, [f[1] for f in FACT], color=[OK["grey"], OK["grey"], OK["green"], OK["blue"]], height=0.6)
    for yy, f in zip(y, FACT):
        a.text(f[1] + 1, yy, f"{f[1]:.1f}%  (ESG {f[2]:.3f})", va="center", fontsize=FS)
    a.set_yticks(y)
    a.set_yticklabels([f[0] for f in FACT], fontsize=FS)
    a.set_xlim(0, 75)
    a.set_xlabel("Denies intact lesion after a TELEA\nedit elsewhere (% of 125 cases)")
    label(a, "B", x=-1.02, y=1.04)
    b = fig.add_subplot(gs[1, 1])
    y = np.arange(len(ARMS))[::-1]
    for yy, r in zip(y, ARMS):
        col = {"with": OK["blue"], "without": OK["verm"], "dpo": OK["green"]}[r[5]]
        b.errorbar(r[1], yy, xerr=r[2] if r[2] else None, fmt="o", ms=3.5, color=col, elinewidth=0.8, capsize=1.5)
    b.set_yticks(y)
    b.set_yticklabels([r[0] for r in ARMS], fontsize=FS, linespacing=1.0)
    b.set_xlim(0, 0.85)
    b.set_xlabel("ESG, main test (mean ± sd over seeds)")
    label(b, "C", x=-1.02, y=1.04)
    save(fig, "fig3_tools_ablations")


# ---------------------------------------------------------------------------------------------------------------------
# Supplementary figure, alternative designs (log Tables 6, 7, 11, 16).
# Panel a: change against each design's matched comparator in erased-lesion claims (x) and in sensitivity (y),
# percentage points; set = where the design was compared (held-out tools pooled unless noted).
# Each design is named by what it changes; the old code name is given in the comment.
SHIFT = [  # label, d_claims, d_sens, set
    ("unmatched control edit", -0.5, +0.9, "held-out tools"),                          # old: C1 unmatched ctrl
    ("preference optimisation\non erasures, alone", +7.1, +8.5, "held-out tools"),      # old: C2 no-CF + DPO
    ("preference\noptimisation on\nerasures, added", +8.0, +2.7, "held-out tools"),     # old: C3 recipe + DPO
    ("consistency loss", +1.1, +3.0, "held-out tools"),                                # old: C4 CMCC
    ("policy-gradient fine-tuning", +2.2, +4.1, "held-out tools"),  # old: GRPO. claims: case-weighted over both tools (log); sensitivity: TELEA +2.7 (219) and diffusion +5.8 (191), case-weighted
    ("multi-agent reader 1", -1.5, +2.2, "held-out tools"),                            # old: Multi-agent v10
    ("multi-agent reader 2", +6.1, +5.6, "held-out tools"),                            # old: Multi-agent v11
    ("larger adapter (rank 64)", -1.4, -1.6, "main test"),                             # old: Rank-64 adapter
    ("vision-encoder adapter", -5.1, +0.7, "main test"),                               # old: Vision LoRA (2e-5)
    ("editing-tool mix", +1.1, +2.8, "validation, TELEA"),                             # old: Tool-family replay
    ("editing-tool mix +\nconsistency loss", -3.9, -2.8, "validation, TELEA"),          # old: Tool-family + CMCC
]
DAGGER = "†"  # comparator = the same model trained longer on the same views (old: "vs replay control")
FOREST = [  # label, dESG, lo, hi (None if no interval recorded), set
    ("unmatched control edit", 0.012, None, None, "held-out tools"),                    # old: C1 unmatched vs matched control
    ("preference optimisation on erasures, alone", 0.017, None, None, "held-out tools"),  # old: C2 no-CF + DPO vs recipe
    ("preference optimisation on erasures, added", -0.054, None, None, "held-out tools"),  # old: C3 recipe + DPO vs recipe
    ("consistency loss" + DAGGER, 0.020, -0.006, 0.047, "held-out tools"),              # old: C4 CMCC vs replay control
    ("multi-agent reader 2" + DAGGER, -0.002, None, None, "held-out tools"),            # old: Multi-agent v11 vs replay control
    ("larger adapter (rank 64)", -0.004, None, None, "main test"),                      # old: Rank-64 vs recipe
    ("vision-encoder adapter", 0.041, None, None, "main test"),                         # old: Vision LoRA 2e-5 vs recipe
    ("editing-tool mix" + DAGGER, 0.017, -0.034, 0.067, "validation, TELEA"),           # old: Tool-family replay vs replay control
    ("editing-tool mix + consistency loss" + DAGGER, 0.011, -0.056, 0.084, "validation, TELEA"),  # old: Tool-family + CMCC vs replay control
    ("whole-image swap term" + DAGGER, -0.028, -0.073, 0.017, "validation, TELEA"),     # old: Hard-negative swap vs replay control
    ("vision-encoder adapter, layer-wise decay", 0.034, -0.028, 0.101, "validation, TELEA"),  # old: Vision LoRA, layer decay vs recipe
]
SET_M = {"held-out tools": ("o", OK["verm"]), "main test": ("s", OK["blue"]), "validation, TELEA": ("D", OK["green"])}
# label offsets in points and alignment (layout only): dx, dy, horizontal, vertical
OFFS = {"unmatched control edit": (5, -3, "left", "center"),
        "preference optimisation\non erasures, alone": (-5, 0, "right", "center"),
        "preference\noptimisation on\nerasures, added": (3, 5, "center", "bottom"),
        "consistency loss": (-5, 5, "right", "center"),
        "policy-gradient fine-tuning": (-5, 3, "right", "center"),
        "multi-agent reader 1": (-5, 2, "right", "center"),
        "multi-agent reader 2": (5, 0, "left", "center"),
        "larger adapter (rank 64)": (5, -1, "left", "center"),
        "vision-encoder adapter": (-2, -12, "center", "top"),
        "editing-tool mix": (5, -12, "left", "center"),
        "editing-tool mix +\nconsistency loss": (5, -3, "left", "center")}


def figS_designs():
    fig = plt.figure(figsize=(W, 3.3))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1], wspace=1.32)
    a = fig.add_subplot(gs[0, 0])
    a.axhline(0, color="0.55", lw=0.5)
    a.axvline(0, color="0.55", lw=0.5)
    a.plot([-9, 10], [-9, 10], color="0.75", lw=0.6, ls="--", zorder=0)
    for lab, dx, dy, st in SHIFT:
        mk, c = SET_M[st]
        a.scatter(dx, dy, marker=mk, s=18, color=c, edgecolor="white", linewidth=0.3, zorder=3)
        ox, oy, ha, va = OFFS[lab]
        a.annotate(lab, (dx, dy), xytext=(ox, oy), textcoords="offset points", fontsize=FS, ha=ha, va=va,
                   linespacing=1.05, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")], zorder=4)
    a.set_xlim(-10.5, 12.5)
    a.set_ylim(-4.5, 10)
    a.set_xlabel("Δ erased-lesion claims (percentage points)")
    a.set_ylabel("Δ sensitivity on intact lesions (percentage points)")
    a.legend(handles=[Line2D([], [], ls="", marker=SET_M[k][0], color=SET_M[k][1], ms=3.5, label=k) for k in SET_M],
             loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, fontsize=FS, handletextpad=0.2, columnspacing=0.8)
    label(a, "A", x=-0.17, y=1.1)
    f = fig.add_subplot(gs[0, 1])
    y = np.arange(len(FOREST))[::-1]
    f.axvline(0, color="0.4", lw=0.6)
    for yy, (lab, d, lo, hi, st) in zip(y, FOREST):
        mk, c = SET_M[st]
        if lo is not None:
            f.errorbar(d, yy, xerr=[[d - lo], [hi - d]], fmt=mk, ms=3.4, color=c, elinewidth=0.8, capsize=1.5)
        else:
            f.plot(d, yy, mk, ms=3.4, mfc="white", mec=c, mew=0.9)
    f.set_yticks(y)
    f.set_yticklabels([r[0] for r in FOREST], fontsize=FS)
    f.set_xlim(-0.09, 0.12)
    f.set_xlabel("Δ ESG against the matched comparator")
    f.legend(handles=[Line2D([], [], ls="", marker="o", color="0.3", ms=3.4, label="95% CI recorded"),
                      Line2D([], [], ls="", marker="o", mfc="white", mec="0.3", ms=3.4, label="point estimate only")],
             loc="lower left", bbox_to_anchor=(-0.05, 1.0), ncol=2, fontsize=FS, handletextpad=0.2, columnspacing=0.8)
    f.text(-1.45, -0.19, DAGGER + " compared with the same model trained longer on the same views;\n"
           "  other designs with the model trained in the standard way", transform=f.transAxes, fontsize=FS,
           color="0.25", ha="left", va="top", linespacing=1.15)
    label(f, "B", x=-1.45, y=1.1)
    save(fig, "figS_designs")


# ---------------------------------------------------------------------------------------------------------------------
# Supplementary figure, edit-site control and hidden-state probes (log Table 15).
# "Stage-1 model" = the model after the first training stage, all counterfactual views, seed 0 (old label: Recipe);
# "Qwen3.5-4B (base)" = the base model, not fine-tuned (old label: Base).
S0 = {  # denial among cases each model finds unedited (log Table 15)
    ("Stage-1 model", "LaMa"): {"far": 0.042, "ring": 0.077, "restored": 0.070, "partial": 0.196, "erased": 0.867},
    ("Stage-1 model", "TELEA"): {"far": 0.126, "ring": 0.203, "restored": 0.140, "erased": 0.923},
    ("Qwen3.5-4B (base)", "LaMa"): {"far": 0.023, "ring": 0.047},
    ("Qwen3.5-4B (base)", "TELEA"): {"far": 0.070, "ring": 0.116},
}
PROBE = {  # stage-1 model, erased vs edit-site (ring) control, AUROC per layer (4..32); AUROC of the answers; base best
    "LaMa": {"last": [0.763, 0.773, 0.851, 0.887, 0.893, 0.897, 0.896, 0.898],
             "image": [0.838, 0.856, 0.860, 0.886, 0.892, 0.901, 0.897, 0.896], "output": 0.845,
             "base": {"last": 0.829, "image": 0.870}},
    "TELEA": {"last": [0.683, 0.703, 0.746, 0.816, 0.784, 0.776, 0.803, 0.780],
              "image": [0.810, 0.822, 0.811, 0.820, 0.837, 0.844, 0.852, 0.852], "output": 0.824,
              "base": {"last": 0.808, "image": 0.831}},
}
LOGODDS = {  # within-case change of the single-turn log-odds, nats (log Table 15)
    "Stage-1 model, LaMa": [-14.10, -0.09, -0.43, 0.87, -4.05],        # old: Recipe, LaMa
    "Stage-1 model, TELEA": [-10.76, -2.41, -1.53, 1.34, np.nan],     # old: Recipe, TELEA
    "Erasures only, TELEA": [-11.88, -4.77, -3.94, -0.62, np.nan],
    "Consistency loss, TELEA": [-6.08, -0.31, -0.12, 0.57, np.nan],   # old: CMCC, TELEA
}
VIEW_NAME = {"far": "control edit,\nfar", "ring": "control edit,\nsame site", "restored": "restored",
             "partial": "half-erased", "erased": "erased"}


def figS_site_probes():
    fig = plt.figure(figsize=(W, 2.75))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1, 1.05], wspace=0.5)
    b = fig.add_subplot(gs[0, 0])
    kinds = ["far", "ring", "restored", "partial", "erased"]
    xs = np.arange(len(kinds))
    wd = 0.2
    series = [("Stage-1 model", "LaMa", OK["blue"], None), ("Stage-1 model", "TELEA", OK["blue"], "/////"),
              ("Qwen3.5-4B (base)", "LaMa", OK["grey"], None), ("Qwen3.5-4B (base)", "TELEA", OK["grey"], "/////")]
    for k, (mname, tool, c, h) in enumerate(series):
        vals = [S0[(mname, tool)].get(kk, np.nan) for kk in kinds]
        b.bar(xs + (k - 1.5) * wd, vals, wd, color=c if h is None else "white", edgecolor=c, hatch=h, linewidth=0.6,
              label=f"{mname}, {tool}")
    b.set_xticks(xs)
    b.set_xticklabels([VIEW_NAME[k] for k in kinds], fontsize=FS, rotation=35, ha="right", rotation_mode="anchor",
                      linespacing=0.95)
    b.set_ylim(0, 1)
    b.set_ylabel("Denies the finding\n(cases found unedited)")
    b.legend(loc="upper left", fontsize=FS, handlelength=1.2)
    label(b, "A", x=-0.32, y=1.03)
    c = fig.add_subplot(gs[0, 1])
    layers = [4, 8, 12, 16, 20, 24, 28, 32]
    for tool, col in (("LaMa", OK["blue"]), ("TELEA", OK["verm"])):
        p = PROBE[tool]
        c.plot(layers, p["image"], "-o", ms=2.2, color=col, label=f"{tool}, image tokens")
        c.plot(layers, p["last"], "--s", ms=2.0, color=col, lw=0.8, label=f"{tool}, last token")
        c.axhline(p["output"], color=col, lw=0.7, ls=":")
    c.set_ylim(0.55, 1.0)
    c.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    c.set_xticks(layers)
    c.set_xticklabels(layers, fontsize=FS)
    c.set_xlabel("Layer")
    c.set_ylabel("Probe AUROC, erased vs\nsame-site control edit")
    c.legend(loc="lower right", fontsize=FS, handlelength=1.6, borderaxespad=0.1, labelspacing=0.3)
    c.add_artist(c.legend_)
    c.legend(handles=[Line2D([], [], color=OK["blue"], ls=":", lw=0.7, label="model's answers, LaMa"),
                      Line2D([], [], color=OK["verm"], ls=":", lw=0.7, label="model's answers, TELEA")],
             loc="upper left", fontsize=FS, handlelength=1.6, borderaxespad=0.1, labelspacing=0.3)
    label(c, "B", x=-0.36, y=1.03)
    d = fig.add_subplot(gs[0, 2])
    views = ["erased", "far", "ring", "restored", "partial"]
    xs3 = np.arange(len(views))
    cols = [OK["blue"], OK["verm"], OK["grey"], OK["green"]]
    for k, (lab, vals) in enumerate(LOGODDS.items()):
        d.bar(xs3 + (k - 1.5) * 0.2, vals, 0.2, color=cols[k], label=lab, lw=0)
    d.axhline(0, color="0.3", lw=0.5)
    d.set_xticks(xs3)
    d.set_xticklabels([VIEW_NAME[k] for k in views], fontsize=FS, rotation=35, ha="right", rotation_mode="anchor",
                      linespacing=0.95)
    d.set_ylim(-24, 2.5)
    d.set_yticks(range(-14, 3, 2))
    d.spines["left"].set_bounds(-14.5, 2.5)
    d.set_ylabel("Δ log-odds vs unedited (nats)", y=0.70)
    d.legend(loc="lower right", fontsize=FS, handlelength=1.0, borderaxespad=0.0, labelspacing=0.3)
    label(d, "C", x=-0.32, y=1.03)
    save(fig, "figS_site_probes")


# ---------------------------------------------------------------------------------------------------------------------
# Supplementary figure, trainee readers (log Table 13), re-scoring on reader-assessed erasures, prompting conditions
# (log Table 8), lesion size (preprint)
KINDS = ["Unedited lesion", "Erased", "Control-edited", "Lesion-free"]
YES = {"Trainee, internal medicine": [29, 19, 31, 16], "Trainee, radiology": [26, 16, 27, 7]}  # of 32; old: R1, R2
MOD = ["Colonoscopy", "Breast US", "Chest X-ray", "Brain MRI", "SLAKE"]
MOD_E = [(1 + 2, 12), (6 + 4, 14), (5 + 4, 12), (3 + 5, 14), (4 + 1, 12)]  # erased: yes reads / reads, both readers
MOD_N = [(2 + 0, 12), (5 + 1, 14), (4 + 3, 12), (1 + 1, 14), (4 + 2, 12)]  # lesion-free
RV = {"Comparison models (9, pooled)": [26, 36, 82], "Open-weight + MedScope-4B (pooled)": [12, 19, 40]}
MEDSCOPE_RV = (0 / 10 * 100, 4 / 13 * 100)  # clean, residual
COND = ["Default", "Cautious", "Solved\nexamples", "Highest\nreasoning", "Highest\nimage", "Plain\nprompt"]
PROMPT = {"gemini-4-argon": [0.441, 0.412, 0.456, 0.456, 0.485, 0.338],
          "claude-opus-5-5": [0.338, 0.382, 0.309, 0.397, np.nan, 0.412],
          "gpt-6-astra": [0.338, 0.397, 0.500, 0.324, 0.397, 0.250]}
QUART = {"MedScope-4B": [0.545, 0.741, 0.836, 0.909], "gemini-4-argon": [0.400, 0.556, 0.418, 0.509],
         "claude-opus-5-5": [0.200, 0.352, 0.345, 0.418], "gpt-6-astra": [0.273, 0.333, 0.400, 0.218]}


def figS_readers_prompts():
    fig = plt.figure(figsize=(W, 4.5))
    gs = fig.add_gridspec(2, 3, hspace=0.80, wspace=0.55)
    a = fig.add_subplot(gs[0, 0])
    x = np.arange(4)
    for k, (r, col) in enumerate(zip(YES, (OK["blue"], OK["green"]))):
        a.bar(x + (k - 0.5) * 0.36, np.array(YES[r]) / 32 * 100, 0.36, color=col, label=r, lw=0)
    a.set_xticks(x)
    a.set_xticklabels(KINDS, fontsize=FS, rotation=30, ha="right", rotation_mode="anchor")
    a.set_ylim(0, 140)
    a.set_yticks(range(0, 101, 20))
    a.spines["left"].set_bounds(0, 100)
    a.set_ylabel("Finding called present (%)", y=0.36)
    a.legend(loc="upper left", fontsize=FS, ncol=1, handlelength=1.0, labelspacing=0.25, borderaxespad=0.1)
    label(a, "A", x=-0.3, y=1.05)
    b = fig.add_subplot(gs[0, 1])
    x = np.arange(len(MOD))
    b.bar(x - 0.18, [e / n * 100 for e, n in MOD_E], 0.36, color=OK["verm"], label="erased", lw=0)
    b.bar(x + 0.18, [e / n * 100 for e, n in MOD_N], 0.36, color=OK["grey"], label="lesion-free", lw=0)
    b.axhline(10, color="0.3", lw=0.6, ls="--")
    b.set_xticks(x)
    b.set_xticklabels(MOD, fontsize=FS, rotation=30, ha="right", rotation_mode="anchor")
    b.set_ylim(0, 140)
    b.set_yticks(range(0, 101, 20))
    b.spines["left"].set_bounds(0, 100)
    b.set_ylabel("Erased / lesion-free\ncalled present (%)", y=0.36)
    b.legend(loc="upper left", fontsize=FS, ncol=2, handlelength=1.0, columnspacing=0.8, borderaxespad=0.1)
    label(b, "B", x=-0.3, y=1.05)
    c = fig.add_subplot(gs[0, 2])
    grp = ["Clean\n(10)", "Majority\nclean (19)", "Residual\n(13)"]
    x = np.arange(3)
    for k, (lab, vals) in enumerate(RV.items()):
        c.bar(x + (k - 1) * 0.27, vals, 0.27, color=[OK["verm"], OK["sky"]][k], label=lab, lw=0)
    c.bar([0 + 0.27, 2 + 0.27], [MEDSCOPE_RV[0], MEDSCOPE_RV[1]], 0.27, color=OK["blue"], label="MedScope-4B", lw=0)
    c.text(0 + 0.30, 3, "0/10", fontsize=FS, ha="center")
    c.text(2 + 0.30, MEDSCOPE_RV[1] + 2, "4/13", fontsize=FS, ha="center")
    c.set_xticks(x)
    c.set_xticklabels(grp, fontsize=FS)
    c.set_ylim(0, 140)
    c.set_yticks(range(0, 101, 20))
    c.spines["left"].set_bounds(0, 100)
    c.set_ylabel("Erased-lesion claims (%)", y=0.36)
    c.legend(loc="upper left", fontsize=FS, handlelength=1.0, borderaxespad=0.1, labelspacing=0.25)
    label(c, "C", x=-0.3, y=1.05)
    d = fig.add_subplot(gs[1, 0:2])
    x = np.arange(len(COND))
    for m, vals in PROMPT.items():
        d.plot(x, vals, "-o", ms=3.2, color=MODEL_C[m], label=m)
    d.axhline(0.750, color=MODEL_C["MedScope-4B"], lw=1.0, ls="--", label="MedScope-4B (default)")
    d.set_xticks(x)
    d.set_xticklabels(COND, fontsize=FS)
    d.set_ylim(0, 0.85)
    d.set_ylabel("ESG (150 cases)")
    d.legend(loc="lower left", ncol=2, fontsize=FS)
    label(d, "D", x=-0.13, y=1.05)
    e = fig.add_subplot(gs[1, 2])
    x = np.arange(4)
    for m, vals in QUART.items():
        e.plot(x, vals, "-o", ms=3.2, color=MODEL_C[m], lw=1.3 if m == "MedScope-4B" else 0.9, label=m)
    e.set_xticks(x)
    e.set_xticklabels(["Q1\n<1.8", "Q2\n1.8–4.2", "Q3\n4.2–8.4", "Q4\n>8.4"], fontsize=FS)
    e.set_xlabel("Lesion area (% of image)", fontsize=FS)
    e.set_ylim(0, 1)
    e.set_ylabel("ESG")
    e.text(2.9, 0.93, "MedScope-4B", fontsize=FS, color=MODEL_C["MedScope-4B"], ha="right", va="bottom")
    label(e, "E", x=-0.3, y=1.05)
    save(fig, "figS_readers_prompts")


if __name__ == "__main__":
    fig2()
    fig3()
    figS_designs()
    figS_site_probes()
    figS_readers_prompts()
    print("figures written to", OUT)
