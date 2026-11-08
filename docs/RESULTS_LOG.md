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

## Rejection-sampling fine-tuning (notebook 09, 2026-10-30)

SFT v2 sampled 4 episodes on 150 training views of each kind; at least one success on 95-100% of views
(per-sample success: degraded 100%, natural negative 95%, random edit 87%, original 84%, erased 84%).
Fine-tuned from SFT v2 on the kept episodes plus 3,000 synthetic views (lr 5e-5, about 670 steps, loss
about 0.21 throughout). Same validation set as notebook 08.

| Metric (validation) | SFT v2 | SFT v2 + RFT (final) |
| --- | --- | --- |
| Net clinical utility | 0.785 [0.688, 0.871] | **0.801** [0.702, 0.887] |
| Evidence sensitivity gap | 0.761 | **0.767** |
| Lesion erased: still claims it | 0.117 | **0.104** |
| Natural negatives: claims the finding | 0.072 | **0.060** |
| Covered-and-correct rate | 0.880 | 0.880 |
| Grounded accuracy | 0.804 | 0.804 |

A small, consistent gain (fewer hallucinated findings on both erased and healthy images, same accuracy),
within the confidence intervals. Breast ultrasound improved most (net utility 0.69 -> 0.80), chest X-ray
ESG dropped (0.65 -> 0.55) while its healthy-image hallucination halved (0.16 -> 0.08). Chosen as the final
model by validation net utility. Stated confidence stays near 0.8 (AURC on stated confidence 0.205);
the final test reports the token-probability AURC as well.

## Final test and external centres, first look (notebooks 10 and 11, 2026-10-31)

Main test: 507 cases (219 counterfactual cases x 4 views + 288 natural negatives), 1,115 views.

| Model (test) | CCR | ESG | Claims erased lesion | Claims finding on healthy | Grounded | Net utility | Malformed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **MedScope-4B (final)** | **0.865** | **0.758** | 0.114 | **0.083** | **0.813** | **0.752** [0.673, 0.829] | 0.000 |
| Refer-only SFT (ablation) | 0.660 | 0.594 | 0.059 | 0.132 | 0.575 | 0.537 | 0.000 |
| Qwen3-VL-8B | 0.553 | 0.297 | 0.128 | 0.125 | 0.388 | 0.186 | 0.000 |
| Qwen3.5-4B (base) | 0.758 | 0.338 | 0.420 | 0.194 | 0.192 | 0.134 | 0.014 |
| MedGemma 1.5 4B | 0.660 | 0.169 | 0.534 | 0.240 | 0.137 | -0.417 | 0.212 |
| Qwen2.5-VL-7B | 0.144 | -0.059 | 0.055 | 0.247 | 0.005 | -0.946 | 0.352 |
| Lingshu-7B | 0.005 | 0.000 | 0.000 | 0.000 | 0.000 | -0.953 | 0.961 |
| HuatuoGPT-Vision-7B | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | -1.000 | 1.000 |

MedScope's token-probability AURC is 0.022 (stated-confidence AURC 0.171): its own answer probability
ranks right and wrong answers well, unlike its stated confidence.

External centres (CVC-ClinicDB, QaTa-COV19, BUS-BRA, BraTS-Africa; 169 cases, 526 views):
MedScope CCR 0.752, ESG 0.664, claims erased lesion 0.109, claims finding on healthy 0.04, net utility
0.534 [0.414, 0.650], token AURC 0.053; Qwen3-VL-8B ESG 0.227, net 0.037; MedGemma ESG 0.185, net -0.262.

Scoring fix before the paper tables: Lingshu and HuatuoGPT answer in plain prose and never use the
action format (100% "no action found"; e.g. "The image shows a polypoid lesion..."), Qwen2.5-VL in 35%
of replies. Scoring those as malformed measures format-following, not the model. From now on a reply
with no action tag is read as the model's decision for every model: a plain answer, or a request for a
better image when it says the image is blurred, noisy, low resolution or the wrong image. Stored
results are rescored without rerunning (notebook 13); the plain-prose rate is reported per model.

Edit detector, first design: a ResNet-18 separates lesion-removed from random-edit views with AUC 0.929
and lesion-removed from original with 0.932. Both pairs differ in whether the lesion is visible, so this
measured lesion detection, not edit traces. Redesigned: the main test is now random edit vs original
(both show the lesion, only one is edited); lesion-removed vs random edit is kept as a reference.

## Generalisation (notebook 11, 2026-10-31)

External centres, paired with MedScope on 169 cases (p from paired bootstrap):

| vs MedScope | ESG | Claims erased lesion | Net utility |
| --- | --- | --- | --- |
| MedScope-4B | 0.664 | 0.109 | 0.534 |
| Qwen3.5-4B | 0.328 (p<0.001) | 0.445 | 0.160 |
| MedGemma 1.5 | 0.185 (p<0.001) | 0.496 | -0.262 |
| Qwen3-VL-8B | 0.227 (p<0.001) | 0.059 | 0.037 |

By source (MedScope): BraTS-Africa ESG 0.93, CVC-ClinicDB 0.80, BUS-BRA 0.69, QaTa-COV19 0.15 (claims the
erased opacity 45%). COVID opacities are diffuse; erasing them is far less complete than erasing a
polyp or tumour, so this is reported as a limitation of the counterfactual for diffuse findings. Only
BraTS-Africa provides lesion-free images among the external sources.

Standard medical VQA (same agent prompt and matching for all; low absolute numbers for every model):

| Accuracy | MedScope | Qwen3.5-4B base | MedGemma 1.5 | Qwen3-VL-8B |
| --- | --- | --- | --- | --- |
| VQA-RAD | 0.415 | 0.481 | 0.379 | 0.452 |
| SLAKE test | 0.387 | 0.570 | 0.407 | 0.477 |
| PathVQA | 0.260 | 0.293 | 0.230 | 0.250 |

Closed (yes/no) questions hold (VQA-RAD 0.673 vs 0.657); open questions drop (SLAKE 0.215 vs 0.424): the
model over-uses "No abnormality" ("Where are the kidneys?" -> "No abnormality") because every training
question was about a lesion. Fix in notebook 15 (SFT v3): replay ordinary questions from the VQA-RAD,
SLAKE and PathVQA training splits, excluding any image near-identical to an evaluation image and any
SLAKE image in our validation or test sets; replaces the final model only if validation net utility is
within 0.02 of it (rule fixed before testing).

## Frontier models (notebook 12, 2026-10-31)

Same 150 test cases (345 views) for both, paired with MedScope on those cases:

| On the same 150 cases | MedScope-4B | GPT-6-sol | Gemini-4-argon |
| --- | --- | --- | --- |
| Correct on lesion images (CCR) | 0.860 | 0.853 (p=0.91) | 0.860 (p=1.0) |
| Evidence sensitivity gap | **0.765** | 0.382 (p<0.001) | 0.441 (p<0.001) |
| Claims the erased lesion | **0.103** | 0.471 (p<0.001) | 0.412 (p<0.001) |
| Claims a finding on a healthy image | 0.073 | 0.293 (p=0.001) | 0.061 (p=0.84) |
| Net utility | **0.743** | 0.271 (p<0.001) | 0.545 (p=0.013) |

Both frontier models follow the action format (0% malformed; GPT 2.6% plain prose). They are as accurate
as MedScope when the lesion is there, but claim an erased lesion 4x as often, typically with a box where
it used to be ("a large sessile polyp occupying the central portion"). GPT also reports findings on 29%
of healthy images; Gemini does not. Gemini's stated confidence ranks its answers well (AURC 0.018).
Note for the paper: some SLAKE "healthy" labels may be noisy (Gemini describes a mass on images SLAKE
labels as a healthy brain); this affects every model equally and is worth a manual look at a sample.

