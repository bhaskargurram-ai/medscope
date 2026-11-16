# paper/jbhi: IEEE J-BHI version (special issue "Agentic AI for Healthcare")

Same results as paper/v3, shortened to the J-BHI limit of 14 pages (IEEEtran journal layout).

- `paper.tex` -> `paper.pdf` (14 pages). The appendix, the related-work and design tables, the reporting checklist and
  the per-arm numeric tables moved to `supplement.tex` -> `supplement.pdf`; the paper cites them as Tables S1-S16
  (cross-references through `xr-hyper`).
- Figure 1 (`figures/fig1_framework.tex`) is now a three-stage flow diagram with real images: tiles cropped from the
  pipeline's example sheet (`figures/examples_montage.png`, from Drive `examples.png`).
- Figures 2-6: `figures/make_figures.py` (drawn at 7.16 in, the IEEE text width).
- Build: `./build.sh` (needs pdflatex and bibtex; `IEEEtran.cls` v1.8b and `IEEEtranN-doi.bst` are included).

Open before submission: co-author name and affiliation, results of review checks R6-R8, IEEE author portal
formatting check (PDF eXpress).
