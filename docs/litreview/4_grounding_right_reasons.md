# Strand 4: Evidence grounding and "right for the right reasons" (RRR)

Prepared for MedScope (4B VLM agent, counterfactual lesion-erasure benchmark, metric ESG = P(absent or refer | erased) - P(absent or refer | control)).
Date of search: 2026-11-14.

---

## 1. Search boundary

**Scope.** Peer-reviewed work from 2017 to 2026, with priority on 2022-2026, covering:
- explanation and attention supervision (RRR, GAIN or attention mining, CDEP, HINT or SCR, energy loss, ISNet, gaze supervision);
- counterfactual-pair supervision (gradient supervision, CSS, counterfactual and invariant augmentation);
- grounded medical VLMs and grounded report generation;
- look-then-answer, visual chain of thought and zoom agents;
- image-conditional preference optimisation;
- mechanistic and causal evaluation of whether VLM answers depend on the right image region.

**Venues accepted.** MICCAI, MIDL, MedIA, TMI, Radiology:AI, NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACL/EMNLP/NAACL (incl. Findings), IJCAI, MLHC (PMLR), Nature Machine Intelligence, Nature Communications and Nature Methods.

**Excluded.** arXiv-only preprints. They are listed separately at the end of this section and are not in the ledger.

**Tools.** WebSearch (about 30 standard queries and 2 "extended" queries) and WebFetch (4 page reads: MICCAI 2025 paper pages, ACL Anthology PDF, one arXiv preprint for the watch list). PubMed, Firecrawl and Undermind were not used. **The shared web-search budget ran out partway through.** Entries marked **V** had their venue confirmed live this session from a proceedings, publisher, conference-virtual or anthology page. Entries marked **†** are canonical papers whose venue comes from established proceedings records but was not re-checked live because of the budget. For **†** entries the URL points to the arXiv version of the peer-reviewed paper, or to a CVF page built from the standard URL pattern. Re-verify † entries before submission.

**Queries run (2026-11-14):**
1. `MAIRA-2 grounded radiology report generation published venue`
2. `RadVLM multitask conversational vision-language model radiology Deperrois published`
3. `MedRegA interpretable bilingual multimodal large language model region ICLR 2025` (+ follow-up `"Interpretable Bilingual Multimodal ..." openreview ICLR`)
4. `GradMask reduce overfitting by regularizing saliency MIDL 2019 Simpson Viviano`
5. `"Saliency is a possible red herring when diagnosing poor generalization" ICLR 2021`
6. `ISNet layer-wise relevance propagation optimization background bias Nature Communications 2024 Bassi`
7. `"Studying How to Efficiently and Effectively Guide Models with Explanations" ICCV 2023 energy loss bounding box`
8. `"Contrastive Region Guidance" improving grounding vision-language models without training ECCV 2024`
9. `mDPO conditional preference optimization multimodal large language models EMNLP 2024 image ignored`
10. `ChEX interactive localization and region description chest X-rays ECCV 2024`
11. `BiRD refer-and-ground multimodal large language model biomedical MICCAI 2024 Med-GRIT-270k`
12. `GEMeX grounded explainable medical VQA chest X-ray ICCV 2025`
13. `ViGoRL grounded reinforcement learning visual reasoning Sarch NeurIPS 2025`
14. `DeepEyes incentivizing thinking with images reinforcement learning accepted conference`
15. `"Worse than Random" ... ProbMed Findings ACL`
16. `Saab "Reducing reliance on spurious features in medical image classification with spatial specificity" MLHC 2022`
17. `"Right for the Wrong Reason: Can Interpretable ML Techniques Detect Spurious Correlations" MICCAI 2023`
18. `"MLLMs know where to look" training-free perception small visual details ICLR 2025`
19. `"Cross-modal Information Flow in Multimodal Large Language Models" CVPR 2025`
20. `Golovanevsky "What Do VLMs NOTICE" NAACL 2025`
21. `Neo "Towards Interpreting Visual Information Processing in Vision-Language Models" ICLR 2025`
22. `MedVLM-R1 ... MICCAI 2025`
23. `"Follow My Eye" using gaze to supervise computer-aided diagnosis IEEE TMI`
24. `BiomedParse ... Nature Methods invalid prompt object absent`
25. (extended) `supervising attention maps of multimodal large language model with bounding boxes loss reduces hallucination 2025 conference`
26. (extended) `medical vision-language model answers without looking at image visual dependency lesion masked counterfactual evaluation 2025 MICCAI`
27. `image-conditioned preference optimization corrupted or masked image rejected sample multimodal DPO hallucination ICLR 2025 CVPR 2025`
28. `medical visual grounding reinforcement learning GRPO bounding box reward MICCAI 2025 grounded reasoning`
29. `"Taking a HINT" ...; "negative case analysis of visual grounding methods for VQA" ACL 2020`
30. `CHiP cross-modal hierarchical DPO ICLR 2025 OR "OPA-DPO" CVPR 2025`
31. (extended-style) `segmentation mask guided attention regularization lesion classification out-of-distribution generalization shortcut medical imaging ...`
32. `"Visual CoT" ... NeurIPS 2024 bounding box`
33. (blocked by budget) Teney ECCV 2020; Chang CVPR 2021; Friedrich NMI 2023; Rieger ICML 2020; Petryk CVPR 2022.