## Evaluation additions for the paper (2026-10-30)

- **Confidence from token probabilities** for every local model (geometric mean of the greedy
  probabilities of the answer tokens), with its own AURC, because fine-tuning collapsed the stated
  confidence to a constant.
- **Paired bootstrap tests** (same cases for both models) for net utility, ESG, CCR and both
  hallucination rates.
- **Learned edit detector** (ResNet-18): can a classifier tell lesion-removed from same-size random
  edits? AUC near 0.5 means the edits themselves give nothing away.
- **External validation** (notebook 11), sources never used in training: CVC-ClinicDB (Barcelona),
  QaTa-COV19 (Qatar), BUS-BRA (Brazil), BraTS-Africa 2023 (axial FLAIR slices with the largest tumour,
  plus a tumour-free slice of the same patient). Mirrors: TahaKoleilat/MedCLIPSeg test folders,
  MedOtter/brats2023-ssa. SIIM pneumothorax and BraTS 2020/2021 were not used: they share images with
  the training sources (NIH ChestX-ray14, TCGA).
- **Standard medical VQA** (notebook 11): VQA-RAD test (451), SLAKE English test and PathVQA test (300
  each), scored with the benchmark's answer matching, closed and open questions separately.
- **Frontier models** (notebook 12, CPU): OpenAI and Gemini through the same agent loop, on a fixed
  150-case test subset; compared with MedScope on exactly those cases.

## Next

- Notebooks 07 (data), 08 (SFT v2), 09 (rejection sampling), 10 (final test and export).

## 2026-10-31: expanded frontier comparison set up (notebook 12 v2)

Nine frontier models on the full test set (all cases, paired with MedScope): OpenAI gpt-6-sol,
gpt-6-astra, gpt-6.1-sol; Anthropic claude-fable-5-1, claude-opus-5-5, claude-sonnet-5-5; Google
gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. Each provider's default settings (reasoning
on where it is the default), the same prompt, images and scoring as every other model. Token usage is
recorded per call from the providers' own counts (usage.json) and priced at the 2026-10-31 list
prices; a 20-case pilot per model measures the cost per view before the full run.

## 2026-10-31: notebook 14 (ablation) and notebook 15 (SFT v3 with VQA replay)

**Ablation: the same fine-tuning without counterfactual views** (sft_nocf vs sft_v2, paired, 507 test cases):
net utility 0.760 vs 0.494 (+0.267 [+0.202, +0.333], p<0.001); ESG 0.758 vs 0.402 (+0.356, p<0.001);
claims an erased lesion 11.9% vs 53.0% (-41 points, p<0.001); claims a finding on a healthy image 8.7% vs
22.2% (p<0.001); CCR 0.877 vs 0.929 (-0.053, p<0.001: the ablation answers "Yes" more often, which helps on
real lesions and fails when the lesion is gone). External centres (169 cases): ESG +0.176 (p=0.001),
erased-lesion claims 10.9% vs 41.2%, healthy-image claims 8.0% vs 36.0% (both p<0.001), net +0.083 (p=0.19).
The counterfactual views are what teach evidence sensitivity; everything else in the recipe is held fixed.

**SFT v3 (continued from RFT with general VQA replay), chosen by validation net utility (0.804 vs 0.801):**
- Test vs RFT: net 0.714 vs 0.752 (p=0.15, not significant), ESG 0.744 vs 0.758 (p=0.52), CCR 0.881 vs 0.865,
  erased-lesion claims 13.7% vs 11.4% (p=0.18), healthy-image claims 14.6% vs 8.3% (p<0.001).
- External: no significant difference on any metric (ESG 0.672 vs 0.664).
- Standard VQA (all closed / open): SLAKE 0.767 (base Qwen3.5-4B 0.570, RFT 0.387); VQA-RAD 0.554 (base 0.481,
  RFT 0.415); PathVQA 0.520 (base 0.293, RFT 0.260). The VQA regression is gone. Note for the paper: v3 saw the
  three benchmarks' train splits (images of the test splits excluded), the base model is zero-shot.
- Final model: sft_v3 (prefix v2_medscope3). It keeps the evidence-sensitivity results and is a general
  medical VQA model as well; the cost is more false findings on healthy images (14.6% vs 8.3%).

## 2026-10-31: nine frontier models, full test set (notebook 12)

All 507 cases (1,115 views), same prompt, tools and scoring as every other model; each provider's
default settings. MedScope-4B (final, v3) for reference: CCR 0.881, ESG 0.744, erased 13.7%, healthy 14.6%, net 0.714.

| Model | CCR | ESG | Claims erased lesion | Claims finding on healthy | Grounded | Clarify on degraded | Net | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-4-argon | 0.874 | 0.470 | 41.1% | 9.0% | 0.726 | 0.941 | 0.565 | $6.08 (770 views) |
| claude-sonnet-5-5 | 0.870 | 0.402 | 48.4% | 16.7% | 0.589 | 0.353 | 0.381 | $12.50 |
| gemini-3.1-pro-preview | 0.849 | 0.384 | 51.6% | 26.7% | 0.712 | 0.412 | 0.306 | $12.40 |
| gpt-6-sol | 0.829 | 0.342 | 51.6% | 25.7% | 0.639 | 0.506 | 0.261 | $2.45 (770 views) |
| claude-fable-5-1 | 0.856 | 0.342 | 52.1% | 23.3% | 0.388 | 0.559 | 0.255 | $54.82 |
| claude-opus-5-5 | 0.863 | 0.329 | 53.9% | 23.6% | 0.735 | 0.629 | 0.358 | $15.54 |
| gpt-6.1-sol | 0.888 | 0.324 | 58.9% | 30.9% | 0.708 | 0.488 | 0.276 | $3.32 |
| gpt-6-astra | 0.886 | 0.306 | 58.9% | 27.8% | 0.717 | 0.547 | 0.309 | $16.18 |
| gemini-3.8-flash | 0.868 | 0.269 | 61.6% | 27.8% | 0.721 | 0.671 | 0.263 | $9.13 |

Full-run API cost $132.42 (plus earlier 150-case runs and pilots). Every frontier model matches MedScope
on real lesions (CCR 0.83-0.89) and claims an erased lesion in 41-62% of cases. Best frontier ESG 0.470
(gemini-4-argon); gemini-4-argon also has the fewest healthy-image false findings of any model (9.0%,
below MedScope v3's 14.6% and close to MedScope RFT's 8.3%). Frontier refer rates are near zero: they
answer, rarely abstain. Paired tests against MedScope come from notebook 13.

## 2026-10-31: paper tables (notebook 13)

- Plain-prose rescoring of the open baselines (leaderboard): Lingshu-7B CCR 0.527, ESG 0.416, erased-lesion
  claims 32.0%, net -0.249; HuatuoGPT-Vision-7B CCR 0.498, ESG 0.265, net -0.426; Qwen2.5-VL-7B CCR 0.144,
  ESG 0.146, net -0.742; MedGemma 1.5 ESG 0.283, net -0.255. Bug: the paired tests, per-imaging-type and VQA
  tables still read the unrescored outcomes (Lingshu/HuatuoGPT at 0); fixed (evaluate writes scored.jsonl,
  every table reads it). Rerun notebook 13 for the corrected tables.
