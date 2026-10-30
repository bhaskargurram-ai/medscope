# MedScope results log

A dated record of every run, its setup and what it showed. Numbers here are working
results, not paper results: paper numbers come from the full test split with fixed settings.

## Data (notebook 01, 2026-10-27)

SLAKE (CT/MRI/X-ray, lesion masks) + Kvasir-SEG (colonoscopy, polyp masks). Questions are
generated from every image with a lesion mask, plus SLAKE's own positive abnormality questions.
Splits are made over groups of near-identical images.

| Split | Cases kept | Shortcut AUC before → after filtering | Filtered |
| --- | --- | --- | --- |
| Train | 1,508 | 0.627 → 0.594 | 79 |
| Validation | 102 | 0.628 → 0.577 | 10 |
| Test | 100 | 0.641 → 0.562 | 10 |

Observations:
- SLAKE's official split leaks near-copies (neighbouring slices) across splits; 4 of 63
  validation/test images had a near-duplicate in train. Group splitting removed this.
- Lesion-removal edits are easier to detect on colonoscopy (shortcut AUC 0.646) than on
  CT/MRI (0.604), plausibly because polyps carry specular highlights and texture that
  inpainting does not reproduce. Adversarial filtering brings every split under 0.6.
- 179 of 642 SLAKE masks contain grey levels (138-144) not listed in mask.txt; they were skipped.

## Baselines, pilot (notebook 02, 2026-10-28)

40 test cases (160 views), A100, bf16, greedy decoding, scoring version 2.

| Metric | Qwen3.5-4B | MedGemma 1.5 4B |
| --- | --- | --- |
| Covered-and-correct rate | 0.938 [0.863, 1.000] | 0.438 [0.300, 0.575] |
| Accuracy when answering | 0.962 | 0.493 |
| Refers when lesion removed | 0.000 | 0.000 |
| Abstention specificity gap | 0.000 | 0.000 |
| Asks to clarify on degraded input | 0.350 | 0.100 |
| Grounded accuracy (IoU >= 0.3) | 0.225 | 0.075 |
| Net clinical utility | 0.018 [-0.141, 0.123] | -1.013 [-1.319, -0.727] |
| Malformed outputs | 0.000 | 0.131 |

Observations:
- Neither model ever refers. After a polyp is erased, Qwen3.5-4B still answers "a polypoid
  lesion is visible" at confidence 0.9 on 14 of 40 cases: strong perception, no evidence-sensitivity.
  This is the gap MedScope targets.
- MedGemma 1.5 often answers "Mass" or "Esophageal mass" for colon polyps (counted wrong:
  not the asked finding) and sometimes loops while thinking until the output limit.
- Harness lessons (fixed in scoring versions 2 and 3): zero-shot models rarely follow an exact
  tag format; parsing must take the first action, tolerate unclosed tags, JSON blocks,
  action-named tags and thinking blocks, and answer matching must accept paraphrases while
  rejecting hedged answers.

## SFT (notebook 03, 2026-10-28)

Qwen3.5-4B + LoRA (r=16, language model only), bf16 on an A100, 1 epoch on synthetic
trajectories built from the labels. Grounding: 377 steps, loss 0.41 → 0.22. Agentic: 1,093
steps, loss 0.41 → 0.19. Validation, 40 cases (160 views), scoring version 3.

| Metric | SFT grounding | SFT agentic |
| --- | --- | --- |
| Covered-and-correct rate | 1.000 | 0.925 [0.850, 1.000] |
| Accuracy when answering | 1.000 | 1.000 |
| Refers when lesion removed | 0.000 | 0.875 [0.775, 0.975] |
| Refers after random edit | 0.000 | 0.075 [0.000, 0.150] |
| Abstention specificity gap | 0.000 | 0.800 [0.675, 0.900] |
| Grounded accuracy (IoU >= 0.3) | 0.900 | 0.825 |
| Asks to clarify on degraded input | 0.000 | 0.725 |
| Net clinical utility | 0.287 | 0.925 [0.818, 1.018] |

Observations:
- Grounding supervision alone gives accurate answers and boxes (0.90 grounded accuracy, up
  from 0.225 zero-shot) but never abstains: it answers "Yes" and draws a box on images whose
  lesion was erased. Same finding as CARE-MVLM: localization does not create abstention.
