# MedScope v0.10: verification of the expanded audit package

**Date:** 5 November 2026. **Package:** `medscope_audit_d029d26_20261105.zip`. **Snapshot identifier:** `d029d2608e97aaf9447b55240f81bda6a0770f06`. This update follows the 64/100 assessment of package `7b15d59`.

## Decision

**Revised submission-readiness score: 67/100. Recommendation: major revision before submission.** The expanded package substantially resolves the earlier transcript, manifest and probe-reproducibility limitations. The central remaining scientific issue is validation of the synthetic reference labels by qualified readers.

The evidence score increases from 3/5 to 4/5 because answer scoring, grouping and the probe can now be checked rather than inferred from reports. Reproducibility stays at 4/5: the supplied results are substantially auditable, but this was not an independent repeat of image generation, model training or inference; adapters and image pixels are not included, and some evaluation manifests are still absent.

| Dimension | Weight | Score /5 | Points |
|---|---:|---:|---:|
| Novelty and significance | 15 | 3 | 9 |
| Methodological soundness | 15 | 3 | 9 |
| Validity of evidence | 15 | 4 | 12 |
| Statistical analysis | 10 | 4 | 8 |
| Baselines and fairness | 10 | 3 | 6 |
| Clinical relevance and safety | 10 | 2 | 4 |
| Reproducibility and transparency | 10 | 4 | 8 |
| Honesty and limitations | 5 | 4 | 4 |
| Reporting quality and clarity | 5 | 4 | 4 |
| References, ethics, declarations | 5 | 3 | 3 |
| **Total** | **100** | | **67** |

The score is an editorial judgment under the existing rubric, not a probability of acceptance. No new clinical performance experiment was supplied in this update; most of its value is stronger verification and clearer interpretation.

## Verification performed

### Package identity and continuity

The ZIP contains 1,382 entries and approximately 242.7 MB uncompressed. The attached manuscript is v0.10 and is byte-identical to the archived PDF. Its SHA-256 is `50e57d8366004d11533fa990450894eb63403f2072c76878d28797ac36b0cc85`.

Every result file present in the previous package is unchanged. Therefore the earlier metric-aggregation and case-bootstrap checks remain applicable without repeating them. The new files add transcripts, 40 view-manifest files, and cached encoder features. The historical natural-negative mismatch is now explicitly explained in the README: the four older runs were summarized on 181 views while their outcome files hold 218 later rows, and they are not used in the paper. This explanation resolves their relevance to the present manuscript; it does not make the old summaries recomputable without the old selection universe.

### Transcript-based rescoring

I remapped the recorded Colab paths to the supplied manifests and used the supplied parsing, answer-matching and reward code, without running models or changing the source archive.

- **186 runs, 134,309 scored rows:** rejudged answer correctness from the transcripts and recalculated rewards. All fields matched the supplied scored records, with **zero discrepancies**.
- **134,011 parseable final responses:** independently reconstructed final actions, correctness, absence flags, box-validity flags and IoU from the final response and manifest lesion box. These matched the saved fields, with **zero discrepancies**.
- The remaining **298 rows were recorded as malformed**, accounting for the difference in totals. They were included in the first rescoring check.
- All four final-model evaluation cohorts were covered, along with the main comparator and ablation runs that had resolvable manifests.

This verifies consistency of the supplied transcripts, manifests and implementation. It does not independently establish clinical correctness of the dataset labels or prove the provenance of model-generated text. Tool-cost rescoring retains recorded tool-use information rather than replaying image tools.

Twenty-two runs could not undergo this full manifest-dependent rescore because their referenced manifests were not available under the supplied paths. They concern paraphrase evaluations, SIIM full-resolution/abnormality checks, and the exploratory v4.1 SIIM evaluations. Their existing summary aggregation remains a separate, weaker check. The package should not claim to contain literally every evaluation manifest.

### Patient/group analysis

All evaluated cases in the four final-model cohorts mapped to a supplied patient/group ID:

| Cohort | Cases | Groups | Largest group |
|---|---:|---:|---:|
| Main test | 507 | 416 | 8 |
| External centres | 169 | 155 | 2 |
| Fresh internal | 76 | 75 | 2 |
| Fresh external | 316 | 230 | 8 |

I reran all 27 main-test patient/group-bootstrap comparisons with 2,000 resamples and seed 0. All remain significant at 0.05/27 = 0.00185185. However, the manuscript's claim that all remain **p < 0.001** is too strong:

**Net utility versus gemini-4-argon: difference +0.167758, patient-bootstrap 95% CI [0.078211, 0.254813], p = 0.001.** The other 26 main comparisons had zero empirical sign-crossings under the stated algorithm. The supplied patient-bootstrap report already prints 0.001 for this Gemini comparison.

I also reran fresh-external ESG versus Claude Opus: **p = 0.060**, reproducing the stated loss of significance under patient/group resampling. These calculations confirm the principal robustness conclusion, while requiring a small correction to its wording.

### Split checks

