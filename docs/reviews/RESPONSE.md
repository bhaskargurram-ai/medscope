# Response to the independent review of MedScope

Current draft: v0.12 (5 November 2026), `paper/method_paper.pdf`. This letter replaces the earlier `RESPONSE_v09.md`.

Review rounds: v0.7 from the PDF alone (54/100); package `7b15d59` (64/100); package `d029d26` (67/100). The
third round rescored 134,309 outcome rows from the transcripts with the repository's own code and found zero
discrepancies, reproduced the 27 primary case-level comparisons, the selection rule, the patient-level bootstrap and
the encoder probe, and found no case or patient overlap between training, validation and the four evaluation
cohorts. The findings below are therefore about wording, scope and the reference standard, not arithmetic.

## 1. Audit package

`notebooks/30_audit_package.ipynb` builds `MyDrive/medscope/audit/medscope_audit_<commit>_<date>.zip`:
the repository at the commit, the full git log and the patch history of `docs/PREREGISTRATION_v4.md`, every
evaluation run's `summary.json`, `report.md`, `scored.jsonl`, `outcomes.jsonl` and `transcripts.jsonl`, the view
manifests of every split (case, patient or near-copy group, question, answer, lesion box), the cached encoder
features, and the reports of notebooks 23–29. Not included: adapters, image pixels (public datasets), the
reader-study answer key while readers are blinded, and the manifests of 22 runs the auditor listed (paraphrase,
SIIM full-resolution and v4.1 runs), which will be added to the next package.

## 2. Experiments added in response to the review (notebook 29)

| Review item | Experiment | Result | Where |
| --- | --- | --- | --- |
| F08 | 2×2 factorial at stage 1, single seed: random-removal control edits × lesion insertions | ESG 0.71–0.74 in all four arms, no pair significantly different. Control edits raise CCR by +0.110 without insertions and +0.041 with (p ≤ 0.018) and reduce denial of the intact lesion after a Telea edit elsewhere from 43% to 16–23% (p < 0.001). Insertions: no measurable benefit on the main test or held-out tools; higher net utility on the fresh external set (+0.144 [0.048, 0.240], p = 0.002) | Table 7, Section 5.3, limitations |
| F09 | Linear probe on the frozen encoder's output | random-removal vs original AUC 0.60 [0.58, 0.63] (ResNet-18 0.83); target vs random 0.86, which reflects the lesion and any anatomy-dependent trace | Section 5.4 |
| F10 | Every comparison rerun resampling patients or near-copy groups | Main test 507 cases from 416 groups; all 27 primary comparisons survive Bonferroni with p ≤ 0.001 (one at 0.001); one secondary comparison crosses 0.05 (fresh-external ESG vs Claude Opus 5.5, 0.037 → 0.060) | Sections 3.8, 5.5, 5.6 |
| F15 | Reader pack rebuilt with a control-edited arm: 128 images, 32 per kind, pack id in every answer file | Readers in progress | Section 7 |
| F18 | Pixel-level crosswalk (notebook 31): every unedited image of every split and cohort hashed, pairs within 8 bits confirmed by pixel correlation; two tiers (identical, near copy); id overlap per pair of sets | 6,849 images, no shared ids. One identical image: a validation lesion-free ChestX-Det image is the same NIH image as a fresh-external SIIM pneumothorax case (never in training; 1 of 316 cases; SIIM result unaffected). 1,834 near-tier pairs, all within the correlation range of pairs that cannot share a patient | Section 4.1, limitations; `results/crosswalk.md` |

## 3. Findings by ID

