# R5 interim analysis: endoscopist reader R1 (Amendment 3a)

Run once on 18 Nov 2026 after Amendment 3a (commit b3637de) was committed. One reader: board-certified
gastroenterologist / endoscopist (advanced endoscopy, 20 years), all 212 images, median 6.7 s per image, no notes.
Sources: Google Sheet "MedScope reader study - pack 4" (answers, profiles) and `reader/key_v4.json` on Drive, scored with
`scripts/make_reader_study.py --from-sheet` and `--score` (spreadsheet export: numbers such as 1.0 read as 1).

## Primary: colonoscopy (61 images)

| View | Finding called present |
| --- | --- |
| Unedited lesion | 8/9 |
| Control edit (lesion intact), LaMa / Stable Diffusion | 8/8 / 19/20 |
| Erasure, LaMa | 3/7 (42.9%, exact 95% CI 9.9-81.6) |
| Erasure, Stable Diffusion | 1/10 (10.0%, 0.3-44.5) |
| Erasure, pooled | 4/17 (23.5%, 6.8-49.9) |
| Unedited lesion-free | 0/7 |

- Erasures asked "Is there an abnormality?": 3/8 called present; asked about a polyp: 1/9.
- The 10% upper-bound criterion cannot be judged from one reader: 0/17 would still give an upper bound of 19.5%.
- Edit detection, colonoscopy: AUC edited vs unedited 0.68, erased vs control 0.68; Stable Diffusion erasures called
  edited 5/10, LaMa erasures 0/7.

## Descriptive: other sources (outside the reader's specialty, no criterion)

Erasures called present 20/55 (36.4%), cannot tell 22. AUC edited vs unedited: brain MRI 0.56, breast ultrasound
0.54, chest X-ray 0.48, SLAKE 0.51; all sources 0.54 (erased vs control 0.59).

## Agreement with the trainee readers (pack 2)

39 images appear in both pack 2 and pack 4. Finding answers: agreement 21/39 with the internal-medicine trainee
(Cohen's kappa 0.24) and 24/39 with the radiology trainee (kappa 0.39). Pack 3 answers were not located on Drive, so
the 20 images shared with pack 3 are not compared.

## Not run in the interim (deviation from Amendment 3a, reported)

Model re-scoring on the erasures R1 calls clean was not run: the stored per-view outputs of the frontier runs are
spread over many run folders on Drive, and the Stable Diffusion erasures need the multi-tool runs. With 4 LaMa and 7
Stable Diffusion colonoscopy erasures called clean it would be descriptive at most. It is done in the final R5 report.
