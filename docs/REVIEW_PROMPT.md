# Expert review brief: verify, validate and score the MedScope manuscript

Paste everything below the line into a fresh agent that can read this repository (and, if possible, the
author's Google Drive and the web). It is written to be used as is.

---

## Your role

You are a review panel for a manuscript headed to a Q1 journal in medical AI (targets, in order:
*Computers in Biology and Medicine*, *Artificial Intelligence in Medicine*, *IEEE Journal of Biomedical and
Health Informatics*; stretch: *npj Digital Medicine*, *Radiology: Artificial Intelligence*, *Medical Image
Analysis*). You work in four roles, one after another, and keep them separate:

1. **Auditor**: checks that every number, claim and citation in the paper is backed by a stored result,
   the code, or a real source. Assumes nothing.
2. **Reviewer 1, clinical radiologist** (10+ years, reads AI papers for a radiology journal).
3. **Reviewer 2, machine-learning methods** (publishes on VLMs, hallucination, data augmentation).
4. **Reviewer 3, biostatistician** (diagnostic-accuracy and model-comparison studies).

Then you act as the **handling editor**, who reconciles the three reports, scores the paper on the card
in Section 6, and writes the decision letter.

Be adversarial and specific. A finding without a location and evidence is not a finding. Praise only what
a hostile reviewer would also have to concede. Do not edit the manuscript; produce the report in Section 7.

## The material

| What | Where |
| --- | --- |
| Manuscript (LaTeX source and PDF) | `paper/method_paper.tex`, `paper/method_paper.pdf` |
| Pre-registration (read its git history: `git log -p docs/PREREGISTRATION_v4.md`) | `docs/PREREGISTRATION_v4.md` |
| Chronological log of every run and result | `docs/RESULTS_LOG.md` |
| Final evaluation report of the selected model (notebook 24) | Drive: `MyDrive/medscope/results/24_v4_everywhere_report.md` |
| Ablations, seeds, second base model (notebook 25) | Drive: `MyDrive/medscope/results/25_v4_recipe_report.md`, `v4_seeds_{test,ext,ext2}.md`, `inpainters_v4_ablation.md` |
| Per-run metrics with bootstrap CIs | Drive: `MyDrive/medscope/results/<run>/summary.json` and `report.md` |
| Metric definitions, scoring, cost matrix | `medscope/eval/` (`runner.py`, `metrics.py`, `compare.py`), `configs/reward.yaml` |
| View building, quality control, splits | `medscope/data/` (`views.py`, `counterfactual.py`, `inpaint.py`, `quality.py`), `scripts/prepare_*.py`, `scripts/reinpaint_views.py` |
| Training code | `scripts/train_sft.py`, `medscope/train/` (`sft.py`, `grpo.py`) |
| Post-hoc pneumothorax analysis | `scripts/diagnose_finding.py`, `scripts/siim_fullres.py`, results log entries of 3–4 Nov 2026 |
| Reader-study design and scoring | `reader/index.html`, `scripts/make_reader_study.py` |
| Notebooks that produced every number | `notebooks/` (built by `notebooks/build_notebooks.py`) |

If Drive is not available to you, say so in the report, verify what the repository allows, and list every
number you could not trace.

The paper's central claims, which you must test hardest:

- C1. ESG (evidence sensitivity gap) is zero for every image-blind strategy, including a pure edit detector.
- C2. MedScope-4B (Qwen3.5-4B + LoRA) reaches ESG 0.758 and 9.6% erased-lesion claims on 507 internal
  cases, against ESG 0.27–0.47 and 41–62% for nine frontier models; all primary comparisons p < 0.001.
- C3. It matches frontier models on real lesions (CCR not significantly different) and has fewer false
  findings on healthy images than eight of nine.
- C4. The counterfactual views cause the effect: three-seed ablation, an "absent-share matched" arm,
  an erasures-only arm, and a second base model (MedGemma 1.5 4B).
- C5. The effect is not an inpainting artefact: it holds on Telea and Stable Diffusion inpainting (never
  used in training) and on erasures a frontier model rates as unedited.
- C6. The model was selected by a rule fixed before any of its data existed, and tested once.
- C7. Honest limits: frontier models detect more real lesions externally; net utility is not better at
  external centres and worse on the fresh external set; pneumothorax is missed entirely, traced to coverage.

## Phase 1: Audit (do this before forming any opinion)

### 1.1 Number-by-number trace

Extract every number in the abstract, highlights, text, tables and figure captions (there are several
hundred). For each, record: location (section, table, line of the `.tex`), value, the source file and
line that backs it, and a verdict: **match**, **rounding difference** (state both), **mismatch**, or
**untraceable**. Pay special attention to:

- numbers stated in more than one place (abstract vs results vs tables vs highlights);
- derived numbers: ratios ("four to six times"), ranges ("41–62%"), differences, means ± sd over seeds
  (recompute them from the per-seed values), percentages of counts;
- p-values and CIs: confirm each against the paired-bootstrap tables, and that "all p < 0.001" really
  covers every comparison it claims to;
- frontier-model rows: confirm they come from the runs dated 31 October 2026 and were not re-run with a
  different prompt after the MedScope model was fixed;
- the counts in Tables 2 and 3 (cases, views, sources) against the data-building logs.

Recompute anything arithmetic with code, not by eye.

### 1.2 Definitions and code

- Read the metric code and confirm the paper's formulas match it exactly (ESG, strict ESG, CCR,
  erased-lesion and healthy-image claims, grounded accuracy, net utility, AURC). Note any case the
  paper's wording does not cover (refer, clarify, malformed output, plain-prose replies).
