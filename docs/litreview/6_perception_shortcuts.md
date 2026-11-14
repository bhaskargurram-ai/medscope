# Strand 6: Perception limits, vision-encoder adaptation, edit-artifact shortcuts, cross-hospital generalisation

Review date: 2026-11-14. Reviewer: literature-review subagent (read-only; no repository edited).

---

## 1. Search boundary

**Scope.** (a) Perception limits of VLMs (encoder bottleneck, resolution, MMVP-style failures, visual-token pruning), medical image encoders and their transfer, and how to fine-tune vision encoders without collapse. (b) Shortcut learning in medical imaging, hospital/scanner confounds, inpainting/editing artifacts and invariance to them. (c) Domain generalisation of lesion detection across hospitals.

**Inclusion.** Peer-reviewed, 2019-2026 (priority 2022-2026). Venues: Nature-family journals, NEJM AI, Lancet Digital Health, Radiology: AI, Eur Radiol, MedIA, TMI, MICCAI, MIDL, ISBI, NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACCV, TMLR, ACL/EMNLP/EACL (incl. Findings), CHIL, USENIX Security.

**Exclusion.** arXiv-only preprints (listed separately in 2.6 and never used as primary evidence), pre-2019 work (except where flagged as background), non-imaging shortcut papers unless the mechanism transfers.

**Tools and queries (all run 2026-11-14).** WebSearch (standard and extended) and Firecrawl web search. Query formulations included:
- "Hidden in plain sight VLMs overlook their visual representations venue"
- "Prismatic VLMs ... fine-tuning vision backbone hurts"
- "What matters when building vision-language models Idefics2 ... unfreezing vision encoder LoRA stability"
- "Feather the Throttle revisiting visual token pruning ... ICCV 2025"
- "Visual Representation Alignment for Multimodal Large Language Models VIRAL accepted"
- "Mukhoti Fine-tuning can cripple your foundation model LDIFS TMLR"
- "medical multimodal large language model ablation unfreeze vision encoder ..." (extended)
- "medical vision-language models fail fine-grained visual perception benchmark ... MICCAI" (extended)
- "Exploring scalable medical image encoders beyond text supervision RAD-DINO ..." plus site:nature.com check
- "BiomedCLIP ... NEJM AI"; "PubMedCLIP ... EACL Findings"; "MedGemma technical report MedSigLIP peer-reviewed"; "LLaVA-Rad ... Nature Communications"; "REMEDIS Nature Biomedical Engineering"
- "RadEdit stress-testing biomedical vision models ... ECCV 2024"
- "counterfactual data augmentation inpainting shortcut artifact classifier learns inpainting region medical imaging lesion removal" (extended)
- "counterfactual image augmentation diffusion editing spurious correlation mitigation ... editing artifacts" (extended)
- "Masked images are counterfactual samples for robust fine-tuning CVPR 2023"; "Teney ... counterfactual examples and gradient supervision ECCV 2020"; "Rong ... ROAD ICML 2022 information leakage mask"
- "Fast Diffusion-Based Counterfactuals for Shortcut Removal and Generation ECCV 2024"; "MaskMedPaint ... venue"
- "Roschewitz counterfactual contrastive learning ... journal"
- "detection of tampered medical images inpainting ... CT-GAN"; "Ojha universal fake image detectors CVPR 2023"
- "Brown shortcut testing Nature Communications"; "Ong Ly shortcut learning npj Digital Medicine"; "Jiménez-Sánchez detecting shortcuts chest drains ISBI 2023"; "Glocker risk of bias chest radiography foundation models Radiology AI"
- "Thian pneumothorax multicenter external validation Radiology AI"; "Sabottke effect of image resolution Radiology AI"; "Cohen limits of cross-domain generalization MIDL 2020"; "Aubreville MIDOG ... Medical Image Analysis"; "Domain generalization for medical image analysis review Proceedings of the IEEE"
- "mDPO conditional preference optimization EMNLP 2024"
- "Your other Left ... MICCAI 2025"

**Limit reached.** The shared web-search budget for this turn ran out before the last three verification queries ("Mask of truth" venue, PRISM venue, Rueckel 2020 Investigative Radiology). Those items are left out of the main ledger. Venue flags in the ledger:
- **V**: venue confirmed by a search result in this session (publisher, proceedings, PubMed or conference page).
- **K**: well-known paper whose venue comes from the reviewer's prior knowledge with high confidence. It was not re-checked because the budget ran out. Spot-check K items before submission.

**Project's own preprint (context only, not in ledger).** arXiv:2611.13006 (v1, 8 Nov 2026), "Seeing Is Not Believing: Counterfactual Lesion Erasure Teaches a Small Medical Vision-Language Agent to Report Only What the Image Shows", describes MedScope-4B. Its abstract matters here for two reasons.
- It already reports what failed: removal-based DPO gave no fresh-external ESG advantage, a paired-view consistency objective did not beat a matched-compute control, and matching the control edit "was not shown to matter".
- It concludes that the approach "does not improve perception".

v1 reports **0/48** pneumothorax on the fresh external test. The brief says 10/48, presumably a later run. Reconcile the two before writing.

---

## 2. Evidence ledger

Columns: Title | First author et al. | Venue, year [flag] | Finding or method | Key result | Relevance to MedScope | URL

### 2.1 Perception limits of VLMs (encoder bottleneck, resolution, token pruning, language priors)

