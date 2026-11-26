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

## 2026-11-08 — v7 result: C4 fails (`results/v7_confirmation.md`); manuscript v0.16

Three seed pairs, CMCC (`v4q_cmccn_s*`) vs matched-compute control (`v4q_sftc_s*`), held-out tools pooled (219 cases):
erased-lesion claims 0.126 vs 0.115, +0.011 [−0.009, +0.030], p=0.27 (per seed −0.029, +0.059, +0.005) → primary
endpoint not met. Secondary: control denial −0.033 [−0.054, −0.012] p=0.001 (lower every seed); CCR +0.030 p=0.004;
net utility +0.051 p=0.042; ESG +0.020 n.s. Guards: main-test healthy-image claims 0.131 vs 0.079 (+0.052, p<0.001)
→ fails; fresh external ESG +0.058, net utility +0.146 → holds, but erased claims +0.073 and CCR +0.127, denial −0.131
(all p<0.001). Reading: the objective shifts the operating point towards "present" everywhere; the invariance term
closed s(O)−s(C) by raising s(C), not by removing the edit's influence. Logs confirm the terms behaved as designed
(inv 3 → 0.2, margin held at 8–10), so the hypothesis failed, not the implementation.
Incidental: the control arm alone (recipe continued 3,000 cases, replay only) has held-out erased claims 11.5% vs the
recipe's 16.3% and ESG 0.709 vs 0.649 — the smoke-test gain was mostly extra training. Paper v0.16: §3.7 C4 plan,
§5.3 C4 paragraph + Table (tab:v7), abstract/contributions/discussion/conclusion/limitations updated; 27 pages.
`docs/RESULTS_SUMMARY.md` written as a standalone status document for outside readers.

## 2026-11-08 — v0.16 review received (72/100, major revision); v0.17

Review in `docs/reviews/MedScope_v016_Review.pdf`; point-by-point in `docs/reviews/RESPONSE.md`. Text corrections
applied in v0.17 (C2 wording and compute, C1 tool+shape confound, C4 "registered after a pilot", longer-training
observation not seed-paired, abstract ESG definition and Gemini utility deficit, provider image settings). New:
`scripts/review_fixes.py` + notebook 37 (overlap-excluded fresh-external estimates with SIIM denominators, errors
by asked finding, error at fixed coverage, 491-vs-507 crosswalk count); notebook 38 (recipe held-out tests at seeds
1–2; `v7_confirm.py` now pairs control vs recipe per seed); reader study: the live pack-2 page (128 images, already with readers) is kept byte for byte; a 96-image
supplement (pack 3: 24 per kind, cases not in pack 2, localized findings first, diffuse/pneumothorax tagged as
stress tests, specialty/experience fields) is published under /pack3/ for the same readers; scoring and adjudication
pool both packs (56 erased images), per-image majority criterion.
RESULTS_SUMMARY open-model line corrected (Qwen2.5-VL-7B: 5.5% erased claims at CCR 0.144).

## 2026-11-08 — notebooks 37 and 38 done; v0.17 figures filled

37 (`results/review_v016.md`): excluding the shared SIIM/ChestX-Det image moves MedScope-4B's fresh-external ESG
0.393 → 0.395, CCR 0.476 → 0.479, net utility −0.053 → −0.046 (315 cases); SIIM unedited positives detected 0/48
(MedScope-4B, DPO s0), 10/48 (recipe s0), 12/48 Claude Opus 5.5, 14/48 gpt-6-astra, 30/48 gemini-4-argon. Errors by
finding: MedScope misses fibrosis 3/4, tumour 5/23, "lesion" 4/20 (main test); fresh external misses pneumothorax
48/48, tumour 11/20, abnormality 12/32. Selective risk at fixed coverage (stated confidence), main test: MedScope-4B
0.151 @100% / 0.107 @70% (AURC 0.065) vs flagships 0.114–0.137 / 0.023–0.055 (AURC 0.020–0.033); referral shares
≤ 2.4%. Crosswalk 491 vs 507: 16 SLAKE lesion-free images each carry two question-cases (section D of the script
first grouped by basename and was corrected to full path; the SLAKE count is unaffected).
38: recipe held-out tests at seeds 1 and 2 (`v4q_inp_{telea,diffusion}_cf_s{1,2}_test`). Control (replay-only
continuation) vs recipe, paired by seed, held-out tools: erased claims −0.012 (n.s.), −0.080 (p<0.001), −0.085
(p<0.001); ESG +0.022, +0.027 (n.s.), +0.076 (p=0.001); CCR +0.012, −0.049 (p<0.001), −0.012; control denial −0.010,
+0.054 (p<0.001), +0.012. Longer training reduces erased claims on unseen tools in two seeds of three, at seed 1
with a loss of clean-image sensitivity; reported as an observation, no locked comparison planned yet.
Paper v0.17: overlap-exclusion and 491/507 figures filled; longer-training paragraph seed-paired; new "errors by
finding and at fixed coverage" paragraph and a confidence limitation. 28 pages.


## 2026-11-08 — v0.17 review (72/100 retained); v0.18

`docs/reviews/MedScope_v017_Review.pdf`. All four numbered corrections applied (duplicate statements reconciled with
actual shifts +0.002/+0.003/+0.007 and the 47-film post-exclusion SIIM denominator; consistent C1/C2 wording; the
training-duration comparison reported seed-paired throughout; fixed-coverage tie handling stated). The reviewer's
novelty route adopted: `docs/PREREGISTRATION_v8.md` fixes a prospective selection-rule test (R1 erased claims; R2 with
a 0.75 sensitivity floor; R3 ESG with the floor; 21 candidates; ties 0.005; smallest worthwhile gain 0.05 net
utility; reader-verified confirmation on a new patient-disjoint cohort with replication on a second source or unseen
editor); `scripts/v8_select.py` applies the rules mechanically. The Qwen2.5-VL-7B reversal (5.5% erased claims at
ESG 0.146 / CCR 0.144) is described in §5.1 as the retrospective motivation.

## 2026-11-08 — Preprint v1.0 prepared

`paper/preprint_v1.0.pdf` (28 pages) and the arXiv source. Changes from v0.18 are listed in
`docs/PREPRINT_SUBMISSION.md`. Author line: Bhaskar Gurram, Independent Researcher, gurrambhaskar.ai@gmail.com.
No placeholders remain; the reader study is described as in progress with its extension; a call for collaboration
(readers; a new cohort for the v8 selection-rule test; a methods collaborator) closes the paper.

## 2026-11-11 — outreach, first reply, and the v9 pilots

Preprint posted (arXiv:2611.13006, cs.AI; cross-lists cs.CL, cs.CV). 48 individual emails sent to authors of the
closest work, radiologists and dataset owners. First reply (Yixiao He, BUPT; declined collaboration, gave advice):
preference objectives help weak base models on perception tasks more than strong ones; LoRA gained much less than
full fine-tuning in his video experiments; offline DPO is sensitive to pair quality, and online RL with verifiable
rewards (GRPO) may suit a rule-scored task. `docs/PILOTS_v9.md` turns two of these into one-seed pilots:
lead 2 (notebook 39a) trains stage 1 at rank 64 with and without adapters on the vision encoder and projector
(`v4q_r64_s0`, `v4q_r64v_s0`; new `--lora-r` and `--lora-vision` options); lead 3 (notebook 39b) continues the
recipe adapter with GRPO on the cost-matrix reward (`v4q_grpo_s0`; brain MRI cases excluded from the reward).
Pilots only: a go signal leads to a separate pre-registration, not to a claim.

**2026-11-11, 39a moved to a G4 runtime.** The first arm (`v4q_r64_s0`) had reached step 1,701 of 3,473 on an A100
after about three hours when the run was stopped and restarted on a 96 GB RTX PRO 6000. Notebook 39a now trains
both arms as two processes at once when the GPU has 70 GB or more (NVIDIA MPS when available); samples, order and
steps of each arm are unchanged, and the first arm resumes from its checkpoint, so its first half was computed on
an A100 and its second half on the RTX PRO 6000 (small floating-point differences between GPU types are possible).

## 2026-11-11 — pilot 39a result (lead 2): no go; the vision arm's test result is suspect

One seed, stage 1, against the recipe `v4q_cf_s0` (report `results/39a_pilot:_vision_adapters_report.md`).
- **Rank 64, vision frozen (`v4q_r64_s0`)**: indistinguishable from the rank-16 recipe on the main test (ESG 0.731 vs
  0.735, erased claims 10.5% vs 11.9%, CCR 0.831 vs 0.847, healthy claims 10.8% vs 9.4%) and on the held-out tools.
  Fresh external: ESG 0.339 vs 0.381, healthy claims 14.9% vs 6.8%. It "detects" 25 of 48 SIIM pneumothorax films
  against 10, but also claims 21 of 48 erased ones and 12 of 48 healthy ones (SIIM ESG 0.042): a response bias, not
  perception. More adapter capacity does not help.
- **Rank 64 with vision adapters (`v4q_r64v_s0`)**: ESG 0.000 on every set. It answers from the question alone:
  tumour, breast mass and "lesion" always present (0 misses, 96-100% erased and healthy claims), polyp and pleural
  effusion always absent, pneumothorax 1 of 48. Its training loss, however, fell normally (0.47 -> 0.22 over 3,700
  logged steps, the same as the frozen-vision arm), which a model that ignores the image cannot reach on paired
  original/erased views. So the tested model is probably not the trained one (a save or load fault for the vision
  adapter weights), or the vision adapters behave differently in the test path. Notebook 39c checks the saved file,
  what the test loader attaches, and the loaded model's loss on training views. Until that is settled the arm says
  nothing about whether the vision encoder can learn; the go signal is not met either way.
Lead 3 (39b): GRPO rollouts can now be generated a whole step at a time (`--draw-batch`; the groups trained on
follow the same draw-until-enough-signal rule, tested).

## 2026-11-11 — notebook 39c: the vision arm's collapse is real; one retry declared

Check of `v4q_r64v_s0` (`results/pilot_v9_lead2_check.md`): the saved adapter holds 692 tensors, 196 on the vision
encoder and projector, all non-zero; the test loader attaches all of them with values equal to the saved file; the
loaded model's loss on 200 training views is 0.235 (frozen-vision arm: 0.179). So there is no save or load fault,
and the earlier entry's reasoning was wrong: a model that answers from the question alone can reach a mean token
loss near 0.22 because format tokens dominate the mean. The arm did learn to ignore the image.
Probable cause: vision adapters trained at 2e-4. `docs/PILOTS_v9.md` now declares one retry, `v4q_r64vl_s0`
(notebook 39d), with the vision-side adapters at a tenth of the learning rate (`--vision-lr-scale 0.1`, new option;
two optimizer groups, same schedule shape). No other setting will be tried under this plan.

## 2026-11-12 — pilot 39b result (lead 3, GRPO): go signal narrowly missed; a sensitivity gain with slightly more claims

`v4q_grpo_s0` (150 steps, ran on an A100 80 GB; report `results/39b_pilot:_grpo_report.md`), one seed, against the
replay-only continuation `v4q_sftc_s0` and the recipe `v4q_cf_s0`. Training had signal in nearly every step
(typically 2-4 of 12 groups drawn), unlike notebook 05.
- **Held-out tools vs control:** TELEA (219): net utility +0.021 [-0.073, +0.118], erased claims +0.032 (p = 0.10),
  CCR +0.027. Diffusion (191): net utility +0.097 [+0.003, +0.199], erased claims +0.010, CCR +0.058 (p < 0.001).
  Case-weighted over both: net utility about +0.056, erased claims about +0.022.
- **Main test vs control:** net utility +0.026 (n.s.), CCR +0.034 (p = 0.010), erased claims +0.009, healthy claims
  +0.021 (within the 0.03 guard).
- **Fresh external vs control:** net utility +0.124 [+0.038, +0.209], ESG +0.083, CCR +0.107, but erased claims
  +0.042 (p = 0.09) and healthy claims +0.054 (p < 0.001). Against the recipe there: net utility -0.016, ESG +0.071,
  erased claims -0.065.
**Reading against the declared go signal:** net utility (+0.056 >= 0.05), sensitivity and the healthy-claim guard
pass; "erased-lesion claims not higher than the control's" does not (+0.022 on the point estimate, not
significant). The signal as written is therefore not met. The pattern is consistent: GRPO makes the model answer
more, which finds more real lesions and adds a few false claims; the cost matrix rates that trade as a gain.

## 2026-11-13 — pilot 39d (lead 2 retry): no collapse, but no go; lead 2 with low-rank vision adapters is closed

`v4q_r64vl_s0` (rank 64, vision adapters at 2e-5; trained on an A100 80 GB, stopped at about step 1,600 and resumed
from its checkpoint on an A100 40 GB; report `results/39d_pilot:_vision_adapters,_gentle_learning_rate_report.md`).
- **The collapse is gone:** ESG 0.776 on the main test (frozen-vision rank 64: 0.731; recipe: 0.735), so the 2e-4
  learning rate was the likely cause of the 39a collapse.
- **Declared go signal not met:** fresh-external sensitivity fell (CCR 0.488 against 0.548 for rank 64 and 0.560 for
  the recipe; -0.071 vs the recipe, p = 0.03) and SIIM pneumothorax detection fell to 7 of 48 (recipe 10 of 48).
  Under `docs/PILOTS_v9.md` this was the only retry, so lead 2 with low-rank vision adapters is closed as negative
  and no further setting is tried.
- **Exploratory, not a claim:** the arm withdrew erased findings more often at unchanged main-test sensitivity
  (erased claims 6.8% vs 11.9% for the recipe, p = 0.007, CCR 0.854 vs 0.847; fresh external 7.7% vs 16.7%,
  p = 0.002), but its fresh-external net utility was lower than the recipe's (-0.112, p = 0.046) and its stated
  confidence ranked errors worse there (AURC 0.508 vs 0.305). It became more conservative, not more perceptive.
- Under the plan, full unfreezing of the vision encoder was conditional on this pilot being positive; it is not
  supported by these results.

## 2026-11-13 — lead 4 declared: a counterfactual multi-agent reader (docs/PREREGISTRATION_v10.md)

After leads 2 and 3, the method question moves from "train one model differently" to structure: a direct reader and a
question-blind reader (both the frozen recipe adapter), a lesion segmenter trained only on unedited training images,
a verifier that erases the region the others point to and makes an equal edit elsewhere before asking again, and a
trained deciding agent that reads all four reports. Prior-work check: the closest published method (counter-evidence
verification, Zhou et al., MICCAI 2026) masks the claimed region at test time without a matched control edit and
without training; lead 4's go signal and its "no control" ablation test exactly that difference. Plan, arms,
ablations and go signal were committed before anything was trained; notebook 40 runs it end to end.

## 2026-11-13 — lead 4 result (notebook 40): NO GO; held-out gain, but sensitivity collapses at new centres

Report `results/40_pilot:_counterfactual_multi-agent_reader_report.md`, rule `results/v10_rule.md` (A100 80 GB).
- **Held-out tools pooled, full system vs `v4q_sftc_s0`:** net utility +0.090 [+0.004, +0.180] (p = 0.044), erased
  claims -0.015, CCR +0.022. The three primary conditions and the main-test healthy-claim guard are met.
