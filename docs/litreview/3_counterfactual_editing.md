# Strand 3: Counterfactual image generation and editing for training and evaluating models (medical imaging focus)

Prepared for the MedScope paper (presence QA with lesion-erased, control-edit and lesion-free views). Date of searches: 2026-11-14.

---

## 1. Search boundary

**Scope.** Counterfactual (CF) image generation or editing used to train, evaluate or explain image models. This covers lesion insertion and removal, pseudo-healthy synthesis, causal generative models, CF augmentation, invariance training ("right for the right reasons"), perturbation-based faithfulness evaluation and its pitfalls, and how papers verify edit validity, including reader studies of synthetic or tampered medical images.

**Inclusion criteria:**
- Peer-reviewed work, 2018-2026.
- Venues: MICCAI and its workshops (LNCS), MIDL, IEEE TMI, MedIA, Nature-family journals, Radiology AI, Eur J Radiol, NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACCV, AAAI, TMLR, USENIX Security, Frontiers in AI.
- Two pre-2018 classics are cited only in the text, not in the ledger.
- arXiv-only preprints are excluded from the ledger.

**Tools:**
- WebSearch, in standard and extended modes.
- PubMed E-utilities (`search_articles`, `get_article_metadata`, `lookup_article_by_citation`).
- WebFetch of proceedings and abstract pages (MICCAI open access, ECVA, USENIX, arXiv abstract pages for method details).

**Queries run (2026-11-14):**
1. `RadEdit stress-testing biomedical vision models via diffusion image editing ECCV 2024`
2. `diffusion pseudo-healthy counterfactual lesion removal medical image MICCAI 2024 2025 evaluation clinicians` (extended)
3. `"Evaluating normative representation learning in generative AI for robust anomaly detection in brain imaging" Nature Communications`
4. `Fontanella "Diffusion models for counterfactual generation and anomaly detection in brain images" IEEE TMI`
5. `Roschewitz "counterfactual contrastive learning" Medical Image Analysis 2025`
6. `"Mitigating attribute amplification in counterfactual image generation" MICCAI 2024`
7. `CF-Seg Counterfactuals meet Segmentation MICCAI 2025`
8. `Auditing the inference processes of medical-image classifiers ... Nature Biomedical Engineering`
9. `CT-GAN malicious tampering of 3D medical imagery radiologists inject remove cancer USENIX Security`
10. `"Measuring axiomatic soundness of counterfactual image models" ICLR 2023`
11. `"Benchmarking counterfactual image generation" NeurIPS 2024`
12. `"Label-free liver tumor segmentation" synthetic tumors visual turing test radiologists CVPR 2023`
13. `CT-GAN radiologists misdiagnosed 99% injected 94% removed ...`
14. PubMed: `(counterfactual[Title] OR pseudo-healthy[Title] OR "healthy counterpart"[Title]) AND (image OR imaging OR radiograph OR MRI)`, from 2020 onwards. This returned 115 hits; the top 40 were screened and roughly 14 were relevant.
15. PubMed: `counterfactual image generation lesion removal diffusion (radiologist OR reader study)`. This returned 0 hits, which is itself informative: reader-validated lesion removal is rare.
16. PubMed author queries for Becker/CycleGAN, Xia/pseudo-healthy, Castro, Ktena and DeGrave, plus a citation lookup for Arun, Lang, Baur and Bluethgen.

**Limitations of this search:**
- Partway through, the shared WebSearch budget for this turn ran out. Three planned queries could not run: Becker CycleGAN (later verified via PubMed instead), Bercea PHANES, and Sanchez "What is healthy?".
- I did not use Firecrawl or Undermind search to get around the limit. Undermind was also avoided because its lookups write into the user's workspace library.
- One fetch was blocked: https://pmc.ncbi.nlm.nih.gov/articles/PMC11825664/ (Bercea et al., Nat Commun 2025, full text). The ledger row for that paper relies on its title and abstract-level knowledge.
- The **Verif.** column shows how each venue was checked:
  - **S**: venue and metadata verified in this session (PubMed record, proceedings page, or publisher page).
  - **K**: well-known paper whose venue comes from the reviewer's prior knowledge and was not re-checked in this session. These are high-confidence, but please spot-check them before camera-ready.

---

## 2. Evidence ledger (44 papers)

Abbreviations:
- **Use**: T = training, E = evaluation, X = explanation.
- **Validity**: how the paper checked that the counterfactual really has or lacks the target finding.

### 2a. Medical counterfactual generation: lesion removal, pseudo-healthy synthesis and causal models

