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

## Next

- 02b again (HyperKvasir negatives: in-domain test, plus the RL training split), then GRPO with
  natural negatives (05), then final evaluation on the full test split and both negative sets (06).
