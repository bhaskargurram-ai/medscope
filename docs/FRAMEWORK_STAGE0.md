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

## Amendment (14 November 2026, after the first run; thresholds and rules unchanged)

**What happened.** The single-turn score failed its validity check: sign(s) agreed with the recipe's agent answers
on 63% of dev views (rule: 80%). Cause: the "present" reply includes the box coordinates and is about 11 nats less
probable than the "absent" reply on every image, unedited lesions included (mean log-prob -48 vs -37), so s < 0
almost everywhere (the recipe "found" 23% of unedited lesions by this score; its agent finds about 85% of unedited lesions on the main test). The
threshold-based quantities of that run are therefore meaningless; the stage was invalid, as the rule says.

**Rerun, as pre-registered: the agent's generated answers** (one greedy episode per view, the benchmark prompt), for
the recipe and the base model (the two the rule needs), then CMCC (descriptive). The rule is applied unchanged with
these definitions: a view is "denied" when the agent does not say the finding is present (absent, refer, clarify or
no answer, as the benchmark counts it); "found" = the agent says present on the unedited image; the output score for
AUROC is the agent's probability of its answer, signed (+p for present, -p for absent, about 0 for refer). The
validity check becomes: the recipe's generated answers on the dev views agree with its stage-B answers (same model,
same views; a determinism check). The linear-probe results of the first run stand (they use only view labels, not
the score) and are reused.

**Seen before this amendment** (so declared): the within-case changes of the invalid score (same reply text within a
case, differences only). For every model the same-site ring lowered the score about as much as the far control edit
(recipe: 3% vs 1% of the erasure's drop on LaMa, 14% vs 22% on TELEA; ring minus control intervals include 0 for the
recipe), half erasures lowered it by 24-29% of an erasure, and TELEA edits anywhere lowered it by 13-40% of an
erasure (CMCC 2-5%). These are descriptive and do not enter the decision.
