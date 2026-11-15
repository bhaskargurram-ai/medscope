# Changes from the PaperOrchestra draft (paper_po_original.tex -> paper.tex)

All 26 items of `paper/orchestra/review_run_20261115.md` are applied.

## Figures (all replaced; no generated images)
- Fig. 1: vector schematic in TikZ (`figures/fig1_framework.tex`), correct numbers (128 images, 45%).
- Figs. 2-6: plotted from the logged numbers by `figures/make_figures.py` (matplotlib, vector PDF, Okabe-Ito colours).
- Old Fig. 4 split: Fig. 4 = negative map (paired changes against matched comparators + dESG forest; replaces the
  invented scatter, ellipse and iso-ESG contours); Fig. 5 = stage 0 (denial, probes, log-odds). Old Fig. 5 -> Fig. 6.
- Fig. 6 A3: no MedScope bar on majority-clean erasures (not computed).

## References
- Fixed: MedHEval (Chang et al., arXiv:2503.02157), Med-HallMark (Chen et al., arXiv:2406.10185), HEAL-MedVQA
  (Nguyen et al., IJCAI 2025), MMedPO (Zhu et al., ICML 2025, PMLR 267), S-VCO (Wu et al., ACL 2025), ChestX-Det
  (Lian et al., IEEE TMI 2021), ProbMed (Findings of ACL 2025), self-citation title.
- Added: EMPO (Wu et al., EMNLP 2025), MFPO (Jiang et al., IJCAI 2025).

## Text
- Flagships (not nine models) in the lesion-quartile claim; pneumothorax: resolution does not explain the final miss.
- 54.7% / 13/32 are over all sources; GRPO missed its go signal on erased-lesion claims; tools-off effect = CCR -0.053.
- Five cost matrices described as run; "270 post-hoc" -> screened under a pre-registered rule.
- Abstention ceiling: "consistent with", not "validated"; diffusion claims: residual or regenerated, not reader-checked.
- Probes are on language-model hidden states (not the vision encoder); "strong evidence", not "unambiguous proof";
  reader reasons stated as hypotheses; CCR = covered-and-correct rate; readers = trainee physicians.
- No references to the input log; "texture classifier" for filtering; p <= 0.001; fresh external 150 lesion-free built;
  "stored per-view transcripts"; multi-agent controls = replay-only; "CMCC continuation"; kappa 0.10 = slight; SLAKE CT/MRI.
- Tables wrapped to fit the text width.
