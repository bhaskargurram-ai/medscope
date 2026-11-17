# arXiv replacement: 2611.13006 v2

Upload `medscope_arxiv_v2_source.tar.gz` (built from this folder: paper.tex, paper.bbl, elsarticle.cls,
math_commands.tex, figures/*.pdf). arXiv compiles it with pdflatex and uses paper.bbl, so no bibtex run is needed.
Checked: compiles from the tarball alone, 28 pages, no undefined references, no Type 3 fonts.

How to replace: arxiv.org > your submissions > 2611.13006 > "Replace". Upload the tarball, then update the fields below.

## Title

Measuring and Attributing Evidence Sensitivity in Medical Vision-Language Models via Symmetric Counterfactual Controls

## Authors

Bhaskar Gurram

## Comments

v2: substantially extended. 28 pages, 6 figures. Adds same-site ring controls, hidden-state probes, a blinded physician
reader study, 12 pre-registered training or system arms, a 270-policy screening funnel, checks requested by an
external review, and a model retrained with pneumothorax cases. Code and pre-registrations:
https://github.com/bhaskargurram-ai/medscope

## Abstract (plain text, under arXiv's 1,920-character limit)

Medical vision-language models (VLMs) asked closed clinical questions ("Is there a polyp?") can score well by relying
on the question rather than the image, and current hallucination benchmarks cannot separate true visual
discrimination from editing shortcuts or shifts in the answer threshold. We introduce a Counterfactual Evidence
Framework that pairs each lesion erasure with a shape- and tool-matched control edit elsewhere in the image, adds
same-site ring controls, restored and partial erasures, degraded views and natural negatives, tests on held-out
inpainting tools, separates discrimination (the Evidence Sensitivity Gap, ESG, and AUROC) from the answer threshold,
and checks the labels with blinded physician readers and hidden-state probes. Across 507 main-test cases (1,115 views),
nine frontier VLMs claim 41.1% to 61.6% of erased lesions (ESG 0.269 to 0.470), whereas MedScope-4B, a Qwen3.5-4B
agent trained on automatically built counterfactual trajectories, claims 9.6% (ESG 0.758; p <= 0.001 in all 27 primary
comparisons). Physician readers support automated erasure in colonoscopy, where frontier models still claim 45% of
erased lesions against 1% for MedScope-4B, but call a finding present on 54.7% of pooled erased reads across all
sources, which bounds what unverified erasure can certify. Across 12 pre-registered training or system arms and 270
decision policies screened under a rule fixed in advance, every apparent utility gain comes from shifting the
threshold rather than improving held-out discrimination, and probes point to perception as the remaining limit. We
also report a 0/48 pneumothorax failure on an external cohort; retraining with pneumothorax patients in every stage
finds 53% of pneumothoraxes on new patients without changing the main-test results.

## Version note (also printed as the title footnote)

Version 2 of arXiv:2611.13006 (v1: 8 November 2026, titled "Seeing Is Not Believing"). Since v1, and each
pre-registered before it ran: same-site ring controls with restored and half-erased views, layer-wise hidden-state
probes, a blinded physician reader study, Stage-1 tool-family training, a 270-policy screening funnel, and seven checks
requested by an external review (Section 4.6), including a post hoc model retrained with pneumothorax cases. Figure 1
now shows real cases. A reader study with board-certified radiologists and endoscopists is in progress.