| # | Title | First author et al. | Venue, year | What counterfactual is made, and how | Use | How edit validity was checked | Key result | Relevance to MedScope | URL | Verif. |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Deep structural causal models for tractable counterfactual inference | Pawlowski et al. | NeurIPS 2020 | SCM over (age, sex, brain volume, ventricle volume) to image. Normalising flows plus a conditional VAE perform abduction-action-prediction. | X/E | Anticounterfactual checks on synthetic data (Morpho-MNIST); regressors on brain-MRI counterfactuals | First tractable full counterfactual inference for images with deep mechanisms | Formal template for treating "erase lesion" as do(lesion=0) with abduction of patient-specific noise, rather than pixel inpainting | NeurIPS 2020 proceedings (URL not re-verified) | K |
| 2 | Causality matters in medical imaging | Castro, Walker, Glocker | Nat Commun 2020 | Conceptual: causal graphs for image-label relations (causal vs anticausal tasks) | Framework | n/a | Shows how the causal direction decides which biases and mitigations apply | Supports a causal definition of "evidence": the lesion causes the image; the report label is anticausal | https://doi.org/10.1038/s41467-020-17478-w | S |
| 3 | High fidelity image counterfactuals with probabilistic causal models | Ribeiro, Xia, Monteiro, Pawlowski, Glocker | ICML 2023 | Deep SCM with hierarchical VAE mechanisms on chest X-ray (sex, race, age, disease) and brain MRI. Adds counterfactual fine-tuning. | X/E/T | Auxiliary attribute classifiers measure effectiveness; also composition and reversibility | High-fidelity, identity-preserving CFs; CF fine-tuning improves effectiveness | Strongest open-source route to structural "disease-off" counterfactuals for CXR. Validity is checked by classifiers only, which is circular. | PMLR v202 (URL not re-verified) | K |
| 4 | Measuring axiomatic soundness of counterfactual image models | Monteiro et al. (Glocker group) | ICLR 2023 | Defines composition, reversibility and effectiveness axioms for CF image models | E | Proposes the metrics: oracle classifiers for effectiveness, null-intervention for composition, cycle for reversibility | Soundness is measurable without ground-truth counterfactuals | Directly reusable as automatic erasure-validity signals (Framework A) | https://iclr.cc/virtual/2023/poster/12177 | S (ICLR virtual page) |
| 5 | Benchmarking counterfactual image generation | Melistas et al. | NeurIPS 2024 (Datasets and Benchmarks) | Benchmark of VAE, GAN and diffusion counterfactual generators on SCM-defined datasets | E | Composition, effectiveness, minimality and realism metrics | No method dominates; the metrics trade off | Shows "realism" and "effectiveness" disagree, which matches MedScope's realistic-but-lesion-still-visible erasures | https://proceedings.neurips.cc/paper_files/paper/2024/hash/f04351c9fa1e22797c7d32c1f6d23948-Abstract.html | S |
| 6 | Mitigating attribute amplification in counterfactual image generation | Xia, Roschewitz, Ribeiro, Jones, Glocker | MICCAI 2024 | DSCM CXR counterfactuals; replaces hard labels with soft predictor labels in CF fine-tuning | T/E | Attribute classifiers (ResNet-34). Reviewers noted no expert validation. | Hard-label CF training amplifies unrelated attributes; soft labels reduce amplification while keeping effectiveness | Strong analogue: hard "lesion absent" targets on imperfect erasures are a source of bias. Motivates soft, validity-weighted targets. | https://papers.miccai.org/miccai-2024/521-Paper1002.html | S |
| 7 | Robust image representations with counterfactual contrastive learning | Roschewitz, Ribeiro, Xia, Khara, Glocker | MedIA 2025 (vol. 105, 103668) | DSCM counterfactuals of scanner or domain (and sex) used as contrastive positive pairs | T | Domain classifiers, downstream robustness | Improves robustness to acquisition shift on 5 CXR and mammography datasets; reduces sex disparities | Precedent for training with structural counterfactual pairs; the intervention is on nuisance variables rather than the finding | https://doi.org/10.1016/j.media.2025.103668 | S |
| 8 | CF-Seg: Counterfactuals meet segmentation | Mehta, Ribeiro, Xia, Roschewitz, ..., Glocker | MICCAI 2025 (LNCS 15967) | DSCM generates disease-removed (pleural effusion) CXR; lungs are then segmented on the CF image | E (inference-time) | Radiologist preference reader study on segmentations. No direct test that the effusion was removed. | Less lung under-segmentation; PE vs no-finding lung-volume gap 398 vs 859-893 (MIMIC) | Recent MICCAI use of a "healthy counterpart" at inference. Reviewers flagged a single pathology and weak validity evidence. | https://papers.miccai.org/miccai-2025/0144-Paper4597.html | S |
| 9 | A structural causal model for MR images of multiple sclerosis | Reinhold et al. | MICCAI 2021 | SCM with an MS lesion-volume variable; counterfactual images with lesion load changed | X/E | Qualitative; lesion-volume regressors | Plausible lesion-load counterfactuals | Graded (dose-response) lesion interventions, not just on/off (Framework D) | MICCAI 2021 LNCS (DOI not re-verified) | K |
| 10 | Pseudo-healthy synthesis with pathology disentanglement and adversarial learning | Xia, Chartsias, Tsaftaris | MedIA 2020 (vol. 64, 101719) | Disentangles a pathology map from "healthy-looking" content; GAN produces a subject-specific healthy image | E/X | Quantitative criteria plus a subjective human study | Better than baselines on ISLES, BraTS and Cam-CAN; recovers mass-effect deformation | Defines pseudo-healthy quality criteria: healthiness, identity, and recovery of mass effect. Inpainting ignores mass effect. | https://doi.org/10.1016/j.media.2020.101719 | S |
| 11 | Harmonizing pathological and normal pixels for pseudo-healthy synthesis | Zhang et al. | IEEE TMI 2022 | GAN pseudo-healthy synthesis with explicit harmonisation of lesion and normal pixels | E | Image metrics plus segmentation-based "healthiness" | Improved healthiness and identity | Healthy-counterpart alternative to LaMa | https://doi.org/10.1109/TMI.2022.3164095 | S |
| 12 | Diffusion models for medical anomaly detection | Wolleb et al. | MICCAI 2022 | DDIM noise encoding plus classifier guidance toward "healthy" produces a pseudo-healthy brain MRI | E | Anomaly-map Dice vs ground-truth masks | Weakly supervised lesion localisation via a healthy counterpart | Classifier-guided removal: validity is defined by the same kind of classifier, which is circular | MICCAI 2022 LNCS (DOI not re-verified) | K |
| 13 | Fast unsupervised brain anomaly detection and segmentation with diffusion models | Pinaya et al. | MICCAI 2022 | Latent DDPM "heals" anomalous regions; the residual is the anomaly | E | Segmentation Dice | Diffusion healing beats AE and transformer baselines | Shows healthy-counterpart generation from healthy-only training | MICCAI 2022 LNCS (DOI not re-verified) | K |
| 14 | What is healthy? Generative counterfactual diffusion for lesion localization | Sanchez, Kascenas, Liu, O'Neil, Tsaftaris | DGM4MICCAI 2022 (LNCS) | Classifier-free-guided diffusion translates to the "healthy" class | E | Dice of the difference map | Better localisation than earlier generative baselines | Conditional healthy-counterpart generation | DGM4MICCAI 2022 LNCS (DOI not re-verified) | K |
| 15 | Reversing the abnormal: Pseudo-healthy generative networks for anomaly detection (PHANES) | Bercea, Wiestler, Rueckert, Schnabel | MICCAI 2023 | Masks the anomaly estimate, then inpaints a pseudo-healthy version with a generative network | E | Anomaly-segmentation metrics | Better stroke-lesion localisation with less healthy-tissue alteration | Close analogue of MedScope's "mask then inpaint", but with a generator trained only on healthy anatomy | MICCAI 2023 LNCS (DOI not re-verified) | K |
| 16 | Diffusion models with implicit guidance for medical anomaly detection (THOR) | Bercea, Wiestler, Rueckert, Schnabel | MICCAI 2024 | DDPM sampling harmonised with the input at intervals; temporal anomaly maps keep healthy tissue | E | Indirect: anomaly detection and segmentation; visual faithfulness. No direct pseudo-healthy metric. | Better restoration detail and anomaly segmentation (ATLAS brain MRI, wrist X-ray) | Fixes "too much change outside the lesion", i.e. control-edit artifacts | https://papers.miccai.org/miccai-2024/225-Paper1315.html | S |
| 17 | Evaluating normative representation learning in generative AI for robust anomaly detection in brain imaging | Bercea et al. | Nat Commun 2025 (vol. 16) | Benchmarks pseudo-healthy reconstructions of many generative methods | E | New metrics for how normative the reconstructions are (full text fetch blocked; details unverified) | Many methods reproduce pathology or distort healthy anatomy; normative-representation quality predicts anomaly-detection robustness | Evidence that pseudo-healthy "erasures" often leak pathology, matching MedScope's ~40% residual findings | https://doi.org/10.1038/s41467-025-56321-y | S (title/venue) |
| 18 | Diffusion models for counterfactual generation and anomaly detection in brain images (Dif-fuse) | Fontanella, Mair, Wardlaw, Trucco, Storkey | IEEE TMI 2025 (44(9):3574-3585) | ACAT saliency gives a rough lesion mask; DDPM edits inside it and DDIM preserves outside; results are fused | E/X | KID vs real negatives (0.040); Dice of anomaly map (BraTS 0.699, WMH 0.569). No classifier or reader check. Authors note realism and localisation metrics disagree. | Best weakly supervised Dice | Shows a mixed DDPM/DDIM edit that keeps anatomy outside the mask. KID does not test whether the lesion was removed. | https://doi.org/10.1109/TMI.2024.3460391 | S |
| 19 | ACAT: Adversarial counterfactual attention for classification and detection in medical imaging | Fontanella et al. | ICML 2023 | Adversarial counterfactual perturbations give saliency used as attention during classifier training | T | Downstream accuracy | Better lesion classification and localisation on brain CT/MRI | Uses counterfactual differences as a training signal for where the evidence is | PMLR v202 (URL not re-verified) | K |
| 20 | Score-based counterfactual generation for interpretable medical image classification and lesion localization | Wang et al. | IEEE TMI 2024 | Score-based diffusion translates diseased to healthy; the difference map localises the lesion | X/E | Classifier flip rate plus localisation metrics | Improved localisation | Another diffusion healthy-counterpart generator | https://doi.org/10.1109/TMI.2024.3375357 | S |
| 21 | Controllable counterfactual generation for interpretable medical image classification | Liu, Wang, Ren, Lian, Ma | MICCAI 2024 | Classifier-free guidance plus attention injection (3D brain MRI, AD vs CN); guidance scale w controls the trade-off | T (augmentation) / X | SSIM, MSE and FID only; no clinicians | CF augmentation lifts accuracy 78.7% to 85.8% at w=5 but lowers it at w=1 | CF augmentation helps only when the edit is strong enough: a validity-strength knob matters | https://papers.miccai.org/miccai-2024/paper/1911_paper.pdf | S |
| 22 | Generating 3D pseudo-healthy knee MR images to support trochleoplasty planning | Wehrli et al. | IJCARS 2025 | Pseudo-healthy 3D knee MRI for surgical planning | X | Clinical plausibility review (per abstract) | Clinically usable healthy-shape targets | Shows clinical (not classifier) validation of healthy counterparts | https://doi.org/10.1007/s11548-025-03343-y | S |
| 23 | HealthiVert-GAN: pseudo-healthy vertebral image synthesis for interpretable compression-fracture grading | Zhang et al. | IEEE JBHI 2025 | Pseudo-healthy vertebra; the height-loss difference is used for grading | T/X | Grading accuracy | Interpretable grading via the healthy counterpart | Uses the healthy counterpart as a measurement of the evidence, not just augmentation | https://doi.org/10.1109/JBHI.2025.3572458 | S |