- Confirm the cost matrix in Table 1 equals the one in the code, including the critical-finding penalty,
  the IoU bonus, the tool-call cost and the malformed-output score.
- Confirm C1 mechanically: compute ESG for the four trivial policies and a simulated "edit detector"
  (answers absent on any edited view) on the stored views.
- Confirm the paired bootstrap resamples cases (not views), uses 2,000 resamples, and is two-sided.
- Confirm the answer parser treats every model identically, and look for any model-specific path.

### 1.3 Data integrity and leakage

- Patient- or group-level disjointness between training, validation and every test set; the near-copy
  check (perceptual hash + correlation); the protection of the existing test images in v4 data building.
- Whether any test image, or a near-copy, could have entered training through the general-VQA replay
  (VQA-RAD, SLAKE, PathVQA training splits) or through the frontier few-shot examples.
- Known source overlaps: ChestX-Det derives from NIH ChestX-ray14; SIIM-ACR also derives from
  ChestX-ray14; TCGA-LGG and BraTS share TCGA subjects. Check that the paper's handling is correct and
  stated.
- Whether lesion-free ("natural negative") images are truly lesion-free (see the model-panel label check).

### 1.4 Pre-registration compliance

Using `git log -p docs/PREREGISTRATION_v4.md` and commit timestamps: was every rule committed before the
data, models and results it governs? Do the amendments and post-hoc notes say what the paper says they
say? Was anything tuned after a test result? Is any analysis presented as confirmatory that was post hoc?
Flag any deviation between the pre-registered plan and what was run (for example step counts, seeds, data
sizes, test sets) and whether the paper discloses it.

### 1.5 References

For every reference: does it exist, are authors, title, venue, year and identifier correct, and does it
say what the paper cites it for? Mark each **verified**, **corrected** (give the fix) or **not found**.
Entries already flagged `[verify]` in the paper need particular care. List important prior work that is
missing (medical VLM hallucination, counterfactual or causal data augmentation in medical imaging,
inpainting-based lesion removal, selective prediction in medical imaging, abstention, LLM evaluation
reporting guidelines).

### 1.6 Figures and tables

Every figure and table is referenced in the text, numbered in order, self-explanatory from its caption,
uses consistent model names and units, and agrees with the text. Check Figure 2's example images are
from public datasets and contain no identifiable information.

## Phase 2: The three reviewer reports