| # | Title | First author | Venue, year | Finding / method | Key result | Relevance to MedScope | URL |
|---|---|---|---|---|---|---|---|
| 1 | Eyes Wide Shut? Exploring the Visual Shortcomings of Multimodal LLMs | Tong et al. | CVPR 2024 [K] | "CLIP-blind pairs" (images CLIP embeds alike but DINOv2 separates) form the MMVP benchmark. Interleaved Mixture-of-Features adds DINOv2 tokens. | MLLMs, GPT-4V included, fail systematic visual patterns. Errors track CLIP-blindness. Adding SSL (DINOv2) features improves visual grounding. | A contrastive-text encoder can be blind to fine local evidence such as a thin pleural line. Supports adding an image-only SSL medical encoder (RAD-DINO) as a second feature stream or teacher. | https://arxiv.org/abs/2401.06209 |
| 2 | Vision language models are blind | Rahmanzadehgervi et al. | ACCV 2024 [K] | Seven trivially easy low-level visual tasks (line crossings, circle overlap, counting). | State-of-the-art VLMs far below human level on simple geometric perception. | Evidence that low-level perception, not reasoning, limits VLM detection of subtle findings. | https://arxiv.org/abs/2407.06581 |
| 3 | Cambrian-1: A Fully Open, Vision-Centric Exploration of Multimodal LLMs | Tong et al. | NeurIPS 2024 [K] | Vision-centric study of encoders and connectors (CV-Bench, Spatial Vision Aggregator). | Encoder choice dominates vision-centric performance. Unfreezing the encoder helps when there is enough data and a sensible recipe. SSL encoders lag on OCR but help vision-centric tasks. | Unfreezing can help, but only under a good recipe. MedScope's collapse is a recipe failure, not proof that encoder tuning is useless. | https://arxiv.org/abs/2406.16860 |
| 4 | Prismatic VLMs: Investigating the Design Space of Visually-Conditioned Language Models | Karamcheti et al. | ICML 2024 [V] | Controlled ablations of LLaVA-style training choices. | Fine-tuning the vision backbone during VLM training degraded performance, worst on localisation tasks. Fused DINOv2+SigLIP features helped. | The clearest published precedent for observation (2): naive vision-backbone tuning hurts. Also motivates fused SSL+contrastive features. | https://mlanthology.org/icml/2024/karamcheti2024icml-prismatic |
| 5 | What matters when building vision-language models? (Idefics2) | Laurençon et al. | NeurIPS 2024 [V] | Ablations of architecture and training. | Full unfreezing of the unimodal backbones destabilised training. LoRA on the backbones, with the new connector parameters trained fully, kept training stable. | LoRA on the encoder is not enough by itself. The LR and parameter grouping between connector and encoder matter. Matches the collapse at LM-level LR. | https://proceedings.neurips.cc/paper_files/paper/2024/hash/a03037317560b8c5f2fb4b6466d4c439-Abstract.html |
| 6 | Why are Visually-Grounded Language Models Bad at Image Classification? | Zhang et al. | NeurIPS 2024 [K] | Compares VLMs with their own CLIP encoder on classification. | VLMs score far below a linear probe on their own encoder. The information is in the latent space; the cause is training data, and adding classification data fixes much of it. | MedScope's perception gap may sit in the LLM read-out, not the encoder. Test with a linear probe on frozen vision tokens before touching the encoder. | https://arxiv.org/abs/2405.18415 |
| 7 | Are We on the Right Way for Evaluating Large Vision-Language Models? (MMStar) | Chen et al. | NeurIPS 2024 [K] | Audits benchmarks for questions answerable without the image. | Many benchmark items are solvable text-only. Defines metrics for multimodal gain and leakage. | Supplies the metric for MedScope's "question-only" collapse: report blind-answer agreement as a guard metric. | https://arxiv.org/abs/2403.20330 |
| 8 | Mitigating Object Hallucinations in LVLMs through Visual Contrastive Decoding (VCD) | Leng et al. | CVPR 2024 [K] | Contrasts output logits on the real image and on a distorted image. | Reduces object hallucination (POPE) without training. Hallucination is attributed to language priors. | A cheap inference-time baseline: contrast logits on the original and lesion-erased views. Also a diagnostic of how much the image drives the answer. | https://arxiv.org/abs/2311.16922 |
| 9 | An Image is Worth 1/2 Tokens After Layer 2 (FastV) | Chen et al. | ECCV 2024 [K] | Attention-based visual-token pruning after early LLM layers. | Large FLOP savings with small losses on standard benchmarks. Deep layers attend little to image tokens. | Shows how little deep LLM layers use visual tokens. Any token reduction in MedScope's pipeline may delete small-lesion tokens. | https://arxiv.org/abs/2403.06764 |
| 10 | Feather the Throttle: Revisiting Visual Token Pruning for VLM Acceleration | Endo et al. | ICCV 2025 [V] | Analyses what early-layer pruning keeps. | Popular pruning keeps tokens largely from the bottom of the image, because of positional bias in attention. Benchmarks hide this because few need fine localisation. Proposes uniform-sampling-aware pruning. | Upright-CXR pneumothorax is often **apical (top of image)**. A positional bias that under-weights top tokens would selectively hurt it. Cheap diagnostic: vertical-flip test (Sec. 5). | https://mlanthology.org/iccv/2025/endo2025iccv-feather/ |
| 11 | When Do We Not Need Larger Vision Models? (S²) | Shi et al. | ECCV 2024 [K] | Multi-scale feature extraction from a frozen smaller ViT. | A multi-scale small model matches or beats larger ones on MLLM benchmarks with high-resolution detail. | Resolution, not encoder size, may be the lever for thin or subtle findings. Supports zoom/tiling tools. | https://arxiv.org/abs/2403.13043 |
| 12 | Vision Transformers Need Registers | Darcet et al. | ICLR 2024 [K] | Finds high-norm "artifact" tokens in low-information patches of large ViTs. Adds register tokens. | Artifact tokens carry global information and corrupt dense feature maps. Registers fix it. | Inpainted, low-texture regions are exactly where artifact tokens appear. A possible mechanism for "edited region → absent". | https://arxiv.org/abs/2309.16588 |
| 13 | Visual Representation Alignment for Multimodal Large Language Models (VIRAL) | Yoon et al. | ICLR 2026 [V] | Aligns MLLM-internal visual representations with a frozen vision foundation model (e.g. DINOv2) during instruction tuning. | Text-only supervision lets fine visual detail decay in the LLM. Alignment improves vision-centric benchmarks. | Close precedent for anchoring MedScope's visual path to a frozen medical teacher (RAD-DINO) during LoRA. | https://iclr.cc/virtual/2026/10013230 |
| 14 | mDPO: Conditional Preference Optimization for Multimodal LLMs | Wang et al. | EMNLP 2024 [V] | Shows multimodal DPO can optimise preferences while ignoring the image. Adds image-conditional preference pairs (same answer, corrupted image = rejected) and a reward anchor. | Reduces hallucination over standard DPO. | Closest published relative of MedScope's "removal-based DPO". It explains why preference training on text alone does not force image use. | https://aclanthology.org/2024.emnlp-main.460/ |

### 2.2 Medical VLM perception failures and medical encoders

