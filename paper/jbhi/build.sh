#!/bin/sh
# Builds paper.pdf and supplement.pdf (they cross-reference each other through xr-hyper).
set -e
rm -f paper.bib paper.bbl supplement.bbl
pdflatex -interaction=nonstopmode paper >/dev/null || true
bibtex paper >/dev/null
pdflatex -interaction=nonstopmode supplement >/dev/null || true
bibtex supplement >/dev/null || true
for i in 1 2; do
  pdflatex -interaction=nonstopmode paper >/dev/null
  pdflatex -interaction=nonstopmode supplement >/dev/null
done
pdflatex -interaction=nonstopmode paper >/dev/null
