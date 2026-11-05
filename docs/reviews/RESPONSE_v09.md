# Response to the independent review of MedScope draft v0.7

Draft reviewed: v0.7 (4 November 2026), scored 54/100 from the PDF alone. Draft now: v0.9 (5 November 2026),
`paper/method_paper.pdf`, repository commit `9bcc1b8`.

## 1. What the review could not see

The review states that every empirical number was "untraceable" because the repository, Drive outputs and git
history were not available, and it scored Reproducibility (2/5) and Validity of evidence (3/5) on that basis.
All of it exists and is listed here so those rows can be re-scored.

| What | Where |
| --- | --- |
| Code, notebooks, pre-registration, results log | `https://github.com/bhaskargurram-ai/medscope` (access granted to the reviewer) |
| Pre-registration and its history | `docs/PREREGISTRATION_v4.md`; `git log -p docs/PREREGISTRATION_v4.md`. First commit `5727c94`, 1 Nov 2026 08:27 (before any v4 data); amendment 1 `ed3bcef`, 1 Nov 20:29 |
| Every run: metrics with bootstrap CIs, per-view transcripts, rescored outcomes | Drive `MyDrive/medscope/results/<run>/` (`summary.json`, `report.md`, `outcomes.jsonl`, `scored.jsonl`) |
| Reports behind each table | `results/24_v4_everywhere_report.md` (final model, every test), `25_v4_recipe_report.md` (seeds, ablations, MedGemma), `29_review_checks_report.md` (this response's new experiments) |
| Metric definitions, cost matrix, parser, bootstrap | `medscope/eval/metrics.py`, `configs/reward.yaml`, `medscope/eval/runner.py`, `medscope/eval/compare.py` |
| Quality control of the views | `medscope/data/quality.py` |
| Chronological log of every result | `docs/RESULTS_LOG.md` |
| The review itself | `docs/reviews/2026-11-04_independent_review_v07.md` |

The main-test frontier runs (31 October) predate the v4 pre-registration (1 November); the paper now says so
(Section 3.6, "Chronology") and says what was and was not known when the plan was committed.

## 2. New experiments run for this response (notebook 29)

| Review item | Experiment | Result | In the paper |
| --- | --- | --- | --- |
| F08 erasures-only arm removed two components at once | 2×2 factorial at stage 1: control edits × lesion insertions (two new arms, same steps and schedule as the others) | ESG equal in all four arms (0.71–0.74). Control edits raise CCR by 0.09–0.11 (p ≤ 0.018) and cut denial of the intact lesion after a Telea edit elsewhere from 43% to 16–23% (p < 0.001). Insertions add nothing on the main test or the held-out tools | Table 7, Section 5.3; limitation added: the pre-registered recipe carries an unneeded component |
| F09 frozen encoder does not rule out an edit detector | Linear probe on the frozen encoder's output (1,200 train / 438 test views) | random-removal vs original AUC 0.60 [0.58, 0.63] (ResNet-18: 0.83); lesion gone vs intact 0.86 | Section 5.4; the impossibility wording removed |
| F10 case bootstrap ignores repeated patients | Every comparison rerun with patients or near-copy groups resampled | Main test: 507 cases from 416 groups; intervals widen ≤ 0.01; all 27 primary comparisons stay p < 0.001; one secondary comparison crosses 0.05 (fresh-external ESG vs Claude Opus 5.5, 0.037 → 0.060) | Sections 3.8, 5.5, 5.6 |
| F15 reader study has no random-removal arm | Reader pack rebuilt and republished: 128 images, 32 per kind including control-edited; answer files carry a pack id | Readers in progress | Section 7 |

## 3. Finding-by-finding

| ID | Status | What changed (v0.9) |
| --- | --- | --- |
| F01 | Fixed | ESG claim restricted to policies that respond to both edits alike; anatomy-dependent traces acknowledged (abstract, highlights, Sections 1, 3.2, 5.4, Figure 1 caption) |
| F02 | Partly; readers pending | Reader study redesigned with a control arm and a pre-specified residual-finding criterion (10%, exact CI); reference-standard limitation stated |
| F03 | Fixed | "Better than all six open models on erased-lesion claims" removed; the two low-CCR open models and their p-values named |
| F04 | Fixed | "Matches" → "no significant difference; equivalence not established", with the CI reaching −0.09 (Sections 1, 5.1, 9) |
| F05 | Fixed | Label-check sentence corrected: the gemini-4-argon healthy-image comparison reverses sign (−0.014, p 0.59 → +0.023, p 0.31) and stays non-significant |
| F06 | Answered | Audit package listed in Section 1 of this note; commit hash given |
| F07 | Fixed | Chronology paragraph in Section 3.6 |
| F08 | Done | Factorial ablation (above) |
| F09 | Done | Probe (above); wording softened |
| F10 | Done | Patient-level bootstrap (above) |
| F11 | Fixed | Primary family of 27 comparisons named; Bonferroni threshold 0.0019 stated, all survive; p-value formula and 0.001 floor given (Section 3.8) |
| F12 | Mostly | Net-utility CI in Table 4; the other MedScope CIs in the text; denominators in the Table 4 caption. Per-row CIs for every model remain in the released reports |
| F13 | Partly | "Own/native prompt" renamed "generic plain prompt" and its limits stated; native-template runs not done |
| F14 | Not done | Resolution-matched API inputs not run; the full-resolution SIIM analysis (Section 6) is the only resolution check |
| F15 | Done | Reader pack 2 (above) |
| F16 | Fixed | Cost matrix described as an assumption, not elicited clinical utility (Section 3.4) |
| F17 | Fixed | Section 6 headings and text: "most plausible explanation", "consistent with", post-hoc; conclusion softened |
| F18 | Partly | Test-set protection and near-copy checks described (Section 4.1); a patient-level crosswalk between SIIM, ChestX-Det and ChestX-ray14 is not done |
| F19 | Fixed | He et al. (NAACL 2025) added and positioned against; causal-VQA comparison sharpened (Section 2) |
| F20 | Mostly | QC criterion filled from the code; prompt examples filled; main-test API cost given (US$132); AI-use declaration and reader-study ethics still bracketed |
| F21 | Fixed | "Independent panel" → "comparator-model consensus panel, not a clinical reference standard" |
| F22 | Fixed | Fresh-external net-utility disadvantage in the abstract; "flagships detect more" qualified for the fresh internal set; conclusion carries the internal-test qualifier |
| F23 | Fixed | Abstract 250 words; every highlight ≤ 85 characters |
| F24 | Fixed | Protected-image counts explained (near-copies); "advantage in every imaging type" limited to ESG and erased claims, SLAKE utility exception named |
| F25 | Fixed | AURC removed from the reported metrics (kept in released reports) |
| F26 | Fixed | Verbatim prompt with its two examples in Appendix A; MedScope's no-tag and malformed rates stated (0) |
| F27 | Mostly | Seven references corrected or completed (HuatuoGPT-Vision title, MedGemma 1.5 authors, WM-DOVA subtitle, BraTS-Africa title, BUS-UCLM, SIIM authors, Qwen3.5 model card); arXiv ids added; TRIPOD-LLM and STARD-AI entries still marked verify |
| F28 | Fixed | "Without additional manual annotation"; "reports only what it sees" kept in the title, qualified in the text |
| F29 | Not done | Figure 2 case ids and licences not yet in a supplement |
| F30 | Fixed | Data draw per arm clarified (Section 4.2) |
| F31 | Partly | Per-seed values are in `results/v4_seeds_test.md`; the paper gives mean ± sd |
| F32 | Fixed | Mask area vs bounding-box area distinguished (Section 6) |
| F33 | Not done | Naming polish |

## 4. Still open

- Reader-study results, reader details, consent statement (readers in progress).
- Native-template and resolution-matched runs for the open and API models (F13, F14).
- Patient-level crosswalk of SIIM / ChestX-Det / ChestX-ray14 and TCGA / BraTS (F18).
- Figure 2 case ids and dataset licences in a supplement (F29).
- Generative-AI-use declaration and the three references marked verify (F20, F27).

Request to the reviewer: re-score against v0.9 with the repository and the Drive results folder, and say which of
the open items above would change the recommendation.

## 5. Update after the audit of package `7b15d59` (v0.10)

The audit recomputed every main-test number, the 27 primary comparisons and the selection rule from the package and
withdrew "untraceable" (score 64/100). Changes made in response:

- Section 3.8: the 27-comparison family and the Bonferroni check are described as a post-review check, not as
  pre-specified; Section 3.6 describes the pre-registration as a versioned plan whose data and split rules were
  revised in commits on 1 November before any data was built.
- Section 5.1: Qwen3-VL-8B's 12.8% is above MedScope's 9.6%; the sentence now says so.
- Section 5.3 and limitations: insertions described as having endpoint-dependent, interacting effects (no benefit
  on the main test, a benefit on the fresh external set), not as "adding nothing"; the single-seed factorial no
  longer claims equal ESG.
- Section 5.4: the 0.86 probe AUC described as lesion plus any anatomy-dependent trace; a linear probe on pooled
  features stated to bound linear, not nonlinear, extraction.
- Limitations: comparator configuration (model-specific instructions, settings, input resolution not tuned).
- `medscope/eval/metrics.py`: the ESG docstring no longer claims an edit detector scores zero.
- Audit package (notebook 30): now includes every run's `transcripts.jsonl`, the view manifests of every split
  (patient and near-copy group ids), and the encoder probe's cached features; the README labels the four `neg_*`
  runs as historical (summarised on an earlier 181-view negative set, not used in the paper).
