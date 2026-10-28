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

## Next

- Full test split (100 cases) for both baselines, scoring version 3.
- SFT (notebook 03), merging (04), GRPO (05), final evaluation (06).