- MedScope v3 vs all nine frontier models (paired, 507 cases): ESG and erased-lesion claims better against
  every one (all p<0.001); CCR not different from 8 of 9 (better than gpt-6-sol, p=0.004); net utility better
  against all (gemini-4-argon +0.150, p=0.003; others p<0.001). Healthy-image false findings: v3 better than
  7 of 9; not different from claude-sonnet-5-5 (p=0.45); worse than gemini-4-argon (14.6% vs 9.0%, p=0.033).
- Learned edit-trace test (ResNet-18): random edit vs original AUC 0.832 [0.799, 0.868]; lesion removed vs
  random edit 0.928 [0.904, 0.948]. The inpainting leaves a trace a trained CNN can find. MedScope's denial
  rate on random-edit views is 11.4%, so its "not there" answers do not follow edit traces; this is what the
  matched control is for, and the paper must state the edit visibility rather than claim invisible edits.
- v3 regressed on SLAKE CT/MRI against RFT: erased-lesion claims 0% -> 24%, healthy-image claims 17% -> 33%,
  ESG 0.59 -> 0.47, net 0.24 -> -0.06 (example: answers "No" to "Is the lung healthy?" on healthy images),
  plausibly from SLAKE's own VQA questions in the replay. Other imaging types same or better.
- Token-probability AURC: v3 0.021 (test), 0.078 (external); RFT 0.022 / 0.053.

Rerun of notebook 13 with the rescored tables (2026-10-31): MedScope v3 vs the open baselines, paired:
Lingshu-7B ESG 0.416 (+0.329), erased-lesion claims 32.0% (-18 points), healthy-image claims 12.5% (not
different, p=0.48); HuatuoGPT-Vision-7B ESG 0.265, erased 30.1%, healthy 22.9% (p=0.003); MedGemma 1.5 ESG
0.283, erased 54.3%; Qwen3-VL-8B ESG 0.297, erased 12.8% (not different, p=0.82: it rarely answers, CCR 0.553).
Standard VQA after rescoring (all questions): Lingshu SLAKE 0.637, VQA-RAD 0.479, PathVQA 0.390; HuatuoGPT
0.450 / 0.470 / 0.380; MedGemma 0.440 / 0.448 / 0.277; MedScope v3 0.767 / 0.554 / 0.520 stays best on all three.
gpt-6-sol after rescoring: CCR 0.829 (MedScope +0.053, p=0.013).

## 2026-10-31: robustness checks (notebooks 16 and 17, first results)

Tools switched off (every tool call refused, main test, 507 cases):
| Model | CCR | ESG | Erased-lesion claims | Healthy-image claims | Grounded | Net |
| --- | --- | --- | --- | --- | --- | --- |
| RFT, tools on / off | 0.865 / 0.847 | 0.758 / 0.726 | 11.4% / 11.9% | 8.3% / 11.1% | 0.813 / 0.804 | 0.752 / 0.675 |
| v3, tools on / off | 0.881 / 0.783 | 0.744 / 0.703 | 13.7% / 6.8% | 14.6% / 12.8% | 0.817 / 0.758 | 0.714 / 0.601 |
Evidence sensitivity comes mostly from training (ESG 0.70-0.73 with no tools); the tools add accuracy on real
lesions (v3 CCR +0.10) and net utility (+0.08 to +0.11). Without tools v3 says "not there" more often overall
(random-edit denials 22% vs 11%).

Frontier flagships at the external centres (169 cases; MedScope v3: CCR 0.773, ESG 0.672, erased 10.1%,
healthy 10.0%, net 0.522): gpt-6-astra CCR 0.945, ESG 0.277, erased 66.4%, healthy 24%, net 0.424;
claude-opus-5-5 CCR 0.966, ESG 0.412, erased 53.8%, healthy 30%, net 0.544; gemini-4-argon CCR 0.950,
ESG 0.370, erased 58.8%, healthy 18%, net 0.544. Externally the frontier models find more real lesions than
MedScope (0.95-0.97 vs 0.77) and tie or edge it on net utility; MedScope's evidence sensitivity advantage holds
(ESG 0.67 vs 0.28-0.41, erased-lesion claims 10% vs 54-66%).

Cautious prompt (150 test cases): gpt-6-astra erased-lesion claims 47.1% (ESG 0.397), claude-opus-5-5 44.1%
(0.382), gemini-4-argon 42.6% (0.412); random-edit denials rise to 13-16%. Full-set agent-prompt rates were
58.9%, 53.9%, 41.1%. Prompting reduces the problem for two of three models but leaves it at 43-47%.

Can a frontier model see the edits? (probability the image was edited, 219 cases x 3 views)
- gemini-4-argon: random edit vs original AUC 0.524 [0.474, 0.575]; erased vs original 0.753; erased vs random 0.737.
- gpt-6.1-sol: 0.546 [0.491, 0.598]; 0.698; 0.658.
Edits on normal tissue are invisible to them; erasing a lesion leaves a region they find suspicious (72% of
erased images rated >= 0.7 by gemini-4-argon). Does MedScope's "not there" depend on that? On the 61 erased
images gemini-4-argon rates as unedited (p <= 0.3), MedScope v3 still claims the lesion in only 21% (RFT 18%),
against 49-64% for gpt-6-sol, gpt-6-astra, gpt-6.1-sol and claude-fable-5-1; on obviously edited ones (p >= 0.7)
11% (RFT 9%) vs 48-58%. Some dependence on edit visibility, but the gap to frontier models is as large on
erasures that look clean.

## 2026-10-31: notebooks 16 and 17, final

Plain native prompt for the open baselines (one reply, no action format), main test, vs MedScope v3 (paired):
| Model (plain prompt) | CCR | ESG | Erased-lesion claims | Healthy-image claims | Net |
| --- | --- | --- | --- | --- | --- |
| Qwen3.5-4B | 0.890 (tie, p=0.73) | 0.183 | 72.1% | 45.1% | -0.137 |
| MedGemma 1.5 4B | 0.849 (tie, p=0.23) | 0.192 | 72.1% | 49.0% | -0.219 |
| Lingshu-7B | 0.728 | 0.301 | 53.0% | 21.5% | -0.174 |
| HuatuoGPT-Vision-7B | 0.799 | 0.265 | 59.8% | 46.9% | -0.214 |
| Qwen2.5-VL-7B | 0.699 | 0.192 | 56.2% | 50.3% | -0.426 |
| Qwen3-VL-8B | 0.811 | 0.260 | 55.7% | 41.0% | -0.170 |
With their own prompt every open model hallucinates more than under the agent prompt; MedScope is better on ESG,
both hallucination rates and net utility against all six (p<0.001; healthy vs Lingshu p=0.032). The agent prompt
helps the baselines, so the format is not what makes them look bad.

Tools off, paired: RFT ESG -0.032 (p=0.21), net -0.077 (p=0.002); v3 CCR -0.098, net -0.114 (both p<0.001), ESG -0.041
(p=0.09). Tool use: MedScope zooms on 93% of lesion views and the first zoom covers the lesion in 96-98%; on erased
views it zooms less (59-67%) and 87-88% of those zooms land on the erased site; it never uses windowing. gpt-6-astra
almost never calls a tool (0.01-0.07 per view).

Strict ESG (only explicit "not there" answers) equals ESG within 0.005 for every model (refer is rare). Trivial
policies: ESG 0 for all four; net utility always-refer +0.110 under the published matrix, -0.118 when referring on
lesion-free images pays 0, -0.300 at -0.3 everywhere; MedScope ranks first under all five matrices.