- **Guard-rail failed:** fresh-external CCR 0.378 vs the recipe's 0.560 (-0.182, p < 0.001); external centres CCR
  0.513 vs 0.769 and net utility 0.232 vs 0.604. Pneumothorax 3 of 48. Erased claims are lower at new centres
  (6.5% vs 16.7%) because the system says "absent" far more often. **Go signal: NO GO.**
- **Ablations (held-out pooled):** only the specialist contributes by the rule (removing it: net utility -0.055,
  erased claims +0.029); the reports together add +0.042 over the arbiter alone (n.s.). The question-blind reader,
  the verifier and the verifier's matched control each change net utility by under 0.02.
- **Agents on their own:** the specialist finds a region on 86-87% of unedited test lesion images but only 50-53% at
  new centres, and still "finds" 19-29% of erased lesions. The verifier behaves as designed where it acts (about 80%
  of claims withdrawn after erasing their region, about 95% kept after the control edit), but the direct reader
  rarely claims an erased lesion with a box (20 of 219 on the main test), so it seldom gets to act.
- **Likely cause of the collapse (post hoc, not tested):** the arbiter was trained on specialist reports for the
  specialist's own training images (found on 96%), so it learned to trust "specialist found nothing" far more than
  the specialist deserves on unseen centres. Out-of-fold specialist reports for arbiter training would remove this;
  that would be a new pre-registered plan, not a change to this one.

## 2026-11-13 — lead 4 retry declared (docs/PREREGISTRATION_v11.md)

The one declared retry: the deciding agent is trained on the other agents' reports on the validation views (images
none of them was trained on) instead of a training subset; 3 epochs; everything else, including the rule, as in v10.
Notebook 41. A NO GO closes lead 4.

## 2026-11-13 — reader study, second reader (TR, radiology, 1 year), pack 2

- Finding judged present (yes): unedited lesion images 26/32 (cannot tell 3), **erased 16/32 (cannot tell 8)**,
  control-edited 27/32, lesion-free 7/32 (cannot tell 9). Edited vs unedited AUC 0.55; erased vs control 0.61.
- Both readers pooled: residual finding on erased images 35/64 reads; per image by majority, 13/32 erased images
  (exact 95% CI 24-59%). **The pre-registered criterion (at most 10%) fails.** Agreement between readers: kappa 0.10
  on "edited", 0.47 on "finding present".
- By source (reader 1 | reader 2, finding present on erased vs lesion-free images): colonoscopy erased 1/6 | 2/6 vs
  lesion-free 2/6 | 0/6 (erasure works); breast ultrasound 6/7 | 4/7 vs 5/7 | 1/7; chest X-ray 5/6 | 4/6 vs 4/6 | 3/6;
  brain MRI 3/7 | 5/7 vs 1/7 | 1/7; SLAKE 4/6 | 1/6 vs 4/6 | 2/6.
- Reading: physicians cannot tell edited images from unedited ones, but on ultrasound, brain MRI and (less clearly,
  because readers also call many healthy films positive) chest X-ray they often still see a finding after erasure.
  The "erased = absent" label is reader-supported for colonoscopy only so far. Two trainee readers, single images
  without clinical context; pack 3 (localized findings) not yet read.

## 2026-11-13 — lead 4 retry result (notebook 41, v11): NO GO; lead 4 closed

Report `results/41_pilot:_multi-agent_reader,_out-of-sample_reports_report.md`, rule `results/v11_rule.md`.
- **Held-out tools pooled vs `v4q_sftc_s0`:** net utility +0.042 [-0.033, +0.119] (needed +0.05), erased claims
  **+0.061** [+0.027, +0.096] (needed not higher), CCR +0.056, ESG -0.002. Fresh-external CCR 0.449 vs the recipe's
  0.560 (guard fails). Three of five conditions fail: **NO GO**.
- **What the fix did:** the deciding agent stopped over-trusting "nothing found". At the external centres sensitivity
  recovered (CCR 0.803 vs 0.513 in the first run; recipe 0.769) and on the main test it had the best net utility of
  any arm (0.809; +0.069 vs the control, +0.117 vs the recipe), but the main test uses the verifier's own inpainter.
  On the held-out tools it now claims more erased lesions. ESG did not move on any set: the agents shifted the
  answer threshold, they did not make the system better at telling an erased lesion from a present one.
- Ablations: only the specialist contributes again (removing it -0.066 net utility); the question-blind reader,
  verifier and matched control add nothing measurable.
- Under `docs/PREREGISTRATION_v11.md` this was the only retry: **lead 4 is closed.** Method leads tried since the
  preprint: C1-C4, lead 2 (vision adapters, 2 runs), lead 3 (GRPO), lead 4 (multi-agent, 2 runs); none met its rule.

## 2026-11-13 — screening stage A (notebook 42a): 128 policies, 19 pass on half A, 0 confirm on half B

Validation set only (`results/screen_a/screen_a.md`). Every policy that passed on half A failed on half B, always on
the ESG condition (and some on CCR). Net utility rose a lot on both halves for many learned combiners (half B: 0.539
for the recipe alone, up to 0.706 for boosted trees on direct reader + specialist with a refer band, with erased claims
3.9% vs 11.2%) but ESG on half B moved by at most +0.026 for any policy (+0.013 for that one) and CCR fell (0.727 vs
0.773). The stored agents add no information that separates an erased lesion from a present one beyond what the
recipe already has; they allow better-calibrated abstention. Combining existing signals is closed; stage B needs new
evidence. (The "V" column of the first report also marked "no verifier" combiners; fixed.)

## 2026-11-14 — screening stage B (notebook 42b): 142 policies with new image evidence, 0 pass

Validation dev set (200 cases, LaMa and TELEA erasures, 80 lesion-free images; `results/screen_b/screen_b.md`).
Probes: altered copies, close-up and control close-up, cautious prompt, answer-token probability, a second model
(Qwen2.5-VL-7B), segmenter score. **No policy passed on half A.** As in stage A, learned combiners and votes raised
net utility a lot (half B, TELEA: 0.444 for the recipe, up to 0.686) by abstaining and saying "absent" more, while
ESG on the TELEA erasures did not rise (recipe 0.600; most combiners 0.55-0.61; the single largest 0.642 at a
cut-off that failed elsewhere). On LaMa erasures ESG reached 0.737, a gap that does not carry over to TELEA.
Stages A and B together: 270 policies screened, none passed. No cheap inference-time evidence separates an erased
lesion from a present one better than the recipe. One likely reason, from the reader study: physicians still see the
finding on about 40% of erasures, so the "erased = absent" label is itself noisy outside colonoscopy, which caps
how far ESG can rise and how small a real gain can be measured.

## 2026-11-14 — reader-verified analysis (notebook 43, docs/READER_VERIFIED.md): the headline does not hold as stated

Pack 2, two trainee readers: 10 reader-clean erasures (neither reader saw the finding), 19 majority-clean, 13 residual
(both saw it). 52 main-test runs scored on these images from stored replies (`results/reader_verified.md`).
- **Frontier models pooled (9):** claim the finding on 26% of reader-clean erasures (95% interval 10-42%), 36% of
  majority-clean, **82% of residual** erasures. Pre-registered rule (lower bound above 20%): **not met.** The
  41-62% erased-claim rates in the preprint are largely driven by erasures that left the finding visible to
  physicians; on clean erasures the rate is about a quarter, with wide uncertainty (10 images).
- **Open and MedScope models pooled (43):** 12% clean, 19% majority-clean, 40% residual.
- **MedScope-4B (v4_final):** 0/10 clean, 4/13 residual (31%), finds 56/63 reader-confirmed lesions, 0/16 claims on
  reader-confirmed healthy images. It says "absent" on most erasures that physicians still read as positive: either
  the readers over-call (they also called many healthy images positive) or the model reacts to the erasure itself;
  13 images cannot separate the two.
- Frontier models' claims track what physicians see (82% residual vs 26% clean), which supports reading their
  erased-lesion claims as partly correct perception of imperfect erasures, not only question-driven hallucination.
- Consequences: the preprint headline must be corrected (v2); the erasure criterion and the clean-image count
  (pack 3, senior readers) decide what can be claimed.

## 2026-11-14 — reader-verified analysis, confound checks: the headline holds where erasure is reader-supported

The first reading (previous entry) over-read 10 images. Checks added to `scripts/reader_verified.py`:
- **Group mix:** the 10 reader-clean erasures are mostly colonoscopy (4); the 13 residual ones mostly chest X-ray,
  breast ultrasound and brain MRI (11). 4 of the 13 residual ones ask "Is there an abnormality ...?", where another
  finding in the image makes "yes" correct.
- **Same cases:** frontier models that found the lesion on the unedited image still claim it after erasure in 30%
  (19/63) of reader-clean cases, 54% of split cases and 85% of residual cases. Erasure quality matters, and clean
  erasures still draw claims.
- **Whole main test, colonoscopy (the imaging type readers judged erasure clean for):** frontier models pooled claim
  the erased finding on **45%** of 83 erased colonoscopy images while finding **96%** of unedited colonoscopy
  lesions. Other types: brain MRI 46%, breast ultrasound 71%, chest X-ray 60%, SLAKE 49%.
- **Reading:** the 10-image pre-registered check is under-powered (its rule was not met); the larger, reader-supported
  colonoscopy subset supports the headline that frontier models claim erased findings. The non-colonoscopy rates mix
  real claims with residual evidence and broad "abnormality" questions; that caveat belongs in the next revision,
  no retraction is indicated.

## 2026-11-14 — literature review (six strands) and framework stage 0 pre-registered

Six reviews of published work in `docs/litreview/` (about 280 papers; venues marked confirmed or from memory, every
citation re-checked before use). Synthesis and plan in `docs/FRAMEWORK.md`. Checks of our stored results first
(recipe seed 0, main test, 219 cases; denies = absent or refer):
- LaMa: denies control 14.6%, but only 2.7% (5/186) where the lesion is found on the unedited image: the remaining
  gap is perception.
- TELEA: erased claims 8%; denies control 21.9%, **12.9% (24/186) where the lesion is found**, 13 of them breast
  ultrasound: on the held-out tool the loss is edit-induced denial, not hallucination.
- Diffusion: erased claims 25.7%; 41 of 45 claims point at the erased site (the diffusion edits have not been
  reader-checked; claims there are not yet known to be errors).
- Our erasures are edited at the lesion and our control edits elsewhere: a site-of-edit shortcut is possible and
  untested (the stage-1 arm trained on erasures without controls already denied 47% of TELEA controls).
`docs/FRAMEWORK_STAGE0.md` fixes the test before any score: same-site ring edits with the lesion intact, restored
and half erasures, six models, probes on hidden features, validation images only (notebook 44).

## 2026-11-14 — framework stage 0, first run (notebook 44): invalid by its own check; generated-answer rerun

The single-turn decision log-odds failed the pre-registered check (63% agreement with the agent's answers, rule 80%):
the "present" reply carries box coordinates and is ~11 nats less probable on every image, so its sign is meaningless
(my design error; the check caught it). Valid without a threshold, descriptive only: within a case, the same-site ring
lowers every model's score about as much as the far control edit (no sign of a site shortcut; recipe ring minus
control -0.34 [-0.78, 0.08] nats on LaMa, +0.89 [-0.23, 1.89] on TELEA); half erasures lower it by about a quarter
of an erasure (graded); TELEA edits anywhere lower it by 13-40% of an erasure, least for CMCC (2-5%). Linear probes:
erased vs ring separable at AUROC 0.90 (LaMa) and 0.85 (TELEA, trained on LaMa) in the recipe, 0.87/0.83 in the
untrained base model. Amendment in `docs/FRAMEWORK_STAGE0.md`; rerun with generated answers in notebook 44b.

## 2026-11-14 — stage 0, generated answers (notebook 44b): recipe complete, decision not yet possible

Generated answers agree with the recipe's stage-B answers on 97.2% of dev views (check passed). Recipe, 143 cases it
finds unedited: denies after a far control 4.2% / ring at the lesion 7.7% / erasure 86.7% (LaMa); 12.6% / **20.3%**
/ 92.3% (TELEA); TELEA site minus far +0.077 [0.000, 0.154]. The recipe meets the first two parts of the site rule on
TELEA (>= 0.10; >= 0.05 above far), not on LaMa. Read-out gap below the rule (0.028 image features, -0.008 last token).
The run was stopped with the base model at 270 of 1,870 views (no ring view), and the report printed "branch C":
**that verdict is void** - the code read a missing base value as "not above base" (fixed: it now says undecided).
Notebook 44c runs the base model on the unedited, ring and control views only (what the rule needs) and applies the
rule.

## 2026-11-14 — framework stage 0 decided (notebook 44c): branch A by the rule; robustness checks weaken it

**Pre-registered rule (docs/FRAMEWORK_STAGE0.md, generated answers):** branch **A** (footprint-balanced
counterfactual training), on TELEA only. Recipe ring denial 0.203 (>= 0.10), ring minus far +0.077 [0.000, 0.154]
(>= 0.05), base model ring denial 0.116 (recipe 0.087 above, >= 0.05). LaMa: no (recipe ring denial 0.077). Read-out
gap: no (0.028 / -0.008). Score check passed (97.2%).

**Checks run after the decision (post hoc, so declared):** the rule compares each model on the cases *it* finds
(recipe 143, base 127). On the 112 cases both models find:
- TELEA ring denial recipe 12.5% vs base 6.2%: difference +0.062 [-0.009, 0.134] (bootstrap over cases, 4,000);
  far control 8.9% vs 4.5%. Training roughly doubles sensitivity to TELEA edits near *and* away from the lesion.
- The site-specific part ((ring - far) recipe minus base) is +0.018 [-0.080, 0.116]: no evidence that training
  taught a *site* shortcut specifically.
- The recipe's TELEA ring denials are 12 of 17 chest X-rays (0 of 33 breast ultrasound, 2 of 34 colonoscopy, 0 of
  24 brain MRI). A TELEA ring 2 pixels from a small chest lesion may also blur its edge; no reader has checked these.
- LaMa: recipe 4.5% vs base 7.1% (-0.027 [-0.081, 0.027]).
Reading: the rule is met, but what the data support is a training-amplified sensitivity to an unfamiliar editing
tool, concentrated in chest X-ray, rather than a site shortcut. A tool-invariance objective (several fill tools on
both ring and far controls) addresses both readings; the expected headroom is the TELEA control denial among found
lesions (main test 12.9% vs 2.7% on LaMa).

## 2026-11-14 — framework stage 1 screen pre-registered (docs/FRAMEWORK_STAGE1.md, notebook 45)

Tool-family training: each training case's erasure and control are made with one of LaMa, blur, mean fill or
shuffled pixels (TELEA and diffusion held out), the control far or in a ring around the lesion. Two arms on the
control's exact 2,739 cases, order and settings (`v4q_tfr_s0` replay only, `v4q_tfc_s0` with the paired-view terms)
against the replay-only control `v4q_sftc_s0` (trainer cmcc-v3, 1,117 lesion-free images). Screen on validation
answers; rule: TELEA ESG +0.03, TELEA control denial -0.03, guards on LaMa ESG, lesions found and lesion-free claims.

