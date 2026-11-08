# MedScope v8: does the paired control change a model choice? (selection-rule test, reader-verified)

Written and committed on 8 November 2026, before any cohort described below exists and before the reader study's
answers were seen. The git history of this file is the record. Nothing here is a training experiment: v8 tests the
*measurement* claim, that the evidence sensitivity gap (ESG) with its matched control edit selects models better than
simpler rules built from the same views.

## Motivation (observed, retrospective, on the main test)

Table 5 of the manuscript already contains a ranking reversal: Qwen2.5-VL-7B claims an erased lesion in 5.5% of cases
against MedScope-4B's 9.6% (difference not significant, p = 0.11), yet its ESG is 0.146 against 0.758 and its
covered-and-correct rate 0.144 against 0.849. A rule that ranks by erased-lesion claims alone prefers a model that
says "absent" nearly everywhere; ESG, which subtracts the control-edit rate, does not. This is the kind of decision
the paired control is meant to change. It was observed after the fact and proves nothing on its own; v8 makes the
test prospective.

## Candidate models (fixed now)

The sixteen models of Table 5 (MedScope-4B, nine frontier models, six open models) plus the three-seed recipe,
no-counterfactual and DPO stage-1 arms (`v4q_cf_s*`, `v4q_nocf_s*`, `v4q_dpo_s*`) and the two constant policies.
Nothing is added after this commit.

## Selection rules (fixed now)

Each rule ranks the candidates on a *selection* set and the ranking is then judged on a *confirmation* set; the two
sets are disjoint by patient and by source image.

- **R1, erased claims alone:** rank by erased-lesion claims, lower is better.
- **R2, erased claims with a sensitivity floor:** drop every candidate whose covered-and-correct rate on unedited
  lesion images is below 0.75 on the selection set (the floor is the recipe's seed-to-seed minimum minus 0.05,
  rounded), then rank the rest as R1.
- **R3, paired control with the same floor:** apply the same floor, then rank by ESG, higher is better.

Ties (differences smaller than 0.005) are broken by net utility, then by model name; the tie rule is applied
mechanically by `scripts/v8_select.py`.

## Cohort

A new patient-disjoint cohort with at least two sources not used anywhere in the paper (candidates, to be fixed when
access is confirmed: a colonoscopy set other than Kvasir/HyperKvasir/ETIS, and a chest or breast set other than
ChestX-Det/SIIM/BUSI/BUS-UCLM), built with the standard view pipeline and, for the confirmation half, with an
inpainting tool not used in training (TELEA or diffusion). Minimum 150 lesion cases with all three views per half.

## Reader-verified outcomes

Before any model is run on the confirmation half, two blinded readers qualified for each modality (a third
adjudicates) judge every erasure and control view of the confirmation half (pairing hidden; views shuffled):
whether the finding is visible, whether a sign of it remains, and whether the image looks edited. A case is
**verified** when the erasure is judged absent by majority and the control view is judged present by majority.
Only verified cases enter the primary analysis; all cases are reported alongside, with indeterminate cases as a
sensitivity analysis.

## Primary endpoint and decision rule

On the verified confirmation cases, the quality of a selection rule is the **net utility of the model it selects**
(the paper's cost matrix), with the paired-outcome rate (withdraws the erased finding *and* retains the control-edited
one) as the secondary endpoint; both with sensitivity on unedited lesions and healthy-image claims reported as
guard-rails. The paired bootstrap over cases (2,000 resamples, seed 0) gives the interval for the difference between
the model selected by R3 and the model selected by R2.

**ESG adds value** if the R3-selected model has higher net utility than the R2-selected model on the verified
confirmation cases, with the interval excluding zero and the difference at least 0.05, and if the same direction holds
on the second source or unseen editor (replication). If R2 and R3 select the same model the test is **uninformative**
and reported as such. If R2's choice is better, the result is reported as **ESG does not add value over a
sensitivity-adjusted rule** and the paper's measurement claim is narrowed accordingly.

**Smallest worthwhile gain:** 0.05 in net utility (about half the recipe-vs-DPO difference on the fresh external
set). Nothing here changes after the cohort is opened; departures are logged in `docs/RESULTS_LOG.md`.
