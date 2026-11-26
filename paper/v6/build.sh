#!/bin/sh
# Builds main.pdf (needs pdflatex and bibtex).
set -e
pdflatex -interaction=nonstopmode main >/dev/null || true
bibtex main >/dev/null || true
pdflatex -interaction=nonstopmode main >/dev/null || true
pdflatex -interaction=nonstopmode main >/dev/null
