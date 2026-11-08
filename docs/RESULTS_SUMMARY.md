# MedScope: complete results to date and open questions

Status document for an outside reader, 8 November 2026. Everything below is in the repository
(`github.com/bhaskargurram-ai/medscope`): the manuscript draft (`paper/method_paper.pdf`, v0.16), the dated log of every
run and every change of plan (`docs/RESULTS_LOG.md`), the four pre-registrations (`docs/PREREGISTRATION_v4.md` …
`_v7.md`, each committed before the arms it describes were trained), the per-run reports, and the notebooks that
reproduce each number. Numbers are given with 95% bootstrap intervals or seed spreads where they exist.

## 1. The question

Medical vision–language models often report a finding because the question names it. Standard VQA accuracy cannot see
this: a model that answers "yes, there is a polyp" to every polyp question scores well on images that have one. We
wanted (a) a way to measure whether an answer follows the image, without human annotation, and (b) a way to train a
small model so that it does.

## 2. What was built

**Counterfactual views.** From public segmentation datasets (SLAKE, Kvasir-SEG, BUSI, QaTa-COV19, BraTS-type MRI,
ChestX-Det, ETIS, BUS-UCLM, SIIM-ACR; five imaging types) each lesion image yields: the original (O), the lesion erased
by inpainting (E, "target removal"), a same-shape, same-tool edit elsewhere on tissue (C, "random removal" = the control
edit), a degraded copy, and unedited lesion-free images (natural negatives). Erasures are quality-checked automatically.
Two inpainting tools are used in training (LaMa, tissue transplant); two more (TELEA, diffusion) appear only at test.

**Evidence sensitivity gap (ESG)** = P(absent answer | E) − P(absent answer | C). Zero for any constant policy and, in
expectation, for any policy that ignores the image or reacts to both edits alike. Reported with: erased-lesion claims
(P(claims finding | E), lower is better), control-edit denial (P(denies intact lesion | C), lower is better),
healthy-image claims (P(claims finding | natural negative)), CCR (accuracy on answerable views), grounding IoU, and a
clinical cost-matrix net utility.

**MedScope-4B.** Qwen3.5-4B + LoRA, an agent with image tools (zoom, window), trained on trajectories derived from the
labels (no human annotators), in three stages, with the final model chosen by a pre-registered validation rule
(v4). Total API spend for all comparator runs: US$373.

## 3. Main results (internal test: 507 cases, 1,115 views, five imaging types)

| Model | ESG | Erased-lesion claims | CCR | Healthy-image claims |
| --- | --- | --- | --- | --- |
| MedScope-4B (final) | **0.758** | **9.6%** | 0.849 | 7.6% |
| Nine frontier VLMs (API) | 0.27–0.47 | 41–62% | comparable on real lesions | – |
| Six open VLMs | lower | higher | – | – |

All frontier differences p < 0.001. No significant loss of accuracy on real lesions on the internal test.

**Robustness of the frontier comparison (notebooks 17, 32).** The gap did not close with a cautious prompt, with solved
examples in context, at the models' highest reasoning and image-processing settings (e.g. gpt-6-astra ESG 0.34 → 0.40,
n.s.), with each model's own free-form reply (no flagship gains net utility under its plain prompt), or with reworded
questions.

**Ablations (3 seeds where stated).**
- Without counterfactual views: ESG 0.279 ± 0.107, erased claims 67.6 ± 11.9% (vs 0.741 ± 0.019 and 13.2 ± 3.2% with).
- "Absent"-share-matched arm without views: ESG 0.215 — the share of "No" answers is not the explanation.
- Erasures only: ESG 0.708, erased 6.8%, but CCR 0.788 and 43% control denial — erasures alone teach "edited means absent".
- Control edits only: ESG 0.744, CCR 0.897, control denial 16% — the control edit is what removes the shortcut.
- Recipe (erasures + controls + insertions): ESG 0.735, CCR 0.847, erased 11.9%, denial 23% (TELEA).
- Second base model (MedGemma 1.5 4B): same effect.
- Held-out inpainting tools (never seen in training): effect holds (recipe ESG 0.65–0.77 by tool).

**Generalisation.** Four external centres: the hallucination advantage holds, but frontier models detect more real
lesions. Fresh external test (pre-registered, run once): MedScope-4B missed every pneumothorax (SIIM); post-hoc analysis
links this to training coverage (pneumothorax nearly absent from training, absent from validation). v4.1 (stage 3
redone with SIIM training patients) is reported as a post-hoc repair, not as the selected model.

**Edit traces.** A trained detector finds edits (AUC 0.83); a linear probe on the frozen vision encoder carries a weak
edit signal (AUC 0.60). The advantage holds on clean-looking erasures and unseen tools, but a residual contribution of
edit traces cannot be excluded.

**Data hygiene.** Pixel-level crosswalk over 6,849 images across all splits and cohorts: no shared ids, one identical
image (removed from consideration), near-duplicates explained by shared anatomy at calibrated thresholds.

## 4. Pre-registered mechanism checks (rules committed before training; scripts apply them verbatim)

