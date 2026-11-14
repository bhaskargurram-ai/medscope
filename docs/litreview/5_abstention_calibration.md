# Strand 5: Abstention, selective prediction, learning to defer, calibration and conformal methods

Strand of the MedScope systematic review. Search date: 2026-11-14. Read-only, no repository edited.

---

## 1. Search boundary

**Scope.** Selective prediction and the reject option, AURC and risk-coverage evaluation, learning to defer, calibration of (V)LMs, conformal prediction and conformal risk control, abstention under distribution shift, "know what you don't know" for LLMs and VLMs, unanswerable or absent-evidence VQA, pitfalls where abstention inflates metrics, and aleatoric/epistemic decomposition. Medical-imaging uses of each are prioritised.

**Years.** 2017-2026, with priority on 2022-2026. Condessa et al. (2017) and Tibshirani et al. (2019) are kept as foundations for metrics and shift.

**Inclusion.** The paper is peer-reviewed at a recognised venue (journal, a main conference, or Findings/D&B tracks), and its venue was checked in this session against the proceedings page, ACL Anthology, PMLR, PubMed/PMC, the MICCAI open-access site or a publisher catalogue. Papers whose venue I remember but did not re-check this session are kept in a separate list (Section 2b). ArXiv-only preprints are excluded from the ledger. Section 2c lists them only as threats to novelty.

**Tools and queries.** Tools were WebSearch (standard and extended), WebFetch on proceedings pages, and the PubMed MCP. The search budget ran out after about 45 queries. I stopped there and did not route searches through another search engine.

Query formulations used (abridged):
1. `Traub "Overcoming common flaws in the evaluation of selective classification systems" AUGRC`
2. `Jaeger "A call to reflect on evaluation practices for failure detection in image classification"`
3. `Dvijotham complementarity-driven deferral to clinicians CoDoC Nature Medicine`
4. `Whitehead "Reliable visual question answering: abstain rather than answer incorrectly" effective reliability`
5. `"Conformal risk control" ICLR 2024`; `"Fair conformal predictors for applications in medical imaging"`
6. `"Understanding silent failures in medical image classification"` (twice; venue not confirmed online)
7. `Condessa "Performance measures for classification systems with rejection"`
8. `ProbMed "Worse than random" medical VQA`; `CARES trustworthiness medical VLM`
9. `"Know your limits" abstention survey TACL`; `AbstentionBench`; `"Don't hallucinate, abstain"`
10. `"Benchmarking uncertainty disentanglement"`; `Wimmer aleatoric epistemic conditional entropy mutual information UAI`
11. `Mohri Hashimoto conformal factuality`; `Conformal alignment`; `conformal abstention Yadkori` (arXiv only, excluded)
12. `semantic entropy Nature 2024`; `Kapoor "must be taught to know what they don't know"`
13. `Leibig decision referral Lancet Digital Health`; `Kompa "Second opinion needed" npj`
14. `learning to defer Mozannar Sontag`; `Verma Nalisnick multiple experts AISTATS`; `causal framework evaluating deferring systems`
15. `Selective classification under distribution shifts TMLR`; `Kamath selective QA under domain shift`; `Gibbs Candes adaptive conformal`; `Tibshirani covariate shift`; `Band diabetic retinopathy Bayesian benchmark`
16. `Geifman bias-reduced E-AURC`; `Galil 523 ImageNet classifiers`; `Cattelan broken confidence estimator`; `Fisch calibrated selective classification`; `Jones selective classification magnify disparities`
17. `Narasimhan plugin estimators selective classification OOD`; `Jin Candes conformal p-values selection`
18. Extended: `conformal prediction medical VQA vision-language abstention 2025 MICCAI`; `medical VLM uncertainty calibration overconfidence selective prediction`; `medical LLM abstention benchmark`; `unanswerable visual questions edited image remove object abstain`; `learning to defer radiologist chest X-ray`
19. `Unsolvable Problem Detection MM-UPD`; `POPE object hallucination`; `Selective "Selective Prediction" ReCoVERR`
20. PubMed: `"conformal prediction"[tiab] AND (imaging OR radiology OR pathology OR dermatology)` since 2021 (36 hits); `("selective prediction" OR "reject option" OR "selective classification" OR "learning to defer")[tiab] AND clinical/imaging` since 2019 (77 hits); first 20 of each were screened.

**Screening.** About 300 search results and the 40 PubMed records were screened. 45 papers were kept: 37 in the main ledger and 8 in the remember-only list. The PubMed hits were mostly applied single-modality CNN papers. Only the high-yield ones were kept: TRUECAM in Nature BME, and the JMIR AI scoping review because of its gap statistic.

---

## 2. Evidence ledger (venues checked in this session)

