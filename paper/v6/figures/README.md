# Figures of manuscript v6

All figures are drawn at the printed size (full text width, 7.16 in); the smallest type is 7 pt. Include them with
`\includegraphics[width=\textwidth]{figures/<file>}`. No figure computes a number: every plotted value is copied
from the source named below.

| File | Label | Made by | Numbers come from |
| --- | --- | --- | --- |
| `fig1_design.pdf` | `fig:design` | `pdflatex fig1_design.tex` (TikZ; needs `tiles/mri_*.png`) | No results. Panel a: real brain MRI case (TCGA-LGG) cropped from the pipeline's example sheet; its question is the one on that sheet. Panel b: drawn schematically (no colonoscopy video frame is stored in the repository); its question is `COLON_Q` in `scripts/natural_pairs.py`. Panel c: study flow. |
| `fig2_main_test.pdf` | `fig:main` | `python make_figures_v6.py` (`fig2`) | Main test, 507 cases, 1,115 views: results log Table 1 (per model) and Table 2 (by imaging type), as in the v5 figure. |
| `fig3_tools_ablations.pdf` | `fig:tools` | `python make_figures_v6.py` (`fig3`) | Results log Table 5 (editing tools, 125 cases), Table 4 (two-by-two of training views), Table 3 (first-stage training variants), as in the v5 figure. |
| `fig4_natural_pairs.pdf` | `fig:natural` | `python make_fig4_natural.py` | `report60.md` (consolidated report of the final model): panel a from section "R27: REAL-Colon pairs, cross-validated" (103 pairs), panel b from section "R26: LDPolypVideo natural pairs" (116 pairs). The rows used are named in the data block of the script. |
| `figS_designs.pdf` | `fig:s_designs` | `python make_figures_v6.py` (`figS_designs`) | Results log Tables 6, 7, 11, 16 (alternative training and system designs), as in the v5 Figure 4. |
| `figS_site_probes.pdf` | (supplement, optional) | `python make_figures_v6.py` (`figS_site_probes`) | Results log Table 15 (edit-site control, hidden-state probes, within-case log-odds), as in the v5 Figure 5. |
| `figS_readers_prompts.pdf` | (supplement, optional) | `python make_figures_v6.py` (`figS_readers_prompts`) | Results log Table 13 (trainee readers), the re-scoring on reader-assessed erasures, Table 8 (prompting conditions), lesion-size quartiles (preprint), as in the v5 Figure 6. |

`make_figures_v6.py` is the earlier plotting script (`paper/v3/figures/make_figures.py`) with labels changed only;
all 17 data blocks were compared value by value with that script and are identical. `fig1_framework.tex/.pdf` is
the v5 design figure, kept only as the source that `fig1_design.tex` was adapted from; it is not used by v6.
`tiles/` holds the image crops (only `mri_orig`, `mri_erased`, `mri_control`, `mri_free` are used).

Both Python scripts accept `--preview DIR` to also write PNG previews to `DIR`.

## Notes for captions

- Fig. 1b is a schematic, not a real video frame pair. Fig. 1 defines D as the share answered absent or referred.
- Fig. 4: x is the report's "Lesion found" column (lesion frames not answered absent or referred), so that
  natural ESG = y - (100 - x) and the grey diagonals are exact. Under each name: natural ESG [95% CI], 2,000
  bootstrap resamples of whole videos. The small blue dot in panel b is the three-seed majority vote.
- Fig. 3: "CF" = counterfactual; "first stage only" = models after the first training stage.
- Fig. S (designs): a dagger marks designs compared with the same model trained longer on the same views; the
  others are compared with the model trained in the standard way. Open symbols in panel b have no recorded interval.
  "multi-agent reader 1 / 2": arbiter trained in sample / on out-of-sample reports.
- Fig. S (site probes): "Stage-1 model" = the model after the first training stage with all counterfactual views;
  "control edit, same site" = area-matched ring just outside the lesion.

## Labels changed from the v5 figures

Fig. 2: "Claude Opus 5.5" -> "claude-opus-5-5"; "Frontier (9)" -> "Comparison models (9)"; "nine frontier models"
-> "nine comparison models"; "Open (6)" -> "Open-weight models (6)"; "Trivial policies" -> "Constant strategies";
"base (Qwen3.5-4B)" -> "Qwen3.5-4B (base)"; "Qwen2.5-VL-7B (CCR 0.14)" -> "Qwen2.5-VL-7B (lesion images correct
0.14)".

Fig. 3: "Claude Opus 5.5" -> "claude-opus-5-5"; rows "Stage 1: recipe / control edits only / insertions only /
erasures only / without CF views" -> heading "First stage only, trained with:" and rows "all CF views / control
edits only / insertions only / erasures only / no CF views" (plus the note "CF: counterfactual"); "Recipe (both)" ->
"+ both"; "Qwen, ..." -> "Qwen3.5-4B, ... CF views"; "Qwen, without, then DPO (3 seeds)" -> "... without, then
preference optimisation (3 seeds)"; "MedGemma, ..." -> "MedGemma 1.5 4B, ... CF views"; "MedGemma, untrained" ->
"MedGemma 1.5 4B, not fine-tuned".

Fig. S designs (old Fig. 4): "C1 unmatched ctrl" -> "unmatched control edit"; "C2 no-CF + DPO" -> "preference
optimisation on erasures, alone"; "C3 recipe + DPO" -> "preference optimisation on erasures, added"; "C4 CMCC" ->
"consistency loss"; "GRPO" -> "policy-gradient fine-tuning"; "Multi-agent v10 / v11" -> "multi-agent reader 1 / 2";
"Rank-64 adapter" -> "larger adapter (rank 64)"; "Vision LoRA (2e-5)" -> "vision-encoder adapter"; "Vision LoRA,
layer decay" -> "vision-encoder adapter, layer-wise decay"; "Tool-family replay" -> "editing-tool mix"; "Tool-family
+ CMCC" -> "editing-tool mix + consistency loss"; "Hard-negative swap" -> "whole-image swap term"; "vs replay
control" -> dagger with a footnote; "vs recipe" / "vs matched control" -> dropped (footnote); legend "held-out" ->
"held-out tools"; y label "(pp)" -> "(percentage points)". The x range of panel a is wider (-12.5 instead of -10.5)
so that the longer labels fit; no point moved.

Fig. S site probes (old Fig. 5): "Recipe" -> "Stage-1 model"; "Base" -> "Qwen3.5-4B (base)"; "CMCC, TELEA" ->
"Consistency loss, TELEA"; views "far / ring / partial" -> "control edit, far / control edit, same site /
half-erased"; "Probe AUROC, erased vs ring" -> "Probe AUROC, erased vs same-site control edit"; "answers, ..." ->
"model's answers, ...". Axis ranges of panels b and c were extended so that the legends no longer cover data.

Fig. S readers and prompts (old Fig. 6): panel letters a1, a2, a3, b1, b2 -> a to e; "R1 / R2" -> "Trainee, internal
medicine / Trainee, radiology"; "Frontier (9, pooled)" -> "Comparison models (9, pooled)"; "Open + MedScope
(pooled)" -> "Open-weight + MedScope-4B (pooled)"; "Claims erased finding (%)" -> "Erased-lesion claims (%)";
"Claude Opus 5.5" -> "claude-opus-5-5".
