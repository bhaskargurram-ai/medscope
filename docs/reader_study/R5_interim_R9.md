# R5 interim look: first board-certified radiologist (reader code R9)

Run on 26 Nov 2026 after the reader finished all 212 images. Not planned in advance: the plan provides an interim
analysis for the endoscopist only (Amendment 3a); this look is post hoc and descriptive, and the R5 criterion is judged
only when the round closes (two board-certified radiologists, or 10 January 2027). Reader profile as entered:
radiology, board-certified radiologist, 8 years; had not seen packs 2 or 3. Sources: Google Sheet "MedScope reader
study - pack 4" (answers, profiles) and `reader/key_v4.json` on Drive, scored with
`scripts/make_reader_study.py --from-sheet` and `--score` (exported numbers such as 1.0 read as 1). Answers and key
are not in the repository.

## Finding called present, all 212 images

| View | Called present |
| --- | --- |
| Unedited lesion | 34/36 (cannot tell 1) |
| Control edit (lesion intact) | 63/68 (cannot tell 3) |
| Erasure | 36/72 (cannot tell 10); 50.0%, exact 95% CI 38.0-62.0 |
| Unedited lesion-free | 8/36 (cannot tell 5) |

By tool, erasures called present: LaMa 17/36, Stable Diffusion 19/36. Named stress tests (diffuse findings,
pneumothorax): 6/9; localized findings 30/63 (34.9-60.6).

## By source (finding called present)

| Source | Unedited lesion | Control edit | Erasure | Unedited lesion-free |
| --- | --- | --- | --- | --- |
| Brain MRI (LGG) | 9/9 | 9/9 | 8/13 | 1/8 |
| Breast ultrasound (BUSI) | 8/9 | 12/14 | 9/18 | 3/7 |
| Chest X-ray (ChestX-Det) | 8/9 | 12/15 | 10/17 | 0/7 |
| SLAKE CT/MRI | - | 2/2 | 2/7 | 1/7 |
| Colonoscopy (outside specialty) | 9/9 | 28/28 | 7/17 | 3/7 |

Radiology sources together (brain MRI, breast ultrasound, chest X-ray, SLAKE): erasures called present 29/55; unedited
lesion-free 5/29 (my arithmetic from the rows above).

## Edit detection

Rating 3 or 4 = called edited: erasures 32/72, control edits 31/68, unedited 11/72. AUC edited vs unedited 0.67; erasure
vs control edit 0.50.

## Reading

The 10% criterion for erasures is not met by this reader (upper bound 62.0%): as with the two trainees (35/64 reads),
the radiologist still called the finding present on about half of the erased images, in every radiology source. The
radiologist told erasures from control edits no better than chance (AUC 0.50) and found the finding on 34/36 unedited
lesion images and 63/68 control-edited ones. Not run here: re-scoring the models on the erasures this reader called
absent (pre-specified for the final R5 report).