Lesion size (quartiles of lesion area): MedScope is weakest on the smallest lesions (Q1, <1.8% of the image: ESG 0.51,
erased claims 25%) and strong above (ESG 0.78-0.86, claims 7-11%). Frontier models do not improve with size: gpt-6-astra
claims a large erased lesion (Q4) in 75% of cases.

Cautious prompt vs standard, same model, same 150 cases (paired): gpt-6-astra erased claims 52.9% -> 47.1% (p=0.031);
claude-opus-5-5 54.4% -> 44.1% (p=0.016), with lower CCR (-0.044, p=0.041); gemini-4-argon 41.2% -> 42.6% (p=0.83).
MedScope v3 vs each cautious flagship: ESG +0.32 to +0.35, erased claims -29 to -34 points (all p<0.001).

External centres, paired with MedScope v3: ESG better than all three flagships (+0.26 to +0.40, p<0.001), erased
claims 10.1% vs 53.8-66.4% (p<0.001); CCR worse (0.773 vs 0.945-0.966, p<0.001); net utility not different
(+0.098 vs gpt-6-astra p=0.12; -0.022 vs opus p=0.76; -0.021 vs argon p=0.78).

External centres, three focal-lesion centres only (BraTS-Africa, CVC-ClinicDB, BUS-BRA; 149 cases; QaTa-COV19
excluded because diffuse opacities cannot be erased): MedScope v3 CCR 0.818, ESG 0.778, erased claims 4.0%,
healthy 10%, net 0.642 (RFT: 0.788 / 0.768 / 4.0% / 4% / 0.635). gpt-6-astra 0.955 / 0.354 / 59.6% / 24% / 0.490;
claude-opus-5-5 0.975 / 0.475 / 48.5% / 30% / 0.602; gemini-4-argon 0.970 / 0.424 / 54.5% / 18% / 0.616. Paired v3 vs
each: ESG +0.30 to +0.42 and erased claims -44 to -56 points (p<0.001); CCR -0.14 to -0.16 (p<0.001); net utility
+0.152 vs astra (p=0.024), +0.040 vs opus (p=0.59), +0.027 vs argon (p=0.72). QaTa alone (20 cases): every model fails
the erasure (MedScope erased claims 40%, frontier 80-100%).

## 2026-11-01: label check by frontier consensus, release (notebook 19)

Disputed labels (lesion-free test images called abnormal by >= 7 of 9 frontier models; MedScope does not vote):
26 of 288 (colonoscopy 12/91, SLAKE 11/90, BUSI 2/15, ChestX-Det 1/50, LGG 0/42). Without them, healthy-image
claims: MedScope v3 13.0% (from 14.6%), RFT 7.3%, gemini-4-argon 4.6%, other frontier 10.3-24.4%. Every paired
comparison keeps its direction and significance; vs all nine frontier models ESG, erased-lesion claims and net
utility stay at p<=0.001. Healthy-image claims vs v3: argon better (p=0.002), Fable/Opus/Sonnet not different, the
other five frontier models worse.
Released privately on Hugging Face: bhaskar-ai/MedScope-4B, bhaskar-ai/MedScope-4B-R (LoRA adapters with model cards)
and datasets/bhaskar-ai/MedScope-Bench (view manifests without images, every evaluation run).

## 2026-11-01 — Training seeds (notebook 18, partial)

Stage-1 SFT with counterfactual views, seed 1 (`v2_sft_v2_s1_*`), compared with seed 0 (`v2_sft_v2_*`):

| Split | Seed | CCR | ESG | Erased-lesion claims | Healthy-image claims | Net utility |
| --- | --- | --- | --- | --- | --- | --- |
| Internal | 0 | 0.877 | 0.758 | 11.9% | 8.7% | 0.760 |
| Internal | 1 | 0.881 | 0.726 | 15.5% | 16.3% | 0.680 |
| External | 0 | 0.761 | 0.655 | 10.9% | 8.0% | 0.519 |
| External | 1 | 0.727 | 0.630 | 10.1% | 10.0% | 0.493 |

The counterfactual effect replicates (seed-0 no-CF: ESG 0.402, erased 53.0%). Healthy-image claims on the internal
test vary with the seed (8.7% vs 16.3%), so the paper reports mean ± sd over seeds. Seeds without CF and seed 2 pending.

Declarations added to the method paper: no external funding, no competing interests, public de-identified data only.

## 2026-11-01 — Fairness checks prepared (notebooks 20 and 21)

Open questions a reviewer will ask, and the runs that answer them:

- *Did MedScope learn LaMa's traces?* Every training and test view used LaMa. Notebook 20 remakes the two edited
  views of each main-test case on the same masks with Telea, tissue transplant (Poisson-blended copy of tissue from
  the same image) and Stable Diffusion inpainting (`scripts/reinpaint_views.py`), then runs MedScope-4B, MedScope-4B-R
  and three frontier flagships on them (`scripts/inpainter_summary.py`).
- *Were frontier models disadvantaged by seeing no examples?* Notebook 20 gives the flagships the cautious prompt
  plus four solved training examples (lesion; same image erased; edit elsewhere, lesion intact; healthy image) on
  the same 150 cases as the cautious run (`--prompt fewshot --fewshot TRAIN...`; examples never enter transcripts or
  rescoring keys beyond their ids).
- *Is it one base model?* Notebook 21 trains MedGemma 1.5 4B with the same stage-1 recipe, with and without
  counterfactual views.

Paper (draft v0.6): checkpoint use stated explicitly (stage-3 headline fixed before testing; RFT beside it
everywhere; ablation and seeds at stage 1, where stage 1 alone already reaches ESG 0.758); abstract now states the
healthy-image result (14.6% vs 9.0% for gemini-4-argon) and the external sensitivity/net-utility trade-off.

## 2026-11-01 — Audit and v4 plan

Two independent audits of every result, review and code path found that notebooks 18, 20 and 21 only measure
weaknesses. v4 is trained to remove them; recipe and selection rule are pre-registered in
docs/PREREGISTRATION_v4.md (committed before any v4 data or model existed). Every MedScope claim in the paper
will come from the single selected v4 model, tested on every set (notebook 24); confirmation on a fresh internal
test (unused test-split patients of ChestX-Det and TCGA-LGG) and a fresh external test (ETIS-Larib, BUS-UCLM,
BraTS 2023 meningioma, SIIM pneumothorax) that no model was evaluated on before v4 was chosen.
Notebook 20 fixes: re-made erasures pass the same quality check, failures stop the notebook, held-out runs use
the full test's answer vocabulary, stage-1 arms also run on the held-out tools. Notebook 18 stopped after
seed 1 (v4 redoes seeds with its own recipe). Notebook 21 superseded by notebook 25.

## 2026-11-01 — Seed 1 complete (notebook 18 stopped here; v4 redoes seeds)

Stage-1 SFT, with vs without counterfactual views, internal test (CCR / ESG / erased claims / healthy claims / net):

| Seed | With CF | Without CF |
| --- | --- | --- |
| 0 | 0.877 / 0.758 / 11.9% / 8.7% / 0.760 | 0.929 / 0.402 / 53.0% / 22.2% / 0.494 |
| 1 | 0.881 / 0.726 / 15.5% / 16.3% / 0.680 | 0.927 / 0.237 / 68.9% / 26.0% / 0.370 |

External (seed 1): with CF ESG 0.630, erased 10.1%, healthy 10.0%, net 0.493; without CF ESG 0.529, erased 34.5%,
healthy 78.0%, net 0.344. The counterfactual effect replicates on the second seed, larger than on seed 0.