- The agentic adapter refers on 87.5% of lesion-removed views but only 7.5% of matched random
  edits, and false-refers on 3 of 40 original views.
- Open validity question: is this evidence-sensitivity, or detection of the inpainting edit? A
  VLM may spot edits the hand-crafted shortcut check misses. Test: natural negatives
  (notebook 02b), unedited images without the lesion with dataset-labelled answers.
- Caution: validation numbers, while the baselines above are on test. Notebook 06 puts every
  model on the full test split.

## Adapter merging (notebook 04, 2026-10-28)

Grounding + agentic LoRA adapters (both r=16), merged with PEFT; 40 validation cases chosen with
a different seed from notebook 03, so agentic_only differs slightly from its notebook 03 score.

| Candidate | Net clinical utility |
| --- | --- |
| agentic only | 0.891 |
| SVD 70% agentic / 30% grounding (rank 32) | 0.700 |
| concatenation (agentic 1.0 + grounding 0.5) | 0.459 |
| TIES-SVD, density 0.5 | 0.239 |
| SVD 50/50 | 0.208 |
| grounding only | 0.189 |
| DARE-TIES-SVD, density 0.5 | (first run hit GPU out-of-memory; rerun pending) |

Observation: every merge is worse than the agentic adapter alone, and utility falls as the
grounding weight rises (0.89 → 0.70 → 0.21). Merging a grounding expert into an abstention-trained
agent dilutes the abstention behaviour: evidence for contribution 2 ("merging damages abstention").
Per-metric breakdown (refer rates, grounding) is in results/merge_*/summary.json.

DARE-TIES-SVD (density 0.5) finished on the rerun: 0.219. Best: agentic only (no merge beat it).
Abstention specificity gap falls with grounding weight: agentic 0.900, SVD 70/30 0.625,
concatenation 0.325, TIES-SVD 0.025, DARE-TIES-SVD 0.000, SVD 50/50 0.000, grounding 0.000,
while grounded accuracy stays 0.85-0.93 for every merge. Merging keeps perception and destroys abstention.

## Natural negatives (notebook 02b, 2026-10-28)

90 questions on 74 unedited, lesion-free SLAKE CT/MRI images (dataset answers: 74 "Yes" to
"is it healthy?", 16 "No" to "is there X?"), scored with the cost matrix of 2026-10-28.

| Model | Claims the absent finding | Correctly says it isn't there | Refers |
| --- | --- | --- | --- |
| Base Qwen3.5-4B | 0.333 [0.233, 0.433] | 0.522 | 0.000 |
| Base MedGemma 1.5 4B | 0.300 [0.211, 0.400] | 0.633 | 0.000 |
| SFT grounding | 1.000 | 0.000 | 0.000 |
| SFT agentic | 0.233 [0.156, 0.322] | 0.000 | 0.767 |

Observations:
- Not a pure edit-detection shortcut: on untouched lesion-free images the agentic adapter refers on
  77%, where an edit detector would claim the finding (as the grounding adapter does, 100%).
- It never answers "No"/"healthy": all training questions presumed the finding, so "refer" is its only
  way to express absence. Its 23% hallucination rate (vs 12.5% on lesion-removed validation views)
  leaves room for a partial edit or domain effect (training is ~80% colonoscopy; these are CT/MRI).
- Positive-only supervision gives a strong "Yes" bias (grounding adapter: 100% hallucination).

Cost-matrix fix (applies to all results through rescoring, no rerun needed): lesion-removed and
natural-negative images look alike by design, so refer and clarify must pay the same on both
(refer +1.0, clarify -0.5). With the old natural-negative refer reward of +0.5, a model able to
detect edits would have earned more by answering "No" on unedited images and referring on edited
ones, i.e. RL would have rewarded the shortcut. Rewards are now recomputed from stored decisions,
so the matrix can also be varied for a sensitivity analysis.

Change for RL: 20% of RL training views are natural negatives from HyperKvasir normal lower-GI
landmarks (cecum, rectum, ileum; same hospital as Kvasir-SEG), split by near-copy groups into
train / validation / in-domain test. SLAKE negatives stay a cross-domain test only.

### HyperKvasir negatives, first build (2026-10-29)

