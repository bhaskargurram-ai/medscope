# MedScope v7 check: the control edit as a constraint (control-matched counterfactual consistency, CMCC)

Written and committed on 7 November 2026, after the v6 results (`results/v6_confirmation.md`) and the CMCC smoke test
(`results/35a_cmcc_smoke_test_report.md`, run `v4q_cmcc_s0`), and before any arm below was trained. The git history
of this file is the record.

## What the smoke test showed (one seed, exploratory, not a finding)

The seed-0 recipe adapter continued for 3,000 triplet cases with the paired-view objective of
`medscope/train/cmcc.py` (trajectory replay + difference-in-differences margin on the present/absent log-odds between
control edit and erasure + original/control invariance + first-action consistency), against the recipe itself and
the recipe continued with removal-based DPO (C3):

- Held-out inpainting tools (TELEA + diffusion, 410 cases): erased-lesion claims 10.7% vs 16.3% (recipe) vs 24.4%
  (C3); control-edit denials 14.9% vs 18.8%; ESG 0.744 vs 0.649; net utility 0.741 vs 0.566. The diffusion-tool
  differences are significant (erased claims −0.094, p < 0.001; ESG +0.120, p < 0.001); TELEA ESG +0.073, p = 0.008.
- Transplant (a training tool): no difference (ESG 0.699 vs 0.720, erased 13.3% vs 11.2%, both n.s.).
- Fresh external set: no difference on any endpoint (ESG 0.393 vs 0.381; erased 14.3% vs 16.7%).
- Main test: no difference on ESG, CCR, erased claims or denials; **more claims of findings on lesion-free images**
  (13.5% vs 9.4%, +0.042 [0.012, 0.073], p = 0.006). The continuation never saw a lesion-free image (triplets exist
  only for lesion cases); this is the one change made to the trainer before v7 (below).

Two things the smoke test cannot tell apart: the objective, and 3,000 more cases of training on the same adapter.
v7 is built to separate them.

## Arms

All arms continue a stage-1 recipe adapter (`v4_s1` = run `v4q_cf_s0`; `v4q_cf_s1`; `v4q_cf_s2`) on the same 3,000
triplet cases (base views + transplant copies, seed-permuted and subsampled with the arm's seed), LR 2e-5, batch 8,
one pass, trainer `cmcc-v3`: trajectory replay of one view per case (round-robin) plus one lesion-free view every
three cases from the recipe's lesion-free pool.

| Arm | Run names | Objective |
| --- | --- | --- |
| CMCC | `v4q_cmccn_s0`, `v4q_cmccn_s1`, `v4q_cmccn_s2` | replay + 0.5·softplus(2 − (s(C) − s(E))) + 0.5·(s(O) − s(C))² + 0.5·(first-action log-prob difference)² |
| Matched-compute control | `v4q_sftc_s0`, `v4q_sftc_s1`, `v4q_sftc_s2` | replay only (all three weights 0): the same cases, the same number of optimizer steps, no paired-view term |

The smoke-test run `v4q_cmcc_s0` (trainer v2, no lesion-free replay) stays in the results as the exploratory run
and is not used in any v7 comparison.

## Confirmatory comparison (fixed now)

Paired bootstrap over cases, 2,000 resamples, seed 0, two-sided p as in the paper; each CMCC seed is paired with the
control at the same seed (s0 vs s0, s1 vs s1, s2 vs s2), and the three seed pairs are also pooled (cases from all
three pairs in one paired bootstrap).

**C4. Does the paired-view objective, and not the extra training, reduce edit-cue reliance on unseen tools?**

- **Primary endpoint:** erased-lesion claims (`target_hallucination_rate`) on the held-out tools pooled (TELEA +
  diffusion test sets).
- **Secondary endpoints**, same sets: ESG, control-edit denial (`random_denial_rate`), net utility.
- **Guards:** on the main test, claims of findings on lesion-free images (`natural_hallucination_rate`) must not be
  higher for CMCC than for the control by more than 0.03 at the pooled point estimate; on the fresh external set,
  ESG and net utility must not be lower by more than 0.03.

**C4 passes** if (i) the primary endpoint is lower for CMCC than for the control in every seed pair at the point
estimate, (ii) the pooled difference's 95% interval excludes zero, (iii) pooled ESG is not lower (difference >
−0.03) and (iv) both guards hold. If (i)–(ii) hold but a guard fails, the result is reported as **a trade, not a
gain**. Otherwise **C4 fails**: the smoke-test gain is attributed to extra training on the same adapter or to seed
noise, and the paper reports CMCC as a negative result.

**Supporting (reported, not decisive):** CMCC vs the recipe adapter itself at each seed (what the smoke test
measured), and CMCC vs C3 at seed 0; the main test and external centres for every arm; the training logs
(invariance and margin terms over steps).

**Not in v7** (to follow only if C4 passes, as a separate pre-registration): a noise-instead-of-inpaint arm, an
inference-time erase/sham probe tool, frontier-model evaluation of the same erase/sham pairs, and the stage-3
(final model) version of the objective with the validation-only selection rule of v6.

**Seeds and minimum effects.** Three seeds per arm, 0.03 margins as above. Nothing here is changed after the arms
are trained; departures are logged in `docs/RESULTS_LOG.md` with reasons.