**Preprints found and excluded from the ledger (watch list):**
| Item | Status found 2026-11-14 | Why it matters |
|---|---|---|
| MAIRA-2: Grounded Radiology Report Generation (Bannur et al.), arXiv 2406.04449 | arXiv / Microsoft tech report only; no venue found | Grounded findings with boxes. Its grounding is evaluated as box accuracy, not as reliance on the box. |
| RadVLM (Deperrois et al.), arXiv 2502.03333 | arXiv + PhysioNet release; no venue found | Multitask CXR VLM with grounding. |
| GradMask (Simpson et al.), arXiv 1904.07478 | arXiv; superseded by the peer-reviewed Viviano et al. ICLR 2021 | Input-gradient mask regulariser for medical images. |
| CORAL: "Do Medical VLMs Actually See? ..." (Zafar et al.), arXiv 2607.03647 (Jul 2026) | Preprint, no venue | **Closest competitor.** Hard-negative image-swap contrastive objective on Qwen2.5-VL-7B LoRA. Reduces the visual hallucination rate by 8 points, but its visual-reliance gain is not significant and image sensitivity got worse. It needs **no masks**, which is where MedScope differs. |
| "Seeing Is Not Believing: Counterfactual Lesion Erasure Teaches a Small Medical VLM Agent ..." arXiv 2611.13006 | Preprint (Nov 2026) | This appears to be MedScope's own preprint or a very close neighbour. Check for overlap. |
| "Learning To Focus: Anatomy-Guided Attention Regularization for Medical Image Classification", arXiv 2607.10851 | Preprint | Mask-guided attention regularisation for medical classifiers. A concurrent signal that this direction is active. |

---

## 2. Evidence ledger

Abbreviations: XIL = explanatory interactive learning; EPG = energy-based pointing game; OOD = out of distribution. Supervision column: masks, boxes, gaze, pairs (counterfactual pairs), none.

### 2a. Explanation and attention supervision (classifiers and classic VQA)

