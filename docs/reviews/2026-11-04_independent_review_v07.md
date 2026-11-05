# Independent manuscript review — MedScope, draft v0.7

**Review date:** 4 November 2026 (America/New_York). **Material reviewed:** the supplied 19-page `method_paper.pdf` and the attached review instructions. Manuscript title: *Seeing Is Not Believing: Counterfactual Lesion Erasure Teaches a Small Medical Vision–Language Agent to Report Only What the Image Shows*.

**Scope and evidence boundary.** This is a PDF-based audit and simulated editorial review, not a certification of the experiments and not an actual physician's assessment. The LaTeX, repository history, code, manifests, checkpoints, transcripts and Drive reports were not supplied. The manuscript's GitHub URL could not be retrieved through web search; an unauthenticated GitHub API request returned 404, which does not distinguish a private repository from an unavailable one. Searches for the named reports did not locate them. Google Drive was not available in this session. Consequently, every empirical number remains **untraceable to a stored result**, even where arithmetic or agreement between two manuscript passages is verified. Missing access is not evidence that a result is fabricated. No `.tex` line numbers are invented; locations below use printed PDF pages, sections and tables. All editorial judgments are conditional on these limitations.

The audit preceded the three role-specific reports. Calculations were executed in Python. Figure 2 was rendered and inspected. The final findings were checked again against the Discussion, which already acknowledges several important limitations.

## 1. Verdict at a glance

**Provisional submission-readiness score: 54/100. Recommendation: do not submit this draft yet; complete the reference-standard validation and audit package, then undertake major revision.** Under the supplied score anchors, this falls in “needs new work.” This is a score for the accessible draft, not an estimate of acceptance probability or a verdict that the underlying method cannot become publishable.

The useful contribution is a controlled counterfactual training recipe with explicit failure analysis. Its strongest result is the reported internal reduction in erased-finding claims, supported by several complementary ablations. The largest obstacle is that the benchmark assumes that removing an annotated region removes all clinically relevant evidence, while the manuscript itself demonstrates exceptions. The universal edit-detector claim is also stronger than the design establishes.

| Journal | Most likely decision on this draft | Reason (editorial assessment, not a prediction from acceptance data) |
|---|---|---|
| Computers in Biology and Medicine | Reject / invite substantial revision; major revision if sent out | Good applied scope, but unfinished reader validation, contradicted claims and an inaccessible audit package obstruct assessment. |
| Artificial Intelligence in Medicine | Reject | The methodological novelty needs a sharper distinction from causal VQA, and the clinical reference standard is unresolved. |
| IEEE Journal of Biomedical and Health Informatics | Reject | Broad technical evaluation is promising, but reproducibility, clustering, clinical meaning and baseline configuration need strengthening. |
| npj Digital Medicine | Reject, likely editorial | No completed human validation or demonstrated clinical benefit; synthetic benchmark gains alone do not establish impact in care. |
| Radiology: Artificial Intelligence | Reject / resubmit after new validation | Validity of erased images and modality-appropriate expert review are central; the study also spans non-radiological imaging. |
| Medical Image Analysis | Reject, likely editorial | A stronger methodological advance and a more rigorous demonstration against shortcut explanations are needed. |

**Top five must-fix items**

1. Correct the universal ESG/edit-detector theorem and frozen-encoder argument (F01, F09).
2. Validate target and control views with qualified readers, including residual disease and secondary signs; report adjudicated sensitivity analyses (F02, F15).
3. Repair concrete contradictions: open-model superiority, label-noise direction, main-test versus external accuracy language (F03–F05, F22).
4. Provide the complete immutable audit package and pre-registration chronology, distinguishing the old main test from the fresh tests (F06, F07, F18).
5. Reanalyse at the patient/group level where needed; provide effect CIs, multiplicity treatment, denominators and restrained null-result interpretation (F04, F10–F12).

**Handling editor's decision letter.** The manuscript addresses an important failure mode and reports a substantial internal benchmark effect. However, I cannot recommend publication in its present form. The benchmark's reference standard has not been independently validated, the proposed invariance to edit detection is overstated, and several statements conflict with the reported tables. The claimed equivalence in lesion accuracy is not established by non-significant superiority tests. Please complete the human validation, release a reviewable audit package, revise the statistical analysis and narrow the causal and generalisation claims. The explicit reporting of complete pneumothorax failure and the separation of post-hoc analysis are strengths and should be retained. A resubmission should be assessed on corrected, auditable evidence rather than on additional unvalidated headline comparisons.

## 2. Score card

Weighted points = score / 5 × weight. The weights sum to 100; the raw scores must not simply be multiplied by the weights without division by five.

| Dimension | Weight | Score / 5 | Weighted points |
|---|---:|---:|---:|
| Novelty and significance | 15 | 3 | 9 |
| Methodological soundness | 15 | 2 | 6 |
| Validity of evidence | 15 | 3 | 9 |
| Statistical analysis | 10 | 3 | 6 |
| Baselines and fairness | 10 | 3 | 6 |
| Clinical relevance and safety | 10 | 2 | 4 |
| Reproducibility and transparency | 10 | 2 | 4 |
| Honesty and limitations | 5 | 4 | 4 |
| Reporting quality and clarity | 5 | 3 | 3 |
| References, ethics, declarations | 5 | 3 | 3 |
| **Total** | **100** | | **54** |

**Novelty, 3/5.** Matched target/control edits combined with training, natural negatives and external tests are useful. Invariant/covariant editing already exists in causal VQA, explicitly acknowledged in §2. ESG is a difference in response rates, not by itself a new causal identification result (F01, F19). **One point higher:** demonstrate the incremental contribution of control matching in a factorial design and compare directly with prior counterfactual training approaches.

**Methods, 2/5.** Multiple ablations, held-out tools and natural negatives address plausible alternatives, but they cannot validate synthetic absence or exclude anatomy-dependent edit signatures. The erasures-only arm also removes insertions (F02, F08, F09, F15). **One point higher:** complete adjudication and isolate the control-edit factor while holding insertion exposure and training effort fixed.

**Evidence, 3/5.** The reported external and fresh tests are a real design strength; the paper does not conceal worse external sensitivity. However, the provenance cannot be audited, fresh external utility is mixed, and the main test predates v4 registration (F06, F07, F18, F22). **One point higher:** provide timestamped artifacts and valid patient-independent external evidence with adjudicated labels.

**Statistics, 3/5.** Paired case bootstrap and CIs for differences are sensible on paper, and the Fisher calculations reproduce. Case resampling may miss patient dependence, non-significance is overinterpreted, and uncertainty is incomplete (F04, F10–F12, F25). **One point higher:** patient/group bootstrap, complete CIs, a clear testing family, and equivalence claims removed or tested with justified margins.

**Baselines, 3/5.** Nine API and six open models plus cautious/few-shot/reasoning conditions are substantial. Identical prompts do not establish equal suitability, and “own prompt” is actually a shared generic prompt; output fallback rates and resolution sensitivity are missing (F13, F14). **One point higher:** fully specify provider settings and compare validated native templates and resolution/format sensitivity.

**Clinical relevance, 2/5.** Targeted finding presence is a meaningful component task, but not a validated diagnostic workflow. A critical finding is missed in every evaluated positive SIIM case, and reader validation is unfinished (F02, F15–F17). **One point higher:** complete qualified reference-standard review and define a narrow research use with per-finding sensitivity reporting; deployment claims would need substantially more.

**Reproducibility, 2/5.** The manuscript describes a reproducibility plan and named artifacts, but none of the run-level evidence was available for this review, and methods contain literal placeholders (F06, F18, F20). **One point higher:** a reviewer-accessible immutable release reproducing all tables and parser checks.

**Honesty, 4/5.** The abstract, failure-analysis section and Discussion prominently report pneumothorax failure and worse external perception. This deserves credit. Absolute causal phrasing, an unrestricted conclusion about matching frontier models and omitted abstract utility harm prevent full marks (F04, F17, F22). **One point higher:** align all prominent claims with the strongest defensible interpretation.

**Reporting, 3/5.** The central idea is understandable early, tables are extensive, and the failure section is unusually informative. The abstract is approximately 338 whitespace-delimited words after joining line-break hyphenation; all five highlights exceed 85 characters. Important definitions and fields remain incomplete (F05, F20, F23–F26). **One point higher:** complete the methods and declarations, shorten the front matter and supply item-level checklists.

**References/ethics, 3/5.** Many cited works exist, and some flagged entries can be resolved. Several titles are incomplete, the model-card reference is not immutable, and reader ethics/AI-writing declarations are pending (F19, F20, F27). **One point higher:** verify the entire bibliography against publisher records, document licences and complete the appropriate ethics determination before reader recruitment.

## 3. Findings register

Severity describes submission impact. An inaccessible artifact is called **unverified**, not wrong. Quotations are from the supplied manuscript; section/page references are the evidence unless an external source is explicitly linked.