### 2b. Medical counterfactual explanation, auditing and stress-testing

| # | Title | First author et al. | Venue, year | What counterfactual is made, and how | Use | How edit validity was checked | Key result | Relevance to MedScope | URL | Verif. |
|---|---|---|---|---|---|---|---|---|---|---|
| 24 | RadEdit: stress-testing biomedical vision models via diffusion image editing | Pérez-García et al. | ECCV 2024 | CXR latent diffusion (MIMIC, CheXpert, ChestX-ray8) with DDPM inversion. Uses an **edit mask** plus a **keep mask** (e.g. keep the chest drain while removing pneumothorax). | E (stress test) | BioViL-T image-text editing score; edits under 0.2 are discarded (the authors say this misses artifacts). A "strong" model confirms drops are not artifacts. No radiologist check reported. | Weak pneumothorax classifier 93.3% to 17.9% on edited sets; the strong model stays at 81.7%. LANCE and DiffEdit shift lung borders and remove devices. | Closest medical precedent for removal views as an evaluation. Its keep mask is the analogue of MedScope's control edit. RadEdit keeps only edits that pass an automatic validity filter. | https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01923.pdf | S |
| 25 | Explaining the black-box smoothly: a counterfactual approach | Singla, Eslami, Pollack, Wallace, Batmanghelich | MedIA 2023 (epub 2022) | Conditional GAN progressively exaggerates the classifier's posterior on CXR | X | Classifier flip, identity preservation, clinical-metric checks (e.g. cardiothoracic ratio) | Smooth counterfactual sequences reveal decision features | Graded "progressive" counterfactuals: a dose-response design (Framework D) | https://doi.org/10.1016/j.media.2022.102721 | S |
| 26 | Gifsplanation via latent shift: a simple autoencoder approach to counterfactual generation for chest X-rays | Cohen et al. | MIDL 2021 | Latent shift along the classifier gradient in autoencoder space | X | Reader study on explanation usefulness (per paper) | Counterfactual GIFs judged more useful than attribution maps | Early CXR counterfactual with physician feedback | PMLR v143 (URL not re-verified) | K |
| 27 | Auditing the inference processes of medical-image classifiers by leveraging generative AI and the expertise of physicians | DeGrave, Cai, Janizek, Daneshjou, Lee | Nat Biomed Eng 2023 (9:294-306) | StyleGAN-style counterfactuals flip melanoma classifier outputs | X/E (audit) | Dermatologists interpret what changed; two readers agree on direction. Confirmatory programmatic perturbations. | Classifiers use real cues (pigment) and spurious ones (background skin, colour balance) | Template for physician-in-the-loop interpretation of counterfactual pairs | https://doi.org/10.1038/s41551-023-01160-9 | S |
| 28 | Using generative AI to investigate medical imagery models and datasets | Lang et al. | eBioMedicine 2024 (102:105075) | StylEx attribute counterfactuals for fundus, external-eye and CXR classifiers | X | Interdisciplinary expert review of attributes | Workflow for hypothesis generation; finds known and spurious signals | Experts review counterfactuals but do not check that they are valid | https://doi.org/10.1016/j.ebiom.2024.105075 | S |
| 29 | GANterfactual: counterfactual explanations for medical non-experts using generative adversarial learning | Mertes et al. | Front Artif Intell 2022 | CycleGAN translation of pneumonia to normal CXR | X | User study with lay users | Counterfactuals beat LIME and LRP in mental-model measures | CycleGAN removal; lay rather than expert validation | https://doi.org/10.3389/frai.2022.825565 | S |
| 30 | Generative models improve fairness of medical classifiers under distribution shifts | Ktena et al. | Nat Med 2024 (30:1166-1173) | Label- and attribute-conditioned diffusion augmentation (histopathology, CXR, dermatology) | T | Downstream robustness and fairness; expert checks of samples (supplement) | Synthetic augmentation improves out-of-distribution robustness and subgroup fairness | Large-scale evidence that diffusion-synthesised training data helps in medicine | https://doi.org/10.1038/s41591-024-02838-6 | S |
| 31 | A vision-language foundation model for the generation of realistic chest X-ray images (RoentGen) | Bluethgen, Chambon et al. | Nat Biomed Eng 2024/25 (9:494-506) | Text-conditioned latent diffusion for CXR | T/E | Board-certified radiologist realism and prompt-correctness review | Realistic, controllable CXR | Could act as a text-conditioned generator for "same anatomy, no finding". Readers checked realism, not finding removal. | https://doi.org/10.1038/s41551-024-01246-y | S |
| 32 | Fast diffusion-based counterfactuals for shortcut removal and generation | Weng, Pegios, Petersen, Feragen, Bigdeli | ECCV 2024 | Diffusion CFs that remove or insert shortcuts (e.g. chest drains, rulers) | E/T | Shortcut classifier plus visual inspection | Diagnoses and quantifies shortcut reliance in CXR and skin models | Same "erase X, check model" logic, applied to shortcuts | ECCV 2024 LNCS (DOI not re-verified) | K |
| 33 | Counterfactual causal-effect intervention for interpretable medical VQA | Cai et al. | IEEE TMI 2024 | Feature-level counterfactual intervention in a medical VQA model (not pixel edits) | T | n/a (feature level) | Better VQA accuracy and interpretability | Closest medical-VQA counterfactual training. It intervenes in feature space, so no image-validity problem arises. | https://doi.org/10.1109/TMI.2024.3425533 | S |