| ID | Status | What changed |
| --- | --- | --- |
| F01 | Fixed | ESG described as zero for policies that respond to both edits alike; anatomy-dependent traces acknowledged throughout; shortcut language is "reduces", not "closes" |
| F02 | Readers pending | Control arm added; pre-specified residual-finding criterion (10%) with exact CI; the paper states that 32 erased images can rule out gross failure only |
| F03 | Fixed | Open-model claim corrected: Qwen2.5-VL-7B claims fewer erased lesions, Qwen3-VL-8B not significantly more |
| F04 | Fixed | "No significant CCR difference; equivalence not established", CI to −0.09 |
| F05 | Fixed | Label-check sign reversal against gemini-4-argon disclosed with both p-values |
| F06 | Done | Audit package (Section 1 above) |
| F07 | Fixed | Chronology paragraph: main-test comparators predate v4; pre-registration is a versioned plan with same-day revisions before any data |
| F08 | Done | Factorial (above); insertions described as endpoint-dependent and interacting with the control edit |
| F09 | Done | Probe (above); the probe measures what this linear reader recovers, not an upper bound |
| F10 | Done | Patient-level bootstrap (above); wording "p ≤ 0.001" |
| F11 | Fixed | The 27-comparison family and Bonferroni check are stated to be a post-review check, not pre-specified; p-value formula and 0.001 floor given |
| F12 | Mostly | MedScope CIs in Table 4 and the text; denominators in the caption; per-model CIs in the released reports |
| F13 | Partly | "Generic plain prompt" with its limits; chat templates applied by each processor; model-specific instructions, settings and resolution not tuned (now a stated limitation); the plain-prompt placeholder removed and the per-model rates given |
| F14 | Not done | Resolution-matched API inputs not run |
| F15 | Done | Reader pack 2 |
| F16 | Fixed | Cost matrix described as an assumption |
| F17 | Fixed | Pneumothorax: "most plausible explanation", post-hoc, repair not demonstrated |
| F18 | Done | Identifier-level disjointness verified by the auditor; pixel-level crosswalk across all six sets run (notebook 31): one identical validation/fresh-external image, disclosed in Section 4.1; BraTS 2023 meningioma vs TCGA-LGG disjoint by cohort design; same-patient different-image overlap between SIIM-ACR and ChestX-Det stated as not excludable without NIH ids, and as a limitation that would bias the pneumothorax result optimistically if present |
| F19 | Fixed | He et al. (NAACL 2025) added; positioning against causal VQA sharpened |
| F20 | Mostly | QC criterion, prompt examples and main-test API cost filled; draft-status box corrected; AI-use declaration and reader ethics still bracketed |
| F21 | Fixed | "Comparator-model consensus panel, not a clinical reference standard" |
| F22 | Fixed | Fresh-external utility disadvantage in the abstract; fresh-internal CCR described as mixed; internal-test qualifier in the conclusion |
| F23 | Fixed | Abstract 250 words; highlights ≤ 85 characters |
| F24 | Fixed | Protected-image counts explained; per-type advantage limited to ESG and erased claims |
| F25 | Fixed | AURC removed from reported metrics |
| F26 | Fixed | Verbatim prompt and examples; MedScope's no-tag and malformed rates (0) |
| F27 | Mostly | Seven references corrected; TRIPOD-LLM and STARD-AI entries still marked verify |
| F28 | Fixed | "Without additional manual annotation" |
| F29 | Not done | Figure 2 case ids and licences for a supplement |
| F30 | Fixed | Data draw per arm clarified |
| F31 | Partly | Per-seed values in `results/v4_seeds_test.md`; paper gives mean ± sd |
| F32 | Fixed | Mask area vs bounding-box area |
| F33 | Not done | Naming polish |
| Audit 2.1 | Fixed | Section 8.1 no longer says insertions add nothing |
| Audit 2.2 | Fixed | Sections 5.3, 8.1, 8.3: "reduces" the shortcut |
| Audit 2.3 | Fixed | Section 5.4 probe wording |
| Audit 2.4 | Fixed | p ≤ 0.001 |
| Audit 2.5 | Fixed | Plain-prompt placeholder removed |
| Audit 2.6 | Fixed | Draft-status box |
| Audit 2.7 | Fixed | This letter |
| `neg_*` runs | Labelled | Historical October runs summarised on a 181-view negative set; not used in the paper; README says so |

## 4. Open

- Reader-study results, reader qualifications, consent and ethics statement (readers in progress; more than
  32 erased images would be needed to bound the residual rate below 10%).
- A focused comparator sensitivity analysis on instructions, settings and input resolution against the strongest
  comparators (F13, F14).
- Figure 2 provenance and licences (F29); generative-AI-use declaration; two references to verify (F20, F27).
- The 22 manifests missing from the package.