| # | Title | First author | Venue, year | Finding / method | Key result | Relevance | URL |
|---|---|---|---|---|---|---|---|
| 15 | Worse than Random? An Embarrassingly Simple Probing Evaluation of LMMs in Medical VQA (ProbMed) | Yan et al. | Findings of ACL 2025 [V] | Adversarial probing pairs (real versus hallucinated finding or attribute). | Leading general and medical LMMs fall below random on adversarial pairs. Domain-specialised models are no safer. | External baseline for "answers from the question wording". ESG is a stronger, image-grounded form of the same probe. | https://preview.aclanthology.org/setup/2025.findings-acl.981 |
| 16 | Your other Left! Vision-Language Models Fail to Identify Relative Positions in Medical Images | Wolf et al. | MICCAI 2025 [V] | Benchmark of relative-position questions on medical images, with and without visual markers. | VLMs fail and fall back on anatomical priors instead of the image. Markers give limited help. | Shows prior knowledge overriding image evidence in medical VLMs. Same failure family as "say absent if edited". | https://papers.miccai.org/miccai-2025/1027-Paper0530.html |
| 17 | FunBench: Benchmarking Fundus Reading Skills of MLLMs | (MICCAI 2025 authors) | MICCAI 2025 [V] | Hierarchical fundus benchmark. Per its description, includes evaluation modes that separate the vision encoder (probing) from the full MLLM. | MLLMs show deficits in basic fundus reading. | A method template: separate encoder capacity from LLM read-out. MedScope should report both. | https://papers.miccai.org/miccai-2025/paper/2156_paper.pdf |
| 18 | Exploring scalable medical image encoders beyond text supervision (RAD-DINO) | Pérez-García et al. | Nature Machine Intelligence 7:119-130, 2025 [V] | DINOv2-style image-only pretraining on large CXR corpora. | Matches or beats text-supervised biomedical encoders on classification, segmentation and report generation. Scales with data. Captures features that reports do not describe. | The most plausible frozen teacher or extra stream for CXR evidence (pleural line, small findings). Image-only SSL avoids the text-prior bias. | https://www.nature.com/articles/s42256-024-00965-w |
| 19 | A Multimodal Biomedical Foundation Model Trained from Fifteen Million Image-Text Pairs (BiomedCLIP) | Zhang et al. | NEJM AI 2025 [V] | CLIP on PMC-15M covering many modalities. | State of the art on biomedical retrieval, classification and VQA at the time. | A cross-modality (five imaging types) contrastive teacher or probe backbone. Figure-derived, so it may be weaker on raw clinical acquisitions. | https://ai.nejm.org/doi/full/10.1056/AIoa2400640 |
| 20 | Expert-level detection of pathologies from unannotated chest X-ray images via self-supervised learning (CheXzero) | Tiu et al. | Nature Biomedical Engineering 2022 [K] | CLIP-style training on MIMIC-CXR image-report pairs. Zero-shot classification. | Zero-shot performance comparable to radiologists on several CheXpert pathologies. | Report-supervised CXR encoder baseline. Its zero-shot heads give a text-independent second opinion for pneumothorax. | https://www.nature.com/articles/s41551-022-00936-9 |
| 21 | Does CLIP Benefit VQA in the Medical Domain as Much as it Does in the General Domain? (PubMedCLIP) | Eslami et al. | Findings of EACL 2023 [V] | CLIP fine-tuned on ROCO, used as MedVQA encoder. | Improves MedVQA over general CLIP and ImageNet encoders. | Early evidence that domain-adapted encoders matter for MedVQA. A historical baseline. | https://aclanthology.org/2023.findings-eacl.88 |
| 22 | DINOv2: Learning Robust Visual Features without Supervision | Oquab et al. | TMLR 2024 [K] | Large-scale SSL ViT with curated data. | Strong frozen-feature transfer, including dense tasks. | Basis of RAD-DINO and of MMVP-style fixes. Frozen DINOv2 features + linear heads are a robust-transfer baseline. | https://arxiv.org/abs/2304.07193 |
| 23 | Robust and data-efficient generalization of self-supervised machine learning for diagnostic imaging (REMEDIS) | Azizi et al. | Nature Biomedical Engineering 2023 [V] | Large-scale supervised + self-supervised pretraining. Evaluated in-distribution and out-of-distribution across 6 imaging tasks. | Better OOD diagnostic accuracy and much better data efficiency when adapting to new sites. | Supports keeping a strong pretrained encoder close to its initial weights for new-hospital robustness. | https://www.nature.com/articles/s41551-023-01049-7 |
| 24 | A clinically accessible small multimodal radiology model and evaluation metric for chest X-ray findings (LLaVA-Rad) | Zambrano Chaves et al. | Nature Communications 2025 [V] | Small (7B) radiology LMM with a domain-specific CXR image encoder. Staged training. | Beats larger general models on CXR findings generation. | The closest small-model precedent. Shows the value of a domain encoder in a small LMM. | https://www.nature.com/articles/s41467-025-58344-x |
| 25 | Risk of bias in chest radiography deep learning foundation models | Glocker et al. | Radiology: Artificial Intelligence 2023 [V] | Audits a CXR foundation model's embeddings for subgroup information and performance disparities. | Embeddings strongly encode sex and race. Downstream performance disparities appear. | Foundation encoders also encode non-pathology cues (site, scanner, edits). Probing for such cues should be routine. | https://arxiv.org/abs/2209.02965 |

### 2.3 Fine-tuning vision encoders without collapse (robust fine-tuning)

| # | Title | First author | Venue, year | Finding / method | Key result | Relevance | URL |
|---|---|---|---|---|---|---|---|
| 26 | Fine-Tuning can Distort Pretrained Features and Underperform Out-of-Distribution (LP-FT) | Kumar et al. | ICLR 2022 [K] | Theory and experiments: full fine-tuning with a poorly fit head distorts features. Fix: linear-probe first, then fine-tune. | Full fine-tuning gains in-distribution but loses OOD under large shift. LP-FT gets both. | Direct mechanism for observation (2). The connector/LLM is a "bad head" for new visual features, so early large gradients distort the encoder. Train the head first, then the encoder slowly. | https://arxiv.org/abs/2202.10054 |
| 27 | Robust fine-tuning of zero-shot models (WiSE-FT) | Wortsman et al. | CVPR 2022 [K] | Weight-space interpolation between zero-shot and fine-tuned weights. | Large OOD gains at little in-distribution cost on ImageNet shifts. | Interpolate the vision LoRA (or the whole adapter) with zero to recover new-hospital sensitivity. Nearly free. | https://arxiv.org/abs/2109.01903 |
| 28 | Model soups: averaging weights of multiple fine-tuned models improves accuracy without increasing inference time | Wortsman et al. | ICML 2022 [K] | Averages fine-tuned models from different hyperparameters. | Improves accuracy and OOD robustness at no inference cost. | Average LoRA runs from different seeds or LRs (MedScope already has three seeds). | https://arxiv.org/abs/2203.05482 |
| 29 | Finetune like you pretrain (FLYP) | Goyal et al. | CVPR 2023 [K] | Fine-tunes CLIP with its own contrastive loss. | Best in-distribution plus OOD among the fine-tuning methods compared. | Supports aligning the vision-side objective with the pretraining objective (contrastive or SSL) rather than LM-loss-only gradients. | https://arxiv.org/abs/2212.00638 |
| 30 | Surgical Fine-Tuning Improves Adaptation to Distribution Shifts | Lee et al. | ICLR 2023 [K] | Tunes only a subset of blocks. | Input-level shifts (corruptions, acquisition) are best fixed by early layers; output-level shifts by later layers. Matches or beats full fine-tuning. | Hospital/scanner shift is input-level, so tune early encoder blocks. Lesion-concept learning points to middle or late blocks. Gives a principled layer-selection rule. | https://arxiv.org/abs/2210.11466 |
| 31 | Trainable Projected Gradient Method for Robust Fine-tuning (TPGM) | Tian et al. | CVPR 2023 [K] | Learns a per-layer distance constraint from the pretrained weights. | Better OOD than plain fine-tuning and L2-SP. | Per-layer trust regions are an automatic alternative to hand-set layer-wise LRs. | https://arxiv.org/abs/2303.10720 |
| 32 | Fine-tuning can cripple your foundation model; preserving features may be the solution (LDIFS) | Mukhoti et al. | TMLR 2024 (presented ICLR 2025) [V] | Feature-space L2 distance to the original model during fine-tuning. | Reduces "concept forgetting" better than parameter-space regularisers. | Feature anchoring is the right regulariser for a vision LoRA. Measures the encoder drift that preceded the collapse. | https://iclr.cc/virtual/2025/poster/31485 |
| 33 | LoRA Learns Less and Forgets Less | Biderman et al. | TMLR 2024 [K] | Compares LoRA with full fine-tuning. | LoRA underfits the target domain but retains more base behaviour. | Explains "more conservative, not more perceptive" at low LR. Low-rank, low-LR updates mostly shifted the output prior. | https://arxiv.org/abs/2405.09673 |
| 34 | Masked Images Are Counterfactual Samples for Robust Fine-tuning | Xiao et al. | CVPR 2023 [V] | Masks image patches (by class-activation map) as counterfactuals. Distils the frozen pretrained model's features on them during fine-tuning. | Better OOD robustness of fine-tuned CLIP. | The closest published method that combines "masked or edited counterfactuals" with "anchor to the pretrained encoder". MedScope differs in using clinical lesion erasures and a VLM target. | https://arxiv.org/abs/2303.03052 |