Within the checked base and v4 training/validation manifests, including the supplied transplant and insertion pools, I found no exact case-ID or patient/group-ID overlap between training and validation, or between those pools and any of the four final-model evaluation cohorts.

This is useful evidence of split separation within the supplied identifier system. It does not resolve identity across differently named public datasets, near-duplicate pixels, completeness of historical exclusions, or all general-VQA replay images. The SIIM/NIH/ChestX-Det and relevant TCGA/BraTS cross-source provenance question therefore remains separate from the now-reproduced grouping calculation.

### Encoder probe

The cached arrays contain 1,800 training views and 657 test views, each with 1,024 pooled features. Each binary task uses 1,200 training and 438 test views. There is no exact case-ID overlap between the cached training and test arrays.

Refitting the supplied logistic-regression procedure reproduced:

| Contrast | Recomputed AUC | Recomputed 95% case-bootstrap CI |
|---|---:|---:|
| Random removal vs original | 0.603178 | [0.583867, 0.626462] |
| Target removal vs original | 0.866183 | [0.840035, 0.894400] |
| Target removal vs random removal | 0.860241 | [0.832029, 0.890372] |

These are close to the stored values; the largest AUC difference is 0.000271, and the manuscript's two-decimal conclusions are unchanged. This is numerical reproduction to reporting precision, not bit-for-bit identity. Pinning the scientific-Python environment would improve exact reproducibility. I did not re-extract encoder features from image pixels.

## Findings now closed or substantially addressed

- The lack of full transcripts is closed for the 186 runs rescored above.
- The lack of patient/group mappings is closed for the four main evaluation cohorts.
- The probe can now be reproduced from its cached features.
- Section 3.8 correctly distinguishes the retrospective Bonferroni check from the versioned preregistration.
- Section 5.1 corrects the Qwen3-VL-8B direction error.
- Section 5.3 identifies the single-seed factorial and acknowledges endpoint-dependent insertion effects.
- The probe interpretation now explicitly acknowledges anatomy-dependent traces.
- The ESG docstring no longer makes the universal edit-detector claim.
- The README appropriately labels the four historical negative-set runs.

## Remaining corrections in v0.10

1. **Discussion contradicts Results.** Section 8.1 still says “lesion insertions add nothing.” Replace it with the mixed main-test/fresh-external interpretation now present in Section 5.3.
2. **Shortcut language remains absolute.** Sections 5.3, 8.1 and 8.3 still say controls stop or close the editing shortcut. The experiment demonstrates reduced denial after a control edit; it does not exclude all edit-based strategies.
3. **A fitted probe is not a formal upper bound.** Section 5.4 now says a linear probe bounds what a linear reader can recover. One finite-sample, regularized logistic-regression fit estimates the performance of that particular procedure; it does not establish an upper bound over all linear classifiers. Use “measures the information recovered by this linear probe.”
4. **Correct the clustered p-value wording.** Say all 27 survive Bonferroni and all have p <= 0.001, rather than all p < 0.001.
5. **Finish the plain-prompt result.** Section 5.5 retains the “regenerate with the v4-era runs” placeholder.
6. **Update the draft-status box.** “Every number” coming from preregistered notebooks 23–25 is inconsistent with post-review notebook 29 and post-hoc analyses.
7. **Consolidate the response letter.** Its opening still identifies v0.9/9bcc1b8, and its earlier table still says equal ESG, a 0.09–0.11 control effect, and no insertion benefit. The appended v0.10 update does not remove those contradictions. The controlled CCR effects are approximately +0.110 without insertions and +0.041 with insertions; the +0.091 contrast changes both factors.

These corrections are mainly manuscript consistency work. They do not negate the reproduced internal effect.

## Remaining work that affects the editorial decision

**Highest priority: complete the reader study and validate the synthetic absence labels.** Report reader qualifications, uncertainty, residual findings and secondary signs, control preservation, and handling of “cannot tell”; rescore a clinically validated subset. The current 32-erasure sample cannot demonstrate a residual rate below 10% using a two-sided exact 95% interval even with zero failures, a limitation already acknowledged by the paper.

**Next: establish or qualify cross-source independence and baseline fairness.** Identifier disjointness is not a cross-dataset patient crosswalk. Model-specific instructions/settings and resolution sensitivity are still incomplete. A focused sensitivity analysis against the strongest relevant comparators is more valuable than indiscriminately adding models.

Complete reader consent/ethics documentation, Figure 2 provenance and licences, the AI-use declaration and unresolved bibliography items. Include the remaining referenced manifests where available, while preserving reader blinding.

Repairing pneumothorax detection is not required to report a carefully scoped methods study and its negative finding. The acceptance-critical issue is whether the claimed counterfactual improvement remains after reliable clinical label validation, appropriate cohort controls and credible comparison settings.

**Conclusion:** the computational evidence is now substantially stronger and reproducible from supplied records. The remaining major-revision recommendation is driven chiefly by reference-standard validity and unresolved scope/fairness questions, not by inability to trace the headline arithmetic.
