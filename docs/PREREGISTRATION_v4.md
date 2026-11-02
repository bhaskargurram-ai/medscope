# MedScope v4: pre-registered training and selection plan

Written and committed on 1 November 2026, before any v4 data was built or any v4 model was trained.
The git history of this file is the record that the rules below were fixed in advance.

## Why a v4

The audit of all results (docs/RESULTS_LOG.md, 1 November 2026) found weaknesses of MedScope-4B that training
can address: false findings on healthy images above the best frontier model, a SLAKE CT/MRI regression after
general-VQA replay, lower sensitivity to real lesions at external centres, weak chest X-ray and small-lesion
results, a possible dependence on one inpainting tool (LaMa), a never-used windowing tool, and stages 2-3 that
did not improve on stage 1. v4 changes the training recipe only; the benchmark, metrics and cost matrix are
unchanged.

## Data (notebook 22)

- More training images (ChestX-Det, BUSI, TCGA-LGG: every image of the v4 training split instead of the first
  500 lesion / 250 lesion-free per source). The v4 split of these sources is drawn afresh (the earlier split
  used a seed formula that was later changed), with the existing test set protected as below.
- Validation enlarged to 100 lesion and 100 lesion-free images per added source, from the validation split.
- Training erasures in two versions where possible: LaMa for every case and tissue transplant for half of them. **Telea and Stable Diffusion are never
  used in training or validation**; they are test-only (held-out tools).
- Lesion-insertion views (training only): a real lesion moved into a healthy training image, answer "present".
- Degraded training views drawn from a larger set (adds resolution-relative low resolution, JPEG, motion blur).
- Training questions reworded with four training paraphrases; three further paraphrases are test-only.
- Confirmatory test sets that no model has been evaluated on before v4 is selected:
  - **fresh internal**: unused images of test-split patients not in the existing test set (ChestX-Det, TCGA-LGG);
  - **fresh external**: new public sources not used anywhere before (colonoscopy, breast ultrasound, brain MRI,
    chest X-ray): ETIS-LaribPolypDB (lesion images only), BUS-UCLM (no calipers/Doppler), BraTS 2023 meningioma
    (no TCGA subjects) and SIIM-ACR pneumothorax (asked only about pneumothorax, the one label it has); near-copies
    of any training or existing test image are removed, lesion-free images included.
  - The existing test set is kept exactly as it is. Every patient (or near-copy group) holding one of its images is
    removed from all v4 splits, and every patient seen in earlier training or validation is kept out of the fresh
    set; notebook 22 stops if any existing test image is missing from the source or differs from the stored copy.

## Training (notebook 23)

1. Stage 1: SFT from Qwen3.5-4B on the v4 data (16,000 views drawn at random from the pools, one pass); windowing trajectories on 30% of grey-scale images; always zoom
   on lesions under 2% of the image and repeat their cases twice; 50% of templated questions paraphrased.
2. Stage 2: rejection sampling from stage 1 (k = 4, temperature 1.2; 200 views per kind, 500 lesion-free and
   300 lesion-erased views), episodes from views the model mostly failed (at most half of the k tries right)
   repeated 3 times; trained on these plus 3,000 synthetic views at learning rate 5e-5.
3. Stage 3: general-VQA replay from stage 2 (5,000 views, learning rate 5e-5) with "absent" views at no less than 35% of the mix and
   "Is X healthy/normal?" replay questions balanced between Yes and No.

Windowing trajectories, always-zoom on small lesions and 50% paraphrased questions apply to the synthetic
trajectories of every stage. LoRA settings, learning rates and the vision encoder (frozen) are as in v3.

## Selection rule (fixed now)

Every candidate is evaluated on the v4 validation set (validation views and validation natural negatives) only.
Let U be validation net utility and H the validation rate of claimed findings on healthy images.

- The final model is **stage 3** if U(stage 3) >= U(stage 2) - 0.02 and H(stage 3) <= H(stage 2) + 0.02.
- Otherwise **stage 2** if U(stage 2) >= U(stage 1) - 0.02 and H(stage 2) <= H(stage 1) + 0.02.
- Otherwise **stage 1**.

**Amendment 1 (2 November 2026, 01:40 UTC; after the stage-1 validation result, before any stage-2/3
validation result and before any test result).** The validation set was enlarged for v4, so v4 cannot be compared
with the earlier final model (v3) through earlier numbers. v3 is therefore evaluated on the same v4 validation set,
and it remains the final model if the v4 stage chosen above is more than 0.02 below it in validation net utility.
Reason: on the 525 validation views shared with the earlier validation set, v4 stage 1 equals or beats v3's stage 1
(net utility 0.796 vs 0.788), but on the newly added chest X-ray and brain MRI validation images its numbers are
lower than v3-era numbers on the old, smaller images of those sources, which cannot be compared directly.

**Amendment 2 (2 November 2026; after the selection, before any v4 test result).** Further comparisons, all fixed
before any v4 model is tested: two extra stage-1 ablation arms (without counterfactual views but with healthy images
repeated to the same share of "absent" answers as the full recipe; erasures only, without edits elsewhere or
insertions), the held-out inpainting tools for every seed-0 stage-1 arm, the three frontier flagships at their
highest reasoning setting on the same 150 test cases as the cautious and few-shot runs and on standard VQA, and the
open models on standard VQA with their own plain prompt. None of these can change the selected model.

No decision threshold, prompt or setting is tuned after this choice. The selected model is then evaluated once
on every test set (notebook 24); no further v4 variant is trained after any v4 test result is seen.

## Reporting rule

Every MedScope claim in the paper comes from the single selected v4 model, on every test set. Earlier
checkpoints appear only as training history. Ablations (without counterfactual views), training seeds and the
second base model use the v4 stage-1 recipe and are compared like-for-like at stage 1 (notebook 25): the arm
without counterfactual views takes the same number of optimiser steps on the same learning-rate schedule. Seeds
change LoRA initialisation, data order and trajectory randomness; the 16,000-view training draw is the same for
every seed.