| Check | Question | Result | Verdict by rule |
| --- | --- | --- | --- |
| **C1** (v5) | Does the control edit need to match the erasure's shape and tool? | Matched vs unmatched within seed noise on every set except SIIM, where the unmatched arm shows a response bias ("present" on 60% of unedited, 67% of erased, 19% of healthy films) | Inconclusive by rule; substantively, matching not shown to matter |
| **C2** (v5, 3 seeds in v6) | Does the recipe beat removal-based DPO (closest existing method) on new data? | Fresh-external ESG 0.381 ± 0.018 vs 0.355 ± 0.015; net utility 0.070 ± 0.008 vs −0.069 ± 0.078. On the internal test the recipe halves erased claims (13 vs 24%) but DPO is more sensitive (CCR 0.90 vs 0.87); on new data DPO is the more conservative | No difference shown on new data; the two fail differently |
| **C3** (v6) | Does DPO on top of the recipe add sensitivity? | Fresh external CCR 0.542 vs 0.560; held-out tools erased claims 24.4% vs 16.3% (p < 0.001), ESG −0.054 | Fails; no stage 4 trained |
| **C4** (v7, 3 seeds) | Does writing the control edit into the loss (CMCC: difference-in-differences margin + original/control invariance + first-action consistency) reduce edit-cue reliance beyond a matched-compute control? | Primary endpoint (erased claims, held-out tools) 12.6% vs 11.5%, +0.011 [−0.009, +0.030], seeds −0.029/+0.059/+0.005. Secondary: denial −0.033 (p = 0.001), CCR +0.030 (p = 0.004), net utility +0.051 (p = 0.04). Guard fails: healthy-image claims 13.1% vs 7.9% (p < 0.001). Fresh external: CCR +0.127, denial −0.131, but erased claims +0.073 (all p < 0.001) | **Fails.** The objective shifts the operating point towards "present"; it does not reduce edit-cue reliance |

**Two incidental findings from C4 worth keeping.** (i) The matched-compute control — the recipe adapter simply trained
longer on the same control-edit data, no new objective — cut erased-lesion claims on *unseen* tools from 16.3% to 11.5%
and raised ESG from 0.649 to 0.709. Longer stage-1 training is a cheap, real improvement with unseen tools. (ii) The CMCC
training logs show the objective worked as designed (original/control log-odds gap 3 → 0.2 while the erasure margin
stayed at 8–10), so the failure is of the hypothesis, not the implementation: matching log-odds between original and
control edit raises the control's "present" probability rather than lowering the edit's influence.

## 5. Literature position (three independent sweeps, November 2026)

No prior training objective uses a pixel-level *matched* control edit as a constraint. Closest: Evidence-RL (token-space
area-matched controls), DeFacto (random-mask triplets under GRPO), Agarwal 2020 (invariant edits as data only), the
original-vs-degraded preference family (mDPO, MMedPO, oDPO, AdaViP, HII-DPO, FIRE-MPO), CoEV (post-hoc erase-and-recheck
at inference, medical, June 2026). Evaluation-side neighbours: MIRAGE, "Beyond Accuracy", PriVE-Tools, CORAL, MedVIGIL.
The ESG with an edit-matched control, built automatically across five modalities, remains unique to this work; the
training-side novelty claim did not survive C4.

## 6. What is ruled out, what is open

Ruled out (pre-registered): that matching the control edit matters; that the recipe beats DPO on new data; that DPO
on top of the recipe helps; that a log-odds consistency constraint on the control edit beats more training.

Not ruled out: a margin-only paired objective (push the erasure's log-odds down rather than the control's up); a
noise-instead-of-inpaint control arm (does the advantage survive when the edit is trivially detectable?); an
inference-time erase/sham probe tool (the model edits its own evidence and checks its answer); the same ideas on the
final stage-3 model rather than stage 1; and whether frontier models' hallucination rate drops when given the
erase/sham pair explicitly.

## 7. Pending

- **Reader study** (notebook 28): 128 blinded images (unmodified, erased, control-edited, lesion-free); design and
  analysis fixed; answers not yet collected. This is the single most important missing piece: it validates the "absent"
  ground truth after erasure and tests whether readers can tell erasure from control edit.
- Manuscript placeholders: reader-study results and ethics statement, AI-use declaration (author's decision), Qwen
  revision hash, one stage-2 cell in Table 13.

## 8. Questions for an expert reader

1. **Framing.** The paper is now a measurement framework + benchmark + demonstration that a small model can acquire
   evidence-gated behaviour, with four pre-registered checks that narrow the training claim. Is that a clinical-AI /
   medical-imaging paper (Radiology: AI, Medical Image Analysis, npj Digital Medicine), an ML-evaluation paper
   (TMLR, NeurIPS Datasets & Benchmarks), or should it be split (benchmark paper + short methods report)?
2. **Clinical plausibility of the view construction.** Which erasures are clinically valid (polyp, mass, nodule) and
   which are not (diffuse opacity, pneumothorax, anything with secondary signs)? Should the benchmark drop the latter?
3. **The utility metric.** Our cost matrix charges a missed critical finding most, which rewards an indiscriminate
   "present" on findings nobody detects. Is there an accepted alternative for selective-prediction evaluation in
   radiology?
4. **Is the longer-training observation from C4 worth a pre-registered follow-up** (a stage 1 twice as long, selected
   on validation), or is it a footnote?
5. **Which of the open directions in §6 would change a reviewer's mind**, and which would a clinician find irrelevant?
6. **Reader study**: how many readers and what specialties make the blinded validation credible for the venues above?
