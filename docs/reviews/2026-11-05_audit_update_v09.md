# MedScope v0.9: audit-package review update

Review date: 5 November 2026. Package: `medscope_audit_7b15d59_20261105.zip`. Snapshot identifier: `7b15d596b06ad62de6f1a975d8ba8793c6ee6d37` in the supplied history export. This is a computational and manuscript audit, not clinical adjudication or an independent repeat of training.

## Decision and revised score

**64/100; major revision before submission.** This replaces the 62/100 PDF-only assessment. The original v0.7 assessment was 54/100. The package materially resolves the concern that the headline results cannot be traced to outcome records. It does not resolve whether the synthetic absence labels are clinically valid.

The two-point increase from 62 is in reproducibility and transparency, from 3/5 to 4/5. Evidence validity remains 3/5 because full transcripts, image/view manifests, patient mappings and independent clinical validation remain unavailable. The score measures submission readiness under the previous rubric, not acceptance probability.

| Dimension | Weight | Score /5 | Weighted points |
|---|---:|---:|---:|
| Novelty and significance | 15 | 3 | 9 |
| Methodological soundness | 15 | 3 | 9 |
| Validity of evidence | 15 | 3 | 9 |
| Statistical analysis | 10 | 4 | 8 |
| Baselines and fairness | 10 | 3 | 6 |
| Clinical relevance and safety | 10 | 2 | 4 |
| Reproducibility and transparency | 10 | 4 | 8 |
| Honesty and limitations | 5 | 4 | 4 |
| Reporting quality and clarity | 5 | 4 | 4 |
| References, ethics, declarations | 5 | 3 | 3 |
| **Total** | **100** | | **64** |

## What was actually verified

- The ZIP contains 1,112 entries, approximately 113.4 MB uncompressed, including source code, notebooks, reports, outcome records, the manuscript and exported history.
- The archived manuscript PDF is byte-identical to the v0.9 PDF previously reviewed. Both have SHA-256 `843fc988381105742f4a21213681b9a584e7036a302bd67b25b706f6d34cb329`.
- Recomputed 5,048 available metric point estimates across 226 runs and 142,428 outcome rows using the supplied metric functions. Used `scored.jsonl` where available, otherwise `outcomes.jsonl`, matching the repository's fallback convention. No duplicate view IDs occurred within these checked runs.
- Found 16 metric-value mismatches and four count mismatches, all in four historical `neg_*` runs described below. The current v2 comparator and v4 run summaries passed this aggregation check.
- Recomputed all 27 main-test case-bootstrap comparisons against the nine frontier models using the supplied algorithm: ESG, erased-lesion claims and net utility, 2,000 resamples, seed 0. Every comparison had zero empirical sign-crossings, reproducing the repository's displayed `p < 0.001` convention. Confirmed common view identities for the paired main-test comparisons. This reproduces the calculation conditional on the recorded outcomes; it does not independently certify the labels or the bootstrap test's calibration.
- Recomputed the final model's main-test bootstrap summary: all 69 fields (23 metric estimates and their two confidence bounds) matched the stored summary exactly.
- Reapplied the selection rule to stored validation summaries: stage 3 is selected. Its utility 0.612695 exceeds stage 2 minus 0.02; its healthy-image claim rate 0.077273 is below stage 2 plus 0.02. It also clears the incumbent-v3 comparison.
- Checked all 54,267 rows in available `v4*/scored.jsonl` files: recorded reward equals the sum of recorded reward components in every row. This is an internal consistency check, not reconstruction of image grounding or clinical correctness.
- Ran 50 existing tests covering metrics, actions/rewards, real-output parsing examples and fairness: all passed after installing the missing OpenCV dependency in an isolated temporary dependency directory. No model training or API inference was performed.

### Headline values recovered from records

| Quantity | Recomputed value |
|---|---:|
| Main-test cases / views | 507 / 1,115 |
| Original correct answers | 186 / 219 |
| Control-edit correct answers | 186 / 219 |
| CCR | 372 / 438 = 0.849315 |
| Target-removal absent answers | 198 / 219 |
| Control-removal absent answers | 32 / 219 |
| ESG | (198 − 32) / 219 = 0.757991 |
| Erased-lesion claims | 21 / 219 = 9.589% |
| Healthy-image claims | 22 / 288 = 7.639% |
| Main-test utility | 0.732287 |
| Fresh-external utility | −0.053354 |
| SIIM positive original images answered correctly | 0 / 48 |

These findings warrant withdrawing the blanket description that the main empirical numbers are untraceable. They are now traceable to supplied derived outcome records.

## Remaining limits of this package

