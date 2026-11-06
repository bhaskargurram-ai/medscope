# MedScope v6 checks: preference training on top of the counterfactual recipe, seed replication, and a stage 4

Written and committed on 6 November 2026, after the v5 results (`results/v5_confirmation.md`) and before any arm
below was trained. The git history of this file is the record.

## What the v5 results showed

- C1: matching the control edit's shape and tool is not demonstrated to matter (matched and unmatched arms within
  seed noise on the main test, the held-out tools and three of four fresh-external sources; the fourth, SIIM
  pneumothorax, differs only through a response bias on a finding neither arm detects).
- C2: removal-based DPO reaches the recipe's ESG on new data. The two methods fail differently: the recipe claims
  fewer erased lesions (main test 12% vs 24%; held-out tools 16% vs 23%), DPO keeps more sensitivity (CCR 0.90 vs
  0.85 on the main test; 0.90 vs 0.81 on held-out tools) and denies fewer intact lesions after a control edit.

## Arms

| Arm | Run name | Training | Status at this commit |
| --- | --- | --- | --- |
| Recipe + DPO | `v4q_cfdpo_s0` | the stage-1 recipe adapter `v4q_cf_s0` continued with removal-based DPO on the same pools the recipe used (base views, transplant copies, insertions, lesion-free images); every usable pair, beta 0.1, LR 2e-5, batch 8, one pass | to be trained (notebook 34a) |
| DPO, seeds 1 and 2 | `v4q_dpo_s1`, `v4q_dpo_s2` | exactly as `v4q_dpo_s0`, from `v4q_nocf_s1` / `v4q_nocf_s2`, seeds 1 / 2 | to be trained (notebook 34b) |
| Stage 4 (conditional) | `v4_s4` | the selected v4 stage-3 model continued with the same DPO on the same pools as stage 3's SFT (recipe pools plus general-VQA replay views that have a yes/no answer); every usable pair, beta 0.1, LR 1e-5, one pass | trained only if C3 passes (notebook 35) |

## Confirmatory comparisons (fixed now)

Paired bootstrap over cases, 2,000 resamples, seed 0, two-sided p as in the paper.

**C3. Does preference training add to the recipe?** `v4q_cfdpo_s0` against `v4q_cf_s0` (same seed, same data,
the DPO pass is the only difference) on the fresh external set and the pooled held-out tools. The combination
**passes** if, on the fresh external set, CCR on unedited lesion images rises by at least 0.03 with the 95%
interval excluding zero and erased-lesion claims do not rise by more than 0.03 at the point estimate, and the same
two conditions hold on the pooled held-out tools. Net utility and ESG are reported alongside and must not fall by
more than 0.03 on either set (otherwise the combination is reported as a trade, not a gain). Main test and external
centres are reported as supporting.

**C2 replicated over seeds.** With `v4q_dpo_s1`/`s2` added, every C2 comparison is reported as mean ± sd over the
three recipe seeds against the three DPO seeds, and the fresh-external ESG and net utility differences are also
tested with the paired bootstrap on each seed pair (s0 vs s0, s1 vs s1, s2 vs s2); the C2 verdict is upgraded to
"recipe better" only if all three seed pairs agree in sign with intervals excluding zero, and to "DPO better" by the
same rule in the other direction; otherwise "no difference shown" stands.

**Stage 4 selection rule.** Run only if C3 passes. `v4_s4` is evaluated on the v4 validation set (validation views
and validation lesion-free images) only. With U = validation net utility and H = validation rate of claimed
findings on healthy images, stage 4 **replaces** stage 3 as the final model if U(stage 4) >= U(stage 3) + 0.02 and
H(stage 4) <= H(stage 3) + 0.02; otherwise stage 3 stays. If stage 4 is selected, every test set and every
comparison in the paper is rerun for it, with the stage-3 results kept in the paper as the previously selected
model; no test result is used for the selection.

**Seeds and minimum effects.** One seed for C3 (stated); 0.03 minimum effects as above. Nothing here is changed
after the arms are trained; departures are logged in `docs/RESULTS_LOG.md` with reasons.