| # | Title | First author et al. | Venue, year | Mechanism | Supervision | Key result | Robustness to spurious/background cues? How measured | Relevance to MedScope | URL |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Right for the Right Reasons: Training Differentiable Models by Constraining their Explanations | Ross et al. | IJCAI 2017 † | Penalises the input gradient of log-probabilities inside an "irrelevant" mask | masks (of irrelevant regions) | Removes decoy reliance on Decoy-MNIST and similar data; finds alternative decision rules iteratively | Yes. Accuracy on test sets where the decoy is absent or swapped | Founding template for a mask loss. Input gradients are noisy in large transformer VLMs. | https://arxiv.org/abs/1703.03717 |
| 2 | Tell Me Where to Look: Guided Attention Inference Network (GAIN) | Li et al. | CVPR 2018 † | Attention mining: erase the attended region and penalise the class score that remains. GAIN_ext adds pixel-mask supervision of attention. | none / masks | Better weakly supervised segmentation. Mask supervision fixes the boat-water context bias. | Partly. Biased test split (boats without water) | Its "erase what you attend and the score must drop" is a training-time version of ESG. MedScope can apply it with *true* lesion masks and real erased views, not self-generated ones. | https://arxiv.org/abs/1802.10171 |
| 3 | Taking a HINT: Leveraging Explanations to Make Vision and Language Models More Grounded | Selvaraju et al. | ICCV 2019 † | Ranking loss aligning Grad-CAM importance of region proposals with human attention | human attention maps | Gains on VQA-CP; better rank correlation with human attention | Yes for language-prior shift (VQA-CP) | Classic VQA grounding loss. See #5 for why its gains may not come from grounding. | https://arxiv.org/abs/1902.03751 |
| 4 | Self-Critical Reasoning for Robust Visual Question Answering | Wu & Mooney | NeurIPS 2019 † | Penalises wrong answers that are more sensitive to the influential region than the correct answer | human explanations (VQA-HAT/VQA-X) | State of the art on VQA-CP at the time | Yes for VQA-CP | An answer-contrastive sensitivity loss, closer to an output-level causal constraint than HINT | https://arxiv.org/abs/1905.09998 |
| 5 | A Negative Case Analysis of Visual Grounding Methods for VQA | Shrestha, Kafle & Kanan | ACL 2020 **V** | Replaces HINT/SCR cues with random or irrelevant regions; proposes a simple regulariser | none | VQA-CP gains persist with **irrelevant** "grounding" cues, so the gains come from regularisation, not grounding | Measured: grounding metrics vs accuracy | **Key caution.** A grounding loss can raise robustness metrics without grounding, and vice versa. MedScope must report a reliance metric alongside ESG. | https://aclanthology.org/2020.acl-main.727/ |
| 6 | Interpretations are Useful: Penalizing Explanations to Align Neural Networks with Prior Knowledge (CDEP) | Rieger et al. | ICML 2020 † | Penalises contextual-decomposition importance of known-spurious patches | masks of spurious features | ISIC skin lesions: removes reliance on coloured patches; better F1 on the subset without patches | Yes. Subgroup without the artefact | Medical precedent for mask-penalised explanations | https://arxiv.org/abs/1909.13584 |
| 7 | Learning What Makes a Difference from Counterfactual Examples and Gradient Supervision | Teney et al. | ECCV 2020 † | Aligns the input gradient with the vector between members of a minimally different counterfactual pair | pairs (no masks) | Better OOD generalisation on VQA-CP, NLI and MNIST variants with a few pairs | Yes. OOD splits | **Most direct analogue.** MedScope has (original, erased) and (original, control) pairs plus masks, so its gradient supervision can be localised. | https://arxiv.org/abs/2004.09034 |
| 8 | Counterfactual Samples Synthesizing for Robust VQA (CSS) | Chen et al. | CVPR 2020 † | Masks critical objects found by attribution and assigns them a changed answer; also masks question words | none (attribution-chosen) | Large gains on VQA-CP v2 | Yes. VQA-CP | Image-side CSS is MedScope's counterfactual SFT on erased views, which already works and saturates. | https://arxiv.org/abs/2003.06576 |
| 9 | Saliency is a Possible Red Herring When Diagnosing Poor Generalization | Viviano et al. | ICLR 2021 **V** | Mask-based saliency regularisation (ActDiff, GradMask-type) on synthetic and medical (chest X-ray) data | masks | Saliency can be pushed onto the right region **without** better generalisation; it also misleads diagnosis of the failure | Measured on a held-out shifted domain | **Key caution.** Attention can change while the output does not. Supports evaluating reliance by intervention, not by saliency. | https://iclr.cc/virtual/2021/poster/3280 |
| 10 | Towards Robust Classification Model by Counterfactual and Invariant Data Generation | Chang, Adam & Goldenberg | CVPR 2021 † | Generates counterfactual images (causal region removed by inpainting, label changed) and invariant ones (background changed, label kept) | saliency/human masks | Better robustness under background shift | Yes. Background-shift benchmarks | Exactly MedScope's erased (counterfactual) and control (invariant) design, but for classifiers and as data augmentation only | https://openaccess.thecvf.com/content/CVPR2021/html/Chang_Towards_Robust_Classification_Model_by_Counterfactual_and_Invariant_Data_Generation_CVPR_2021_paper.html |
| 11 | On Guiding Visual Attention with Language Specification (GALS) | Petryk et al. | CVPR 2022 † | Uses CLIP text-specified saliency as an RRR-style target | none (text) | Better worst-group accuracy on Waterbirds and similar | Yes. Worst-group accuracy | Masks could come from text when masks are missing; MedScope has real masks. | https://arxiv.org/abs/2202.08926 |
| 12 | Reducing Reliance on Spurious Features in Medical Image Classification with Spatial Specificity | Saab et al. | MLHC 2022 (PMLR 182) **V** | Spatially specific supervision (segmentation-style training) instead of image-level labels | masks | Less reliance on spurious features (e.g., chest drains in pneumothorax) | Yes. Spurious-feature subgroups | Mask supervision helps a detector but does not guarantee causal locality: MedScope's DeepLabV3 still fires on 19-29% of erased lesions. | https://proceedings.mlr.press/v182/saab22a.html |
| 13 | Follow My Eye: Using Gaze to Supervise Computer-Aided Diagnosis | Wang et al. | IEEE TMI 2022 **V** | Gaze-attention consistency loss on a CNN | eye gaze | Better diagnostic accuracy on CXR/knee X-ray | Not explicitly OOD | Mask or gaze attention loss in medicine; changes attention, but OOD reliance is not shown | https://ieeexplore.ieee.org/document/9694633 |
| 14 | A Typology for Exploring the Mitigation of Shortcut Behaviour | Friedrich et al. | Nature Machine Intelligence 2023 † | Unified XIL framework and benchmark (RRR, RBR, CDEP, HINT, counterexamples, ...) | masks | Methods vary widely; simple counterexample augmentation is competitive with explanation losses | Yes. Decoy and confounded test sets | Expect explanation losses to give at most incremental gains over MedScope's counterfactual SFT, which is already a counterexample method. | https://arxiv.org/abs/2203.03668 |
| 15 | Studying How to Efficiently and Effectively Guide Models with Explanations | Rao et al. | ICCV 2023 **V** | "Energy" loss: maximise the fraction of positive attribution inside the box; compares attribution methods and layers | boxes (coarse; few annotations suffice) | Box-guided attributions become more localised (EPG up) at little accuracy cost; boxes work as well as masks; guidance can help under distribution shift (reported on Waterbirds-type data, re-check) | Partly. Localisation metrics and a shifted dataset | A cheap box-level loss that suits MedScope's box output. A good *baseline* attention-supervision arm. | https://openaccess.thecvf.com/content/ICCV2023/papers/Rao_Studying_How_to_Efficiently_and_Effectively_Guide_Models_with_Explanations_ICCV_2023_paper.pdf |
| 16 | Improving Deep Neural Network Generalization and Robustness to Background Bias via Layer-wise Relevance Propagation Optimization (ISNet) | Bassi et al. | Nature Communications 2024 **V** | Penalises LRP relevance outside a foreground (lung) mask during training | masks | Better generalisation to external datasets when background bias exists (COVID-19 CXR, synthetic bias) than standard training and other XIL methods | **Yes. External or cross-dataset tests** | Strongest medical evidence that mask-based relevance loss transfers. Its masks remove *background*, whereas MedScope's shortcut may be *peri-lesional context*. | https://www.nature.com/articles/s41467-023-44371-z |
| 17 | Right for the Wrong Reason: Can Interpretable ML Techniques Detect Spurious Correlations? | Sun et al. | MICCAI 2023 **V** | Evaluates post-hoc and inherently interpretable explanations at detecting injected spurious artefacts in CXR | masks of artefacts | SHAP and inherently interpretable Attri-Net detect shortcuts best; Grad-CAM-type methods are weaker | Evaluation only | Choose attributions carefully if any explanation loss or metric is used. | https://doi.org/10.1007/978-3-031-43895-0_40 |
| 18 | Inducing Causal Structure for Interpretable Neural Networks (Interchange Intervention Training, IIT) | Geiger et al. | ICML 2022 † | Swaps internal activations between two inputs and trains the network so its output matches what a causal model predicts | causal model + pairs | Networks align with a high-level causal model and generalise better | Yes. Structural generalisation | **Formal basis for Framework 1.** MedScope's (original, erased, control) triplets and lesion masks specify the causal model ("presence is determined by tokens inside M"). | https://proceedings.mlr.press/v162/geiger22a.html |

### 2b. Do saliency maps localise lesions? (medical evaluation)