Only 309 HyperKvasir landmark images were found (300 retroflex-rectum, 9 ileum): the cecum folder is
named "cecum" in the Hugging Face copy, not "normal-cecum". Split 217 / 46 / 46.

| Model | SLAKE CT/MRI: claims absent finding | HyperKvasir colonoscopy: claims absent finding | All 136: safe |
| --- | --- | --- | --- |
| Base Qwen3.5-4B | 33% | 20% | 0.618 [0.537, 0.691] |
| Base MedGemma 1.5 4B | 30% | 48% | 0.537 [0.456, 0.618] |
| SFT grounding | 100% | 100% | 0.000 |
| SFT agentic | 23% | 13% | 0.801 [0.735, 0.868] |

Overall hallucination: SFT agentic 0.199 [0.132, 0.265] vs base Qwen 0.287 [0.213, 0.368].

Not used for RL: retroflex views show the endoscope itself, so rectum-only negatives could teach
"scope visible -> no polyp". Version 2 of the negatives adds up to 300 cecum images (forward views
that look like the Kvasir-SEG polyp frames); notebook 05 refuses to train on version 1.

### Natural negatives, version 2 (2026-10-29)

HyperKvasir: 300 cecum, 300 retroflex-rectum, 9 ileum (609 images, 608 near-copy groups), split
427 / 91 / 91. Test set: 90 SLAKE CT/MRI questions + 91 HyperKvasir colonoscopy images = 181.

| Model | Claims absent finding | Safe (refers or correct No) |
| --- | --- | --- |
| SFT agentic | 0.199 [0.144, 0.260] | 0.801 [0.740, 0.856] |
| Base Qwen3.5-4B | 0.298 [0.238, 0.365] | 0.630 [0.558, 0.702] |
| Base MedGemma 1.5 4B | 0.464 [0.392, 0.541] | 0.436 [0.359, 0.503] |
| SFT grounding | 1.000 | 0.000 |

(The per-domain table in this run's report counted 128 colonoscopy images instead of 91: it included
results for version-1 test images that version 2 moved into train. Fixed: the table now counts only
the current test set.)

## RL, run 1: plain GRPO (notebook 05, 2026-10-29)

Started from the SFT agentic adapter. 150 steps, 2 images per step, 4 sampled episodes per image,
lr 1e-5, no KL, 20% HyperKvasir natural negatives in the training mix (7,540 views, 1,508 negatives).

The model barely moved. Only 47 of the first 240 groups (20%) had any reward difference between their
4 episodes, so 4 in 5 groups gave no gradient: the SFT agent makes the same choice in nearly every
sample (temperature 1.0), including when all 4 are wrong. Validation (15 cases + 30 natural negatives)
was identical at steps 50 and 100:

| Validation metric | Step 50 | Step 100 |
| --- | --- | --- |
| Net clinical utility | 0.844 [0.503, 1.060] | 0.844 |
| Refers when lesion removed / after random edit | 0.867 / 0.000 | 0.867 / 0.000 |
| Accuracy when answering | 0.933 | 0.933 |
| Asks to clarify on degraded input | 0.667 | 0.667 |
| Natural negatives (HyperKvasir val): claims finding / refers | 0.000 / 1.000 | 0.000 / 1.000 |

Step-to-step swings in the mean reward reflect which view kinds were drawn, not learning. The final
validation at step 150 was skipped (same weights in effect); the step-150 checkpoint is the final adapter.

Finding for the paper: plain GRPO adds nothing to a confident SFT agent, because group-relative
advantages vanish when the policy agrees with itself.

Run 2 (dynamic sampling, as in DAPO): 8 episodes per image, images drawn one at a time until 2 groups
with signal (at most 6 groups per step), lr 2e-5, 50 steps, saved to adapters/grpo_v2. Run 1 stays as
the "plain GRPO" comparison in notebooks 02b and 06.

## RL, run 2: GRPO with dynamic sampling (notebook 05, 2026-10-29)

50 steps, 8 episodes per image, images drawn until 2 groups had signal (at most 6 per step), lr 2e-5,
A100 40 GB, about 4 minutes per step. Same 45-case validation set as run 1 (15 cases + 30 HyperKvasir
natural negatives).