## 2026-11-01 — Notebook 22, first attempt stopped by the split check (no data built, no model trained)

The safety check found that re-deriving the ChestX-Det/BUSI/TCGA-LGG split reproduced only 19 of the 119 existing
test cases: notebook 07 ran with an earlier split-seed formula (seed + 10 + dataset index), changed minutes later
in commit 16c5bf7. The v4 split no longer tries to reproduce the old one: the existing test files are kept as they
are, every patient holding an existing test image is removed from all v4 splits (after checking that each such
image is identical in the source), and patients seen in earlier training or validation are kept out of the fresh
set. Pre-registration updated accordingly before any v4 data existed.

## 2026-11-01 — v4 data built (notebook 22)

- Protection of the existing test set: every protected test image found and identical in the source
  (ChestX-Det 93, BUSI 57, TCGA-LGG 79 images; 0 differ, 0 missing); their patients/groups removed from all v4
  splits (ChestX-Det 93 images, BUSI 71, TCGA-LGG 537 slices of 14 patients).
- v4 training cases added from these sources: 1,792 after quality checks (earlier: 1,055); lesion-free training
  images: ChestX-Det 404, BUSI 91, TCGA-LGG 195. Hand-crafted shortcut AUC 0.59 (no filtering needed).
- v4 validation: 218 cases after checks (+ 129 lesion-free) from these sources, plus the existing SLAKE/Kvasir set.
- Fresh internal test: ChestX-Det only, 36 cases and 40 lesion-free images. TCGA-LGG gives none: all 14
  test-split patients already hold existing test images (pre-registration listed it; noted here).
- Fresh external test: 168 cases after checks (ETIS-Larib, BUS-UCLM, BraTS meningioma, SIIM pneumothorax; 13
  failed the erasure check) and 150 lesion-free images (ETIS has none); 0 near-copies of training or test images.

## 2026-11-01 — Notebook 20: held-out inpainting tools and few-shot frontier models (v3-era models)

Held-out tools, edited views only, 125 cases common to every run (ESG LaMa / Telea / transplant / Stable Diffusion):
MedScope-4B 0.704 / 0.536 / 0.640 / 0.640; MedScope-4B-R 0.728 / 0.600 / 0.616 / 0.624; stage 1 with CF
0.720 / 0.536 / 0.656 / 0.632; stage 1 without CF 0.440 / 0.232 / 0.320 / 0.416; gpt-6-astra 0.312 / 0.256 /
0.240 / 0.256; claude-opus-5-5 0.376 / 0.296 / 0.264 / 0.352; gemini-4-argon 0.536 / 0.560 / 0.488 / 0.392.
- MedScope-4B on transplant and diffusion: changes not significant (ESG -0.064, p 0.20 and 0.15). Telea: ESG -0.168,
  erased claims 14% -> 33% (p<0.001); the no-CF arm drops as much on Telea (-0.208), so the Telea drop is not
  specific to counterfactual training. CF vs no-CF advantage holds on every tool (ESG +0.22 to +0.32, p<0.001).
- MedScope-4B beats every flagship on every tool (ESG p<=0.006) except gemini-4-argon on Telea (ESG -0.024, n.s.):
  gemini recognises Telea's smooth patches as edits (erased claims 33% -> 9%), i.e. its absent answers follow
  visible edit traces.
Few-shot (cautious prompt + 4 solved training examples, 150 cases): gpt-6-astra improves (erased 52.9% -> 38.2%,
ESG 0.34 -> 0.50, p<=0.003); Claude Opus 5.5 unchanged; gemini-4-argon unchanged on ESG with more healthy-image
claims (6.1% -> 15.9%, p=0.001). MedScope-4B vs few-shot flagships: ESG +0.24 to +0.43, erased claims -24 to -40
points (all p<=0.001).
Note for v4: Telea is the weakest tool for the v3-era models; v4 trains on LaMa + transplant and is tested on Telea
and Stable Diffusion as unseen tools.

## 2026-11-02 — v4 stage 1 on validation

v4 stage 1 (3,706 steps): v4 validation (540 cases, 1,473 views) CCR 0.805, ESG 0.672, erased claims 13.1%,
denials after an edit elsewhere 19.7%, healthy-image claims 13.6%, net 0.585. Not comparable with v3's stage-1
validation numbers as a whole (the v4 validation set is larger and weighted towards chest X-ray and brain MRI). On
the 525 identical views (colonoscopy, SLAKE): v3 stage 1 -> v4 stage 1: ESG 0.768 -> 0.795, erased 8.0% -> 7.1%,
net 0.788 -> 0.796. By type (different images old vs new): brain MRI CCR 0.94 -> 0.75, healthy claims 0% -> 24%,
denials after edit elsewhere 6% -> 25%; chest X-ray ESG 0.65 -> 0.46; breast ultrasound healthy claims 24% -> 0%.
Amendment 1 to the pre-registration (before any stage-2/3 validation or test result): v3 is evaluated on the same
v4 validation set and stays the final model unless v4 is within 0.02 of it in net utility.

## 2026-11-02 — v4 selection (notebook 23)

Validation (540 cases, 1,473 views), net utility / healthy-image claims: stage 1 0.585 / 13.6%, stage 2 0.610 /
12.7%, stage 3 0.613 / 7.7% -> pre-registered rule selects stage 3. v3 on the same validation set: 0.593 / 8.2%
-> amendment 1 keeps v4 stage 3 (within 0.02 of v3 or better). Final model: adapters/v4_s3/final.
v4 stage 3 minus v3, paired over the same validation cases: net +0.020 (p 0.59), ESG +0.016 (p 0.58), erased-lesion
claims 16.6% -> 8.7% (p<0.001), healthy-image claims 8.2% -> 7.7% (p 0.89), CCR 0.852 -> 0.792 (p 0.004), denials
after an edit elsewhere 14.1% -> 20.3% (p 0.004), grounded accuracy 0.772 -> 0.706 (p 0.001). By type: chest X-ray
erased claims 28% -> 12%, CCR 0.79 -> 0.67; breast ultrasound erased 20% -> 8%, healthy 10% -> 0%, CCR 0.92 -> 0.81;
colonoscopy net 0.95 -> 1.00; SLAKE (21 cases) net 0.14 -> 0.03.

## 2026-11-02 — final notebooks 24 and 25 (no new results)

Notebook 24 (final evaluation, selected model v4 stage 3 only) and notebook 25 (like-for-like stage-1 recipe) are
the last notebooks. Added before any v4 test result (pre-registration amendment 2): highest-reasoning-effort
flagships (OpenAI reasoning_effort high, Anthropic effort max, Gemini thinking level high), flagships and open models
(own plain prompt) on standard VQA, net utility without degraded views and clarify rate by degradation type on all four
test sets, release of v4 (private), and two extra ablation arms (absent-matched without CF; erasures only) with
held-out inpainting tools for every seed-0 arm.

## 2026-11-03 — v4 final evaluation (notebooks 24, 24c, 24r)

Single selected model (v4 stage 3) on every test; all frontier runs re-checked for API errors (none left).
- Main test (507 cases): CCR 0.849, ESG 0.758, erased-lesion claims 9.6%, healthy-image claims 7.6%, net 0.732.
  Better than all 9 frontier and 6 open models on ESG, erased claims and net utility (all p<0.001); CCR not
  different from any frontier model. Healthy-image claims lower than 8/9 frontier models; vs gemini-4-argon 7.6% vs
  9.0% (p 0.59; v3 was worse than argon, p 0.033). vs v3: healthy 14.6% -> 7.6% (p 0.001), erased 13.7% -> 9.6%
  (p 0.059), net +0.018 (n.s.), CCR -0.032 (p 0.066). Label check (26 disputed healthy images removed): same picture.