### 2.4 Shortcut learning, edit artifacts, counterfactual training

| # | Title | First author | Venue, year | Finding / method | Key result | Relevance | URL |
|---|---|---|---|---|---|---|---|
| 35 | Shortcut learning in deep neural networks | Geirhos et al. | Nature Machine Intelligence 2020 [K] | Conceptual framework and examples. | Models adopt decision rules that work on the i.i.d. test set and fail OOD. | Frames "edited region → absent" as a textbook shortcut. Test OOD on edits that should not change the label. | https://arxiv.org/abs/2004.07780 |
| 36 | AI for radiographic COVID-19 detection selects shortcuts over signal | DeGrave et al. | Nature Machine Intelligence 2021 [K] | Saliency and GAN counterfactual auditing of COVID CXR classifiers. | Models used laterality markers, text and positioning, and failed across sites. | The canonical CXR shortcut paper. Its counterfactual auditing parallels MedScope's benchmark. | https://www.nature.com/articles/s42256-021-00338-7 |
| 37 | Hidden stratification causes clinically meaningful failures in machine learning for medical imaging | Oakden-Rayner et al. | ACM CHIL 2020 [K] | Subgroup analysis. | Pneumothorax classifiers do much worse on cases **without chest drains**, i.e. untreated, clinically important pneumothorax. | Likely relevant to the pneumothorax failure at the new hospital: drain prevalence and protocol differ by site. | https://arxiv.org/abs/1909.12475 |
| 38 | Detecting Shortcuts in Medical Images - A Case Study in Chest X-rays | Jiménez-Sánchez et al. | ISBI 2023 [V] | Annotates chest drains in public pneumothorax data and measures their effect. | Pneumothorax models rely on drains. Performance drops on drain-free positives. | Stratify the 48 external pneumothorax cases by drain presence. If the misses are drain-free, the external loss is a drain shortcut, not a resolution problem. | https://WWW.GITHUB.COM/ameliajimenez/shortcuts-chest-xray |
| 39 | Pneumothorax detection in chest radiographs: optimizing AI system for accuracy and confounding bias reduction using in-image annotations in algorithm training | Rueckel et al. | European Radiology 2021 [V, via reference list] | Training with in-image pneumothorax annotations. | Reduced confounding by thoracic tubes and improved accuracy. | Localised supervision of the pleural line is a documented fix for pneumothorax confounding. | https://doi.org/10.1007/s00330-021-07833-w |
| 40 | A Consistent and Efficient Evaluation Strategy for Attribution Methods (ROAD) | Rong et al. | ICML 2022 [V] | Shows removal-based evaluation leaks class information through the **shape and location of the removal mask**. Proposes noisy linear imputation to stop the leak. | Models can classify from the mask pattern alone. Leak-free imputation gives consistent rankings. | **The central mechanism for observation (3).** When the label depends on where the edit is, the edit becomes a label. MedScope's control edit is placed elsewhere, so "edit at the queried lesion site" is still predictive. | https://proceedings.mlr.press/v162/rong22a.html |
| 41 | A Benchmark for Interpretability Methods in Deep Neural Networks (ROAR) | Hooker et al. | NeurIPS 2019 [K] | Remove-and-retrain evaluation. | Removal creates distribution shift. Without retraining, removal results are confounded by artifacts. | Supports training on erased views, but also warns that retraining can learn the removal signature itself. | https://arxiv.org/abs/1806.10758 |
| 42 | Learning What Makes a Difference from Counterfactual Examples and Gradient Supervision | Teney et al. | ECCV 2020 [V] | Uses minimal counterfactual pairs. Aligns input gradients with the pair difference vector. | Better OOD generalisation on VQA and other tasks than plain augmentation. | Pair-level gradient or feature supervision is the principled form of "learn from erased versus original". MedScope's paired-view consistency is a weaker, output-level version, which may be why it failed. | https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/1165_ECCV_2020_paper.php |
| 43 | Learning the Difference that Makes a Difference with Counterfactually-Augmented Data | Kaushik et al. | ICLR 2020 [K] | Humans minimally edit text to flip labels. | Models trained on such data rely less on spurious features. | Conceptual origin of counterfactual augmentation. Shows the value of label-flipping and label-preserving minimal edits together. | https://arxiv.org/abs/1909.12434 |
| 44 | RadEdit: Stress-Testing Biomedical Vision Models via Diffusion Image Editing | Pérez-García et al. | ECCV 2024 [V] | Diffusion CXR editing with an edit mask and a keep mask to avoid spurious edit correlations. Simulates acquisition, manifestation and population shift. | Biomedical classifiers and segmenters fail on the synthetic shifts. Multi-mask editing reduces edit artifacts outside the target. | The closest medical-editing tool. Its keep-mask idea is how to build **lesion-preserving same-site edits** (Sec. 5, F1). | https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01923.pdf |
| 45 | Fast Diffusion-Based Counterfactuals for Shortcut Removal and Generation (FastDiME) | Weng et al. | ECCV 2024 [V] | Fast diffusion counterfactuals for detecting and removing shortcuts. | Generates counterfactuals that expose shortcut dependence and supports mitigation. | Tooling for generating shortcut-removal counterfactuals at scale. | https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/11674_ECCV_2024_paper.php |
| 46 | Robust image representations with counterfactual contrastive learning | Roschewitz et al. | Medical Image Analysis 2025 [V] (MICCAI DEMI workshop 2024 version) | Causal generative model makes **domain (scanner) counterfactuals**, used as contrastive positives. | Better robustness to acquisition shift on mammography and CXR, especially for under-represented domains. | The most relevant medical DG method. Counterfactual site or scanner positives target new-hospital sensitivity directly. | https://www.sciencedirect.com/science/article/pii/S1361841525002154 |
| 47 | High Fidelity Image Counterfactuals with Probabilistic Causal Models | De Sousa Ribeiro et al. | ICML 2023 [K] | HVAE-based causal counterfactual generation. | High-fidelity, intervention-faithful counterfactuals on medical and other data. | The generator family behind #46. Could make scanner or site counterfactuals for MedScope's training data. | https://arxiv.org/abs/2306.15764 |
| 48 | CT-GAN: Malicious Tampering of 3D Medical Imagery using Deep Learning | Mirsky et al. | USENIX Security 2019 [K] | GAN injection and removal of lung nodules in CT. | Tampered scans fooled radiologists and an AI screening model. | Shows removals can be visually convincing to humans yet carry statistical traces, the regime MedScope's "physician still reads positive" erasures fall outside. | https://arxiv.org/abs/1901.03597 |
| 49 | Towards Universal Fake Image Detectors that Generalize Across Generative Models | Ojha et al. | CVPR 2023 [V] | Linear probe on frozen CLIP features detects generated images. | Generalises across unseen generators. | **Large frozen encoders separate generated or inpainted content from real content almost linearly.** MedScope's vision tower likely "sees" inpainting directly, so the shortcut is cheap to learn. | https://arxiv.org/abs/2302.10174 |
| 50 | Detecting shortcut learning for fair medical AI using shortcut testing | Brown et al. | Nature Communications 2023 [V] | Multitask intervention on how strongly a sensitive attribute is encoded. Measures how performance changes. | Shortcut testing separates shortcut-driven from legitimate attribute effects. | Template for an "edit-attribute shortcut test": vary how strongly edit-presence is encoded and measure the change in ESG. | https://www.nature.com/articles/s41467-023-39902-7 |
| 51 | Shortcut learning in medical AI hinders generalization: method for estimating AI model generalization without external data | Ong Ly et al. | npj Digital Medicine 2024 [V] | Estimates shortcut reliance and generalisation from internal data. | Shortcut reliance predicts external performance drop. | Could forecast new-hospital sensitivity before external testing. | https://www.nature.com/articles/s41746-024-01118-4 |
| 52 | AI recognition of patient race in medical imaging: a modelling study | Gichoya et al. | Lancet Digital Health 2022 [K] | Tests whether models predict race from images. | Race is predictable even from heavily degraded images, by cues humans cannot see. | Imperceptible global cues (here, edit statistics) are readily learned. Human-judged "natural" erasures are no guarantee of artifact-free inputs. | https://doi.org/10.1016/S2589-7500(22)00063-2 |
| 53 | Saliency is a Possible Red Herring When Diagnosing Poor Generalization | Viviano et al. | ICLR 2021 [K] | Mask-supervised saliency regularisers under synthetic and medical confounds. | Saliency alignment does not reliably buy OOD generalisation. | Caution: attention or saliency supervision on lesion masks is not enough by itself. Pair it with invariance. | https://arxiv.org/abs/1910.00199 |
| 54 | Last Layer Re-Training is Sufficient for Robustness to Spurious Correlations (DFR) | Kirichenko et al. | ICLR 2023 [K] | Retrains the last layer on group-balanced data. | Core features are already learned even when the model relies on shortcuts. A small balanced re-fit restores worst-group accuracy. | The shortcut may be removable by re-fitting only the read-out (LLM LoRA) on an artifact-balanced set, with no encoder change. | https://arxiv.org/abs/2204.02937 |