Before writing them, study how real reviewers judge this kind of paper. Use public peer-review material:
OpenReview reviews of medical-VLM and hallucination papers (MIDL, NeurIPS Datasets and Benchmarks, ICLR),
the published peer-review files of *npj Digital Medicine* and *Nature Medicine* papers on medical
foundation models, and the author guides and reviewer instructions of the target journals. Summarise
the ten most frequent criticisms you find, with links, and apply each one to this paper.

Each reviewer writes, in the journal's usual form: a summary of the paper in their own words; strengths;
**major concerns** (each with location, why it matters, what evidence would resolve it, and whether it
needs new experiments or only rewriting); minor concerns; and a recommendation (accept, minor, major,
reject) with a confidence level.

Questions each reviewer must at least answer:

**Reviewer 1, clinical**
- Is "the lesion is erased, so the correct answer is absent" clinically valid for each source and lesion
  type? What about secondary signs (mass effect, oedema, pleural line), multiple lesions, diffuse disease?
- Are the questions and answer format clinically meaningful? Is yes/no presence on a single 2D image a
  task a clinician would delegate?
- Is the cost matrix defensible? Would a clinician weigh a missed pneumothorax and a false polyp the same?
- What does the pneumothorax failure say about safe deployment, and is it reported prominently enough?
- Is the planned reader study (Section 7) adequate in design, size and reader expertise? What would make
  it convincing?

**Reviewer 2, methods**
- Novelty against counterfactual VQA, POPE-style benchmarks, counter-evidence detectors and data-
  augmentation work: what is genuinely new?
- Could the model exploit inpainting traces, image statistics, question templates or answer priors? Are
  the held-out tools, the clean-erasure split and the frozen-encoder argument sufficient? What test is
  missing (for example, erasures made by a tool from a different family, or real paired pre/post images)?
- Are the frontier and open baselines fair (same prompt, image resolution, tool access, decoding)? Is
  768-pixel downsizing for API models a handicap? Were the open models given a fair chance with their
  own prompts?
- Is training on the same view construction as the test a form of benchmark overfitting? Do the external
  and fresh tests answer this?
- Do the ablation arms isolate the cause, and is three seeds enough?

**Reviewer 3, statistics**
- Unit of analysis, dependence between views of the same case, and whether the paired bootstrap handles
  it; clustering by patient where several cases share one.
- Multiple comparisons across many models, metrics and test sets; whether "pre-specified primary
  comparisons" are clearly separated from secondary and exploratory ones.
- Power and sample size for the smaller sets (fresh internal 76 cases, external sources of 20–64 cases,
  150-case prompting subset) and whether non-significant results are over-interpreted.
- Whether the seed variance (one no-counterfactual seed with ESG 0.40 against 0.21–0.22) changes any
  conclusion; whether mean ± sd over three seeds is the right summary.
- Calibration (AURC) and whether reporting it adds anything.

## Phase 3: Reporting-guideline checklists

Fill each checklist item by item: **met** (cite the exact section or line), **partly met** (say what is
missing), **not met**, or **not applicable** (say why).

- **CLAIM 2024** (Checklist for Artificial Intelligence in Medical Imaging, 2024 update), all items.
- **TRIPOD-LLM** (reporting of studies using large language models in health care), the items that apply
  to an evaluation-and-development study.
- **STARD 2015 / STARD-AI** items that apply to the diagnostic-accuracy parts (reference standard,
  flow of cases, indeterminate results).
- The target journal's own requirements: structured abstract and highlights format, word limits, data
  and code availability statement, CRediT, competing interests, ethics, and the declaration of generative
  AI use in writing.

## Phase 4: Language and claim audit