- Held-out wordings (373 cases): no change vs original wording (net +0.006, p 0.74). vs flagships on 150 cases: net
  +0.35 to +0.57 (p<0.001).
- Highest reasoning effort (150 cases): no flagship improves over its default (all n.s.); v4 better than each on ESG
  (+0.29 to +0.43), erased claims (-32 to -52 points) and net (+0.18 to +0.41).
- Few-shot and cautious prompts: v4 better than every flagship on ESG and net (p<=0.006).
- Held-out inpainters (125 cases, ESG lama/telea/transplant/diffusion): v4 0.752/0.664/0.720/0.640 (v3 0.704/0.536/
  0.640/0.640). Telea erased claims unchanged (7.2%; v3 14% -> 33%); diffusion +10.4 points (p 0.006). v4 beats all
  three flagships on every tool (ESG p<=0.049).
- Tools off: ESG unchanged (0.753), CCR -0.053, net -0.092 (p 0.003). Windowing now used (35% of tool calls).
- Lesion-size quartiles: ESG 0.55 / 0.74 / 0.84 / 0.91 (smallest lesions still weakest; flagships 0.2-0.45 in all).
- Clean-looking erasures (rated unedited by gemini): v4 claims the lesion in 15% (flagships 41-64%).
- External centres (169): ESG 0.597 vs flagships 0.28-0.41 (p<=0.002), erased 11.8% vs 54-66%, healthy 4% vs 18-30%;
  CCR 0.73 vs 0.95-0.97; net 0.530 vs 0.424/0.544/0.544 (n.s.). vs v3: ESG -0.076 (p 0.062).
- Fresh internal (ChestX-Det, 76 cases): net 0.402 vs flagships 0.22/-0.02/0.05; ESG 0.47 vs 0.00-0.08 (p<=0.001).
- Fresh external (316 cases): net -0.053 vs astra -0.106, opus 0.056, argon 0.310 (argon better, p<0.001); ESG 0.393
  vs 0.27/0.29/0.43. By source: BUS-UCLM net 0.67 (argon 0.55), ETIS 0.38 (argon 0.75), BraTS-MEN -0.03 (argon 0.09),
  **SIIM pneumothorax CCR 0.00, net -1.10** (argon CCR 0.66, net -0.06; astra/opus CCR 0.28-0.29). Diagnosis: v4 answers a confident "No" on all 48 SIIM pneumothorax originals (answer prob ~1.0; no scoring or parsing error). Share of SIIM originals called present: base Qwen3.5-4B 0%, stage 1 without CF 0%, stage 1 with CF 21%, final v4 0%. The miss comes from the base model on subtle low-resolution (256 px) pneumothorax; counterfactual training does not cause it (it is the only arm above 0%), stages 2-3 remove what stage 1 had.
- Standard VQA (all): PathVQA 0.477, SLAKE 0.730, VQA-RAD 0.514 (v3 0.520/0.767/0.554; argon 0.417/0.780/0.674).

## 2026-11-03 — post-hoc SIIM check at original resolution (notebook 26, exploratory)

Added notebook 26: the 48 SIIM pneumothorax cases and the SIIM lesion-free images of the fresh external test,
rebuilt from the original SIIM-ACR DICOMs (scripts/siim_fullres.py, matched by image UID; case ids "siimfull"),
views rebuilt with LaMa, and tested with v4, both stage-1 arms, base Qwen3.5-4B and (optionally) gemini-4-argon.
Labelled post hoc in the pre-registration; no model is changed. 42 of the 48 SIIM pneumothorax cases were found in
the original-resolution data (Kaggle jesperdramsch copy), all 48 lesion-free images.

Pneumothorax called present, same 42 cases, 256 px -> original resolution: final v4 0% -> 0%; stage 1 (CF) 19% -> 40%;
stage 1 without CF 0% -> 5%; base Qwen3.5-4B 0% -> 12%; gemini-4-argon 69% -> 69%. Stage 2 at original resolution 40%
(1/48 healthy images claimed). Resolution helps the earlier models but does not explain the final model's miss.

Diagnosis (notebook 26b, scripts/diagnose_finding.py; nothing trained):
- Training coverage: questions naming pneumothorax were 54 of ~7,000 chest X-ray training views in stage 1 (35 in stage 2,
  15 in stage 3), trained to "No" 80% / 100% / 87% of the time; only 4 pneumothorax lesion images in all of stage 1, all
  large (lesion box median 37% of the image vs 6.9% for the SIIM cases).
- Selection could not see it: validation, main test and fresh internal hold no pneumothorax lesion image asked about
  pneumothorax (only 7, 7 and 4 healthy images).
- Stage 3 is the step that removes it (stage 1 and 2: 17/42; stage 3: 0/42, all sizes). Stage 3 shifts chest X-ray answers
  towards "No" in general on validation (named findings detected 63% -> 56%, erased-lesion claims 16% -> 9%, healthy
  claims 24% -> 10%); with almost no positive pneumothorax examples, the weak detection of stages 1-2 drops to zero.
  The share of "No" targets alone does not explain it (stage 2 trained 35/35 "No" and still detected 40%).
- Asked "Is there an abnormality?", the final model says yes on 35/42 of the same images (base 38/42, stage 1 34/42,
  stage 2 37/42). Not specific evidence that it sees the pneumothorax: it also calls 4/8 healthy validation chest X-rays
  abnormal.
Conclusion: a coverage gap (rare critical finding, almost no positives in training, none in validation) that the final,
more conservative stage turned into a complete miss. Fix for future work: positives of every critical finding in
validation and a per-finding sensitivity floor in the selection rule.


## 2026-11-04 — notebook 25 (partial) and post-hoc v4.1 (notebook 27, exploratory)

Notebook 25, main test (net / ESG / erased claimed / healthy claimed): CF s0 0.69/0.74/12%/9%, CF s2 0.66/0.73/17%/17%;
no CF s0 0.28/0.21/76%/39%, s1 0.30/0.22/73%/37%; no CF with matched "absent" answers 0.32/0.21/74%/32% (the gain is not
the share of "No" answers); erasures only 0.67/0.71/7%/6% (random-edit denial 22% vs 11-15%); MedGemma CF 0.70/0.72/8%/6%,
no CF 0.41/0.37/58%/32%, untrained -0.26/0.28/54%/24%. Held-out tools, ESG (random-edit denial): Telea CF 0.70 (22%),
erasures only 0.49 (47%), no CF 0.11, matched 0.11; diffusion CF 0.59 (15%), erasures only 0.71 (24%), no CF 0.18,
matched 0.16. Seeds CF s1 and no CF s2 still running.

Abnormality control (notebook 27): "Is there an abnormality?" called yes on SIIM pneumothorax vs SIIM images without
pneumothorax: v4 35/42 vs 28/48 (Fisher p 0.012), stage 1 34/42 vs 31/48 (p 0.10), base 38/42 vs 23/48 (p<0.001).
v4 separates the two partly: it registers something abnormal but does not name pneumothorax.