## 2026-11-14 — framework stage 1 screen (notebook 45): neither arm passes; the tool-family line ends

Validation dev set, generated answers, against the replay-only control `v4q_sftc_s0` (paired by case, bootstrap 95%):
- **Tool-family replay (`v4q_tfr_s0`)**: TELEA ESG +0.017 [-0.034, 0.067]; TELEA control denial (found) -0.021
  [-0.057, 0.007]; LaMa ESG -0.022 (guard -0.02 missed); erasures denied less (LaMa 82% vs 87%): a shift towards
  "present" everywhere, not better separation. **Fails** (1, 2, 3).
- **Tool-family CMCC (`v4q_tfc_s0`)**: TELEA ESG +0.011 [-0.056, 0.084]; TELEA control denial +0.008; erasures
  denied more (TELEA 95% vs 91%) but ring edits denied more too (TELEA 21.4% vs 15.3%) and lesion-free images claimed
  more (8.7% vs 1.3%, guard). **Fails** (1, 2, 5).
- Reference: the recipe against the same control: ESG differences +0.006 on both tools; lesion-free claims 12.5% vs
  1.3%.
By the rule in docs/FRAMEWORK_STAGE1.md this line ends and is reported as a negative result. With stage 0 (the
model's hidden features separate erased from intact images no better than its answers, and the untrained base model's
features almost as well), this is the eleventh training or inference method whose effect on the held-out tools is a
change of threshold rather than of separation.

## 2026-11-15 — review checks R1-R4 (notebooks 47-48; docs/REVIEW_EXPERIMENTS.md)

- **R4, abstention ceiling measured (validation dev set).** Out-of-sample probe TPR - FPR (a lower bound on TV),
  best layer, erased vs ring: recipe LaMa 0.665 (last) / 0.642 (image) vs its denial gap 0.648; TELEA 0.492 / 0.615
  vs 0.642. Erased vs control: LaMa 0.659 / 0.637 vs 0.665; TELEA 0.374 / 0.542 vs 0.654. No read-out gap (bound minus
  gap < 0.05 everywhere). Base model: ring LaMa 0.553 / 0.570 vs gap 0.019; TELEA 0.469 / 0.520 vs 0.130 (54 cases with
  both answers): the base model's hidden states hold separation its answers do not use; training closes it.
- **R3, frozen encoders (erasure vs control edit, main test; whole image / crop).** Qwen3.5-4B 0.859/0.898 (LaMa),
  0.856/0.873 (TELEA), 0.798/0.841 (diffusion); BiomedCLIP 0.812/0.884, 0.799/0.859, 0.781/0.831; DINOv2 0.730/0.823,
  0.688/0.742, 0.666/0.747; RAD-DINO 0.710/0.764, 0.671/0.645, 0.666/0.669. No alternative better by >= 0.05 (reading
  not met): no evidence another frozen encoder holds more. Side result: BiomedCLIP erasure vs unedited on diffusion
  crops +0.074 [0.039, 0.110]. Qwen's encoder detects control edits most (C vs O 0.61-0.75, whole image).
- **R1, hard-negative swap (CORAL-style), `v4q_hns_s0` vs `v4q_sftc_s0`:** does not pass. TELEA ESG -0.028
  [-0.073, 0.017], LaMa ESG +0.011, found +0.017, lesion-free claims +0.013. Hard negatives for 2,603 of 2,739 cases;
  the swapped image was already rejected by ~26 nats (margin 2), so the term rarely acted.
- **R2, vision LoRA with layer-wise decay (0.1 top, x0.9 per block), `v4_vlrd_s0` vs `v4_s1`:** does not pass.
  Found +0.017 [-0.034, 0.067] (rule +0.03); ESG LaMa +0.061 [-0.011, 0.134], TELEA +0.034 [-0.028, 0.101];
  lesion-free claims -0.075 [-0.150, 0.000]; TELEA ring denial +0.075 [0.030, 0.128]. One seed.
- Paper: new Section 4.6 and Appendix Table (review checks); Fig. 4B gains the two arms; perception and ceiling text
  updated.

## 2026-11-16 — review checks R6, R7 (notebook 50; docs/REVIEW_EXPERIMENTS.md, Amendment 1)

- **R6, Med-CAP-style adaptive prior suppression (validation dev set; fitted on half A, LaMa views; reported on half B,
  118 cases):** does not pass. Chosen variant: fixed, a = 1.0 (adaptive a0 = 0.5, t = 15.44). TELEA erased-vs-ring
  AUROC raw 0.731; fixed +0.003 [-0.018, 0.024]; adaptive -0.003 [-0.022, 0.019]. The adaptive form lowers LaMa AUROC
  (ring -0.036 [-0.061, -0.010], control -0.047 [-0.075, -0.019]). At the half-A threshold the fixed form finds more
  intact lesions (0.675 vs 0.506) but lowers TELEA ESG (ring 0.325 vs 0.398): a threshold change, not separation.
  Lesion-free claims 0 for all three. Source: RESULTS/fw_stage0/aps.md, aps.json.
- **R7, leakage sensitivity where patient ids do not exist:** reading met. (1) Calibration on training images with ids:
  DINOv2 similarity barely separates same-patient from other-patient images (AUROC ChestX-Det 0.531, 35 images;
  TCGA-LGG 0.530, 486 images). Note: the statistic compares the most similar of a patient's few other images with the
  most similar of hundreds of other-patient images, which favours the latter, but in any case similarity is not a
  patient detector here. (2) Worst-case exclusion: removing the top 25% most similar test cases per source (378 cases
  kept): ESG 0.755; advantage over gemini-4-argon +0.306 [0.200, 0.405], Claude Opus 5.5 +0.435 [0.333, 0.530],
  gpt-6-astra +0.456 [0.342, 0.561]. Top 50% (252 kept): ESG 0.795, all advantages >= +0.375 with CI above zero.
  Sources without ids only, top 50% removed (337 kept): ESG 0.715, erased claims 13.1%, advantages +0.323, +0.454,
  +0.415, all CIs above zero. Median nearest-training similarity by source: LGG 0.889, BUSI 0.844, ChestX-Det 0.987,
  colonoscopy 0.863, SLAKE 0.846. Source: RESULTS/leakage/leakage.md, leakage.json.
- Paper (v3): two paragraphs added to Section 4.6; Section 4.1 points to the exclusion.

## 2026-11-16 — review check R8: v4.2, SIIM in every stage (notebook 51; post hoc)

- **Rule (fixed before any v4.2 test result): PASSED.** Validation net utility 0.632 (v4 0.613; limit >= 0.593),
  lesion-free claims 9.1% (v4 7.7%; limit <= 9.7%), SIIM validation pneumothorax found 65% (v4.1 48%, v4 2%).
- **New SIIM test patients (100 + 100):** pneumothorax found v4.2 53/100, v4.1 26/100 (27% in its original run,
  notebook 27), v4 0/100; healthy called positive 5/100, 1/100, 0/100. ESG 0.360 vs 0.000 (v4), 0.080 (v4.1).
- **Main test (507), v4.2 vs v4:** ESG 0.740 vs 0.758 (-0.018 [-0.073, 0.037], p 0.59); net utility 0.714 vs 0.732
  (p 0.57); CCR 0.856 vs 0.849; erased claims 11.0% vs 9.6% (p 0.64); lesion-free claims 9.0% vs 7.6% (p 0.42).
- **External centres (169):** ESG 0.739 vs 0.597 (+0.143 [0.070, 0.218]); net utility 0.696 vs 0.530 (+0.166
  [0.071, 0.266]); CCR +0.088; erased claims 6.7% vs 11.8%.
- **Fresh internal (76):** no significant difference (net utility +0.098 [-0.105, 0.318]).
- **Fresh external (316):** net utility 0.048 vs -0.053 (+0.101 [0.001, 0.196], p 0.049); CCR +0.060; ESG +0.024
  [-0.043, 0.086]. By source: SIIM (256-px copies) CCR 0.22 vs 0.00, utility -0.70 vs -1.10; BraTS meningioma worse
  (ESG 0.31 vs 0.41, utility -0.17 vs -0.03, healthy claims 0.18 vs 0.08); BUS-UCLM ESG 0.63 vs 0.71; ETIS-Larib
  ESG 0.59 vs 0.46.
- **Standard VQA (all questions):** VQA-RAD 0.539 vs 0.514; SLAKE 0.750 vs 0.730; PathVQA 0.487 vs 0.477.
- One seed. v4 remains the pre-registered model; v4.2 is reported as a post hoc remedy (paper v3: Sections 4.5, 4.6,
  abstract, contributions, limitations). Source: RESULTS/51_v4.2_rebalanced_report.md, adapters/v42_choice.json.

## 2026-11-18 — R5 interim: endoscopist reader R1 (Amendment 3a; one reader)

- Reader: board-certified gastroenterologist / endoscopist, 20 y; all 212 images; median 6.7 s per image.
- **Colonoscopy (primary):** erasures called present 4/17 (23.5%, exact 95% CI 6.8-49.9): LaMa 3/7, Stable Diffusion
  1/10; 3 of the 4 asked "Is there an abnormality?" (polyp questions 1/9). Unedited lesions 8/9, control edits 27/28,
  lesion-free 0/7. Edit AUC 0.68. 10% criterion not judgeable from one reader (0/17 would give upper bound 19.5%).
- **Other sources (descriptive):** erasures called present 20/55, cannot tell 22; edit AUC 0.54 over all sources.
- Agreement with pack-2 trainees on 39 shared images: kappa 0.24 and 0.39.
- Model re-scoring not run in the interim (deviation, reported); done in the final R5 report.
- Source: docs/reader_study/R5_interim_R1.md; paper v4, Section 4.5.

## 2026-11-19 — R9 natural pairs pre-registered (Amendment 4; no results yet)

Real lesion against real absence of the same video or patient, nothing edited: REAL-Colon colonoscopy (primary, up to
180 pairs from 60 videos) and NIH ChestX-ray14 follow-up films (secondary, up to 200 pairs). Models: MedScope-4B, v4.2,
base Qwen3.5-4B, gemini-4-argon, claude-opus-5-5, gpt-6-astra. Reading rules in docs/REVIEW_EXPERIMENTS.md; code in
scripts/natural_pairs.py and notebook 52. Manuscript v4: new Section 5.1 collects the existing shortcut tests and their
limits (no new runs; one bound derived from logged ESG and erased-claim rates).

## 2026-11-20 — Amendment 5 pre-registered (R12-R15) and notebook 53 (no results yet)

R12 training seeds 1-2 of the full recipe; R13 erased-lesion results on low-visibility erasures (edit-trace detector);
R14 open-ended request with a blind text judge; R15 reproduction from the public Hugging Face release. Notebook 53 runs
them with R9 and makes the release public (MedScope-4B, MedScope-4B-v4.2, MedScope-Bench; cards link arXiv:2611.13006).
Manuscript v4: the data-availability text no longer says per-view outputs are in the GitHub repository (they were on
Drive and in a private release); it now points to the public Hugging Face release.

## 2026-11-20 — notebook 53b, first session: R15, R13 done; R14 partial; R9 colonoscopy selection done

- **R15 reproduction (rule met: REPRODUCED).** MedScope-4B downloaded from huggingface.co/bhaskar-ai/MedScope-4B:
  main-test ESG 0.763 (stored run 0.758); 1102/1115 per-view decisions identical (98.8%).
- **R13 edit visibility (rule met).** Edit-trace detector test AUC: control edit vs unedited 0.826, erasure vs
  unedited 0.841, erasure vs control edit 0.522. Median control-edit score 0.509: 111 low-visibility, 108 other
  erasures. Erased-lesion claims, low-visibility vs other: MedScope-4B 16.2% vs 2.8%; gemini-4-argon 44.1% vs 38.0%;
  claude-opus-5-5 59.5% vs 48.1%; gpt-6-astra 55.0% vs 63.0%. ESG on low-visibility cases: MedScope-4B 0.640
  [0.550, 0.721]; difference vs argon +0.270 [+0.153, +0.387], opus +0.450 [+0.324, +0.568], astra +0.378
  [+0.243, +0.514] (all p < 0.001). Reading: the advantage holds where edits are hard to see, but MedScope-4B's own
  erased-lesion claims rise from 2.8% to 16.2% on those erasures, so part of its denial tracks edit visibility (or
  those erasures keep more residual lesion; not separable here).
- **R14 open-ended request (partial; claude-opus-5-5 run failed: anthropic package not installed in the notebook).**
  36 cases with a lesion-specific question. Reports the finding on unedited / erased images; free-text ESG:
  MedScope-4B 47.2% / 0.0%, 0.472 [0.306, 0.639]; Qwen3.5-4B 80.6% / 52.8%, 0.278; gemini-4-argon 69.4% / 38.9%,
  0.306 (difference vs MedScope +0.167 [-0.028, +0.361], p 0.135); gpt-6-astra 83.3% / 47.2%, 0.361 (+0.111
  [-0.056, +0.278], p 0.250). Rule (above each flagship, interval above 0) not met with 2 of 3 flagships; final after
  the opus run. MedScope-4B never reports an erased lesion in free text but also reports fewer real lesions.
- **R9 colonoscopy:** REAL-Colon selection complete (60 videos annotated; 46 with pairs; 103 pairs); candidate frames
  extracted for 33 of 46 videos before the session stopped (22:33 UTC). Fixes for the rerun: API clients installed in
  notebooks 52-53b; video archives now download to local disk instead of Drive.

## 2026-11-21 — R14 complete (notebook 53b, second session)

claude-opus-5-5 added: reports the finding on 86.1% of unedited / 52.8% of erased images, free-text ESG 0.333
[0.139, 0.528]; difference vs MedScope-4B +0.139 [-0.083, +0.333], p 0.232 (n = 36). **Pre-registered rule not
met**: MedScope-4B's free-text ESG (0.472) is the highest of the five models but not above any flagship with the 95%
interval above 0 (36 cases). Reported as a limit: the advantage is shown for the trained yes/no agent format and is
directionally consistent, not established, for open-ended answers; MedScope-4B never reports an erased lesion in
free text (0/36) but reports fewer real ones (47.2% vs 69-86% for the flagships).

## 2026-11-21 — R9 data built; two deviations found in the chest X-ray build (secondary analysis)