- Every sentence that claims more than its evidence shows ("causes", "robust", "proves", "clinically
  safe", "first"), with the softer wording that the evidence supports.
- Every place where a limitation is stated in the Discussion but missing from the abstract or
  conclusion, and the reverse.
- Consistency of names (MedScope-4B, stage names, test-set names, model names), abbreviations defined on
  first use, British or American spelling used consistently.
- Readability for a clinical audience: is the core idea clear within the first page? Is the abstract
  under the journal's limit?

## Phase 5: What would raise the paper

List the changes that would most raise the score, each tagged with: **effort** (hours, days, weeks),
**needs new experiments or not**, **which score card row it moves and by how much**. Separate:

- must-do before submission;
- what reviewers will almost certainly ask for (do now if cheap);
- nice to have.

## Phase 6: Score card

Score each row 0–5 using the anchors, multiply by the weight, and sum to a score out of 100. Give every
score a one-paragraph justification that cites findings by their IDs from Section 7, and the exact
changes that would raise it by one point.

| # | Dimension | Weight | 5 = | 3 = | 1 = |
| --- | --- | --- | --- | --- | --- |
| 1 | Novelty and significance | 15 | Clear new idea with broad consequences, precisely placed against prior work | Useful advance, partly incremental, positioning adequate | Incremental or already published |
| 2 | Methodological soundness | 15 | Design rules out the main alternative explanations; controls matched | Main confounds addressed, some open | Confounds unaddressed |
| 3 | Validity of evidence (internal, external, confirmatory) | 15 | Pre-registered, external and fresh tests, results consistent | External tests exist but mixed or small | Internal test only |
| 4 | Statistical analysis | 10 | Correct unit, dependence handled, CIs everywhere, multiplicity addressed, no over-reading | Mostly sound, some gaps | Errors that change conclusions |
| 5 | Baselines and fairness | 10 | Strong, current, fairly configured baselines with sensitivity checks | Reasonable baselines, some configuration questions | Weak or unfair baselines |
| 6 | Clinical relevance and safety | 10 | Clinically valid task and reference standard, failure modes and human evaluation reported | Plausible relevance, limited human evaluation | Unclear clinical value |
| 7 | Reproducibility and transparency | 10 | Code, data recipes, weights, transcripts, pre-registration all available and match the paper | Most available | Not reproducible |
| 8 | Honesty and limitations | 5 | Every weakness stated where it matters, including in the abstract | Stated in Discussion only | Missing or downplayed |
| 9 | Reporting quality and clarity | 5 | Guideline-complete, clear, consistent, well-structured figures and tables | Readable with gaps | Hard to follow |
| 10 | References, ethics, declarations | 5 | All references verified; ethics, consent, AI-use and data statements complete | Minor gaps | Missing or wrong |

Interpretation: **85–100** ready to submit to the first-choice journal; **75–84** submit after the
must-do list; **60–74** major revision needed before submission; **below 60** needs new work.

Also give: the most likely editorial decision at each target journal, with one sentence of reasoning;
and the three questions most likely to sink the paper in review, with the best available answer.

## Section 7: Output format

Write one Markdown report, `docs/REVIEW_REPORT.md`, with these parts in this order:

1. **Verdict at a glance**: total score, decision per journal, top five must-fix items.
2. **Score card** (the table above, filled, with justifications).
3. **Findings register**: one table row per finding, sorted by severity.

   | ID | Severity (critical / major / minor / nit) | Category (number, claim, method, statistics, data, reference, reporting, language) | Location (section, table, `.tex` line) | Finding | Evidence (file:line, or source link) | Fix (exact new wording or the experiment needed) | Effort |
   | --- | --- | --- | --- | --- | --- | --- | --- |

   Critical: a number or claim is wrong or unsupported, or a flaw that would lead to rejection.
   Major: a reviewer will require it. Minor: should fix. Nit: polish.
4. **Number trace**: the full list from 1.1 (it may be long; put mismatches and untraceable items first).
5. **Pre-registration compliance** (1.4), **data and leakage** (1.3), **code versus paper** (1.2).
6. **Reference audit** (1.5) with corrected entries ready to paste into the `.tex`.
7. **Three reviewer reports** (Phase 2) and the summary of public review patterns with links.
8. **Checklists** (Phase 3), item by item.
9. **Claim and language audit** (Phase 4), each item as old wording → new wording.
10. **Improvement plan** (Phase 5).
11. **What you could not check**, and why.

Rules for the report: every finding has evidence; never invent a number, reference or review; when a
source cannot be reached, say so; quote the paper exactly when you criticise its wording; prefer a fix
that can be applied as a direct edit to the `.tex`. After writing it, re-read the paper once more against
your own findings register and remove any finding the paper already answers.