v4.1 (stage 3 redone with 150 + 150 SIIM training patients): pre-set rule NOT PASSED (validation net 0.610 vs 0.613;
healthy-image claims 10.0% vs 7.7%, limit +2 points; SIIM validation detection 46% vs 2%). Tested anyway, as fixed:
new SIIM patients (100 + 100): pneumothorax found 27% (v4 0%), healthy called positive 0% (v4 0%), net -0.62 (v4 -1.10);
notebook 26 SIIM cases: found 33% (v4 0%). Main test: net 0.770 (v4 0.732), ESG 0.804 (0.758), erased claimed 5.5%
(9.6%), healthy claimed 8.3% (7.6%), CCR 0.861 (0.849). v4 stays the reported model; v4.1 is an exploratory remedy that
recovers part of the missed finding without harming the main test. Even with SIIM training cases detection stays far
below gemini-4-argon (69%), consistent with the frozen vision encoder limiting subtle findings (future work).

## 2026-11-05 — review checks (notebook 29): factorial ablation, encoder probe, patient-level bootstrap

Factorial of the two training-only components at stage 1, seed 0, main test (CCR / ESG / erased claimed / healthy
claimed / denies intact lesion after a Telea edit elsewhere): erasures only 0.788 / 0.708 / 6.8% / 5.9% / 43%; insertions
only 0.806 / 0.735 / 7.3% / 11.1% / 43%; control edits only 0.897 / 0.744 / 15.1% / 11.8% / 16%; both (the recipe)
0.847 / 0.735 / 11.9% / 9.4% / 23%. ESG is the same in every arm; the control edit raises CCR (+0.109 without insertions,
+0.041 with; p <= 0.018) and removes the "edited means absent" shortcut on the unseen tool; insertions add nothing on the
main test or the held-out tools. Fresh external net: recipe 0.061 vs control-only -0.083 (p 0.002, fewer healthy-image
claims). Decision: keep the pre-registered recipe, report that insertions are unneeded.

Linear probe on the frozen Qwen3.5-4B vision encoder (mean-pooled features, 1,200 training views, 438 test views):
random vs original AUC 0.603 [0.584, 0.626] (ResNet-18: 0.83); target vs original 0.866; target vs random 0.860.

Patient-level bootstrap: main test 507 cases from 416 patients/groups (39 groups > 1 case, largest 8); external 169 from
155; fresh internal 76 from 75; fresh external 316 from 230 (largest 8). Intervals widen by <= 0.01 (main) and <= 0.03
(fresh external); all 27 primary comparisons stay p < 0.001; one comparison crosses 0.05: fresh-external ESG vs Claude
Opus 5.5, p 0.037 -> 0.060. Paper v0.9 carries all three (Tables 7, 9; Sections 5.3-5.5, 8.5).

## 2026-11-05 — cross-set crosswalk (notebook 31)

Every unedited image of every split and cohort (training 5,257; validation 540; main test 491; external centres 169;
fresh internal 76; fresh external 316) hashed (64-bit dhash) and every pair within 8 bits confirmed by pixel
correlation at 64 px. No case id or patient/group id is shared by any two sets. Identical images (<= 4 bits, r >=
0.98): exactly one pair in 6,849 images: validation lesion-free image chestxdet03089neg_abn (ChestX-Det "no finding",
group chestxdet_g2428) is the same NIH ChestX-ray14 image as fresh-external pneumothorax case siimext00119_ptx
(distance 0, r = 1.000). It was never in training; validation was used only for model selection; the case is 1 of
316 fresh-external cases, so no fresh-external mean moves by more than 0.003, and the SIIM pneumothorax result is
unchanged (the model answered "No" on every SIIM image). The two datasets label this image differently (no finding
vs pneumothorax with a mask). Near tier (<= 8 bits, r 0.90-0.97): 1,834 pairs, all within the range reached by pairs
that cannot share a patient (ChestX-Det across patient-split folds up to r = 0.946; SLAKE vs BraTS-Africa up to
0.966), so at 64 px this tier reflects shared anatomy, not shared studies, and cannot tell a neighbouring slice of
one SLAKE volume from another patient's similar slice. Report: results/crosswalk.md. Paper v0.12, Section 4.1 and
limitations.

## 2026-11-05 — comparator sensitivity (notebook 32), same 150 main-test cases

Highest image-processing setting (OpenAI detail high, Gemini media resolution high; Anthropic has none): gpt-6-astra
ESG 0.338 -> 0.397 (p 0.18), erased claims 52.9 -> 51.5%, net utility 0.328 -> 0.316; gemini-4-argon ESG 0.441 ->
0.485 (p 0.34), erased claims 41.2 -> 38.2%, net utility 0.545 -> 0.562. No significant change. MedScope-4B vs these
arms: ESG +0.353 and +0.265 (p < 0.001), net utility +0.413 (p < 0.001) and +0.167 (p 0.012).
Plain prompt (one free reply, no tools): gpt-6-astra ESG 0.250, erased claims 66.2% (vs 52.9, p 0.023), healthy-image
claims 54.9% (vs 32.9, p < 0.001), net utility -0.054 (vs 0.328, p < 0.001); gemini-4-argon ESG 0.338, erased claims
52.9% (vs 41.2, p 0.083), net utility 0.281 (vs 0.545, p < 0.001). The agent prompt helps the flagships, not hinders
them on net utility. Claude Opus 5.5 plain prompt (run later the same night): ESG 0.412, erased claims 38.2% (vs 54.4,
p 0.002), healthy-image claims 17.1% (vs 25.6, p 0.011), CCR 0.846 (vs 0.890), net utility 0.260 (vs 0.387, p 0.061):
fewer claims of both kinds, fewer correct answers, no net gain. MedScope-4B vs plain-prompt flagships: ESG +0.34 to
+0.50, net utility +0.45 to +0.78 (p < 0.001). Runs: v2_detail_{gpt6astra,gemini}_test, v2_plain_{gpt6astra,claudeopus,
gemini}_test; report 32_comparator_sensitivity_report.md.
Paper v0.13, Table 10 and Section 5.5.

## 2026-11-06 — v5 checks pre-registered (docs/PREREGISTRATION_v5.md), notebooks 33a/33b/33r

Committed before the unmatched-control arm (v4q_unm_s0) or the removal-based DPO baseline (v4q_dpo_s0) existed.
C1: matched vs unmatched control, primary endpoint random-removal denial on the fresh external set and the pooled
held-out tools, 5-point minimum effect, claim and CCR constraints. C2: recipe vs DPO, ESG and net utility on the
fresh external set decisive, 0.05 minimum effects. Rules applied by scripts/v5_confirm.py. Results: pending.

## 2026-11-06 — v5 results (notebooks 33a/33b), and v6 pre-registered (docs/PREREGISTRATION_v6.md)

C1 (matched vs unmatched control): inconclusive by the pre-registered rule; substantively, matching is not
demonstrated to matter: within seed noise on the main test (denial 0.105 vs 0.091), the pooled held-out tools
(0.137 vs 0.129) and BraTS 2023 meningioma, ETIS and BUS-UCLM. The fresh-external difference (denial 0.512 vs 0.315, net
utility -0.083 vs 0.165) comes entirely from SIIM pneumothorax, where the unmatched arm answers "present" on 60% of
unedited, 67% of erased and 19% of healthy films (a response bias on a finding it does not see: ESG ~ 0) while the
matched arm, the recipe and DPO answer "No" on nearly all of them.
C2 (recipe vs removal-based DPO, single seed): not shown to beat DPO on new data by the rule (fresh-external ESG
+0.012 [-0.053, +0.077]); recipe better on fresh-external net utility (+0.148 [+0.054, +0.247], driven by BraTS 2023
meningioma sensitivity 0.625 vs 0.438) and on the main test (ESG +0.078, net utility +0.090, erased claims 12% vs 24%); DPO
better on sensitivity (main test CCR 0.900 vs 0.847; held-out tools 0.895 vs 0.810) and random-removal denial.
Departure: 7,590 usable pairs rather than the 8,000 named in the plan (open-question lesion-free images have no
yes/no pair). Reports: results/v5_confirmation.md, 33_v5_checks_report.md.
v6 pre-registered before any run: C3 recipe + DPO vs recipe; C2 over three seeds; stage-4 selection rule.