- Colonoscopy (primary): 103 pairs from 46 REAL-Colon videos, built as pre-registered. Unaffected.
- Chest X-ray (secondary): 200 pairs built (50 per finding), but (1) the ChestX-Det patient exclusion matched 0
  patients (the project's ChestX-Det views do not carry NIH patient numbers in a form the script recognised), and (2)
  the near-copy check dropped 156 of 200 pairs: it used a coarse 64-bit image hash without the pixel-correlation
  confirmation that check_views.py uses, and chest X-rays of different patients often share a coarse hash. The models
  were run on the remaining 44 pairs. Found while monitoring the run, after one model's chest X-ray result had been
  seen. Handling: the 44-pair chest X-ray analysis is reported as run, with both deviations stated; a corrected rebuild
  (hash matches confirmed by pixel correlation >= 0.98) is reported beside it as post hoc. The colonoscopy reading rules
  are unchanged.


## 2026-11-21 — R9 natural pairs: result (notebook 53b, 22:19 UTC)

**Colonoscopy (primary, pre-registered; 103 pairs, 46 REAL-Colon videos).** Lesion found / lesion-free image answered
absent or referred / natural ESG [95% CI]; paired difference vs MedScope-4B (MedScope minus model), bootstrap over videos:
- MedScope-4B: 37.9% / 86.4% / 0.243 [0.149, 0.340]
- MedScope-v4.2: 39.8% / 86.4% / 0.262 [0.168, 0.357]; -0.019 [-0.094, +0.047], p 0.678
- Qwen3.5-4B (untrained base): 38.8% / 85.4% / 0.243 [0.143, 0.350]; +0.000 [-0.103, +0.095], p 1.000
- gemini-4-argon: 68.0% / 78.6% / 0.466 [0.336, 0.581]; -0.223 [-0.346, -0.102], p 0.001
- claude-opus-5-5: 70.9% / 73.8% / 0.447 [0.317, 0.579]; -0.204 [-0.333, -0.071], p 0.001
- gpt-6-astra: 64.1% / 68.0% / 0.320 [0.212, 0.437]; -0.078 [-0.184, +0.028], p 0.172

**Reading (Amendment 4 rule): does not carry over.** MedScope-4B's natural ESG is above none of the flagships (every
interval reaches 0 or below); it is significantly below gemini-4-argon and claude-opus-5-5. Descriptively: 0.243 on
natural pairs against 0.95 on the counterfactual colonoscopy test, and the same natural ESG as the untrained base
model (0.243). The gap to the flagships comes from lesion detection (MedScope-4B finds 37.9% of real polyps vs
64-71%); on lesion-free frames it is the most often correct (86.4% vs 68-79%). The counterfactual ESG advantage is
therefore established for edited images only; the paper must say so. (Corrected the same evening: an earlier version
of this entry said training "changes nothing measurable" on these pairs. The natural ESG is equal, but the answers
are not: see the per-pair breakdown below.)

**Chest X-ray (secondary, descriptive; 44 pairs after the over-aggressive near-copy check, deviations logged above).**
Natural ESG: MedScope-4B 0.068 [-0.068, 0.205]; v4.2 0.068; Qwen3.5-4B 0.068; gemini-4-argon 0.136 [0.000, 0.295];
claude-opus-5-5 0.045; gpt-6-astra 0.159 [0.000, 0.318]. All differences vs MedScope-4B include 0. By finding,
MedScope-4B: effusion 0.00 (n 11), mass 0.50 (n 10), nodule -0.14 (n 7), pneumothorax -0.06 (n 16). No model separates
lesion from lesion-free follow-up films well. Corrected rebuild (notebook 53c) to be reported as post hoc.

## 2026-11-21 — R9 per-pair breakdown (stored answers only; no new runs) and Amendment 6 (v5)

From `np_v4_colon`, `np_base_colon` and `np_claudeopus_colon` (scored.jsonl), 103 pairs:
- **Lesion-free frames, polyp claimed:** MedScope-4B 2/103, Qwen3.5-4B 15/103, claude-opus-5-5 20/103. MedScope-4B
  asks for a better image ("clarify") on 12 lesion-free frames (11 of them cohort 004) and 3 polyp frames; the
  pre-registered measure counts a clarify as neither safe nor a denial, which is why its lesion-free safe rate is
  86.4% (89/103) and its "lesion found" 37.9% (36 called present + 3 clarify).
- **Polyp frames called present:** MedScope-4B 36/103, Qwen3.5-4B 40/103, claude-opus-5-5 73/103. By thirds of polyp
  box area (small / middle / large): MedScope-4B 5/34, 7/35, 24/34; base 5/34, 8/35, 27/34; claude-opus-5-5 19/34,
  23/35, 31/34. Median polyp box: 2.9% of the frame; 35 of 103 under 2%.
- **Tool use on polyp frames (MedScope-4B):** no tool call on 61 frames (5 found, 53 "absent", 3 clarify); one zoom on
  42 frames (31 found, 11 "absent"). When it calls a polyp present its box is right (IoU >= 0.3) in 32 of 36.
- **By cohort (found / lesion-free safe), MedScope-4B:** 001 10/23, 22/23; 002 5/28, 26/28; 003 6/28, 28/28; 004
  18/24, 13/24.
- Reading: training removed false claims on real lesion-free frames (15 -> 2) but did not improve detection of real,
  small polyps; the model answers "absent" at first glance and zooms only where it already sees something. Its
  training has no real lesion paired with a real lesion-free image of the same patient (training polyps are large,
  centred stills; lesion-free colonoscopy images come from another source). Same pattern as pneumothorax (v4 0/100,
  v4.2 53/100 after training coverage).

**Amendment 6 (R16) pre-registered** (docs/REVIEW_EXPERIMENTS.md), before any training frame was drawn: MedScope-v5 =
the v4.2 stage 3 with natural REAL-Colon pairs added; three fold models (videos 1-5 / 6-10 / 11-15 of each cohort)
answer the 103 R9 pairs of the videos they never saw; the Amendment 4 reading rule is applied to the cross-validated
result; guard on validation; secondary: correct boxes and context-matched lesion-free frames. One attempt. The R9
result for MedScope-4B stays as reported. Notebooks 54a (data, CPU) and 54b (training and tests). Notebook 53b was
stopped during R12 seed 1, stage 1 (about 10 minutes in); R12 is run after 54b. Notebook 53c (chest X-ray rebuild) not
yet run.

## 2026-11-22 — R16 result: MedScope-v5 with natural pairs in training (notebook 54b; Amendment 6; post hoc)

Ran on an A100 80 GB, 00:47-09:01 ET (two trainings at a time). Training data (notebook 54a): 60 REAL-Colon videos,
1,727 polyp frames (772 with the polyp under 2% of the frame) and 1,881 lesion-free frames; folds of 40 training videos
each; 96 context frames for the 103 R9 pairs (7 pairs had no usable frame 3-10 s from a box). The interim look of
notebook 54p was offered but not run.

**Guard (validation, before any test result): PASSED.** Net utility 0.654 (v4 0.613; limit >= 0.593), lesion-free
claims 9.1% (v4 7.7%; limit <= 9.7%).

**Primary: R9 pairs, cross-validated v5 (each pair answered by the fold model that never saw its video), 103 pairs.**
Lesion found / lesion-free safe / natural ESG [95% CI]; difference v5 minus model, bootstrap over videos:
- MedScope-v5 (CV): 63.1% / 92.2% / 0.553 [0.430, 0.670]
- MedScope-4B: 37.9% / 86.4% / 0.243; +0.311 [+0.200, +0.423], p < 0.001
- MedScope-v4.2: 39.8% / 86.4% / 0.262; +0.291 [+0.172, +0.402], p < 0.001
- Qwen3.5-4B: 38.8% / 85.4% / 0.243; +0.311 [+0.194, +0.427], p < 0.001
- gemini-4-argon: 68.0% / 78.6% / 0.466; +0.087 [-0.030, +0.207], p 0.155
- claude-opus-5-5: 70.9% / 73.8% / 0.447; +0.107 [-0.019, +0.233], p 0.115
- gpt-6-astra: 64.1% / 68.0% / 0.320; +0.233 [+0.096, +0.369], p < 0.001

**Reading (Amendment 6 rule): mixed, comparison by comparison.** Cross-validated v5 has the highest natural ESG of all
seven models and is above gpt-6-astra with the interval above 0; above gemini-4-argon and claude-opus-5-5 the
intervals reach below 0 (not established). By fold: 0.63 / 0.49 / 0.53 (flagships 0.20-0.58). By cohort: 0.61 / 0.50
/ 0.39 / 0.75.

**Secondary (descriptive).** Grounded detection (polyp called present with a box of IoU >= 0.3): v5-CV 53/103
(51.5%), gemini-4-argon 52 (50.5%), claude-opus-5-5 50 (48.5%), gpt-6-astra 41 (39.8%), v4 32 (31.1%), base 13
(12.6%). Context-matched lesion-free frames (96 pairs): lesion-free safe v5-CV 88.5% vs flagships 55.2-66.7%; natural
ESG 0.500 vs 0.333 / 0.323 / 0.188 (differences +0.167 [+0.045, +0.280], +0.177 [+0.063, +0.292], +0.312 [+0.167,
+0.446]).

**MedScope-v5 (all videos) on the earlier tests.** Main test: ESG 0.744 vs v4 0.758 (-0.014 [-0.062, +0.036]; no
trade), net utility 0.707 vs 0.732 (n.s.), CCR 0.854 vs 0.849. External centres vs v4: net utility +0.115 [+0.018,
+0.217], CCR +0.071, ESG +0.084 [-0.000, +0.172]; vs v4.2 erased claims 11.8% vs 6.7% (p 0.005). Fresh internal: no
significant difference. Fresh external vs v4: net utility 0.088 vs -0.053 (+0.141 [+0.044, +0.241]), CCR +0.101, but
erased-lesion claims 19.6% vs 8.3% (+0.113 [+0.052, +0.175]; SIIM 35%, ETIS 18%); vs v4.2 erased claims +0.083
(p 0.003). New SIIM patients: ESG 0.400 (v4.2 0.360, v4 0.000). Standard VQA: VQA-RAD 0.517, SLAKE 0.747, PathVQA
0.503 (v4 0.514 / 0.730 / 0.477).

Post hoc, one run, nothing tuned; the 103 pairs were used a second time; flagships used as they are, fold models
trained on other videos of the same four centres. MedScope-4B (v4) stays the pre-registered model; its R9 result stays
as reported. Source: RESULTS/54b_v5_natural_pairs_in_training_(r16)_report.md.

## 2026-11-22 — R16, complete tables (copied from RESULTS/54b_v5_natural_pairs_in_training_(r16)_report.md)

So that every number used in paper v5 (Table 7, Appendix Tables A.9 and A.11) is in this log.

**Primary, natural ESG by fold (0 / 1 / 2):** v5-CV 0.63 (n=38) / 0.49 (n=35) / 0.53 (n=30); MedScope-4B 0.32 / 0.23 /
0.17; v4.2 0.34 / 0.31 / 0.10; Qwen3.5-4B 0.26 / 0.23 / 0.23; gemini-4-argon 0.58 / 0.43 / 0.37; claude-opus-5-5 0.55 /
0.43 / 0.33; gpt-6-astra 0.29 / 0.46 / 0.20.
**By cohort (001 / 002 / 003 / 004; n = 23 / 28 / 28 / 24):** v5-CV 0.61 / 0.50 / 0.39 / 0.75; MedScope-4B 0.39 / 0.11 /
0.21 / 0.29; v4.2 0.52 / 0.11 / 0.21 / 0.25; Qwen3.5-4B 0.35 / 0.04 / 0.14 / 0.50; gemini-4-argon 0.57 / 0.43 / 0.36 /
0.54; claude-opus-5-5 0.43 / 0.43 / 0.29 / 0.67; gpt-6-astra 0.39 / 0.21 / 0.25 / 0.46.

**Context-matched lesion-free frames (96 pairs): lesion found / context frame safe / natural ESG [95% CI]; v5-CV minus
model [95% CI], p:**
- v5-CV: 61.5% / 88.5% / 0.500 [0.367, 0.629]
- MedScope-4B: 36.5% / 84.4% / 0.208 [0.089, 0.333]; +0.292 [+0.174, +0.404], p < 0.001
- v4.2: 37.5% / 86.5% / 0.240 [0.132, 0.352]; +0.260 [+0.126, +0.384], p 0.001
- Qwen3.5-4B: 37.5% / 81.2% / 0.188 [0.032, 0.346]; +0.312 [+0.165, +0.478], p < 0.001
- gemini-4-argon: 66.7% / 66.7% / 0.333 [0.211, 0.458]; +0.167 [+0.045, +0.280], p 0.007
- claude-opus-5-5: 69.8% / 62.5% / 0.323 [0.177, 0.466]; +0.177 [+0.063, +0.292], p 0.004
- gpt-6-astra: 63.5% / 55.2% / 0.188 [0.033, 0.353]; +0.312 [+0.167, +0.446], p < 0.001
By cohort (n = 21 / 27 / 26 / 22): v5-CV 0.62 / 0.44 / 0.27 / 0.73; MedScope-4B 0.48 / 0.11 / -0.04 / 0.36; v4.2 0.43 /
0.19 / 0.08 / 0.32; Qwen3.5-4B 0.43 / -0.04 / -0.19 / 0.68; gemini-4-argon 0.48 / 0.33 / 0.00 / 0.59; claude-opus-5-5
0.52 / 0.15 / 0.12 / 0.59; gpt-6-astra 0.29 / 0.15 / -0.15 / 0.55.