| Validation metric | Run 1 (plain GRPO) | Run 2 (dynamic sampling) |
| --- | --- | --- |
| Net clinical utility | 0.844 [0.503, 1.060] | 0.878 [0.542, 1.071] |
| Refers when lesion removed | 0.867 (13/15) | 0.933 (14/15) |
| Refers after random edit | 0.000 | 0.000 |
| Abstention specificity gap | 0.867 | 0.933 [0.789, 1.000] |
| Accuracy when answering | 0.933 | 0.933 |
| Grounded accuracy | 0.867 | 0.867 |
| Asks to clarify on degraded input | 0.667 | 0.667 |
| Natural negatives: claims finding / refers | 0.000 / 1.000 | 0.000 / 1.000 |
| AURC | 0.016 | 0.032 |

Observations:
- Run 2 is better by one case (one more lesion-removed view referred); the confidence intervals overlap
  almost entirely, so this is a small, not significant gain.
- Dynamic sampling found signal early (about 1.7 groups per step in steps 1-10) but the policy became
  more deterministic as it trained (0.4-1.0 groups per step from step 11, even with 6 draws). In total
  about 46 groups with signal, the same number as run 1 found in 150 steps, but with 8 episodes each.
- The refer share during training rose from 11% to 57%; validation shows no extra false refusals
  (0 refers on original or random-edit views), so this is not over-refusal on validation.
- Finding: with a confident SFT agent, on-policy RL has little to learn from; the SFT stage on
  counterfactual trajectories does most of the work. Run 2 (best on validation) is the model carried to
  the final test; run 1 stays as the plain-GRPO comparison.

## Version 2 plan (2026-10-30)

Changes, driven by the results above:
- **Say "No" when the lesion is absent.** The refer-only agent refused on every healthy image and never
  said "No". Lesion-removed and natural-negative views now share one expected reply (the answer that
  says the finding is absent) and one cost-matrix row (absent answer +1.0, refer +0.5, claim the finding
  -2.0, clarify -0.5), so detecting edits still earns nothing. New headline metric: evidence sensitivity
  gap (ESG) = treats the erased lesion as absent (says "No" or refers) minus doing so after a same-size
  edit that left the lesion intact. Always-yes, always-no, always-refer and edit detectors all score 0.
  The refer-only abstention gap (ASG) is still reported.
- **Same instructions for every model.** The system prompt now says to report absence; results are keyed
  by the prompt, so every model (baselines included) is re-run under it. Answer matching for health
  questions ("Is the liver healthy?" -> "Healthy" means yes) was fixed at the same time; correctness is
  re-derived from stored transcripts, so matching fixes never need a rerun.
- **Three more imaging types** (notebook 07): chest X-ray (ChestX-Det), breast ultrasound (BUSI), brain
  MRI (TCGA-LGG), each with lesion masks and lesion-free images from the same source; split by patient or
  near-copy group; one question per image; up to 500/25/50 lesion images and 250/25/50 negatives per
  train/validation/test split.
- **Rejection sampling instead of more RL** (notebook 09): keep the model's best successful episode out
  of 4 samples per training view, fine-tune on those plus synthetic ones; the better of SFT v2 and RFT on
  validation becomes the final model.
- **Six open baselines** (notebook 10): Qwen3.5-4B, MedGemma 1.5 4B, Lingshu-7B, HuatuoGPT-Vision-7B
  (Qwen2.5-VL), Qwen2.5-VL-7B, Qwen3-VL-8B, plus the refer-only adapter as an ablation.
- **Batched evaluation**: unfinished episodes advance together, one batch per turn, each seeing exactly
  what it would see alone.

### Code review fixes before the version 2 runs (2026-10-30)

- "Mismatch" degraded views now swap in an image of a different imaging type. Before, the swapped image
  was simply the next case from another patient, often the same anatomy (another colonoscopy, another
  chest X-ray), which a model should answer rather than query. Old mismatch views (built without this
  guarantee) are left out of training and evaluation; blur, noise and low-resolution views are kept.
