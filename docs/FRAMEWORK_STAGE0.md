# Framework stage 0: pre-registration (written 14 November 2026, before any stage-0 score was computed)

Stage 0 decides which framework (docs/FRAMEWORK.md) is built. It trains nothing and uses **validation images
only**: the 200 validation cases and 80 lesion-free validation images of the screening dev set (docs/SCREENING.md,
same seed, same cases), with their LaMa views and TELEA views. The test sets are not touched.

## New views (per case; files under results/fw_stage0/views)

- **ring**: the same tool fills a ring right around the lesion (starting 2 pixels outside it) with the same area as
  the erasure's edit mask (lesion dilated by 5 pixels). The lesion is intact: the correct answer is "present".
- **restored**: the case's erasure with the lesion's own pixels put back inside the lesion mask; only the 5-pixel
  band that the erasure also filled stays edited. Correct answer: "present".
- **partial** (LaMa only): half of the lesion (one side of its centroid along its longer axis) erased. Present, with
  less evidence.

## Score

The decision log-odds s(x) = log p(present reply) - log p(absent reply), one turn, the two replies worded from the
case's unedited view (as in `medscope/train/cmcc.py`), so every view of a case is scored on identical text.
Yes/no questions only. Models: the recipe (`v4_s1/final`), the untrained base model, stage 1 without
counterfactual views (`v4q_nocf_s0`), stage 1 with erasures but no control edits (`v4q_tgt_s0`), CMCC
(`v4q_cmccn_s0`) and its replay-only control (`v4q_sftc_s0`); models whose adapter is missing are skipped and
reported. Hidden features (last prompt token and mean over image tokens, layers 4-32 in steps of 4) for the recipe
and the base model.

**Validity check of the score:** sign(s) must agree with the recipe's own agent answers (screening stage B,
`results/screen_b/probes.jsonl`, refer and clarify answers skipped) on at least 80% of dev views. Otherwise the
stage is invalid and is repeated with generated answers before anything is decided.

## Quantities (`medscope/fw/analysis.py`)

Among cases whose unedited image the model scores present (s > 0), the share scored absent on each view:
- **site effect** = share absent on ring views; **far effect** = share absent on the benchmark's control edit
  (same tool, elsewhere); site minus far with a bootstrap 95% interval (cases resampled, 2,000, seed 0).
- ESG far = P(s<0 | erased) - P(s<0 | control) and **ESG site** = P(s<0 | erased) - P(s<0 | ring), all cases.
- AUROC of s for control vs erased, ring vs erased, restored vs erased (discrimination without a threshold).
- Graded order: share of cases with s(original) > s(partial) > s(erased).
- Linear probes (logistic regression, standardised, C = 0.05; 5 folds grouped by case) on hidden features: erased vs
  ring, erased vs control and ring vs original, trained on LaMa views and tested on LaMa and on TELEA views.

## Decision rule (fixed now)

- **A, site shortcut:** for LaMa or TELEA, the recipe's site effect is at least 0.10, at least 0.05 above its far
  effect, and at least 0.05 above the base model's site effect.
- **B, read-out gap:** the best layer's probe AUROC for TELEA erased vs ring (trained on LaMa) is at least 0.05
  above the recipe's own output AUROC for the same pair (last-token or image-token features).
- Branch: A and B -> footprint-balanced counterfactual training with an evidence read-out; A only ->
  footprint-balanced training with the output-level objective; B only -> evidence read-out from internal features;
  neither -> perception-limited (the framework's training part is not supported by stage 0, and the next step is
  perception, docs/FRAMEWORK.md section 6).

Everything else in the report (ESG site, restored and partial views, the four other models, the base model's
probes) is descriptive and is reported whichever branch is taken. Results go into `docs/RESULTS_LOG.md`.
