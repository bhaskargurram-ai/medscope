# paper/v3: Elsevier two-column layout and redrawn figures

Same text, numbers and tables as paper/v2; only the layout and the figures changed.

- **Template.** `elsarticle` (Elsevier, v3.4c; class file included) with `5p,times,twocolumn,authoryear`, the layout
  used by Medical Image Analysis. Front matter with keywords; figures and wide tables span both columns; appendix in
  one column. Bibliography `plainnat` (author-year). `\usepackage[OT1]{fontenc}` keeps every font Type 1 (no
  cm-super needed). Long equations split over two lines for the 3.5 in column.
- **Figures.** Drawn at printed size (7.22 in full width) with the settings of SciencePlots' `nature` style
  (github.com/garrettj403/SciencePlots): 7 pt sans text, 0.5 pt axes, no frames on legends, light grid; sizing as in
  tueplots (github.com/pnkraemer/tueplots), so no figure is scaled in LaTeX. Colours: Paul Tol's colour-blind-safe
  "bright" scheme. Bold lower-case panel labels (captions and text references follow). Figure 1 redrawn in TikZ at
  the full text width.

Build: `cd figures && python3 make_figures.py && pdflatex fig1_framework.tex`, then
`pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper`.