| # | Title | First author et al. | Venue, year | Method | Guarantee / evaluation | Key result | Relevance to MedScope | URL |
|---|---|---|---|---|---|---|---|---|
| 1 | Overcoming Common Flaws in the Evaluation of Selective Classification Systems | Traub et al. | NeurIPS 2024 | Proposes AUGRC (area under the generalized risk-coverage curve, i.e. the average risk of *undetected* failures) | Lists requirements a selective-classification metric should meet; AURC fails several | AURC over-weights high-rejection regions; switching to AUGRC substantially reorders method rankings across benchmarks | MedScope gains come from rejecting more. AUGRC-style metrics penalise that less kindly than AURC, so report them next to ESG | https://proceedings.neurips.cc/paper_files/paper/2024/hash/047c84ec50bd8ea29349b996fc64af4b-Abstract-Conference.html |
| 2 | A Call to Reflect on Evaluation Practices for Failure Detection in Image Classification | Jaeger et al. | ICLR 2023 (oral) | FD-Shifts benchmark joining misclassification detection, OOD and shift detection | AURC as a single metric covering classifier and confidence score; includes medical datasets | Complex confidence-scoring functions rarely beat the max-softmax baseline once evaluated properly | Precedent for "the clever method doesn't beat the baseline": MedScope's 270 policies fit this pattern | https://iclr.cc/virtual/2023/oral/12528 |
| 3 | Enhancing the reliability and accuracy of AI-enabled diagnosis via complementarity-driven deferral to clinicians (CoDoC) | Dvijotham et al. | Nature Medicine, 2023 | Learns from AI confidence when to defer to a clinician, using clinician-vs-AI accuracy at each confidence level | Retrospective evaluation on mammography (UK, US) and chest X-ray TB | Fewer false positives and less clinician workload than AI alone or clinician alone, with no loss in sensitivity (paper reports about 25% fewer UK false positives) | Strongest clinical precedent that *deferral itself* can be the contribution. It assumes the confidence score already separates cases, which MedScope's ESG says is not true | https://www.nature.com/articles/s41591-023-02437-x |
| 4 | Reliable Visual Question Answering: Abstain Rather Than Answer Incorrectly | Whitehead et al. | ECCV 2022 | Learned selector on top of VQA models, plus the *effective reliability* metric Φ_c (+1 correct, -c wrong, 0 abstain) | Coverage at fixed risk, and Φ_c at several costs | VQA models reach very low coverage at 1% risk; the learned selector helps | Φ_c is a simplified MedScope cost matrix. With large c, abstaining wins by construction, which is exactly the MedScope pitfall | https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/2576_ECCV_2022_paper.php |
| 5 | Performance measures for classification systems with rejection | Condessa et al. | Pattern Recognition 63, 2017 | Three measures: non-rejected accuracy, *classification quality* and *rejection quality* | Axiomatic; rejection quality isolates whether rejected samples are the misclassified ones | Separates the rejector's contribution from the classifier's | Basis for splitting "abstaining well" from "discriminating well" (Section 3) | https://arxiv.org/abs/1504.02763 (journal version: Pattern Recognit. 2017) |
| 6 | Bias-Reduced Uncertainty Estimation for Deep Neural Classifiers | Geifman et al. | ICLR 2019 | Defines E-AURC = AURC - AURC* (the optimal AURC at the same accuracy) | Normalises AURC by base accuracy | Isolates the confidence ranking from accuracy | E-AURC computed only on erased-vs-control pairs is a natural partner to ESG | https://iclr.cc/virtual/2019/poster/963 |
| 7 | What Can We Learn From the Selective Prediction and Uncertainty Estimation Performance of 523 ImageNet Classifiers? | Galil et al. | ICLR 2023 | Large empirical study of AURC, AUROC and calibration | Ranking (AUROC of confidence) vs calibration (ECE) vs AURC | These properties come apart; training regime matters more than architecture | Calibration ≠ ranking ≠ selective risk. MedScope must say which one it improves | https://iclr.cc/virtual/2023/poster/11783 |
| 8 | How to Fix a Broken Confidence Estimator: Evaluating Post-hoc Methods for Selective Classification | Cattelan & Silva | UAI 2024 (PMLR 244) | Post-hoc logit normalisation for confidence | AURC and NAURC across many models, including under shift | Simple post-hoc fixes give large AURC gains | Cheap baseline. Shows that abstention gains are often score-ranking artefacts, not new discrimination | https://proceedings.mlr.press/v244/cattelan24a.html |
| 9 | Selective Classification Can Magnify Disparities Across Groups | Jones et al. | ICLR 2021 | Analyses group-wise accuracy-coverage curves | Theory plus experiments on spurious-correlation datasets | Average accuracy goes up with abstention while worst-group accuracy can go *down* | Key pitfall: the "erased-lesion" group is a worst group. Aggregate utility can rise while ESG stays flat | https://iclr.cc/virtual/2021/poster/3060 |
| 10 | Calibrated Selective Classification | Fisch et al. | TMLR 2022 | Trains a selector so that the *accepted* subset is calibrated (robust calibration objective) | Calibration of selected predictions under shift; includes a clinical risk task | Better calibration on the accepted subset than confidence thresholding | Turns abstention into a calibration contract on answered items, a possible guarantee target | https://mlanthology.org/tmlr/2022/fisch2022tmlr-calibrated |
| 11 | Plugin estimators for selective classification with out-of-distribution detection (SCOD) | Narasimhan et al. | ICLR 2024 | Bayes-optimal rule for rejecting both misclassifications and OOD inputs; plug-in estimators | Derived optimal rule (Chow's rule plus a density-ratio term) | One principled rule beats ad-hoc mixes of confidence and OOD scores | Direct template for MedScope's **clarify** (unusable/OOD image) vs **refer** (uncertain finding) split | https://iclr.cc/virtual/2024/poster/19150 |
| 12 | Consistent Estimators for Learning to Defer to an Expert | Mozannar & Sontag | ICML 2020 | Consistent surrogate loss with a (K+1)-th "defer" class | Bayes consistency | The standard L2D baseline | Referral to a radiologist is L2D. MedScope's referral cost (-0.3) is the expert cost | https://proceedings.mlr.press/v119/mozannar20b.html |
| 13 | Learning to Defer to Multiple Experts: Consistent Surrogate Losses, Confidence Calibration, and Conformal Ensembles | Verma et al. | AISTATS 2023 (PMLR 206) | One-vs-all L2D surrogates; conformal sets over experts | Consistency plus calibrated deferral probabilities | Calibrated estimates of expert correctness | Lets "ask to clarify" and "refer" be modelled as two experts with different costs | https://proceedings.mlr.press/v206/verma23a.html |
| 14 | A Causal Framework for Evaluating Deferring Systems | Palomba et al. | AISTATS 2025 (PMLR 258) | Potential outcomes for deferral; identifies effects with designs such as regression discontinuity | Causal estimands for "what if the system had not deferred" | Standard deferral metrics confound what is deferred with how well it is handled | Methodological ally. ESG is a counterfactual estimand, and this paper gives the language for it | https://proceedings.mlr.press/v258/palomba25a.html |
| 15 | Combining the strengths of radiologists and AI for breast cancer screening: a retrospective analysis (decision referral) | Leibig et al. | Lancet Digital Health, 2022 | AI handles confident-normal and confident-cancer exams and refers the uncertain middle band | Large retrospective multi-site screening cohort | Radiologist plus AI with referral beat either alone in sensitivity and specificity while automating most exams | Clinical template for answer/refer thresholds; uses two thresholds, much like the MedScope cost matrix | https://pmc.ncbi.nlm.nih.gov/articles/PMC9839981 |
| 16 | Second opinion needed: communicating uncertainty in medical machine learning | Kompa et al. | npj Digital Medicine, 2021 | Perspective arguing for "I don't know" outputs in medical ML | Conceptual | Argues that abstention and uncertainty should be first-class outputs | Motivation citation for the clarify/refer actions | https://pmc.ncbi.nlm.nih.gov/articles/7785732 |
| 17 | Conformal Risk Control | Angelopoulos et al. | ICLR 2024 | Extends split conformal to bound the expectation of any monotone loss | Finite-sample E[L] ≤ α | Controls FNR in tumour/polyp segmentation, multilabel tasks and more | Main tool for a *guarantee* on a MedScope loss (e.g. claim-rate on erased views) | https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html |
| 18 | Fair Conformal Predictors for Applications in Medical Imaging | Lu et al. | AAAI 2022 | Group-conditional (Mondrian) conformal prediction sets for medical imaging | Coverage within each subgroup | Marginal coverage hides subgroup under-coverage; group-conditional fixes it | Treat {erased, control, natural-absent, present} as groups. Coverage can be certified per group only if group membership is observable or proxied | https://ojs.aaai.org/index.php/AAAI/article/view/21459 |
| 19 | Trustworthy Few-Shot Transfer of Medical VLMs through Split Conformal Prediction | Silva-Rodríguez et al. | MICCAI 2025 (LNCS 15966) | Transductive split conformal adaptation (SCA-T) for medical VLMs | Keeps SCP coverage; better efficiency and conditional coverage | Shows that adapting on calibration data breaks exchangeability; proposes a fix | Warning for MedScope: calibrating policies on the same data used to tune signals voids guarantees | https://papers.miccai.org/miccai-2025/0955-Paper4783.html |
| 20 | Conformal Alignment: Knowing When to Trust Foundation Models with Guarantees | Gui et al. | NeurIPS 2024 | Conformal selection with FDR control over which foundation-model outputs to trust | FDR guarantee on selected outputs | Demonstrated on QA and chest-X-ray report generation | Closest guaranteed "answer vs refer" method for medical VLMs; not counterfactual | https://proceedings.neurips.cc/paper_files/paper/2024/hash/870ccde24673d3970a680bb48496ed63-Abstract.html |
| 21 | Selection by Prediction with Conformal p-values | Jin & Candès | JMLR 24, 2023 | Conformal p-values plus Benjamini-Hochberg to select units | Finite-sample FDR | Foundation of conformal selection | Theory behind #20. "Answer only when selected" gives FDR control on wrong answers | https://jmlr.org/papers/v24/22-1176.html |
| 22 | Language Models with Conformal Factuality Guarantees | Mohri & Hashimoto | ICML 2024 | Conformal back-off: drop sub-claims until the remaining output is correct with prob ≥ 1-α | Finite-sample correctness guarantee | 80-90% correctness targets met by removing claims | "Abstain by saying less" guarantee. The analogue is withholding a lesion claim | https://proceedings.mlr.press/v235/mohri24a.html |
| 23 | Robots That Ask for Help: Uncertainty Alignment for LLM Planners (KnowNo) | Ren et al. | CoRL 2023 (PMLR 229) | Conformal prediction set over candidate actions; ask a human when the set is not a singleton | Task-success guarantee at 1-α with minimal help | Calibrated ask-for-help | Template for the **ask-to-clarify** action with a guarantee | https://proceedings.mlr.press/v229/ren23a/ren23a.pdf |
| 24 | Adaptive Conformal Inference Under Distribution Shift | Gibbs & Candès | NeurIPS 2021 | Online update of α | Long-run coverage under arbitrary shift | Robust coverage over time | Deployment shift across the 5 imaging types and scanners | https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html |
| 25 | Conformal Prediction Under Covariate Shift | Tibshirani et al. | NeurIPS 2019 | Likelihood-ratio-weighted conformal | Coverage under known covariate shift | Founding result for conformal under shift | Erasure is a *label-changing* intervention, not covariate shift, so weighted conformal does not cover it. This is a gap | https://papers.nips.cc/paper/8522-conformal-prediction-under-covariate-shift |
| 26 | Selective Classification Under Distribution Shifts | Liang et al. | TMLR 2024 | Generalised selective classification covering covariate and label shift; margin-based scores | Risk-coverage under shift | Raw-logit margin scores beat softmax scores under shift | Cheap alternative signal; still a ranking of the same evidence | https://mlanthology.org/tmlr/2024/liang2024tmlr-selective |
| 27 | Selective Question Answering under Domain Shift | Kamath et al. | ACL 2020 | Calibrator trained on a mix of in-domain and OOD data | Coverage at fixed accuracy under shift | Softmax confidence over-answers under shift; the calibrator fixes part of it | Early evidence that abstention signals must be trained on the shifted population (here, edited images) | https://virtual.acl2020.org/paper_main.503.html |
| 28 | Benchmarking Bayesian Deep Learning on Diabetic Retinopathy Detection Tasks (RETINA) | Band et al. | NeurIPS 2021 D&B | Selective prediction / referral under country shift | Referral curves in- and out-of-distribution | No Bayesian method dominates; referral benefits shrink under shift | Medical-imaging referral-curve precedent; benefits do not transfer to shift | https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/ac1dd209cbcc5e5d1c6e28598e8cbbe8-Abstract-round2.html |
| 29 | Benchmarking Uncertainty Disentanglement: Specialized Uncertainties for Specialized Tasks | Mucsányi et al. | NeurIPS 2024 D&B | Tests whether aleatoric and epistemic estimators are really disentangled | Many tasks (abstention, OOD, label noise and others) | Current estimators are highly correlated; disentanglement mostly fails in practice | Do not expect an "epistemic" score to isolate evidence absence | https://proceedings.neurips.cc/paper_files/paper/2024/hash/5afa9cb1e917b898ad418216dc726fbd-Abstract.html |
| 30 | Quantifying Aleatoric and Epistemic Uncertainty in ML: Are Conditional Entropy and Mutual Information Appropriate Measures? | Wimmer et al. | UAI 2023 (PMLR 216) | Axiomatic critique of the entropy/MI decomposition | Theoretical | The standard decomposition violates natural axioms | Theoretical backing for not using the entropy/MI split to detect erased lesions | https://mlanthology.org/uai/2023/wimmer2023uai-quantifying |
| 31 | Detecting hallucinations in large language models using semantic entropy | Farquhar et al. | Nature, 2024 | Entropy over meaning clusters of sampled answers | AUROC for detecting confabulations | Beats token-level baselines | Probably MedScope's "consistency" signal family. Detects arbitrary answers, not answers that are consistently confident and wrong (the erased-lesion case) | https://oatml.cs.ox.ac.uk/publications/202406_FarquharKossenKuhn_HallucinatingLLMs.html |
| 32 | Large Language Models Must Be Taught to Know What They Don't Know | Kapoor et al. | NeurIPS 2024 | Fine-tunes uncertainty heads/LoRA on a small graded set | Calibration and AUROC, with transfer | About 1k graded examples give calibrated uncertainty that generalises | Cheap way to get a learned P(correct). Still a ranking of existing evidence | https://proceedings.neurips.cc/paper_files/paper/2024/hash/9c20f16b05f5e5e70fa07e2a4364b80e-Abstract.html |
| 33 | Don't Hallucinate, Abstain: Identifying LLM Knowledge Gaps via Multi-LLM Collaboration | Feng et al. | ACL 2024 (outstanding paper) | Multi-LLM cooperate/compete probing to decide when to abstain | Abstain accuracy and reliable accuracy | Beats calibration and self-reflection baselines | Same family as MedScope's multi-agent verification, which also left ESG flat | https://aclanthology.org/2024.acl-long.786 |
| 34 | Know Your Limits: A Survey of Abstention in Large Language Models | Wen et al. | TACL 2025 | Survey: query, model and human-values views of abstention | Lists abstention metrics and benchmarks | Notes over-abstention and metric gaming | Taxonomy and metric reference | https://aclanthology.org/2025.tacl-1.26 |
| 35 | AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions | Kirichenko et al. | NeurIPS 2025 D&B | 20-dataset abstention benchmark (underspecified, false premise, unanswerable) | Abstention recall/precision | Reasoning fine-tuning *hurts* abstention; scale does not fix it | Unanswerable-because-evidence-missing is a known weak spot. MedScope's erased views are the visual, medical version | https://proceedings.neurips.cc/paper_files/paper/2025/hash/fb122bfc3f0127a94ded048b5b03496f-Abstract-Datasets_and_Benchmarks_Track.html |
| 36 | Unsolvable Problem Detection: Robust Understanding Evaluation for Large Multimodal Models | Miyai et al. | ACL 2025 | Benchmarks for absent answers, incompatible answer sets and incompatible image/question | Detection of unsolvable inputs | Strong LMMs often answer anyway; prompting and tuning help only partly | Nearest general-domain benchmark to the "erased evidence" construct, but with no matched control edit | https://aclanthology.org/2025.acl-long.326/ |
| 37 | Selective "Selective Prediction": Reducing Unnecessary Abstention in Vision-Language Reasoning (ReCoVERR) | Srinivasan et al. | Findings of ACL 2024 | When the VLM would abstain, an LLM asks follow-up perception questions to *collect evidence* and answers only if the evidence supports it | Raises coverage without raising risk | Fewer needless abstentions at matched risk | **Closest method to an evidence-conditional abstention framework**: it gathers evidence instead of only thresholding | https://aclanthology.org/2024.findings-acl.767 |
| 38 | Evaluating Object Hallucination in Large Vision-Language Models (POPE) | Li et al. | EMNLP 2023 | Polling yes/no "is there an X?" probes (random/popular/adversarial negatives) | Accuracy and yes-ratio | LVLMs lean towards "yes", worst on adversarial co-occurring objects | Same task form as MedScope's presence questions. "Yes" bias is the general-domain version of claiming an erased lesion | https://aclanthology.org/2023.emnlp-main.20 |
| 39 | Worse than Random? An Embarrassingly Simple Probing Evaluation of LMMs in Medical VQA (ProbMed) | Yan et al. | Findings of ACL 2025 | Paired probing with adversarial hallucinated findings/attributes | Accuracy on paired questions | Top LMMs (incl. GPT-4o, Gemini) score below random on specialised diagnostic probes | Medical evidence that presence answers are driven by priors, not evidence | https://aclanthology.org/2025.findings-acl.981 |
| 40 | CARES: A Comprehensive Benchmark of Trustworthiness in Medical Vision Language Models | Xia et al. | NeurIPS 2024 D&B | Five-dimension trust benchmark (trustfulness incl. over-confidence, fairness, safety, privacy, robustness) | Includes uncertainty/abstention-style probes | Med-LVLMs are over-confident and rarely abstain on OOD inputs | Medical-VLM baseline evidence of poor abstention | https://proceedings.neurips.cc/paper_files/paper/2024/hash/fde7f40f8ced5735006810534dc66b33-Abstract.html |
| 41 | Confidence Calibration for Multimodal LLMs: An Empirical Study through Medical VQA | Du et al. | MICCAI 2025 (LNCS 15965) | Prompt-based multi-strategy interrogation plus an expert LLM to re-score confidence | ECE, AUROC on VQA-RAD and others | About 40% average ECE reduction; AUROC stays modest (e.g. 56.9 on VQA-RAD with LLaVA-NeXT) | Same pattern as MedScope: calibration improves while discrimination stays near chance | https://papers.miccai.org/miccai-2025/0165-Paper1840.html |
| 42 | Calibrated Confidence Expression for Radiology Report Generation (ConRad) | Bani-Harouni et al. | MICCAI 2026 | GRPO with a log-scoring-rule reward for verbalised report/sentence confidence | ECE vs CheXbert/RadGraph correctness; small reader study | ECE drops sharply (e.g. 0.72→0.19 under RadGraph) | Recipe for RL-trained verbalised confidence on a 4B-class VLM. Optimises calibration, not discrimination | https://papers.miccai.org/miccai-2026/0142-Paper2409.html |
| 43 | Implementing trust in non-small cell lung cancer diagnosis with a conformalized uncertainty-aware AI framework (TRUECAM) | Zhang et al. | Nature Biomedical Engineering, 2026 | SNGP out-of-scope detection, ambiguity-guided tile elimination, conformal error control | Conformal error-rate control on WSIs | Wrapped models more accurate, robust and fair | High-profile medical precedent for an out-of-scope gate plus a conformal answer gate (≈ clarify + refer) | https://doi.org/10.1038/s41551-026-01694-8 |
| 44 | Trustworthiness Evaluation of Medical Vision-Language Models: A Scoping Review and a Proposed Minimum Evaluation Checklist | Sadanandan et al. | JMIR AI, 2026 | PRISMA-ScR review (2022-Mar 2026) of 29 studies | Descriptive | **No included study reported a formal calibration metric or a selective-prediction curve**; only 4/29 used image-reliance controls | Quantified gap MedScope can cite: medical VLM work almost never combines image-reliance controls with abstention evaluation | https://doi.org/10.2196/102330 |

(Main ledger: 44 rows, all with venues checked this session. Rows 1-37 are the core set; rows 38-44 add medical-VLM and benchmark context. Row 5 links to the arXiv copy, but its Pattern Recognition 2017 publication was confirmed in the British Library catalogue.)

### 2b. Venue remembered, not re-checked this session (check before citing)

| Title | Authors | Venue (from memory) | Why it matters |
|---|---|---|---|
| Selective classification for deep neural networks | Geifman & El-Yaniv | NeurIPS 2017 | Selection with guaranteed risk (SGR); origin of the risk-coverage framing |
| SelectiveNet | Geifman & El-Yaniv | ICML 2019 | Trains selector and classifier together at a target coverage |
| Understanding Silent Failures in Medical Image Classification | Bungert et al. | MICCAI 2023 | Failure detection across medical shifts; no confidence scorer is reliable on every shift |
| Evidential Deep Learning to Quantify Classification Uncertainty | Sensoy et al. | NeurIPS 2018 | "Vacuity" (lack of evidence) as an uncertainty type; the explicit evidence-absence idea |
| Are Uncertainty Quantification Capabilities of Evidential Deep Learning a Mirage? | Shen et al. | NeurIPS 2024 | Shows EDL "vacuity" does not reliably measure epistemic uncertainty or missing evidence |
| Conformal Prediction with Conditional Guarantees | Gibbs, Cherian & Candès | JRSS-B 2025 | Coverage conditional on a function class of features; route to evidence-conditional guarantees |
| Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control | Angelopoulos et al. | Annals of Applied Statistics 2025 | Controls several risks at once (e.g. claim-rate on erased views AND referral-rate on controls) |
| Conformal Language Modeling | Quach et al. | ICLR 2024 | Sample-until-set-covers with a stopping and rejection rule; conformal for generative answers |

### 2c. Preprints (not in the ledger; closest-work and novelty threats)

- **Look Again Before You Abstain: Budgeted Conformal Evidence Acquisition for Reliable VLMs.** Xu et al., arXiv 2606.16667, 2026. Adds "acquire evidence" (zoom crops, flips) between answering and abstaining. It shows that reusing pre-acquisition thresholds *breaks* conformal validity and recalibrates on post-acquisition scores. On POPE-style existence claims, holding hallucination ≤5% requires asserting only about 18% of claims. **This is the most direct threat to Framework C.** MedScope must differ by using *evidence-removal* interventions, medical presence questions and a counterfactual control-edit guarantee.
- **Uncertainty Is Not a Safety Net for Clinical VQA, but Can It Anticipate Model Failure?** Fazla et al., arXiv 2606.16583, 2026. When the correct option is replaced by "none of the options", accuracy drops 12-33 points while uncertainty barely rises. Independent replication of MedScope's core finding (uncertainty does not track missing evidence).
- Mitigating LLM Hallucinations via Conformal Abstention (Yadkori et al., arXiv 2405.01563). TUBench (arXiv 2410.04107). Knowing When to Abstain: Medical LLMs Under Clinical Uncertainty (arXiv 2601.12471).

---

## 3. How the literature separates "abstaining well" from "discriminating well"

### 3.1 The decomposition, in terms MedScope can use

The selective risk of an answer/abstain system at coverage c depends on three separable components.

- **(i) Base discrimination of the answerer.** Accuracy or AUROC at full coverage, or for presence questions how well P(present | x) separates present from absent.
- **(ii) Ranking quality of the confidence score.** Does the score order failures below successes? This is measured by failure-detection AUROC, Condessa's *rejection quality* (row 5) and Geifman's **E-AURC** (row 6), which subtracts the optimal AURC at the same accuracy and so removes (i).
- **(iii) Operating point.** How much the system abstains: coverage, or the threshold set by a cost.

Metrics fall into three groups:

- **Metrics that mix all three:** AURC (Jaeger et al., row 2, say this is intended), Whitehead's Φ_c (row 4), and any net-utility cost matrix, including MedScope's.
- **Metrics that remove (i):** E-AURC, rejection quality, failure-detection AUROC and AUGRC normalisations (row 1).
- **Metrics that remove (iii):** AURC/AUGRC integrate over all coverages. A threshold-based utility does not.

Galil et al. (row 7) show that calibration (ECE), ranking (AUROC of confidence) and selective risk can each improve while the others do not. Du et al. (row 41) and ConRad (row 42) show this in medical VLMs: ECE falls 40-70% while AUROC stays near 0.57.

### 3.2 Why "more abstention" raises utility without raising ESG: a data-processing view

Two definitions:
- **S** = the vector of all test-time signals the policy sees (logits, consistency, multi-agent votes and so on).
- **π(a | S)** = any decision policy that sees only S. MedScope's 270 policies are of this kind.

Then:

ESG(π) = P(absent ∨ refer | erased) − P(absent ∨ refer | control) ≤ TV(P_{S|erased}, P_{S|control}).

This holds because for any event A of S, |P(A | erased) − P(A | control)| ≤ TV. It is the data-processing inequality: **no policy over S can separate erased from control better than S itself does.**

Consequences:
- If the signals are nearly identically distributed on erased and control views, every policy (learned, multi-agent or conformal) has ESG ≈ 0 by construction. That is exactly what MedScope sees across 270 policies.
- Utility can still rise. Under the cost matrix, referring on erased views scores +0.5 versus −2 for claiming, and needless referral costs only −0.3. So lowering the referral threshold buys utility on erased *and* control items alike, with no discrimination. This is the "abstention inflates metrics" pitfall in its general form (Jones et al., row 9: average up, worst group flat or down).
- In the ideal model, evidence absence is not an *uncertainty* state. A model that truly sees no lesion should answer "absent" confidently, which scores +1, better than refer at +0.5. So referral is a *second-best* answer to erased views, and uncertainty is the wrong axis for detecting them. Erased-lesion claims are **confident, prior-driven errors**: POPE's "yes" bias (row 38) and ProbMed's below-random probes (row 39).
- Disentanglement does not rescue this. Mucsányi et al. (row 29) and Wimmer et al. (row 30) show aleatoric/epistemic splits are entangled and axiomatically shaky. EDL "vacuity" was meant to capture missing evidence but is unreliable (Shen et al., NeurIPS 2024, venue not re-checked). Semantic entropy (row 31) catches *arbitrary* answers, not answers that are consistently wrong.

### 3.3 Metrics that separate the two (recommended reporting set)

1. **ESG** (discrimination on counterfactual pairs), reported **at matched referral rate**. Compare against a "coverage-matched evidence-blind" baseline: refer at random, or by a score shuffled within each pair, at the same overall rate. Utility above that baseline is the *discrimination dividend*; the rest is the *coverage dividend*.
2. **Pairwise E-AURC / rejection quality on (erased, control) pairs.** Is the erased view ranked as less "claim-worthy" than its control twin? This is a paired AUROC that ignores thresholds.
3. **AUGRC** (row 1) next to AURC, so that high-rejection regimes are not rewarded.
4. **Group-wise risk-coverage curves** (row 9) for {present, natural-absent, erased, control-edit}.
5. **Signal TV bound.** Estimate TV(P_{S|erased}, P_{S|control}) with a held-out classifier two-sample test (balanced accuracy − 0.5, times 2, is a lower bound on TV). It is an *a priori ceiling* on attainable ESG for any policy over S.

---

## 4. Gaps MedScope could own

1. **No abstention or selective-prediction work evaluates or guarantees behaviour under *counterfactual evidence removal* with a matched control edit.**
   - The nearest benchmarks are UPD (row 36), AbstentionBench (row 35), POPE/ProbMed (rows 38-39) and TUBench (preprint). None pairs an evidence-erased view with an edit-matched control, so none can separate "detects missing evidence" from "detects editing artefacts".
   - The JMIR AI scoping review (row 44) found *zero* medical-VLM trust papers reporting selective-prediction curves, and only 4/29 using image-reliance controls.
2. **Conformal guarantees cover marginal, group-conditional (rows 18-19) or covariate-shift (rows 24-25) settings. Nothing covers interventional or label-changing edits.**
   - Erasing a lesion changes the label, so weighted conformal under covariate shift does not apply.
   - A *paired/counterfactual risk* (claim rate on erased views ≤ α while referral on control views ≤ β) controlled with LTT/CRC is, as far as this search found, unclaimed.
3. **No formal statement that abstention policies cannot create discrimination they are not given.**
   - The evaluation literature (rows 1, 2, 5, 6, 9) implies it but never states it as a ceiling with a usable estimator.
   - MedScope's 270-policy null result plus the TV ceiling is a clean, falsifiable negative-result contribution.
4. **Evidence acquisition before abstaining exists in general VQA but not in medical imaging, and not with evidence-*removal* probes.**
   - ReCoVERR (row 37) asks perception sub-questions. BCEA (preprint) zooms and flips.
   - Neither uses the model's own grounding to *remove* the purported evidence and check whether the answer depends on it.
5. **Three-way actions (answer / clarify-unusable / refer) with separate, principled rules.**
   - SCOD (row 11) gives the Bayes-optimal two-reason reject rule; KnowNo (row 23) gives a guaranteed ask-for-help; TRUECAM (row 43) gates out-of-scope inputs.
   - None is combined for medical VLMs under a clinical cost matrix with a critical-error tier (−4).

---

## 5. Candidate frameworks

The literature points to **A (evaluation theory) + C (mechanism) + B (guarantee)** as the strongest single paper. A explains the null result, C supplies the missing signal, and B certifies it. D is a strong baseline or ablation, not a headline.

### Framework A: "Abstention cannot buy discrimination": a counterfactual ceiling and a utility decomposition

- **Mechanism.**
  - (1) Prove ESG(π) ≤ TV(P_{S|erased}, P_{S|control}) for any policy measurable in signals S. Extend it to utility: ΔU = coverage dividend + discrimination dividend, where the coverage dividend is the utility of an evidence-blind policy with the same referral rate.
  - (2) Estimate the TV ceiling with a cross-fitted two-sample classifier on S.
  - (3) Re-score all 270 policies, multi-agent and training variants on the dividend split.
- **Closest work.** Condessa 2017 (rejection quality), Geifman 2019 (E-AURC), Traub 2024 (AUGRC), Jones 2021 (group disparity), Palomba 2025 (causal deferral evaluation).
- **Difference.**
  - The paired counterfactual construction and the policy-class ceiling are new.
  - It turns MedScope's negative result into a theorem plus a diagnostic that predicts the null result *before* any policy is trained.
- **Falsifiable predictions.**
  - (a) The estimated TV ceiling on current signals is small, e.g. below about 0.05-0.1. Every one of the 270 policies has ESG ≤ ceiling, within CI.
  - (b) More than about 80% of each method's utility gain is coverage dividend.
  - (c) Adding a signal that raises the estimated TV raises the best attainable ESG, monotonically.
  - Finding a policy with ESG significantly above the estimated ceiling would falsify the estimator; the theorem itself is exact.
- **Compute.** Reuses cached signals. Two-sample classifiers and bootstrap take CPU-minutes to about 1 A100-hour.
- **Novelty risk.** The theorem alone is elementary. Novelty rests on the counterfactual benchmark plus the empirical ceiling. Pair it with C so the paper is not only negative.

### Framework B: Counterfactual Conformal Risk Control (CCRC): certified evidence-conditional abstention

- **Mechanism.**
  - Calibrate on triples (original-with-lesion, erased, control-edit) plus lesion-free images.
  - Use Learn-then-Test, or CRC with Bonferroni, to choose thresholds λ = (λ_answer, λ_refer, λ_clarify) that certify all three of:
    - R1 = P(claim present | erased) ≤ α₁
    - R2 = P(miss | present) ≤ α₂ (critical errors)
    - R3 = P(refer | control or answerable) ≤ β
  - If no λ satisfies all three, the procedure *outputs infeasibility*. That is a certificate that the signal cannot meet the clinical contract.
  - Report a certified lower bound on ESG.
- **Closest work.** CRC (row 17), LTT (2b), Conformal Alignment (row 20), Mohri & Hashimoto (row 22), KnowNo (row 23), fair conformal (row 18).
- **Difference.**
  - The risks are defined on *counterfactual twins*, with a matched control to rule out artefact detection.
  - The guarantee holds on the edit-generating distribution, i.e. exchangeability between calibration and test edits.
  - Abstention becomes a contract, not a tuning knob.
- **Falsifiable predictions.**
  - (a) With current signals, CCRC meets α₁ only by pushing referral on controls to near the referral on erased views. The certified ESG lower bound is ≈ 0, and the procedure reports infeasibility at clinically useful β. This repeats A's prediction in certified form.
  - (b) With an evidence-sensitive signal (C), the feasible region opens: the same α₁ is met at much lower β.
  - (c) Empirical test-time R1 ≤ α₁ holds in about 90%+ of random calibration/test splits. Violation beyond the nominal rate would falsify the implementation.
- **Compute.** Calibration only, minutes on CPU, given cached scores. Main cost is generating calibration triples, which the benchmark already has.
- **Caveat.** The guarantee covers *the editing process*, not natural lesion absence. Say this plainly, and add natural lesion-free images as a fourth stratum.

### Framework C: Self-Counterfactual Evidence Probing (SCEP): abstention conditioned on whether the answer depends on the evidence

- **Mechanism.** For a presence query:
  - (1) The agent localises the region it would cite as evidence, via grounding output or attention/attribution.
  - (2) It produces its own *erased* view of that region (inpainting) and a *matched control* edit of a non-cited region of similar size and texture.
  - (3) Evidence-dependence score: D = logit P(present | x) − logit P(present | erase_cited(x)), minus the same difference for the control edit.
  - Logic: on a truly present lesion, removing the cited region should collapse the "present" belief (large D). On an already-erased or hallucinated lesion, the cited region holds no lesion evidence, so D ≈ the control effect (D ≈ 0).
  - (4) Feed D with existing signals into the policy, and certify with B.
  - Optional third action: when grounding fails, return "clarify".
- **Closest work.**
  - ReCoVERR (row 37): asks follow-up questions for evidence; does not remove evidence.
  - BCEA (preprint, 2c): zoom/flip acquisition with conformal recalibration.
  - POPE/ProbMed (rows 38-39) as probes.
  - The counterfactual edits in the benchmark itself.
- **Difference.**
  - The intervention is *evidence removal at the model's own cited location*, with a built-in control edit, mirroring the benchmark's causal construct at test time.
  - It is aimed at confident prior-driven errors, which uncertainty misses (Section 3.2).
  - Paired with B for a guarantee. BCEA's lesson applies: recalibrate on post-probe scores.
- **Falsifiable predictions.**
  - (a) D separates present from erased views with AUROC ≥ 0.7, where current signals are near 0.5. This would show up as a jump in A's TV ceiling.
  - (b) ESG at matched referral rate rises by ≥ 0.10 over the best of the 270 policies.
  - (c) **Artefact control:** D on control-edited images matches D on unedited originals (|Δ| small). If D just detects inpainting artefacts, ESG measured with the benchmark's control edits stays ≈ 0, so the hypothesis fails cleanly.
  - (d) The gain shrinks where the 4B model's grounding is poor. Predict it is smallest on the imaging type with the worst localisation.
- **Compute.**
  - Per query: 1 grounding pass, 2 inpaint edits and 2 extra VLM forwards.
  - Assumed costs: 4B VLM at about 0.1-0.2 s per forward; a diffusion or LaMa-style inpainter at about 0.2-1.5 s per 512² edit on an A100.
  - For about 10-20k benchmark queries: about 5-15 A100-hours. No training required; an optional LoRA to improve grounding is about 4-8 A100-hours.
- **Main risks.**
  - Localisation fails for diffuse findings, so restrict to focal lesions or use multiple candidate regions.
  - Inpainting domain gap on some modalities. Use the benchmark's own eraser to stay in-distribution, but report a different eraser to show the method does not overfit the edit.

### Framework D: Cost-derived three-action Chow/SCOD rule ("principled abstention" baseline)

- **Mechanism.**
  - Derive the Bayes-optimal answer/refer/clarify rule in closed form from the MedScope cost matrix: Chow thresholds on calibrated P(present), with the critical-error tier, plus SCOD's density-ratio term for unusable images.
  - Fit only the calibrated posterior (temperature, or Kapoor-style probe) and a usability density-ratio estimate. Calibrate per imaging type, Mondrian style.
- **Closest work.** Narasimhan et al. 2024 (SCOD), Chow's rule, Leibig 2022 (two-threshold referral), CoDoC (row 3), L2D (rows 12-13).
- **Difference.**
  - Three actions with modality-specific costs.
  - It shows the 270 learned policies collapse to a 2-3 parameter Bayes rule, which makes the null result easier to interpret.
- **Falsifiable predictions.**
  - (a) The closed-form rule matches the best learned policy's utility within bootstrap CI.
  - (b) Its ESG equals the learned policies' ESG (≈ 0).
  - (c) Its utility tracks the analytic coverage-dividend curve from A.
- **Compute.** Negligible: calibration on cached logits.
- **Role.** This is a baseline and ablation, not the headline. It shows "better abstention" can be made principled and parsimonious, but not that it is novel enough to stand alone.

### Framework E (optional): Paired counterfactual ranking objective for the confidence head

- **Mechanism.** Train a light confidence/abstention head, a LoRA probe as in Kapoor et al. (row 32), with a *pairwise* loss that ranks erased views below their control twins. A pairwise loss directly targets E-AURC on pairs instead of a pointwise correctness target.
- **Closest work.** Kapoor 2024, Fisch 2022 (calibrated selective), ConRad (row 42; RL verbalised confidence).
- **Difference.** The pairwise counterfactual target, scored with a held-out eraser.
- **Falsifiable prediction.**
  - By A's theorem, this can help *only if* the backbone's hidden states carry erased-vs-control information. A linear probe of hidden states (TV estimate) decides this up front.
  - If the probe sits near chance, E will fail. MedScope's previous training results suggest it will. That makes this a cheap, decisive experiment of about 2-4 A100-hours.

---

### Bottom line for the authors' question

- **Can "better abstention" be the contribution by itself?**
  - As a *method*, mostly no. The data-processing ceiling (Section 3.2) means no abstention policy can raise ESG without new evidence-sensitive information. CoDoC- and Leibig-style deferral work only because their scores already discriminate.
  - As an *evaluation and theory* contribution (Framework A, with B's certified infeasibility), yes. It is principled, falsifiable and largely unclaimed.
- **The paper that would be novel and strong** pairs that theory with a mechanism that *adds* discrimination at test time (Framework C), certified by counterfactual risk control (Framework B).
- **Closest prior work to differentiate from:** ReCoVERR (ACL Findings 2024) and the 2026 BCEA preprint.
