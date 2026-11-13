# MedScope v11 pilot: lead 4 retried with out-of-sample reports (the one declared retry)

Written and committed on 13 November 2026, after the v10 result and before anything below was run. The git history
of this file is the record. A **pilot**: one seed, test sets already used. It is the only retry of lead 4: if it does
not meet the go signal, lead 4 is closed and no further variant is tried.

## Why (from the v10 result, post hoc)

The v10 system (`docs/PREREGISTRATION_v10.md`) met the three primary conditions on the held-out tools (net utility
+0.090 against `v4q_sftc_s0`) but failed the fresh-external sensitivity guard (CCR 0.378 against the recipe's 0.560).
The deciding agent was trained on reports the other agents made **on images they had been trained on**: the
segmenter found a region on 96% of those lesion images (87% on unseen test images, about 50% at new centres), and the
recipe readers had been trained on the same views. The deciding agent therefore learned to trust "nothing found" far
more than the agents deserve on unseen images.

## The one change

The deciding agent is trained on reports made on **images no agent has seen in training**: every view of the v4
validation set (validation views and validation natural negatives; patient-disjoint from training and from every
test set; used before only to choose the stage of the v4 recipe). Readers (frozen recipe adapter `v4_s1`), the
segmenter (`specialist_v10`, unchanged) and the verifier (LaMa) are exactly as in v10. Because the validation set is
about half the size of the v10 training subset, the deciding agent trains for 3 epochs instead of 2; learning rate,
schedule shape, report dropout (0.25 per part) and starting adapter are unchanged. Run name `v4q_mas2_s0`.

Nothing else changes: the test-set reports are the v10 reports (same agents, same images), the ablations are the same
six (`v4q_mas2_s0`, `v4q_mas2nob_s0`, `v4q_mas2nos_s0`, `v4q_mas2nov_s0`, `v4q_mas2noc_s0`, `v4q_mas2dir_s0`), and
the comparators, go signal, guard-rails and contribution rule are those of `docs/PREREGISTRATION_v10.md`, applied by
`scripts/v10_rule.py --base mas2`.

## Known limits, stated before the run

- The validation images come from the same sources as training, not from new centres, so the agents' reliability
  there (segmenter about 89% on validation lesions) is still higher than at new centres (about 50%). The retry fixes
  the in-sample bias; it cannot fix the shift to new hospitals.
- The validation set was used once before, to choose the recipe's stage; it has not been used to train anything.

## Decision

GO or NO GO by the v10 rule. A GO leads to a confirmatory pre-registration (three seeds, a control trained on the
same validation views without reports). A NO GO closes lead 4.