| ID | Severity | Category | Location | Finding | Evidence | Fix | Effort |
|---|---|---|---|---|---|---|---|
| F01 | critical | claim | Abstract; highlights; §§1, 3.2, 5.4; pp.1–4,11 | ESG is not zero for every possible edit-based strategy. | §3.7 is a difference of conditional probabilities; §5.4 itself reports erased-vs-original detectability 0.70–0.75 versus random-vs-original 0.52–0.55. Same tool/shape does not imply identical artifact distributions. | Restrict the theorem to text-only policies on identical paired questions and policies depending only on an identical binary edit flag. Test anatomy/location-dependent artifact classifiers. | 1 day wording; days experiments |
| F02 | critical | data | §§3.2–3.3, 7, 8.5; Fig.2; pp.4–5,14–15 | Synthetic “absent” labels lack independent clinical validation. | §8.5 explicitly concedes a second unmasked lesion makes the expected absent answer wrong, and residual oedema/mass effect can persist; §7 results pending. | Validate absence of the asked finding and preservation of control evidence, with blinded specialist adjudication; re-score a validated subset and report exclusions. | Weeks |
| F03 | critical | number | §5.1; Table 4; pp.8–9 | The all-open-model erased-claim superiority statement is contradicted by the table. | Text: “better than all nine frontier and all six open models on ESG, erased-lesion claims and net utility”; MedScope erased 9.6%, Qwen2.5-VL-7B 5.5%, CCR 0.144. | State superiority in ESG/utility separately; lowest erased-claim rate among frontier comparators, with the low-CCR open baseline exception. Do not claim erased-rate superiority over all six. | Hours |
| F04 | major | statistics | Abstract; §§1, 5.1, 9; Table 5 | Non-significance is used to imply matching accuracy. | “matches nine frontier models on real lesions”; CCR CIs include clinically meaningful losses, e.g. −0.039 [−0.088,0.010] versus gpt-6.1-sol. | “On the internal test, CCR differences were not statistically significant; equivalence was not established.” Noninferiority needs an independently justified margin and appropriate analysis. | Hours; new design if equivalence retained |
| F05 | major | number | §5.5 label noise; Table 5; p.12 | “every comparison ... keeps its direction and significance” is false for the reported Gemini healthy-claim direction. | Before exclusion: 7.6% vs 9.0% (MedScope lower); after: 6.9% vs 4.6% (MedScope higher). | Explicitly disclose the reversal and supply the new paired CI/p-value; significance cannot be reconstructed from marginal percentages. | Hours |
| F06 | major | reporting | §3.6; Appendix B; Declarations | Stored-result traceability and code consistency cannot be certified. | PDF supplied without `.tex`, code, outputs or history; repository access failed/404. | Provide a reviewable archive with commit hash, manifests, logs and table-generation script; keep all empirical figures unverified until then. | Hours–days |
| F07 | major | method | §§3.6, 4.2; pp.6,8 | Registration chronology needs narrower claims. | Frontier main-test runs dated 31 Oct; registration dated 1 Nov; amendment 1 occurs after stage-1 validation. | Separate prior benchmark exposure from prospective v4 selection and fresh-test confirmation; disclose amendment commits, what had been seen, and checkpoint/test timestamps. | Day with records |
| F08 | major | method | §§4.2, 5.3; Tables 7–8 | Erasures-only comparison does not isolate the random-control factor. | Arm removes both “edits elsewhere” and “insertions.” | Factorial control-edit × insertion study, matched effective examples/updates; otherwise describe the combined intervention. | Days |
| F09 | major | claim | §5.4; p.11 | Frozen vision encoder does not rule out an edit detector. | Trainable language adapter can exploit artifact features already present in frozen embeddings. | Remove the impossibility argument; test a probe on frozen embeddings and report residual artifact predictability. | Hours; days experiment |
| F10 | major | statistics | §3.8; Tables 2–3 | Case bootstrap may ignore repeated patients/slices/frames. | Cases are images; BUS-UCLM source has 683 images from 38 patients, while this paper evaluates 99 images. Patient disjointness between splits does not ensure independence within a split. [Source](https://www.nature.com/articles/s41597-025-04562-3). | Report unique patients/groups and bootstrap paired predictions by patient/group, retaining all their views and images. | Days |
| F11 | major | statistics | §3.8; Tables 5,8–10 | Prespecification does not remove multiplicity; p-value implementation/resolution unclear. | No adjustment; 3 primary endpoints × 9 frontier models = 27 comparisons; secondary claims include p≤0.049. | Identify families; show Holm-adjusted primary results and label secondary exploration; report bootstrap tail formula and exceedance counts. | Day |
| F12 | major | reporting | Tables 4,6–13; §§3.7–3.8 | Point estimates often omit CIs and eligible denominators. | Table 4 literally has “[CI]”; 507 cases includes only 219 masked cases and 288 natural negatives. | Give numerator/denominator and cluster-aware CI per metric; distinguish O/R views from patients and source-case totals. | Days |
| F13 | major | method | §§3.9,4.2,5.5; Appendix A | Fairness checks are incomplete and “own/native prompt” is misleading. | Appendix A supplies one generic plain prompt for all open models; §5.5 own-prompt result is marked for regeneration. | Document each model's actual chat template/processor, decoding, token budget and parser failure rates; finish native-prompt sensitivity runs. | Days |
| F14 | major | method | §§3.9,6; Table 13 | Resolution and provider-default differences remain material. | APIs capped at 768 pixels; fresh SIIM uses 256-pixel copies; stage-1 detections improve at full resolution. | Retain the same image subset and compare matched high-resolution input settings, recording provider image-detail mode and tool outputs. | Days |
| F15 | major | method | §7; p.14 | Planned reader study does not validate the random-removal control and lacks readers/precision targets. | 32 original +32 erased +32 negative; no random-removal arm; number/specialty/experience blank. | Add control images, specialist coverage, cannot-tell handling, adjudication and case/reader uncertainty; choose sample size for a prespecified acceptable residual-finding rate. | Weeks |
| F16 | major | method | Table 1; §§3.4,5.5 | “Clinical” net utility is an assumed reward, not validated patient benefit. | Arbitrary asymmetric rewards, grounding bonus and first-tool-free rule; always-refer earns +0.110. | Call it benchmark reward; elicit clinically grounded costs or show separate sensitivity/specificity and decision analyses over clinically justified tradeoffs. | Hours–weeks |
| F17 | major | claim | §6; Abstract; p.13–14 | Coverage is a plausible explanation, not an experimentally identified exclusive cause. | “Resolution is not the cause”; “Counterfactual training is not the cause”; “Training coverage is.” No controlled coverage-repair experiment, and later paragraph concedes other mechanisms. | Describe evidence as consistent with low positive coverage and stage-3 suppression; if causal wording retained, use a registered coverage-repair experiment and a new locked test. | Hours or weeks |
| F18 | major | data | §§3.3,4.1; Tables 2–3 | Cross-source leakage and “external centre” provenance are not demonstrated by the PDF. | ChestX-Det origin disclosed; SIIM/NIH and TCGA/BraTS crosswalks absent; near-copy thresholds absent. | Supply source/patient provenance and overlap matrix across replay, all historical splits, few-shot images and evaluation sets; classify external datasets by actual acquisition independence. | Days |
| F19 | major | reference | §§1–2,8.3; refs 9–17 | Novelty and descriptions of prior counterfactual work need closer comparison. | Causal VQA already includes invariant/covariant edits; [He et al., NAACL2025](https://aclanthology.org/2025.naacl-long.349/) removes objects and trains mitigation, but is absent from the bibliography. | Compare mechanisms, supervision, matching and failure cases individually; add directly relevant text-reliance work and reporting guidance. | Days |
| F20 | major | reporting | §§3.3,4.3,5.5,7; Declarations | Submission-critical placeholders remain. | QC criterion, API cost, own-prompt regeneration, reader results/ethics/credit, AI-writing declaration incomplete. | Populate from records or explicitly remove unsupported analyses; do not invent an ethics determination or costs. | Hours–weeks |
| F21 | major | claim | §5.5; p.12 | Model-panel sensitivity analysis is not independent clinical ground truth. | Nine comparator models vote to identify disputed labels; same family of outcomes is evaluated after exclusion. | Call it a model-consensus sensitivity analysis; retain original cohort and obtain independent adjudication. | Hours–weeks |
| F22 | major | claim | Abstract; §§5.6,8.1,9 | Scope of generalisation is broader in some sentences than tables support. | Fresh internal CCR 0.681 exceeds Gemini 0.639 and Opus 0.653; fresh external ESG 0.393 is below Gemini 0.435. Conclusion omits internal qualifier for “matches.” | Describe source/test-specific patterns; add fresh external utility disadvantage to abstract; avoid “flagships detect more” as a universal statement across all new sets. | Hours |
| F23 | minor | reporting | Abstract; Highlights | Front matter is too long for commonly listed CBM limits; current official page could not be read. | Python count ≈338 words; highlight character counts 101,94,113,127,94. Archived guide lists 250 words/85 characters. | Shorten to ≤250 words and each highlight ≤85 characters, then confirm against live journal instructions. | Hours |
| F24 | minor | number | §§4.1,5.2; Tables 2,6 | Counts/prose need reconciliation and metric qualification. | Protected ChestX-Det 93 vs test 91, TCGA 79 vs78; SLAKE utility 0.22 vs Gemini0.38/Opus0.32 despite “advantage ... every imaging type.” | Explain protected-universe exclusions; specify ESG/erased-claim advantage rather than all metrics. | Hours |
| F25 | minor | statistics | §3.7; Results | AURC is introduced without a reported result; token confidence is not calibration. | No AURC table/curve found; §6 confidently wrong answers. | Supply risk-coverage curves with a defined error event, tied-score rules and confidence availability; add calibration analysis if claimed, or remove unused metric. | Day |
| F26 | minor | reporting | Appendix A; §§3.1,3.9 | Exact prompt and fallback reporting incomplete. | “[two examples: a zoom turn and a final answer]” is a placeholder; no-action-tag rate is promised but not tabulated. | Include verbatim prompts and examples plus per-model parse/fallback/malformed/refer/clarify frequencies. | Hours |
| F27 | minor | reference | References pp.16–18 | Bibliography includes shortened titles and unfinished metadata. | Ref2 prepends HuatuoGPT-Vision; ref40 omits subtitle; ref44 shortens title; ref31 “[verify]”. | Use verified entries in §6; resolve remaining records without treating a failed search as proof of nonexistence. | Day |
| F28 | minor | language | Title; §§1,3.2,9 | “Only what the image shows” and “without human annotation” overstate reliability and annotation independence. | Nonzero 9.6% erased claims; training starts from expert masks and dataset labels. | “Reduces unsupported finding claims”; “without additional manual annotation of generated views.” | Hours |
| F29 | minor | reporting | Fig.2; p.5 | Render shows source labels but does not establish image provenance or de-identification. | No obvious patient name visible at inspected scale; colonoscopy overlays and image identifiers require source-level review. | Add exact public case IDs/licences in supplement and inspect full-resolution pixels/metadata; do not certify PHI absence from the thumbnail. | Hours |
| F30 | minor | method | §§3.5,4.2; Table 7 | “same 16,000-view draw” is ambiguous across arms excluding entire view kinds. | Identical draw cannot literally contain the same allowed views in all arms without replacement/reweighting. | Publish case IDs, view-kind counts, repeat weights, effective examples and update counts per arm. | Day |
| F31 | minor | statistics | Table 7; §5.3 | Three-seed mean±SD is descriptive, not strong evidence about training-run variability. | Only aggregate seed summaries and paired-case p-values supplied. | Publish each seed; distinguish case uncertainty from seed variability; use additional seeds for unstable arms if feasible. | Hours–days |
| F32 | minor | reporting | §§3.2,4.1,6 | Dataset eligibility terms are ambiguous. | Diffuse chest findings described as excluded; QaTa diffuse disease evaluated; lesion mask-area cap20% versus pneumothorax median box area37%. | Specify which splits exclusions apply to and distinguish mask area from bounding-box area. These are not demonstrated numerical contradictions. | Hours |
| F33 | nit | language | Table3; Appendix A; throughout | Labels/abbreviations and names need polish. | “five imaging types” mixes modality and body region; Table5 abbreviates Gemini; AURC not expanded in metric sentence. | Use “five source groups spanning CT/MRI, radiography, ultrasound and endoscopy”; define acronyms and use a model-name key. | Hours |

## 4. Number trace

### 4.1 Recomputed checks and conflicts

“Match” in this subsection means **internal arithmetic match**, not a match to an unavailable experiment. All p-values except the two Fisher tests below require transcripts/resampling output. Means and SDs cannot be independently reconstructed without individual seeds.

| Location | Printed value / claim | Recalculation from PDF | Verdict |
|---|---|---|---|
| Table2 | 219 masked, 288 negative, 507 total | 17+83+41+42+36=219; 90+91+50+15+42=288; sum507 | Match, internal |
| Table2; §5.1 | 1,115 views, 170 degraded | 3×219+288+170=1,115 | Match; implies only170/219 cases have degraded views—explain filtering |
| Table3 external |169 |40+20+45+64=169 | Match |
| Table3 fresh external |316 |82+99+96+39=316 | Match |
| Table3 standard VQA |1,051 |451+300+300=1,051 | Match |
| Figure3 |55,54,55,55 |Sum219 | Match |
| §5.4 clean split |61+158 |219 | Match |
| §5.5 disputed labels |26/288;12+11+2+1 |9.0278%; sum26 | Match |
| Table4 frontier ranges |ESG0.27–0.47; erased41–62% |0.269–0.470;41.1–61.6% | Rounding difference, appropriate |
| Contributions/conclusion |four to six times less often |41.1/9.6=4.28125;61.6/9.6=6.41667 | Coarse rounded ratio; write rates or4.3–6.4-fold lower rate |
| §5.1 all open erased-rate superiority |9.6% versus all six lower |Qwen2.5-VL-7B=5.5% | Mismatch, F03 |
| Table5 vsTable4 net utility Gemini |+0.168 vs0.732−0.565 |+0.167 from rounded cells | Rounding-compatible difference; raw numbers required |
| Table5 several differences |e.g.CCR+0.021 vs0.849−0.829=0.020 |At most displayed rounding can explain0.001 discrepancies | Rounding-compatible, not confirmed rounding without raw figures |
| §5.3 absent-share arm |+0.521 |0.735−0.215=0.520 | Rounding-compatible |
| §5.3 seed deltas |+0.525,+0.539,+0.324 |Mean0.462667; displayed means0.741−0.279=0.462 | Rounding-compatible; cannot recover SDs |
| §5.5 always-refer |+0.110 |(438×−0.3+507×0.5+170×0)/1,115=0.1095067 | Match rounded |
| §5.5 referral on absent paid0 |−0.118 |438×−0.3/1,115=−0.1178475 | Match rounded |
| §5.5 all referral costs−0.3 |−0.300 |Constant reward−0.3 | Match |
| §5.5 utility excluding degraded |0.774 |(1,115×0.732−170×0.5)/945=0.7737354 | Match rounded, assuming no extra tool cost on degraded |
| §5.5 label exclusion |all directions maintained |7.6−9.0=−1.4pp;6.9−4.6=+2.3pp | Mismatch, F05 |
| §5.6 fresh external utility gap |−0.363 |−0.053−0.310=−0.363 | Match, CI untraceable |
| §6 Fisher test |35/42 vs28/48;p=0.012 |Two-sided Fisher0.01176564286 | Match rounded, independent-count assumption only |
| §6 Fisher test |38/42 vs23/48;p<0.001 |Two-sided Fisher0.00001346505 | Match |
| Abstract |338 words by extraction |Whitespace count after joining wrapped hyphenation, including headings | Reporting count; original `.tex` needed for definitive journal count |
| Highlights |five bullets |Character counts101,94,113,127,94 after joining wraps | All exceed85 |

Other consistency checks: MedScope strict ESG=ESG is consistent with the statement that it never refers, but its absence of referrals is unverified. The main ESG is consistent with 1−0.096−0.146=0.758 if no other terminal actions alter the complement. A displayed fraction is not enough to infer an exact count or prove the parser used that complement.

### 4.2 Complete extracted numerical-occurrence ledger

The ledger below preserves each numeric token and its surrounding PDF line, including repeated claims, table cells, references, model/version identifiers, dates, and equation constants. Tokens in citation/section/model identifiers are retained for completeness rather than misclassified as experimental measurements. Context is the discriminator. PDF page/line denotes the `pdftotext -layout` page and line within that page; it is **not a LaTeX line**. Signs, inequality symbols and units are in the context. Superscript scientific notation may be split by extraction; the full line is authoritative. The bibliography is also audited independently in §6. Source-file/line is unavailable for every experimental occurrence. The verified internal computations above do not change that provenance verdict.

**1760 extracted numeric/number-word occurrences.**

| ID | PDF location | Printed token | Context | Stored source file:line | Verdict |
|---|---|---|---|---|---|
|N0001|p.1,L7|7|Manuscript draft v0.7, 4 November 2026|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0002|p.1,L7|4|Manuscript draft v0.7, 4 November 2026|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0003|p.1,L7|2026|Manuscript draft v0.7, 4 November 2026|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0004|p.1,L13|23|Draft for expert review. Every number comes from the pre-registered v4 runs (notebooks 23–25) and is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0005|p.1,L13|25|Draft for expert review. Every number comes from the pre-registered v4 runs (notebooks 23–25) and is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0006|p.1,L14|7|regenerated from stored per-view transcripts. Items in orange brackets are open: the reader study (Section 7),|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0007|p.1,L26|zero|the rate of “absent” answers after erasure minus the rate after the control edit; it is zero for any model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0008|p.1,L27|4B|that ignores the image or only detects edits. MedScope-4B, Qwen3.5-4B with LoRA and zoom and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0009|p.1,L27|5|that ignores the image or only detects edits. MedScope-4B, Qwen3.5-4B with LoRA and zoom and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0010|p.1,L27|4B|that ignores the image or only detects edits. MedScope-4B, Qwen3.5-4B with LoRA and zoom and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0011|p.1,L28|three|windowing tools, was trained in three stages on label-derived trajectories. Data, recipe and model-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0012|p.1,L29|nine|selection rule were pre-registered; the selected model was tested once against nine frontier and six open|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0013|p.1,L29|six|selection rule were pre-registered; the selected model was tested once against nine frontier and six open|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0014|p.1,L31|507|Results. On 507 internal test cases across five imaging types, MedScope-4B reached ESG 0.758 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0015|p.1,L31|five|Results. On 507 internal test cases across five imaging types, MedScope-4B reached ESG 0.758 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0016|p.1,L31|4B|Results. On 507 internal test cases across five imaging types, MedScope-4B reached ESG 0.758 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0017|p.1,L31|0.758|Results. On 507 internal test cases across five imaging types, MedScope-4B reached ESG 0.758 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0018|p.1,L32|9.6%|claimed an erased lesion in 9.6% of cases, against ESG 0.27–0.47 and 41–62% for the frontier models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0019|p.1,L32|0.27|claimed an erased lesion in 9.6% of cases, against ESG 0.27–0.47 and 41–62% for the frontier models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0020|p.1,L32|0.47|claimed an erased lesion in 9.6% of cases, against ESG 0.27–0.47 and 41–62% for the frontier models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0021|p.1,L32|41|claimed an erased lesion in 9.6% of cases, against ESG 0.27–0.47 and 41–62% for the frontier models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0022|p.1,L32|62%|claimed an erased lesion in 9.6% of cases, against ESG 0.27–0.47 and 41–62% for the frontier models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0023|p.1,L33|0.001|(all p &lt; 0.001). Accuracy on real lesions did not differ from any frontier model, and false findings on|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0024|p.1,L34|7.6%|unedited healthy images (7.6%) were lower than for eight of nine. Removing only the counterfactual|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0025|p.1,L34|eight|unedited healthy images (7.6%) were lower than for eight of nine. Removing only the counterfactual|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0026|p.1,L34|nine|unedited healthy images (7.6%) were lower than for eight of nine. Removing only the counterfactual|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0027|p.1,L35|0.741|views lowered ESG from 0.741 ± 0.019 to 0.279 ± 0.107 over three seeds and raised erased-lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0028|p.1,L35|0.019|views lowered ESG from 0.741 ± 0.019 to 0.279 ± 0.107 over three seeds and raised erased-lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0029|p.1,L35|0.279|views lowered ESG from 0.741 ± 0.019 to 0.279 ± 0.107 over three seeds and raised erased-lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0030|p.1,L35|0.107|views lowered ESG from 0.741 ± 0.019 to 0.279 ± 0.107 over three seeds and raised erased-lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0031|p.1,L35|three|views lowered ESG from 0.741 ± 0.019 to 0.279 ± 0.107 over three seeds and raised erased-lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0032|p.1,L36|13%|claims from 13% to 68%; the effect replicated on MedGemma 1.5 4B and on two inpainting tools never|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0033|p.1,L36|68%|claims from 13% to 68%; the effect replicated on MedGemma 1.5 4B and on two inpainting tools never|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0034|p.1,L36|1.5|claims from 13% to 68%; the effect replicated on MedGemma 1.5 4B and on two inpainting tools never|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0035|p.1,L36|4B|claims from 13% to 68%; the effect replicated on MedGemma 1.5 4B and on two inpainting tools never|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0036|p.1,L36|two|claims from 13% to 68%; the effect replicated on MedGemma 1.5 4B and on two inpainting tools never|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0037|p.1,L37|four|used in training. At four external centres the ESG advantage held (0.597 vs 0.28–0.41), but frontier|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0038|p.1,L37|0.597|used in training. At four external centres the ESG advantage held (0.597 vs 0.28–0.41), but frontier|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0039|p.1,L37|0.28|used in training. At four external centres the ESG advantage held (0.597 vs 0.28–0.41), but frontier|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0040|p.1,L37|0.41|used in training. At four external centres the ESG advantage held (0.597 vs 0.28–0.41), but frontier|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0041|p.1,L39|4B|4B missed every pneumothorax; diagnosis traced this to a training coverage gap amplified by the final|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0042|p.2,L4|zero|• The evidence sensitivity gap is zero for every image-blind strategy, including edit detection.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0043|p.2,L5|4B|• A 4B agent trained only from dataset labels claims erased lesions in 9.6% of cases; nine frontier models,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0044|p.2,L5|9.6%|• A 4B agent trained only from dataset labels claims erased lesions in 9.6% of cases; nine frontier models,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0045|p.2,L5|nine|• A 4B agent trained only from dataset labels claims erased lesions in 9.6% of cases; nine frontier models,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0046|p.2,L6|41|41–62%.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0047|p.2,L6|62%|41–62%.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0048|p.2,L7|68%|• Without the counterfactual views, erased-lesion claims rise to 68% (three seeds); the effect replicates on a|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0049|p.2,L7|three|• Without the counterfactual views, erased-lesion claims rise to 68% (three seeds); the effect replicates on a|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0050|p.2,L13|1|1 Introduction|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0051|p.2,L14|one|A radiologist asked “Is there a polyp?” looks for one. A vision–language model asked the same question|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0052|p.2,L15|one|may answer “Yes, a sessile polyp is visible” whether or not the image contains one. In the image–text data|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0053|p.2,L19|1|Medical VLMs are now built by instruction-tuning general models on biomedical data [1, 2, 3, 4,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0054|p.2,L19|2|Medical VLMs are now built by instruction-tuning general models on biomedical data [1, 2, 3, 4,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0055|p.2,L19|3|Medical VLMs are now built by instruction-tuning general models on biomedical data [1, 2, 3, 4,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0056|p.2,L19|4|Medical VLMs are now built by instruction-tuning general models on biomedical data [1, 2, 3, 4,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0057|p.2,L20|5|5] and are evaluated mainly on VQA-RAD, SLAKE and PathVQA [6, 7, 8]. In these benchmarks the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0058|p.2,L20|6|5] and are evaluated mainly on VQA-RAD, SLAKE and PathVQA [6, 7, 8]. In these benchmarks the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0059|p.2,L20|7|5] and are evaluated mainly on VQA-RAD, SLAKE and PathVQA [6, 7, 8]. In these benchmarks the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0060|p.2,L20|8|5] and are evaluated mainly on VQA-RAD, SLAKE and PathVQA [6, 7, 8]. In these benchmarks the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0061|p.2,L22|9|Hallucination benchmarks [9, 10, 11, 12, 13] probe absent findings, but they change the question or the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0062|p.2,L22|10|Hallucination benchmarks [9, 10, 11, 12, 13] probe absent findings, but they change the question or the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0063|p.2,L22|11|Hallucination benchmarks [9, 10, 11, 12, 13] probe absent findings, but they change the question or the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0064|p.2,L22|12|Hallucination benchmarks [9, 10, 11, 12, 13] probe absent findings, but they change the question or the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0065|p.2,L22|13|Hallucination benchmarks [9, 10, 11, 12, 13] probe absent findings, but they change the question or the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0066|p.2,L28|14|with learned inpainting [14]. The obvious confound is that a model could learn to detect that an image was|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0067|p.2,L31|two|model that reads the lesion can treat the two differently.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0068|p.2,L32|twice|We use these views twice: to measure evidence sensitivity, and to train it. A 4-billion-parameter agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0069|p.2,L32|4|We use these views twice: to measure evidence sensitivity, and to train it. A 4-billion-parameter agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0070|p.2,L34|nine|by a rule committed before any of its data existed, and tested once against nine frontier and six open models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0071|p.2,L34|six|by a rule committed before any of its data existed, and tested once against nine frontier and six open models|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0072|p.2,L38|1|1. Counterfactual evidence views with an edit-matched control, built and quality-checked automatically|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0073|p.2,L39|five|across five imaging types, with no human annotation (Section 3.2).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0074|p.2,L39|3.2|across five imaging types, with no human annotation (Section 3.2).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0075|p.2,L40|2|2. The evidence sensitivity gap (ESG), zero for every image-blind strategy (always yes, always no, always|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0076|p.2,L40|zero|2. The evidence sensitivity gap (ESG), zero for every image-blind strategy (always yes, always no, always|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0077|p.2,L42|3.7|grounding, and a clinical cost-matrix utility (Section 3.7).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0078|p.2,L43|3|3. MedScope-4B, selected by a pre-registered rule, which claims erased findings four to six times less|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0079|p.2,L43|4B|3. MedScope-4B, selected by a pre-registered rule, which claims erased findings four to six times less|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0080|p.2,L43|four|3. MedScope-4B, selected by a pre-registered rule, which claims erased findings four to six times less|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0081|p.2,L43|six|3. MedScope-4B, selected by a pre-registered rule, which claims erased findings four to six times less|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0082|p.2,L44|nine|often than nine frontier models while matching their accuracy on real lesions, robustly to prompting,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0083|p.2,L45|5.1|question wording and unseen inpainting tools (Sections 5.1–5.5).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0084|p.2,L45|5.5|question wording and unseen inpainting tools (Sections 5.1–5.5).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0085|p.2,L46|4|4. Causal evidence on what produces the behaviour: a three-seed ablation of the counterfactual views,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0086|p.2,L46|three|4. Causal evidence on what produces the behaviour: a three-seed ablation of the counterfactual views,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0087|p.2,L48|5.3|(Section 5.3).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0088|p.2,L49|5|5. A transparent account of failure: at new centres frontier models detect more real lesions, and a confir-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0089|p.2,L51|5.6|(Sections 5.6, 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0090|p.2,L51|6|(Sections 5.6, 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0091|p.3,L1|2|2 Related work|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0092|p.3,L3|1|VLMs on biomedical image–text data: LLaVA-Med [1], HuatuoGPT-Vision [2], MedGemma [3, 4] and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0093|p.3,L3|2|VLMs on biomedical image–text data: LLaVA-Med [1], HuatuoGPT-Vision [2], MedGemma [3, 4] and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0094|p.3,L3|3|VLMs on biomedical image–text data: LLaVA-Med [1], HuatuoGPT-Vision [2], MedGemma [3, 4] and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0095|p.3,L3|4|VLMs on biomedical image–text data: LLaVA-Med [1], HuatuoGPT-Vision [2], MedGemma [3, 4] and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0096|p.3,L4|5|Lingshu [5]. They are evaluated mostly on VQA-RAD [6], SLAKE [7] and PathVQA [8], where the asked|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0097|p.3,L4|6|Lingshu [5]. They are evaluated mostly on VQA-RAD [6], SLAKE [7] and PathVQA [8], where the asked|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0098|p.3,L4|7|Lingshu [5]. They are evaluated mostly on VQA-RAD [6], SLAKE [7] and PathVQA [8], where the asked|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0099|p.3,L4|8|Lingshu [5]. They are evaluated mostly on VQA-RAD [6], SLAKE [7] and PathVQA [8], where the asked|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0100|p.3,L7|9|Hallucination benchmarks and detectors. POPE [9] probes object hallucination with questions about|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0101|p.3,L8|10|absent objects. Medical benchmarks — CARES [10], Med-HallMark [11], MedVH [12] and MedHE-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0102|p.3,L8|11|absent objects. Medical benchmarks — CARES [10], Med-HallMark [11], MedVH [12] and MedHE-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0103|p.3,L8|12|absent objects. Medical benchmarks — CARES [10], Med-HallMark [11], MedVH [12] and MedHE-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0104|p.3,L9|13|val [13] — curate or perturb questions and answers. Two recent training-free detectors use counterfactual|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0105|p.3,L9|Two|val [13] — curate or perturb questions and answers. Two recent training-free detectors use counterfactual|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0106|p.3,L10|15|probes at inference: counter-evidence verification [15] blacks out the region supporting a claim and checks|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0107|p.3,L11|16|whether the claim persists, and counterfactual visual grounding uncertainty [16] contrasts grounding on|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0108|p.3,L12|three|factual and perturbed inputs. Our work differs in three ways: we change the image while holding the ques-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0109|p.3,L14|one|use the views to train a model, not only to audit one.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0110|p.3,L16|17|Counterfactual image editing. Agarwal et al. [17] edited natural images for VQA, removing objects so|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0111|p.3,L19|two|analogue, with two additions: the invariant edit uses the same tool and the same shape as the covariant one,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0112|p.3,L19|one|analogue, with two additions: the invariant edit uses the same tool and the same shape as the covariant one,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0113|p.3,L20|14|and abstention and clarification are scored by a clinical cost matrix. Learned inpainting such as LaMa [14]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0114|p.3,L21|18|makes plausible fills of large masks possible; classical inpainting [18], Poisson blending [19] and diffusion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0115|p.3,L21|19|makes plausible fills of large masks possible; classical inpainting [18], Poisson blending [19] and diffusion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0116|p.3,L22|20|inpainting [20] provide independent tools for testing whether a model learned one tool’s traces.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0117|p.3,L22|one|inpainting [20] provide independent tools for testing whether a model learned one tool’s traces.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0118|p.3,L25|21|are trained with reinforcement learning [21, 22]; in medicine, MMedAgent [23] learns to call tools and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0119|p.3,L25|22|are trained with reinforcement learning [21, 22]; in medicine, MMedAgent [23] learns to call tools and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0120|p.3,L25|23|are trained with reinforcement learning [21, 22]; in medicine, MMedAgent [23] learns to call tools and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0121|p.3,L26|24|MMedAgent-RL [24] optimises multi-agent collaboration. Our agent uses two simple tools. On-policy RL|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0122|p.3,L26|two|MMedAgent-RL [24] optimises multi-agent collaboration. Our agent uses two simple tools. On-policy RL|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0123|p.3,L27|25|(GRPO [25] with DAPO-style dynamic sampling [26]) gave no signal in pilot runs, so we use rejection-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0124|p.3,L27|26|(GRPO [25] with DAPO-style dynamic sampling [26]) gave no signal in pilot runs, so we use rejection-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0125|p.3,L28|27|sampling fine-tuning [27, 28]. Selective prediction is summarised by the area under the risk–coverage|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0126|p.3,L28|28|sampling fine-tuning [27, 28]. Selective prediction is summarised by the area under the risk–coverage|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0127|p.3,L29|29|curve [29]. We follow the CLAIM 2024 checklist [30] (Appendix C).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0128|p.3,L29|2024|curve [29]. We follow the CLAIM 2024 checklist [30] (Appendix C).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0129|p.3,L29|30|curve [29]. We follow the CLAIM 2024 checklist [30] (Appendix C).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0130|p.3,L32|3|3 Methods|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0131|p.3,L33|3.1|3.1 Task and agent protocol|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0132|p.3,L34|one|An episode presents one image and one question whose answer depends on a lesion. Each turn the model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0133|p.3,L34|one|An episode presents one image and one question whose answer depends on a lesion. Each turn the model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0134|p.3,L35|one|writes brief reasoning followed by exactly one tagged JSON action (prompt in Appendix A): zoom (a box|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0135|p.3,L36|0|on the original image, integer coordinates 0–1000, returning the cropped region) or window (centre and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0136|p.3,L36|1000|on the original image, integer coordinates 0–1000, returning the cropped region) or window (centre and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0137|p.3,L37|0|width on a 0–255 scale, returning the contrast-adjusted image), at most three calls per episode; answer,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0138|p.3,L37|255|width on a 0–255 scale, returning the contrast-adjusted image), at most three calls per episode; answer,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0139|p.3,L37|three|width on a 0–255 scale, returning the contrast-adjusted image), at most three calls per episode; answer,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0140|p.3,L44|3.2|3.2 Counterfactual views|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0141|p.3,L45|four|For every case (image, expert lesion mask, question whose answer depends on the lesion) we build four|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0142|p.3,L46|1|views; unedited lesion-free images from the same sources form a fifth kind (Figure 1; real test views in|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0143|p.3,L47|2|Figure 2).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0144|p.4,L24|1|Figure 1: Views built from each case and the expected action. Target removal and the random-removal control share|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0145|p.4,L29|5|Target removal. The lesion mask, dilated by 5 pixels, is inpainted. Expected: the answer stating the finding|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0146|p.4,L34|40|Degraded. Gaussian blur (σ = max(h, w)/40), Gaussian noise (σ = 60), 8× down- and up-sampling, JPEG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0147|p.4,L34|60|Degraded. Gaussian blur (σ = max(h, w)/40), Gaussian noise (σ = 60), 8× down- and up-sampling, JPEG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0148|p.4,L34|8|Degraded. Gaussian blur (σ = max(h, w)/40), Gaussian noise (σ = 60), 8× down- and up-sampling, JPEG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0149|p.4,L38|Two|Two symmetries make the design work. Target removal and natural negatives share expected answer and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0150|p.4,L40|0|model that reacts to edits treats them alike and scores ESG 0. Lesions under 20 pixels or over 20% of the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0151|p.4,L40|20|model that reacts to edits treats them alike and scores ESG 0. Lesions under 20 pixels or over 20% of the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0152|p.4,L40|20%|model that reacts to edits treats them alike and scores ESG 0. Lesions under 20 pixels or over 20% of the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0153|p.4,L43|19|same image, Poisson-blended [19]), for half of the cases.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0154|p.4,L43|half|same image, Poisson-blended [19]), for half of the cases.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0155|p.4,L46|3.3|3.3 Automated quality control|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0156|p.4,L51|4|neighbouring slices (4 of 63 validation and test images had a near-copy in training), which group splitting|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0157|p.4,L51|63|neighbouring slices (4 of 63 validation and test images had a near-copy in training), which group splitting|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0158|p.4,L53|0.6|its AUC is at most 0.6 (test set: 0.56). A hand-crafted shortcut classifier on the v4 training views reached|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0159|p.4,L53|0.56|its AUC is at most 0.6 (test set: 0.56). A hand-crafted shortcut classifier on the v4 training views reached|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0160|p.4,L54|0.59|AUC 0.59, so no further filtering was needed.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0161|p.4,L57|3.4|3.4 Reward and net utility|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0162|p.4,L58|1|Each decision is scored with a clinical cost matrix (Table 1). It is the selection reward during training and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0163|p.4,L59|0.5|the net utility metric at test. A correct answer on an original or random-removal view earns 0.5 more when|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0164|p.4,L60|0.3|its box overlaps the lesion with IoU ≥ 0.3 (boxes covering over half the image earn no bonus); unparseable|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0165|p.4,L60|half|its box overlaps the lesion with IoU ≥ 0.3 (boxes covering over half the image earn no bonus); unparseable|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0166|p.4,L61|−1|output scores −1; each tool call beyond the first costs 0.05. Section 5.5 reports net utility under four|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0167|p.4,L61|0.05|output scores −1; each tool call beyond the first costs 0.05. Section 5.5 reports net utility under four|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0168|p.4,L61|5.5|output scores −1; each tool call beyond the first costs 0.05. Section 5.5 reports net utility under four|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0169|p.4,L61|four|output scores −1; each tool call beyond the first costs 0.05. Section 5.5 reports net utility under four|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0170|p.5,L1|2|Figure 2: Real test views, one case per imaging type. Yellow: lesion (reference-standard mask); dashed cyan: edited|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0171|p.5,L1|one|Figure 2: Real test views, one case per imaging type. Yellow: lesion (reference-standard mask); dashed cyan: edited|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0172|p.5,L2|8.5|region. Note the second dark region in the breast-ultrasound image that the mask does not cover (Section 8.5).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0173|p.5,L4|1|Table 1: Cost matrix (reward per view). Target removal and natural negatives are scored identically by design.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0174|p.5,L7|+1.0|Original, random removal +1.0 −2.0 (−4.0 critical) −0.3 −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0175|p.5,L7|−2.0|Original, random removal +1.0 −2.0 (−4.0 critical) −0.3 −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0176|p.5,L7|−4.0|Original, random removal +1.0 −2.0 (−4.0 critical) −0.3 −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0177|p.5,L7|−0.3|Original, random removal +1.0 −2.0 (−4.0 critical) −0.3 −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0178|p.5,L7|−0.3|Original, random removal +1.0 −2.0 (−4.0 critical) −0.3 −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0179|p.5,L8|+1.0|Target removal, natural negative +1.0 −2.0 +0.5 −0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0180|p.5,L8|−2.0|Target removal, natural negative +1.0 −2.0 +0.5 −0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0181|p.5,L8|+0.5|Target removal, natural negative +1.0 −2.0 +0.5 −0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0182|p.5,L8|−0.5|Target removal, natural negative +1.0 −2.0 +0.5 −0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0183|p.5,L9|+0.25|Degraded +0.25 −2.0 0.0 +0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0184|p.5,L9|−2.0|Degraded +0.25 −2.0 0.0 +0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0185|p.5,L9|0.0|Degraded +0.25 −2.0 0.0 +0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0186|p.5,L9|+0.5|Degraded +0.25 −2.0 0.0 +0.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0187|p.5,L12|3.5|3.5 Model and training|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0188|p.5,L13|5|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0189|p.5,L13|4B|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0190|p.5,L13|31|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0191|p.5,L13|32|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0192|p.5,L13|16|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0193|p.5,L13|32|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0194|p.5,L13|0.05|The base model is Qwen3.5-4B [31] with LoRA [32] (rank 16, α = 32, dropout 0.05, on all linear layers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0195|p.5,L15|2%|the labels alone: optionally a zoom on a jittered box around the lesion (always for lesions under 2% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0196|p.5,L16|30%|the image), windowing on 30% of grey-scale images, then the expected final action with short template|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0197|p.5,L17|Half|reasoning. Half of the templated questions are reworded with one of four training paraphrases; three further|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0198|p.5,L17|one|reasoning. Half of the templated questions are reworded with one of four training paraphrases; three further|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0199|p.5,L17|four|reasoning. Half of the templated questions are reworded with one of four training paraphrases; three further|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0200|p.5,L17|three|reasoning. Half of the templated questions are reworded with one of four training paraphrases; three further|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0201|p.6,L1|1|Stage 1, supervised fine-tuning. 16,000 views drawn once at random from the training pools, one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0202|p.6,L1|16,000|Stage 1, supervised fine-tuning. 16,000 views drawn once at random from the training pools, one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0203|p.6,L1|one|Stage 1, supervised fine-tuning. 16,000 views drawn once at random from the training pools, one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0204|p.6,L2|3,706|pass (3,706 optimiser steps), learning rate 2 × 10−4 ; cases with lesions under 2% of the image are repeated|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0205|p.6,L2|2|pass (3,706 optimiser steps), learning rate 2 × 10−4 ; cases with lesions under 2% of the image are repeated|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0206|p.6,L2|10|pass (3,706 optimiser steps), learning rate 2 × 10−4 ; cases with lesions under 2% of the image are repeated|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0207|p.6,L2|4|pass (3,706 optimiser steps), learning rate 2 × 10−4 ; cases with lesions under 2% of the image are repeated|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0208|p.6,L2|2%|pass (3,706 optimiser steps), learning rate 2 × 10−4 ; cases with lesions under 2% of the image are repeated|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0209|p.6,L3|twice|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0210|p.6,L3|2|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0211|p.6,L3|27|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0212|p.6,L3|28|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0213|p.6,L3|1|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0214|p.6,L3|4|twice. Stage 2, rejection-sampling fine-tuning [27, 28]. The stage-1 model samples k = 4 episodes at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0215|p.6,L4|1.2|temperature 1.2 on 200 training views per view kind, 500 lesion-free and 300 lesion-erased views; the best|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0216|p.6,L4|200|temperature 1.2 on 200 training views per view kind, 500 lesion-free and 300 lesion-erased views; the best|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0217|p.6,L4|500|temperature 1.2 on 200 training views per view kind, 500 lesion-free and 300 lesion-erased views; the best|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0218|p.6,L4|300|temperature 1.2 on 200 training views per view kind, 500 lesion-free and 300 lesion-erased views; the best|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0219|p.6,L5|two|successful episode of each view is kept, and episodes from views the model mostly failed (at most two of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0220|p.6,L6|four|four right) are repeated three times. Training continues on these plus 3,000 synthetic views at learning rate|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0221|p.6,L6|three|four right) are repeated three times. Training continues on these plus 3,000 synthetic views at learning rate|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0222|p.6,L6|3,000|four right) are repeated three times. Training continues on these plus 3,000 synthetic views at learning rate|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0223|p.6,L7|5|5 × 10−5 . Stage 3, general-VQA replay. 5,000 views mixing MedScope views with ordinary questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0224|p.6,L7|10|5 × 10−5 . Stage 3, general-VQA replay. 5,000 views mixing MedScope views with ordinary questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0225|p.6,L7|5|5 × 10−5 . Stage 3, general-VQA replay. 5,000 views mixing MedScope views with ordinary questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0226|p.6,L7|3|5 × 10−5 . Stage 3, general-VQA replay. 5,000 views mixing MedScope views with ordinary questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0227|p.6,L7|5,000|5 × 10−5 . Stage 3, general-VQA replay. 5,000 views mixing MedScope views with ordinary questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0228|p.6,L9|35%|image excluded), with “absent” views at no less than 35% of the mix and “Is X healthy?” replay questions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0229|p.6,L10|5|balanced between yes and no; learning rate 5 × 10−5 .|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0230|p.6,L10|10|balanced between yes and no; learning rate 5 × 10−5 .|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0231|p.6,L10|5|balanced between yes and no; learning rate 5 × 10−5 .|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0232|p.6,L13|3.6|3.6 Pre-registered selection|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0233|p.6,L14|1|The data plan, recipe, selection rule and reporting rule were committed to the public repository on 1 Novem-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0234|p.6,L15|2026|ber 2026, before any v4 data was built or model trained. Let U be validation net utility and H the validation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0235|p.6,L16|3|rate of claimed findings on healthy images. Stage 3 is selected if U3 ≥ U2 − 0.02 and H3 ≤ H2 + 0.02;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0236|p.6,L16|0.02|rate of claimed findings on healthy images. Stage 3 is selected if U3 ≥ U2 − 0.02 and H3 ≤ H2 + 0.02;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0237|p.6,L16|0.02|rate of claimed findings on healthy images. Stage 3 is selected if U3 ≥ U2 − 0.02 and H3 ≤ H2 + 0.02;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0238|p.6,L17|2|otherwise stage 2 under the same rule against stage 1; otherwise stage 1. Amendment 1 (after the stage-1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0239|p.6,L17|1|otherwise stage 2 under the same rule against stage 1; otherwise stage 1. Amendment 1 (after the stage-1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0240|p.6,L17|1|otherwise stage 2 under the same rule against stage 1; otherwise stage 1. Amendment 1 (after the stage-1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0241|p.6,L17|1|otherwise stage 2 under the same rule against stage 1; otherwise stage 1. Amendment 1 (after the stage-1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0242|p.6,L17|1|otherwise stage 2 under the same rule against stage 1; otherwise stage 1. Amendment 1 (after the stage-1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0243|p.6,L19|0.02|set, to be kept if the chosen stage fell more than 0.02 below it. Amendment 2 (before any test result) added|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0244|p.6,L19|2|set, to be kept if the chosen stage fell more than 0.02 below it. Amendment 2 (before any test result) added|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0245|p.6,L21|540|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0246|p.6,L21|1,473|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0247|p.6,L21|0.585|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0248|p.6,L21|13.6%|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0249|p.6,L21|1|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0250|p.6,L21|0.610|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0251|p.6,L21|12.7%|On 540 validation cases (1,473 views), U and H were 0.585 and 13.6% for stage 1, 0.610 and 12.7%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0252|p.6,L22|2|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0253|p.6,L22|0.613|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0254|p.6,L22|7.7%|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0255|p.6,L22|3|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0256|p.6,L22|0.593|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0257|p.6,L22|8.2%|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0258|p.6,L22|3|for stage 2, and 0.613 and 7.7% for stage 3; v3 scored 0.593 and 8.2%. The rule selected stage 3, which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0259|p.6,L23|4B|is MedScope-4B. It was then evaluated once on every test set; no setting, threshold or prompt was tuned|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0260|p.6,L27|3.7|3.7 Metrics|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0261|p.6,L34|0.3|claims P(claims finding \| N); grounded accuracy is correct with IoU ≥ 0.3 on O; the clarify rate is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0262|p.6,L35|29|P(clarify \| D); net utility is the mean reward over all views; AURC [29] uses the geometric mean of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0263|p.6,L39|3.8|3.8 Statistics|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0264|p.6,L40|95%|95% confidence intervals use 2,000 bootstrap resamples of cases [33]. Model comparisons use a paired|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0265|p.6,L40|2,000|95% confidence intervals use 2,000 bootstrap resamples of cases [33]. Model comparisons use a paired|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0266|p.6,L40|33|95% confidence intervals use 2,000 bootstrap resamples of cases [33]. Model comparisons use a paired|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0267|p.6,L41|two|bootstrap over shared cases with two-sided p-values. Seed results are reported as mean ± standard deviation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0268|p.6,L42|three|over three seeds, with each seed pair also compared by paired bootstrap. Proportions on small subsets use|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0269|p.6,L45|0.001|reach p &lt; 0.001.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0270|p.6,L48|3.9|3.9 Evaluation harness|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0271|p.6,L49|one|Open models decode greedily in bf16 on one A100 40 GB; API models use provider defaults. No model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0272|p.6,L49|40|Open models decode greedily in bf16 on one A100 40 GB; API models use provider defaults. No model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0273|p.6,L50|768|receives a model-specific repetition penalty. API models receive PNG images with the long side at most 768|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0274|p.7,L1|2|Table 2: Main (internal) test set by source.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0275|p.7,L4|7|SLAKE [7] CT / MRI 17 90 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0276|p.7,L4|17|SLAKE [7] CT / MRI 17 90 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0277|p.7,L4|90|SLAKE [7] CT / MRI 17 90 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0278|p.7,L5|34|Kvasir-SEG [34] + HyperKvasir [35] Colonoscopy 83 91 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0279|p.7,L5|35|Kvasir-SEG [34] + HyperKvasir [35] Colonoscopy 83 91 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0280|p.7,L5|83|Kvasir-SEG [34] + HyperKvasir [35] Colonoscopy 83 91 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0281|p.7,L5|91|Kvasir-SEG [34] + HyperKvasir [35] Colonoscopy 83 91 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0282|p.7,L6|36|ChestX-Det [36] Chest X-ray 41 50 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0283|p.7,L6|41|ChestX-Det [36] Chest X-ray 41 50 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0284|p.7,L6|50|ChestX-Det [36] Chest X-ray 41 50 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0285|p.7,L7|38|BUSI [38] Breast ultrasound 42 15 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0286|p.7,L7|42|BUSI [38] Breast ultrasound 42 15 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0287|p.7,L7|15|BUSI [38] Breast ultrasound 42 15 near-copy groups|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0288|p.7,L8|39|TCGA-LGG [39] Brain MRI (FLAIR) 36 42 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0289|p.7,L8|36|TCGA-LGG [39] Brain MRI (FLAIR) 36 42 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0290|p.7,L8|42|TCGA-LGG [39] Brain MRI (FLAIR) 36 42 patient|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0291|p.7,L9|219|Total 219 288 507 cases, 1,115 views|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0292|p.7,L9|288|Total 219 288 507 cases, 1,115 views|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0293|p.7,L9|507|Total 219 288 507 cases, 1,115 views|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0294|p.7,L9|1,115|Total 219 288 507 cases, 1,115 views|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0295|p.7,L11|3|Table 3: Further test sets. “Fresh” sets were untouched until the model was selected (confirmatory).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0296|p.7,L14|169|External centres 169|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0297|p.7,L15|40|CVC-ClinicDB [40] (40), QaTa-COV19 [41] (20), BUS- New scanners, pop-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0298|p.7,L15|40|CVC-ClinicDB [40] (40), QaTa-COV19 [41] (20), BUS- New scanners, pop-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0299|p.7,L15|41|CVC-ClinicDB [40] (40), QaTa-COV19 [41] (20), BUS- New scanners, pop-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0300|p.7,L15|20|CVC-ClinicDB [40] (40), QaTa-COV19 [41] (20), BUS- New scanners, pop-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0301|p.7,L16|42|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0302|p.7,L16|45|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0303|p.7,L16|2023|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0304|p.7,L16|43|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0305|p.7,L16|44|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0306|p.7,L16|64|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0307|p.7,L16|50|BRA [42] (45), BraTS-Africa 2023 [43, 44] (64, with 50 ulations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0308|p.7,L18|76|Fresh internal 76 ChestX-Det, unused test-split patients (36 with a lesion, 40 Confirmatory|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0309|p.7,L18|36|Fresh internal 76 ChestX-Det, unused test-split patients (36 with a lesion, 40 Confirmatory|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0310|p.7,L18|40|Fresh internal 76 ChestX-Det, unused test-split patients (36 with a lesion, 40 Confirmatory|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0311|p.7,L20|316|Fresh external 316 BraTS 2023 meningioma [45] (82), BUS-UCLM [46] Confirmatory, new|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0312|p.7,L20|2023|Fresh external 316 BraTS 2023 meningioma [45] (82), BUS-UCLM [46] Confirmatory, new|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0313|p.7,L20|45|Fresh external 316 BraTS 2023 meningioma [45] (82), BUS-UCLM [46] Confirmatory, new|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0314|p.7,L20|82|Fresh external 316 BraTS 2023 meningioma [45] (82), BUS-UCLM [46] Confirmatory, new|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0315|p.7,L20|46|Fresh external 316 BraTS 2023 meningioma [45] (82), BUS-UCLM [46] Confirmatory, new|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0316|p.7,L21|99|(99), SIIM-ACR pneumothorax [47] (96), ETIS- sources|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0317|p.7,L21|47|(99), SIIM-ACR pneumothorax [47] (96), ETIS- sources|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0318|p.7,L21|96|(99), SIIM-ACR pneumothorax [47] (96), ETIS- sources|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0319|p.7,L22|48|LaribPolypDB [48] (39)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0320|p.7,L22|39|LaribPolypDB [48] (39)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0321|p.7,L23|373|Held-out wordings 373 Main test with three test-only paraphrases Question wording|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0322|p.7,L23|three|Held-out wordings 373 Main test with three test-only paraphrases Question wording|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0323|p.7,L24|1,051|Standard VQA 1,051 VQA-RAD test (451), SLAKE English test (300 sampled), No regression|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0324|p.7,L24|451|Standard VQA 1,051 VQA-RAD test (451), SLAKE English test (300 sampled), No regression|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0325|p.7,L24|300|Standard VQA 1,051 VQA-RAD test (451), SLAKE English test (300 sampled), No regression|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0326|p.7,L25|300|PathVQA test (300 sampled)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0327|p.7,L30|one|that rate is reported. Correctness and rewards are recomputed from stored per-view transcripts by one script|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0328|p.7,L34|4|4 Experimental setup|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0329|p.7,L35|4.1|4.1 Study design and data|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0330|p.7,L37|3.2|segmentation masks and image labels; expected answers are derived from them by rule (Section 3.2). No|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0331|p.7,L39|7|Training and validation. Training uses SLAKE CT/MRI [7], Kvasir-SEG [34] with HyperKvasir|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0332|p.7,L39|34|Training and validation. Training uses SLAKE CT/MRI [7], Kvasir-SEG [34] with HyperKvasir|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0333|p.7,L40|35|normal landmarks as lesion-free images [35], ChestX-Det [36] (from NIH ChestX-ray14 [37]), BUSI [38]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0334|p.7,L40|36|normal landmarks as lesion-free images [35], ChestX-Det [36] (from NIH ChestX-ray14 [37]), BUSI [38]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0335|p.7,L40|37|normal landmarks as lesion-free images [35], ChestX-Det [36] (from NIH ChestX-ray14 [37]), BUSI [38]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0336|p.7,L40|38|normal landmarks as lesion-free images [35], ChestX-Det [36] (from NIH ChestX-ray14 [37]), BUSI [38]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0337|p.7,L41|39|and TCGA-LGG [39]: 1,508 SLAKE and colonoscopy cases plus 1,792 chest X-ray, breast ultrasound and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0338|p.7,L41|1,508|and TCGA-LGG [39]: 1,508 SLAKE and colonoscopy cases plus 1,792 chest X-ray, breast ultrasound and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0339|p.7,L41|1,792|and TCGA-LGG [39]: 1,508 SLAKE and colonoscopy cases plus 1,792 chest X-ray, breast ultrasound and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0340|p.7,L42|690|brain MRI cases after quality checks, with 690 lesion-free images from the latter three sources. Validation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0341|p.7,L42|three|brain MRI cases after quality checks, with 690 lesion-free images from the latter three sources. Validation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0342|p.7,L43|540|holds 540 cases (1,473 views). Diffuse chest findings, oversized lesions and brain slices with little tissue|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0343|p.7,L43|1,473|holds 540 cases (1,473 views). Diffuse chest findings, oversized lesions and brain slices with little tissue|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0344|p.7,L44|2|are excluded. Table 2 gives the main test set and Table 3 the further test sets, none of which was used for|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0345|p.7,L44|3|are excluded. Table 2 gives the main test set and Table 3 the further test sets, none of which was used for|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0346|p.7,L47|93|source and checked to be identical (ChestX-Det 93, BUSI 57, TCGA-LGG 79 images; none differed or was|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0347|p.7,L47|57|source and checked to be identical (ChestX-Det 93, BUSI 57, TCGA-LGG 79 images; none differed or was|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0348|p.7,L47|79|source and checked to be identical (ChestX-Det 93, BUSI 57, TCGA-LGG 79 images; none differed or was|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0349|p.7,L48|one|missing), and every patient or near-copy group holding one was removed from all v4 splits. Patients seen|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0350|p.7,L50|14|any training or test image. TCGA-LGG contributed no fresh internal cases because all 14 of its test-split|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0351|p.8,L1|4.2|4.2 Models compared|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0352|p.8,L2|31|Frontier models through their APIs, identical agent loop and provider defaults, evaluated on 31 October|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0353|p.8,L3|2026|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0354|p.8,L3|6|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0355|p.8,L3|6|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0356|p.8,L3|6.1|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0357|p.8,L3|5.1|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0358|p.8,L3|5.5|2026: OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol; Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0359|p.8,L4|5.5|Sonnet 5.5; Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. The three flagships (gpt-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0360|p.8,L4|4|Sonnet 5.5; Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. The three flagships (gpt-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0361|p.8,L4|3.1|Sonnet 5.5; Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. The three flagships (gpt-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0362|p.8,L4|3.8|Sonnet 5.5; Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. The three flagships (gpt-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0363|p.8,L4|three|Sonnet 5.5; Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash. The three flagships (gpt-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0364|p.8,L5|6|6-astra, Claude Opus 5.5, gemini-4-argon) were also run on the same 150 main-test cases with a cautious|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0365|p.8,L5|5.5|6-astra, Claude Opus 5.5, gemini-4-argon) were also run on the same 150 main-test cases with a cautious|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0366|p.8,L5|4|6-astra, Claude Opus 5.5, gemini-4-argon) were also run on the same 150 main-test cases with a cautious|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0367|p.8,L5|150|6-astra, Claude Opus 5.5, gemini-4-argon) were also run on the same 150 main-test cases with a cautious|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0368|p.8,L6|four|prompt, with four solved training examples in context, at their highest reasoning setting, and with held-out|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0369|p.8,L7|5|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0370|p.8,L7|4B|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0371|p.8,L7|31|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0372|p.8,L7|1.5|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0373|p.8,L7|4B|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0374|p.8,L7|4|wordings. Open models (bf16): Qwen3.5-4B (MedScope’s base) [31], MedGemma 1.5 4B [4], Lingshu-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0375|p.8,L8|7B|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0376|p.8,L8|5|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0377|p.8,L8|7B|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0378|p.8,L8|2|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0379|p.8,L8|5|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0380|p.8,L8|7B|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0381|p.8,L8|49|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0382|p.8,L8|8B|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0383|p.8,L8|50|7B [5], HuatuoGPT-Vision-7B [2], Qwen2.5-VL-7B [49] and Qwen3-VL-8B [50], each with the agent|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0384|p.8,L9|1|prompt and, separately, with its own plain prompt. Ablation arms, all at stage 1 with the same 16,000-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0385|p.8,L9|16,000|prompt and, separately, with its own plain prompt. Ablation arms, all at stage 1 with the same 16,000-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0386|p.8,L13|two|first two are trained with three seeds each (seeds change LoRA initialisation, data order and trajectory|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0387|p.8,L13|three|first two are trained with three seeds each (seeds change LoRA initialisation, data order and trajectory|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0388|p.8,L14|1.5|sampling); both are repeated on MedGemma 1.5 4B. Trivial policies that ignore the image: always claim|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0389|p.8,L14|4B|sampling); both are repeated on MedGemma 1.5 4B. Trivial policies that ignore the image: always claim|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0390|p.8,L18|4.3|4.3 Compute and software|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0391|p.8,L19|40|Every training stage ran on a single NVIDIA A100 40 GB (Google Colab), about 4 hours per stage; one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0392|p.8,L19|4|Every training stage ran on a single NVIDIA A100 40 GB (Google Colab), about 4 hours per stage; one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0393|p.8,L19|one|Every training stage ran on a single NVIDIA A100 40 GB (Google Colab), about 4 hours per stage; one|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0394|p.8,L20|1|evaluation of a local model on the main test takes about 1 hour. Software: PyTorch 2.11, Transformers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0395|p.8,L20|2.11|evaluation of a local model on the main test takes about 1 hour. Software: PyTorch 2.11, Transformers|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0396|p.8,L21|5.22.1|5.22.1, PEFT 0.21.2, bitsandbytes 0.50.2. [Total API cost of all frontier runs, from the stored token counts.]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0397|p.8,L21|0.21.2|5.22.1, PEFT 0.21.2, bitsandbytes 0.50.2. [Total API cost of all frontier runs, from the stored token counts.]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0398|p.8,L21|0.50.2|5.22.1, PEFT 0.21.2, bitsandbytes 0.50.2. [Total API cost of all frontier runs, from the stored token counts.]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0399|p.8,L24|5|5 Results|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0400|p.8,L25|5.1|5.1 Main test|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0401|p.8,L26|4B|MedScope-4B has the highest ESG (0.758) and the lowest erased-lesion claims (9.6%) of any model that|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0402|p.8,L26|0.758|MedScope-4B has the highest ESG (0.758) and the lowest erased-lesion claims (9.6%) of any model that|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0403|p.8,L26|9.6%|MedScope-4B has the highest ESG (0.758) and the lowest erased-lesion claims (9.6%) of any model that|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0404|p.8,L27|4|answers (Table 4). It is better than all nine frontier and all six open models on ESG, erased-lesion claims|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0405|p.8,L27|nine|answers (Table 4). It is better than all nine frontier and all six open models on ESG, erased-lesion claims|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0406|p.8,L27|six|answers (Table 4). It is better than all nine frontier and all six open models on ESG, erased-lesion claims|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0407|p.8,L28|0.001|and net utility (all p &lt; 0.001; Table 5). Its accuracy on real lesions does not differ from any frontier model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0408|p.8,L28|5|and net utility (all p &lt; 0.001; Table 5). Its accuracy on real lesions does not differ from any frontier model|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0409|p.8,L29|0.849|(CCR 0.849 vs 0.829–0.888; all p ≥ 0.12). On unedited healthy images it reports a finding in 7.6% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0410|p.8,L29|0.829|(CCR 0.849 vs 0.829–0.888; all p ≥ 0.12). On unedited healthy images it reports a finding in 7.6% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0411|p.8,L29|0.888|(CCR 0.849 vs 0.829–0.888; all p ≥ 0.12). On unedited healthy images it reports a finding in 7.6% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0412|p.8,L29|0.12|(CCR 0.849 vs 0.829–0.888; all p ≥ 0.12). On unedited healthy images it reports a finding in 7.6% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0413|p.8,L29|7.6%|(CCR 0.849 vs 0.829–0.888; all p ≥ 0.12). On unedited healthy images it reports a finding in 7.6% of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0414|p.8,L30|eight|cases, fewer than eight of nine frontier models (p ≤ 0.001); against gemini-4-argon (9.0%) the difference|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0415|p.8,L30|nine|cases, fewer than eight of nine frontier models (p ≤ 0.001); against gemini-4-argon (9.0%) the difference|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0416|p.8,L30|0.001|cases, fewer than eight of nine frontier models (p ≤ 0.001); against gemini-4-argon (9.0%) the difference|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0417|p.8,L30|4|cases, fewer than eight of nine frontier models (p ≤ 0.001); against gemini-4-argon (9.0%) the difference|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0418|p.8,L30|9.0%|cases, fewer than eight of nine frontier models (p ≤ 0.001); against gemini-4-argon (9.0%) the difference|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0419|p.8,L31|0.59|is not significant (p = 0.59). It asks to clarify on every degraded view (170 of 170). Qwen3-VL-8B and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0420|p.8,L31|170|is not significant (p = 0.59). It asks to clarify on every degraded view (170 of 170). Qwen3-VL-8B and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0421|p.8,L31|170|is not significant (p = 0.59). It asks to clarify on every degraded view (170 of 170). Qwen3-VL-8B and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0422|p.8,L31|8B|is not significant (p = 0.59). It asks to clarify on every degraded view (170 of 170). Qwen3-VL-8B and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0423|p.8,L32|5|Qwen2.5-VL-7B claim few erased lesions because they rarely answer lesion questions correctly at all (CCR|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0424|p.8,L32|7B|Qwen2.5-VL-7B claim few erased lesions because they rarely answer lesion questions correctly at all (CCR|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0425|p.8,L33|0.55|0.55 and 0.14); their ESG stays low.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0426|p.8,L33|0.14|0.55 and 0.14); their ESG stays low.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0427|p.8,L36|5.2|5.2 By imaging type|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0428|p.8,L37|6|The advantage holds in every imaging type (Table 6). MedScope-4B is strongest on colonoscopy (ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0429|p.8,L37|4B|The advantage holds in every imaging type (Table 6). MedScope-4B is strongest on colonoscopy (ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0430|p.8,L38|0.95|0.95), brain MRI and breast ultrasound (0.74–0.75), and weakest on chest X-ray (0.51) and SLAKE|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0431|p.8,L38|0.74|0.95), brain MRI and breast ultrasound (0.74–0.75), and weakest on chest X-ray (0.51) and SLAKE|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0432|p.8,L38|0.75|0.95), brain MRI and breast ultrasound (0.74–0.75), and weakest on chest X-ray (0.51) and SLAKE|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0433|p.8,L38|0.51|0.95), brain MRI and breast ultrasound (0.74–0.75), and weakest on chest X-ray (0.51) and SLAKE|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0434|p.8,L39|0.47|CT/MRI (0.47). No flagship exceeds ESG 0.69 in any type, and on chest X-ray the three flagships lie|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0435|p.8,L39|0.69|CT/MRI (0.47). No flagship exceeds ESG 0.69 in any type, and on chest X-ray the three flagships lie|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0436|p.8,L39|three|CT/MRI (0.47). No flagship exceeds ESG 0.69 in any type, and on chest X-ray the three flagships lie|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0437|p.8,L40|−0.05|between −0.05 and 0.20.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0438|p.8,L40|0.20|between −0.05 and 0.20.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0439|p.8,L43|5.3|5.3 What produces the behaviour|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0440|p.8,L44|1|The counterfactual views are the active ingredient. Removing them from stage-1 training, with the same|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0441|p.8,L45|+0.525|data draw, optimiser steps and schedule, lowers ESG on every seed (seed by seed +0.525, +0.539 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0442|p.8,L45|+0.539|data draw, optimiser steps and schedule, lowers ESG on every seed (seed by seed +0.525, +0.539 and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0443|p.8,L46|+0.324|+0.324 in favour of the recipe, all p &lt; 0.001) and raises erased-lesion claims to the frontier level or above|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0444|p.8,L46|0.001|+0.324 in favour of the recipe, all p &lt; 0.001) and raises erased-lesion claims to the frontier level or above|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0445|p.8,L47|7|(Table 7). The arm without counterfactual views says “present” more readily, so it is more accurate on real|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0446|p.8,L48|0.955|lesions (CCR 0.955 vs 0.871) and fails whenever the lesion is gone. Healthy-image claims also fall with|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0447|p.8,L48|0.871|lesions (CCR 0.955 vs 0.871) and fails whenever the lesion is gone. Healthy-image claims also fall with|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0448|p.8,L49|13.9%|the recipe (13.9% vs 35.9%), although both arms train on the same lesion-free images.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0449|p.8,L49|35.9%|the recipe (13.9% vs 35.9%), although both arms train on the same lesion-free images.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0450|p.9,L1|4|Table 4: Main test (507 cases, 1,115 views; agent prompt for every model). Erased, Healthy: % of views on which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0451|p.9,L1|507|Table 4: Main test (507 cases, 1,115 views; agent prompt for every model). Erased, Healthy: % of views on which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0452|p.9,L1|1,115|Table 4: Main test (507 cases, 1,115 views; agent prompt for every model). Erased, Healthy: % of views on which|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0453|p.9,L5|4B|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0454|p.9,L5|0.849|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0455|p.9,L5|0.758|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0456|p.9,L5|9.6|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0457|p.9,L5|7.6|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0458|p.9,L5|0.732|MedScope-4B (this work) 0.849 0.758 9.6 7.6 0.732 [CI]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0459|p.9,L6|4|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0460|p.9,L6|0.874|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0461|p.9,L6|0.470|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0462|p.9,L6|41.1|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0463|p.9,L6|9.0|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0464|p.9,L6|0.565|gemini-4-argon 0.874 0.470 41.1 9.0 0.565|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0465|p.9,L7|5.5|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0466|p.9,L7|0.870|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0467|p.9,L7|0.402|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0468|p.9,L7|48.4|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0469|p.9,L7|16.7|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0470|p.9,L7|0.381|Claude Sonnet 5.5 0.870 0.402 48.4 16.7 0.381|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0471|p.9,L8|3.1|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0472|p.9,L8|0.849|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0473|p.9,L8|0.384|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0474|p.9,L8|51.6|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0475|p.9,L8|26.7|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0476|p.9,L8|0.306|gemini-3.1-pro-preview 0.849 0.384 51.6 26.7 0.306|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0477|p.9,L9|6|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0478|p.9,L9|0.829|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0479|p.9,L9|0.342|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0480|p.9,L9|51.6|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0481|p.9,L9|25.7|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0482|p.9,L9|0.261|gpt-6-sol 0.829 0.342 51.6 25.7 0.261|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0483|p.9,L10|5.1|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0484|p.9,L10|0.856|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0485|p.9,L10|0.342|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0486|p.9,L10|52.1|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0487|p.9,L10|23.3|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0488|p.9,L10|0.255|Claude Fable 5.1 0.856 0.342 52.1 23.3 0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0489|p.9,L11|5.5|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0490|p.9,L11|0.863|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0491|p.9,L11|0.329|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0492|p.9,L11|53.9|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0493|p.9,L11|23.6|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0494|p.9,L11|0.358|Claude Opus 5.5 0.863 0.329 53.9 23.6 0.358|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0495|p.9,L12|6.1|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0496|p.9,L12|0.888|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0497|p.9,L12|0.324|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0498|p.9,L12|58.9|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0499|p.9,L12|30.9|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0500|p.9,L12|0.276|gpt-6.1-sol 0.888 0.324 58.9 30.9 0.276|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0501|p.9,L13|6|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0502|p.9,L13|0.886|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0503|p.9,L13|0.306|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0504|p.9,L13|58.9|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0505|p.9,L13|27.8|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0506|p.9,L13|0.309|gpt-6-astra 0.886 0.306 58.9 27.8 0.309|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0507|p.9,L14|3.8|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0508|p.9,L14|0.868|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0509|p.9,L14|0.269|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0510|p.9,L14|61.6|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0511|p.9,L14|27.8|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0512|p.9,L14|0.263|gemini-3.8-flash 0.868 0.269 61.6 27.8 0.263|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0513|p.9,L15|7B|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0514|p.9,L15|0.527|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0515|p.9,L15|0.416|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0516|p.9,L15|32.0|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0517|p.9,L15|12.5|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0518|p.9,L15|−0.249|Lingshu-7B 0.527 0.416 32.0 12.5 −0.249|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0519|p.9,L16|5|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0520|p.9,L16|4B|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0521|p.9,L16|0.758|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0522|p.9,L16|0.338|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0523|p.9,L16|42.0|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0524|p.9,L16|19.4|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0525|p.9,L16|0.134|Qwen3.5-4B (base) 0.758 0.338 42.0 19.4 0.134|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0526|p.9,L17|8B|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0527|p.9,L17|0.553|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0528|p.9,L17|0.297|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0529|p.9,L17|12.8|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0530|p.9,L17|12.5|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0531|p.9,L17|0.186|Qwen3-VL-8B 0.553 0.297 12.8 12.5 0.186|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0532|p.9,L18|1.5|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0533|p.9,L18|4B|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0534|p.9,L18|0.674|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0535|p.9,L18|0.283|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0536|p.9,L18|54.3|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0537|p.9,L18|24.0|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0538|p.9,L18|−0.255|MedGemma 1.5 4B 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0539|p.9,L19|7B|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0540|p.9,L19|0.498|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0541|p.9,L19|0.265|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0542|p.9,L19|30.1|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0543|p.9,L19|22.9|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0544|p.9,L19|−0.426|HuatuoGPT-Vision-7B 0.498 0.265 30.1 22.9 −0.426|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0545|p.9,L20|5|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0546|p.9,L20|7B|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0547|p.9,L20|0.144|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0548|p.9,L20|0.146|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0549|p.9,L20|5.5|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0550|p.9,L20|24.7|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0551|p.9,L20|−0.742|Qwen2.5-VL-7B 0.144 0.146 5.5 24.7 −0.742|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0552|p.9,L21|1.000|Always claims the finding 1.000 0.000 100 100 −0.478|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0553|p.9,L21|0.000|Always claims the finding 1.000 0.000 100 100 −0.478|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0554|p.9,L21|100|Always claims the finding 1.000 0.000 100 100 −0.478|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0555|p.9,L21|100|Always claims the finding 1.000 0.000 100 100 −0.478|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0556|p.9,L21|−0.478|Always claims the finding 1.000 0.000 100 100 −0.478|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0557|p.9,L22|0.000|Always says it is absent 0.000 0.000 0 0 −0.848|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0558|p.9,L22|0.000|Always says it is absent 0.000 0.000 0 0 −0.848|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0559|p.9,L22|0|Always says it is absent 0.000 0.000 0 0 −0.848|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0560|p.9,L22|0|Always says it is absent 0.000 0.000 0 0 −0.848|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0561|p.9,L22|−0.848|Always says it is absent 0.000 0.000 0 0 −0.848|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0562|p.9,L23|0.000|Always refers 0.000 0.000 0 0 0.110|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0563|p.9,L23|0.000|Always refers 0.000 0.000 0 0 0.110|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0564|p.9,L23|0|Always refers 0.000 0.000 0 0 0.110|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0565|p.9,L23|0|Always refers 0.000 0.000 0 0 0.110|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0566|p.9,L23|0.110|Always refers 0.000 0.000 0 0 0.110|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0567|p.9,L25|5|Table 5: MedScope-4B minus each model, paired bootstrap over the same 507 cases: difference [95% CI]. Positive|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0568|p.9,L25|4B|Table 5: MedScope-4B minus each model, paired bootstrap over the same 507 cases: difference [95% CI]. Positive|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0569|p.9,L25|507|Table 5: MedScope-4B minus each model, paired bootstrap over the same 507 cases: difference [95% CI]. Positive|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0570|p.9,L25|95%|Table 5: MedScope-4B minus each model, paired bootstrap over the same 507 cases: difference [95% CI]. Positive|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0571|p.9,L26|four|is better for ESG and net utility; negative is better for the claim rates. Against the other four open models every ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0572|p.9,L27|0.001|and net-utility difference is also p &lt; 0.001.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0573|p.9,L30|4|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0574|p.9,L30|+0.288|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0575|p.9,L30|0.208|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0576|p.9,L30|0.367|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0577|p.9,L30|−0.315|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0578|p.9,L30|−0.385|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0579|p.9,L30|−0.243|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0580|p.9,L30|−0.014|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0581|p.9,L30|−0.059|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0582|p.9,L30|0.028|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0583|p.9,L30|−0.025|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0584|p.9,L30|−0.070|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0585|p.9,L30|0.017|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0586|p.9,L30|+0.168|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0587|p.9,L30|0.083|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0588|p.9,L30|0.254|gemini-4-argon +0.288 [0.208, 0.367] −0.315 [−0.385, −0.243] −0.014 [−0.059, 0.028] −0.025 [−0.070, 0.017] +0.168 [0.083, 0.254]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0589|p.9,L31|5.5|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0590|p.9,L31|+0.356|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0591|p.9,L31|0.284|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0592|p.9,L31|0.431|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0593|p.9,L31|−0.388|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0594|p.9,L31|−0.459|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0595|p.9,L31|−0.318|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0596|p.9,L31|−0.090|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0597|p.9,L31|−0.137|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0598|p.9,L31|−0.045|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0599|p.9,L31|−0.021|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0600|p.9,L31|−0.069|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0601|p.9,L31|0.026|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0602|p.9,L31|+0.351|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0603|p.9,L31|0.267|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0604|p.9,L31|0.437|Claude Sonnet 5.5 +0.356 [0.284, 0.431] −0.388 [−0.459, −0.318] −0.090 [−0.137, −0.045] −0.021 [−0.069, 0.026] +0.351 [0.267, 0.437]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0605|p.9,L32|3.1|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0606|p.9,L32|+0.374|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0607|p.9,L32|0.298|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0608|p.9,L32|0.448|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0609|p.9,L32|−0.420|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0610|p.9,L32|−0.491|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0611|p.9,L32|−0.350|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0612|p.9,L32|−0.191|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0613|p.9,L32|−0.252|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0614|p.9,L32|−0.133|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0615|p.9,L32|0.000|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0616|p.9,L32|−0.043|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0617|p.9,L32|0.044|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0618|p.9,L32|+0.426|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0619|p.9,L32|0.337|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0620|p.9,L32|0.519|gemini-3.1-pro-prev. +0.374 [0.298, 0.448] −0.420 [−0.491, −0.350] −0.191 [−0.252, −0.133] 0.000 [−0.043, 0.044] +0.426 [0.337, 0.519]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0621|p.9,L33|6|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0622|p.9,L33|+0.416|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0623|p.9,L33|0.341|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0624|p.9,L33|0.489|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0625|p.9,L33|−0.420|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0626|p.9,L33|−0.491|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0627|p.9,L33|−0.346|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0628|p.9,L33|−0.181|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0629|p.9,L33|−0.235|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0630|p.9,L33|−0.126|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0631|p.9,L33|+0.021|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0632|p.9,L33|−0.022|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0633|p.9,L33|0.063|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0634|p.9,L33|+0.472|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0635|p.9,L33|0.389|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0636|p.9,L33|0.554|gpt-6-sol +0.416 [0.341, 0.489] −0.420 [−0.491, −0.346] −0.181 [−0.235, −0.126] +0.021 [−0.022, 0.063] +0.472 [0.389, 0.554]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0637|p.9,L34|5.1|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0638|p.9,L34|+0.416|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0639|p.9,L34|0.339|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0640|p.9,L34|0.496|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0641|p.9,L34|−0.425|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0642|p.9,L34|−0.500|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0643|p.9,L34|−0.355|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0644|p.9,L34|−0.156|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0645|p.9,L34|−0.212|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0646|p.9,L34|−0.102|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0647|p.9,L34|−0.007|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0648|p.9,L34|−0.054|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0649|p.9,L34|0.039|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0650|p.9,L34|+0.477|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0651|p.9,L34|0.384|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0652|p.9,L34|0.566|Claude Fable 5.1 +0.416 [0.339, 0.496] −0.425 [−0.500, −0.355] −0.156 [−0.212, −0.102] −0.007 [−0.054, 0.039] +0.477 [0.384, 0.566]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0653|p.9,L35|5.5|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0654|p.9,L35|+0.429|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0655|p.9,L35|0.345|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0656|p.9,L35|0.507|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0657|p.9,L35|−0.443|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0658|p.9,L35|−0.515|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0659|p.9,L35|−0.368|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0660|p.9,L35|−0.160|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0661|p.9,L35|−0.217|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0662|p.9,L35|−0.103|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0663|p.9,L35|−0.014|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0664|p.9,L35|−0.066|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0665|p.9,L35|0.036|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0666|p.9,L35|+0.374|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0667|p.9,L35|0.283|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0668|p.9,L35|0.466|Claude Opus 5.5 +0.429 [0.345, 0.507] −0.443 [−0.515, −0.368] −0.160 [−0.217, −0.103] −0.014 [−0.066, 0.036] +0.374 [0.283, 0.466]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0669|p.9,L36|6.1|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0670|p.9,L36|+0.434|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0671|p.9,L36|0.354|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0672|p.9,L36|0.520|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0673|p.9,L36|−0.493|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0674|p.9,L36|−0.566|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0675|p.9,L36|−0.423|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0676|p.9,L36|−0.233|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0677|p.9,L36|−0.292|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0678|p.9,L36|−0.178|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0679|p.9,L36|−0.039|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0680|p.9,L36|−0.088|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0681|p.9,L36|0.010|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0682|p.9,L36|+0.456|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0683|p.9,L36|0.360|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0684|p.9,L36|0.552|gpt-6.1-sol +0.434 [0.354, 0.520] −0.493 [−0.566, −0.423] −0.233 [−0.292, −0.178] −0.039 [−0.088, 0.010] +0.456 [0.360, 0.552]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0685|p.9,L37|6|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0686|p.9,L37|+0.452|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0687|p.9,L37|0.364|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0688|p.9,L37|0.539|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0689|p.9,L37|−0.493|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0690|p.9,L37|−0.562|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0691|p.9,L37|−0.426|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0692|p.9,L37|−0.201|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0693|p.9,L37|−0.261|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0694|p.9,L37|−0.145|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0695|p.9,L37|−0.037|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0696|p.9,L37|−0.087|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0697|p.9,L37|0.014|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0698|p.9,L37|+0.424|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0699|p.9,L37|0.329|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0700|p.9,L37|0.522|gpt-6-astra +0.452 [0.364, 0.539] −0.493 [−0.562, −0.426] −0.201 [−0.261, −0.145] −0.037 [−0.087, 0.014] +0.424 [0.329, 0.522]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0701|p.9,L38|3.8|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0702|p.9,L38|+0.489|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0703|p.9,L38|0.407|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0704|p.9,L38|0.566|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0705|p.9,L38|−0.521|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0706|p.9,L38|−0.596|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0707|p.9,L38|−0.446|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0708|p.9,L38|−0.201|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0709|p.9,L38|−0.259|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0710|p.9,L38|−0.143|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0711|p.9,L38|−0.018|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0712|p.9,L38|−0.065|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0713|p.9,L38|0.029|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0714|p.9,L38|+0.470|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0715|p.9,L38|0.380|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0716|p.9,L38|0.560|gemini-3.8-flash +0.489 [0.407, 0.566] −0.521 [−0.596, −0.446] −0.201 [−0.259, −0.143] −0.018 [−0.065, 0.029] +0.470 [0.380, 0.560]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0717|p.9,L39|5|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0718|p.9,L39|4B|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0719|p.9,L39|+0.420|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0720|p.9,L39|0.338|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0721|p.9,L39|0.498|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0722|p.9,L39|−0.324|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0723|p.9,L39|−0.398|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0724|p.9,L39|−0.249|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0725|p.9,L39|−0.118|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0726|p.9,L39|−0.171|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0727|p.9,L39|−0.070|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0728|p.9,L39|+0.091|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0729|p.9,L39|0.035|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0730|p.9,L39|0.148|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0731|p.9,L39|+0.599|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0732|p.9,L39|0.503|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0733|p.9,L39|0.695|Qwen3.5-4B (base) +0.420 [0.338, 0.498] −0.324 [−0.398, −0.249] −0.118 [−0.171, −0.070] +0.091 [0.035, 0.148] +0.599 [0.503, 0.695]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0734|p.9,L40|1.5|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0735|p.9,L40|4B|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0736|p.9,L40|+0.475|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0737|p.9,L40|0.391|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0738|p.9,L40|0.556|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0739|p.9,L40|−0.447|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0740|p.9,L40|−0.518|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0741|p.9,L40|−0.376|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0742|p.9,L40|−0.163|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0743|p.9,L40|−0.223|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0744|p.9,L40|−0.104|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0745|p.9,L40|+0.176|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0746|p.9,L40|0.116|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0747|p.9,L40|0.235|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0748|p.9,L40|+0.988|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0749|p.9,L40|0.878|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0750|p.9,L40|1.099|MedGemma 1.5 4B +0.475 [0.391, 0.556] −0.447 [−0.518, −0.376] −0.163 [−0.223, −0.104] +0.176 [0.116, 0.235] +0.988 [0.878, 1.099]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0751|p.9,L43|6|Table 6: Main test by imaging type: ESG / erased-lesion claims (fraction) / net utility.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0752|p.9,L45|4B|Imaging (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0753|p.9,L45|4|Imaging (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0754|p.9,L45|5.5|Imaging (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0755|p.9,L45|6|Imaging (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0756|p.9,L46|174|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0757|p.9,L46|0.95|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0758|p.9,L46|0.01|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0759|p.9,L46|1.06|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0760|p.9,L46|0.69|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0761|p.9,L46|0.31|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0762|p.9,L46|0.83|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0763|p.9,L46|0.57|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0764|p.9,L46|0.40|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0765|p.9,L46|0.53|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0766|p.9,L46|0.40|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0767|p.9,L46|0.58|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0768|p.9,L46|0.40|Colonoscopy (174) 0.95 / 0.01 / 1.06 0.69 / 0.31 / 0.83 0.57 / 0.40 / 0.53 0.40 / 0.58 / 0.40|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0769|p.9,L47|78|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0770|p.9,L47|0.75|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0771|p.9,L47|0.14|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0772|p.9,L47|0.75|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0773|p.9,L47|0.42|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0774|p.9,L47|0.47|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0775|p.9,L47|0.56|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0776|p.9,L47|0.31|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0777|p.9,L47|0.61|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0778|p.9,L47|0.51|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0779|p.9,L47|0.50|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0780|p.9,L47|0.31|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0781|p.9,L47|0.43|Brain MRI (78) 0.75 / 0.14 / 0.75 0.42 / 0.47 / 0.56 0.31 / 0.61 / 0.51 0.50 / 0.31 / 0.43|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0782|p.9,L48|57|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0783|p.9,L48|0.74|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0784|p.9,L48|0.14|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0785|p.9,L48|0.78|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0786|p.9,L48|0.40|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0787|p.9,L48|0.48|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0788|p.9,L48|0.53|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0789|p.9,L48|0.29|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0790|p.9,L48|0.62|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0791|p.9,L48|0.40|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0792|p.9,L48|0.12|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0793|p.9,L48|0.83|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0794|p.9,L48|0.28|Breast ultrasound (57) 0.74 / 0.14 / 0.78 0.40 / 0.48 / 0.53 0.29 / 0.62 / 0.40 0.12 / 0.83 / 0.28|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0795|p.9,L49|91|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0796|p.9,L49|0.51|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0797|p.9,L49|0.17|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0798|p.9,L49|0.40|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0799|p.9,L49|0.20|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0800|p.9,L49|0.49|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0801|p.9,L49|0.21|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0802|p.9,L49|−0.05|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0803|p.9,L49|0.66|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0804|p.9,L49|−0.12|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0805|p.9,L49|0.15|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0806|p.9,L49|0.66|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0807|p.9,L49|0.14|Chest X-ray (91) 0.51 / 0.17 / 0.40 0.20 / 0.49 / 0.21 −0.05 / 0.66 / −0.12 0.15 / 0.66 / 0.14|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0808|p.9,L50|107|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0809|p.9,L50|0.47|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0810|p.9,L50|0.12|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0811|p.9,L50|0.22|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0812|p.9,L50|0.35|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0813|p.9,L50|0.41|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0814|p.9,L50|0.38|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0815|p.9,L50|0.24|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0816|p.9,L50|0.59|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0817|p.9,L50|0.32|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0818|p.9,L50|0.29|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0819|p.9,L50|0.47|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0820|p.9,L50|0.17|SLAKE CT/MRI (107) 0.47 / 0.12 / 0.22 0.35 / 0.41 / 0.38 0.24 / 0.59 / 0.32 0.29 / 0.47 / 0.17|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0821|p.9,L55|0.215|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0822|p.9,L55|0.735|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0823|p.9,L55|+0.521|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0824|p.9,L55|0.440|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0825|p.9,L55|0.600|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0826|p.9,L55|0.001|equals the recipe’s leaves ESG at 0.215 (recipe 0.735; difference +0.521 [0.440, 0.600], p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0827|p.9,L57|0.708|similar ESG on the main test (0.708 vs 0.735, p = 0.37) by denying more: it claims fewer erased lesions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0828|p.9,L57|0.735|similar ESG on the main test (0.708 vs 0.735, p = 0.37) by denying more: it claims fewer erased lesions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0829|p.9,L57|0.37|similar ESG on the main test (0.708 vs 0.735, p = 0.37) by denying more: it claims fewer erased lesions|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0830|p.9,L58|6.8%|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0831|p.9,L58|11.9%|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0832|p.9,L58|0.019|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0833|p.9,L58|0.788|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0834|p.9,L58|0.847|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0835|p.9,L58|0.002|(6.8% vs 11.9%, p = 0.019) but is less accurate on real lesions (CCR 0.788 vs 0.847, p = 0.002). The cost|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0836|p.9,L59|43%|shows on an unseen tool: after a Telea edit elsewhere it denies the intact lesion in 43% of cases (recipe|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0837|p.9,L60|23%|23%, p &lt; 0.001), so without the control a model partly learns to react to edits (Section 5.4).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0838|p.9,L60|0.001|23%, p &lt; 0.001), so without the control a model partly learns to react to edits (Section 5.4).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0839|p.9,L60|5.4|23%, p &lt; 0.001), so without the control a model partly learns to react to edits (Section 5.4).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0840|p.9,L61|1.5|It replicates on a second base model. The same recipe on MedGemma 1.5 4B gives ESG 0.721 vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0841|p.9,L61|4B|It replicates on a second base model. The same recipe on MedGemma 1.5 4B gives ESG 0.721 vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0842|p.9,L61|0.721|It replicates on a second base model. The same recipe on MedGemma 1.5 4B gives ESG 0.721 vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0843|p.10,L1|7|Table 7: Stage-1 arms on the main test (507 cases). Three-seed arms: mean ± sd.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0844|p.10,L1|1|Table 7: Stage-1 arms on the main test (507 cases). Three-seed arms: mean ± sd.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0845|p.10,L1|507|Table 7: Stage-1 arms on the main test (507 cases). Three-seed arms: mean ± sd.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0846|p.10,L1|Three|Table 7: Stage-1 arms on the main test (507 cases). Three-seed arms: mean ± sd.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0847|p.10,L4|5|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0848|p.10,L4|4B|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0849|p.10,L4|3|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0850|p.10,L4|0.871|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0851|p.10,L4|0.022|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0852|p.10,L4|0.741|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0853|p.10,L4|0.019|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0854|p.10,L4|13.2|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0855|p.10,L4|3.2|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0856|p.10,L4|13.9|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0857|p.10,L4|4.0|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0858|p.10,L4|0.684|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0859|p.10,L4|0.021|Qwen3.5-4B, with counterfactual views (3 seeds) 0.871 ± 0.022 0.741 ± 0.019 13.2 ± 3.2 13.9 ± 4.0 0.684 ± 0.021|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0860|p.10,L5|5|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0861|p.10,L5|4B|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0862|p.10,L5|3|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0863|p.10,L5|0.955|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0864|p.10,L5|0.008|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0865|p.10,L5|0.279|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0866|p.10,L5|0.107|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0867|p.10,L5|67.6|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0868|p.10,L5|11.9|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0869|p.10,L5|35.9|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0870|p.10,L5|3.9|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0871|p.10,L5|0.341|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0872|p.10,L5|0.090|Qwen3.5-4B, without (3 seeds) 0.955 ± 0.008 0.279 ± 0.107 67.6 ± 11.9 35.9 ± 3.9 0.341 ± 0.090|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0873|p.10,L6|0|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0874|p.10,L6|0.945|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0875|p.10,L6|0.215|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0876|p.10,L6|73.5|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0877|p.10,L6|31.6|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0878|p.10,L6|0.321|Without, “absent” share matched (seed 0) 0.945 0.215 73.5 31.6 0.321|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0879|p.10,L7|0|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0880|p.10,L7|0.788|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0881|p.10,L7|0.708|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0882|p.10,L7|6.8|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0883|p.10,L7|5.9|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0884|p.10,L7|0.667|Erasures only (seed 0) 0.788 0.708 6.8 5.9 0.667|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0885|p.10,L8|1.5|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0886|p.10,L8|4B|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0887|p.10,L8|0.806|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0888|p.10,L8|0.721|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0889|p.10,L8|7.8|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0890|p.10,L8|5.9|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0891|p.10,L8|0.698|MedGemma 1.5 4B, with counterfactual views 0.806 0.721 7.8 5.9 0.698|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0892|p.10,L9|1.5|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0893|p.10,L9|4B|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0894|p.10,L9|0.947|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0895|p.10,L9|0.374|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0896|p.10,L9|57.5|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0897|p.10,L9|31.6|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0898|p.10,L9|0.409|MedGemma 1.5 4B, without 0.947 0.374 57.5 31.6 0.409|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0899|p.10,L10|1.5|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0900|p.10,L10|4B|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0901|p.10,L10|0.674|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0902|p.10,L10|0.283|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0903|p.10,L10|54.3|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0904|p.10,L10|24.0|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0905|p.10,L10|−0.255|MedGemma 1.5 4B, untrained 0.674 0.283 54.3 24.0 −0.255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0906|p.10,L12|8|Table 8: Edited views by inpainting tool, 125 cases: ESG / erased-lesion claims (%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0907|p.10,L12|125|Table 8: Edited views by inpainting tool, 125 cases: ESG / erased-lesion claims (%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0908|p.10,L15|4B|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0909|p.10,L15|0.752|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0910|p.10,L15|7.2|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0911|p.10,L15|0.720|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0912|p.10,L15|8.0|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0913|p.10,L15|0.664|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0914|p.10,L15|7.2|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0915|p.10,L15|0.640|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0916|p.10,L15|17.6|MedScope-4B 0.752 / 7.2 0.720 / 8.0 0.664 / 7.2 0.640 / 17.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0917|p.10,L16|4|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0918|p.10,L16|0.536|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0919|p.10,L16|32.8|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0920|p.10,L16|0.488|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0921|p.10,L16|32.8|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0922|p.10,L16|0.560|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0923|p.10,L16|8.8|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0924|p.10,L16|0.392|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0925|p.10,L16|40.0|gemini-4-argon 0.536 / 32.8 0.488 / 32.8 0.560 / 8.8 0.392 / 40.0|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0926|p.10,L17|5.5|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0927|p.10,L17|0.376|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0928|p.10,L17|45.6|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0929|p.10,L17|0.264|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0930|p.10,L17|56.8|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0931|p.10,L17|0.296|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0932|p.10,L17|41.6|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0933|p.10,L17|0.352|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0934|p.10,L17|46.4|Claude Opus 5.5 0.376 / 45.6 0.264 / 56.8 0.296 / 41.6 0.352 / 46.4|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0935|p.10,L18|6|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0936|p.10,L18|0.312|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0937|p.10,L18|55.2|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0938|p.10,L18|0.240|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0939|p.10,L18|64.0|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0940|p.10,L18|0.256|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0941|p.10,L18|60.8|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0942|p.10,L18|0.256|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0943|p.10,L18|61.6|gpt-6-astra 0.312 / 55.2 0.240 / 64.0 0.256 / 60.8 0.256 / 61.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0944|p.10,L19|1|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0945|p.10,L19|0.720|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0946|p.10,L19|12.0|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0947|p.10,L19|0.744|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0948|p.10,L19|8.0|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0949|p.10,L19|0.696|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0950|p.10,L19|7.2|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0951|p.10,L19|0.568|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0952|p.10,L19|24.8|Stage 1, with counterfactual views 0.720 / 12.0 0.744 / 8.0 0.696 / 7.2 0.568 / 24.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0953|p.10,L20|1|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0954|p.10,L20|0.688|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0955|p.10,L20|7.2|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0956|p.10,L20|0.656|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0957|p.10,L20|4.8|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0958|p.10,L20|0.544|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0959|p.10,L20|2.4|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0960|p.10,L20|0.712|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0961|p.10,L20|4.8|Stage 1, erasures only 0.688 / 7.2 0.656 / 4.8 0.544 / 2.4 0.712 / 4.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0962|p.10,L21|1|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0963|p.10,L21|0.272|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0964|p.10,L21|69.6|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0965|p.10,L21|0.200|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0966|p.10,L21|76.8|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0967|p.10,L21|0.144|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0968|p.10,L21|83.2|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0969|p.10,L21|0.232|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0970|p.10,L21|73.6|Stage 1, without counterfactual views 0.272 / 69.6 0.200 / 76.8 0.144 / 83.2 0.232 / 73.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0971|p.10,L22|1|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0972|p.10,L22|0.224|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0973|p.10,L22|72.0|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0974|p.10,L22|0.208|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0975|p.10,L22|73.6|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0976|p.10,L22|0.096|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0977|p.10,L22|85.6|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0978|p.10,L22|0.184|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0979|p.10,L22|77.6|Stage 1, without, “absent” share matched 0.224 / 72.0 0.208 / 73.6 0.096 / 85.6 0.184 / 77.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0980|p.10,L26|0.374|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0981|p.10,L26|+0.347|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0982|p.10,L26|0.276|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0983|p.10,L26|0.425|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0984|p.10,L26|0.001|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0985|p.10,L26|7.8%|0.374 without counterfactual views (+0.347 [0.276, 0.425], p &lt; 0.001) and erased-lesion claims 7.8% vs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0986|p.10,L27|57.5%|57.5%. With counterfactual views the two base models do not differ (net utility −0.005, p = 0.83; ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0987|p.10,L27|two|57.5%. With counterfactual views the two base models do not differ (net utility −0.005, p = 0.83; ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0988|p.10,L27|−0.005|57.5%. With counterfactual views the two base models do not differ (net utility −0.005, p = 0.83; ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0989|p.10,L27|0.83|57.5%. With counterfactual views the two base models do not differ (net utility −0.005, p = 0.83; ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0990|p.10,L28|+0.014|+0.014, p = 0.73).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0991|p.10,L28|0.73|+0.014, p = 0.73).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0992|p.10,L29|2|Stages 2 and 3 add little on the main test. The final model against its own stage 1: net utility +0.040|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0993|p.10,L29|3|Stages 2 and 3 add little on the main test. The final model against its own stage 1: net utility +0.040|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0994|p.10,L29|1|Stages 2 and 3 add little on the main test. The final model against its own stage 1: net utility +0.040|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0995|p.10,L29|+0.040|Stages 2 and 3 add little on the main test. The final model against its own stage 1: net utility +0.040|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0996|p.10,L30|0.15|(p = 0.15), ESG +0.023 (p = 0.39), healthy-image claims −1.7 points (p = 0.35). Their contribution is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0997|p.10,L30|+0.023|(p = 0.15), ESG +0.023 (p = 0.39), healthy-image claims −1.7 points (p = 0.35). Their contribution is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0998|p.10,L30|0.39|(p = 0.15), ESG +0.023 (p = 0.39), healthy-image claims −1.7 points (p = 0.35). Their contribution is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N0999|p.10,L30|−1.7|(p = 0.15), ESG +0.023 (p = 0.39), healthy-image claims −1.7 points (p = 0.35). Their contribution is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1000|p.10,L30|0.35|(p = 0.15), ESG +0.023 (p = 0.39), healthy-image claims −1.7 points (p = 0.35). Their contribution is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1001|p.10,L31|13.6%|on validation healthy-image claims, which the selection rule used (13.6% → 7.7%), and on ordinary VQA|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1002|p.10,L31|7.7%|on validation healthy-image claims, which the selection rule used (13.6% → 7.7%), and on ordinary VQA|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1003|p.10,L32|5.6|questions (Section 5.6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1004|p.10,L33|three|The recipe’s effect also holds at the external centres (three seeds: ESG 0.622 ± 0.030 vs 0.389 ± 0.043;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1005|p.10,L33|0.622|The recipe’s effect also holds at the external centres (three seeds: ESG 0.622 ± 0.030 vs 0.389 ± 0.043;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1006|p.10,L33|0.030|The recipe’s effect also holds at the external centres (three seeds: ESG 0.622 ± 0.030 vs 0.389 ± 0.043;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1007|p.10,L33|0.389|The recipe’s effect also holds at the external centres (three seeds: ESG 0.622 ± 0.030 vs 0.389 ± 0.043;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1008|p.10,L33|0.043|The recipe’s effect also holds at the external centres (three seeds: ESG 0.622 ± 0.030 vs 0.389 ± 0.043;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1009|p.10,L34|14.6%|erased-lesion claims 14.6% vs 48.2%; healthy-image claims 9.3% vs 49.3%) and on the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1010|p.10,L34|48.2%|erased-lesion claims 14.6% vs 48.2%; healthy-image claims 9.3% vs 49.3%) and on the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1011|p.10,L34|9.3%|erased-lesion claims 14.6% vs 48.2%; healthy-image claims 9.3% vs 49.3%) and on the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1012|p.10,L34|49.3%|erased-lesion claims 14.6% vs 48.2%; healthy-image claims 9.3% vs 49.3%) and on the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1013|p.10,L35|0.070|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1014|p.10,L35|0.008|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1015|p.10,L35|−0.149|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1016|p.10,L35|0.033|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1017|p.10,L35|9.7%|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1018|p.10,L35|26.1%|test (net utility 0.070 ± 0.008 vs −0.149 ± 0.033; healthy-image claims 9.7% vs 26.1%), where the ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1019|p.10,L36|0.381|difference is smaller (0.381 vs 0.288) and significant on two of three seeds.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1020|p.10,L36|0.288|difference is smaller (0.381 vs 0.288) and significant on two of three seeds.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1021|p.10,L36|two|difference is smaller (0.381 vs 0.288) and significant on two of three seeds.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1022|p.10,L36|three|difference is smaller (0.381 vs 0.288) and significant on two of three seeds.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1023|p.10,L39|5.4|5.4 Does it read the lesion or the edit?|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1024|p.10,L40|4B|Every training erasure used LaMa or tissue transplant. If MedScope-4B had learned those tools’ traces, its|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1025|p.10,L41|125|advantage should vanish on other tools. We remade both edited views of 125 main-test cases on the same|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1026|p.10,L42|18|masks with Telea [18] and Stable Diffusion inpainting [20], neither used in training or selection, and with|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1027|p.10,L42|20|masks with Telea [18] and Stable Diffusion inpainting [20], neither used in training or selection, and with|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1028|p.10,L43|8|tissue transplant (Table 8).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1029|p.10,L44|4B|MedScope-4B beats all three flagships on every tool (ESG differences +0.10 to +0.48, p ≤ 0.049). On|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1030|p.10,L44|three|MedScope-4B beats all three flagships on every tool (ESG differences +0.10 to +0.48, p ≤ 0.049). On|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1031|p.10,L44|+0.10|MedScope-4B beats all three flagships on every tool (ESG differences +0.10 to +0.48, p ≤ 0.049). On|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1032|p.10,L44|+0.48|MedScope-4B beats all three flagships on every tool (ESG differences +0.10 to +0.48, p ≤ 0.049). On|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1033|p.10,L44|0.049|MedScope-4B beats all three flagships on every tool (ESG differences +0.10 to +0.48, p ≤ 0.049). On|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1034|p.10,L45|7.2%|Telea its erased-lesion claims are unchanged (7.2%; ESG −0.088, p = 0.025, from more denials after the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1035|p.10,L45|−0.088|Telea its erased-lesion claims are unchanged (7.2%; ESG −0.088, p = 0.025, from more denials after the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1036|p.10,L45|0.025|Telea its erased-lesion claims are unchanged (7.2%; ESG −0.088, p = 0.025, from more denials after the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1037|p.10,L46|10.4|edit elsewhere); on Stable Diffusion they rise by 10.4 points (p = 0.006), the largest drop, yet still two to|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1038|p.10,L46|0.006|edit elsewhere); on Stable Diffusion they rise by 10.4 points (p = 0.006), the largest drop, yet still two to|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1039|p.10,L46|two|edit elsewhere); on Stable Diffusion they rise by 10.4 points (p = 0.006), the largest drop, yet still two to|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1040|p.10,L47|four|four times below Claude Opus 5.5 and gpt-6-astra. The arms without counterfactual views stay near ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1041|p.10,L47|5.5|four times below Claude Opus 5.5 and gpt-6-astra. The arms without counterfactual views stay near ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1042|p.10,L47|6|four times below Claude Opus 5.5 and gpt-6-astra. The arms without counterfactual views stay near ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1043|p.10,L48|0.1|0.1–0.3 on every tool. gemini-4-argon’s erased-lesion claims fall from 33% to 9% on Telea only, whose|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1044|p.10,L48|0.3|0.1–0.3 on every tool. gemini-4-argon’s erased-lesion claims fall from 33% to 9% on Telea only, whose|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1045|p.10,L48|4|0.1–0.3 on every tool. gemini-4-argon’s erased-lesion claims fall from 33% to 9% on Telea only, whose|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1046|p.10,L48|33%|0.1–0.3 on every tool. gemini-4-argon’s erased-lesion claims fall from 33% to 9% on Telea only, whose|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1047|p.10,L48|9%|0.1–0.3 on every tool. gemini-4-argon’s erased-lesion claims fall from 33% to 9% on Telea only, whose|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1048|p.10,L50|4|Clean-looking erasures. Asked for the probability that an image was edited, gemini-4-argon’s ratings|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1049|p.10,L51|219|of the 219 erased views are bimodal (61 rated ≤ 0.20, 158 rated ≥ 0.75, none in between), so the split needs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1050|p.10,L51|61|of the 219 erased views are bimodal (61 rated ≤ 0.20, 158 rated ≥ 0.75, none in between), so the split needs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1051|p.10,L51|0.20|of the 219 erased views are bimodal (61 rated ≤ 0.20, 158 rated ≥ 0.75, none in between), so the split needs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1052|p.10,L51|158|of the 219 erased views are bimodal (61 rated ≤ 0.20, 158 rated ≥ 0.75, none in between), so the split needs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1053|p.10,L51|0.75|of the 219 erased views are bimodal (61 rated ≤ 0.20, 158 rated ≥ 0.75, none in between), so the split needs|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1054|p.10,L52|4B|no threshold choice. On erasures it rates as unedited, MedScope-4B still claims the lesion in only 15% (8%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1055|p.10,L52|15%|no threshold choice. On erasures it rates as unedited, MedScope-4B still claims the lesion in only 15% (8%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1056|p.10,L52|8%|no threshold choice. On erasures it rates as unedited, MedScope-4B still claims the lesion in only 15% (8%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1057|p.10,L53|41|on visible ones), against 41–64% for the nine frontier models, which claim the lesion as often on visible|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1058|p.10,L53|64%|on visible ones), against 41–64% for the nine frontier models, which claim the lesion as often on visible|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1059|p.10,L53|nine|on visible ones), against 41–64% for the nine frontier models, which claim the lesion as often on visible|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1060|p.10,L54|41|erasures (41–58%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1061|p.10,L54|58%|erasures (41–58%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1062|p.11,L1|1|1 0.91|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1063|p.11,L1|0.91|1 0.91|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1064|p.11,L2|0.84|0.84 MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1065|p.11,L2|4B|0.84 MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1066|p.11,L3|0.74|0.74|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1067|p.11,L4|0.75|0.75|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1068|p.11,L5|0.55|0.55|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1069|p.11,L9|0.5|0.5 gemini-4-argon|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1070|p.11,L9|4|0.5 gemini-4-argon|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1071|p.11,L10|5.5|Claude Opus 5.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1072|p.11,L12|0.25|0.25 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1073|p.11,L12|6|0.25 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1074|p.11,L17|0|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1075|p.11,L17|1.8%|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1076|p.11,L17|1.8|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1077|p.11,L17|4.2%|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1078|p.11,L17|4.2|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1079|p.11,L17|8.4%|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1080|p.11,L17|8.4|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1081|p.11,L17|20%|0–1.8% 1.8–4.2% 4.2–8.4% 8.4–20%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1082|p.11,L20|3|Figure 3: Evidence sensitivity gap by quartile of lesion area on the main test (55, 54, 55, 55 cases with a lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1083|p.11,L20|55|Figure 3: Evidence sensitivity gap by quartile of lesion area on the main test (55, 54, 55, 55 cases with a lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1084|p.11,L20|54|Figure 3: Evidence sensitivity gap by quartile of lesion area on the main test (55, 54, 55, 55 cases with a lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1085|p.11,L20|55|Figure 3: Evidence sensitivity gap by quartile of lesion area on the main test (55, 54, 55, 55 cases with a lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1086|p.11,L20|55|Figure 3: Evidence sensitivity gap by quartile of lesion area on the main test (55, 54, 55, 55 cases with a lesion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1087|p.11,L21|4B|mask). The gap between MedScope-4B and the flagships grows with lesion size but holds in the smallest quartile|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1088|p.11,L22|0.55|(0.55 vs 0.20–0.40).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1089|p.11,L22|0.20|(0.55 vs 0.20–0.40).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1090|p.11,L22|0.40|(0.55 vs 0.20–0.40).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1091|p.11,L24|9|Table 9: Flagships under four prompting conditions, same 150 cases: ESG / erased-lesion claims (%). MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1092|p.11,L24|four|Table 9: Flagships under four prompting conditions, same 150 cases: ESG / erased-lesion claims (%). MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1093|p.11,L24|150|Table 9: Flagships under four prompting conditions, same 150 cases: ESG / erased-lesion claims (%). MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1094|p.11,L24|4B|Table 9: Flagships under four prompting conditions, same 150 cases: ESG / erased-lesion claims (%). MedScope-4B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1095|p.11,L25|0.750|on these cases: 0.750 / 7.4.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1096|p.11,L25|7.4|on these cases: 0.750 / 7.4.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1097|p.11,L27|Four|Model Default Cautious prompt Four solved examples Highest reasoning|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1098|p.11,L28|4|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1099|p.11,L28|0.441|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1100|p.11,L28|41.2|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1101|p.11,L28|0.412|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1102|p.11,L28|42.6|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1103|p.11,L28|0.456|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1104|p.11,L28|36.8|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1105|p.11,L28|0.456|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1106|p.11,L28|39.7|gemini-4-argon 0.441 / 41.2 0.412 / 42.6 0.456 / 36.8 0.456 / 39.7|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1107|p.11,L29|5.5|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1108|p.11,L29|0.338|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1109|p.11,L29|54.4|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1110|p.11,L29|0.382|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1111|p.11,L29|44.1|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1112|p.11,L29|0.309|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1113|p.11,L29|52.9|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1114|p.11,L29|0.397|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1115|p.11,L29|51.5|Claude Opus 5.5 0.338 / 54.4 0.382 / 44.1 0.309 / 52.9 0.397 / 51.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1116|p.11,L30|6|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1117|p.11,L30|0.338|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1118|p.11,L30|52.9|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1119|p.11,L30|0.397|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1120|p.11,L30|47.1|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1121|p.11,L30|0.500|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1122|p.11,L30|38.2|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1123|p.11,L30|0.324|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1124|p.11,L30|58.8|gpt-6-astra 0.338 / 52.9 0.397 / 47.1 0.500 / 38.2 0.324 / 58.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1125|p.11,L34|18|Edit visibility. A ResNet-18 trained on 5,126 training views separates random-removal from original|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1126|p.11,L34|5,126|Edit visibility. A ResNet-18 trained on 5,126 training views separates random-removal from original|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1127|p.11,L35|0.83|views with AUC 0.83 [0.80, 0.87], so the inpainting leaves a trace that a trained detector can find. Zero-shot,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1128|p.11,L35|0.80|views with AUC 0.83 [0.80, 0.87], so the inpainting leaves a trace that a trained detector can find. Zero-shot,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1129|p.11,L35|0.87|views with AUC 0.83 [0.80, 0.87], so the inpainting leaves a trace that a trained detector can find. Zero-shot,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1130|p.11,L35|Zero|views with AUC 0.83 [0.80, 0.87], so the inpainting leaves a trace that a trained detector can find. Zero-shot,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1131|p.11,L36|4|gemini-4-argon and gpt-6.1-sol cannot separate random-removal views from originals (AUC 0.52–0.55) but|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1132|p.11,L36|6.1|gemini-4-argon and gpt-6.1-sol cannot separate random-removal views from originals (AUC 0.52–0.55) but|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1133|p.11,L36|0.52|gemini-4-argon and gpt-6.1-sol cannot separate random-removal views from originals (AUC 0.52–0.55) but|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1134|p.11,L36|0.55|gemini-4-argon and gpt-6.1-sol cannot separate random-removal views from originals (AUC 0.52–0.55) but|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1135|p.11,L37|0.70|find erased-lesion views suspicious (0.70–0.75): erasing a lesion leaves a smooth region where structure is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1136|p.11,L37|0.75|find erased-lesion views suspicious (0.70–0.75): erasing a lesion leaves a smooth region where structure is|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1137|p.11,L39|Four|Four results argue that MedScope’s answers follow the lesion rather than edit traces: (i) an edit detector|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1138|p.11,L40|0|scores ESG 0 by construction, and MedScope-4B denies the lesion on only 14.6% of random-removal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1139|p.11,L40|4B|scores ESG 0 by construction, and MedScope-4B denies the lesion on only 14.6% of random-removal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1140|p.11,L40|14.6%|scores ESG 0 by construction, and MedScope-4B denies the lesion on only 14.6% of random-removal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1141|p.11,L43|18|ResNet-18 learns; (iii) the advantage holds on clean-looking erasures and on two unseen tools; (iv) on|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1142|p.11,L43|two|ResNet-18 learns; (iii) the advantage holds on clean-looking erasures and on two unseen tools; (iv) on|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1143|p.11,L45|35.9%|from 35.9% to 13.9% (Table 7).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1144|p.11,L45|13.9%|from 35.9% to 13.9% (Table 7).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1145|p.11,L45|7|from 35.9% to 13.9% (Table 7).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1146|p.11,L48|5.5|5.5 Robustness|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1147|p.11,L50|3|ure 3; erased-lesion claims 18.2% in the smallest quartile and 1.8% in the largest). The flagships show no|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1148|p.11,L50|18.2%|ure 3; erased-lesion claims 18.2% in the smallest quartile and 1.8% in the largest). The flagships show no|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1149|p.11,L50|1.8%|ure 3; erased-lesion claims 18.2% in the smallest quartile and 1.8% in the largest). The flagships show no|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1150|p.11,L51|0.20|such trend: their ESG stays between 0.20 and 0.56 in every quartile, and gpt-6-astra claims a large erased|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1151|p.11,L51|0.56|such trend: their ESG stays between 0.20 and 0.56 in every quartile, and gpt-6-astra claims a large erased|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1152|p.11,L51|6|such trend: their ESG stays between 0.20 and 0.56 in every quartile, and gpt-6-astra claims a large erased|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1153|p.11,L52|75%|lesion in 75% of cases.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1154|p.11,L53|thousands|Prompting the frontier models harder. MedScope learned from thousands of counterfactual views;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1155|p.11,L54|150|the frontier models saw none. On the same 150 cases we gave the three flagships a cautious prompt (an|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1156|p.11,L54|three|the frontier models saw none. On the same 150 cases we gave the three flagships a cautious prompt (an|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1157|p.11,L55|four|explicit warning that the question may name an absent finding), four solved training examples in context (a|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1158|p.11,L57|9|reasoning setting. None closes the gap (Table 9). At the highest reasoning setting no flagship differs from|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1159|p.11,L58|0.13|its default (all p ≥ 0.13). MedScope-4B stays better than every flagship under every condition on ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1160|p.11,L58|4B|its default (all p ≥ 0.13). MedScope-4B stays better than every flagship under every condition on ESG|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1161|p.11,L59|0.001|(p ≤ 0.001) and net utility (p ≤ 0.034).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1162|p.11,L59|0.034|(p ≤ 0.001) and net utility (p ≤ 0.034).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1163|p.12,L1|10|Table 10: MedScope-4B and the three flagships on the further test sets.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1164|p.12,L1|4B|Table 10: MedScope-4B and the three flagships on the further test sets.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1165|p.12,L1|three|Table 10: MedScope-4B and the three flagships on the further test sets.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1166|p.12,L4|4B|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1167|p.12,L4|0.727|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1168|p.12,L4|0.597|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1169|p.12,L4|11.8|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1170|p.12,L4|4.0|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1171|p.12,L4|0.530|MedScope-4B 0.727 0.597 11.8 4.0 0.530|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1172|p.12,L5|4|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1173|p.12,L5|0.950|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1174|p.12,L5|0.370|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1175|p.12,L5|58.8|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1176|p.12,L5|18.0|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1177|p.12,L5|0.544|gemini-4-argon 0.950 0.370 58.8 18.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1178|p.12,L6|169|External centres (169)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1179|p.12,L7|5.5|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1180|p.12,L7|0.966|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1181|p.12,L7|0.412|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1182|p.12,L7|53.8|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1183|p.12,L7|30.0|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1184|p.12,L7|0.544|Claude Opus 5.5 0.966 0.412 53.8 30.0 0.544|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1185|p.12,L8|6|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1186|p.12,L8|0.945|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1187|p.12,L8|0.277|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1188|p.12,L8|66.4|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1189|p.12,L8|24.0|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1190|p.12,L8|0.424|gpt-6-astra 0.945 0.277 66.4 24.0 0.424|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1191|p.12,L9|4B|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1192|p.12,L9|0.681|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1193|p.12,L9|0.472|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1194|p.12,L9|19.4|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1195|p.12,L9|12.5|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1196|p.12,L9|0.402|MedScope-4B 0.681 0.472 19.4 12.5 0.402|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1197|p.12,L10|4|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1198|p.12,L10|0.639|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1199|p.12,L10|0.056|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1200|p.12,L10|61.1|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1201|p.12,L10|12.5|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1202|p.12,L10|0.048|gemini-4-argon 0.639 0.056 61.1 12.5 0.048|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1203|p.12,L11|76|Fresh internal (76)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1204|p.12,L12|5.5|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1205|p.12,L12|0.653|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1206|p.12,L12|0.000|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1207|p.12,L12|63.9|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1208|p.12,L12|25.0|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1209|p.12,L12|−0.023|Claude Opus 5.5 0.653 0.000 63.9 25.0 −0.023|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1210|p.12,L13|6|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1211|p.12,L13|0.847|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1212|p.12,L13|0.083|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1213|p.12,L13|75.0|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1214|p.12,L13|17.5|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1215|p.12,L13|0.219|gpt-6-astra 0.847 0.083 75.0 17.5 0.219|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1216|p.12,L14|4B|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1217|p.12,L14|0.476|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1218|p.12,L14|0.393|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1219|p.12,L14|8.3|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1220|p.12,L14|4.7|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1221|p.12,L14|−0.053|MedScope-4B 0.476 0.393 8.3 4.7 −0.053|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1222|p.12,L15|4|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1223|p.12,L15|0.741|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1224|p.12,L15|0.435|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1225|p.12,L15|31.5|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1226|p.12,L15|9.5|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1227|p.12,L15|0.310|gemini-4-argon 0.741 0.435 31.5 9.5 0.310|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1228|p.12,L16|316|Fresh external (316)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1229|p.12,L17|5.5|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1230|p.12,L17|0.696|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1231|p.12,L17|0.292|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1232|p.12,L17|42.3|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1233|p.12,L17|18.9|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1234|p.12,L17|0.056|Claude Opus 5.5 0.696 0.292 42.3 18.9 0.056|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1235|p.12,L18|6|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1236|p.12,L18|0.634|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1237|p.12,L18|0.268|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1238|p.12,L18|35.7|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1239|p.12,L18|34.5|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1240|p.12,L18|−0.106|gpt-6-astra 0.634 0.268 35.7 34.5 −0.106|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1241|p.12,L22|one|Open models with their own prompt. With a short native prompt and one plain reply, every open|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1242|p.12,L23|53|model claims erased lesions more often than under the agent prompt (53–72%) [regenerate with the v4-era|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1243|p.12,L23|72%|model claims erased lesions more often than under the agent prompt (53–72%) [regenerate with the v4-era|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1244|p.12,L25|373|Question wording. On 373 cases with three test-only paraphrases, net utility is unchanged against the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1245|p.12,L25|three|Question wording. On 373 cases with three test-only paraphrases, net utility is unchanged against the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1246|p.12,L26|+0.006|original wording (+0.006 [−0.033, 0.041], p = 0.74). With the same paraphrases on 150 cases, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1247|p.12,L26|−0.033|original wording (+0.006 [−0.033, 0.041], p = 0.74). With the same paraphrases on 150 cases, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1248|p.12,L26|0.041|original wording (+0.006 [−0.033, 0.041], p = 0.74). With the same paraphrases on 150 cases, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1249|p.12,L26|0.74|original wording (+0.006 [−0.033, 0.041], p = 0.74). With the same paraphrases on 150 cases, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1250|p.12,L26|150|original wording (+0.006 [−0.033, 0.041], p = 0.74). With the same paraphrases on 150 cases, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1251|p.12,L27|4B|4B leads the flagships by +0.35 to +0.57 in net utility (p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1252|p.12,L27|+0.35|4B leads the flagships by +0.35 to +0.57 in net utility (p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1253|p.12,L27|+0.57|4B leads the flagships by +0.35 to +0.57 in net utility (p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1254|p.12,L27|0.001|4B leads the flagships by +0.35 to +0.57 in net utility (p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1255|p.12,L28|0.753|Tools off. With every tool call refused at test time, ESG is unchanged (0.753 vs 0.758, p = 0.92) and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1256|p.12,L28|0.758|Tools off. With every tool call refused at test time, ESG is unchanged (0.753 vs 0.758, p = 0.92) and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1257|p.12,L28|0.92|Tools off. With every tool call refused at test time, ESG is unchanged (0.753 vs 0.758, p = 0.92) and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1258|p.12,L29|0.092|net utility falls by 0.092 (p = 0.003): the model says “absent” more often on lesion views (21% vs 15%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1259|p.12,L29|0.003|net utility falls by 0.092 (p = 0.003): the model says “absent” more often on lesion views (21% vs 15%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1260|p.12,L29|21%|net utility falls by 0.092 (p = 0.003): the model says “absent” more often on lesion views (21% vs 15%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1261|p.12,L29|15%|net utility falls by 0.092 (p = 0.003): the model says “absent” more often on lesion views (21% vs 15%).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1262|p.12,L30|4B|Evidence sensitivity comes from training; the tools add accuracy on real lesions. MedScope-4B calls a tool|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1263|p.12,L31|0.99|on 0.99 of lesion views (35% of calls are windowing), and its first zoom covers the lesion in 93%. gpt-6-sol|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1264|p.12,L31|35%|on 0.99 of lesion views (35% of calls are windowing), and its first zoom covers the lesion in 93%. gpt-6-sol|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1265|p.12,L31|93%|on 0.99 of lesion views (35% of calls are windowing), and its first zoom covers the lesion in 93%. gpt-6-sol|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1266|p.12,L31|6|on 0.99 of lesion views (35% of calls are windowing), and its first zoom covers the lesion in 93%. gpt-6-sol|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1267|p.12,L32|6|and gpt-6-astra almost never call a tool.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1268|p.12,L33|+0.110|Cost matrix. The always-refer policy earns +0.110 under the published matrix, a weakness of that|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1269|p.12,L34|0|matrix; with referral on lesion-free images paid 0 it earns −0.118, and −0.300 when referral costs −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1270|p.12,L34|−0.118|matrix; with referral on lesion-free images paid 0 it earns −0.118, and −0.300 when referral costs −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1271|p.12,L34|−0.300|matrix; with referral on lesion-free images paid 0 it earns −0.118, and −0.300 when referral costs −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1272|p.12,L34|−0.3|matrix; with referral on lesion-free images paid 0 it earns −0.118, and −0.300 when referral costs −0.3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1273|p.12,L35|4B|everywhere. MedScope-4B ranks first among all models under all five matrices (wrong-answer penalty −2,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1274|p.12,L35|five|everywhere. MedScope-4B ranks first among all models under all five matrices (wrong-answer penalty −2,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1275|p.12,L35|−2|everywhere. MedScope-4B ranks first among all models under all five matrices (wrong-answer penalty −2,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1276|p.12,L36|−1|−1, −0.5; the two referral variants), and its strict ESG equals its ESG (0.758), since it never refers.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1277|p.12,L36|−0.5|−1, −0.5; the two referral variants), and its strict ESG equals its ESG (0.758), since it never refers.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1278|p.12,L36|two|−1, −0.5; the two referral variants), and its strict ESG equals its ESG (0.758), since it never refers.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1279|p.12,L36|0.758|−1, −0.5; the two referral variants), and its strict ESG equals its ESG (0.758), since it never refers.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1280|p.12,L38|0.774|0.774 for MedScope-4B and 0.310–0.579 for the flagships (MedScope better, p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1281|p.12,L38|4B|0.774 for MedScope-4B and 0.310–0.579 for the flagships (MedScope better, p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1282|p.12,L38|0.310|0.774 for MedScope-4B and 0.310–0.579 for the flagships (MedScope better, p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1283|p.12,L38|0.579|0.774 for MedScope-4B and 0.310–0.579 for the flagships (MedScope better, p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1284|p.12,L38|0.001|0.774 for MedScope-4B and 0.310–0.579 for the flagships (MedScope better, p &lt; 0.001).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1285|p.12,L39|nine|Label noise. Without human review, the nine frontier models served as an independent panel: a lesion-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1286|p.12,L40|seven|free test image that at least seven call abnormal is treated as a disputed label (26 of 288: 12 colonoscopy,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1287|p.12,L40|26|free test image that at least seven call abnormal is treated as a disputed label (26 of 288: 12 colonoscopy,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1288|p.12,L40|288|free test image that at least seven call abnormal is treated as a disputed label (26 of 288: 12 colonoscopy,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1289|p.12,L40|12|free test image that at least seven call abnormal is treated as a disputed label (26 of 288: 12 colonoscopy,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1290|p.12,L41|11|11 SLAKE, 2 breast ultrasound, 1 chest X-ray; MedScope does not vote). Without them, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1291|p.12,L41|2|11 SLAKE, 2 breast ultrasound, 1 chest X-ray; MedScope does not vote). Without them, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1292|p.12,L41|1|11 SLAKE, 2 breast ultrasound, 1 chest X-ray; MedScope does not vote). Without them, MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1293|p.12,L42|4B|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1294|p.12,L42|6.9%|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1295|p.12,L42|4|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1296|p.12,L42|4.6%|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1297|p.12,L42|10.3|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1298|p.12,L42|24.4%|4B’s healthy-image claims are 6.9% (gemini-4-argon 4.6%, other frontier models 10.3–24.4%), and every|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1299|p.12,L43|5|comparison in Table 5 keeps its direction and significance.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1300|p.12,L46|5.6|5.6 Generalisation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1301|p.12,L47|4B|On every new test set MedScope-4B keeps the lowest erased-lesion claims and the lowest (once tied)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1302|p.12,L48|four|healthy-image claims of the four models, but the flagships detect more real lesions (Table 10). Net util-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1303|p.12,L48|10|healthy-image claims of the four models, but the flagships detect more real lesions (Table 10). Net util-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1304|p.12,L49|4B|ity, which weighs both, does not differ at the external centres, favours MedScope-4B on the fresh internal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1305|p.12,L50|4|set, and favours gemini-4-argon on the fresh external set.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1306|p.12,L51|0.002|External centres. ESG is higher than every flagship’s (p ≤ 0.002), erased-lesion claims are 42–55|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1307|p.12,L51|42|External centres. ESG is higher than every flagship’s (p ≤ 0.002), erased-lesion claims are 42–55|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1308|p.12,L51|55|External centres. ESG is higher than every flagship’s (p ≤ 0.002), erased-lesion claims are 42–55|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1309|p.12,L52|0.001|points lower (p &lt; 0.001) and healthy-image claims 14–26 points lower (p ≤ 0.026), while CCR is 0.22–|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1310|p.12,L52|14|points lower (p &lt; 0.001) and healthy-image claims 14–26 points lower (p ≤ 0.026), while CCR is 0.22–|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1311|p.12,L52|26|points lower (p &lt; 0.001) and healthy-image claims 14–26 points lower (p ≤ 0.026), while CCR is 0.22–|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1312|p.12,L52|0.026|points lower (p &lt; 0.001) and healthy-image claims 14–26 points lower (p ≤ 0.026), while CCR is 0.22–|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1313|p.12,L52|0.22|points lower (p &lt; 0.001) and healthy-image claims 14–26 points lower (p ≤ 0.026), while CCR is 0.22–|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1314|p.12,L53|0.24|0.24 lower (p &lt; 0.001); net utility does not differ (p ≥ 0.07). By source, ESG is 0.85 on CVC-ClinicDB,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1315|p.12,L53|0.001|0.24 lower (p &lt; 0.001); net utility does not differ (p ≥ 0.07). By source, ESG is 0.85 on CVC-ClinicDB,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1316|p.12,L53|0.07|0.24 lower (p &lt; 0.001); net utility does not differ (p ≥ 0.07). By source, ESG is 0.85 on CVC-ClinicDB,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1317|p.12,L53|0.85|0.24 lower (p &lt; 0.001); net utility does not differ (p ≥ 0.07). By source, ESG is 0.85 on CVC-ClinicDB,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1318|p.12,L54|0.71|0.71 on BraTS-Africa, 0.58 on BUS-BRA and 0.05 on QaTa-COV19, where diffuse COVID-19 opacities|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1319|p.12,L54|0.58|0.71 on BraTS-Africa, 0.58 on BUS-BRA and 0.05 on QaTa-COV19, where diffuse COVID-19 opacities|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1320|p.12,L54|0.05|0.71 on BraTS-Africa, 0.58 on BUS-BRA and 0.05 on QaTa-COV19, where diffuse COVID-19 opacities|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1321|p.12,L54|19|0.71 on BraTS-Africa, 0.58 on BUS-BRA and 0.05 on QaTa-COV19, where diffuse COVID-19 opacities|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1322|p.12,L56|0.47|Fresh internal (confirmatory, chest X-ray). ESG 0.47 against 0.00–0.08 for the flagships (p ≤ 0.001);|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1323|p.12,L56|0.00|Fresh internal (confirmatory, chest X-ray). ESG 0.47 against 0.00–0.08 for the flagships (p ≤ 0.001);|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1324|p.12,L56|0.08|Fresh internal (confirmatory, chest X-ray). ESG 0.47 against 0.00–0.08 for the flagships (p ≤ 0.001);|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1325|p.12,L56|0.001|Fresh internal (confirmatory, chest X-ray). ESG 0.47 against 0.00–0.08 for the flagships (p ≤ 0.001);|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1326|p.13,L1|11|Table 11: Fresh external test by source: CCR / net utility.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1327|p.13,L3|4B|Source (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1328|p.13,L3|4|Source (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1329|p.13,L3|5.5|Source (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1330|p.13,L3|6|Source (cases) MedScope-4B gemini-4-argon Claude Opus 5.5 gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1331|p.13,L4|99|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1332|p.13,L4|0.73|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1333|p.13,L4|0.67|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1334|p.13,L4|0.71|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1335|p.13,L4|0.55|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1336|p.13,L4|0.93|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1337|p.13,L4|0.48|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1338|p.13,L4|0.98|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1339|p.13,L4|0.18|BUS-UCLM, breast ultrasound (99) 0.73 / 0.67 0.71 / 0.55 0.93 / 0.48 0.98 / 0.18|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1340|p.13,L5|39|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1341|p.13,L5|0.69|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1342|p.13,L5|0.38|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1343|p.13,L5|0.97|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1344|p.13,L5|0.75|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1345|p.13,L5|0.92|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1346|p.13,L5|0.59|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1347|p.13,L5|0.73|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1348|p.13,L5|0.35|ETIS-Larib, colonoscopy (39) 0.69 / 0.38 0.97 / 0.75 0.92 / 0.59 0.73 / 0.35|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1349|p.13,L6|2023|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1350|p.13,L6|82|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1351|p.13,L6|0.53|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1352|p.13,L6|−0.03|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1353|p.13,L6|0.62|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1354|p.13,L6|0.09|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1355|p.13,L6|0.69|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1356|p.13,L6|0.00|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1357|p.13,L6|0.50|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1358|p.13,L6|−0.21|BraTS 2023 meningioma, MRI (82) 0.53 / −0.03 0.62 / 0.09 0.69 / 0.00 0.50 / −0.21|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1359|p.13,L7|96|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1360|p.13,L7|0.00|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1361|p.13,L7|−1.10|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1362|p.13,L7|0.66|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1363|p.13,L7|−0.06|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1364|p.13,L7|0.28|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1365|p.13,L7|−0.68|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1366|p.13,L7|0.29|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1367|p.13,L7|−0.62|SIIM-ACR pneumothorax, chest X-ray (96) 0.00 / −1.10 0.66 / −0.06 0.28 / −0.68 0.29 / −0.62|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1368|p.13,L9|12|Table 12: Standard medical VQA, same agent loop for every model: closed / open / all questions.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1369|p.13,L11|451|Model VQA-RAD (451) SLAKE (300) PathVQA (300)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1370|p.13,L11|300|Model VQA-RAD (451) SLAKE (300) PathVQA (300)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1371|p.13,L11|300|Model VQA-RAD (451) SLAKE (300) PathVQA (300)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1372|p.13,L12|4B|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1373|p.13,L12|0.741|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1374|p.13,L12|0.230|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1375|p.13,L12|0.514|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1376|p.13,L12|0.881|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1377|p.13,L12|0.644|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1378|p.13,L12|0.730|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1379|p.13,L12|0.801|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1380|p.13,L12|0.125|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1381|p.13,L12|0.477|MedScope-4B 0.741 / 0.230 / 0.514 0.881 / 0.644 / 0.730 0.801 / 0.125 / 0.477|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1382|p.13,L13|4|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1383|p.13,L13|0.884|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1384|p.13,L13|0.410|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1385|p.13,L13|0.674|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1386|p.13,L13|0.927|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1387|p.13,L13|0.696|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1388|p.13,L13|0.780|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1389|p.13,L13|0.712|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1390|p.13,L13|0.097|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1391|p.13,L13|0.417|gemini-4-argon 0.884 / 0.410 / 0.674 0.927 / 0.696 / 0.780 0.712 / 0.097 / 0.417|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1392|p.13,L14|5.5|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1393|p.13,L14|0.876|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1394|p.13,L14|0.380|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1395|p.13,L14|0.656|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1396|p.13,L14|0.927|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1397|p.13,L14|0.602|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1398|p.13,L14|0.720|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1399|p.13,L14|0.865|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1400|p.13,L14|0.153|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1401|p.13,L14|0.523|Claude Opus 5.5 0.876 / 0.380 / 0.656 0.927 / 0.602 / 0.720 0.865 / 0.153 / 0.523|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1402|p.13,L15|6|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1403|p.13,L15|0.797|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1404|p.13,L15|0.255|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1405|p.13,L15|0.557|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1406|p.13,L15|0.835|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1407|p.13,L15|0.476|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1408|p.13,L15|0.607|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1409|p.13,L15|0.526|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1410|p.13,L15|0.062|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1411|p.13,L15|0.303|gpt-6-astra 0.797 / 0.255 / 0.557 0.835 / 0.476 / 0.607 0.526 / 0.062 / 0.303|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1412|p.13,L16|5|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1413|p.13,L16|4B|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1414|p.13,L16|0.657|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1415|p.13,L16|0.260|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1416|p.13,L16|0.481|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1417|p.13,L16|0.826|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1418|p.13,L16|0.424|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1419|p.13,L16|0.570|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1420|p.13,L16|0.545|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1421|p.13,L16|0.021|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1422|p.13,L16|0.293|Qwen3.5-4B (base) 0.657 / 0.260 / 0.481 0.826 / 0.424 / 0.570 0.545 / 0.021 / 0.293|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1423|p.13,L17|7B|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1424|p.13,L17|0.705|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1425|p.13,L17|0.195|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1426|p.13,L17|0.479|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1427|p.13,L17|0.798|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1428|p.13,L17|0.545|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1429|p.13,L17|0.637|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1430|p.13,L17|0.712|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1431|p.13,L17|0.042|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1432|p.13,L17|0.390|Lingshu-7B 0.705 / 0.195 / 0.479 0.798 / 0.545 / 0.637 0.712 / 0.042 / 0.390|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1433|p.13,L19|13|Table 13: SIIM pneumothorax images called present (the 42 cases found in the original-resolution data).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1434|p.13,L19|42|Table 13: SIIM pneumothorax images called present (the 42 cases found in the original-resolution data).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1435|p.13,L21|256|Model 256-pixel copy Original resolution|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1436|p.13,L22|5|Qwen3.5-4B (base) 0% 12%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1437|p.13,L22|4B|Qwen3.5-4B (base) 0% 12%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1438|p.13,L22|0%|Qwen3.5-4B (base) 0% 12%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1439|p.13,L22|12%|Qwen3.5-4B (base) 0% 12%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1440|p.13,L23|1|Stage 1 without counterfactual views 0% 5%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1441|p.13,L23|0%|Stage 1 without counterfactual views 0% 5%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1442|p.13,L23|5%|Stage 1 without counterfactual views 0% 5%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1443|p.13,L24|1|Stage 1 with counterfactual views 19% 40%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1444|p.13,L24|19%|Stage 1 with counterfactual views 19% 40%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1445|p.13,L24|40%|Stage 1 with counterfactual views 19% 40%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1446|p.13,L25|2|Stage 2 [–] 40%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1447|p.13,L25|40%|Stage 2 [–] 40%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1448|p.13,L26|4B|MedScope-4B (stage 3) 0% 0%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1449|p.13,L26|3|MedScope-4B (stage 3) 0% 0%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1450|p.13,L26|0%|MedScope-4B (stage 3) 0% 0%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1451|p.13,L26|0%|MedScope-4B (stage 3) 0% 0%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1452|p.13,L27|4|gemini-4-argon 69% 69%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1453|p.13,L27|69%|gemini-4-argon 69% 69%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1454|p.13,L27|69%|gemini-4-argon 69% 69%|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1455|p.13,L30|5.5|net utility better than Claude Opus 5.5 and gemini-4-argon (p = 0.002), not different from gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1456|p.13,L30|4|net utility better than Claude Opus 5.5 and gemini-4-argon (p = 0.002), not different from gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1457|p.13,L30|0.002|net utility better than Claude Opus 5.5 and gemini-4-argon (p = 0.002), not different from gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1458|p.13,L30|6|net utility better than Claude Opus 5.5 and gemini-4-argon (p = 0.002), not different from gpt-6-astra|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1459|p.13,L31|0.15|(p = 0.15).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1460|p.13,L32|6|Fresh external (confirmatory). The result is mixed. ESG is higher than gpt-6-astra’s and Claude Opus|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1461|p.13,L33|5.5|5.5’s (p ≤ 0.037) and not different from gemini-4-argon’s (p = 0.34); net utility is below gemini-4-argon’s|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1462|p.13,L33|0.037|5.5’s (p ≤ 0.037) and not different from gemini-4-argon’s (p = 0.34); net utility is below gemini-4-argon’s|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1463|p.13,L33|4|5.5’s (p ≤ 0.037) and not different from gemini-4-argon’s (p = 0.34); net utility is below gemini-4-argon’s|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1464|p.13,L33|0.34|5.5’s (p ≤ 0.037) and not different from gemini-4-argon’s (p = 0.34); net utility is below gemini-4-argon’s|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1465|p.13,L33|4|5.5’s (p ≤ 0.037) and not different from gemini-4-argon’s (p = 0.34); net utility is below gemini-4-argon’s|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1466|p.13,L34|−0.363|(−0.363 [−0.496, −0.233], p &lt; 0.001). The by-source breakdown (Table 11) locates the loss: MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1467|p.13,L34|−0.496|(−0.363 [−0.496, −0.233], p &lt; 0.001). The by-source breakdown (Table 11) locates the loss: MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1468|p.13,L34|−0.233|(−0.363 [−0.496, −0.233], p &lt; 0.001). The by-source breakdown (Table 11) locates the loss: MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1469|p.13,L34|0.001|(−0.363 [−0.496, −0.233], p &lt; 0.001). The by-source breakdown (Table 11) locates the loss: MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1470|p.13,L34|11|(−0.363 [−0.496, −0.233], p &lt; 0.001). The by-source breakdown (Table 11) locates the loss: MedScope-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1471|p.13,L35|4B|4B leads on breast ultrasound and trails on colonoscopy and meningioma MRI, and on SIIM pneumothorax|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1472|p.13,L36|one|it answers “No” to every one of 48 pneumothorax images (Section 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1473|p.13,L36|48|it answers “No” to every one of 48 pneumothorax images (Section 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1474|p.13,L36|6|it answers “No” to every one of 48 pneumothorax images (Section 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1475|p.13,L37|12|Standard medical VQA. Accuracy on ordinary questions is kept (Table 12). MedScope-4B saw these|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1476|p.13,L37|4B|Standard medical VQA. Accuracy on ordinary questions is kept (Table 12). MedScope-4B saw these|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1477|p.13,L39|three|comparison; against its own base model it gains on all three. With their own plain prompt most open|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1478|p.13,L40|7B|models score higher than in the agent loop (Lingshu-7B: 0.552, 0.803, 0.573), so the loop is a harder|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1479|p.13,L40|0.552|models score higher than in the agent loop (Lingshu-7B: 0.552, 0.803, 0.573), so the loop is a harder|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1480|p.13,L40|0.803|models score higher than in the agent loop (Lingshu-7B: 0.552, 0.803, 0.573), so the loop is a harder|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1481|p.13,L40|0.573|models score higher than in the agent loop (Lingshu-7B: 0.552, 0.803, 0.573), so the loop is a harder|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1482|p.13,L44|6|6 Failure analysis: why is pneumothorax missed?|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1483|p.13,L45|4B|MedScope-4B answered a confident “No” on all 48 SIIM-ACR pneumothorax images of the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1484|p.13,L45|48|MedScope-4B answered a confident “No” on all 48 SIIM-ACR pneumothorax images of the fresh external|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1485|p.13,L46|1.0|test (answer-token probability about 1.0). Scoring and parsing were checked and are correct. The analysis|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1486|p.13,L50|256|Resolution is not the cause. The fresh test used a 256-pixel copy of SIIM. Rebuilt from the original|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1487|p.13,L51|13|DICOMs, earlier checkpoints detect more pneumothoraxes, but the final model still detects none (Table 13).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1488|p.13,L52|1|Counterfactual training is not the cause. The stage-1 model with counterfactual views is the most|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1489|p.14,L1|54|Training coverage is. Questions naming pneumothorax were 54 of about 7,000 chest X-ray training|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1490|p.14,L1|7,000|Training coverage is. Questions naming pneumothorax were 54 of about 7,000 chest X-ray training|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1491|p.14,L2|1|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1492|p.14,L2|35|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1493|p.14,L2|2|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1494|p.14,L2|15|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1495|p.14,L2|3|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1496|p.14,L2|80%|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1497|p.14,L2|100%|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1498|p.14,L2|87%|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1499|p.14,L2|1|views in stage 1 (35 in stage 2, 15 in stage 3), trained to “No” 80%, 100% and 87% of the time. Stage 1 held|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1500|p.14,L3|four|only four pneumothorax lesion images, all large (lesion box median 37% of the image, against 6.9% for the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1501|p.14,L3|37%|only four pneumothorax lesion images, all large (lesion box median 37% of the image, against 6.9% for the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1502|p.14,L3|6.9%|only four pneumothorax lesion images, all large (lesion box median 37% of the image, against 6.9% for the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1503|p.14,L5|7|(only 7, 7 and 4 lesion-free ones), so the selection rule could not see the problem.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1504|p.14,L5|7|(only 7, 7 and 4 lesion-free ones), so the selection rule could not see the problem.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1505|p.14,L5|4|(only 7, 7 and 4 lesion-free ones), so the selection rule could not see the problem.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1506|p.14,L6|3|Stage 3 turns weak detection into none. Stage 3 shifts chest X-ray answers towards “No” in general:|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1507|p.14,L6|3|Stage 3 turns weak detection into none. Stage 3 shifts chest X-ray answers towards “No” in general:|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1508|p.14,L7|63%|on validation, named findings detected fall from 63% to 56%, erased-lesion claims from 16% to 9% and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1509|p.14,L7|56%|on validation, named findings detected fall from 63% to 56%, erased-lesion claims from 16% to 9% and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1510|p.14,L7|16%|on validation, named findings detected fall from 63% to 56%, erased-lesion claims from 16% to 9% and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1511|p.14,L7|9%|on validation, named findings detected fall from 63% to 56%, erased-lesion claims from 16% to 9% and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1512|p.14,L8|24%|healthy-image claims from 24% to 10%. With almost no positive pneumothorax examples, its weak detec-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1513|p.14,L8|10%|healthy-image claims from 24% to 10%. With almost no positive pneumothorax examples, its weak detec-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1514|p.14,L9|zero|tion drops to zero at every lesion size. The share of “No” targets alone does not explain this: stage 2 trained|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1515|p.14,L9|2|tion drops to zero at every lesion size. The share of “No” targets alone does not explain this: stage 2 trained|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1516|p.14,L10|35|on 35 of 35 “No” targets and still detected 40%.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1517|p.14,L10|35|on 35 of 35 “No” targets and still detected 40%.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1518|p.14,L10|40%|on 35 of 35 “No” targets and still detected 40%.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1519|p.14,L11|4B|The model registers something. Asked “Is there an abnormality?”, MedScope-4B says yes on 35 of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1520|p.14,L11|35|The model registers something. Asked “Is there an abnormality?”, MedScope-4B says yes on 35 of|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1521|p.14,L12|42|42 pneumothorax images and on 28 of 48 SIIM images without pneumothorax (Fisher p = 0.012); the base|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1522|p.14,L12|28|42 pneumothorax images and on 28 of 48 SIIM images without pneumothorax (Fisher p = 0.012); the base|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1523|p.14,L12|48|42 pneumothorax images and on 28 of 48 SIIM images without pneumothorax (Fisher p = 0.012); the base|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1524|p.14,L12|0.012|42 pneumothorax images and on 28 of 48 SIIM images without pneumothorax (Fisher p = 0.012); the base|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1525|p.14,L13|38|model separates them more (38/42 vs 23/48, p &lt; 0.001). The final model sees that something is abnormal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1526|p.14,L13|42|model separates them more (38/42 vs 23/48, p &lt; 0.001). The final model sees that something is abnormal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1527|p.14,L13|23|model separates them more (38/42 vs 23/48, p &lt; 0.001). The final model sees that something is abnormal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1528|p.14,L13|48|model separates them more (38/42 vs 23/48, p &lt; 0.001). The final model sees that something is abnormal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1529|p.14,L13|0.001|model separates them more (38/42 vs 23/48, p &lt; 0.001). The final model sees that something is abnormal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1530|p.14,L17|4|every aggregate metric improves. Coverage may not be the whole story: the gap to gemini-4-argon even at|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1531|p.14,L21|7|7 Reader study|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1532|p.14,L23|two|therefore read a blinded set of test images to check two assumptions: that an erased finding is no longer|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1533|p.14,L26|96|Images. 96 images from the main test, each from a different case and stratified by source: 32 unmod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1534|p.14,L26|32|Images. 96 images from the main test, each from a different case and stratified by source: 32 unmod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1535|p.14,L27|32|ified images with a lesion, 32 lesion-erased images (the LaMa erasures the models were tested on) and 32|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1536|p.14,L27|32|ified images with a lesion, 32 lesion-erased images (the LaMa erasures the models were tested on) and 32|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1537|p.14,L32|1|time limit and no other information. For each image they answer (1) whether the image has been digitally|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1538|p.14,L33|2|edited (definitely real, probably real, probably edited, definitely edited) and (2) the case’s clinical question|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1539|p.14,L36|four|Pre-specified analysis. Per reader: the AUC for separating erased from unmodified images on the four-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1540|p.14,L40|zero|if their AUC for recognising erasures is close to the zero-shot frontier models’ (0.70–0.75) rather than near|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1541|p.14,L40|0.70|if their AUC for recognising erasures is close to the zero-shot frontier models’ (0.70–0.75) rather than near|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1542|p.14,L40|0.75|if their AUC for recognising erasures is close to the zero-shot frontier models’ (0.70–0.75) rather than near|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1543|p.14,L41|1|1.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1544|p.14,L45|8|8 Discussion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1545|p.14,L46|8.1|8.1 Principal findings|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1546|p.14,L47|Nine|Seeing a lesion and reporting only what is seen are separable abilities. Nine frontier models see real|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1547|p.14,L48|4B|lesions as well as a 4B model, yet claim about half of the lesions after they have been erased, under the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1548|p.14,L48|half|lesions as well as a 4B model, yet claim about half of the lesions after they have been erased, under the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1549|p.15,L9|8.2|8.2 What it is not|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1550|p.15,L11|0.95|lesions (CCR 0.95–0.97 vs 0.73), and the two abilities pull net utility in opposite directions: frontier mod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1551|p.15,L11|0.97|lesions (CCR 0.95–0.97 vs 0.73), and the two abilities pull net utility in opposite directions: frontier mod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1552|p.15,L11|0.73|lesions (CCR 0.95–0.97 vs 0.73), and the two abilities pull net utility in opposite directions: frontier mod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1553|p.15,L11|two|lesions (CCR 0.95–0.97 vs 0.73), and the two abilities pull net utility in opposite directions: frontier mod-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1554|p.15,L12|4B|els behave as high-sensitivity, high-hallucination readers, MedScope-4B as an evidence-gated reader that|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1555|p.15,L19|8.3|8.3 Relation to prior work|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1556|p.15,L20|9|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1557|p.15,L20|10|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1558|p.15,L20|11|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1559|p.15,L20|12|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1560|p.15,L20|13|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1561|p.15,L20|15|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1562|p.15,L20|16|Hallucination benchmarks and training-free detectors [9, 10, 11, 12, 13, 15, 16] measure or flag unsupported|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1563|p.15,L22|17|train the behaviour into a model. Compared with natural-image counterfactual VQA [17], the control edit|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1564|p.15,L25|21|learning [21, 22, 23, 24], label-derived trajectories and rejection sampling were enough to teach tool use|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1565|p.15,L25|22|learning [21, 22, 23, 24], label-derived trajectories and rejection sampling were enough to teach tool use|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1566|p.15,L25|23|learning [21, 22, 23, 24], label-derived trajectories and rejection sampling were enough to teach tool use|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1567|p.15,L25|24|learning [21, 22, 23, 24], label-derived trajectories and rejection sampling were enough to teach tool use|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1568|p.15,L26|93%|(first zoom on the lesion in 93% of lesion views).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1569|p.15,L29|8.4|8.4 Implications|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1570|p.15,L32|one|hallucination rates can hide a complete miss of one critical finding; per-finding sensitivity floors belong in|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1571|p.15,L33|4B|model selection. For clinical use, MedScope-4B is a research model, not a medical device, and nothing|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1572|p.15,L37|8.5|8.5 Limitations|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1573|p.15,L39|6|by the most conservative stage (Section 6).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1574|p.15,L40|0.55|• Perception. The vision encoder is frozen; subtle findings and the smallest lesions (ESG 0.55 in the lowest|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1575|p.15,L42|0.05|• Erasure as ground truth. Diffuse findings are erased less completely (QaTa-COV19 ESG 0.05), erasure|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1576|p.15,L43|2|can leave secondary signs such as mass effect or oedema, and a second, unmasked lesion (Figure 2, breast|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1577|p.15,L46|0.83|• Edit traces. A trained detector finds the edits (AUC 0.83). The advantage holds on clean-looking erasures|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1578|p.15,L49|26|free labels (26 of 288) do not change any comparison.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1579|p.15,L49|288|free labels (26 of 288) do not change any comparison.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1580|p.16,L5|2|• Scope. Yes/no and short-answer questions on single 2D images; no report generation, no 3D volumes,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1581|p.16,L5|3|• Scope. Yes/no and short-answer questions on single 2D images; no report generation, no 3D volumes,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1582|p.16,L9|8.6|8.6 Future work|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1583|p.16,L10|Three|Three directions follow directly: per-finding coverage and sensitivity floors in data and selection; unfreezing|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1584|p.16,L16|9|9 Conclusion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1585|p.16,L19|4B|views and selected by a pre-registered rule, a 4B agent matches nine frontier models on real lesions and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1586|p.16,L19|nine|views and selected by a pre-registered rule, a 4B agent matches nine frontier models on real lesions and|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1587|p.16,L20|four|claims erased findings four to six times less often, robustly to prompting, question wording and unseen|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1588|p.16,L20|six|claims erased findings four to six times less often, robustly to prompting, question wording and unseen|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1589|p.16,L30|4B|(bhaskar-ai/MedScope-4B; datasets/bhaskar-ai/MedScope-Bench), public on accep-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1590|p.16,L42|1|[1] C. Li et al. LLaVA-Med: Training a large language-and-vision assistant for biomedicine in one day. NeurIPS|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1591|p.16,L42|one|[1] C. Li et al. LLaVA-Med: Training a large language-and-vision assistant for biomedicine in one day. NeurIPS|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1592|p.16,L43|2023|Datasets and Benchmarks, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1593|p.16,L44|2|[2] J. Chen et al. HuatuoGPT-Vision: Towards injecting medical visual knowledge into multimodal LLMs at scale.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1594|p.16,L45|2024|EMNLP, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1595|p.16,L46|3|[3] A. Sellergren et al. MedGemma technical report. arXiv:2507.05201, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1596|p.16,L46|2507.05201|[3] A. Sellergren et al. MedGemma technical report. arXiv:2507.05201, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1597|p.16,L46|2025|[3] A. Sellergren et al. MedGemma technical report. arXiv:2507.05201, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1598|p.16,L47|4|[4] Google Research and Google DeepMind (A. Sellergren, F. Mahvar et al.). MedGemma 1.5 technical report.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1599|p.16,L47|1.5|[4] Google Research and Google DeepMind (A. Sellergren, F. Mahvar et al.). MedGemma 1.5 technical report.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1600|p.16,L48|2604.05081|arXiv:2604.05081, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1601|p.16,L48|2026|arXiv:2604.05081, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1602|p.17,L1|5|[5] LASA Team, W. Xu, H. P. Chan, L. Li et al. Lingshu: A generalist foundation model for unified multimodal|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1603|p.17,L2|2506.07044|medical understanding and reasoning. arXiv:2506.07044, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1604|p.17,L2|2025|medical understanding and reasoning. arXiv:2506.07044, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1605|p.17,L4|6|[6] J. J. Lau et al. A dataset of clinically generated visual questions and answers about radiology images. Scientific|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1606|p.17,L5|2018|Data, 2018.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1607|p.17,L7|7|[7] B. Liu et al. SLAKE: A semantically-labeled knowledge-enhanced dataset for medical visual question answer-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1608|p.17,L8|2021|ing. ISBI, 2021.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1609|p.17,L10|8|[8] X. He et al. PathVQA: 30000+ questions for medical visual question answering. arXiv, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1610|p.17,L10|30000|[8] X. He et al. PathVQA: 30000+ questions for medical visual question answering. arXiv, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1611|p.17,L10|2020|[8] X. He et al. PathVQA: 30000+ questions for medical visual question answering. arXiv, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1612|p.17,L12|9|[9] Y. Li et al. Evaluating object hallucination in large vision-language models. EMNLP, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1613|p.17,L12|2023|[9] Y. Li et al. Evaluating object hallucination in large vision-language models. EMNLP, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1614|p.17,L14|10|[10] P. Xia et al. CARES: A comprehensive benchmark of trustworthiness in medical vision language models.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1615|p.17,L15|2024|NeurIPS, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1616|p.17,L17|11|[11] J. Chen et al. Detecting and evaluating medical hallucinations in large vision language models (Med-HallMark).|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1617|p.17,L18|2024|arXiv, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1618|p.17,L20|12|[12] Z. Gu et al. MedVH: Towards systematic evaluation of hallucination for large vision language models in the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1619|p.17,L21|2024|medical context. arXiv, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1620|p.17,L23|13|[13] A. Chang et al. MedHEval: Benchmarking hallucinations and mitigation strategies in medical large vision-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1621|p.17,L24|2503.02157|language models. arXiv:2503.02157, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1622|p.17,L24|2025|language models. arXiv:2503.02157, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1623|p.17,L26|14|[14] R. Suvorov et al. Resolution-robust large mask inpainting with Fourier convolutions. WACV, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1624|p.17,L26|2022|[14] R. Suvorov et al. Resolution-robust large mask inpainting with Fourier convolutions. WACV, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1625|p.17,L28|15|[15] N. Zhou, K. Zou, M. Liu et al. Hallucination detection and correction in medical VLMs via counter-evidence|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1626|p.17,L29|2606.18609|verification. arXiv:2606.18609, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1627|p.17,L29|2026|verification. arXiv:2606.18609, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1628|p.17,L31|16|[16] X. Song, H. Qin, Z. Zhang et al. Detecting clinical hallucinations in LVLMs via counterfactual visual grounding|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1629|p.17,L32|2606.28520|uncertainty. arXiv:2606.28520, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1630|p.17,L32|2026|uncertainty. arXiv:2606.28520, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1631|p.17,L34|17|[17] V. Agarwal, R. Shetty, M. Fritz. Towards causal VQA: Revealing and reducing spurious correlations by invariant|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1632|p.17,L35|2020|and covariant semantic editing. CVPR, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1633|p.17,L37|18|[18] A. Telea. An image inpainting technique based on the fast marching method. Journal of Graphics Tools, 2004.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1634|p.17,L37|2004|[18] A. Telea. An image inpainting technique based on the fast marching method. Journal of Graphics Tools, 2004.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1635|p.17,L39|19|[19] P. Pérez, M. Gangnet, A. Blake. Poisson image editing. ACM SIGGRAPH, 2003.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1636|p.17,L39|2003|[19] P. Pérez, M. Gangnet, A. Blake. Poisson image editing. ACM SIGGRAPH, 2003.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1637|p.17,L41|20|[20] R. Rombach et al. High-resolution image synthesis with latent diffusion models. CVPR, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1638|p.17,L41|2022|[20] R. Rombach et al. High-resolution image synthesis with latent diffusion models. CVPR, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1639|p.17,L43|21|[21] Z. Zheng et al. DeepEyes: Incentivizing “thinking with images” via reinforcement learning. ICLR, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1640|p.17,L43|2026|[21] Z. Zheng et al. DeepEyes: Incentivizing “thinking with images” via reinforcement learning. ICLR, 2026.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1641|p.17,L45|22|[22] A. Su et al. Pixel Reasoner: Incentivizing pixel-space reasoning with curiosity-driven reinforcement learning.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1642|p.17,L46|2505.15966|arXiv:2505.15966, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1643|p.17,L46|2025|arXiv:2505.15966, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1644|p.17,L48|23|[23] B. Li et al. MMedAgent: Learning to use medical tools with multi-modal agent. Findings of EMNLP, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1645|p.17,L48|2024|[23] B. Li et al. MMedAgent: Learning to use medical tools with multi-modal agent. Findings of EMNLP, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1646|p.17,L50|24|[24] P. Xia et al. MMedAgent-RL: Optimizing multi-agent collaboration for multimodal medical reasoning.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1647|p.17,L51|2506.00555|arXiv:2506.00555, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1648|p.17,L51|2025|arXiv:2506.00555, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1649|p.17,L53|25|[25] Z. Shao et al. DeepSeekMath: Pushing the limits of mathematical reasoning in open language models. arXiv,|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1650|p.17,L54|2024|2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1651|p.17,L56|26|[26] Q. Yu et al. DAPO: An open-source LLM reinforcement learning system at scale. NeurIPS, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1652|p.17,L56|2025|[26] Q. Yu et al. DAPO: An open-source LLM reinforcement learning system at scale. NeurIPS, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1653|p.17,L58|27|[27] E. Zelikman et al. STaR: Bootstrapping reasoning with reasoning. NeurIPS, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1654|p.17,L58|2022|[27] E. Zelikman et al. STaR: Bootstrapping reasoning with reasoning. NeurIPS, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1655|p.17,L60|28|[28] Z. Yuan et al. Scaling relationship on learning mathematical reasoning with large language models. arXiv, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1656|p.17,L60|2023|[28] Z. Yuan et al. Scaling relationship on learning mathematical reasoning with large language models. arXiv, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1657|p.17,L62|29|[29] Y. Geifman and R. El-Yaniv. Selective classification for deep neural networks. NeurIPS, 2017.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1658|p.17,L62|2017|[29] Y. Geifman and R. El-Yaniv. Selective classification for deep neural networks. NeurIPS, 2017.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1659|p.17,L64|30|[30] A. S. Tejani et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. Radiology:|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1660|p.17,L64|2024|[30] A. S. Tejani et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. Radiology:|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1661|p.17,L65|2024|Artificial Intelligence, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1662|p.18,L1|31|[31] Qwen Team. Qwen3.5 model card and technical report, 2026. [verify]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1663|p.18,L1|5|[31] Qwen Team. Qwen3.5 model card and technical report, 2026. [verify]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1664|p.18,L1|2026|[31] Qwen Team. Qwen3.5 model card and technical report, 2026. [verify]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1665|p.18,L3|32|[32] E. J. Hu et al. LoRA: Low-rank adaptation of large language models. ICLR, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1666|p.18,L3|2022|[32] E. J. Hu et al. LoRA: Low-rank adaptation of large language models. ICLR, 2022.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1667|p.18,L5|33|[33] B. Efron and R. J. Tibshirani. An Introduction to the Bootstrap. Chapman & Hall, 1993.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1668|p.18,L5|1993|[33] B. Efron and R. J. Tibshirani. An Introduction to the Bootstrap. Chapman & Hall, 1993.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1669|p.18,L7|34|[34] D. Jha et al. Kvasir-SEG: A segmented polyp dataset. MMM, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1670|p.18,L7|2020|[34] D. Jha et al. Kvasir-SEG: A segmented polyp dataset. MMM, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1671|p.18,L9|35|[35] H. Borgli et al. HyperKvasir, a comprehensive multi-class image and video dataset for gastrointestinal en-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1672|p.18,L10|2020|doscopy. Scientific Data, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1673|p.18,L12|36|[36] J. Lian et al. A structure-aware relation network for thoracic diseases detection and segmentation. IEEE Trans-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1674|p.18,L13|2021|actions on Medical Imaging, 2021.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1675|p.18,L15|37|[37] X. Wang et al. ChestX-ray8: Hospital-scale chest X-ray database and benchmarks on weakly-supervised clas-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1676|p.18,L16|2017|sification and localization of common thorax diseases. CVPR, 2017.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1677|p.18,L18|38|[38] W. Al-Dhabyani et al. Dataset of breast ultrasound images. Data in Brief, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1678|p.18,L18|2020|[38] W. Al-Dhabyani et al. Dataset of breast ultrasound images. Data in Brief, 2020.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1679|p.18,L20|39|[39] M. Buda, A. Saha, M. A. Mazurowski. Association of genomic subtypes of lower-grade gliomas with shape|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1680|p.18,L21|2019|features automatically extracted by a deep learning algorithm. Computers in Biology and Medicine, 2019.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1681|p.18,L23|40|[40] J. Bernal et al. WM-DOVA maps for accurate polyp highlighting in colonoscopy. Computerized Medical Imag-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1682|p.18,L24|2015|ing and Graphics, 2015.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1683|p.18,L26|41|[41] A. Degerli et al. COVID-19 infection map generation and detection from chest X-ray images. Health Informa-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1684|p.18,L26|19|[41] A. Degerli et al. COVID-19 infection map generation and detection from chest X-ray images. Health Informa-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1685|p.18,L27|9|tion Science and Systems, 9:15, 2021.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1686|p.18,L27|15|tion Science and Systems, 9:15, 2021.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1687|p.18,L27|2021|tion Science and Systems, 9:15, 2021.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1688|p.18,L29|42|[42] W. Gómez-Flores et al. BUS-BRA: A breast ultrasound dataset for assessing computer-aided diagnosis systems.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1689|p.18,L30|2024|Medical Physics, 2024.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1690|p.18,L32|43|[43] M. Adewole et al. The Brain Tumor Segmentation (BraTS) Challenge 2023: Glioma segmentation in sub-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1691|p.18,L32|2023|[43] M. Adewole et al. The Brain Tumor Segmentation (BraTS) Challenge 2023: Glioma segmentation in sub-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1692|p.18,L33|2305.19369|Saharan Africa patient population (BraTS-Africa). arXiv:2305.19369, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1693|p.18,L33|2023|Saharan Africa patient population (BraTS-Africa). arXiv:2305.19369, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1694|p.18,L35|44|[44] M. Adewole et al. The BraTS-Africa dataset. Radiology: Artificial Intelligence, 2025, doi:10.1148/ryai.240528.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1695|p.18,L35|2025|[44] M. Adewole et al. The BraTS-Africa dataset. Radiology: Artificial Intelligence, 2025, doi:10.1148/ryai.240528.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1696|p.18,L35|10.1148|[44] M. Adewole et al. The BraTS-Africa dataset. Radiology: Artificial Intelligence, 2025, doi:10.1148/ryai.240528.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1697|p.18,L35|240528|[44] M. Adewole et al. The BraTS-Africa dataset. Radiology: Artificial Intelligence, 2025, doi:10.1148/ryai.240528.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1698|p.18,L37|45|[45] D. LaBella et al. The ASNR-MICCAI Brain Tumor Segmentation (BraTS) Challenge 2023: Intracranial menin-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1699|p.18,L37|2023|[45] D. LaBella et al. The ASNR-MICCAI Brain Tumor Segmentation (BraTS) Challenge 2023: Intracranial menin-|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1700|p.18,L38|2305.07642|gioma. arXiv:2305.07642, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1701|p.18,L38|2023|gioma. arXiv:2305.07642, 2023.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1702|p.18,L40|46|[46] N. Vallez et al. BUS-UCLM: Breast ultrasound lesion segmentation dataset. Scientific Data, 2025. [verify]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1703|p.18,L40|2025|[46] N. Vallez et al. BUS-UCLM: Breast ultrasound lesion segmentation dataset. Scientific Data, 2025. [verify]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1704|p.18,L42|47|[47] A. Zawacki et al. SIIM-ACR Pneumothorax Segmentation. Kaggle, 2019. [verify citation form]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1705|p.18,L42|2019|[47] A. Zawacki et al. SIIM-ACR Pneumothorax Segmentation. Kaggle, 2019. [verify citation form]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1706|p.18,L44|48|[48] J. Silva et al. Toward embedded detection of polyps in WCE images for early diagnosis of colorectal cancer.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1707|p.18,L45|2014|International Journal of Computer Assisted Radiology and Surgery, 2014.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1708|p.18,L47|49|[49] S. Bai et al. Qwen2.5-VL technical report. arXiv, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1709|p.18,L47|5|[49] S. Bai et al. Qwen2.5-VL technical report. arXiv, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1710|p.18,L47|2025|[49] S. Bai et al. Qwen2.5-VL technical report. arXiv, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1711|p.18,L49|50|[50] Qwen Team. Qwen3-VL technical report. arXiv, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1712|p.18,L49|2025|[50] Qwen Team. Qwen3-VL technical report. arXiv, 2025.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1713|p.18,L57|ONE|On each turn, think briefly in plain text, then write exactly ONE action as a tagged JSON object|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1714|p.18,L59|two|[two examples: a zoom turn and a final answer]|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1715|p.18,L60|3|Tools (at most 3 calls per case; boxes are integers 0-1000 on the ORIGINAL full image, as [x1, y1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1716|p.18,L60|0|Tools (at most 3 calls per case; boxes are integers 0-1000 on the ORIGINAL full image, as [x1, y1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1717|p.18,L60|1000|Tools (at most 3 calls per case; boxes are integers 0-1000 on the ORIGINAL full image, as [x1, y1|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1718|p.18,L63|128|&lt;tool&gt;{"name": "window", "center": 128, "width": 100}&lt;/tool&gt; adjust brightness/contrast (0-255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1719|p.18,L63|100|&lt;tool&gt;{"name": "window", "center": 128, "width": 100}&lt;/tool&gt; adjust brightness/contrast (0-255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1720|p.18,L63|0|&lt;tool&gt;{"name": "window", "center": 128, "width": 100}&lt;/tool&gt; adjust brightness/contrast (0-255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1721|p.18,L63|255|&lt;tool&gt;{"name": "window", "center": 128, "width": 100}&lt;/tool&gt; adjust brightness/contrast (0-255|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1722|p.18,L65|one|Final actions (exactly one, then stop):|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1723|p.19,L1|0.0|&lt;final&gt;{"action": "answer", "answer": "...", "box": [x1, y1, x2, y2], "confidence": 0.0-1.0}&lt;/|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1724|p.19,L1|1.0|&lt;final&gt;{"action": "answer", "answer": "...", "box": [x1, y1, x2, y2], "confidence": 0.0-1.0}&lt;/|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1725|p.19,L15|One|and answer the question. Keep the answer short.” One reply, no tools. Cautious prompt (Table 9): the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1726|p.19,L15|9|and answer the question. Keep the answer short.” One reply, no tools. Cautious prompt (Table 9): the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1727|p.19,L19|9|Few-shot condition (Table 9): the cautious prompt plus four solved training examples before each case (a|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1728|p.19,L19|four|Few-shot condition (Table 9): the cautious prompt plus four solved training examples before each case (a|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1729|p.19,L25|One|• Hardware. One NVIDIA A100 40 GB per training stage (about 4 hours each); one local model on the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1730|p.19,L25|40|• Hardware. One NVIDIA A100 40 GB per training stage (about 4 hours each); one local model on the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1731|p.19,L25|4|• Hardware. One NVIDIA A100 40 GB per training stage (about 4 hours each); one local model on the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1732|p.19,L25|one|• Hardware. One NVIDIA A100 40 GB per training stage (about 4 hours each); one local model on the|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1733|p.19,L26|1|main test, about 1 hour. Frontier models run from a CPU runtime.|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1734|p.19,L27|16,000|• Determinism. Greedy decoding for open models; the 16,000-view stage-1 draw is fixed across seeds;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1735|p.19,L27|1|• Determinism. Greedy decoding for open models; the 16,000-view stage-1 draw is fixed across seeds;|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1736|p.19,L29|one|• Re-scoring. Every table is regenerated from stored per-view transcripts by one script; the notebook|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1737|p.19,L33|1|• Negative results from development. Plain GRPO from a stage-1 agent gave reward differences in only|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1738|p.19,L34|20%|20% of sampled groups, so group-relative advantages vanished; dynamic sampling gained one validation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1739|p.19,L34|one|20% of sampled groups, so group-relative advantages vanished; dynamic sampling gained one validation|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1740|p.19,L35|0.90|case. Merging a grounding-only adapter into the agent removed evidence sensitivity (abstention gap 0.90|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1741|p.19,L36|0.00|→ 0.00) while keeping grounding. An adapter trained only to answer with boxes claimed the finding on|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1742|p.19,L40|2024|C CLAIM 2024 checklist (summary)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1743|p.19,L43|1|Study design (retrospective); intended use (research) Sections 1, 4.1; Discussion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1744|p.19,L43|4.1|Study design (retrospective); intended use (research) Sections 1, 4.1; Discussion|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1745|p.19,L44|4.1|Data sources, inclusion and exclusion Section 4.1, Tables 2–3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1746|p.19,L44|2|Data sources, inclusion and exclusion Section 4.1, Tables 2–3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1747|p.19,L44|3|Data sources, inclusion and exclusion Section 4.1, Tables 2–3|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1748|p.19,L46|3.2|Reference standard and its limits Sections 3.2, 8.5; reader study (Section 7)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1749|p.19,L46|8.5|Reference standard and its limits Sections 3.2, 8.5; reader study (Section 7)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1750|p.19,L46|7|Reference standard and its limits Sections 3.2, 8.5; reader study (Section 7)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1751|p.19,L48|4.1|(Section 4.1)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1752|p.19,L49|3.5|Model, initialisation, training details Section 3.5; Appendix B|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1753|p.19,L50|3.6|Selection of the final model Section 3.6 (pre-registered)|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1754|p.19,L51|3.7|Metrics, uncertainty, statistical tests Sections 3.7, 3.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1755|p.19,L51|3.8|Metrics, uncertainty, statistical tests Sections 3.7, 3.8|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1756|p.19,L52|5.3|Robustness and sensitivity analyses Sections 5.3–5.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1757|p.19,L52|5.5|Robustness and sensitivity analyses Sections 5.3–5.5|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1758|p.19,L53|5.1|Internal and external testing Sections 5.1, 5.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1759|p.19,L53|5.6|Internal and external testing Sections 5.1, 5.6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|
|N1760|p.19,L54|6|Failure analysis Section 6|Unavailable (.tex/run files not supplied)|Untraceable to stored evidence|

## 5. Pre-registration, data/leakage, and code versus paper

### Central-claim disposition

| Claim | Audit verdict |
|---|---|
|C1|Valid for constant/text-only deterministic policies and an identical binary edit flag; false as a universal guarantee for image-based artifact detection. Stochastic policies require an expectation qualifier.|
|C2|Printed internal rates/ranges agree; all run-level results and bootstrap p-values remain untraceable. Open-model expansion of the claim is contradicted by Table4.|
|C3|Reported internal CCR non-significance does not establish equivalence. Healthy-image superiority requires raw paired results; label-exclusion direction claim is wrong.|
|C4|Ablations support a recipe effect conditional on unverified results; component causality is not isolated by the bundled erasures-only arm.|
|C5|Transfer across tools and the clean-looking subset are reported, but do not establish absence of artifact use or clinical validity.|
|C6|The printed selection rule selects stage3; prospective commitment, amendment timing and single-test execution cannot be certified.|
|C7|The important limitations are mostly disclosed prominently. Generalisation is mixed, and the exclusive coverage explanation needs softer wording.|

### 5.1 Registration chronology and confirmatory status

| Event | What the manuscript says | What can be concluded |
|---|---|---|
| Frontier evaluations |31 October 2026, §4.2 |Predates v4 registration; the main benchmark was already used. Whether results informed v4 is unknown. |
| Initial v4 registration |1 November 2026, §3.6 |Claimed prospective for v4 data/training; commit and server-side timestamp not available. |
| Amendment1 |After stage1 validation, before later results |Not prospective to all v4 results; may be a transparently disclosed adaptation. Need exact rule changes and results already visible. |
| Amendment2 |Before any test result |Need timestamp, amendment scope and definition of “test”—v4 test versus already-existing frontier main-test results. |
| Final selection |Stage3 by stated validation rule |Arithmetic supports the choice from printed values; immutable checkpoint hash and log needed. |
| Fresh tests |Untouched until selection, Table3 |Potentially confirmatory if manifests and timestamps support it. No independent verification. |
| Pneumothorax analyses |Explicitly post hoc, §6 |Appropriately labelled; avoid upgrading the interpretation to causal proof. |
| Reader study |Design fixed before answers, §7 |Prospective claim is unverified; recruitment/results pending. |

Selection arithmetic: stage3 U=0.613≥0.610−0.02=0.590 and H=0.077≤0.127+0.02=0.147. Stage3 exceeds v3 U=0.593 rather than falling below it. This validates the **application of the printed rule**, not that the rule was fixed prospectively. Obtain `git log -p docs/PREREGISTRATION_v4.md`, all parent commits, remote publication records, checkpoint timestamps, data manifest hashes and first test access times. Git author dates alone are editable and are not an independent time stamp. Do not assume manipulation; simply supply a stronger audit trail.

“Tested once” can reasonably mean one locked final-model evaluation per test set. It cannot imply that no other model or intervention was evaluated on the same main cases: the paper explicitly reports ablations and prompting tests. State exactly which claim is intended. Re-scoring stored transcripts should be distinguished from rerunning inference. Any parser fix prompted by test inspection must be logged, uniformly applied and described.

### 5.2 Data and leakage checklist

| Check | PDF evidence | Audit verdict / evidence needed |
|---|---|---|
| Patient/group-disjoint train/validation/test |§§3.3,4.1; Table2 |Claimed, unverified; publish unique patient/group counts and intersections. |
| Near-copy detection |Perceptual hash plus correlation |Thresholds, resize conventions, candidate search coverage, false-negative assessment absent. |
| Existing-test protection |93 chest,57 BUSI,79 TCGA images checked |Explain difference from91/57/78 evaluated cases; protecting a larger universe is not necessarily an error. |
| VQA replay |Near-identical evaluation images excluded |Must join replay image IDs to source studies/patients; pixel similarity alone cannot exclude same-patient different-view leakage. |
| Few-shot examples |AppendixA says training examples never in tests |Need exact four image IDs and group-level exclusion, not only file-name exclusion. |
| NIH-derived collections |ChestX-Det origin stated |The [official SIIM challenge page](https://siim.org/research-journal/siim-machine-learning-challenges/pneumothorax-kaggle-challenge/) confirms NIH-origin images. Require a patient/image crosswalk with ChestX-Det; shared provenance is verified, but exact sampled-cohort overlap remains unknown. |
| TCGA/BraTS |TCGA training; Africa/meningioma external |Do not assume all BraTS subsets overlap with TCGA-LGG: disease and geography differ. Supply subject-level crosswalk for the exact releases and sampled subjects. |
| External centres |Four named datasets |Datasets are not automatically independent centres; document actual sites and source origins. |
| Natural negatives |Source labels plus model-panel exclusion |Absence of one annotated condition is not absence of all disease; same-patient tumour-free MRI slices need care. Human adjudication required for clinical absence. |
| Degraded views |170 on main test |Report why49 masked cases lack this view and whether QC failures affect comparability. |
| Public-image licences |General declaration only |Dataset-specific use/derivative/redistribution rules required; do not assume public access grants unrestricted reuse. |
| Foundation-model contamination |Not systematically audited |Opaque pretraining cannot be ruled out. Separate author-controlled leakage checks from unknown baseline pretraining exposure. |

### 5.3 Formula and code audit

No metric or training code was available; the following records what must be tested, without claiming the implementation passes.

| Component | PDF specification | Outstanding implementation check |
|---|---|---|
| ESG |P(absent or refer∣T)−P(absent or refer∣R) |Denominators, pairing, weighting, missing actions and malformed replies. Abstract omits referral from its definition. |
| Strict ESG |Explicit absent only |Report positive/negative clinical polarity mapping and refer/clarify handling. |
| CCR |Correct on O∪R |Verify whether each image contributes equally, what correctness means for open answers, and abstentions in denominator. |
| Erased/healthy claims |Claims finding on T/N |“Not absent” is not automatically “claims present”; distinguish unusable, refer, malformed and irrelevant outputs. |
| Grounded accuracy |Correct and IoU≥0.3 on O |Union mask versus boxes, multiple lesions, oversized-box rule and coordinate conversion. |
| Clarification |P(clarify∣D) |Unknown/refer/malformed outcomes and exclusions. |
| Utility |Table1 mean per view; +0.5 box bonus; −1 malformed; −0.05 for calls after first |Order of penalties, critical-condition list, whether wrong answer to healthy question gets critical penalty, whether tool errors count. |
| AURC |Greedy answer-token geometric mean |Which tokens, EOS/tags/reasoning inclusion, API logprob availability, score ties, risk definition and curves absent. |
| Bootstrap |2,000 case draws; paired/two-sided |Resample whole patient/groups when clustered; fixed shared cohort, percentile method, NaN handling and p-value formula. |
| Parser |First final action, fallback on plain text |Conflicting finals, negation scope, missing tags, malformed JSON, numeric/yes-no variants; no model-specific branches. |
| Data building |5-pixel dilation; area bounds; QC |Pre/post resize units; foreground placement; overlapping lesions/secondary signs; thresholds and QC exclusions. |
| Training |Three stages; rank16, alpha32; frozen vision |Trainable modules, optimizer, batch/accumulation, packing, true update counts, seed mapping and effective per-arm distributions. |

**C1 proof with the necessary assumptions.** For paired case i with identical question qᵢ, define aᵢv=1 if the policy outputs absent or refer on view v. ESG is the average of aᵢT−aᵢR on a common complete set. A deterministic text-only policy has aᵢT=aᵢR, hence zero exactly. A stochastic image-blind policy has zero **in expectation** under the same input distribution; independently sampled finite runs can give nonzero empirical ESG. A policy using only the binary flag “edited” also gives zero if both T and R always receive the same flag. It does not follow that an image-based edit classifier has equal response probabilities: artifact visibility can differ by anatomy, texture, location and amount of plausible replacement.

Mechanical **synthetic** calculation (not on unavailable stored views): always claim→ESG0; always absent→0; always refer→0; always clarify→0; absent on any edited view→0. A hypothetical artifact-only detector firing on80% of T and20% of R gives ESG0.60 without lesion recognition. Those percentages are a counterexample constructed for the proof, not observed model results. The corrected claim should not call an image-processing edit detector “image blind.”

**Multiplicity and small samples.** Twenty-seven main comparisons have a Bonferroni threshold0.05/27=0.00185185, so if all truly have p<0.001 they would survive this conservative correction for that defined family. Thus lack of correction alone does **not** invalidate the primary result. Secondary p-values near0.05 are more vulnerable. With2,000 resamples, a doubled one-tail add-one estimate has minimum2/2001≈0.0009995; reporting strict p<0.001 can be legitimate at zero tail exceedances under that convention but needs its exact formula and Monte Carlo uncertainty. Do not report a computed p=0 as evidence of impossibility.

For 0/48 pneumothorax detections, a two-sided exact binomial95% interval has upper bound≈7.40%, conditional on independent cases and valid labels. For 0/32 residual findings in the planned erased-image reader sample, the analogous upper bound is≈10.89%; even no observed errors would not establish that residual disease is below5%. Multiple reads of the same32 images do not create more independent image cases. Source strata of20–64 images and150-case prompting subsets have even fewer positive eligible cases than their total sample size suggests. Report effect precision and do not label null differences equivalence.

## 6. Reference audit

**Status convention.** “Verified” below means bibliographic identity and the indicated broad use were supported by the linked primary source/record. It does not mean every sentence of the cited full text was verified. “Corrected” supplies an actual metadata correction/completion. “Not verified” means retrieval failed, the record was ambiguous, or the full cited mechanism was unavailable; it is not “nonexistent.” A Crossref query was attempted for every entry; many returned429 and some returned unrelated titles, which were rejected. This distinction avoids falsely accusing real references of being invented.

| Ref | Manuscript entry | Verdict | Evidence / correction and claim support |
|---|---|---|---|
|1|C. Li et al. LLaVA-Med: Training a large language-and-vision assistant for biomedicine in one day. NeurIPS Datasets and Benchmarks, 2023.|Verified|[Source](https://papers.neurips.cc/paper_files/paper/2023/file/5abcdf8ecdcacba028c6662789194572-Paper-Datasets_and_Benchmarks.pdf). Title/venue/year supported; biomedical instruction tuning supported. Does not establish that most questions in all cited benchmarks presuppose presence.|
|2|J. Chen et al. HuatuoGPT-Vision: Towards injecting medical visual knowledge into multimodal LLMs at scale. EMNLP, 2024.|Corrected|[Source](https://aclanthology.org/2024.emnlp-main.418/). Official title omits the prepended HuatuoGPT-Vision label. EMNLP2024,7346–7370; doi10.18653/v1/2024.emnlp-main.418.|
|3|A. Sellergren et al. MedGemma technical report. arXiv:2507.05201, 2025.|Partly verified|[Source](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card). Original report2507.05201 corroborated by developer references; exact original author list/full-text claims not independently audited.|
|4|Google Research and Google DeepMind (A. Sellergren, F. Mahvar et al.). MedGemma 1.5 technical report. arXiv:2604.05081, 2026. 16|Corrected|[Source](https://arxiv.org/abs/2604.05081). Sellergren et al.,2026; official report exists. Use developer-suggested author citation, not an improvised corporate/byline mixture.|
|5|LASA Team, W. Xu, H. P. Chan, L. Li et al. Lingshu: A generalist foundation model for unified multimodal medical understanding and reasoning. arXiv:2506.07044, 2025.|Partly verified|[Source](https://huggingface.co/lingshu-medical-mllm/Lingshu-7B/blob/e0dfc6cf4507844afdb0da0d5e494fd97ca0a524/README.md). Developer model card confirms title/report2506.07044. Full author/version metadata and detailed comparison not completely audited.|
|6|J. J. Lau et al. A dataset of clinically generated visual questions and answers about radiology images. Scientific Data, 2018.|Verified|[Source](https://www.nature.com/articles/sdata2018251). Lau et al.,Scientific Data2018,doi10.1038/sdata.2018.251. Dataset identity verified; exact prevalence assertion in manuscript needs a count.|
|7|B. Liu et al. SLAKE: A semantically-labeled knowledge-enhanced dataset for medical visual question answer- ing. ISBI, 2021.|Verified|[Source](https://ieeexplore.ieee.org/abstract/document/9434010). SLAKE title and ISBI2021 record found. Does not verify this study's regrouped splits.|
|8|X. He et al. PathVQA: 30000+ questions for medical visual question answering. arXiv, 2020.|Verified|[Source](https://arxiv.org/abs/2003.10286). He et al.,2020; add identifier2003.10286. Dataset paper, not proof of no replay leakage.|
|9|Y. Li et al. Evaluating object hallucination in large vision-language models. EMNLP, 2023.|Verified|[Source](https://aclanthology.org/2023.emnlp-main.20/). Li et al.,EMNLP2023; POPE absent-object questioning supported.|
|10|P. Xia et al. CARES: A comprehensive benchmark of trustworthiness in medical vision language models. NeurIPS, 2024.|Verified|[Source](https://proceedings.neurips.cc/paper_files/paper/2024/hash/fde7f40f8ced5735006810534dc66b33-Abstract-Datasets_and_Benchmarks_Track.html). Xia et al.,NeurIPS2024 Datasets and Benchmarks. Broad trustworthiness benchmark; blanket characterisation of all perturbations needs closer checking.|
|11|J. Chen et al. Detecting and evaluating medical hallucinations in large vision language models (Med-HallMark). arXiv, 2024.|Verified|[Source](https://arxiv.org/abs/2406.10185). Chen et al.,2024; add arXiv2406.10185. Benchmark/detector exists; detailed protocol comparison not fully audited.|
|12|Z. Gu et al. MedVH: Towards systematic evaluation of hallucination for large vision language models in the medical context. arXiv, 2024.|Verified|[Source](https://www.physionet.org/content/medvh/1.0.0/). Developer-hosted dataset confirms2024 preprint2407.02730; later journal version has updated metadata. Cite one specified version consistently.|
|13|A. Chang et al. MedHEval: Benchmarking hallucinations and mitigation strategies in medical large vision- language models. arXiv:2503.02157, 2025.|Verified|[Source](https://arxiv.org/abs/2503.02157). Chang et al.,2025; bibliographic identity verified, full mechanism comparison incomplete.|
|14|R. Suvorov et al. Resolution-robust large mask inpainting with Fourier convolutions. WACV, 2022.|Verified (metadata)|[Source](https://doi.org/10.1109/WACV51458.2022.00323). Crossref publisher-deposited record matches Suvorov,title,WACV2022. Does not establish medical validity of this study's LaMa outputs.|
|15|N. Zhou, K. Zou, M. Liu et al. Hallucination detection and correction in medical VLMs via counter-evidence verification. arXiv:2606.18609, 2026.|Not fully verified|[Source](https://arxiv.org/abs/2606.18609). Index results corroborate title/authors/ID, but primary page access failed. Blackout/counter-evidence mechanism not certified; do not label nonexistent.|
|16|X. Song, H. Qin, Z. Zhang et al. Detecting clinical hallucinations in LVLMs via counterfactual visual grounding uncertainty. arXiv:2606.28520, 2026.|Not fully verified|[Source](https://arxiv.org/abs/2606.28520). Index records corroborate identity, primary access failed. Especially verify whether perturbation is of entities/text or pixels before contrasting with this paper.|
|17|V. Agarwal, R. Shetty, M. Fritz. Towards causal VQA: Revealing and reducing spurious correlations by invariant and covariant semantic editing. CVPR, 2020.|Verified|[Source](https://openaccess.thecvf.com/content_CVPR_2020/html/Agarwal_Towards_Causal_VQA_Revealing_and_Reducing_Spurious_Correlations_by_Invariant_CVPR_2020_paper.html). Agarwal,Shetty,Fritz,CVPR2020. Invariant/covariant editing directly relevant; novelty must be incremental and precise.|
|18|A. Telea. An image inpainting technique based on the fast marching method. Journal of Graphics Tools, 2004.|Verified|[Source](https://research.tue.nl/en/publications/an-image-inpainting-technique-based-on-the-fast-marching-method/). Telea,Journal of Graphics Tools9(1),25–36,2004; doi10.1080/10867651.2004.10487596.|
|19|P. Pérez, M. Gangnet, A. Blake. Poisson image editing. ACM SIGGRAPH, 2003.|Verified (identity)|[Source](https://www.inf.ed.ac.uk/publications/report/1094.html). Pérez,Gangnet,Blake,2003. Poisson editing identity supported; does not validate transplanted tissue clinically.|
|20|R. Rombach et al. High-resolution image synthesis with latent diffusion models. CVPR, 2022.|Verified (metadata)|[Source](https://doi.org/10.1109/CVPR52688.2022.01042). Rombach et al.,CVPR2022. Generic diffusion-method reference; add exact inpainting checkpoint/scheduler/configuration used.|
|21|Z. Zheng et al. DeepEyes: Incentivizing “thinking with images” via reinforcement learning. ICLR, 2026.|Verified|[Source](https://proceedings.iclr.cc/paper_files/paper/2026/hash/cdb347d7516d52a9280ea9d6708911f6-Abstract-Conference.html). DeepEyes,ICLR2026 record found; publisher author spelling should be exported directly.|
|22|A. Su et al. Pixel Reasoner: Incentivizing pixel-space reasoning with curiosity-driven reinforcement learning. arXiv:2505.15966, 2025.|Verified (developer record)|[Source](https://github.com/TIGER-AI-Lab/Pixel-Reasoner). Developer README lists Alex Su and Haozhe Wang as co-first; author order differs across versions. Do not flag A.Su as fabricated. Pin the cited version2505.15966.|
|23|B. Li et al. MMedAgent: Learning to use medical tools with multi-modal agent. Findings of EMNLP, 2024.|Verified (metadata)|[Source](https://doi.org/10.18653/v1/2024.findings-emnlp.510). Li et al.,Findings EMNLP2024; medical tool-agent work. Full comparison not audited.|
|24|P. Xia et al. MMedAgent-RL: Optimizing multi-agent collaboration for multimodal medical reasoning. arXiv:2506.00555, 2025.|Verified|[Source](https://arxiv.org/abs/2506.00555). Xia et al.,2025; RL multi-agent collaboration, distinct from this single small agent recipe.|
|25|Z. Shao et al. DeepSeekMath: Pushing the limits of mathematical reasoning in open language models. arXiv, 2024.|Verified|[Source](https://arxiv.org/abs/2402.03300). Shao et al.,DeepSeekMath2024; add identifier2402.03300. Pilot GRPO claims still require this study's logs.|
|26|Q. Yu et al. DAPO: An open-source LLM reinforcement learning system at scale. NeurIPS, 2025.|Verified|[Source](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a4277440d50f1f15d2cb4c14f7e0c0d2-Abstract-Conference.html). Correct DAPO paper,NeurIPS2025; do not confuse another same-acronym paper. Dynamic sampling supported.|
|27|E. Zelikman et al. STaR: Bootstrapping reasoning with reasoning. NeurIPS, 2022.|Verified|[Source](https://proceedings.neurips.cc/paper_files/paper/2022/hash/639a9a172c044fbb64175b5fad42e9a5-Abstract-Conference.html). Zelikman et al.,NeurIPS2022; reasoning bootstrapping precedent, not exact identity of this reward/selection procedure.|
|28|Z. Yuan et al. Scaling relationship on learning mathematical reasoning with large language models. arXiv, 2023.|Verified|[Source](https://arxiv.org/abs/2308.01825). Yuan et al.,2023; add identifier2308.01825. Fine-grained methodological attribution requires full-text comparison.|
|29|Y. Geifman and R. El-Yaniv. Selective classification for deep neural networks. NeurIPS, 2017.|Verified|[Source](https://proceedings.neurips.cc/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf). Geifman/El-Yaniv,2017; selective classification precedent. Does not make token confidence calibrated.|
|30|A. S. Tejani et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. Radiology: Artificial Intelligence, 2024. 17|Verified|[Source](https://doi.org/10.1148/ryai.240300). Tejani et al.,Radiology:AI6(4),e240300,2024; AppendixC not full compliance.|
|31|Qwen Team. Qwen3.5 model card and technical report, 2026. [verify]|Corrected|[Source](https://huggingface.co/Qwen/Qwen3.5-4B). Official card exists. Cite the model card and actual revision; separate any technical report rather than inventing one.|
|32|E. J. Hu et al. LoRA: Low-rank adaptation of large language models. ICLR, 2022.|Verified|[Source](https://www.microsoft.com/en-us/research/publication/lora-low-rank-adaptation-of-large-language-models/). Hu et al.,ICLR2022; LoRA identity verified.|
|33|B. Efron and R. J. Tibshirani. An Introduction to the Bootstrap. Chapman & Hall, 1993.|Partly verified|[Source](https://www.cns.nyu.edu/~eero/math-tools14/Handouts/Efron-ch1%2B2.pdf). Book excerpt and catalogue records agree with Efron/Tibshirani,Chapman and Hall1993; implementation-specific bootstrap claims require code.|
|34|D. Jha et al. Kvasir-SEG: A segmented polyp dataset. MMM, 2020.|Verified|[Source](https://datasets.simula.no/kvasir-seg/). Jha et al.,MMM2020,451–462; official dataset citation and use restrictions available.|
|35|H. Borgli et al. HyperKvasir, a comprehensive multi-class image and video dataset for gastrointestinal en- doscopy. Scientific Data, 2020.|Verified (metadata)|[Source](https://doi.org/10.1038/s41597-020-00622-y). Borgli et al.,Scientific Data2020; exact metadata matches. Normal landmarks are not automatically an independently reviewed globally healthy cohort.|
|36|J. Lian et al. A structure-aware relation network for thoracic diseases detection and segmentation. IEEE Trans- actions on Medical Imaging, 2021.|Verified|[Source](https://pubmed.ncbi.nlm.nih.gov/33819152/). Lian et al.,TMI40(8),2042–2052,2021; ChestX-Det/NIH origin supported.2024 correction concerns subsection hierarchy, not demonstrated dataset invalidity.|
|37|X. Wang et al. ChestX-ray8: Hospital-scale chest X-ray database and benchmarks on weakly-supervised clas- sification and localization of common thorax diseases. CVPR, 2017.|Verified|[Source](https://openaccess.thecvf.com/content_cvpr_2017/html/Wang_ChestX-ray8_Hospital-Scale_Chest_CVPR_2017_paper.html). Wang et al.,CVPR2017; distinguish paper'sChestX-ray8 title from later14-label dataset release.|
|38|W. Al-Dhabyani et al. Dataset of breast ultrasound images. Data in Brief, 2020.|Verified (metadata)|[Source](https://doi.org/10.1016/j.dib.2019.104863). Al-Dhabyani et al.,Data in Brief2020;2019 in DOI does not make2020 year wrong.|
|39|M. Buda, A. Saha, M. A. Mazurowski. Association of genomic subtypes of lower-grade gliomas with shape features automatically extracted by a deep learning algorithm. Computers in Biology and Medicine, 2019.|Verified|[Source](https://pubmed.ncbi.nlm.nih.gov/31078126/). Buda,Saha,Mazurowski,2019; TCGA-LGG cohort origin verified; this study's split remains unverified.|
|40|J. Bernal et al. WM-DOVA maps for accurate polyp highlighting in colonoscopy. Computerized Medical Imag- ing and Graphics, 2015.|Corrected|[Source](https://pubmed.ncbi.nlm.nih.gov/25863519/). Restore subtitle: Validation vs. saliency maps from physicians;43:99–111,2015;doi10.1016/j.compmedimag.2015.02.007.|
|41|A. Degerli et al. COVID-19 infection map generation and detection from chest X-ray images. Health Informa- tion Science and Systems, 9:15, 2021.|Verified (metadata)|[Source](https://doi.org/10.1007/s13755-021-00146-8). Degerli et al.,Health Information Science and Systems2021; dataset identity not evidence that diffuse disease can be erased completely.|
|42|W. Gómez-Flores et al. BUS-BRA: A breast ultrasound dataset for assessing computer-aided diagnosis systems. Medical Physics, 2024.|Verified|[Source](https://aapm.onlinelibrary.wiley.com/doi/10.1002/mp.16812). Gómez-Flores et al.,Medical Physics51:3110–3123,2024.2023 online date is compatible with2024 issue date.|
|43|M. Adewole et al. The Brain Tumor Segmentation (BraTS) Challenge 2023: Glioma segmentation in sub- Saharan Africa patient population (BraTS-Africa). arXiv:2305.19369, 2023.|Not fully verified|[Source](https://arxiv.org/abs/2305.19369). Index/mirror identity consistent with Adewole/BraTS-Africa2023, but authoritative full source not retrieved here. No correction asserted.|
|44|M. Adewole et al. The BraTS-Africa dataset. Radiology: Artificial Intelligence, 2025, doi:10.1148/ryai.240528.|Corrected|[Source](https://pubs.rsna.org/doi/full/10.1148/ryai.240528). Restore full title: The BraTS-Africa Dataset: Expanding the Brain Tumor Segmentation Data to Capture African Populations;7(4):e240528,2025.|
|45|D. LaBella et al. The ASNR-MICCAI Brain Tumor Segmentation (BraTS) Challenge 2023: Intracranial menin- gioma. arXiv:2305.07642, 2023.|Not fully verified|[Source](https://arxiv.org/abs/2305.07642). Index record matches LaBella/meningioma2023; primary source not retrieved. Verify full author/version metadata and exact dataset subset.|
|46|N. Vallez et al. BUS-UCLM: Breast ultrasound lesion segmentation dataset. Scientific Data, 2025. [verify]|Corrected|[Source](https://www.nature.com/articles/s41597-025-04562-3). Vallez et al.,Scientific Data12:242,2025;doi10.1038/s41597-025-04562-3. Remove verify marker.|
|47|A. Zawacki et al. SIIM-ACR Pneumothorax Segmentation. Kaggle, 2019. [verify citation form]|Corrected/completed|[Source](https://www.kaggle.com/c/siim-acr-pneumothorax-segmentation/overview). Official citation: Anna Zawacki et al.,SIIM-ACR Pneumothorax Segmentation,Kaggle2019. Official SIIM page confirms NIH-origin images.|
|48|J. Silva et al. Toward embedded detection of polyps in WCE images for early diagnosis of colorectal cancer. International Journal of Computer Assisted Radiology and Surgery, 2014.|Verified (identity)|[Source](https://pubmed.ncbi.nlm.nih.gov/24037504/). Silva et al. title exists;2013 online publication versus2014 issue needs final publisher export. Exact association with sampled ETIS release not audited.|
|49|S. Bai et al. Qwen2.5-VL technical report. arXiv, 2025.|Verified|[Source](https://arxiv.org/abs/2502.13923). Bai et al.,2025; add identifier2502.13923 and cited version.|
|50|Qwen Team. Qwen3-VL technical report. arXiv, 2025.|Verified/completed|[Source](https://github.com/QwenLM/Qwen3-VL/blob/main/README.md). Developer citation identifies Qwen3-VL Technical Report,arXiv2511.21631,2025; use export and pin model revision.|

### Ready-to-paste bibliographic corrections/completions

Use the manuscript's existing citation keys in place of the descriptive keys below. These are bibliographic replacements, not edits made to the manuscript.

```latex
\bibitem{huatuo}
J. Chen et al. Towards Injecting Medical Visual Knowledge into Multimodal LLMs at Scale.
In: Proceedings of EMNLP, 2024, pp. 7346--7370.
\url{https://doi.org/10.18653/v1/2024.emnlp-main.418}.

\bibitem{medgemma15}
A. Sellergren et al. MedGemma 1.5 Technical Report.
arXiv:2604.05081, 2026.

\bibitem{wmDova}
J. Bernal et al. WM-DOVA maps for accurate polyp highlighting in colonoscopy:
Validation vs. saliency maps from physicians.
Computerized Medical Imaging and Graphics 43 (2015), 99--111.
\url{https://doi.org/10.1016/j.compmedimag.2015.02.007}.

\bibitem{bratsAfrica}
M. Adewole et al. The BraTS-Africa Dataset: Expanding the Brain Tumor
Segmentation Data to Capture African Populations.
Radiology: Artificial Intelligence 7(4) (2025), e240528.
\url{https://doi.org/10.1148/ryai.240528}.

\bibitem{busUclm}
N. Vallez, G. Bueno, O. Deniz, M. A. Rienda, C. Pastor.
BUS-UCLM: Breast ultrasound lesion segmentation dataset.
Scientific Data 12 (2025), 242.
\url{https://doi.org/10.1038/s41597-025-04562-3}.

\bibitem{qwen35card}
Qwen Team. Qwen3.5-4B model card. 2026.
\url{https://huggingface.co/Qwen/Qwen3.5-4B}.
% Add the exact revision hash used in the experiment; do not invent a technical-report ID.
```

Ref4's current corporate author is not fabricated, but the model developer's official suggested citation is Sellergren et al. Ref46 can have its “[verify]” marker removed after incorporating the verified record. Ref47 was subsequently resolved from the official Kaggle citation: Anna Zawacki, Carol Wu, George Shih, Julia Elliott, Mikhail Fomitchev, Mohannad Hussain, ParasLakhani, Phil Culliton and Shunxing Bao. SIIM-ACR Pneumothorax Segmentation. Kaggle,2019. Use the official export and record the dataset version/access date.

### Prior work and positioning still needed

**Directly missing:** He et al. (2025), *Evaluating and Mitigating Object Hallucination in Large Vision-Language Models: Can They Still See Removed Objects?*, NAACL,6841–6858, [doi:10.18653/v1/2025.naacl-long.349](https://aclanthology.org/2025.naacl-long.349/). Its removal-based evaluation and oDPO mitigation make it a particularly important baseline/positioning comparison. This does not establish that the medical matched-control contribution is identical; it does rule out treating removal plus mitigation as sufficient novelty.

- [Agarwal et al., causal VQA](https://openaccess.thecvf.com/content_CVPR_2020/html/Agarwal_Towards_Causal_VQA_Revealing_and_Reducing_Spurious_Correlations_by_Invariant_CVPR_2020_paper.html) is already cited. Strengthen the comparison rather than calling it missing: independently vary matched shape/tool, random-control training and insertions.
- [Multimodal foundation models exploit text to make medical image predictions](https://www.nature.com/articles/s41467-026-74207-5) directly relates to the motivation that text can dominate image evidence. Explain what the training intervention adds beyond documenting that phenomenon.
- Add [TRIPOD-LLM](https://www.nature.com/articles/s41591-024-03425-5) and [STARD-AI](https://www.nature.com/articles/s41591-025-03953-8), with study-appropriate checklists; CLAIM alone is not a substitute.
- Selective classification is already cited as ref29. Separate abstention, selective risk and probability calibration rather than treating AURC as calibration.
- A complete targeted search of medical lesion-removal augmentation and medical selective-prediction methods remains required. No unverified “missing paper” is invented here. The current report establishes that novelty must be narrowed, not that the method has already been published.

## 7. Three reviewer reports and public-review evidence

### 7.1 Public review material inspected

Two actual public peer-review files were downloaded and read before drafting the role reports:

- **PR-A:** *Multimodal Foundation Models Exploit Text to Make Medical Image Predictions*, Nature Communications, initial reviewers2,3 and5: [article](https://www.nature.com/articles/s41467-026-74207-5), [public review PDF](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-026-74207-5/MediaObjects/41467_2026_74207_MOESM3_ESM.pdf).
- **PR-B:** *On-Premise Medical AI Agents for Reliable Clinical Decision-Making*, Nature Medicine, initial reviewers1 and2: [article](https://www.nature.com/articles/s41591-026-04609-x), [public review PDF](https://static-content.springer.com/esm/art%3A10.1038%2Fs41591-026-04609-x/MediaObjects/41591_2026_4609_MOESM3_ESM.pdf).

OpenReview's Med-HallMark forum ([link](https://openreview.net/forum?id=WgpAFnjvPr)) returned a verification wall; both API routes returned403. The inspected npj Digital Medicine EVA-X page did not expose a review file. Therefore this is a **small convenience sample**, not a systematic review of MIDL/ICLR/NeurIPS/npj reviews. “Ten most frequent criticisms” across those venues cannot honestly be claimed. The ten applicable themes below are grounded in the accessible reports; frequencies and a ranking are intentionally not invented. Summaries are paraphrases, not quotations.

| Theme observed | Public-review location | Application here |
|---|---|---|
| External validity |PR-B, initial reviewers1–2, data/methods |Fresh datasets are valuable; verify patients/sites and limit clinical generalisation (F18,F22). |
| Excessive mechanism claims |PR-A, reviewer3, detailed remarks; PR-B reviewer1 conclusions |The ESG and coverage explanations require narrowing (F01,F17). |
| Reader expertise and adjudication |PR-A reviewer2; PR-B reviewer2 |Complete specialties, training and agreement (F15). |
| Clinically important failure analysis |PR-A reviewer2; PR-B reviewer2 |Pneumothorax analysis is a strength; add per-finding denominators and intervals. |
| Prompt/inference sensitivity |PR-A reviewers2–3; PR-B reviewers1–2 |Existing prompting tests help; finish native templates and settings (F13). |
| Cohort composition and selection |PR-A reviewer2 |Publish flow, demographics and unique groups (F10,F18). |
| CIs and threshold selection |PR-B reviewers1–2 |Replace placeholders and audit the selection chronology (F07,F12). |
| Confidence versus correctness |PR-B reviewer1, confidence framework |Token likelihood is not calibrated certainty; report AURC properly (F25). |
| Novelty against recent methods |PR-B reviewers1–2 |Direct removal/mitigation prior work needs explicit comparison (F19). |
| Compute and latency |PR-B reviewers1–2 |Complete costs and inference accounting; token/episode budgets matter (F20). |

### 7.2 Reviewer 1 — clinical radiology perspective (simulated)

**Summary.** The paper constructs lesion-erased and control-edited images from existing masks, then trains a small multimodal model to alter its answers appropriately. It reports fewer finding claims on erased and natural-negative images, but poorer external lesion detection and complete failure for pneumothorax. This is a research evaluation of response behaviour, not a clinical diagnostic validation.

**Strengths.** The control edit is more informative than an erased-only test. Natural negatives address one synthetic-data confound. The pneumothorax failure is reported in the abstract and examined in detail, rather than hidden in an aggregate score. The paper explicitly excludes unsupervised clinical use (§8.4).

**Major concern R1.1 — Does erasure establish absence?** At §§3.2–3.3 and8.5/F02, the reference standard fails in acknowledged examples. A masked polyp might be removed while another remains; an ultrasound lesion may be incompletely annotated; a brain tumour may leave mass effect or oedema; diffuse lung opacity and pleural signs are not necessarily contained within a mask. “No lesion pixel changed” in the control also does not guarantee that diagnostic context was preserved. Resolve with blinded expert adjudication of the asked finding, residual signs and control integrity, and re-score valid versus invalid counterfactuals. **Requires new human evaluation**, not merely adding a limitation already present.

**R1.2 — Reader study is too narrow for the claims.** Section7/F15 samples32 erasures across five groups and excludes random-removal controls. Reader numbers, expertise and ethics are blank. Include thoracic/breast/neuro-radiology and endoscopy expertise as appropriate, multiple independent readers per relevant modality, disagreements/cannot-tell handling, a consensus rule and case-level CIs. Separate clinical validity from edit visibility. An AUC near0.70–0.75 is not an acceptance criterion for clinical absence and still indicates detectable editing. Add a precision-based sample-size plan. **Requires new evaluation and protocol completion.** Real paired pre/post images may be useful additional evidence but are not automatically perfect counterfactuals because interventions and time change other features.

**R1.3 — Clinical task and reward.** §§3.1,3.4/F16 evaluate single-image, question-conditioned presence with an artificial reward. It can audit a system component but is not a task that can be safely delegated on this evidence. Explain intended users and workflow. Table1 does distinguish critical misses (−4 versus−2), so the criticism is not that all harms are identical; it is that the critical list, relative weights and grounding/tool bonuses lack clinical elicitation. Report sensitivity/specificity and false positives separately. **Rewriting and reanalysis; clinician elicitation if a clinical-utility claim is retained.**

**R1.4 — Pneumothorax and deployment.** Section6 documents a dangerous condition-specific failure. No reader should infer safety from lower erased-lesion claims. Keep the failure prominent; include its denominator and CI, and limit the causal diagnosis. Add prespecified critical-finding coverage and sensitivity floors only for a future model, with new locked testing; do not tune on this SIIM cohort and relabel it confirmatory. **Rewriting now; new experiments for a corrected model.**

**Minor concerns.** Use “target finding absent” rather than globally healthy when labels are condition-specific; distinguish mask area from box area; report native image acquisition/resolution; clarify why external COVID cases are allowed despite the exclusion of diffuse training disease; verify Figure2 provenance.

**Recommendation: reject in current form, with encouragement to resubmit after reference-standard validation. Confidence: high for the clinical-validity concern; moderate overall because this is a simulated perspective without access to source images or a completed specialist study.**

### 7.3 Reviewer 2 — machine-learning methods perspective (simulated)

**Summary.** This is a counterfactual augmentation recipe using target erasure, matched irrelevant-region edits, negatives and insertion examples, followed by supervised/rejection-sampled training and general-VQA replay. A behaviour-difference metric rewards changing responses between target and control views. The empirical claim is plausible and interesting, but the claimed shortcut immunity and causal interpretation are not established.

**Strengths.** Three-seed primary ablations, an absent-share control, a second backbone and unseen inpainting tools are complementary checks. Reworded prompts and tool refusal probe different components. The manuscript openly reports that stages2/3 add little on the internal test and can suppress rare-finding sensitivity.

**Major concern R2.1 — Novelty.** §§2,8.3/F19 should compare not just with POPE and Causal VQA, but with He et al., NAACL2025, *Evaluating and Mitigating Object Hallucination in Large Vision-Language Models: Can They Still See Removed Objects?* ([publisher record](https://aclanthology.org/2025.naacl-long.349/)). That work removes objects for evaluation and proposes oDPO for mitigation. Thus removal plus mitigation is not itself new. Position the contribution around medically validated matched controls, the training recipe and the demonstrated tradeoff; implement a relevant adaptation/comparison where feasible. **Requires rewriting and likely a direct baseline.**

**R2.2 — ESG is not a shortcut-proof certificate.** §§3.2,5.4/F01,F09 conflate a binary edit flag with any edit detector. Editing in abnormal tissue can differ systematically from editing elsewhere. A frozen encoder does not remove artifact information from its embeddings. An LLM judge's clean-looking subset is neither independent clinical validation nor proof of imperceptibility. Test anatomy-conditioned artifact probes, matched nonlesional fills, randomised placement and other construction changes on a locked set. **Requires corrected theorem and targeted experiments.** A fourth arbitrary inpainting engine is less informative than a test designed to break the actual shortcut hypothesis.

**R2.3 — Ablations identify a recipe, not every component.** §§4.2,5.3/F08,F30 remove multiple ingredients in the erasures-only arm and do not explain how the same draw remains matched when view kinds are removed. Publish exposure weights and add a factorial control/insertion experiment. Three seeds support a consistent observed direction but do not precisely characterise the unstable no-counterfactual arm. **Requires exact reporting and a limited new ablation.**

**R2.4 — Baseline fairness.** §§3.9,4.2,5.5/F13,F14,F26 do not supply complete model-specific processors/chat templates, output budgets, provider image-detail settings or parser fallback rates. A common generic plain prompt is not each model's own native protocol. Resolution is especially relevant for subtle signs. Provide a common-protocol comparison plus validated native-template sensitivity analyses, recording run IDs and immutable model versions. **Requires reporting and some sensitivity reruns.**

**R2.5 — Benchmark adaptation.** §4.2 puts main frontier evaluation before v4 registration. Training on the same construction as testing is legitimate supervised learning when splits are clean, but cannot independently prove robustness beyond that construction. Fresh external sources still use the same image edits and therefore only partially address this. Publish what was known before v4 and test one prospectively fixed construction-shift condition. **Requires audit records; experiments if general robustness retained.**

**Minor concerns.** Report grounded accuracy, AURC and parser failures if advertised; fill the QC criterion; clarify the exact status of stage2 as rejection sampling rather than successful GRPO training; remove the all-open erased-rate claim contradicted by Qwen2.5-VL-7B.

**Recommendation: major revision, conditional on an auditable release and completion of label validation; otherwise reject. Confidence: high on the mathematical and internal-table issues, moderate on empirical validity.**

### 7.4 Reviewer 3 — biostatistics perspective (simulated)

**Summary.** The manuscript uses paired case bootstrap comparisons across multiple models and several synthetic-view endpoints. The main internal contrasts are large, but the estimands, resampling units, multiplicity families and equivalence language require clarification. Several secondary subgroup studies are small and primarily descriptive.

**Strengths.** Pairing is recognised; difference CIs are presented in Table5; training variability is reported over three seeds; negative generalisation results are retained. Both reported Fisher tests reproduce from the printed counts.

**Major concern R3.1 — Sampling unit.** §3.8/F10 needs patient/group identifiers. Bootstrapping each case with all its views handles within-case correlation but not multiple images from one patient, scan or video. This matters especially for MRI slices and ultrasound sequences. Use a paired group bootstrap and report group counts and weighting; retain paired cases across models. **Reanalysis from existing predictions.**

**R3.2 — Null findings.** §5.1 and conclusion/F04 do not demonstrate equality. Table5 includes losses of several percentage points consistent with the data. Replace matching/equivalent language. Fresh internal comparisons also do not universally favour frontier CCR or MedScope utility. **Rewriting; an equivalence study requires a justified margin and adequate precision.**

**R3.3 — Uncertainty/multiplicity.** §3.8/F11,F12 should provide the exact bootstrap p-value formula, primary-family definition and adjusted results. The reported p<0.001 primary results would pass Bonferroni for27 tests if verified; the near0.05 secondary findings need more caution. Provide95% CIs for absolute metrics and source-specific counts. **Reanalysis and reporting.**

**R3.4 — Seeds and causal evidence.** Table7/F31 reports only three-run summaries; a large SD0.107 in the no-counterfactual ESG means the run distribution is uncertain. The brief mentions one seed around0.40 and others around0.21–0.22, but those individual values are not in the supplied PDF and cannot be verified here. Case bootstrap p-values conditional on checkpoints are not confidence intervals over future training seeds. Show each run and pair, and do not pool seed-case observations as independent. **Reporting, with more runs desirable for the unstable arm.**

**R3.5 — Reader study and post-hoc selection.** Section7/F15 must set a clinical validity target, sample-size calculation, handling of uncertain labels and reader/case dependence. Two-sided exact upper bounds illustrate that32 erasures cannot validate a very low failure rate with precision. Report the six SIIM positives absent from the42-case full-resolution subset and reasons for their exclusion; post-hoc mechanism claims remain exploratory. **Protocol improvement, new reads and transparent subset accounting.**

**R3.6 — Confidence evaluation.** §3.7/F25 needs an explicit risk event, tie convention and actual AURC results. AURC measures ordering for selective prediction, not probabilistic calibration. Confidence≈1 on false SIIM negatives is an important failure, but calibration requires reliability/Brier/log-loss evaluation with a clearly defined probability. **Reanalysis if scores exist; otherwise remove unreported metric.**

**Minor concerns.** Report source-level denominators for each endpoint, multiplicity-adjusted exploratory summaries separately, and both original and adjudicated cohorts. Correct the direction-reversal claim; show missing/malformed action handling. Do not infer exact numerators from rounded percentages.

**Recommendation: major revision. Confidence: high for arithmetic, estimand and equivalence criticisms; moderate for implementation-dependent questions.**

## 8. Reporting-guideline checklists

These assess **reporting in the supplied PDF**, not whether unprovided implementation passes. “Met” can describe a clearly reported method even when its factual execution is unverified. “Partly met” indicates a substantive omission; “not met” means absent/incomplete in this draft. No clinical-trial registration is inferred from a Git document. Topics below are compact paraphrases; consult linked originals for exact wording.

### 8.1 CLAIM 2024 — all 44 items

Source: [RSNA's CLAIM 2024 item list](https://rsna.github.io/claim/checklist.html), [2024 publication](https://doi.org/10.1148/ryai.240300). AppendixC of the manuscript is a summary, not a completed44-item checklist.

| Item | Topic | Status | PDF evidence / gap |
|---|---|---|---|
|1|AI identification|Met|Title and abstract identify a VLM.|
|2|Summary|Partly met|Abstract structured; important utility harm and uncertainty missing.|
|3|Motivation|Met|§§1–2 give context and research purpose.|
|4|Objectives|Met|§1 contributions.|
|5|Design timing|Met|§4.1 retrospective.|
|6|Study purpose|Met|§§1,8.4 research use stated.|
|7|Sources|Met|§4.1, Tables2–3; provenance verification separate.|
|8|Eligibility|Partly met|§§3.2,4.1; QC placeholder and split-specific exclusions unclear.|
|9|Processing|Partly met|§§3.2–3.3; exact QC/resize details absent.|
|10|Subsampling|Partly met|Tables3,8–9; sampled IDs/rationale absent.|
|11|De-identification|Partly met|Declarations assert public de-identified data; source process not detailed.|
|12|Missingness|Not met|No comprehensive handling of missing images/masks/failed requests.|
|13|Acquisition|Partly met|Modalities/sources given; scanner/protocol details missing.|
|14|Truth construction|Partly met|§3.2 explains derived labels; erased-image validity unresolved.|
|15|Truth rationale|Partly met|Public masks convenient; clinical adequacy not established.|
|16|Annotation origin|Partly met|Expert source labels cited, per-source annotator details absent.|
|17|Test annotation|Partly met|§4.1 rules; no completed independent reading.|
|18|Reader variation|Not met|§7 planned κ; no results.|
|19|Allocation|Partly met|§§3.3,4.1; split counts and exact manifests incomplete.|
|20|Disjointness|Partly met|Table2 levels; cross-source and replay proof absent.|
|21|Sample planning|Not met|No precision/power rationale for test/reader cohorts.|
|22|Architecture|Partly met|§3.5; model/processor revisions and complete modules missing.|
|23|Software|Met|§4.3 versions reported; execution unverified.|
|24|Initialisation|Partly met|Base checkpoint named; immutable hash/seed values missing.|
|25|Optimisation|Partly met|§3.5; batch/accumulation/packing and effective exposures absent.|
|26|Selection|Partly met|§3.6 rule explicit; amendment audit unavailable.|
|27|Ensemble|Not applicable|Final predictor is one selected checkpoint, not a model ensemble.|
|28|Endpoints|Partly met|§3.7; action edge cases and AURC risk incompletely specified.|
|29|Inference|Partly met|§3.8; patient clustering and p-value details needed.|
|30|Stress tests|Met|§§5.3–5.5 describe multiple analyses; some claims need narrowing.|
|31|Explanations|Partly met|Boxes/tool use described; rationale faithfulness not validated.|
|32|Internal testing|Met|§5.1, Tables4–7.|
|33|External testing|Met|§5.6, Tables10–11; independence unverified.|
|34|Trial registry|Not applicable|Retrospective model study, not a clinical trial. Reader ethics still applies.|
|35|Case flow|Partly met|Tables2–3 counts; no full inclusion/exclusion flow.|
|36|Cohort descriptors|Not met|§8.5 acknowledges limited demographics; no per-partition table.|
|37|Performance|Partly met|Extensive results but incomplete intervals/subgroups.|
|38|Precision|Partly met|Table5 difference CIs; most absolute/source intervals missing.|
|39|Failures|Partly met|§6 strong analysis; full per-finding confusion tables absent.|
|40|Limitations|Met|§8.5 comprehensive; some corresponding claims remain too strong.|
|41|Practice implications|Met|§§8.2,8.4 distinguish research from deployment.|
|42|Protocol access|Partly met|AppendixB path supplied; archive not accessible here.|
|43|Artifact access|Partly met|Declarations; weights/manifests promised on acceptance.|
|44|Support|Met|Declarations: no external funding.|

### 8.2 TRIPOD-LLM — all rows of the retrieved official checklist assessed

Source: [official Table2](https://www.nature.com/articles/s41591-024-03425-5/tables/2). The article describes50 subitems, but the retrieved official Table2 exposes49 numbered rows; all49 are mapped below, with none omitted from that table. This source-count discrepancy is not silently repaired by inventing an item. Fine-tuning plus retrospective evaluation applies; this is not an implemented clinical-care outcome study. Where an item is specific to deployment or clinical outcomes, that scope is stated rather than imposing an irrelevant requirement.

| Item | Topic | Status | PDF evidence / gap |
|---|---|---|---|
|1|Identification|Partly met|Title identifies model/training, not a precise target population.|
|2|Abstract|Partly met|Structured but overlong and lacks key uncertainty.|
|3a|Rationale|Met|§§1–2.|
|3b|Care context|Partly met|Research-only §8.4; intended clinical user/task not operationalised.|
|4|Objectives|Met|§1.|
|5a|Data origin|Met|§4.1, Tables2–3.|
|5b|Distributions|Partly met|Counts/modalities; demographics and country distributions absent.|
|5c|Data dates|Not met|Collection/text ranges and base pretraining cutoffs absent.|
|5d|Cleaning|Partly met|§3.3 QC placeholder; source-specific procedures incomplete.|
|5e|Missing/imbalanced|Partly met|Some reweighting described; missingness not systematically reported.|
|6a|Model identity|Partly met|§4.2; immutable API/checkpoint versions and cutoff dates missing.|
|6b|Development|Partly met|§3.5; training implementation incomplete.|
|6c|Generation|Partly met|§3.9/AppendixA; defaults, tokens and template examples incomplete.|
|6d|Outputs|Met|§§3.1,3.9 describe actions and parsing at a high level.|
|6e|Decision rules|Partly met|§§3.6–3.7; confidence thresholds/parser mapping not exhaustive.|
|7a|Output quality|Partly met|Presence/grounding endpoints; no complete human assessment.|
|7b|Task validity|Partly met|Utility assumptions stated; correlation with human judgment unavailable.|
|7c|Metric construction|Partly met|§§3.7–3.9/API date; code unavailable and edge cases unresolved.|
|7d|Assessors|Not met|§7 reader credentials/results blank.|
|7e|Comparisons|Met|§4.2; numerous baselines and paired analysis described.|
|8a|Labelling rules|Partly met|§3.2; inherits human source labels; protocol details incomplete.|
|8b|Annotator agreement|Not met|No source-level/review agreement data.|
|8c|Annotator background|Partly met|Dataset experts cited, reader details pending; model-panel identities given.|
|9a|Prompt selection|Partly met|AppendixA prompts; design/selection history incomplete.|
|9b|Prompt-development data|Partly met|Training examples named generally; exact examples/IDs missing.|
|10|Summarisation|Not applicable|Task is finding-question answering, not summarisation.|
|11|Alignment evaluation|Partly met|Label-derived trajectories described; exact templates/interface details incomplete.|
|12|Compute|Partly met|§4.3/AppendixB hardware and timings; API cost blank.|
|13|Ethics|Partly met|Public-data rationale; reader-study determination/consent pending.|
|14a|Funding|Met|Declarations.|
|14b|Conflicts|Met|Declarations.|
|14c|Protocol|Partly met|Path supplied; inaccessible, though not a clinical implementation study.|
|14d|Registration|Partly met|Git pre-registration asserted; clarify non-registry status and chronology.|
|14e|Data access|Partly met|Sources cited, derived artifacts promised later.|
|14f|Code access|Partly met|Repository URL; access unsuccessful.|
|15|Public involvement|Not applicable|No care-setting implementation; adding an explicit no-involvement statement would improve clarity.|
|16a|Data flow|Partly met|Image/question counts; no patient flow/exclusion diagram.|
|16b|Population details|Partly met|Source counts; dates/demographics incomplete.|
|16c|Clinical outcomes|Not applicable|No downstream patient outcomes evaluated.|
|16d|Analysis denominators|Partly met|Case totals provided; eligible positive/negative/group counts incomplete.|
|17|Results|Partly met|Tables extensive; pending AURC/human validation/CIs.|
|18|Updating results|Met|§§3.6,5.3,6 report sequential stages and failure.|
|19a|Interpretation|Partly met|§8; fairness and causal scope need work.|
|19b|Limitations|Met|§8.5.|
|19c|Data challenges|Partly met|§§6,8.5; missingness/harmonisation not fully discussed.|
|19d|Implementation role|Not applicable|No clinical implementation; research-only statement is present.|
|19e|Input handling in care|Not applicable|Synthetic degradation tests are not clinical implementation evidence.|
|19f|User expertise in care|Not applicable|No deployed end-user evaluation; §7 reader expertise still missing.|
|19g|Next steps|Met|§8.6.|

### 8.3 STARD-AI — all 40 numbered items, including subitems

Source: [official Table2](https://www.nature.com/articles/s41591-025-03953-8/tables/2). Applicable to diagnostic-accuracy interpretations of finding detection. The synthetic task is not automatically a clinical diagnostic-accuracy study.

| Item | Topic | Status | PDF evidence / gap |
|---|---|---|---|
|1|Identification|Partly met|Abstract reports AI performance; diagnostic estimand unclear.|
|2|Summary|Partly met|Structured; uncertainty/flow incomplete.|
|3|Clinical role|Partly met|§1/§8.4; no intended care workflow.|
|4|Objectives|Met|§1.|
|5|Timing|Met|§4.1 retrospective.|
|6|Ethics|Partly met|Declarations; reader component incomplete.|
|7|Eligibility|Partly met|§§3.2–3.3,4.1; ordered exclusions/QC absent.|
|8|Identification|Partly met|Dataset-based cases; detailed sampling not given.|
|9|Setting/dates|Partly met|Source names; acquisition dates/settings missing.|
|10|Sampling series|Partly met|Subsets described without complete selection mechanism.|
|11|Provenance|Met|§4.1 public sources.|
|12|Annotation|Partly met|Inherited masks/labels; expertise and clinical context not detailed.|
|13|Devices/software|Partly met|Software §4.3, source scanner details absent.|
|14|Acquisition/processing|Partly met|Edits specified partly; QC missing.|
|15a|Index test|Partly met|§§3.1,3.5,3.9; exact templates/revisions absent.|
|15b|Development sets|Partly met|Training totals/test sets; full split/group counts missing.|
|15c|Categories|Partly met|Actions/correctness described; parser edges absent.|
|15d|Users|Not applicable|No clinical deployment; research role only.|
|16a|Reference test|Partly met|§3.2; no validated erased labels.|
|16b|Reference rationale|Partly met|Mask-based derivation not sufficient for clinical absence.|
|16c|Reference categories|Partly met|Expected answer rules given; multiple/secondary findings unresolved.|
|17a|Index-test masking|Partly met|Prompt given, no label access stated implicitly; confirm implementation.|
|17b|Reference masking|Partly met|§7 reader blinding planned; source annotation conditions absent.|
|18|Statistical methods|Partly met|§3.8; cluster/p-value gaps.|
|19|Indeterminate outcomes|Partly met|Refer/clarify scores; clinically uncertain labels unresolved.|
|20|Missing observations|Not met|No comprehensive missing/failure handling.|
|21|Variability analyses|Partly met|Many analyses; confirmatory/exploratory taxonomy incomplete.|
|22|Sample size|Not met|No rationale.|
|23|Error/bias methods|Partly met|§6 failure analysis; demographic fairness missing.|
|24|Participant flow|Not met|Counts only, no full diagram.|
|25|Baseline descriptors|Partly met|Sources/modalities; demographic/technical table absent.|
|26a|Disease spectrum|Partly met|Area quartiles and SIIM details; severity by condition missing.|
|26b|Alternative disease|Not met|Natural-negative labels do not establish full disease spectrum.|
|27|Interval/intervention|Not applicable|Static source image reused; no prospective clinical test interval.|
|28|Representativeness|Partly met|§8.5 limits; artificial cohort prevalence not related to target care population.|
|29|External differences|Partly met|Table3 modality/site intentions; detailed population comparison absent.|
|30|Cross-tabulations|Not met|No complete per-finding/action confusion matrices.|
|31|Accuracy precision|Partly met|Table5 difference intervals only; absolute precision incomplete.|
|32|Adverse events|Not applicable|No patient-facing intervention; hypothetical harms still discussed.|
|33|Limitations|Met|§8.5.|
|34|Practice meaning|Met|§§8.2,8.4,8.6 explicitly limit use.|
|35|Ethics/fairness|Partly met|Public data and safety caveat; bias/licences/readers incomplete.|
|36|Registration|Partly met|Git document, no registry claim independently verified.|
|37|Protocol|Partly met|AppendixB references unavailable protocol/history.|
|38|Support|Met|Declarations.|
|39|Commercial interests|Met|Declarations state none.|
|40a|Reproducibility access|Partly met|Code link and promised artifacts; restrictions not tabulated.|
|40b|Auditable outputs|Partly met|AppendixB says stored transcripts; not available here.|

### 8.4 STARD 2015 crosswalk — all applicable original items

Source: [official STARD2015 checklist via EQUATOR](https://www.equator-network.org/wp-content/uploads/2015/03/STARD-2015-checklist.pdf). The STARD-AI table above supplies detailed evidence; this crosswalk avoids silently substituting the newer numbering for the original.

| STARD2015 | Status | Evidence / corresponding STARD-AI item |
|---|---|---|
|1|Partly met|AI1; diagnostic-accuracy framing.|
|2|Partly met|AI2; abstract uncertainty.|
|3|Partly met|AI3; intended role.|
|4|Met|§1; AI4.|
|5|Met|§4.1; AI5.|
|6|Partly met|AI7 eligibility.|
|7|Partly met|AI8 case identification.|
|8|Partly met|AI9 setting/dates.|
|9|Partly met|AI10 sampling.|
|10a|Partly met|AI15a index test.|
|10b|Partly met|AI16a reference standard.|
|11|Partly met|AI16b rationale.|
|12a|Partly met|AI15c categories.|
|12b|Partly met|AI16c reference thresholds.|
|13a|Partly met|AI17a masking.|
|13b|Partly met|AI17b masking.|
|14|Partly met|AI18 statistical methods.|
|15|Partly met|AI19 indeterminates.|
|16|Not met|AI20 missingness.|
|17|Partly met|AI21 variability.|
|18|Not met|AI22 sample size.|
|19|Not met|AI24 flow.|
|20|Partly met|AI25 demographics.|
|21a|Partly met|AI26a severity.|
|21b|Not met|AI26b alternative diagnoses.|
|22|Not applicable|AI27 static images.|
|23|Not met|AI30 cross-tabulations.|
|24|Partly met|AI31 precision.|
|25|Not applicable|AI32 no intervention.|
|26|Met|AI33 limitations.|
|27|Met|AI34 implications/research-only role.|
|28|Partly met|AI36 Git registration requires chronology.|
|29|Partly met|AI37 protocol access.|
|30|Met|AI38 funding.|

### 8.5 Journal requirements

The current official [CBM author guide](https://www.sciencedirect.com/journal/computers-in-biology-and-medicine/publish/guide-for-authors) returned403/blocked content; a [publisher-branded archived guide](https://dl.icdst.org/pdfs/files/90f9373bdf47f1a5ab063c2c6d7f0c00.pdf) supports the commonly listed250-word abstract and3–5 highlights of at most85 characters each, but current policy is **not independently certified**. The same caution applies to exact current limits for other journals. Do not invent a body word limit or assert that structured headings are mandatory everywhere.

| Requirement | Status for this draft | Action |
|---|---|---|
|Structured abstract|Met as a format|Background/Methods/Results/Conclusions present; confirm selected journal's headings.|
|Abstract length|Not met against250-word guide|≈338 words after dehyphenation; shorten and count in final source.|
|Highlights|Partly met|Five bullets; all over85 characters; supply separate editable file.|
|Body/page limit|Unverified|19-page custom draft cannot be converted to journal template length by assumption.|
|Data/code statement|Partly met|Present; ensure reviewer access now and define release/licence conditions.|
|CRediT|Partly met|Author roles present; reader contributor plan unresolved.|
|Competing interests|Met|Explicit declaration.|
|Funding|Met|Explicit no-external-funding statement.|
|Ethics/consent|Partly met|Public-data rationale; reader consent and ethics position blank.|
|Generative-AI writing use|Not met|Literal placeholder. State actual use according to chosen publisher policy.|
|Editable tables/figures|Unverified|Only PDF supplied; manuscript citations for all3 figures and13 tables were found.|
|Reporting checklists|Partly met|AppendixC is only a summary; replace with completed official forms.|
|References|Partly met|Several corrected/unfinished entries, see§6.|

[Artificial Intelligence in Medicine's publisher scope](https://shop.elsevier.com/journals/artificial-intelligence-in-medicine/0933-3657) explicitly emphasises both medical impact and AI-method novelty; simply increasing the count of VLM comparisons would not resolve either concern. Current JBHI and stretch-journal submission-format requirements were not fully retrieved and must be checked before formatting a submission. The decision estimates in§1 are scientific-fit judgments, not verified editorial policies.

## 9. Claim and language audit

These are proposed replacement passages, not edits applied to the manuscript. Quoted old wording is exact after joining PDF line wraps. Replacements are conditional on the printed results being verified.

| Location / finding | Old wording | Evidence-supported replacement |
|---|---|---|
|Abstract, F01|“it is zero for any model that ignores the image or only detects edits”|“For paired identical questions, ESG is zero for deterministic text-only policies and policies responding only to a shared binary edit flag; this does not exclude richer artifact-based strategies.”|
|Highlights, F01|“The evidence sensitivity gap is zero for every image-blind strategy, including edit detection.”|“Paired controls test whether responses change beyond a shared binary edit cue.”|
|§1, F01|“Only a model that reads the lesion can treat the two differently.”|“Different responses are consistent with lesion sensitivity, although unequal editing artifacts or anatomical context can also contribute.”|
|§1 contribution2, F01|“zero for every image-blind strategy (always yes, always no, always abstain, react to edits)”|“zero for constant-response policies and, in expectation, for image-blind policies on identically paired questions.”|
|§3.2, F01|“so learning to detect edits earns nothing”|“A policy responding only to whether any edit occurred cannot distinguish target from control views; richer edit cues remain possible.”|
|Fig.1 caption, F01|“so detecting edits earns nothing”|“Natural negatives test behaviour on unedited absent-finding images; this does not make every artifact-based policy uninformative.”|
|§5.4, F01|“an edit detector scores ESG 0 by construction”|“A detector that outputs the same edit flag for target and control views scores ESG0; actual edit-detector response distributions need empirical evaluation.”|
|§5.4, F09|“cannot learn a pixel-level detector of the kind the ResNet-18 learns”|“The frozen encoder prevents updates to visual feature extraction, but the adapter may still exploit artifact information already encoded in those features.”|
|§5.1, F03|“the lowest erased-lesion claims (9.6%) of any model that answers”|“Lower erased-lesion claims than all frontier comparators (9.6% versus41.1–61.6%); Qwen2.5-VL-7B has a lower rate but much poorer CCR.”|
|§5.1, F03|“better than all nine frontier and all six open models on ESG, erased-lesion claims and net utility”|“Higher ESG and net utility than the reported frontier and open comparators, and fewer erased-lesion claims than all frontier models.”|
|§1 contribution3 /§9, F04|“while matching their accuracy on real lesions”|“with no statistically significant internal-test CCR differences; equivalence was not established.”|
|§5.2, F24|“The advantage holds in every imaging type”|“The ESG and erased-claim advantages over the three flagships are observed in every source group; utility does not uniformly improve.”|
|§5.3, F08|“The control edit matters.”|“The combined control-edit/insertion recipe reduces denial of intact lesions relative to the erasures-only arm; the independent contribution of each component remains unresolved.”|
|§5.3, F31|It is not the share of “No” answers.|“Matching the absent-target share in the tested arm did not reproduce the recipe's ESG gain.”|
|§5.4, F09|“its advantage should vanish on other tools”|“Persistence on other tools tests transfer beyond the training tools, but does not rule out shared artifact cues.”|
|§5.5, F05|“every comparison in Table 5 keeps its direction and significance”|“The Gemini healthy-image point-estimate difference reverses after exclusion; report the updated paired intervals and significance for each comparison.”|
|§5.5, F21|“an independent panel”|“a comparator-model consensus panel, independent of MedScope voting but not a clinical reference standard.”|
|§5.5, F13|“so the agent loop does not handicap them on this task”|“The tested generic plain-prompt condition increases erased-lesion claims; this alone does not establish fairness across all metrics or native prompting protocols.”|
|§5.6, F22|“but the flagships detect more real lesions”|“Frontier CCR is higher on the pooled external-centre and fresh-external sets, but the fresh-internal comparisons are mixed.”|
|§5.6, F04|“this shows the absence of a regression”|“Aggregate VQA accuracy exceeds the base model's on these tested benchmarks after replay; subgroup preservation and equivalence were not established.”|
|§6, F17|“Resolution is not the cause.”|“Increasing resolution did not restore detection in the final model on the42 recovered positives, although earlier checkpoints improved.”|
|§6, F17|“Counterfactual training is not the cause.”|“The stage1 counterfactual arm performs better than the no-counterfactual arm on these cases; this does not exclude interactions with later training.”|
|§6, F17|“Training coverage is.”|“Low positive pneumothorax coverage and loss of detection after stage3 are plausible contributors.”|
|§6, F17|“The final model sees that something is abnormal but does not name pneumothorax.”|“The model more often predicts a generic abnormality on positive than negative SIIM images; this does not identify which visual cue it uses.”|
|§7, F15|“The benchmark’s assumptions are supported if readers rarely see the erased finding”|“Estimate the residual target-finding rate and its confidence interval against a prespecified acceptability criterion; assess edit visibility separately.”|
|§8.1, F08|the ablations identify those views — not the data, the answer format or the share of “No” answers — as the active ingredient|“The tested ablations support an effect of the counterfactual recipe; they do not identify every component or rule out residual shortcuts.”|
|§8.1, F02|“the recipe extends to any dataset with segmentation labels”|“The recipe may extend to datasets whose masks permit clinically valid removal and matched controls; this must be evaluated for each task.”|
|§8.5, F08|“which isolates the views as the cause”|“which supports a contribution of the view recipe under the tested training design.”|
|§9, F04/F22|“a 4B agent matches nine frontier models on real lesions”|“The4B agent had no statistically significant CCR differences from the nine frontier models on the internal benchmark, while external sensitivity was lower.”|
|§9, F17|“the fix belongs in data coverage and model selection, not in prompting”|“Data coverage and selection safeguards are priority hypotheses for repair; a successful fix remains to be demonstrated on new held-out data.”|
|Title/abstract/§9, F28|“without human annotation”|“without additional manual annotation of the generated views, using existing expert masks and labels.”|

**Prominence of limitations.** Pneumothorax failure, external sensitivity loss and limited perception are already in the abstract; do not criticise them as hidden. The fresh-external net-utility loss versus Gemini, missing reader validation, residual edit cues and inherited label uncertainty are in the body but not adequately reflected in the abstract. The conclusion's internal-accuracy claim loses its internal-set qualifier. The abstract's strong causal coverage diagnosis should be softened to match §6's own acknowledgement that coverage may not be the whole explanation. There is no demonstrated “clinically safe” or “first” claim to invent and attack.

**Terminology/readability.** The first-page paired-edit idea is clear. Define “evidence sensitivity” as the operational response contrast rather than a direct measure of visual understanding; expand CCR, ESG and AURC on first use. Distinguish “case,” “image,” “patient,” “view,” “centre” and “dataset.” The prose mainly uses British spelling (behaviour, centre, optimiser); preserve that consistently while leaving official paper/model titles untouched. Use a consistent full model name or a declared short-name key. “Own/native prompt” should become “generic plain prompt” unless actual model-specific templates are supplied. Table6's erased rate is a fraction, unlike percent tables; state this visibly or harmonise units.

**Figures and tables.** All3 figures and13 tables have text references and appear in numbered order in the rendered draft. Table1 is first mentioned on p.4 and printed on p.5, which is normal float placement. Figure2 was visually inspected: source labels are present, the second breast-ultrasound dark region is visible, and no obvious patient name was seen at the inspected resolution. That does not establish public provenance or complete de-identification. Figure3's55/54/55/55 counts sum correctly but its uncertainty is not shown. Tables4 and13 still contain placeholders; Table5's narrow dense text and inconsistent abbreviated model names merit layout attention. Captions should define abbreviations, denominators and whether units are proportions or percentages without requiring a reader to search the body.

## 10. Improvement plan

Score movements are judgment-based possibilities, not promised acceptance gains. A one-point increase in a15%-weight row adds3 total points; a10%-weight row adds2; a5%-weight row adds1. Improvements overlap and must not be blindly added.

### Must do before submission

| Priority | Action / acceptance criterion | Effort | New experiments? | Rows potentially moved |
|---|---|---|---|---|
|1|Correct F01/F03/F04/F05/F09/F17/F22; no universal edit immunity, equivalence or exclusive-cause claims remain.|Hours–day|No|Honesty4→5; reporting3→4.|
|2|Provide immutable repository/history, per-view transcripts, all seed summaries, manifests and deterministic table regeneration.|Days|No new inference if stored|Reproducibility2→3 or4; evidence3→4 if chronology supports it.|
|3|Finish specialist adjudication of target, control and natural-negative validity with prespecified uncertain-label handling and CIs.|Weeks|Yes, human reading|Methods2→3; clinical2→3; evidence3→4.|
|4|Patient/group reanalysis; all endpoint denominators/CIs; adjusted primary comparisons; retain raw p-values separately.|Days|Usually no|Statistics3→4.|
|5|Resolve declarations, QC specification, prompt examples, cost totals, bibliography and front-matter lengths.|Days|No, except missing runs/readers|Reporting3→4; references3→4.|
|6|Add direct removed-object/oDPO prior-work comparison and narrow novelty to demonstrated new components.|Days; longer for baseline|Writing plus baseline experiment|Novelty3→4 only if incremental benefit is demonstrated.|

### Likely reviewer requests — do now if feasible

| Action | Effort | New experiments? | Potential score movement |
|---|---|---|---|
|Separate control edits from lesion insertion in a matched factorial ablation.|Days|Yes|Methods2→3/4; novelty3→4.|
|Probe artifact predictability in frozen embeddings and perform an anatomy-matched construction-shift test.|Days–weeks|Yes|Methods2→3/4.|
|Complete native-template, resolution and parser-failure sensitivity analyses.|Days|Some reruns|Baselines3→4.|
|Publish all seed values; add seeds to unstable no-counterfactual/erasures-only arms.|Days|Yes|Statistics3→4, evidence3→4.|
|Provide per-finding sensitivity/specificity/action confusion matrices, including critical diagnoses.|Day|No if predictions retained|Clinical2→3; reporting3→4.|
|Report AURC with risk definition and confidence source, or remove it as an unused endpoint.|Day|No if scores retained|Statistics3→4.|
|Run a prespecified coverage-repair pilot, then evaluate on a genuinely new locked pneumothorax cohort.|Weeks|Yes|Clinical2→3/4; evidence3→4.|

### Nice to have / needed for stronger clinical journals

| Action | Effort | New experiments? | Potential score movement |
|---|---|---|---|
|Clinician-plus-model workflow study with patient-relevant error/efficiency endpoints.|Weeks–months|Yes|Clinical relevance toward4/5.|
|Independent external-site replication of construction and scoring.|Weeks|Yes|Evidence toward4/5; reproducibility toward4/5.|
|Real-world paired/intervention images with careful control of time/treatment differences.|Weeks–months|Yes|Methods/evidence toward4/5.|
|Prospective dataset collection with subgroup coverage and critical-finding floors.|Months|Yes|Clinical/evidence toward4/5.|

**Three questions most likely to sink the paper, with the best currently available answers**

1. **How do you know an erased image is truly negative?** Best answer: currently only automatic QC and inherited masks support that assumption, and the manuscript admits failures. Held-out tools and model consensus do not resolve it. The defensible response is to complete specialist validation and report adjudicated sensitivity analyses.
2. **Why is this more than object-removal augmentation plus conservative answering?** Best answer: matched controls, natural negatives, an absent-share ablation and a second backbone support a useful recipe. They do not establish immunity to artifacts or novelty of removal-based mitigation. Add the direct NAACL2025 comparison and isolate component contributions.
3. **Why should a clinical reader prefer a model that misses every pneumothorax?** Best answer: this paper does not establish that they should. It demonstrates a tradeoff on a research benchmark and a failure of aggregate selection criteria. Preserve that honest scope; a repaired model needs a new locked evaluation and per-finding safety criteria.

## 11. What could not be checked, and why

- **Every run-level empirical value:** no stored `summary.json`, reports or transcripts were supplied. The occurrence ledger inventories printed numbers, not verified experiments.
- **LaTeX line references:** no `.tex` file. Page/section/table and extraction-line locators are provided instead.
- **Pre-registration and chronology:** no git history, remote commit evidence, data/checkpoint timestamps or notebook execution records. The main-test chronology issue is a request for evidence, not proof of improper tuning.
- **Code/formula equivalence, parser uniformity, reward matrix and bootstrap implementation:** all named code paths absent. Synthetic policy calculations are mathematical examples, not execution of the author's code on stored images.
- **Patient/source overlaps:** no identifiers/manifests/crosswalks. No actual leak has been demonstrated; neither has leakage been excluded.
- **Model/API versions and run fairness:** dates/defaults claimed in PDF; provider logs and exact request settings unavailable. No unsupported claim is made that the named frontier models do not exist.
- **All per-seed means/SDs:** individual seed metrics absent. Aggregate differences only were checked.
- **Full bibliographic claim support:** primary metadata verified for many entries; some sources blocked, rate-limited or only partially retrievable. Each reference's residual limitation is noted in§6.
- **Complete requested review corpus:** two real public review files read; OpenReview blocked and no accessible npj review file recovered. No “top ten frequency” ranking claimed.
- **All live journal submission rules:** CBM official guide inaccessible, other exact current limits not fully retrieved. Archived formatting guidance is explicitly labelled.
- **Human clinical validity/ethics:** reader study pending, no specialist judgments or institutional determination supplied.
- **Figure2 provenance/PHI:** rendered image inspected only; source IDs, original metadata, licences and full-resolution de-identification checks unavailable.
- **Every graphical pixel / exact typesetting:** text of all19 pages extracted; key Figure2 page rendered. This was not a full high-resolution visual QA of all pages. Numeric tokens encoded as graphics could escape extraction; the main plotted labels in Figure3 were included in text extraction.

**Final re-read check.** The paper already acknowledges external perception loss, arbitrary cost assumptions, residual edits, incomplete lesion removal, unknown clinical generalisation, public-API drift and no completed human annotation. These are not counted as undisclosed flaws. Findings remain where the corresponding evidence is still missing or a stronger statement elsewhere contradicts those acknowledgements. Mask area20% versus box area37%, and protected-image counts larger than evaluated-image counts, are recorded as clarifications rather than proved errors. The complete pneumothorax miss is treated as an important openly disclosed result, not a reason to suppress the study.