| # | Title | First author et al. | Venue, year | Mechanism | Supervision | Key result | Robustness / measurement | Relevance | URL |
|---|---|---|---|---|---|---|---|---|---|
| 19 | Benchmarking Saliency Methods for Chest X-ray Interpretation | Saporta et al. | Nature Machine Intelligence 2022 † | Compares saliency maps with radiologist segmentations | masks (eval) | Saliency localisation is below radiologist level, worst for small or diffuse findings | Localisation only | Attention-based grounding metrics are unreliable for small lesions, so prefer interventional metrics. | https://doi.org/10.1038/s42256-022-00536-x |
| 20 | AI for Radiographic COVID-19 Detection Selects Shortcuts over Signal | DeGrave et al. | Nature Machine Intelligence 2021 † | Saliency plus GAN-generated counterfactuals to audit shortcuts | none | Models relied on text markers and borders; external performance collapsed | Yes. External sets and counterfactual audits | Generative counterfactual auditing is the ancestor of the erased-view protocol. | https://doi.org/10.1038/s42256-021-00338-7 |

### 2c. Grounded medical VLMs and grounded report generation

| # | Title | First author et al. | Venue, year | Mechanism | Supervision | Key result | Robustness / measurement | Relevance | URL |
|---|---|---|---|---|---|---|---|---|---|
| 21 | Making the Most of Text Semantics to Improve Biomedical Vision-Language Processing (BioViL; MS-CXR) | Boecking et al. | ECCV 2022 † | CXR text-image pretraining; introduces phrase-grounding benchmark MS-CXR | boxes (eval) | Better zero-shot phrase grounding | Localisation (CNR, mIoU) | Grounding measured as localisation, not reliance | https://arxiv.org/abs/2204.09817 |
| 22 | Interactive and Explainable Region-guided Radiology Report Generation (RGRG) | Tanida et al. | CVPR 2023 † | Detects anatomical regions, selects salient ones and generates sentences per region | boxes (anatomy) | Competitive report generation; each sentence is tied to a region | Not tested for reliance | Shows "localise then describe": the text is a function of the region by construction. | https://openaccess.thecvf.com/content/CVPR2023/html/Tanida_Interactive_and_Explainable_Region-Guided_Radiology_Report_Generation_CVPR_2023_paper.html |
| 23 | A Refer-and-Ground Multimodal LLM for Biomedicine (BiRD; Med-GRIT-270k) | Huang et al. | MICCAI 2024 **V** | Instruction tuning on referring and grounding tasks across modalities | boxes | Grounding and referring ability across 8 modalities | Box accuracy only | Same output format as MedScope (claim + box); no reliance test | https://papers.miccai.org/miccai-2024/030-Paper1279.html |
| 24 | ChEX: Interactive Localization and Region Description in Chest X-rays | Müller et al. | ECCV 2024 **V** | Text- or box-prompted localisation and region description in one model | boxes | Competitive on localisation and region-description tasks | Box accuracy | Region-prompted description is a "verify this region" primitive. | https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/03114.pdf |
| 25 | Interpretable Bilingual Multimodal LLM for Diverse Biomedical Tasks (MedRegA) | Wang et al. | ICLR 2025 **V** | Region-centric MLLM; Region-Text dataset; region-aligned evaluation; answers with boxes | boxes | Region-aware tasks across 8 modalities; bilingual; better interpretability | Box metrics only, no counterfactual reliance | Nearest medical box-answering VLM. MedScope's counterfactual test is what it lacks. | https://iclr.cc/virtual/2025/poster/32076 |
| 26 | GEMeX: A Large-Scale, Groundable and Explainable Medical VQA Benchmark for Chest X-ray Diagnosis | Liu et al. | ICCV 2025 **V** | VQA with a textual rationale and visual grounding (boxes) per answer; fine-tuning baselines | boxes + reasons | Fine-tuning on grounded explanations improves LVLMs on the benchmark | Grounding IoU and answer accuracy; no erasure test | Possible external data for grounded CXR answers; its metric does not test necessity. | https://openaccess.thecvf.com/content/ICCV2025/html/Liu_GEMeX_A_Large-Scale_Groundable_and_Explainable_Medical_VQA_Benchmark_for_ICCV_2025_paper.html |
| 27 | MedGround-R1: Medical Image Grounding via Spatial-Semantic Rewarded GRPO | Xu et al. | MICCAI 2025 **V** | GRPO with spatial and semantic rewards; "Chain-of-Box" reasoning template; Qwen2.5-VL | boxes (reward) | State of the art on MS-CXR, ChestX-ray8, M3D-RefSeg | Grounding accuracy only | RL with box rewards improves localisation. MedScope's GRPO failure shows box reward alone does not tie the claim to evidence. | https://papers.miccai.org/miccai-2025/0542-Paper1222.html |
| 28 | MedVLM-R1: Incentivizing Medical Reasoning Capability of VLMs via RL | Pan et al. | MICCAI 2025 **V** | GRPO with format and accuracy rewards on Qwen2-VL-2B | none (answer labels) | Better OOD accuracy across modalities with little data | OOD modality accuracy, not visual reliance | Outcome-only RL. Matches MedScope's negative GRPO result: reward on answers does not force evidence use. | https://papers.miccai.org/miccai-2025/0553-Paper3267.html |
| 29 | A Foundation Model for Joint Segmentation, Detection and Recognition of Biomedical Objects across Nine Modalities (BiomedParse) | Zhao et al. | Nature Methods 2025 **V** (online Nov 2024) | Text-prompted segmentation with object recognition; detects invalid prompts (object not present) | masks | Strong cross-modality segmentation; can reject prompts for objects that are absent | Absent-object rejection is measured | A text-conditioned segmenter with an explicit "absent" decision. A stronger verifier candidate than DeepLabV3. | https://microsoft.github.io/BiomedParse |
| 30 | Eliminating Language Bias for Medical VQA with Counterfactual Contrastive Training (DeCoCT) | Wan et al. | MICCAI 2025 **V** | Key Region Capture Module trained with counterfactual strategies, plus counterfactual contrastive loss; new VQA-RAD-CP split | none (counterfactuals) | Reduces language bias; state of the art on VQA-RAD and SLAKE (per reviews) | Yes. Changing-prior split (VQA-RAD-CP) | Medical VQA-CP analogue. Addresses *language* priors, not *visual-context* priors as in ESG. | https://papers.miccai.org/miccai-2025/0283-Paper2827.html |
| 31 | Worse than Random? An Embarrassingly Simple Probing Evaluation of LMMs in Medical VQA (ProbMed) | Yan et al. | Findings of ACL 2025 **V** | Paired adversarial questions (hallucinated attributes or findings) | none | Top LMMs fall below random on adversarial presence probes | Yes. Adversarial pair accuracy | Text-side counterpart to ESG. MedScope's image-side counterfactuals are stronger. | https://aclanthology.org/2025.findings-acl.981 |
| 32 | Your other Left! VLMs Fail to Identify Relative Positions in Medical Images (MIRP) | Wolf et al. | MICCAI 2025 **V** | Benchmark with rotated or flipped CT slices so anatomical priors cannot be used | none | VLMs rely on memorised anatomy, not the image; visual markers help only a little | Yes. Prior-breaking transforms | Further evidence that medical VLMs answer from priors. | https://papers.miccai.org/miccai-2025/paper/0530_paper.pdf |