### 2c. Reader studies of synthetic or tampered medical images (edit validity by humans)

| # | Title | First author et al. | Venue, year | What counterfactual is made, and how | Use | How edit validity was checked | Key result | Relevance to MedScope | URL | Verif. |
|---|---|---|---|---|---|---|---|---|---|---|
| 34 | CT-GAN: Malicious tampering of 3D medical imagery using deep learning | Mirsky, Mahler, Shelef, Elovici | USENIX Security 2019 | 3D conditional GAN injects or removes lung nodules in CT (in-painting conditioned on the local context) | E (attack) | 3 radiologists plus a CAD AI. As recalled from the full paper, without being told: 99% of injected scans called malignant, 94% of removed scans called healthy; after being told of tampering: 60% and 87%. | Domain-trained removal fooled experts | Contrast with MedScope: a domain-specific conditional generator achieved high reader-judged removal on small nodules, whereas generic LaMa leaves ~40% residual findings | https://www.usenix.org/conference/usenixsecurity19/presentation/mirsky | S (venue); numbers K |
| 35 | Injecting and removing suspicious features in breast imaging with CycleGAN: a pilot study | Becker et al. | Eur J Radiol 2019 (120:108649) | CycleGAN injects or removes suspicious mammographic features | E | 3 radiologists, MRMC-ROC | Low resolution: readers could not tell modified from original (**AUC 0.55**). High resolution: cancer detection fell 0.80 to 0.37 on modified images, but readers spotted manipulation (AUC 0.94) because of artifacts. | Almost the same "AUC 0.55" indistinguishability as MedScope. Shows that indistinguishability and removal effectiveness are separate axes and both must be reported. | https://doi.org/10.1016/j.ejrad.2019.108649 | S |
| 36 | Label-free liver tumor segmentation | Hu et al. | CVPR 2023 | Hand-crafted synthetic liver tumours (texture, shape, mass effect, capsule) inserted into healthy CT | T | Visual Turing test: junior (6 yr) and senior (15 yr) professionals, 50 CTs. Junior accuracy 26.5%; senior 71.0% (sensitivity 63.2%, specificity 83.3%). | Synthetic-only training gives Dice 59.8 vs 57.5 for training on real annotated tumours | Lesion insertion with reader validation; realism tracks experience level | https://openaccess.thecvf.com/content/CVPR2023/html/Hu_Label-Free_Liver_Tumor_Segmentation_CVPR_2023_paper.html | S |
| 37 | Towards generalizable tumor synthesis (DiffTumor) | Chen et al. | CVPR 2024 | Diffusion tumour synthesis transferred across abdominal organs | T | Downstream segmentation (readers in the earlier work) | Synthetic early tumours generalise across organs | Insertion as the dual of erasure; organ-agnostic generator | CVPR 2024 open access (URL not re-verified) | K |

