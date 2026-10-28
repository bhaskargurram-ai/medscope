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

## Next

- Merging (04), natural negatives (02b), then GRPO (05) — with natural negatives added to RL
  training if 02b shows an edit-detection shortcut — and final evaluation (06).
