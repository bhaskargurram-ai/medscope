# MedScope v5 checks: pre-registered confirmation of what the control edit adds

Written and committed on 6 November 2026, before either of the two new training arms below was built or trained
(no `unmatched/` views and no `v4q_unm_s0` or `v4q_dpo_s0` adapter existed at this commit). The git history of
this file is the record. No existing model, number or test set changes; the selected model stays v4 stage 3.

## Question

The factorial ablation (notebook 29) showed that training with MedScope's control edit (the erasure's own edit,
same shape and same tool, placed away from the lesion) raises correct answers on unedited lesion images and reduces
denial of an intact lesion after an unrelated edit. Two things it did not show, which the independent review asked
for:

1. **Does matching matter?** Would any edit elsewhere do, or does the control have to match the erasure's shape and
   tool?
2. **Does the recipe beat the closest established method?** Removal-based preference training (DPO on pairs that
   contrast "the finding is absent" with "the finding is present" on erased and unedited images; oDPO and relatives)
   is the nearest existing approach to teaching a model not to describe what is not there.

## Arms (all stage-1, seed 0, base Qwen3.5-4B, same LoRA configuration)

| Arm | Run name | Control views | Training | Status at this commit |
| --- | --- | --- | --- | --- |
| Matched control | `v4q_ctrl_s0` | erasure's own edit, same shape and tool, elsewhere | SFT, S1 steps | trained 5 Nov (notebook 29) |
| Unmatched control | `v4q_unm_s0` | an ellipse of half or twice the erasure's area, random aspect and orientation, elsewhere, filled with the other training tool (transplant for LaMa erasures, LaMa for transplant erasures) | SFT, same data otherwise, same S1 steps and schedule | to be trained (notebook 33) |
| No control | `v4q_tgt_s0` | none (erasures only) | SFT, S1 steps | trained (notebook 25) |
| Removal-based DPO | `v4q_dpo_s0` | none | SFT without counterfactual views (`v4q_nocf_s0`, S1 steps), then DPO on 8,000 preference pairs from the same cases: erased image (chosen: absent; rejected: the finding with its former box), unedited lesion image (chosen: the finding with box; rejected: absent), lesion-free image (chosen: No; rejected: Yes); beta 0.1, LR 2e-5, batch 8 pairs, one pass | to be trained (notebook 33) |
| Recipe | `v4q_cf_s0` | matched control plus lesion insertions | SFT, S1 steps | trained (notebooks 23/25) |

The DPO arm receives *more* compute than any SFT arm (a full stage 1 plus the preference pass); this favours the
baseline and is stated as such. Telea and diffusion remain unseen by every arm.

## Confirmatory comparisons (fixed before any result is seen)

Paired bootstrap over cases, 2,000 resamples, seed 0, 95% intervals, two-sided p as in the paper (Section 3.8).

**C1. Matched vs unmatched control.** Test sets: the fresh external set (316 cases, never used for any selection)
and the two held-out-tool copies of the main test (Telea and diffusion edits; both tools unseen by both arms).
Primary endpoint: random-removal denial rate (refusing or denying an intact lesion after a control edit; lower is
better). Decision rule: matching matters if the matched arm's denial rate is lower by at least 5 percentage points
with the 95% interval excluding zero on the fresh external set **and** on the pooled held-out-tool sets, while
(constraints) its erased-lesion claim rate is not higher by more than 5 points at the point estimate and its CCR on
unedited lesion images is not lower by more than 3 points. If the unmatched arm is within these margins of the
matched arm, the benefit belongs to control edits in general and the paper's novelty claim narrows to "training
with control edits", with matching reported as not demonstrated. Any other pattern is reported as inconclusive.

**C2. Recipe vs removal-based DPO.** Same test sets plus the main test. Primary endpoints: ESG and net utility
(the paper's primary outcomes), each compared recipe minus DPO. Decision rule: the recipe is better than the
closest method if both differences are positive with 95% intervals excluding zero on the fresh external set; if
either interval includes zero there, the paper reports the recipe as not shown to beat removal-based preference
training on new data, whatever the main test shows. Secondary: random-removal denial rate (DPO sees no control
edits, so a higher denial rate under DPO would be the specific signature the control edit is meant to prevent),
erased-lesion claims, CCR.

**Minimum worthwhile effects**, chosen before the runs: 5 points of denial rate (C1); 0.05 ESG and 0.05 net
utility (C2). Effects smaller than these are reported as too small to matter even if significant.

**Seeds.** One seed per arm, like the factorial. The stage-1 seed-to-seed standard deviation observed for the
recipe (`results/v4_seeds_test.md`) is printed next to every C1 and C2 difference; a difference smaller than twice
that standard deviation is flagged as within seed noise.

**Main-test results** for C1 are reported as supporting evidence only (the main test guided the factorial's
interpretation). Nothing in this plan is changed after the arms are trained; any departure is logged in
`docs/RESULTS_LOG.md` with its reason.