### 2d. Perturbation-based faithfulness evaluation and its pitfalls

| # | Title | First author et al. | Venue, year | What counterfactual is made, and how | Use | How edit validity was checked | Key result | Relevance to MedScope | URL | Verif. |
|---|---|---|---|---|---|---|---|---|---|---|
| 38 | Sanity checks for saliency maps | Adebayo et al. | NeurIPS 2018 | Model and label randomisation tests | E | n/a | Many saliency maps are independent of the model | Explanations must be tested for dependence on the model | NeurIPS 2018 proceedings (URL not re-verified) | K |
| 39 | A benchmark for interpretability methods in deep neural networks (ROAR/KAR) | Hooker, Erhan, Kindermans, Kim | NeurIPS 2019 | Remove top-k features (and keep-and-retrain), then retrain | E | Retraining avoids distribution shift from removal | Without retraining, accuracy drops reflect the shift, not importance | Core pitfall: an edited-image accuracy drop confounds evidence removal with the edit being OOD. MedScope's control edit is the right fix. | NeurIPS 2019 proceedings (URL not re-verified) | K |
| 40 | A consistent and efficient evaluation strategy for attribution methods (ROAD) | Rong, Leemann, Borisov, Kasneci, Kasneci | ICML 2022 | Noisy linear imputation for removal | E | Shows the mask shape itself leaks class information | Removal metrics are biased by information leaking through the mask; ROAD removes the leak without retraining | Lesion-shaped holes leak "lesion was here", which motivates MedScope's same-shape control edit and a held-out editor | PMLR v162 (URL not re-verified) | K |
| 41 | The out-of-distribution problem in explainability and search methods for feature importance explanations | Hase, Xie, Bansal | NeurIPS 2021 | Counterfactual feature removal | E | Theoretical and empirical OOD analysis | Removal-based explanations are confounded by model behaviour on OOD inputs; proposes in-distribution training with removals | Training on erased views (as MedScope does) is the recommended fix, but it can teach "edit detected, so say no" | NeurIPS 2021 proceedings (URL not re-verified) | K |
| 42 | Decoupling pixel flipping and occlusion strategy for consistent XAI benchmarks | Blücher, Vielhaben, Strodthoff | TMLR 2024 | Compares occlusion and imputation strategies, including generative inpainting | E | Agreement across occlusion strategies | Faithfulness rankings change with the occlusion or inpainting method | Generator dependence: MedScope's held-out TELEA and SD test is necessary, and agreement across editors should be a reported metric | TMLR 2024, OpenReview (URL not re-verified) | K |
| 43 | Explaining image classifiers by counterfactual generation (FIDO) | Chang, Creager, Goldenberg, Duvenaud | ICLR 2019 | Generative in-fill (CA-GAN) vs blur or zero removal | X/E | Compares in-fill strategies | Generative in-fill gives more relevant and less artifact-driven saliency | Origin of "use a generative in-filler for removal". Its weakness: the in-filler can restore the object. | ICLR 2019, OpenReview (URL not re-verified) | K |
| 44 | Assessing the trustworthiness of saliency maps for localizing abnormalities in medical imaging | Arun et al. | Radiology: AI 2021 (3:e200267) | Saliency randomisation and repeatability on CXR | E | n/a | All 8 saliency methods failed at least one trust criterion | Medical evidence that post-hoc attribution is unreliable, so intervention-based (counterfactual) evaluation is preferable | https://doi.org/10.1148/ryai.2021200267 | S |

### 2e. Counterfactual training and invariance (general CV, VQA, "right for the right reasons")

These are cited for the framework sections. All are venue-confirmed from prior knowledge (K).