**MedScope-v5 (all videos) on the earlier tests: v5 value, other value, v5 minus other [95% CI], p.**
Main test (507), vs v4: net utility 0.707, 0.732, -0.025 [-0.082, +0.029], 0.420; ESG 0.744, 0.758, -0.014 [-0.062,
+0.036], 0.652; CCR 0.854, 0.849, +0.005 [-0.026, +0.036], 0.840; erased claims 0.110, 0.096, +0.014 [-0.027, +0.055],
0.608; lesion-free claims 0.087, 0.076, +0.010 [-0.021, +0.042], 0.572. vs v4.2: net utility 0.714, -0.007 [-0.054,
+0.038], 0.757; ESG 0.740, +0.005 [-0.044, +0.051], 0.956; CCR 0.856, -0.002 [-0.027, +0.022], 0.907; erased claims
0.110, +0.000 [-0.036, +0.035], 1.000; lesion-free claims 0.090, -0.003 [-0.034, +0.026], 0.907.
External centres (169), vs v4: net utility 0.645, 0.530, +0.115 [+0.018, +0.217], 0.022; ESG 0.681, 0.597, +0.084
[-0.000, +0.172], 0.073; CCR 0.798, 0.727, +0.071 [+0.014, +0.131], 0.019; erased claims 0.118, 0.118, +0.000 [-0.050,
+0.052], 1.000; lesion-free claims 0.020, 0.040, -0.020 [-0.093, +0.042], 0.802. vs v4.2: net utility 0.696, -0.050
[-0.131, +0.032], 0.270; ESG 0.739, -0.059 [-0.132, +0.017], 0.156; CCR 0.815, -0.017 [-0.068, +0.036], 0.618; erased
claims 0.067, +0.050 [+0.017, +0.095], 0.005; lesion-free claims 0.060, -0.040 [-0.104, +0.000], 0.276.
Fresh internal (76), vs v4: net utility 0.484, 0.402, +0.082 [-0.176, +0.349], 0.533; ESG 0.500, 0.472, +0.028 [-0.189,
+0.270], 0.858; CCR 0.819, 0.681, +0.139 [-0.029, +0.324], 0.127; erased claims 0.333, 0.194, +0.139 [-0.026, +0.296],
0.132; lesion-free claims 0.200, 0.125, +0.075 [-0.095, +0.244], 0.470. vs v4.2: net utility 0.500, -0.016 [-0.192,
+0.143], 0.879; ESG 0.528, -0.028 [-0.154, +0.103], 0.760; CCR 0.778, +0.042 [-0.088, +0.167], 0.617; erased claims
0.250, +0.083 [+0.000, +0.184], 0.106; lesion-free claims 0.175, +0.025 [-0.105, +0.158], 0.861.
Fresh external (316), vs v4: net utility 0.088, -0.053, +0.141 [+0.044, +0.241], 0.006; ESG 0.387, 0.393, -0.006
[-0.074, +0.058], 0.880; CCR 0.577, 0.476, +0.101 [+0.043, +0.162], 0.003; erased claims 0.196, 0.083, +0.113 [+0.052,
+0.175], 0.001; lesion-free claims 0.041, 0.047, -0.007 [-0.042, +0.028], 0.880. vs v4.2: net utility 0.048, +0.040
[-0.048, +0.128], 0.355; ESG 0.417, -0.030 [-0.088, +0.032], 0.349; CCR 0.536, +0.042 [-0.006, +0.092], 0.106; erased
claims 0.113, +0.083 [+0.031, +0.138], 0.003; lesion-free claims 0.068, -0.027 [-0.066, +0.008], 0.216.
New SIIM patients (200), vs v4.2: net utility -0.028, -0.096, +0.068 [-0.116, +0.253], 0.470; ESG 0.400, 0.360, +0.040
[-0.060, +0.140], 0.482; CCR 0.585, 0.540, +0.045 [-0.043, +0.131], 0.342; erased claims 0.200, 0.190, +0.010 [-0.063,
+0.083], 0.933; lesion-free claims 0.070, 0.050, +0.020 [+0.000, +0.052], 0.284. vs v4: net utility -1.100, +1.072
[+0.873, +1.263]; ESG 0.000, +0.400 [+0.299, +0.500]; CCR 0.000, +0.585 [+0.490, +0.670]; erased claims 0.000, +0.200
[+0.125, +0.280]; lesion-free claims 0.000, +0.070 [+0.021, +0.125] (all p <= 0.001).
By source, v5 (v4): correct on lesion images / ESG / erased claims / lesion-free claims / net utility. Main test: brain
MRI 0.82 / 0.75 / 0.06 / 0.00 / 0.68 (0.88 / 0.75 / 0.14 / 0.00 / 0.75); breast ultrasound 0.92 / 0.76 / 0.17 / 0.13 /
0.82 (0.88 / 0.74 / 0.14 / 0.07 / 0.78); chest X-ray 0.72 / 0.44 / 0.24 / 0.18 / 0.38 (0.70 / 0.51 / 0.17 / 0.20 /
0.40); colonoscopy 0.98 / 0.95 / 0.04 / 0.04 / 1.04 (0.96 / 0.95 / 0.01 / 0.00 / 1.06); SLAKE 0.47 / 0.41 / 0.12 / 0.11
/ 0.16 (0.53 / 0.47 / 0.12 / 0.12 / 0.22). Fresh external: BraTS meningioma 0.42 / 0.22 / 0.16 / 0.06 / -0.20 (0.53 /
0.41 / 0.16 / 0.08 / -0.03); BUS-UCLM 0.73 / 0.67 / 0.08 / 0.06 / 0.64 (0.73 / 0.71 / 0.02 / 0.06 / 0.67); SIIM
pneumothorax 0.36 / 0.04 / 0.35 / 0.00 / -0.56 (0.00 / 0.00 / 0.00 / 0.00 / -1.10); ETIS-Larib 0.77 / 0.59 / 0.18 / n/a
/ 0.55 (0.69 / 0.46 / 0.21 / n/a / 0.38).
Standard VQA, closed / open / all: v5 PathVQA 0.840 / 0.139 / 0.503, SLAKE 0.881 / 0.670 / 0.747, VQA-RAD 0.725 / 0.255
/ 0.517; v4.2 0.833 / 0.111 / 0.487, 0.872 / 0.681 / 0.750, 0.773 / 0.245 / 0.539; v4 0.801 / 0.125 / 0.477, 0.881 /
0.644 / 0.730, 0.741 / 0.230 / 0.514.

Paper v5 (paper/v5): natural-pairs section, Table 7, Figure 7, checks R13-R15, Appendix Tables A.9 (every registered
analysis and its outcome) and A.11; abstract and contributions rewritten; corrections from a line-by-line audit of this
log against paper v4 (training lesion-free counts, cost-matrix timing, C1-C4 wording, prompting range, earlier model
versions disclosed, longer-training observation added).

## 2026-11-22 — sources added for numbers the manuscript uses (no new runs)

Found by a number-by-number check of paper v5 against this log; each is copied from a stored report.

**R16 grounded detection, complete (RESULTS/54b_v5_natural_pairs_in_training_(r16)_report.md): polyp frames called
present / present with a box of IoU >= 0.3, of 103.** v5-CV 65 / 53; MedScope-4B 36 / 32; v4.2 37 / 34; Qwen3.5-4B
40 / 13; gemini-4-argon 69 / 52; claude-opus-5-5 73 / 50; gpt-6-astra 66 / 41.

**Main test by imaging type (RESULTS/24_v4_everywhere_report.md, 3 Nov): correct on lesion images / ESG / erased
claims / lesion-free claims / net utility.**
- MedScope-4B: brain MRI (78) 0.88 / 0.75 / 0.14 / 0.00 / 0.75; breast ultrasound (57) 0.88 / 0.74 / 0.14 / 0.07 /
  0.78; chest X-ray (91) 0.70 / 0.51 / 0.17 / 0.20 / 0.40; colonoscopy (174) 0.96 / 0.95 / 0.01 / 0.00 / 1.06; SLAKE
  CT/MRI (107) 0.53 / 0.47 / 0.12 / 0.12 / 0.22.
- gemini-4-argon: 0.89 / 0.42 / 0.47 / 0.00 / 0.56; 0.89 / 0.40 / 0.48 / 0.13 / 0.53; 0.65 / 0.20 / 0.49 / 0.06 /
  0.21; 1.00 / 0.69 / 0.31 / 0.11 / 0.83; 0.74 / 0.35 / 0.41 / 0.12 / 0.38 (same order of imaging types).
- claude-opus-5-5: 0.93 / 0.31 / 0.61 / 0.14 / 0.51; 0.92 / 0.29 / 0.62 / 0.40 / 0.40; 0.60 / -0.05 / 0.66 / 0.20 /
  -0.12; 0.96 / 0.57 / 0.40 / 0.37 / 0.53; 0.76 / 0.24 / 0.59 / 0.13 / 0.32.
- gpt-6-astra: 0.83 / 0.50 / 0.31 / 0.10 / 0.43; 0.98 / 0.12 / 0.83 / 0.60 / 0.28; 0.79 / 0.15 / 0.66 / 0.26 / 0.14;
  0.95 / 0.40 / 0.58 / 0.37 / 0.40; 0.68 / 0.29 / 0.47 / 0.22 / 0.17.
So on counterfactual colonoscopy the three flagships score ESG 0.69, 0.57, 0.40, and on natural colonoscopy pairs
0.466, 0.447, 0.320: the same order.

**R9 paired-frame rule, wording against code.** Amendment 4's prose says the paired frame is taken after the track "if
no frame qualifies before". The selection code committed in the same commit as the amendment (0e966c5, 19 Nov 00:11
ET, before any frame was drawn) takes it after the track when fewer than three frames qualify before
(`neg = before if len(before) >= 3 else after`), and that is what ran; Amendment 6 states the rule this way. Of the
103 pairs, 75 take the lesion-free frame from before the track and 28 from after it. The two wordings differ only for
tracks with one or two qualifying frames before; how many of the 28 these are was not stored.

**Numbering of the review checks.** REVIEW_EXPERIMENTS.md holds R1-R9 and R12-R16: fourteen checks. The numbers R10
and R11 were never used (two script docstrings carried them for what became R13 and R14; corrected in 2eafc91).

**R16 by source, reading.** On the fresh external set v5's extra erased-lesion claims over MedScope-4B come from SIIM
pneumothorax (35% against 0%) and, slightly, BUS-UCLM (8% against 2%); ETIS-Larib is 18% against 21% and BraTS
meningioma 16% against 16%. The earlier note "SIIM 35%, ETIS 18%" listed v5's rates only.

## 2026-11-22 — paper v5 checked by four independent agents and revised; corrections and sources (no new runs)

Two reviewer agents (one ML venue, one clinical venue; each saw only the manuscript) and two number checkers (every
number in the changed parts of paper v5 against this log). About 1,100 numbers were checked; none in the natural-pair
sections disagreed with this log, and four elsewhere were wrong or unsourced as listed below.

**Corrections to earlier entries of this log.**
- Entry of 3 Nov, lesion-size quartiles: "flagships 0.2-0.45 in all" is wrong. Per quartile (Q1-Q4), ESG is
  gemini-4-argon 0.400 / 0.556 / 0.418 / 0.509, claude-opus-5-5 0.200 / 0.352 / 0.345 / 0.418, gpt-6-astra 0.273 /
  0.333 / 0.400 / 0.218: range 0.20-0.56, as the manuscript says.
- MedGemma 1.5 4B, main test: the CCR of 0.660 in the first-look table predates the plain-prose re-scoring. Re-scored
  (RESULTS/24_v4_everywhere_report.md): CCR 0.674 (MedScope-4B 0.849, +0.176 [0.116, 0.235]), ESG 0.283, erased claims
  54.3%, lesion-free claims 24.0%, net utility -0.255.
- v4.1 SIIM validation detection is 46% in its original run (notebook 27) and 48% when re-run in notebook 51 for R8:
  one case apart; both are logged above. R8 passes with either.

**Sources for numbers used in the manuscript (RESULTS/24_v4_everywhere_report.md unless stated).**
- MedScope-4B main-test ESG 0.758 [0.701, 0.815] (RESULTS/v4_final_test/report.md).
- Strict ESG (explicit "absent" answers only): MedScope-4B 0.758; gpt-6-sol 0.237, gpt-6-astra 0.311, gpt-6.1-sol
  0.297, Claude Fable 5.1 0.342, Claude Opus 5.5 0.324, Claude Sonnet 5.5 0.397, gemini-4-argon 0.470,
  gemini-3.1-pro 0.384, gemini-3.8-flash 0.269.
- Net utility without the 170 degraded views: MedScope-4B 0.774; gpt-6-astra 0.310, claude-opus-5-5 0.361,
  gemini-4-argon 0.579 (MedScope-4B minus model +0.464, +0.413, +0.195; each p < 0.001).