### 2.5 Cross-hospital generalisation of lesion detection

| # | Title | First author | Venue, year | Finding / method | Key result | Relevance | URL |
|---|---|---|---|---|---|---|---|
| 55 | Deep Learning Systems for Pneumothorax Detection on Chest Radiographs: A Multicenter External Validation Study | Thian et al. | Radiology: Artificial Intelligence 2021 [V] | External validation of pneumothorax detectors at multiple institutions. | Performance dropped and varied across external sites. | Direct precedent: pneumothorax sensitivity is site-fragile even for dedicated detectors. | https://pubmed.ncbi.nlm.nih.gov/34350409/ |
| 56 | The Effect of Image Resolution on Deep Learning in Radiography | Sabottke & Spieler | Radiology: Artificial Intelligence 2020 [V] | Varies CXR input resolution per finding. | Optimal resolution was finding-dependent. Subtle findings benefited from higher resolution. | Check MedScope's effective pixels per token for thin pleural lines. | https://pubs.rsna.org/doi/10.1148/ryai.2019190015 |
| 57 | On the limits of cross-domain generalization in automated X-ray prediction | Cohen et al. | MIDL 2020 [V] | Cross-dataset CXR training and testing. | Cross-site failures stem partly from label (definition) shift, not only image shift. | New-hospital "misses" may partly be label-definition differences (e.g. small or treated pneumothorax). Audit labels. | https://proceedings.mlr.press/v121/cohen20a.html |
| 58 | Underdiagnosis bias of AI algorithms applied to chest radiographs in under-served patient populations | Seyyed-Kalantari et al. | Nature Medicine 2021 [K] | Underdiagnosis rates across subgroups for CXR classifiers. | Systematic underdiagnosis (false "no finding") in under-served groups. | Being "conservative" (saying absent) is the clinically harmful failure. Supports reporting FN-weighted utility. | https://www.nature.com/articles/s41591-021-01595-0 |
| 59 | In Search of Lost Domain Generalization | Gulrajani & Lopez-Paz | ICLR 2021 [K] | DomainBed: fair comparison of DG algorithms. | Carefully tuned ERM matches most DG algorithms. | Any DG claim needs a tuned-ERM, matched-compute baseline (MedScope already uses one). | https://arxiv.org/abs/2007.01434 |
| 60 | Causality-Inspired Single-Source Domain Generalization for Medical Image Segmentation | Ouyang et al. | IEEE TMI 2023 [K] | Random-convolution intensity augmentation plus interventional augmentation that breaks spurious correlations. | Better cross-site segmentation from a single source. | Cheap, single-source augmentation for the segmenter and the encoder. Same causal logic as artifact-balancing. | https://arxiv.org/abs/2111.12525 |
| 61 | Mitosis domain generalization in histopathology images - The MIDOG challenge | Aubreville et al. | Medical Image Analysis 2023 [K] | Multi-scanner lesion (mitosis) detection challenge. | Scanner shift strongly degrades detection. Augmentation and domain-adversarial methods help partly. | Evidence that lesion-level detection under scanner shift is a known hard problem with established baselines. | https://eprints.whiterose.ac.uk/194640 |