## 2026-11-06 — notebook 34a path fix (no departure from the v6 plan)

34a stopped before training: it looked for the seed-0 recipe adapter at adapters/v4q_cf_s0, but that arm is notebook
23's stage 1 and is stored as adapters/v4_s1 (its test runs carry the run name v4q_cf_s0, as in notebooks 25 and 26).
Same model as the plan names; nothing was trained or evaluated before the fix.

## 2026-11-06 — C3 (notebook 34a): recipe + DPO vs recipe — fails; no stage 4

v4q_cfdpo_s0 = the seed-0 recipe (v4_s1) continued with removal-based DPO on the recipe's pools. Fresh external:
CCR 0.542 vs 0.560 (-0.018 [-0.068, +0.040]), erased claims 15.5% vs 16.7%, ESG 0.381 vs 0.381, net utility 0.057 vs
0.061. Pooled held-out tools: CCR 0.837 vs 0.810 (+0.027 [-0.002, +0.059], p 0.106), erased claims 24.4% vs 16.3%
(+0.080 [+0.046, +0.118], p < 0.001), ESG 0.595 vs 0.649 (p 0.027). Main test: CCR 0.872 vs 0.847 (p 0.079), erased
11.4% vs 11.9%, ESG 0.753 vs 0.735. By the rule C3 fails; the conditional stage 4 is not trained; stage 3 stays the
final model. Exploratory reading: the preference pass keeps training-tool performance and loses on unseen tools
(erased claims 11.4% main test -> 24.4% held-out tools, vs 11.9% -> 16.3% for the recipe).
Total measured API spend over all 48 API runs: US$373.48 (results/api_cost.md).

## 2026-11-07 — C2 over three seeds (notebooks 34b/34c): no difference shown on new data; error profiles differ

34b/34c stopped once at 17:46 on 6 Nov (both runtimes at the same time, during testing) and were restarted; training
had finished, so testing resumed. DPO baseline seeds 1/2: main test ESG 0.626 / 0.699, net utility 0.640 / 0.669,
erased claims 29.7% / 19.2%, healthy claims 17.7% / 16.3%. Three seeds, recipe vs DPO:
fresh external ESG 0.381 +- 0.018 vs 0.355 +- 0.015 (per seed +0.012, +0.006, +0.060, all CIs include 0) -> by the
rule "no difference shown"; net utility 0.070 +- 0.008 vs -0.069 +- 0.078 (per seed +0.148 p<0.001, +0.060 p 0.318,
+0.209 p<0.001); CCR 0.587 vs 0.485; erased claims 20.0% vs 12.9%; denial 41.9% vs 51.6% (DPO more conservative on
new data). Main test: ESG 0.741 +- 0.019 vs 0.661 +- 0.037; erased 13.2% vs 24.2%; CCR 0.871 vs 0.903; denial 12.6%
vs 9.6%; net utility 0.684 vs 0.637.
Correction to paper v0.14: abstract, contributions and discussion said DPO had more erased-lesion claims and more
sensitivity "on new data"; that holds on the internal test only (on the fresh external set it already had fewer of
both at seed 0). Fixed in v0.15.

## 2026-11-07 — CMCC smoke test built (notebook 35a)

Three literature sweeps found no training method that uses a matched control edit at pixel level inside the objective
(closest: Evidence-RL's token-space area-matched controls, DeFacto's random-mask triplet under GRPO, Agarwal 2020's
invariant edits as data only, the original-vs-degraded preference family, CoEV's post-hoc erase-and-recheck).
`medscope/train/cmcc.py` adds control-matched counterfactual consistency: decision log-odds s(x) on the single-turn
present/absent replies; L = L_sft(O, E, C) + 0.5·softplus(2 − (s(C) − s(E))) + 0.5·(s(O) − s(C))² + 0.5·(first-action
log-prob | O − | C)². Notebook 35a continues the seed-0 recipe adapter for 3,000 triplet cases (`v4q_cmcc_s0`) and tests
everywhere; matched-compute comparison is the C3 arm. Go signature for a pre-registered v7: held-out-tool erased claims
below the recipe (16.3%) and C3 (24.4%), fewer control denials, ESG at or above the recipe. Not run yet.

**2026-11-07, 35a first attempt stopped.** The v1 trainer ran at 11.6 s per case (80 cases in 932 s: thirteen full
forward/backward passes per triplet at batch size 1), i.e. about 10 h for 3,000 cases; stopped after ~30 min. The
first log record showed the objective behaving as intended on the recipe adapter: s(O) −10.8, s(C) −11.3, s(E) −23.7,
margin term 0.51 (active on a minority of cases), invariance term 3.08, first-action term ≈ 0. Trainer v2 (`cmcc-v2`)
replays one trajectory view per case, scores the two candidate replies of a view in one batch-of-2 pass
(`HFPolicy.token_logprobs_pair`) and prepares the next case on the CPU while the GPU works; a v1 checkpoint is
discarded automatically. Expected ≈ 5 s per case.

## 2026-11-07 — 35a smoke test result; v7 pre-registered (C4)

`v4q_cmcc_s0` (trainer v2, 3,000 triplet cases from `v4_s1`, 2.4 s/case on an RTX PRO 6000) vs the recipe and C3:
- Held-out tools (TELEA + diffusion, 410 cases): erased-lesion claims 10.7% vs 16.3% (recipe) vs 24.4% (C3);
  control denial 14.9% vs 18.8%; ESG 0.744 vs 0.649; net utility 0.741 vs 0.566. Diffusion: erased −0.094
  [−0.147, −0.047] p<0.001, ESG +0.120 p<0.001, net utility +0.212 p<0.001; TELEA: ESG +0.073 p=0.008, net utility
  +0.144 p=0.007, erased −0.023 n.s. Transplant (a training tool): no difference.
- Fresh external: no difference on any endpoint (ESG 0.393 vs 0.381; erased 14.3 vs 16.7; denial 46.4 vs 45.2;
  lesion-free claims 3.4 vs 6.8, p=0.068).
- Main test: ESG 0.717 vs 0.735 n.s.; erased 12.8 vs 11.9 n.s.; denial 15.5 vs 14.6; **lesion-free claims 13.5% vs
  9.4% (+0.042 [0.012, 0.073], p=0.006)** — the continuation saw no lesion-free image.
- Training log: invariance term 3.1 → 0.2, margin term 0.5 → 0.3, s(O) − s(C) → ≈0, s(C) − s(E) ≈ 8–10, replay
  loss flat at 0.25–0.28.
Reading: the gain is where the edit signature is unfamiliar, as the objective predicts; one seed, and not separable
from "3,000 more cases on the same adapter". Trainer v3 adds a lesion-free replay view every third case.
`docs/PREREGISTRATION_v7.md` (C4): CMCC vs a matched-compute control (same replay, all paired-view weights zero),
three seeds from `v4_s1`/`v4q_cf_s1`/`v4q_cf_s2`; primary endpoint erased-lesion claims on the pooled held-out
tools, per-seed direction + pooled CI; guards on lesion-free claims (main test) and ESG/net utility (fresh
external). Rules: `scripts/v7_confirm.py`; notebooks 36a/36b/36c (one seed each, ~7–8 h) and 36r.