- Grounded accuracy (IoU >= 0.3): 0.785 main test, 0.655 external centres.
- Solved-examples prompt, 150 cases: gemini-4-argon claims 36.8% of erased lesions (the low end of the
  manuscript's 36.8-66.2% range); MedScope-4B on the same 150 cases ESG 0.750, erased claims 7.4%.
- Fresh external, MedScope-4B minus gemini-4-argon, net utility: -0.363 [-0.496, -0.233], p < 0.001. Erased claims
  8.3% against 31.5% / 42.3% / 35.7% (argon / opus / astra); ESG 0.393 against 0.435 / 0.292 / 0.268.
- Held-out wordings (373 cases): net utility +0.006 [-0.033, 0.041], p 0.738.
- Tools off: ESG 0.753 against 0.758 (p 0.918); net utility -0.092 (p 0.003); CCR -0.053 (p 0.001).
- Lesion-size quartiles, MedScope-4B: ESG 0.545 / 0.741 / 0.836 / 0.909; erased claims 18.2 / 13.0 / 5.5 / 1.8%.
- External centres by source, MedScope-4B ESG: CVC-ClinicDB 0.85, BraTS-Africa 0.71, BUS-BRA 0.58, QaTa-COV19 0.05.
- Qwen3.5-4B (base), standard VQA closed / open / all: VQA-RAD 0.657 / 0.260 / 0.481; SLAKE 0.826 / 0.424 / 0.570;
  PathVQA 0.545 / 0.021 / 0.293.
- Erasures gemini-4-argon rated unedited (61) against edited (158): MedScope-4B claims 15% against 8%; the nine
  frontier models 41-64% on the 61.
- Reader study (entries of 12-13 Nov): the two trainee readers called a finding on 16/32 and 7/32 unedited
  lesion-free images, 23/64 reads (35.9%), against 35/64 (54.7%) erased reads. "By majority" with two readers means
  both: 13 erased images both called positive ("residual"), 19 at most one did ("majority-clean"), 10 neither
  ("reader-clean") (scripts/reader_verified.py).
- R9 stored answers, tool use on the 103 polyp frames: the untrained base calls a tool on every frame (97 once, 4
  twice, 2 three times) and calls 40 present, 13 with a box on the polyp; MedScope-4B makes no tool call on 61. The
  earlier sentence in the manuscript that MedScope-4B "like the base model" decides at first glance was wrong and is
  removed.
- Training zooms: in medscope/agent/trajectories.py a training trajectory zooms only on a view that has a lesion box,
  and the zoom region is that box padded; lesion-free training images are answered without a zoom.
- Critical findings (a miss costs -4.0): brain tumour, malignant breast lesion, pneumothorax or mass on chest X-ray,
  SLAKE findings labelled cancer or tumour (medscope/data/loaders).

**Still without a source in the reports read today (carried from manuscript v4; to re-read from RESULTS before
submission).** C2 standard deviations (erased claims +-7.9 / +-4.0, CCR +-0.086 / +-0.026); the first trainee
reader's edit AUC 0.54; tool-family 0.141, 0.067 and [0.045, 0.106]; R1 LaMa interval [-0.022, 0.050]; R8 interval
[-0.074, 0.038]; why the fresh external set lists 168 lesion and 150 lesion-free images but 316 evaluated cases.

**Manuscript v5, changes made after the review (text only).** Abstract, contributions, Section 4.7 lead and
conclusion re-ordered around one finding (the trained agent rarely claims what is not shown; finding real lesions
needed training coverage). Each negative result is now stated once in the results and once in a single Limitations
paragraph. Over-claims removed: "keeps its advantage at external centres", "physicians support / reader-validated",
"highest of seven models", "threshold-independent", "formal abstention ceiling", "perception limit", "every
intervention shifted the threshold", "more than half", "fixed before the test sets were used", "no model had seen".
Reader result now given next to the readers' lesion-free call rate. Strict ESG, net utility without degraded views and
grounded accuracy reported. ETIS-Larib attribution, paired-frame rule, check numbering (R1-R9, R12-R16), "27
comparisons" label, arm counts (4 checks + 8 one-seed pilots or screens), and four stale appendix lines corrected.
Outcomes table: three declared analyses added (v4.1 rule not met; stage 4 not triggered; selection-rule test not
run). Chest X-ray natural pairs and the error catalogue moved to the appendix. Limitations added: authors as
readers, registration in our own repository, earlier versions run on the main test, generic questions, image
resolution, single API runs, no task-specific baseline, no image-blind control, no natural-pairs-only arm.

**Ratings by the two reviewer agents (their judgement, before the revision).** ML venue: NeurIPS Evaluations &
Datasets 3 of 6 (borderline reject), "would move to 4-5 with the re-scoping and re-analyses"; TMLR leaning accept
conditional on text and re-analysis changes. Clinical venue: Medical Image Analysis major revision. Estimated
acceptance: TMLR about 60% (80% after text fixes), MIDL 40-55%, MICCAI about 35%, Medical Image Analysis about 35%
(45% with the expert reader study, seeds and restructuring), NeurIPS E&D 18% (35% after fixes), npj Digital Medicine
15-20%, Radiology: AI about 10%. Experiments both ask for: the finished expert reader study; independent
confirmation of v5 (leave-one-centre-out, or a second colonoscopy video set); natural pairs without counterfactual
views; seeds (R12); results by question type; an image-blind control.

## 2026-11-22 — Amendment 7 pre-registered (R17-R22), code and notebooks 55a-58 (no results yet)

After the independent review of manuscript v5, the plan for six further checks was committed at 11:06 ET (03eb83e)
before any of them ran: R17 counterfactual views x natural pairs (stage-1 factorial, three folds); R18 the v5 recipe
with every video of one centre left out (four trainings; the same reading rule against the stored flagship answers);
R19 an image-blind control (blank and swapped images, nine frontier models, MedScope-4B, base); R20 the main results
by question type (stored answers); R21 a one-seed pilot of rewarding the look, suggested by S. Sharma (look-first
training; GRPO with a process reward and its control); R22 access to CheXthought and its schema only. R12 (seeds) and
the chest X-ray rebuild stay in notebooks 53b and 53c; R5 (expert readers) stays open.

Code: `scripts/natural_pairs.py colon-loco` (leave-one-centre-out files from the frames already drawn: 23 / 28 / 28 /
24 test pairs for centres 001-004, 45 training videos each), `scripts/question_type.py`, `scripts/blind_views.py`,
`medscope/train/look.py` with `--look-first` (train_sft) and `--look-bonus` (train_grpo), `scripts/release_v5.py`;
11 new tests (225 pass). Notebooks: 55a (R20, R19), 55b (R18), 55c (R17), 56 (R21), 57 (R22), 58 (v5 release).

Manuscript v5: new title ("MedScope-Bench: Do Medical Vision-Language Models Answer from the Image? Matched
Counterfactual Erasures and Unedited Same-Patient Pairs"), abstract cut to 250 words, a draft AI-use declaration for
the authors to confirm. No number changed.

## 2026-11-22 — R22: CheXthought access confirmed (notebook 57); run status of Amendment 7

Notebook 57 done. CheXthought (owner AIMI, `chexthought:ds7j`) opens and downloads to Colab: one file,
chexthoughtdataset.csv (509 MB), 103,592 reasoning traces on 50,312 CheXpert Plus images (every image read at least
twice; median 2, max 42 reads), columns image_id, chain_of_thought_reasoning, spatial_annotations (normalised click
points linked to [#n] markers in the text), report. Median 277 words per trace. CheXpert Plus (images, CheXpert
labels, reports, RadGraph) also opens. Keyword counts (pneumothorax in 78,369 traces) include negations; per-finding
positive / negative / uncertain statements are computed in notebook 57b (scripts/chexthought.py).

Running: 55a (R20, R19) and 53c (chest X-ray rebuild). Not yet started: 55b (R18), 55c (R17), 53b (R12 seeds),
56 (R21), 57b, 58 (release, last).

## 2026-11-22 — R20 result: the headline holds on finding-specific questions (notebook 55a; Amendment 7)

Stored main-test answers split by question type (RESULTS/r20_question_type.md). 219 lesion cases: 114 ask about a
named finding, 105 are generic ("abnormality", "healthy", "normal"); lesion-free cases 128 and 160.

Finding-specific questions (114 lesion cases): MedScope-4B ESG 0.728 [0.649, 0.807], erased claims 9.6%, lesion-free
claims 7.8%. Nine frontier models ESG 0.298-0.439, erased claims 37.7-53.5%: gpt-6-sol 0.351, gpt-6-astra 0.351,
gpt-6.1-sol 0.333, claude-fable-5-1 0.333, claude-opus-5-5 0.342, claude-sonnet-5-5 0.386, gemini-4-argon 0.439,
gemini-3.1-pro-preview 0.316, gemini-3.8-flash 0.298; base Qwen3.5-4B 0.263. MedScope-4B minus each: +0.289 [0.175,
0.412] (gemini-4-argon) to +0.430 [0.316, 0.544] (gemini-3.8-flash), all p < 0.001; against Claude Opus 5.5 +0.386
[0.280, 0.500], gpt-6-astra +0.377 [0.246, 0.509].
Generic questions (105): MedScope-4B 0.790 [0.714, 0.867], erased claims 9.5%; frontier 0.238-0.505, erased claims
44.8-70.5%; MedScope-4B minus each +0.286 to +0.552, all p < 0.001.

**Reading (Amendment 7): met.** MedScope-4B is above each of the three flagships on finding-specific questions with
the interval above zero (and above all nine). Frontier models claim erased lesions less often on finding-specific
than on generic questions (for 8 of 9), as expected if part of the generic-question claims reflect other findings.
The by-imaging-type tables of this run show "unknown" (the views carry no meta.modality); fixed in e5925e2, to be
regenerated by rerunning the notebook (stored answers only). R19 (image-blind) was still running.

## 2026-11-22 — R19 result: frontier models do not claim findings on a blank or unrelated image (notebook 55a)

183 main-test lesion cases with a "Yes" question (RESULTS/r19_image_blind.md). Blank: a grey image of the same size.
Swapped: a lesion-free main-test image of another imaging type (141 of 183; same-type swaps left out, a bug in the
first build, fixed e5925e2).

| Model | Blank: claimed / denied / clarify | Swapped: claimed / denied / clarify | Erased: claimed | Erased minus blank [95% CI] |
| --- | --- | --- | --- | --- |
| MedScope-4B | 0 / 100 / 0% | 2.1 / 21.3 / 76.6% | 10.9% | +0.109 [0.066, 0.158] |
| Qwen3.5-4B | 0 / 18.6 / 81.4% | 2.1 / 18.4 / 79.4% | 40.4% | +0.404 [0.333, 0.475] |
| nine frontier models | 0 / 0 / 100% (every model) | 0-2.1 / 0-17.0 / 82-100% | 42.1-56.8% | +0.421 to +0.568, all p < 0.001 |

(gpt-6-sol 48.1%, gpt-6-astra 54.1%, gpt-6.1-sol 54.6%, claude-fable-5-1 52.5%, claude-opus-5-5 54.1%,
claude-sonnet-5-5 48.1%, gemini-4-argon 42.1%, gemini-3.1-pro-preview 52.5%, gemini-3.8-flash 56.8%.)

**Reading (Amendment 7).** For every model the erased-claim rate is above the blank-claim rate with the interval above
zero: the erased-lesion claims are **not** explained by the question alone. Every frontier model asks for a better
image when shown a blank or an image of the wrong kind. The manuscript's phrase "answer from the question rather than
the image" is therefore replaced by "claim findings the image no longer shows": the claims depend on what remains in
the edited image (context, residual or secondary signs, the setting the image comes from), not on the question alone.
The blank image is an easy control (it is obviously not a medical image); a same-type lesion-free image is the
natural negative already reported (lesion-free claims 9.0-30.9%).

## 2026-11-22 — R20 by imaging type (notebook 55a rerun with the fix; stored answers)

Lesion cases finding-specific / generic: brain MRI 18 / 18, breast ultrasound 42 / 0, chest X-ray 20 / 21,
colonoscopy 24 / 59, SLAKE 10 / 7. Pooled result unchanged (logged above: met). By imaging type, finding-specific
questions, MedScope-4B ESG and the flagships (gemini-4-argon, claude-opus-5-5, gpt-6-astra):
- breast ultrasound (42): 0.738 vs 0.405 / 0.286 / 0.119; above all nine, p < 0.001.
- colonoscopy (24): 0.917 vs 0.792 / 0.625 / 0.625; above opus and astra (p 0.012, 0.025), not gemini-4-argon
  (+0.125 [-0.083, 0.333]); claude-sonnet-5-5 ties (0.917). Frontier erased claims 0-45.8% (mean of the nine 26.9%)
  against 35.6-69.5% (mean 52.4%) on the 59 generic colonoscopy questions. The 45% frontier claim rate on erased
  polyps quoted in the manuscript pools both; on polyp-specific questions it is 27%.
- brain MRI (18): 0.778 vs 0.500 / 0.389 / 0.611; above gemini-4-argon and opus, not astra (p 0.068) nor the
  gpt-6 models; base Qwen3.5-4B 0.722.
- chest X-ray (20): 0.550 vs 0.150 / 0.100 / 0.300; above opus (p 0.030), not gemini-4-argon (p 0.077) or astra.
- SLAKE (10): 0.500 vs 0.200 / 0.300 / 0.300; no difference significant (n = 10).
Reading: the pooled advantage on finding-specific questions holds; by imaging type it is clearest in breast
ultrasound, and in colonoscopy polyp-specific questions it is smaller (n = 24) than the pooled colonoscopy figure.

## 2026-11-22 — chest X-ray natural pairs, corrected rebuild (notebook 53c; post hoc)

Near-copy check confirmed by pixel correlation: 200 pairs built (50 per finding), 183 scored; patients excluded 0
(the ChestX-Det exclusion still matches none). Natural ESG: MedScope-4B 0.169 [0.098, 0.240]; v4.2 0.126; base
0.071 [0.005, 0.137]; gemini-4-argon 0.109; claude-opus-5-5 0.115; gpt-6-astra 0.148. MedScope-4B minus flagships
+0.060 / +0.055 / +0.022, all intervals include zero; minus base +0.098 [0.022, 0.175], p 0.012. By finding,
MedScope-4B: effusion 0.31, mass 0.24, nodule 0.13, pneumothorax 0.00 (n 45-46 each). Reading: on unedited chest
X-ray follow-up pairs every model separates lesion from lesion-free films poorly (0.07-0.17); MedScope-4B is
highest in point estimate and above its base, not above the flagships; pneumothorax again 0.00 for MedScope-4B.

57b: first run stopped at the labels step (the notebook copy had the old cell); the statement reader and label
download were fixed in 83c8fc7 and the script now continues without labels if the label file is wrong.

## 2026-11-22 — CheXthought statistics (notebook 57b; R22, descriptive)

103,592 traces, 50,312 images. Statements read by rules (scripts/chexthought.py, NegEx-style), spot-checked by eye:
about 90% of the 160 sampled sentences read correctly; the misreadings found ("resolution of", "evacuation of",
"survey ... for", "any ... masses") were fixed after this run (the counts below predate that fix).

| Finding | Traces positive / uncertain / negative | Images both readers positive | Images readers disagree | Positive traces with click points | Images CheXpert label 1 |
| --- | --- | --- | --- | --- | --- |
| pneumothorax | 8,149 / 1,919 / 67,943 | 2,072 | 4,695 | 7,062 | 4,504 |
| pleural effusion | 40,900 / 10,364 / 31,636 | 12,075 | 15,467 | 34,811 | 21,916 |
| consolidation | 14,077 / 12,610 / 32,142 | 1,884 | 15,627 | 12,685 | 3,301 |
| nodule | 2,402 / 602 / 1,967 | 306 | 2,149 | 2,201 | (lung lesion 1,926) |
| mass | 1,001 / 927 / 6,997 | 161 | 1,434 | 794 | (lung lesion 1,926) |
| cardiomegaly | 22,385 / 3,135 / 3,468 | 4,479 | 14,053 | 15,880 | 7,663 |
| edema | 19,496 / 10,102 / 9,670 | 4,225 | 12,687 | 14,078 | 13,059 |
| atelectasis | 21,621 / 21,659 / 1,155 | 3,436 | 19,389 | 18,508 | 7,504 |

Against the CheXbert impression labels of CheXpert Plus (a different radiologist's report): traces on label-1 images
positive or uncertain 68.7% (pneumothorax), 81.2% (effusion), 61.4% (consolidation), 68.5% (cardiomegaly), 70.9%
(edema), 70.4% (atelectasis); on label-0 or blank images negative or silent 96.7%, 77.7%, 81.8%, 83.5%, 90.1%, 70.8%.
Reading: for pneumothorax, the finding MedScope-4B missed entirely, CheXthought offers about 2,000-4,500 positive
images, about 7,000 positive statements with click points, and about 4,700 images on which two radiologists
disagree, against 4 pneumothorax images in our training set. Designs for Sonali Sharma's ideas 1, 3 and 4 on this
data are to be registered (Amendment 8) before any training.

## 2026-11-22 — R18 result: v5 with no centre shared (notebook 55b; Amendment 7): mixed, as before

The v5 recipe trained four times, each without every video of one REAL-Colon centre (45 training videos each); each
of the 103 R9 pairs answered by the model that never saw its centre (RESULTS/55b_v5_leave-one-centre-out_(r18)_report.md).

| Model | Polyp not denied | Polyp-free: absent or refers | Natural ESG [95% CI] | v5-LOCO minus model [95% CI], p |
| --- | --- | --- | --- | --- |
| v5, leave-one-centre-out | 58.3% | 91.3% | 0.495 [0.370, 0.612] | -- |
| v5, cross-validated (R16) | 63.1% | 92.2% | 0.553 [0.430, 0.670] | -0.058 [-0.132, +0.010], p 0.119 |
| MedScope-4B | 37.9% | 86.4% | 0.243 | +0.252 [+0.147, +0.360], p < 0.001 |
| v4.2 | 39.8% | 86.4% | 0.262 | +0.233 [+0.120, +0.343], p < 0.001 |
| Qwen3.5-4B | 38.8% | 85.4% | 0.243 | +0.252 [+0.135, +0.367], p 0.001 |
| gemini-4-argon | 68.0% | 78.6% | 0.466 | +0.029 [-0.091, +0.152], p 0.696 |
| claude-opus-5-5 | 70.9% | 73.8% | 0.447 | +0.049 [-0.072, +0.174], p 0.494 |
| gpt-6-astra | 64.1% | 68.0% | 0.320 | +0.175 [+0.039, +0.311], p 0.013 |

By centre (held out): 0.61 / 0.39 / 0.29 / 0.75 (cross-validated v5 0.61 / 0.50 / 0.39 / 0.75). Grounded detection:
60 called present, 50 with a correct box (v5-CV 65 / 53; gemini-4-argon 69 / 52; opus 73 / 50; astra 66 / 41).
Context-matched frames (96 pairs): natural ESG 0.427 [0.286, 0.562]; minus gemini-4-argon +0.094 [-0.042, 0.220],
opus +0.104 [-0.030, 0.239], astra +0.240 [0.101, 0.375]; 85.4% of context frames absent or referred (flagships
55.2-66.7%).

**Reading (rule of Amendments 4, 6 and 7): mixed.** Above gpt-6-astra with the interval above zero; above
gemini-4-argon and Claude Opus 5.5 in point estimate, intervals include zero. Holding out the whole centre cost
0.058 natural ESG against the cross-validated v5 (interval includes zero), mostly in centres 002 and 003. The gain
over MedScope-4B, v4.2 and the base model (+0.23 to +0.25) holds with no centre shared. v5 still answers the most
polyp-free frames "absent" or refers them (91.3% against 68.0-78.6%), and finds fewer polyps than the flagships
(58.3% against 64.1-70.9%).

## 2026-11-23 — R12 seed 1 of the full v4 recipe (notebook 53b, section 6; Amendment 5): partial

Seed 1 finished all three stages (adapter `seed1_s3/final`, 13:29 ET) and its four test runs (RESULTS/seed1_test,
seed1_ext, seed1_fresh, seed1_ext2, summary.json; 14:06 ET). Seed 0 is MedScope-4B (v4 final evaluation, 2026-11-03).

| Set (cases) | Seed | CCR | ESG [95% CI] | Erased-lesion claims | Lesion-free claims | Net utility |
| --- | --- | --- | --- | --- | --- | --- |
| Main test (507) | 0 | 0.849 | 0.758 | 9.6% | 7.6% | 0.732 |
| Main test (507) | 1 | 0.861 | 0.744 [0.680, 0.805] | 11.4% | 17.0% | 0.672 |
| External centres (169) | 0 | 0.73 | 0.597 | 11.8% | 4% | 0.530 |
| External centres (169) | 1 | 0.739 | 0.605 [0.505, 0.704] | 11.8% | 12.0% | 0.542 |
| Fresh internal (76) | 0 | -- | 0.47 | -- | -- | 0.402 |
| Fresh internal (76) | 1 | 0.681 | 0.472 [0.314, 0.641] | 16.7% | 20.0% | 0.386 |
| Fresh external (316) | 0 | -- | 0.393 | -- | -- | -0.053 |
| Fresh external (316) | 1 | 0.494 | 0.333 [0.253, 0.410] | 15.5% | 6.1% | -0.099 |

First reading (not the R12 test): ESG and erased-lesion claims reproduce within 0.06 on every set. Lesion-free claims
on the main test are higher for seed 1 (17.0% against 7.6%), as at stage 1 in November (8.7% against 16.3% by seed).
The R12 rule (each seed's main-test ESG above each flagship, paired interval above zero) is computed at the end of
notebook 53b, after seed 2. Seed 2 stage 1 started 14:07 ET.

## 2026-11-24 — R23 CheXthought pneumothorax (notebook 59; Amendment 8): first results, before the paired report

v4.3-cxt = v4.2 stage 3 with the CheXthought pneumothorax views added (adapter `v43cxt_s3/final`, 20:47 ET on 23 Nov).
Guard on validation (fixed in Amendment 8): v4.3 net utility 0.628 and lesion-free claims 9.5% (RESULTS/r23_v43_val);
v4.2 0.632 and 9.1% (2026-11-16 entry); limits 0.612 and 11.1%: within both (the notebook re-scored v4.2 as
r23_v42_val and went on to the tests).

| Set (cases) | Model | CCR | ESG [95% CI] | Erased-lesion claims | Lesion-free claims | Net utility |
| --- | --- | --- | --- | --- | --- | --- |
| New SIIM patients (200) | v4.3-cxt | 0.690 | 0.380 [0.278, 0.476] | 31.0% | 7.0% | 0.145 |
| New SIIM patients (200) | v4.2 | 0.540 | 0.360 | 19.0% | 5.0% | -0.096 |
| CheXthought test (300 + 300) | v4.3-cxt | 0.807 | -- | -- | 15.7% | 0.333 |
| Main test (507) | v4.3-cxt | 0.840 | 0.753 [0.692, 0.811] | 7.3% | 7.6% | 0.725 |
| Main test (507) | v4.2 | 0.856 | 0.740 | 11.0% | 9.0% | 0.714 |
| Fresh external (316) | v4.3-cxt | 0.583 | 0.381 [0.298, 0.461] | 20.2% | 5.4% | 0.127 |
| Fresh external (316) | v4.2 | 0.536 | 0.417 | 11.3% | 6.8% | 0.048 |

(RESULTS/r23_v43_siimte, r23_v43_cxt, r23_v43_test, r23_v43_ext2, summary.json; v4.2 rows from the 2026-11-16 and
later v4.2 entries.) On the new SIIM patients v4.3 finds pneumothorax on 69 of 100 originals against 54 for v4.2, with
lesion-free claims 7.0% against 5.0%; it also claims more erased pneumothoraces (31.0% against 19.0%). The paired
intervals and the R23 reading come from `chexthought.py score-test` at the end of notebook 59.

## 2026-11-24 — R12 complete: training seeds 0, 1, 2 (notebook 53b; Amendment 5): HOLDS

RESULTS/53_release_and_robustness_checks_report.md (07:17 UTC).

| Set | Metric | Seed 0 (MedScope-4B) | Seed 1 | Seed 2 | Mean (sd) |
| --- | --- | --- | --- | --- | --- |
| Main test (507) | CCR | 0.849 | 0.861 | 0.840 | 0.850 (0.010) |
| Main test (507) | ESG | 0.758 | 0.744 | 0.731 | 0.744 (0.014) |
| Main test (507) | Erased claims | 9.6% | 11.4% | 10.5% | 10.5% (0.9) |
| Main test (507) | Lesion-free claims | 7.6% | 17.0% | 9.0% | 11.2% (5.1) |
| Main test (507) | Net utility | 0.732 | 0.672 | 0.698 | 0.701 (0.030) |
| External centres (169) | ESG | 0.597 | 0.605 | 0.605 | 0.602 (0.005) |
| External centres (169) | Net utility | 0.530 | 0.542 | 0.500 | 0.524 (0.022) |
| Fresh internal (76) | ESG | 0.472 | 0.472 | 0.361 | 0.435 (0.064) |
| Fresh internal (76) | Net utility | 0.402 | 0.386 | 0.283 | 0.357 (0.065) |
| Fresh external (316) | ESG | 0.393 | 0.333 | 0.375 | 0.367 (0.031) |
| Fresh external (316) | Net utility | -0.053 | -0.099 | -0.045 | -0.066 (0.029) |

Main-test ESG minus flagship, paired [95% CI]: seed 1 vs gemini-4-argon +0.274 [+0.190, +0.359], claude-opus-5-5
+0.416 [+0.333, +0.495], gpt-6-astra +0.438 [+0.350, +0.526]; seed 2 +0.260 [+0.178, +0.341], +0.402 [+0.311, +0.484],
+0.425 [+0.332, +0.514] (all p < 0.001). Erased claims minus flagship: seed 1 -0.297 to -0.475, seed 2 -0.306 to
-0.484 (all p < 0.001). Net utility: seed 1 +0.107 to +0.363, seed 2 +0.134 to +0.390 (p <= 0.015). Lesion-free claims:
seed 1 higher than gemini-4-argon (+0.080 [+0.034, +0.130], p 0.002) and lower than opus and astra; seed 2 equal to
gemini-4-argon (0.090 each) and lower than opus and astra (p < 0.001).

**Reading (rule of Amendment 5): HOLDS.** Every seed's main-test ESG is above each of the three flagships with the
paired interval above zero. Lesion-free claims vary with the seed (7.6% to 17.0%) and are reported as mean (sd).

## 2026-11-24 — R23 complete: CheXthought pneumothorax (notebook 59; Amendment 8): RAISED

RESULTS/59_chexthought_pneumothorax_coverage_(r23)_report.md (08:29 UTC); 1,500 + 1,500 CheXthought training films,
300 + 300 test films. Guard as re-scored in the notebook: validation net utility 0.628 (v4.2 0.631; limit >= 0.611),
lesion-free claims 9.5% (v4.2 8.6%; limit <= 10.6%): PASSED.

**Primary, new SIIM patients (100 + 100):** pneumothorax called present v4.3-cxt 69/100 (49 with a correct box),
v4.2 53/100 (33), MedScope-4B 0/100; difference vs v4.2 +0.160 [+0.070, +0.260], p 0.002; healthy films called
positive 7/100 vs 5/100 (+0.020 [-0.020, +0.060]). Youden 0.620 [0.510, 0.730] vs 0.480 (+0.140 [+0.040, +0.250],
p 0.010). **Rule (Amendment 8): RAISED.**

**CheXthought test patients (300 + 300), secondary:**

| Model | Pneumothorax called present | With a correct box | Healthy: absent or referred | Youden [95% CI] | v4.3-cxt minus model [95% CI] |
| --- | --- | --- | --- | --- | --- |
| v4.3-cxt | 80.7% | 61 | 84.3% | 0.650 [0.582, 0.716] | -- |
| v4.2 | 35.7% | 38 | 93.0% | 0.287 | +0.363 [+0.264, +0.460] |
| MedScope-4B | 0.0% | 0 | 100.0% | 0.000 | +0.650 [+0.503, +0.812] |
| Qwen3.5-4B | 6.3% | 7 | 85.7% | -0.080 | +0.730 [+0.598, +0.865] |
| gemini-4-argon | 62.0% | 82 | 84.0% | 0.460 | +0.190 [+0.108, +0.272] |
| claude-opus-5-5 | 37.0% | 21 | 83.7% | 0.207 | +0.443 [+0.322, +0.551] |
| gpt-6-astra | 41.0% | 35 | 96.7% | 0.377 | +0.273 [+0.176, +0.374] |

All p < 0.001. Correct box: IoU >= 0.3 against the radiologists' click box.

**Main test, v4.3-cxt vs v4.2:** ESG 0.753 vs 0.740 (+0.014 [-0.037, +0.064]); erased claims 7.3% vs 11.0% (-0.037
[-0.071, -0.004], p 0.039); lesion-free claims 7.6% vs 9.0% (n.s.); net utility 0.725 vs 0.714 (n.s.). vs MedScope-4B:
no metric different (ESG -0.005, p 0.946).

**Fresh external (316), the cost:** erased claims 20.2% vs 11.3% for v4.2 (+0.089 [+0.037, +0.143], p < 0.001) and
8.3% for MedScope-4B; ESG 0.381 vs 0.417 (n.s.); net utility 0.127 vs 0.048 (n.s.) and vs -0.053 for MedScope-4B
(+0.180 [+0.065, +0.302], p 0.004). By source, the rise is in SIIM pneumothorax: erased claims 46% (v4.2 10%, v4 0%),
lesion images correct 51% (22%, 0%). v4.3 finds more pneumothoraces and also says "present" on more films whose
pneumothorax was erased.

## 2026-11-24 — R17 complete: counterfactual views x natural pairs (notebook 55c; Amendment 7): NOT SHOWN

RESULTS/55c_counterfactual_views_x_natural_pairs_(r17)_report.md (21:26 UTC). Four stage-1 arms (seed 0); the two
arms with natural pairs are cross-validated over colonoscopy videos (three folds), 103 natural pairs.

**Primary (Amendment 7): CF-and-natural minus natural-only, natural ESG: -0.058 [-0.168, +0.042], p 0.311.**
Interval includes zero: counterfactual views add nothing shown on unedited frames beyond natural pairs.

| Arm / model | Lesion found | Lesion-free: absent or refers | Natural ESG [95% CI] | Correct box (IoU >= 0.3) |
| --- | --- | --- | --- | --- |
| CF-and-natural | 62.1% | 88.3% | 0.505 [0.369, 0.629] | 48/103 |
| natural-only | 68.9% | 87.4% | 0.563 [0.444, 0.676] | 57/103 |
| CF-only | 35.9% | 86.4% | 0.223 [0.133, 0.309] | 33/103 |
| neither | 52.4% | 68.9% | 0.214 [0.079, 0.343] | 43/103 |
| gemini-4-argon | 68.0% | 78.6% | 0.466 | 52/103 |
| claude-opus-5-5 | 70.9% | 73.8% | 0.447 | 50/103 |
| gpt-6-astra | 64.1% | 68.0% | 0.320 | 41/103 |

Natural pairs raise natural ESG: natural-only minus neither +0.350 [+0.227, +0.474]; CF-and-natural minus CF-only
+0.282 [+0.156, +0.405] (both p < 0.001). CF-and-natural vs flagships: gemini +0.039 (p 0.635), opus +0.058
(p 0.409), astra +0.184 [+0.047, +0.321] (p 0.014). Polyp claimed on polyp-free frames: CF-and-natural 12/103,
natural-only 13, CF-only 3, neither 27. By fold, CF-and-natural 0.63 / 0.40 / 0.47; natural-only 0.58 / 0.51 / 0.60.

**Main test (507), fold-0 models, paired:** CF-and-natural ESG 0.744 vs natural-only 0.260 (+0.484 [+0.408, +0.558])
and vs v4q_cf_s0 0.735 (+0.009, p 0.777); erased claims 13.7% vs 68.0% (natural-only) and 11.9% (v4q_cf_s0, n.s.);
lesion-free claims 16.3% vs 9.4% for v4q_cf_s0 (+0.069 [+0.030, +0.111], p 0.001); net utility 0.684 vs 0.343
(natural-only) and 0.692 (v4q_cf_s0, n.s.).

**Reading:** the pre-registered primary is not shown. Natural pairs drive natural ESG; counterfactual views drive
main-test ESG; only the arm with both does well on both tests, at the cost of more lesion-free claims on the main test.

## 2026-11-25 — R21 pilot complete: rewarding the look (notebook 56; Amendment 7 go signal): NO GO

RESULTS/56_rewarding_the_look_(r21,_pilot)_report.md (01:24 UTC). One seed, fold 0, 38 natural pairs from videos no
arm saw, against the fold-0 v5 model. Suggestion by Sonali Sharma.

| Model | Natural ESG | Polyp not denied | Polyp-free absent or referred | Correct box | Polyp frames inspected | Val. net utility | Val. lesion-free claims |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v5 fold-0 (reference) | 0.632 | 71.1% | 92.1% | 21 | 27 | 0.626 | 11.4% |
| L1 look-first training | 0.500 | 78.9% | 71.1% | 21 | 38 | 0.560 | 25.5% |
| L2 GRPO + process reward | 0.263 | 84.2% | 42.1% | 20 | 38 | 0.564 | 10.0% |
| L0 GRPO, usual reward | 0.579 | 63.2% | 94.7% | 20 | 24 | 0.630 | 7.3% |

L1: NO GO (natural ESG -0.132, correct boxes +0). L2: NO GO (natural ESG -0.368 vs v5, -0.316 vs L0; correct boxes -1).

**Reading:** rewarding inspection made the models inspect every polyp frame (38/38) but not find or locate more
polyps; both look arms said "present" more often on polyp-free frames (L2: 42.1% absent or referred, vs 92.1% for v5).
The GRPO control is close to v5. One seed, 38 pairs: a pilot; not carried forward.

## 2026-11-24 — Amendment 9 pre-registered (R24-R27), code and notebook 60 (no results yet)

Committed at 21:35 ET (a3629e0), before any LDPolypVideo file was downloaded or any v6 model trained. One model,
MedScope-4B-v6, takes the place of v4.2, v4.3-cxt and v5 in the follow-up results: v4.2's three stages with the
REAL-Colon natural frames and the CheXthought films added to stage 3 together.

- **R24** two stage-3 mixes (plain; erased-lesion views kept at their v4.2 share), one chosen on validation images
  only; the R8 guard.
- **R25** the whole recipe with seeds 1 and 2; the rule of Amendment 5; a three-seed vote from stored decisions.
- **R26** natural pairs from LDPolypVideo (160 clips, a hospital no model here has seen; takes the place of R18b):
  v6 against the three flagships by the rule of Amendments 4 and 6; at least 40 pairs for a confirmatory reading.
- **R27** v6 on every earlier test: cross-validated REAL-Colon pairs, new SIIM patients (rule of Amendment 8),
  CheXthought test patients, main test (trade rule), fresh external (erased-lesion claims against v4.2), R13 and R20.

Code: `scripts/train_sft.py` (`--min-erased-share`, `--mix-only`), `scripts/natural_pairs.py ldpolyp-build`,
`scripts/seed_vote.py`, `scripts/release_v5.py` (v6 runs and reports added to the release patterns); 10 new tests
(255 pass). Notebook: 60 (`60_final_model_v6.ipynb`). Its selection, vote, reading and report cells were run once on
made-up decisions to check that they execute; no real result exists. MedScope-4B (v4) stays the pre-registered model.

## 2026-11-24 — Notebook 60 started: LDPolypVideo pairs and the stage-3 mixes (Amendment 9; no model result yet)

**R26 data (`natural_pairs/ldpolyp/report_ldpolyp.txt`, 22:53 ET).** 160 clips, 40,186 labelled frames (33,875 with
a polyp, 6,311 polyp-free); box format read as corners. **116 pairs**; 44 clips without a pair (39: no polyp-free
frame at least 5 frames from a polyp frame; 5: no polyp frame with a box of at least 1%). At least 40 pairs: the
confirmatory reading applies.

**R24 mixes (`v6/mix_*.json`, 23:02 ET; counted by `train_sft.py --mix-only`, nothing trained).** Stage-3 training
views and the share that are erased-lesion views: v4.2 1,756 of 6,217 (28.2%); v6 plain 1,223 of 12,292 (9.9%); v6
kept 4,359 of 15,428 (28.3%). Lesion-free images: 420 (6.8%), 3,801 (30.9%), 3,801 (24.6%). So adding the natural
frames and films without the kept rule cuts the erased-lesion share to about a third of v4.2's; whether that
explains the higher erased-lesion claims of v5 and v4.3-cxt is what R24 and R27 test.

## 2026-11-25 — Notebook 60: scheduling only (no command, name, rule or number changed)

At the pace seen on an A100 80 GB (two jobs at a time, GPU at 98%), the two stage-3 mixes took 5 h and 6.5 h; they
hold 12,292 and 15,428 training views against 6,217 in v4.2's stage 3. Notebook 60's training and test steps were
therefore rewritten as one queue of GPU slots: each step starts when what it needs is ready (the choice of mix no
longer waits for the seeds' stage 1; the tests of v6 no longer wait for the seeds and folds), with six slots on an
H200, four on a G4, three on an H100, two on an A100 80 GB. Every training and test command, every output name and
every reading rule of Amendment 9 is as committed in a3629e0; finished pieces are skipped on resume. The queue was
run on made-up decisions with one, three and six slots (never more jobs at once than slots; stage 3 of seeds and
folds only after the choice; a second pass runs nothing).

## 2026-11-25 — Notebook 60r: the same notebook 60 for a RunPod pod (no command, name, rule or number changed)

`60r_final_model_v6_runpod.ipynb` is built from notebook 60's own cells; only Colab's Drive mount, secrets and
runtime calls are replaced. The Colab folders are recreated on the pod's volume (every stored view keeps its
`/content/...` image path), the data, earlier adapters and stored answers are copied from Google Drive with rclone
(about 20 GB; old runs without their transcripts), whatever of v6 is already on Drive is resumed, and new adapters,
checkpoints, results and a log (`runpod/notebook60.log`) are copied back every 15 minutes and at the end. Checked
here only against stand-ins (the Drive cell against a stand-in rclone; the queue, readings and report cells on
made-up decisions); not yet run on a pod.

## 2026-11-25 — R24 result: MedScope-4B-v6 is the plain mix; guard PASSED (notebook 60; Amendment 9; validation only)

`adapters/v6_choice.json` (22:48 UTC). Validation images only; no test result of v6 exists yet.

**Choice.** Net utility over the main validation views (1,473 views, 540 cases) and the SIIM validation patients
(242 views, 98 cases) together: plain 0.547, kept 0.452. Rule (kept, unless plain is higher by more than 0.005):
**plain**. **Guard on the main validation views: PASSED** (net utility 0.642, v4 0.613, limit >= 0.593; lesion-free
claims 9.1%, v4 7.7%, limit <= 9.7%).

| Validation set | Mix | Net utility | ESG | Lesion images correct (CCR) | Erased claims | Control edit denied | Lesion-free claims |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Main (540 cases) | plain | 0.642 [0.556, 0.721] | 0.706 | 0.819 | 10.6% | 18.8% | 9.1% |
| Main (540 cases) | kept | 0.621 [0.533, 0.704] | 0.716 | 0.792 | 7.5% | 20.9% | 10.0% |
| SIIM patients (98 cases) | plain | -0.031 [-0.313, 0.272] | 0.292 | 0.604 | 31.3% | 39.6% | 8.0% |
| SIIM patients (98 cases) | kept | -0.576 [-0.851, -0.267] | 0.167 | 0.302 | 14.6% | 68.8% | 8.0% |

**Reading.** Keeping the erased-lesion views at their v4.2 share (28.3% of stage-3 views against 9.9%) lowers
erased-lesion claims on both validation sets (10.6% to 7.5%; 31.3% to 14.6%), but on the SIIM validation patients it
halves the pneumothoraces found (60.4% to 30.2%) and raises denials of control-edited films (39.6% to 68.8%): the
model says "absent" more, not more selectively. The plain mix is MedScope-4B-v6; seeds 1 and 2 and the fold models are
trained with it. The kept mix is run on the main test, the fresh external set and the new SIIM patients as planned.

## 2026-11-26 — R25, R26, R27 results: MedScope-4B-v6 on the main test, three seeds, a new hospital and every earlier test (notebook 60; Amendment 9)

Report `results/60_consolidated_model_v6_(r24-r27)_report.md`, written 09:32 UTC on an RTX PRO 6000 Blackwell (Colab
"G4"); readings in `r24_readings_v6.md`, `r25_seeds_v6.md`, `r26_natural_ldpolyp.md`, `r27_*.md`. Every rule was
fixed in Amendment 9 (a3629e0) before any of this ran. One attempt.

**R25, three training seeds: HOLDS.** Every seed is above each of the three flagships on main-test ESG with the paired
interval above zero. The three-seed vote is the reported operating point.

| Main test (507 cases) | Seed 0 (v6) | Seed 1 | Seed 2 | Mean (sd) | Three-seed vote |
| --- | --- | --- | --- | --- | --- |
| ESG | 0.744 | 0.740 | 0.726 | 0.737 (0.010) | 0.753 |
| Lesion images correct (CCR) | 0.847 | 0.872 | 0.874 | 0.865 (0.015) | 0.863 |
| Erased claims | 9.1% | 13.7% | 14.6% | 12.5% (2.9%) | 10.5% |
| Lesion-free claims | 8.7% | 15.3% | 10.8% | 11.6% (3.4%) | 9.0% |
| Net utility | 0.709 | 0.675 | 0.721 | 0.702 (0.024) | 0.726 |

Vote minus each flagship, main-test ESG: gemini-4-argon +0.283 [+0.203, +0.364]; claude-opus-5-5 +0.425
[+0.350, +0.500]; gpt-6-astra +0.447 [+0.368, +0.528]; all p < 0.001.

**R27, main test: no trade.** v6 ESG 0.744 against 0.758 for v4 (-0.014 [-0.068, +0.040], p = 0.680); net utility
0.709 against 0.732 (-0.023 [-0.089, +0.040], p = 0.487). v6 against v4.2, v5 and v4.3-cxt: no interval excludes zero
on any of the five measures.

**R26, LDPolypVideo natural pairs (116 pairs from 160 clips; a hospital no model here had seen): MIXED.**

| Model | Lesion found | Lesion-free frame: absent or referred | Natural ESG [95% CI] | v6 minus model [95% CI], p |
| --- | --- | --- | --- | --- |
| MedScope-4B-v6 | 62.1% | 99.1% | 0.612 [0.526, 0.698] | -- |
| v6 three-seed vote | 61.2% | 97.4% | 0.586 [0.491, 0.673] | +0.026 [-0.009, +0.069], p = 0.238 |
| MedScope-4B (v4) | 45.7% | 96.6% | 0.422 [0.328, 0.517] | +0.190 [+0.112, +0.267], p < 0.001 |
| MedScope-v5 | 59.5% | 99.1% | 0.586 [0.491, 0.672] | +0.026 [-0.017, +0.069], p = 0.351 |
| Qwen3.5-4B (base) | 40.5% | 95.7% | 0.362 [0.276, 0.448] | +0.250 [+0.155, +0.353], p < 0.001 |
| gemini-4-argon | 71.6% | 81.0% | 0.526 [0.422, 0.621] | +0.086 [-0.017, +0.190], p = 0.117 |
| claude-opus-5-5 | 62.9% | 83.6% | 0.466 [0.362, 0.569] | +0.147 [+0.043, +0.250], p = 0.010 |
| gpt-6-astra | 55.2% | 75.0% | 0.302 [0.198, 0.405] | +0.310 [+0.181, +0.431], p < 0.001 |

Natural-pair training carries over to the new hospital (v6 minus v4 +0.190). v6 is above two of the three flagships;
the interval against gemini-4-argon includes zero. Present with a correct box (IoU >= 0.3): v6 66/116, gemini-4-argon
76/116, claude-opus-5-5 66/116, gpt-6-astra 55/116, v4 50/116.

**R27, REAL-Colon natural pairs, cross-validated (103 pairs): MIXED.** v6-CV natural ESG 0.534 [0.394, 0.661]. Minus
gemini-4-argon +0.068 [-0.069, +0.202], p = 0.347; claude-opus-5-5 +0.087 [-0.049, +0.230], p = 0.259; gpt-6-astra
+0.214 [+0.071, +0.343], p = 0.003. v6-CV minus v5-CV -0.019 [-0.086, +0.048], p = 0.604: adding the chest films to
stage 3 costs nothing here. v6-CV minus v4 +0.291 [+0.176, +0.402]; minus v4.2 +0.272 [+0.162, +0.378]. On the 96
context-matched pairs: v6-CV 0.479 [0.322, 0.615]; minus gemini-4-argon +0.146 [+0.000, +0.284], p = 0.067;
claude-opus-5-5 +0.156 [+0.032, +0.277], p = 0.019; gpt-6-astra +0.292 [+0.137, +0.429], p < 0.001.

**R27, pneumothorax, new SIIM patients (100 pneumothorax and 100 healthy films): NOT RAISED.** v6 calls 54/100
pneumothorax films present, v4.2 53/100 (+0.010 [-0.080, +0.100], p = 0.920); healthy films called positive 4/100
against 5/100. Seeds 1 and 2 call 75/100 and 70/100, the vote 68/100 (Youden 0.620 [0.510, 0.730] against 0.500
[0.380, 0.610] for seed 0 and 0.480 for v4.2); the rule was fixed on seed 0, so this is descriptive.

**R27, CheXthought test patients (300 and 300 films).** Youden: v6 0.660 [0.591, 0.726], vote 0.700 [0.633, 0.763],
v4.3-cxt 0.650, v4.2 0.287, gemini-4-argon 0.460, claude-opus-5-5 0.207, gpt-6-astra 0.377. v6 minus each flagship:
+0.200 [+0.122, +0.284], +0.453 [+0.344, +0.560], +0.283 [+0.196, +0.375]; all p < 0.001.

**R27, fresh external (316 cases): THE COST REMAINS.** Erased-lesion claims v6 22.0%, v4.2 11.3% (+0.107
[+0.054, +0.162], p < 0.001); v5 19.6%, v4.3-cxt 20.2% (neither interval excludes zero). By source, v6 against v4.2:
SIIM pneumothorax chest films 33% against 10%, ETIS-Larib 26% against 15%, BUS-UCLM 14% against 8%, BraTS meningioma
12% against 12%. On the same set v6 is above v4 on net utility (0.114 against -0.053, +0.168 [+0.056, +0.279],
p = 0.002) and on lesion images correct (0.607 against 0.476, +0.131 [+0.069, +0.197]); ESG 0.381 against 0.393.
Vote: erased claims 22.6%, net utility 0.147.

**R27, external centres (169 cases).** v6 minus v4: net utility +0.096 [+0.011, +0.182], p = 0.020; ESG +0.076
[+0.009, +0.143], p = 0.033. v6 minus v4.2: ESG -0.067 [-0.126, -0.009], p = 0.025. **Fresh internal (76 cases):**
v6 against v4 and v4.2, no interval excludes zero; v6 minus v5 on lesion images correct -0.139 [-0.250, -0.038].

**R24, the kept mix on the tests (run as planned; not the model).** Main test: net utility 0.765 against 0.709 for the
plain mix (plain minus kept -0.056 [-0.115, +0.003], p = 0.062). Fresh external: erased claims 17.3% against 22.0%
(+0.048 [+0.006, +0.092], p = 0.035). New SIIM patients: lesion images correct 0.320 against 0.530 (+0.210
[+0.111, +0.307]), net utility -0.512 against -0.134 (+0.378 [+0.195, +0.567]).

**R13 again (edit visibility).** Low-visibility erasures (117 cases): ESG v6 0.624 [0.538, 0.709], v4 0.650; v6 minus
gemini-4-argon +0.231 [+0.103, +0.359], claude-opus-5-5 +0.402 [+0.291, +0.513], gpt-6-astra +0.359 [+0.231, +0.479].
Erased claims on low-visibility erasures: v6 13.7%, flagships 42.7% to 57.3%.

**R20 again (question type).** v6 ESG 0.711 [0.632, 0.789] on finding-specific questions (114 lesion cases) and 0.781
[0.695, 0.857] on generic ones (105); minus the flagships +0.272 to +0.368 and +0.276 to +0.524, all p < 0.001.

**Standard VQA (all questions).** v6: PathVQA 0.507, SLAKE 0.743, VQA-RAD 0.532 (v4: 0.477, 0.730, 0.514).

**Reading.** One model now does what v4.2, v4.3-cxt and v5 did separately, with no loss on the main test, and its
lead over the flagships on the main test holds for every seed. On real colonoscopy frames it is far above v4 at two
hospitals, one of them unseen, and above two of three flagships at the unseen one; against gemini-4-argon the
difference is not shown on either set. Two limits stay: erased-lesion claims on the fresh external set remain about
twice v4.2's, and pneumothorax sensitivity on new SIIM patients depends on the seed (54% to 75%).

## 2026-11-26 — R5 interim look: first board-certified radiologist (post hoc, descriptive)

`docs/reader_study/R5_interim_R9.md`. One board-certified radiologist (8 years) finished all 212 images. Erasures called
present 36/72 (50.0%, exact 95% CI 38.0-62.0; LaMa 17/36, Stable Diffusion 19/36); radiology sources 29/55; unedited
lesion images 34/36; control edits 63/68; unedited lesion-free 8/36. Edit detection AUC 0.67 (edited vs unedited), 0.50
(erasure vs control edit). The 10% criterion is not met by this reader; R5 closes with the second radiologist or on 10
January 2027. Not planned in advance (Amendment 3a covers the endoscopist only).