### 2d. General VLMs: look-then-answer, region-contrastive inference and image-conditional preferences

| # | Title | First author et al. | Venue, year | Mechanism | Supervision | Key result | Robustness / measurement | Relevance | URL |
|---|---|---|---|---|---|---|---|---|---|
| 33 | V*: Guided Visual Search as a Core Mechanism in Multimodal LLMs | Wu & Xie | CVPR 2024 † | LLM-guided search for target regions before answering | boxes (training of search) | Large gains on high-resolution detail benchmark (V*Bench) | Not a spurious-cue test | Analogue of MedScope's zoom tool | https://arxiv.org/abs/2312.14135 |
| 34 | Visual CoT: Advancing MLLMs with a Comprehensive Dataset and Benchmark for Chain-of-Thought Reasoning | Shao et al. | NeurIPS 2024 (D&B) **V** | Two-turn pipeline: predict the key-region box, crop it, then answer | boxes | Better performance on detail-dependent VQA | Not a spurious-cue test | Localisation before answer, with box supervision on the intermediate step | https://proceedings.neurips.cc/paper_files/paper/2024/hash/0ff38d72a2e0aa6dbe42de83a17b2223-Abstract.html |
| 35 | MLLMs Know Where to Look: Training-free Perception of Small Visual Details (ViCrop) | Zhang et al. | ICLR 2025 **V** | Shows MLLM attention localises correctly even when answers are wrong; crops attended region | none | Training-free gains on small-detail VQA | n/a | **Attention ≠ answer.** Correct localisation does not mean the answer depends on it, which is the mirror image of MedScope's failure. | https://proceedings.iclr.cc/paper_files/paper/2025/hash/aaa0ac4253da75faf9b0dc0dda062612-Abstract-Conference.html |
| 36 | Contrastive Region Guidance: Improving Grounding in VLMs without Training (CRG) | Wan et al. | ECCV 2024 **V** | Contrasts output logits with vs without the relevant region blacked out (classifier-free-guidance style) | boxes (given or from a detector) | Gains on region-grounded VQA and referring tasks | Measures sensitivity to the region | **Inference-time version of the ESG estimand.** The box-ablation logit difference can gate claims (Framework 2). | https://eccv2024.ecva.net/virtual/2024/poster/754 |
| 37 | DeepEyes: Incentivizing "Thinking with Images" via RL | Zheng et al. | ICLR 2026 **V** | RL in which the model calls a crop/zoom tool inside its reasoning; tool-use-oriented rewards | none (outcome + tool reward) | Better high-resolution perception and grounding; fewer hallucinations | Hallucination benchmarks | Same agent design as MedScope (zoom tool). Outcome RL did not fix ESG in MedScope. | https://iclr.cc/virtual/2026/poster/10006639 |
| 38 | Grounded Reinforcement Learning for Visual Reasoning (ViGoRL) | Sarch et al. | NeurIPS 2025 **V** | Each reasoning step is anchored to an image coordinate; multi-turn zoom; MCTS warm-start + RL | none (outcome); grounded traces | Better spatial reasoning, visual search and web-grounding; grounding accuracy of steps measured | Grounding of reasoning steps | Point-anchored reasoning makes evidence explicit. Whether the answer depends on it is not tested. | https://neurips.cc/virtual/2025/poster/120218 |
| 39 | mDPO: Conditional Preference Optimization for Multimodal LLMs | Wang et al. | EMNLP 2024 **V** | Shows standard multimodal DPO can ignore the image ("unconditional preference"). Adds an image-conditional term: same answer, corrupted image as rejected, plus a reward anchor. | none (corrupted images) | Fewer hallucinations than DPO across benchmarks | Hallucination benchmarks | **Explains why text-only DPO can fail for MedScope.** MedScope's erased views make an exact image-conditional preference. | https://aclanthology.org/2024.emnlp-main.460/ |
| 40 | LPOI: Listwise Preference Optimization for VLMs | Pesaran zadeh et al. | ACL 2025 **V** | Masks a detected object at interpolated ratios; listwise ranking so P(mention) increases with object visibility; + DPO + anchor | none (detector masks) | Lower hallucination than DPO and mDPO (e.g., Object HalBench CHAIRs 24.3 vs 30.7 mDPO, LLaVA-1.5-7B) | Hallucination benchmarks | **Closest training method to graded lesion erasure.** MedScope has true masks, real inpainting and a matched control (Framework 5). | https://aclanthology.org/2025.acl-long.1302/ |
| 41 | CHiP: Cross-modal Hierarchical DPO for MLLMs | Fu et al. | ICLR 2025 **V** | Adds visual preference optimisation (image pairs) to text preference levels | none | Reduces hallucination versus DPO | Hallucination benchmarks | Another image-side preference variant | https://proceedings.iclr.cc/paper_files/paper/2025/hash/e1c73e9595126794186536cfbbed012f-Abstract-Conference.html |
| 42 | Mitigating Object Hallucinations in LVLMs through Visual Contrastive Decoding (VCD) | Leng et al. | CVPR 2024 † | Contrasts logits under the original vs a noise-distorted image at decoding | none | Fewer object hallucinations (POPE etc.) | Presence-probe accuracy | Global-distortion contrast. CRG (#36) is the region-specific version, which MedScope needs. | https://arxiv.org/abs/2311.16922 |
| 43 | Evaluating Object Hallucination in Large Vision-Language Models (POPE) | Li et al. | EMNLP 2023 † | Yes/no presence probes with random, popular and adversarial (co-occurring) negatives | none | LVLMs hallucinate co-occurring objects | Presence probes | MedScope's presence questions are POPE-like; ESG is the counterfactual upgrade. | https://arxiv.org/abs/2305.10355 |

### 2e. Measuring whether VLM answers depend on the right region (mechanistic / causal)

| # | Title | First author et al. | Venue, year | Mechanism | Supervision | Key result | Robustness / measurement | Relevance | URL |
|---|---|---|---|---|---|---|---|---|---|
| 44 | Towards Interpreting Visual Information Processing in VLMs | Neo et al. | ICLR 2025 **V** | Ablates object-specific visual tokens in LLaVA; logit lens; attention knockout | object masks/boxes | Ablating object-region tokens strongly reduces object identification; object info is localised in the corresponding tokens and extracted in middle-late layers | Interventional (token ablation) | **Ready-made protocol for a lesion-token reliance metric** and for finding which layers to target | https://proceedings.iclr.cc/paper_files/paper/2025/hash/900fb3439e4968df79a6f2bfedec49cd-Abstract-Conference.html |
| 45 | What Do VLMs NOTICE? A Mechanistic Interpretability Pipeline for Noise-free Text-Image Corruption and Evaluation | Golovanevsky et al. | NAACL 2025 **V** | Semantic minimal-pair image corruption (no Gaussian noise) + activation patching to find important heads | pairs | Identifies the attention heads that move image info to the answer in BLIP/LLaVA | Interventional (patching) | Erased/original pairs are natural "noise-free corruptions" for patching. | https://aclanthology.org/2025.naacl-long.571 |
| 46 | Cross-modal Information Flow in Multimodal LLMs | Zhang et al. | CVPR 2025 **V** | Attention knockout between image, question and answer positions across layers | none | Two-stage flow: general image info to question tokens in lower layers, then question-relevant region info in middle layers, then to the answer | Interventional | Tells where to intervene (middle layers) in Framework 1 | https://openaccess.thecvf.com/content/CVPR2025/papers/Zhang_Cross-modal_Information_Flow_in_Multimodal_Large_Language_Models_CVPR_2025_paper.pdf |
| 47 | Interpreting and Editing Vision-Language Representations to Mitigate Hallucinations | Jiang et al. | ICLR 2025 † | Logit lens on image tokens to find object presence; projects out hallucinated-object directions (knowledge erasure) | none | Localises objects and reduces hallucinations by representation editing | Hallucination benchmarks | Representation-level "presence" read-out per token; could be a cheap reliance probe | https://arxiv.org/abs/2410.02762 |

Total: 47 peer-reviewed entries (30 **V**, 17 †).

---

## 3. Which mechanisms change *what the model attends to* vs only *its outputs*?

**(a) Output-only mechanisms.** These change P(answer | image) without constraining which image evidence produces it.
- Counterfactual SFT or augmentation: CSS (#8), counterexamples in the Friedrich typology (#14), Chang (#10), and MedScope's own SFT.
- Text-side DPO; outcome-reward RL (MedVLM-R1 #28, DeepEyes #37); decision-threshold policies.
- Evidence they do not fix reliance:
  - mDPO (#39) shows standard multimodal DPO can optimise preferences that do not depend on the image at all.
  - Shrestha (#5) shows "grounding" losses improve VQA-CP even with irrelevant regions, so the gains were output regularisation.
  - In the CORAL preprint (watch list), the hard-negative objective reduced hallucination rate but did not significantly raise visual reliance and worsened image sensitivity.
  - MedScope's own eight failures are consistent: every one acts on outputs or on an external verifier.

**(b) Attention or attribution mechanisms.** These change where the attribution mass lies: RRR (#1), GAIN_ext (#2), HINT (#3), CDEP (#6), GALS (#11), gaze (#13), energy loss (#15), ISNet (#16).
- Evidence they move attributions: EPG and rank correlation go up (#15, #3, #13).
- Evidence that this changes robust behaviour is **mixed**:
  - Positive: ISNet (#16) on external CXR with background bias; CDEP (#6) on ISIC patches.
  - Negative: Viviano (#9) shows saliency can be aligned with no generalisation gain; Shrestha (#5) shows the opposite dissociation; Saporta (#19) and Sun (#17) show attribution maps are unreliable localisers, especially for small lesions.
  - ViCrop (#35) shows MLLM attention can already be on the right region while the answer is wrong. Attention is neither necessary nor sufficient evidence of reliance.

**(c) Interventional and causal mechanisms.** These change what the output *depends on*:
- Teney's gradient supervision on counterfactual pairs (#7);
- GAIN's attention mining (erase the attended region, require the score to drop; #2);
- IIT (#18), which trains the network so that swapping internal states between inputs changes outputs as a causal model says;
- image-conditional and listwise-masked preference (mDPO #39, LPOI #40), which make the likelihood depend on the image or on object visibility;
- at inference, CRG (#36), which makes the output depend on the difference made by removing a region.

These mechanisms constrain *output sensitivity to a specific intervention*, which is exactly what ESG measures. The best-supported reading of the literature is that **you get the reliance you train for**: outputs if you train outputs, attributions if you train attributions, interventional sensitivity if you train interventional sensitivity.

**(d) Measurement.** Token ablation and attention knockout (Neo #44, Zhang #46) and minimal-pair activation patching (Golovanevsky #45) are the accepted ways to show *dependence* on a region in a VLM. None of the grounded medical VLMs (#23-#27) or the watch-listed MAIRA-2 and RadVLM reports such a test. They report box IoU or grounding accuracy only.

---

## 4. Gaps MedScope could own

MedScope has pixel masks for every training lesion, real erased views, matched control edits and lesion-free images.

1. **No grounded medical VLM tests reliance.** MedRegA, BiRD, ChEX, GEMeX, MedGround-R1 and MAIRA-2 judge grounding by box overlap. None asks whether the claim survives when the boxed evidence is removed. MedScope's ESG with a matched control is the first paired interventional grounding metric for box-answering medical VLMs. Pair it with a token-level reliance ratio (Neo-style ablation inside the mask vs the matched control region) to separate "does not look" from "looks but uses context".
2. **No method trains medical VLMs on interventional constraints that use true masks.**
   - Teney (#7) uses pairs without masks.
   - LPOI (#40) uses detector masks on natural images and no control anchor.
   - mDPO (#39) uses generic corruptions.
   - IIT (#18) has never been applied to VLM grounding.
   - ISNet and CDEP use masks but act on attributions in CNN classifiers.

   A loss that requires the presence decision to *change* under lesion-token intervention and *not change* under control-token intervention is unoccupied ground.
3. **Context versus lesion is untested.** Medical shortcut work (ISNet, CDEP, Saab) treats the spurious cue as *background*. MedScope's evidence suggests the residual cue is **peri-lesional context**: the segmenter fires on erased lesions, and frontier VLMs claim 41-62% of erased lesions. No paper separates "lesion pixels necessary" from "context sufficient" with masks.
4. **Erasure leakage is uncontrolled.** The 19-29% segmenter firing on erased lesions is either context reliance or residual lesion signal. Nobody reports a leakage-stratified counterfactual metric. Reporting ESG by an independent leakage score (e.g., a BiomedParse or segmenter probability inside the erased region) is a methodological contribution and protects against an unbeatable ceiling.
5. **Claim–box causal coupling is missing.** Box-answering VLMs emit a box, but no work enforces that the *claim* is a function of the *boxed content*. CRG (#36) does this only at inference, on natural images, with external boxes.

---

## 5. Candidate frameworks

Compute assumptions: one A100-80GB, bf16, LoRA on a 4B VLM. "SFT unit" means MedScope's current counterfactual-SFT run time. Visual tokens are computed once per view and reused for token swaps.

### Framework 1 (recommended core): Lesion-Interchange Intervention Training (LIIT)

**Mechanism.** Interchange intervention training at the visual-token level, plus optionally at one middle LLM layer, using masks and the paired views. For each lesion case with mask M (dilated by k patches), take the original x, the erased view x_e and the control-edit view x_c with control region C. Let ℓ = log-odds of "present", or of the box-claim token. Losses:
- **Necessity:** build x ⊕_M e by putting erased-view tokens into the patches covering M. Require ℓ(x) - ℓ(x ⊕_M e) ≥ δ (hinge), with the target label "absent/refer".
- **Control invariance:** build x ⊕_C c. Require |ℓ(x) - ℓ(x ⊕_C c)| ≤ ε. This is the training-time mirror of ESG's control term.
- **Graded necessity:** swap random subsets of M's tokens (25/50/75%) and require ℓ to fall monotonically (listwise, as in LPOI).
- **Sufficiency (low weight):** keep M plus a margin and replace context tokens with tokens from a lesion-free image of the same modality. Require ℓ to stay "present". This penalises context-only claims.
- **Middle-layer variant:** patch hidden states at M positions from the erased-view run (from Zhang #46 and Neo #44, the middle layers are where region information reaches the answer).
- **Anti-artefact control:** also swap in tokens from *other healthy patches or images*, so the model cannot learn "swapped token = absent" from a splice artefact.

Keep the existing counterfactual SFT loss. LIIT is additive.

**Closest work and difference.**
- Teney ECCV 2020 (#7): gradient alignment with pair differences, no masks, no VLM.
- IIT (#18): activation swaps against a causal model, never used for visual grounding.
- LPOI (#40): masked-object listwise preference from detector masks, no control anchor, natural images.
- GAIN (#2): self-erasure of the attended region, CNN classifiers.
- CORAL (preprint): whole-image hard-negative swap, no masks.

LIIT is the first to (i) train the presence claim of a VLM to be causally mediated by mask-defined lesion tokens, (ii) use a matched-control invariance term that is the training analogue of ESG, and (iii) separate lesion necessity from context sufficiency.

**Falsifiable predictions.**
- P1: On held-out hospitals, ESG(LIIT) - ESG(counterfactual SFT) ≥ +5 points (pre-register; 3 seeds; bootstrap CI excludes 0).
- P2: The token-reliance ratio R = Δℓ(ablate M tokens) / Δℓ(ablate matched C tokens) rises by ≥ 2× over SFT on *test* cases, which the training loss never saw.
- P3: The context-only claim rate falls (lesion tokens replaced, context kept).
- **Decision rule:**
  - If P2 holds but P1 fails, the model now relies on lesion tokens but erased test images still contain lesion signal. That points to erasure leakage, not to the model. Check by stratifying ESG on the leakage score (Gap 4).
  - If P2 fails, interventional training did not transfer and the framework is refuted.
- Accuracy on real lesions (sensitivity) must not drop more than 2 points. Otherwise the gain is just more abstention.

**Compute.** Each step needs one vision-encoder pass per view (already done for SFT) plus 3-4 extra LLM forward passes with swapped tokens, about 2.5-3.5× SFT units. Middle-layer patching adds one cached forward pass. This fits in 80 GB with gradient checkpointing at batch 4-8. If the current SFT takes about 6-10 GPU-hours, LIIT is about 20-35 GPU-hours per seed, or about 4 days for 3 seeds plus ablations.

### Framework 2 (inference-time partner, training-free): Self-Ablation Evidence Gate (SAEG)

**Mechanism.** When the agent claims a finding with box B, compute the CRG-style difference Δ = ℓ(x) - ℓ(x with B inpainted or blacked out, or B's tokens swapped with tokens from a healthy reference). Also compute Δ_ctrl for a matched random box. The claim stands only if Δ - Δ_ctrl > τ; otherwise the agent answers "refer". τ is calibrated on validation lesion-free and erased views.

**Closest work.** CRG (#36), which uses external boxes and natural images to improve grounding, not to reject claims; VCD (#42), which uses global noise. The difference: the model's *own* box, a matched-control subtraction, and use as a claim-rejection test.

**Prediction.** On erased views where the claim is driven by context, Δ ≈ Δ_ctrl, so SAEG converts claims to refer and ESG rises. Pre-register a gain of +5 points at sensitivity loss ≤ 3 points. **Falsifier:** if Δ on erased-view claims has a distribution similar to Δ on true-lesion claims (AUROC < 0.65), the model's claims are box-local even on erased views. That means leakage, or a model that "sees" residual lesion, and SAEG cannot help.

SAEG is cheap. Combined with LIIT it is a strong pair: LIIT makes Δ meaningful, and SAEG uses it.

**Compute.** No training; 2-3 extra forward passes per claim. Evaluation of the full benchmark is about 2-3× current inference time, only a few GPU-hours.

### Framework 3 (necessary baseline / negative control): Mask-Energy Relevance Alignment in the LLM

**Mechanism.** Rao's energy loss (#15) or ISNet-style relevance penalty (#16). Take attention rollout or gradient×input from the claim token to the visual tokens. Maximise the fraction of positive relevance inside M on lesion images; on erased views, penalise relevance concentrated at the erased location when the model says "present".

**Closest work.** Energy loss, ISNet, HINT. The new element is applying it to LLM-side relevance in a box-answering VLM.

**Prediction.** Following Viviano (#9) and Shrestha (#5), *we predict EPG within masks rises (≥ +15 points) while ESG gains are below +2 points.* If ESG rises as much as with LIIT, the hypothesis that attention-level supervision is insufficient is refuted. Either way the result is publishable as the contrast that motivates LIIT.

**Compute.** About 1.5-2× SFT units (one backward pass for relevance; attention rollout is cheaper).

### Framework 4 (diagnostic that targets the fix): Causal-Mediation Map of Erased-Lesion Claims, then Targeted LoRA

**Mechanism.** Run activation patching (#45) between erased and original views across layers, positions (M tokens, context tokens, question tokens) and heads. This finds where "present" on an erased view is produced. Three possible outcomes:
- (i) context tokens around M;
- (ii) question or prior pathways (text tokens; claims persist with all visual tokens ablated, as in the MIRP and ProbMed findings, #31-#32);
- (iii) residual lesion tokens.

Restrict LIIT, or a simple LoRA, to the mediating layers and heads.

**Closest work.** Neo (#44), Zhang (#46), Golovanevsky (#45), Jiang (#47). None is medical, none uses lesion masks, and none links mediation to a robustness intervention.

**Prediction.** If more than 50% of the erased-claim effect is mediated by non-visual (text/prior) positions, no visual grounding method, including Frameworks 1 and 3, can close ESG. The fix would then be prior suppression, e.g., penalising answer confidence when visual tokens are mean-ablated. This is a clean go/no-go criterion for the whole strand.

**Compute.** Patching sweeps on about 500 cases × layers × 3 position groups take roughly 10-20 GPU-hours. Targeted LoRA is then about 1 SFT unit.

### Framework 5 (preference variant): Graded-Erasure Listwise Preference with Control Anchor (GELP)

**Mechanism.** For each case, render erasure at α ∈ {0, 0.25, 0.5, 0.75, 1} of the lesion mask. A listwise loss makes P(claim) monotone in α. The control edit and lesion-free image act as equality anchors, which mDPO-style anchors prevent from collapsing toward "refer".

**Closest work.** LPOI (#40; detector masks, no control, natural images) and mDPO (#39). The differences are true masks, medical inpainting, a matched control anchor and an ESG-aligned objective.

**Prediction.** ESG rises over DPO and SFT by ≥ +3 points, and the dose–response slope of P(claim) vs α becomes monotone on test cases (Spearman ρ < -0.8). **Falsifier:** a monotone slope in training but not on held-out hospitals means memorisation, consistent with the earlier DPO failure.

**Compute.** Requires 4 extra inpainted views per case, generated offline (inpainting cost depends on the eraser; cache them). Training is about 2× SFT units.

### Recommendation

Make **LIIT (Framework 1) the single method contribution**, with **SAEG (Framework 2)** as its inference-time readout. Use **Framework 4's mediation map** as the go/no-go pre-study, and **Framework 3** as the attention-supervision baseline that the literature predicts will fail on ESG.

The paper's claim would then be: grounding objectives that act on outputs or attributions do not produce evidence dependence; interchange interventions on mask-defined lesion tokens, anchored by a matched control, do. This is measured by ESG and by a token-ablation reliance ratio, stratified by erasure leakage.