Ledger total: **61** entries (29 flagged V, 32 flagged K). Spot-check K items before submission.

### 2.6 Seen but excluded from the main ledger

- MedGemma Technical Report / MedSigLIP (Sellergren et al., arXiv:2507.05201). Still arXiv-only per search. Usable as a model resource, not as evidence.
- Hidden in plain sight: VLMs overlook their visual representations (Fu et al., arXiv:2506.08008). No venue found. Its finding (VLMs fall below their own encoders on vision-centric tasks) agrees with #6.
- MaskMedPaint (arXiv:2411.10686). Venue not found.
- PRISM (arXiv:2503.00196; PDF header says PMLR, likely MIDL 2025). Not verified, budget exhausted.
- Mask of truth: model sensitivity to unexpected regions of medical images (arXiv:2412.04030). Venue not verified.
- Domain Generalization for Medical Image Analysis: A Review (Yoon et al., arXiv:2310.08598). Possibly Proceedings of the IEEE 2024. Not verified.
- Fast-moving 2025-26 medical-VLM benchmarks (RadSight, DrVD-Bench, MedGround, Med-Banana). arXiv-only at search time.

---

## 3. What is known

### 3.1 Safely adapting a vision encoder inside a VLM

1. **Naive encoder tuning in VLMs is often harmful, and it is recipe-dependent.**
   - Prismatic (#4) found vision-backbone fine-tuning degrades performance, especially localisation.
   - Idefics2 (#5) found full unfreezing unstable. LoRA on the backbones with a fully trained connector was stable.
   - Cambrian-1 (#3) found unfreezing helps under a good recipe with enough data.
   - MedScope's collapse at the LM learning rate fits the "bad recipe" regime.
2. **Mechanism of the collapse.**
   - LP-FT (#26): when the head is mis-specified, early large gradients distort pretrained features. Here the "head" is the projector plus the LLM, which was tuned to the old features.
   - Once visual features become noisy, the LLM's text prior wins. MMStar (#7), VCD (#8) and mDPO (#14) all document that the language prior is the fallback.
   - The result is "answering from question wording alone".
3. **Mechanism of "more conservative, not more perceptive" at 1/10 LR.**
   - Low-rank, low-LR updates fit the easiest signal, the output prior (#33).
   - Training on erased views pushes "absent" up. Without new visual features, the cheapest loss reduction is a global shift towards "absent".
4. **Tools that work outside medicine.**
   - Stage order (LP-FT, #26).
   - Layer selection matched to the shift type (surgical fine-tuning, #30): input-level hospital shift points to early blocks.
   - Per-layer trust regions (TPGM, #31).
   - Feature-space anchoring to the frozen encoder (LDIFS #32, Xiao #34, VIRAL #13).
   - Pretraining-matched objectives (FLYP, #29).
   - Weight-space interpolation or averaging (WiSE-FT #27, soups #28).
   - None of these has been tested on a medical VLM against an evidence-sensitivity metric. That is the opening.
5. **The bottleneck may not be the encoder at all.**
   - VLMs underperform linear probes on their own encoder (#6; excluded preprint "Hidden in plain sight").
   - Deep LLM layers largely ignore visual tokens (#9).
   - First diagnostic: a linear probe for "pneumothorax present" on frozen Qwen vision tokens at the new hospital. If the probe sensitivity is high, fix the read-out, not the encoder.
6. **Medical encoders.**
   - RAD-DINO (#18): image-only SSL matches or beats text-supervised encoders and captures detail that reports omit.
   - BiomedCLIP (#19) covers many modalities.
   - CheXzero (#20) is report-supervised.
   - SSL pretraining gives better OOD and data efficiency at new sites (REMEDIS, #23).
   - Fused SSL+contrastive features help VLMs (#1, #4).
   - All encode non-pathological attributes strongly (#25), so they need shortcut audits.

### 3.2 Stopping a model from exploiting edit artifacts

1. **Removal leaks the label.** ROAD (#40) shows a model can classify from where and how pixels were removed. ROAR (#41) shows removal shifts the distribution. Large frozen encoders detect generated or inpainted content almost linearly (#49). High-norm artifact tokens concentrate in low-information patches (#12), which is exactly what smooth inpainting produces.
2. **Imperceptible cues are learned readily** (race from degraded images, #52; CT-GAN traces, #48). Physician judgement that an erasure "looks natural" or "still looks positive" does not bear on what the model detects.
3. **The confound in MedScope's design (inference from 1-2).**
   - Erasure is applied at the lesion site and the control edit elsewhere.
   - So "edit co-located with the queried finding's typical region" still predicts "absent".
   - Matched-shape controls remove shape information but not location or co-location information. ROAD's point is about both.
   - This fits the preprint's report that matching the control edit "was not shown to matter".
4. **What works against such shortcuts.**
   - (a) Make the nuisance independent of the label in training data: group balancing, as in DFR #54, causal augmentation #60, counterfactual positives #46.
   - (b) Supervise pairs at the representation or gradient level, not only the output (#42, #34).
   - (c) Imputation that does not leak (#40), or edits constrained to the target with keep-masks (#44).
   - (d) Re-fitting only the read-out on balanced data when core features exist (#54).
   - Saliency or attention alignment alone is unreliable (#53).
5. **Pneumothorax-specific confounds.**
   - Chest drains (#37, #38, #39) produce strong, documented shortcuts.
   - Drain prevalence and treatment timing vary by hospital, a plausible cause of new-site sensitivity loss independent of the edit shortcut.
   - In-image (localised) annotation reduced the confounding (#39).

### 3.3 Cross-hospital lesion detection

- External drops are the norm for pneumothorax (#55) and for scanner-shifted lesion detection (#61).
- Part of the drop is label-definition shift (#57).
- Tuned ERM is a strong baseline (#59).
- Single-source causal augmentation (#60) and counterfactual domain positives (#46) are the strongest medical DG tools that need no target data.
- SSL foundation features improve OOD robustness (#23, #18).
- Resolution is finding-dependent (#56). Token pruning and positional bias may drop apical evidence (#10).

---

## 4. Gaps MedScope could own

1. **No published work measures, or controls, the edit-location shortcut in counterfactual training of medical VLMs.**
   - ROAD-style leakage is known in attribution evaluation (#40).
   - It has never been applied to counterfactual training data for VLM grounding, where it turns into a learned policy ("edited → absent").
   - MedScope has the exact failure case: physician-positive erasures called absent.
2. **No study separates encoder capacity from read-out in a medical VLM under hospital shift.** Benchmarks show failures (#15, #16, #17). None asks whether a linear probe on the VLM's own vision tokens detects the missed pneumothorax at the new hospital.
3. **Robust fine-tuning methods (LP-FT, surgical, LDIFS, WiSE-FT, VIRAL) have not been tested inside a medical VLM with an image-reliance metric.** Every published robust-fine-tuning study reports accuracy only. None reports whether the model still uses the image (ESG, question-only agreement) after encoder adaptation.
4. **Positional bias and apical findings.** No paper links VLM token-selection or attention positional bias (#10) to the anatomical position of critical findings such as apical pneumothorax.
5. **Counterfactual site positives in a VLM.** Counterfactual contrastive learning (#46) has been shown only for classifier encoders. It has not been shown inside an instruction-tuned VLM or combined with lesion-erasure counterfactuals.
6. **Artifact-balanced (2×2) counterfactual design.** Prior counterfactual-augmentation work crosses label-flipping and label-preserving edits (#43). No medical imaging work crosses lesion-flipping and lesion-preserving edits at the same site with the same editor.

---

## 5. Candidate frameworks

All predictions are stated so that they can fail. "ESG" = absent/refer rate after erasure minus after control edit (as defined in arXiv:2611.13006). "Physician-positive erasures" = erasures physicians still read as positive. Compute assumes Qwen3.5-4B in bf16 with LoRA and gradient checkpointing on one 80 GB A100.

### Step 0 (shared diagnostics, ~1 GPU-day, do first)
- **D1 Edit-detectability probe.** Freeze MedScope. Fit a logistic probe on mean-pooled vision tokens (and on LLM hidden states at the answer position) to classify erased vs control-edited vs unedited.
  - Prediction under the shortcut hypothesis: AUC > 0.9 for erased-vs-unedited at the lesion site, and the probe score predicts "absent" on physician-positive erasures (point-biserial r > 0.3).
  - If AUC ≈ 0.5, the shortcut hypothesis for observation (3) is wrong. Drop F1's invariance term.
- **D2 Read-out versus encoder.** Fit a linear probe for "pneumothorax present" on frozen vision tokens, trained internally and tested at the new hospital.
  - If probe sensitivity is far above the VLM's 10/48, the bottleneck is read-out: favour F2/F3 read-out fixes over encoder tuning.
  - If the probe is also near 10/48, the encoder lacks the evidence: favour F2 teacher fusion and F4 resolution.
- **D3 Positional test.** Re-run the external pneumothorax films flipped vertically (the question is unchanged).
  - A sensitivity change of ≥ 8/48 indicates positional or token-selection bias (#10).
- **D4 Drain stratification.** Label drains on the 48 external positives (#38).
  - If misses concentrate in drain-free films, part of the gap is a drain shortcut.

### F1 (recommended core). Artifact-Balanced Counterfactuals with Edit-Invariance ("same-site, same-editor 2×2")

**Mechanism.**
1. **Close the confound in the data.** For each lesion image, add a **lesion-preserving same-site edit**, labelled *present*. It passes the lesion mask region through the same inpainting pipeline with the lesion kept: RadEdit-style keep-mask (#44), low-strength SDEdit round-trip, or inpaint-then-paste-back of the lesion core with a blended border. For lesion-free images, add same-anatomical-site edits labelled *absent*. Edit presence, location, shape and editor then become statistically independent of the label (a full 2×2: lesion {kept, erased} × edit {at site, elsewhere}).
2. **Label erasures by residual evidence, not by intent.** A frozen in-distribution scorer (an ensemble of the segmenter and a RAD-DINO linear probe; internal data only, so its poor generalisation does not matter here) flags incomplete erasures as *present/refer* rather than *absent*. This removes the label noise behind "physician-positive erasure → absent".
3. **Representation-level invariance.** Add a small adversarial head with gradient reversal, trained to predict "was this region edited?" from vision tokens and from the LLM hidden state at the answer token. Add a Teney-style (#42) pair loss: the feature difference between original and erased views must concentrate on lesion-mask tokens (penalise feature change outside the mask, reward change inside), not on output agreement. Output agreement is what the failed paired-view objective used.
4. Keep the existing LLM-LoRA. Encoder stays frozen in F1 alone, so F1 isolates the shortcut fix.

**Closest work and difference.**
- ROAD (#40) only diagnoses leakage, for attribution evaluation.
- Xiao et al. (#34) use masks as counterfactuals but not label-preserving edits, and not a VLM.
- Teney (#42) supervises gradients on pairs without the edit-artifact control.
- Kaushik (#43) crosses edit types in NLP.
- RadEdit (#44) uses keep-masks for stress testing, not for training.
- MedScope's preprint used control edits *elsewhere* and output-level consistency.
- Novelty: the first counterfactual-training design in which the editing operation is provably uninformative of the label, with representation-level enforcement, for a medical VLM.

**Falsifiable predictions.**
- P1: D1 probe AUC for "edited at site" falls from > 0.9 to < 0.65.
- P2: On physician-positive erasures, the absent rate falls by ≥ 20 percentage points versus MedScope (paired McNemar, α = 0.05).
- P3: ESG on physician-confirmed complete erasures stays ≥ 0.70 (no more than 0.06 below 0.758).
- P4: On a held-out unseen inpainting tool, erased-lesion claims stay ≤ 12%.
- P5 (new hospital): sensitivity does **not** need to rise. F1 targets observation (3). If sensitivity drops by > 4/48 relative to MedScope, F1 is over-correcting towards "present". Report specificity on lesion-free images as a guard (≤ 5 pp loss).
- Kill condition: if P1 holds but P2 fails, the shortcut is not mediated by detectable edit features. Revisit label noise.

**Compute.**
- Generating lesion-preserving edits: about 3-6 s per image with an SD-class inpainter, so roughly 5-8 GPU-hours for 5k images.
- One LoRA run: about 6-12 h. Three seeds plus a matched-compute control: about 2-3 GPU-days.

### F2. Anchored, staged vision adaptation (perception without collapse)

**Mechanism.**
1. **Stage A (LP-FT order, #26).** Train the projector and LLM-LoRA with the encoder frozen, including F1 data.
2. **Stage B (surgical, #30).** Unfreeze LoRA only on (i) the first 25% of ViT blocks (input-level hospital shift) and (ii) a middle band, at 1/20-1/50 of the LLM LR. Use a per-layer trust region (TPGM, #31) or a fixed L2-SP on the LoRA deltas.
3. **Anchor losses.**
   - LDIFS feature distance to the frozen original encoder on all patches (#32).
   - A VIRAL-style (#13) alignment of LLM-internal visual tokens to **frozen RAD-DINO** (CXR) or BiomedCLIP (other modalities) patch features. This puts medical SSL detail into the VLM without swapping the encoder.
4. **Image-reliance guard.**
   - An mDPO-style (#14) conditional term: for the same question, the correct answer on the real image must beat the same answer on a lesion-erased or blank image by a margin.
   - Track question-only agreement (MMStar-style, #7) every N steps and early-stop if it rises by > 10 pp above Stage A.
5. **WiSE-FT (#27).** Interpolate the Stage B vision-LoRA with zero (α ∈ {0.25, 0.5, 0.75}) and pick α on internal validation only.

**Closest work and difference.** Prismatic, Idefics2 and Cambrian (#3-#5) report when tuning hurts or helps, not how to prevent collapse in a small model. LDIFS, VIRAL and WiSE-FT are general-domain and measure accuracy only. Novelty: (a) shift-type-matched layer selection for hospital shift inside a VLM, (b) anchoring to a *medical* SSL teacher, (c) collapse monitored by an image-reliance metric. All three are testable on ESG.

**Falsifiable predictions.**
- P1: Question-only agreement stays within 5 pp of the frozen-encoder model. Observation (2) does not recur at any α.
- P2: New-hospital pneumothorax sensitivity rises by ≥ 8/48 over MedScope (paired McNemar, one-sided α = 0.05), with ≤ 5 pp specificity loss.
- P3: Pooled four-centre lesion sensitivity rises by ≥ 5 pp. ESG stays ≥ 0.70.
- P4 (mechanism): without the RAD-DINO anchor (LDIFS only), P2 fails, showing the gain comes from imported medical detail, not regularisation.
- If D2 showed the encoder already holds the evidence, the prediction flips: F2's gain should be ≤ that of read-out-only re-fitting (F3). That outcome would also be informative.

**Compute.**
- RAD-DINO teacher (ViT-B) features are precomputed once: about 1 h for 20k images.
- Stage A ≈ 8 h. Stage B ≈ 10-14 h with checkpointing.
- WiSE sweep: inference only, about 2 h.
- Three seeds: about 4-5 GPU-days.

### F3. Read-out repair with a frozen evidence probe as a tool ("probe-gated reading")

**Mechanism.**
- If D2 shows the frozen encoder carries the evidence, attach lightweight patch-level probes to frozen Qwen vision tokens, or to frozen RAD-DINO/BiomedCLIP tokens: logistic or 1-layer attention per finding.
- Train the probes on internal data with F1's artifact-balanced 2×2 and hospital-style intensity augmentation (#60).
- The agent calls the probe as an image tool. The tool returns a coarse evidence heatmap and crops the top-k regions at native resolution for a second look.
- Then re-fit **only** the LLM-LoRA read-out on an artifact-balanced, site-balanced set (DFR logic, #54).

**Closest work and difference.**
- Zhang et al. (#6) add classification data to the VLM; DFR (#54) re-fits last layers in classifiers.
- MedScope already uses image tools, but its segmenter generalises poorly. A frozen-foundation probe is a lower-capacity head on robust features (REMEDIS #23, LP-FT #26), so it should transfer better.
- Novelty: an evidence probe trained with artifact-balanced counterfactuals, used as a tool, with read-out-only re-fitting.

**Falsifiable predictions.**
- P1: At new hospitals, probe AUROC for pneumothorax is ≥ 0.05 above the current segmenter's.
- P2: VLM new-hospital sensitivity improves by ≥ 6/48 with ≤ 5 pp specificity loss.
- P3: ESG ≥ 0.70 and erased-lesion claims ≤ 12%. Because the probe was trained on F1 data, it must respond to real erasures. If it fires on erased views (probe false-positive rate on erasures > 20%), the framework fails.

**Compute.** Probes take minutes to train. Read-out LoRA ≈ 6-8 h. In total about 1-1.5 GPU-days with three seeds. The cheapest option.

### F4. Resolution- and position-aware evidence tokens (for thin or apical findings)

**Mechanism.** If D3 or D4 implicate resolution or positional bias:
- (a) raise the max-pixels budget for CXR, or add S²-style (#11) multi-scale tiles of the lung apices and periphery;
- (b) disable any token reduction and add a 2D position-balanced token-sampling constraint (#10);
- (c) train with random vertical and horizontal crops, so apical evidence does not occupy a fixed token position.

**Closest work.** S² (#11), Feather (#10), Sabottke (#56). None of them targets anatomically positioned critical findings.

**Predictions.**
- After F4, the D3 vertical-flip sensitivity difference shrinks below 3/48.
- Pneumothorax sensitivity rises by ≥ 6/48 at the new hospital, while large-lesion classes (other modalities) change by ≤ 2 pp. A finding-specific signature tests the mechanism.

**Compute.** Higher-resolution inputs roughly double the tokens. About 1.5-2× the training cost of F1, around 3-4 GPU-days with seeds.

### F5 (optional add-on). Counterfactual site positives in the VLM

**Mechanism.** Use a causal generative model (#46, #47) trained on the internal multi-site data to make "same patient, other scanner or site" counterfactuals. Add a contrastive or LDIFS-style invariance on vision tokens between each image and its site counterfactual during F2 Stage B.

**Prediction.** Lowers the internal-to-new-hospital sensitivity drop by ≥ 30% relative to F2 alone, with no ESG change (±0.03).

**Compute.** Generator training takes about 1-2 GPU-days at 256-512 px. This is the most expensive option and image fidelity for fine pleural lines is a risk. Treat it as stretch.

### Recommendation (ONE framework)

Package **F1 + F2** as a single framework: *Artifact-Balanced, Anchored Evidence Learning*. F3 and F4 serve as ablation arms chosen by diagnostics D1-D4.
- F1 fixes the label-identifying edit confound (observation 3) with a data design that is new and easy to explain: same site, same editor, label varies.
- F2 gives the first principled, collapse-free route to better perception (observations 1 and 2): staged, layer-selective, anchored to a medical SSL teacher, and guarded by an image-reliance metric.
- The diagnostics make the paper strong even if gains are modest: each one has a pre-registrable outcome that falsifies a specific mechanism.

Total compute: about 7-10 A100-days including three seeds and matched-compute controls.