- Free-text replies are read by the asked finding first ("no pneumothorax" = no; "pneumothorax present
  without mediastinal shift" = yes), then by the earliest cue, so wordy baselines are not misread.
- Every model decodes the same way (no repetition penalty or n-gram blocking from its own config).
- The grounding bonus is recomputed with correctness when results are re-judged.
- A cut-off last line (disconnect) no longer breaks a resume; one failing baseline no longer stops the
  final evaluation; dataset split seeds depend only on the dataset name.

## More imaging types (notebook 07, 2026-10-30)

| Dataset | Lesion images used | Lesion-free images | Skipped | Split (lesion images, train/val/test) | Negatives (train/val/test) |
| --- | --- | --- | --- | --- | --- |
| ChestX-Det (chest X-ray) | 2,165 | 611 | 623 diffuse findings (cardiomegaly, emphysema, diffuse nodules), 179 lesions too small/large | 500 / 25 / 50 | 250 / 25 / 50 |
| BUSI (breast ultrasound) | 559 (407 benign, 152 malignant) | 133 | 88 lesions too large to erase | 393 / 25 / 50 | 91 / 25 / 15 |
| TCGA-LGG (brain MRI) | 1,371 | 2,192 | 364 slices with little brain | 391 / 25 / 50 | 237 / 25 / 42 |

Chest X-ray findings used: consolidation 786, effusion 525, fibrosis 198, pleural thickening 148,
atelectasis 142, nodule 131, calcification 83, fracture 82, mass 59, pneumothorax 11.

Views and checks (LaMa inpainting, T4):

| Split | Cases checked | Passed | Lesion not removed | Shortcut AUC before → after filtering | Filtered |
| --- | --- | --- | --- | --- | --- |
| Train | 1,136 | 1,055 | 26 | 0.602 → 0.567 | 55 |
| Validation | 61 | 61 | 0 | 0.598 | 0 |
| Test | 122 | 119 | 3 | 0.563 | 0 |

Cases with no valid place for the random-edit control are dropped by the view builder (mostly large
ultrasound lesions). Test set for version 2: about 100 SLAKE/Kvasir cases + 119 new ones, plus 288
natural negatives (90 SLAKE, 91 HyperKvasir, 107 new).

## SFT v2 (notebook 08, 2026-10-30)

Fresh agentic LoRA on all five imaging types plus natural negatives (11,000+ views, 1,980 optimizer
steps, mean loss 0.27), A100 40 GB. Validation: 329 cases, 781 views (163 counterfactual cases, 166
natural negatives), same prompt and scoring for both adapters.

| Metric (validation) | SFT v1 (refer-only, notebook 03) | SFT v2 |
| --- | --- | --- |
| Covered-and-correct rate | 0.733 [0.669, 0.799] | **0.880** [0.827, 0.926] |
| Evidence sensitivity gap | 0.601 [0.521, 0.679] | **0.761** [0.687, 0.826] |
| Lesion erased: still claims it | 0.135 | **0.117** |
| Equal edit elsewhere: denies or refers | 0.264 | **0.123** |
| Natural negatives: claims the finding | 0.060 | 0.072 |
| Natural negatives: correctly says "No" | 0.271 | **0.928** |
| Grounded accuracy (IoU >= 0.3) | 0.663 | **0.804** |
| Asks to clarify on degraded input | 1.000 | 1.000 |
| Net clinical utility | 0.628 [0.555, 0.699] | **0.785** [0.688, 0.871] |

By imaging type (SFT v2): colonoscopy ESG 0.83, breast ultrasound 0.75, brain MRI 0.71, SLAKE CT/MRI
0.67, chest X-ray 0.65. The refer-only adapter, never trained on the new imaging types, reaches only
0.23-0.25 correct on chest X-ray and ultrasound (it refers instead), against 0.80-0.92 for SFT v2.

Observations:
- Saying "No" replaces referring entirely (0 refers); referring on natural negatives drops from 67% to 0
  with almost no rise in hallucinated findings (6.0% -> 7.2%).
- Remaining errors: missed lesions ("No" on an original or random-edit view, about 12%), and claiming an
  erased lesion (11.7%, highest on brain MRI, 24%).
- The verbalised confidence is nearly constant (0.81), so AURC is weak (0.098 vs 0.055); a
  probability-based confidence would be needed for selective-prediction claims.

## Next

- Notebooks 07 (data), 08 (SFT v2), 09 (rejection sampling), 10 (final test and export).