- **Kaushik, Hovy, Lipton.** "Learning the difference that makes a difference with counterfactually-augmented data." ICLR 2020. Humans minimally edit inputs to flip labels; training on the pairs reduces reliance on spurious features. Its validity check is human editing; its image analogue is reader-validated erasures.
- **Teney, Abbasnejad, van den Hengel.** "Learning what makes a difference from counterfactual examples and gradient supervision." ECCV 2020. Aligns input gradients with the counterfactual difference vector. Closest to the "paired-view consistency" MedScope already tried.
- **Agarwal, Shetty, Fritz.** "Towards causal VQA: revealing and reducing spurious correlations by invariant and covariant semantic editing." CVPR 2020. GAN-based object removal for VQA. It distinguishes *invariant* edits (removing irrelevant objects should not change the answer) from *covariant* edits (removing the queried object should change the count). This maps one-to-one onto MedScope's control edit vs erasure. Removal validity was checked qualitatively (details from memory; re-check before citing).
- **Chen et al.** "Counterfactual samples synthesizing for robust VQA" (CSS). CVPR 2020. Masks critical objects and assigns "not that answer" targets.
- **Veitch, D'Amour, Yadlowsky, Eisenstein.** "Counterfactual invariance to spurious correlations." NeurIPS 2021. Shows counterfactual invariance can be implied by conditional-independence regularisers chosen according to the causal graph (causal vs anticausal).
- **Sauer and Geiger.** "Counterfactual generative networks." ICLR 2021. Training on factorised (shape, texture, background) counterfactuals improves OOD robustness.
- **Rieger, Singh, Murdoch, Yu.** "Interpretations are useful: penalizing explanations to align neural networks with prior knowledge" (CDEP). ICML 2020. Penalises attribution to known artifacts (ISIC colour patches).
- **Schramowski et al.** "Making deep neural networks right for the right scientific reasons by interacting with their explanations." Nat Mach Intell 2020.
- **Bassi et al.** "Improving deep neural network generalization and robustness to background bias via layer-wise relevance propagation optimization" (ISNet). Nat Commun 2024. CXR background-bias suppression.
- **Augustin et al.** "Diffusion visual counterfactual explanations." NeurIPS 2022.
- **Jeanneret et al.** "Diffusion models for counterfactual explanations." ACCV 2022.
- **Schlüter et al.** "Natural synthetic anomalies for self-supervised anomaly detection and localization" (NSA). ECCV 2022. Synthetic lesion insertion via Poisson blending.
- **DeGrave, Janizek, Lee.** "AI for radiographic COVID-19 detection selects shortcuts over signal." Nat Mach Intell 2021. Uses counterfactual (CycleGAN) and saliency analysis to show shortcut use.
- **Baur et al.** "Autoencoders for unsupervised anomaly segmentation in brain MR images: a comparative study." MedIA 2021 (S, https://doi.org/10.1016/j.media.2020.101952).

Pre-2018 classics, cited for context only: Ross, Hughes, Doshi-Velez, "Right for the right reasons", IJCAI 2017; Pezeshk et al., "Seamless lesion insertion for data augmentation in CAD training", IEEE TMI 2017.

**Total:** 44 ledger rows plus 14 supporting papers. 31 were verified in this session (S) and the rest come from prior knowledge (K).

---

## 3. What the literature says about validating erasures

**1. Most papers never test whether the erasure removed the finding.** They test one of three proxies:
- (a) **Realism or distribution distance** (FID, KID). Example: Dif-fuse reports KID against real negatives, and its authors note that realism and localisation disagree.
- (b) **Flip rate of an auxiliary classifier.** Used by Wolleb, Sanchez, Wang (TMI 2024), Ribeiro/Monteiro "effectiveness", Xia 2024 and Weng. This is circular when the same or a similar classifier family is the object under study, and it is fooled by adversarial or shortcut edits.
- (c) **Indirect downstream metrics** (anomaly-map Dice, downstream accuracy). Used by THOR, PHANES, Pinaya, Liu 2024 and CF-Seg.

RadEdit adds an image-text consistency filter (BioViL-T score > 0.2), but its authors state this filter misses editing artifacts. It then uses a "strong model" sanity check.

**2. Physician verification of edits is rare, and verification of *removal* is rarer still.** Of the ~33 medical papers in the ledger, about 9 involve clinicians at all:
- CT-GAN, Becker, Hu, RoentGen, DeGrave, Lang, Cohen, CF-Seg, Xia 2020 (human study).
- Only **two** ask readers whether a removed lesion is still there: CT-GAN (lung CT) and Becker (mammography). Both are adversarial-attack papers, not ML-training papers.
- No paper in this search trains a model on erasures and *also* reader-validates those training erasures.
- The PubMed query for counterfactual lesion removal with diffusion plus a radiologist or reader study returned zero hits.

**3. Indistinguishability and removal effectiveness are separate axes.**
- Becker 2019 is the cleanest evidence. At low resolution, readers could not tell edited from original images (AUC 0.55, the same as MedScope's), and cancer-detection AUC was not significantly changed.
- So "readers can't tell it's edited" says nothing about "the finding is gone". At high resolution the edits removed cancers (detection 0.80 to 0.37) but were detectable (AUC 0.94).
- Hu 2023 shows that realism judgements depend on reader seniority: the junior reader was at 26.5% accuracy and the senior at 71%.

**4. Known artifacts of erasure and inpainting:**
- **Mask-shape leakage.** The hole itself encodes "lesion was here" (ROAD, Rong 2022). MedScope's same-shape control edit addresses this, as does the keep-mask idea in RadEdit.
- **OOD artifacts.** Inpainted regions are off the data manifold, so models may react to "edited-ness" rather than to lesion absence (ROAR, Hooker 2019; Hase 2021). Training on edited views fixes the OOD problem but can create a shortcut: "texture of LaMa means say no".
- **Pathology leakage or restoration.** Generative in-fillers trained on mixed data re-synthesise the lesion or a lesion-like structure; this is the motivation for THOR, PHANES and Bercea 2025. MedScope's ~40% reader-visible residual findings outside colonoscopy fit this.
- **Global and correlated changes.** Diffusion edits alter structures correlated with the finding (pneumothorax removal deletes the chest drain; LANCE shifts lung borders), and DSCM edits amplify unrelated attributes (Xia 2024). These spoil control edits.
- **Mass effect and secondary signs.** Pseudo-healthy synthesis must undo deformation and secondary signs (oedema, shadowing, posterior acoustic enhancement in ultrasound, midline shift in MRI). Local inpainting cannot (Xia 2020). This is a plausible reason erasures fail in breast ultrasound, brain MRI and CXR but work in colonoscopy, where polyps are locally bounded with weak secondary signs.
- **Generator dependence.** Faithfulness rankings change with the infill method (Blücher 2024; Chang 2019). Results must be shown across editors.

**5. Emerging best practices** (none yet a standard in medical imaging):
- Report effectiveness, composition (null edit leaves the image unchanged), reversibility and minimality (Monteiro 2023; Melistas 2024).
- Use keep masks or matched control edits (RadEdit).
- Use soft rather than hard counterfactual labels (Xia 2024).
- Use generators trained only on healthy anatomy (pseudo-healthy literature).
- Run cross-model checks with an independent "strong" model (RadEdit).
- Run expert reader studies with MRMC analysis on a stratified sample (Becker).

---

## 4. Gaps MedScope could own

1. **Validated counterfactual supervision for VLMs.** No published work trains a medical VLM, or even a classifier, on lesion-erased views with per-sample, reader-calibrated validity. MedScope already has reader data (~40% residual findings). That is a rare asset that allows learning and auditing erasure validity.
2. **An explanation for the plateau.** The literature predicts that hard "absent" targets on invalid erasures inject systematic label noise (Xia 2024's attribute amplification is the generator-side analogue). This would explain why DPO, consistency loss, GRPO and larger LoRA all failed to move ESG: they optimise the same partly wrong targets. To my knowledge, nobody has tested whether a counterfactual-training ceiling is set by edit validity.
3. **Erasure realism and erasure effectiveness are reported as one number.** MedScope can report both axes separately (Becker-style), per modality, with secondary signs analysed.
4. **Generator-agnostic evaluation of evidence sensitivity.** Faithfulness metrics depend on the removal operator (Blücher, Chang, ROAD). In medicine, no benchmark reports evidence sensitivity across a family of editors with an agreement statistic. MedScope's held-out TELEA and SD views are a start.
5. **Graded or dose-response counterfactuals for presence questions.** Medical counterfactual work is either binary (healthy vs diseased) or explains a classifier's posterior (Singla, Reinhold). Nobody uses a graded intervention on lesion conspicuity (size, contrast, secondary signs) to test whether a VLM's "yes" probability is monotone and well calibrated near the detection threshold.
6. **Modalities.** There is almost no counterfactual-editing literature for **breast ultrasound** or **colonoscopy**; nearly all of it is brain MRI, CXR, dermatology or mammography. Ultrasound speckle and acoustic shadowing are likely failure modes of generic inpainting.
7. **Causal definition of "evidence" for VQA.** Agarwal 2020's invariant and covariant edits plus the DSCM abduction view have not been combined into a formal estimand for medical presence QA. One possible estimand: the effect of do(lesion = absent) on the answer, minus the effect of a matched do(edit artifact).

---

## 5. Candidate frameworks

### A. Validity-calibrated counterfactual supervision (VCCS): learning which erasures are valid

This is the recommended core.

**Mechanism:**
1. Train a small **erasure-validity estimator** v(x_erased, mask, x_orig) ∈ [0,1], estimating P(a reader sees no finding).
   - Labels come from the existing reader annotations (~40% residual outside colonoscopy).
   - Weak features: an independent lesion detector or segmenter on the erased region; a residual-saliency difference vs the control edit; cross-editor agreement (LaMa, TELEA and SD produce similar results); Monteiro-style reversibility (re-insert, then compare); and mask-boundary statistics.
2. Replace hard "No" targets on erased views with **soft targets** 1 − v. Gate the evidence loss so it acts only where v is high. Erasures with low v become *positives*; this is a free hard-positive mining source.
3. Report ESG on **reader-verified-valid** erasures as the primary endpoint, alongside the full set.

**Closest work and the difference:**
- Xia et al. MICCAI 2024 uses soft labels, but for generator fine-tuning, with classifier-derived labels.
- RadEdit uses a hard validity filter from BioViL-T and no readers.
- Kaushik 2020 uses human-validated counterfactuals for text.
- VCCS differs in three ways: (i) per-sample, reader-calibrated validity in medical imaging; (ii) it is used to supervise a VLM's presence answers; (iii) invalid erasures are recycled as hard positives.

**Falsifiable predictions:**
- (P1) If the ESG plateau is caused by invalid-erasure label noise, VCCS improves ESG on the reader-valid subset by a pre-registered margin (e.g. ≥ 5 points) over plain fine-tuning, in breast ultrasound, MRI and CXR. It should give little or no gain in colonoscopy, where erasures are already valid.
- (P2) On reader-invalid erasures, the VCCS model says "yes" more often than plain fine-tuning does. This is correct behaviour.
- (P3) If neither P1 nor P2 holds, label noise is not the bottleneck. That negative result is publishable and redirects effort to Framework B.

**Compute on one A100:**
- Validity estimator: ConvNeXt-T or ViT-S on about 10^4 to 10^5 erased crops, 1-3 GPU-hours.
- LoRA fine-tuning of the 4B VLM: about the same cost as the current fine-tuning (roughly 0.5-2 days).
- Reader calibration reuses the existing annotations, plus about 200 new stratified cases per modality.

### B. Healthy-counterpart generation instead of inpainting (structural, modality-specific)

**Mechanism:**
1. Replace LaMa with a **pseudo-healthy generator trained only on lesion-free images** of each modality. Options:
   - A latent diffusion model with THOR- or Dif-fuse-style sampling: DDPM inside a dilated mask, DDIM or harmonisation outside.
   - For CXR, a DSCM with abduction (Ribeiro 2023) or a RadEdit-style keep mask.
2. The dilated mask covers secondary signs: shadowing and enhancement in ultrasound, oedema and mass effect in MRI.
3. Control edits use the *same generator* on a lesion-free region, so artifact statistics match.
4. Train the VLM on these views, optionally combined with Framework A.

**Closest work and the difference:** PHANES, THOR, Dif-fuse and Wolleb, Pinaya and Sanchez all use healthy counterparts for anomaly localisation, never as supervision for a VLM's presence answers. CF-Seg uses them at inference for segmentation. B is the first to (i) measure reader-judged *removal* rates of healthy-counterpart vs inpainting erasures and (ii) show the downstream effect on evidence sensitivity.

**Falsifiable predictions:**
- (P1) The reader residual-finding rate drops from ~40% to ≤15% in breast ultrasound, MRI and CXR.
- (P2) Editor-detection AUC by readers stays ≤0.6.
- (P3) Training on these views lowers ESG relative to LaMa-trained models, measured on reader-valid erasures from *both* generators. If the residual rate falls but ESG does not move, generator quality is not the bottleneck.

**Compute:**
- Fine-tune a pretrained latent diffusion model at 256-512 px per modality on lesion-free images: about 1-2 A100-days each, so 3 days for the 3 problematic modalities.
- Sampling: about 1-3 s per image. Generating 20k erasures takes a few GPU-hours.

### C. Generator-agnostic evidence: editors as environments

**Mechanism:**
1. Treat each editor (LaMa, TELEA, SD inpainting, the healthy-counterpart generator from B, and patch-transplant from lesion-free images) as an environment e.
2. Define the per-sample evidence effect as Δ_e = f(x) − f(erase_e(x)), and the artifact effect as A_e = f(x) − f(control_e(x)).
3. Train with:
   - a difference-in-differences target, so that (Δ_e − A_e) is large on lesion images and ≈0 on lesion-free images;
   - a V-REx or IRM-style penalty on the variance of (Δ_e − A_e) across editors.
4. The model can then only lower ESG through features shared across editors, which by construction is the lesion and not the editor's texture.

**Closest work and the difference:**
- Agarwal CVPR 2020 (invariant and covariant edits, single editor).
- Veitch 2021 (counterfactual invariance).
- Blücher 2024 and ROAD (occlusion dependence, evaluation only).
- MedScope's earlier paired-view consistency loss used one editor and no artifact baseline. C makes the *editor* the nuisance variable and uses the control edit as the artifact estimate.

**Falsifiable predictions:**
- ESG on a held-out editor (e.g. SD or a new one) improves relative to single-editor training. The gap between in-editor and held-out-editor ESG shrinks by ≥50%.
- If the gain disappears when evaluating only reader-valid erasures, C was learning editor statistics rather than evidence.

**Compute:** generate K=4 editors' views offline (CPU or GPU, hours), then run one LoRA training with a multi-view batch. That costs about 1.5-2× current training, roughly 1-3 A100-days.

### D. Structural (dose-response) definition of evidence

**Mechanism:**
1. Define the SCM: image = g(anatomy, lesion(size, contrast, secondary signs), acquisition, edit artifact).
2. Define evidence sensitivity as the **controlled direct effect** of lesion conspicuity on P("yes"), with the artifact held fixed by matched controls.
3. Produce **graded interventions**, partial erasures at conspicuity α ∈ {1, 0.75, 0.5, 0.25, 0}. Use the healthy-counterpart generator from B with mask-interpolated latent blending, or a DSCM with a lesion-size variable as in Reinhold 2021.
4. Measure each grade's validity with Framework A's estimator or with readers.
5. Train with a monotonicity and calibration loss, so that P("yes" | α) tracks the reader-detection probability at α (a psychometric curve). Do not train toward a binary target.

**Why this helps:** an erasure that leaves a faint finding is no longer "wrong". It is simply a lower-α point whose target is the reader-measured detection rate. This removes the validity problem by construction.

**Closest work and the difference:**
- Singla 2023 (progressive exaggeration, for explanation).
- Reinhold 2021 (lesion-load counterfactuals).
- Pawlowski 2020 and Ribeiro 2023 (DSCM abduction).
- None calibrate a model's presence answer to human psychometric curves under graded interventions, or use them for training.

**Falsifiable predictions:**
- (P1) The D-trained model's P("yes") is monotone in α for ≥90% of cases (plain fine-tuning is lower).
- (P2) D improves sensitivity on *real* small or subtle lesions and lowers false claims on real lesion-free images. This is the external-validity test.
- (P3) ESG improves on reader-valid full erasures. If (P1) holds but (P2) fails, graded counterfactuals teach generator-specific contrast cues.

**Compute:**
- Generating 5 grades × about 10k lesions with the B generator takes a few A100-hours.
- LoRA training takes about 1-2 days.
- Psychometric reader calibration needs about 100-150 cases × 5 grades × 2 readers per modality. This is the main cost, and it is human rather than GPU.

### E. Counterfactual-validated selective answering (lower priority)

Inference-time checks only helped through abstention. A fallback is to formalise that: use the A-estimator and the cross-editor disagreement from C as nonconformity scores in split-conformal selective prediction, with a guaranteed bound on false-claim rate at fixed coverage.

- **Closest work:** MedScope's own verifier, plus selective-prediction work (strand 5).
- **Difference:** a coverage guarantee driven by counterfactual validity.
- **Prediction:** at matched coverage, the false-claim rate is lower than with confidence-only abstention.
- **Compute:** negligible beyond A.

### Recommendation

Build the paper around **A + D**, with B as the generator upgrade and C as the robustness evaluation. Together they give a single framework, "validity-calibrated structural counterfactuals". The narrative:

1. Diagnose: the eight failed methods share hard targets on partly invalid erasures (supported by reader data and Becker 2019's realism vs effectiveness dissociation).
2. Model: write evidence as a structural, graded intervention.
3. Learn: learn the validity of each intervention from readers.
4. Train: train the VLM to match reader psychometrics.
5. Evaluate: across held-out editors.

The A-alone ablation tests the label-noise hypothesis cheaply first (about 1 week on one A100).