The audit README explicitly excludes full per-view transcripts and model adapters. The outcome records contain correctness/action fields rather than the complete original answer text. Therefore, aggregation can be reproduced, but every model response cannot be independently re-parsed or rejudged. Selected examples in reports do not replace the full transcript set.

The archive also contains no view-manifest JSONL files or frozen-encoder feature NPZ files found in the inventory. Consequently:

1. The patient-bootstrap report and implementation can be inspected, but the actual case-to-patient/near-copy-group mapping cannot be independently rerun. The reported 416 main-test groups and 230 fresh-external groups remain report-level evidence.
2. Cross-source patient independence and the historical train/validation/test exclusion rules cannot be verified on the actual manifest populations.
3. The encoder probe's AUC values match its stored JSON report, and the script uses case-paired bootstrapping, but its logistic regression and AUC cannot be reproduced without the features or source inputs.
4. No independent training/inference reproduction or image-level clinical validation has occurred.

The history export supports the claimed chronology: first registration commit `5727c94` on 1 November at 08:27:47 −0500; amendment commit `ed3bcef` at 20:29:35 −0500; manuscript commit `9bcc1b8` on 5 November. These are exported records, not a full Git object database or an independently timestamped registry. The patch history also records early changes to data/split rules after the first commit; describe the versioned plan and amendments rather than implying every final detail was already in the initial file.

## Findings requiring correction

### 1. Primary-family prespecification needs qualification

The supplied `docs/PREREGISTRATION_v4.md` and its patch history do not explicitly identify the 27-comparison primary family or the Bonferroni procedure. The paper can report that these 27 comparisons survive a post-review multiplicity check. Calling that exact family pre-specified requires a dated source that explicitly establishes it. The strong recomputed results do not depend on calling the adjustment prospective.

### 2. Historical summaries do not all match the packaged rows

`neg_sft_agentic`, `neg_sft_grounding`, `neg_base_medgemma15` and `neg_base_qwen35` report 181 views/cases, while their supplied outcomes contain 218 rows. Sixteen metric values also differ across three of those runs. For example, `neg_sft_agentic` utility is 0.277523 from the packaged rows versus 0.403315 in its summary.

These are historical runs, not discrepancies in the current main-test headline. They may reflect an earlier filtering universe; the archive does not supply the manifests needed to establish that. Label their cohort/filtering explicitly or regenerate compatible summaries. Do not silently overwrite historical provenance.

### 3. Earlier manuscript corrections still apply

- Control-edit CCR effects are approximately +0.110 without insertions and +0.041 with insertions. The response's +0.09–0.11 range mixes comparisons. The report's +0.091 contrast compares control-only against insertion-only and changes both factors.
- Insertions have mixed effects. The fresh-external utility benefit of +0.144 [0.048, 0.240] contradicts an unrestricted claim that they add nothing. Conversely, main-test CCR is lower with insertions when controls are present. Report this interaction and endpoint dependence.
- Qwen3-VL-8B's 12.8% erased-claim rate is greater than MedScope's 9.6%; only Qwen2.5-VL-7B has the lower point estimate among the two cited exceptions.
- Non-significant differences in the single-seed factorial do not establish equal ESG or equal training-run performance.
- Target-versus-control probe AUC 0.86 does not isolate lesion information from anatomy-dependent artifacts. A mean-pooled linear probe is not an upper bound on nonlinear artifact extraction.
- The metric code's ESG docstring still says an edit detector scores zero and only reading the lesion scores high. Update this obsolete universal claim to match the qualified manuscript.
- Native chat templates are already reported as applied by model processors. The outstanding fairness issue concerns model-appropriate instructions/settings and resolution sensitivity, not simply the existence of chat templates.

## What would change the recommendation

Highest priority is completed specialist validation of erased and control-edited images, with handling of residual findings, secondary signs and uncertain judgments, followed by rescoring on clinically valid cases. The current reader study correctly acknowledges that 0/32 residual findings still gives an approximately 10.9% two-sided exact upper confidence bound; it cannot establish a residual rate below 10%.

Next provide the missing transcripts and de-identified case/group and split manifests. Cached probe features would make that experiment reproducible without another GPU run. These additions do not require disclosing the reader-study answer key while readers remain blinded.

Resolve cross-source independence where possible and qualify external claims where it cannot be established. Complete targeted baseline sensitivity checks, reader ethics/consent documentation, figure provenance/licences, pending declarations and references.

A successful pneumothorax repair is not a prerequisite for a carefully scoped methods paper. The existing negative result is informative. The prerequisite is a credible demonstration that the counterfactual improvement survives valid reference labels and adequate comparator and cohort controls.

**Editorial conclusion:** the audit package confirms substantial numerical consistency and materially improves reproducibility. Major revision remains warranted because clinical reference-standard validity, rather than arithmetic traceability alone, is the main unresolved scientific issue.
