# Strand 2: Reducing object hallucination and language-prior dominance in general VLMs

Search date: 2026-11-14. Reviewer: research-agent strand 2 (read-only).

---

## 1. Search boundary

**Scope.** Methods that reduce object hallucination or language-prior dominance in general (mostly non-medical) vision-language models:
- contrastive and guided decoding;
- preference and RL alignment;
- counterfactual or negative-sample instruction data;
- attention re-weighting, visual-token emphasis and latent steering;
- causal and counterfactual debiasing of VQA language priors (the classic VQA-CP line);
- studies of why these methods fail or which evaluations they game.

Two medical-VQA papers are included only as the closest analogues. Medical hallucination benchmarks belong to other strands.

**Years.** 2019-2026, weighted towards 2023-2026. The VQA-CP debiasing papers (2019-2021) are kept on purpose: "the question names a finding" is the same failure as "the question type predicts the answer".

**Inclusion rules**
- Peer-reviewed venues only in the main ledger: CVPR, ICCV, ECCV, NeurIPS, ICML, ICLR, ACL, EMNLP, NAACL, AAAI, IJCAI and MICCAI.
- Workshop papers are kept but labelled as workshop papers (IBD at CVPRW 2025; POVID at an ICLR 2024 workshop).
- Excluded: arXiv-only work (listed separately in §2b), surveys, and papers about hallucination in text-only LLMs.

**Venue verification codes**
- **V**: the venue was confirmed this pass on an official proceedings or venue page (openaccess.thecvf.com, proceedings.iclr.cc, proceedings.mlr.press, proceedings.neurips.cc, aclanthology.org, ojs.aaai.org, ijcai.org, papers.miccai.org, the ECCV/ECVA, ICLR, ICML or NeurIPS virtual sites, or mlanthology.org).
- **R**: the venue is recalled from prior knowledge and was **not** re-fetched. The shared web-search budget ran out (200 calls per turn). Re-check these before citing.

**Queries run.** Searches used WebSearch (standard and "extended"), plus WebFetch on official pages.
1. contrastive decoding hallucination LVLM POPE gains yes/no answer bias critique "contrastive decoding" not effective (extended)
2. IBD image-biased decoding hallucination large vision-language models venue
3. POVID "Aligning Modalities in Vision Large Language Models via Preference Fine-tuning" accepted
4. HA-DPO "Beyond Hallucinations ... Hallucination-Aware DPO" venue
5. "On the Value of Out-of-Distribution Testing: An Example of Goodhart's Law" VQA-CP NeurIPS 2020
6. mDPO conditional preference optimization EMNLP 2024
7. V-DPO vision-guided DPO Findings EMNLP 2024
8. CHiP cross-modal hierarchical DPO ICLR 2025
9. HSA-DPO fine-grained AI feedback AAAI 2025
10. RLAIF-V CVPR 2025
11. AGLA assembly of global and local attention CVPR 2025
12. "Paying More Attention to Image" ECCV 2024
13. "Instruction Contrastive Decoding" Findings ACL 2024
14. HALC adaptive focal-contrast decoding ICML 2024
15. M3ID "Multi-Modal Hallucination Control by Visual Information Grounding" CVPR 2024
16. Bootstrapped Preference Optimization ECCV 2024
17. "Symmetrical Visual Contrastive Optimization" minimal contrastive images
18. OPA-DPO "On-Policy Data Hold the Key" CVPR 2025
19. Teney "Learning what makes a difference from counterfactual examples and gradient supervision" ECCV 2020
20. CausalMM "Deciphering Attention Causality" ICLR 2025
21. VTI latent space steering ICLR 2025
22. LRV-Instruction ICLR 2024
23. Counterfactual Samples Synthesizing CVPR 2020
24. "A negative case analysis of visual grounding methods for VQA" ACL 2020
25. Self-Introspective Decoding ICLR 2025
26. preference optimization counterfactual edited images object removed inpainting hallucination MLLM 2025 (extended)
27. Greedy Gradient Ensemble ICCV 2021
28. Counterfactual VQA CVPR 2021
29. Concentric Causal Attention NeurIPS 2024
30. DeCo "MLLM can see?" ICLR 2025
31. "Interpreting and Editing Vision-Language Representations" ICLR 2025
32. Nullu HalluSpace CVPR 2025
33. MARINE image-grounded guidance ICML 2025
34. HALVA data-augmented phrase-level alignment ICLR 2025
35. VLind-Bench NAACL 2025
36. Visual Attention Sink ICLR 2025
37. ClearSight CVPR 2025
38. Introspective Distillation NeurIPS 2021
39. MMStar NeurIPS 2024
40. NeurIPS 2025 multimodal preference optimisation with image-side rejected images, symmetric DPO (extended)
41. medical VLM hallucination mitigation with contrastive decoding or preference optimisation, MICCAI 2025, counterfactual image (extended)
42. AutoHallusion and HallusionBench venue checks: **blocked**, budget exhausted

**Known blind spots**
- The search budget ran out before every recalled venue (code R) could be re-verified, and before AutoHallusion (Findings of EMNLP 2024, recalled) could be checked. AutoHallusion is therefore listed only in §2b.
- No systematic database export (Scopus or Web of Science) was run. Recall is limited to keyword queries plus snowballing from known anchor papers.

---

## 2. Evidence ledger

**Column notes**
- **Mech** is the mechanism class: Dec = decoding, Pref = preference/RL, Data = data, Att = attention/representation, Causal = causal/ensemble, Eval = critique or evaluation.
- **V/R** is the venue verification code from §1.
- "Key result" gives the authors' own headline claim. Exact numbers are given only where the paper was read this pass, or where the number is widely cited and recalled with confidence. Everything else is stated qualitatively.

### 2a. Main ledger (peer-reviewed)

| # | Title | First author et al. | Venue, year (V/R) | Core idea | Mech | Key result & benchmark | Known failure modes / critiques | Relevance to MedScope | URL |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mitigating Object Hallucinations in LVLMs through Visual Contrastive Decoding (VCD) | Leng et al. | CVPR 2024 (R) | Subtract the logits from a Gaussian-noised image from the clean-image logits, with an adaptive plausibility constraint | Dec | Several POPE-F1 points higher on LLaVA-1.5, InstructBLIP and Qwen-VL. Mirage (#10) measured LLaVA-7B on POPE COCO-random: 88.6 acc vs greedy 87.1 | Mirage (#10): the gain is a shift of the yes-ratio from 39.2% to 46.4%, and it *hurts* on GQA-adversarial (80.9 → 78.0) where the model already says yes. No gains on CHAIR or MME | MedScope's answer-flip and second-view policies are VCD-like. Expect only a criterion shift, which ESG cancels by design | https://arxiv.org/abs/2311.16922 |
| 2 | OPERA: Alleviating Hallucination via Over-Trust Penalty and Retrospection-Allocation | Huang et al. | CVPR 2024 (R) | A beam-search penalty on "summary token" attention columns, plus rollback | Dec/Att | Lower CHAIR in long captions | Mostly a captioning effect (fewer objects mentioned); expensive beam search; little bearing on a single yes/no token | Low: MedScope answers one token | https://arxiv.org/abs/2311.17911 |
| 3 | Multi-Modal Hallucination Control by Visual Information Grounding (M3ID) | Favero et al. | CVPR 2024 (V) | Mutual-information decoding that boosts tokens whose probability depends on the image, since visual influence decays with generated length | Dec | Reports roughly a quarter fewer hallucinated objects in captions (LLaVA-13B, InstructBLIP); also a DPO variant | Its premise (visual influence decays with length) does not apply to one-token answers. It is still subtraction of an image-free prior, a criterion shift | The theory (prompt dependence vs image dependence) is useful for the write-up; the method itself transfers poorly | https://openaccess.thecvf.com/content/CVPR2024/papers/Favero_Multi-Modal_Hallucination_Control_by_Visual_Information_Grounding_CVPR_2024_paper.pdf |
| 4 | HALC: Object Hallucination Reduction via Adaptive Focal-Contrast Decoding | Chen et al. | ICML 2024 (V) | Use an open-vocabulary detector to find the token's visual context, then contrast between fields of view | Dec | Lower CHAIR; better POPE and MME on LLaVA, MiniGPT-4 and mPLUG-Owl2 | Depends on the external detector; much slower; the gain comes from the detector | Equivalent to MedScope's "close-up + segmenter" policies, which failed. The detector is the real evidence source | https://proceedings.mlr.press/v235/chen24bi.html |
| 5 | Mitigating Hallucinations in LVLMs with Instruction Contrastive Decoding (ICD) | Wang et al. | Findings ACL 2024 (V) | Contrast against a "disturbance instruction" (role prefix) that amplifies hallucination | Dec | POPE and MME gains | Named in Mirage (#10) among the contrastive methods whose gains are yes-ratio and plausibility artifacts | The "cautious prompt" policies MedScope tested are the mirror image of this | https://aclanthology.org/2024.findings-acl.937 |
| 6 | IBD: Alleviating Hallucinations in LVLMs via Image-Biased Decoding | Zhu et al. | CVPR 2025 **Workshops** (V) | Contrast the base model with an "image-biased" copy whose attention is pushed towards image tokens | Dec/Att | Gains on POPE, CHAIR and MME | Workshop paper; same POPE caveat | Low | https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Zhu_IBD_Alleviating_Hallucinations_in_Large_Vision-Language_Models_via_Image-Biased_Decoding_CVPRW_2025_paper.html |
| 7 | Self-Introspective Decoding (SID) | Huo et al. | ICLR 2025 (V) | Keep only the *least* important vision tokens after early layers to build a better "hallucination-amplified" contrast branch | Dec | Lower POPE, CHAIR and MME hallucination at lower cost than VCD | Mirage (#10): SID's POPE gain also comes with a yes-ratio rise (39.2% → 42.3%) | Low | https://proceedings.iclr.cc/paper_files/paper/2025/hash/3cc87f2bd3e3b4df8f9217326761c322-Abstract-Conference.html |
| 8 | MLLM Can See? Dynamic Correction Decoding (DeCo) | Wang et al. | ICLR 2025 (V) | Earlier layers *recognise* objects that the final layer suppresses. Mix logits from an adaptively chosen earlier layer into the final layer | Dec/Att | Reports roughly a 10% average hallucination reduction across captioning benchmarks | Evaluated on captioning and POPE; no matched-control test; the layer choice is a heuristic | **High in principle.** It is a "knows but does not say" hypothesis: if MedScope's middle layers separate erased from control, a readout fix can raise discrimination. Testable with probes (Framework C) | https://mlanthology.org/iclr/2025/wang2025iclr-mllm/ |
| 9 | Mitigating Object Hallucination in LVLMs via Image-Grounded Guidance (MARINE) | Zhao et al. | ICML 2025 (V) | Classifier-free guidance from the outputs of open-vocabulary detectors or segmenters | Dec | Lower CHAIR, better POPE; training-free | Moves the evidence into an external detector. Gains are bounded by that detector, and are zero where it fails (as with MedScope's segmenter policy) | Medium: confirms that external evidence only helps if the external model separates erased from real | https://proceedings.mlr.press/v267/zhao25j.html |
| 10 | **The Mirage of Performance Gains: Why Contrastive Decoding Fails to Mitigate Object Hallucinations in MLLMs?** | Yin, Si, Wang | **NeurIPS 2025** (V) | Audits VCD, ICD and SID. POPE gains come from (i) a shift in the yes/no answer distribution and (ii) the adaptive plausibility constraint, which reduces sampling to near-greedy | Eval | A prompt that just biases towards "yes" (90.2) or a forced-yes rule near ties (90.0) beats VCD (89.2) on COCO-random with LLaVA-13B. No contrastive-decoding gains on MME, CHAIR, NoCaps or LLaVA-Bench | n/a (this is the critique) | **Central.** An independent replication of MedScope's 270-policy result in the general domain: decoding changes the criterion, not discrimination. Cite it as prior support for ESG's design | https://proceedings.neurips.cc/paper_files/paper/2025/file/2f89a23a19d1617e7fb16d4f7a049ce2-Paper-Conference.pdf |
| 11 | Counterfactual Anatomy-Guided Spatial-Temporal Decoding for Annotation-Free Hallucination Mitigation in Medical VLMs (CAST) | Lu et al. | MICCAI 2026 (V) | A segmenter proposes regions; the region whose occlusion most reduces the answer likelihood is chosen; contrastive decoding with CFG attention correction | Dec | On SLAKE closed questions with Phi-3.5V-Med, accuracy rises from 61.42 to 81.49 (per a reviewer summary); about 2.1x latency | Reviewers flagged reliance on the segmenter (MedSAM3) and many hyperparameters. Not tested against edited images | Closest medical decoding method. The occlusion-sensitivity idea resembles MedScope's segmenter and close-up policies; it would need an ESG test | https://papers.miccai.org/miccai-2026/0209-Paper4832.html |
| 12 | Paying More Attention to Image: A Training-Free Method for Alleviating Hallucination in LVLMs (PAI) | Liu et al. | ECCV 2024 (V) | Scale up attention to image tokens in self-attention and subtract text-only logits ("text inertia") | Att/Dec | Lower CHAIR; better POPE and MME | The text-only subtraction is a prior or criterion shift; amplifying attention cannot create evidence the encoder lacks | Diagnostic: if PAI changes MedScope ESG without changing AUROC, that supports the criterion-shift story | https://mlanthology.org/eccv/2024/liu2024eccv-paying |
| 13 | Mitigating Object Hallucinations in LVLMs with Assembly of Global and Local Attention (AGLA) | An et al. | CVPR 2025 (V) | Ensemble the global image logits with logits from a prompt-relevant, locally masked augmented view | Att/Dec | POPE, CHAIR and MME gains | Same POPE caveat. The local view is selected by image-prompt matching, which is weak for subtle lesions | Equivalent to MedScope's close-up test-time augmentation, which failed | https://openaccess.thecvf.com/content/CVPR2025/html/An_Mitigating_Object_Hallucinations_in_Large_Vision-Language_Models_with_Assembly_of_CVPR_2025_paper.html |
| 14 | Mitigating Modality Prior-Induced Hallucinations in MLLMs via Deciphering Attention Causality (CausalMM) | Zhou et al. | ICLR 2025 (V) | A structural causal model over attention; counterfactual attention (backdoor adjustment) in the vision encoder and LLM layers | Att/Causal | Large gains on VLind-Bench language-prior items; gains on MME and POPE | Counterfactual attention maps (random, uniform, shuffled) are crude; still a decode-time logit difference | Medium. It is the only decoding method evaluated on a language-prior benchmark that uses counterfactual images | https://mlanthology.org/iclr/2025/zhou2025iclr-mitigating |
| 15 | See What You Are Told: Visual Attention Sink in Large Multimodal Models (VAR) | Kang et al. | ICLR 2025 (V) | Find "visual sink" tokens that soak up attention, and redistribute that budget to image-centric heads | Att | Training-free gains across general VQA and hallucination benchmarks | Not tested on minimal-pair discrimination | Low-medium: a cheap attention-redistribution ablation on Qwen3.5 | https://www.iclr.cc/virtual/2025/poster/30795 |
| 16 | ClearSight: Visual Signal Enhancement for Object Hallucination Mitigation in MLLMs | Yin et al. | CVPR 2025 (V) | Visual Amplification Fusion: amplify visual signals in middle-layer attention instead of using a contrastive branch | Att | Lower hallucination at near-baseline speed; claims to keep content quality, unlike contrastive decoding | Same group as Mirage (#10), which partly motivates leaving contrastive decoding. Still POPE- and CHAIR-centred | Medium: middle-layer emphasis is a cheap ablation | https://openaccess.thecvf.com/content/CVPR2025/html/Yin_ClearSight_Visual_Signal_Enhancement_for_Object_Hallucination_Mitigation_in_Multimodal_CVPR_2025_paper.html |
| 17 | Mitigating Object Hallucination via Concentric Causal Attention (CCA) | Xing et al. | NeurIPS 2024 (V) | Long-term decay in RoPE makes distant image tokens under-attended; re-order visual-token positions concentrically and retrain | Att (architectural) | POPE and CHAIR gains after re-training LLaVA | Needs pre-training or alignment re-training; spatial position bias | Medium: lesions near the image edge may get less attention because of position; check where ESG failures sit | https://neurips.cc/virtual/2024/poster/96152 |
| 18 | Reducing Hallucinations in LVLMs via Latent Space Steering (VTI) | Liu et al. | ICLR 2025 (V) | Steering vectors for the vision encoder and text decoder, computed from perturbed-image variance, added at test time | Att/Latent | Better CHAIR, POPE and MMHal | The steering direction is generic stability; not tested on minimal pairs | The direction could be computed from the *erased-control* difference instead (Framework C) | https://proceedings.iclr.cc/paper_files/paper/2025/hash/b4008025c2182bfe16fcc8566ee14d64-Abstract-Conference.html |
| 19 | Nullu: Mitigating Object Hallucinations in LVLMs via HalluSpace Projection | Yang et al. | CVPR 2025 (V) | SVD of embedding differences between truthful and hallucinated pairs gives a "HalluSpace"; project the MLP weights onto its null space | Att/Weight-edit | CHAIR and POPE gains at no inference cost | The subspace encodes the LLM prior; the edit may remove prior knowledge needed for real findings | Medium: a null-space edit on a prior-direction is a cheap ablation | https://openaccess.thecvf.com/content/CVPR2025/html/Yang_Nullu_Mitigating_Object_Hallucinations_in_Large_Vision-Language_Models_via_HalluSpace_CVPR_2025_paper.html |
| 20 | Interpreting and Editing Vision-Language Representations to Mitigate Hallucinations (ProjectAway) | Jiang et al. | ICLR 2025 (V) | Applying the logit lens to image-token hidden states gives an internal confidence that an object is present, which separates real from hallucinated objects. A linear edit removes hallucinated-object features | Att/Latent | Large CHAIR reduction on COCO captions; zero-shot segmentation from the internal confidence | Captioning only; COCO objects; no edited-image control | **High.** It shows the internal representation can be more discriminative than the output, in the same model. MedScope can test whether this holds for inpainted erasures (Framework C) | https://proceedings.iclr.cc/paper_files/paper/2025/hash/9f14fb9acd243c13c95d4a490d1684ce-Abstract-Conference.html |
| 21 | RLHF-V: Towards Trustworthy MLLMs via Behavior Alignment from Fine-grained Correctional Human Feedback | Yu et al. | CVPR 2024 (R) | Segment-level human corrections; dense DPO | Pref | Large relative cut in Object HalBench hallucination with only about 1.4k samples | Captioning-centric. Partly works by making outputs more conservative (fewer object mentions) | Low for yes/no; the dense, segment-level signal idea is relevant | https://arxiv.org/abs/2312.00849 |
| 22 | RLAIF-V: Open-Source AI Feedback Leads to Super GPT-4V Trustworthiness | Yu et al. | CVPR 2025 (V) | Divide-and-conquer AI feedback; iterative on-policy DPO; feedback-guided inference-time scaling | Pref | State-of-the-art open-source trustworthiness on Object HalBench, MMHal and AMBER | Gains in generative tasks; less on discriminative tasks; reward-model quality limits it | Low-medium: MedScope's GRPO with a cost reward is the RL analogue and failed | https://openaccess.thecvf.com/content/CVPR2025/html/Yu_RLAIF-V_Open-Source_AI_Feedback_Leads_to_Super_GPT-4V_Trustworthiness_CVPR_2025_paper.html |
| 23 | Aligning Modalities in Vision LLMs via Preference Fine-tuning (POVID) | Zhou et al. | ICLR 2024 **Workshop** (V, workshop only) | Dispreferred answers come from GPT-4V hallucination injection *and* from the model answering a diffusion-noised image | Pref | Gains on POPE, CHAIR and MMHal | Workshop only. Noised-image negatives teach "degraded image → say less" | Noised-image negatives are exactly the edit-artifact shortcut that MedScope's control edit is designed to expose | https://mlanthology.org/iclrw/2024/zhou2024iclrw-aligning |
| 24 | Detecting and Mitigating Hallucination in LVLMs via Fine-Grained AI Feedback (HSA-DPO) | Xiao et al. | AAAI 2025 (V) | Train a sentence-level hallucination detector; detect-then-rewrite pipeline; severity-weighted DPO | Pref | Lower hallucination on AMBER and Object HalBench | Long-form only; depends on the detector | Low | https://ojs.aaai.org/index.php/AAAI/article/view/34744 |
| 25 | **mDPO: Conditional Preference Optimization for Multimodal LLMs** | Wang et al. | EMNLP 2024 (V) | Shows *unconditional preference*: multimodal DPO behaves much the same when the image is removed, i.e. it learns language-only preferences. Adds an image-conditional preference (same response, original vs corrupted image) and a reward anchor | Pref | Reduces hallucination across MMHal, Object HalBench and AMBER on two model sizes; the paper uses a ~3B and a 7B model (sizes from the full text, recalled) | The corrupted images are generic (random crop or mask). Nothing shows that discrimination improves rather than "corrupted → less confident" | **Central to explaining why MedScope's DPO failed.** If MedScope's DPO pairs differed only in text, mDPO predicts the model learns a text prior. Image-conditional pairs anchored on the control edit have not been published (Framework A) | https://aclanthology.org/2024.emnlp-main.460/ |
| 26 | V-DPO: Mitigating Hallucination in LVLMs via Vision-Guided DPO | Xie et al. | Findings EMNLP 2024 (V) | Builds classifier-free guidance into DPO training so the policy depends more on the image; builds synthetic image-contrast pairs | Pref | Gains on POPE, AMBER and related benchmarks; largest with image-contrast pairs | Small scale (LLaVA-7B); POPE-centric | Medium: a guidance-style objective with an image-contrast pair | https://aclanthology.org/2024.findings-emnlp.775/ |
| 27 | CHiP: Cross-modal Hierarchical DPO for Multimodal LLMs | Fu et al. | ICLR 2025 (V) | Visual preference module plus response-, segment- and token-level textual preferences | Pref | Roughly halves Object HalBench hallucination relative to DPO (Muffin, LLaVA) | Rejected images are generic diffusion-noised versions | Medium: the visual-preference term is the relevant part | https://proceedings.iclr.cc/paper_files/paper/2025/hash/e1c73e9595126794186536cfbbed012f-Abstract-Conference.html |
| 28 | Strengthening Multimodal LLM with Bootstrapped Preference Optimization (BPO) | Pi et al. | ECCV 2024 (V, oral) | Negatives come from the model's own answers on *distorted* images (bootstrapping the pre-training bias), plus LLM-injected errors | Pref | Gains on MM-Vet, LLaVA-Bench and POPE | Distortion-based negatives; risk of learning a distortion-detection shortcut | Same shortcut risk as POVID-style data. Shows on-policy negatives from degraded views are plausible | https://mlanthology.org/eccv/2024/pi2024eccv-strengthening |
| 29 | Mitigating Hallucinations in LVLMs via DPO: On-Policy Data Hold the Key (OPA-DPO) | Yang et al. | CVPR 2025 (V, oral) | Off-policy preference data is largely ignored because of the KL constraint. Expert-corrected on-policy responses are aligned first, then DPO | Pref | Large AMBER and Object HalBench gains with about 4.8k samples | Captioning-centric | **High for diagnosing MedScope's DPO failure.** If its DPO used off-policy pairs, OPA-DPO predicts little effect | https://mlanthology.org/cvpr/2025/yang2025cvpr-mitigating |
| 30 | Stop Learning it All to Mitigate Visual Hallucination, Focus on the Hallucination Target (TL-DPO) | Yoon et al. | CVPR 2025 (V) | Restricts the DPO loss to annotated hallucination-target spans | Pref | Lower hallucination across tasks while keeping general ability | Needs target annotation | Low for one-token answers (the target *is* the answer token) | https://cvpr.thecvf.com/virtual/2025/poster/32999 |
| 31 | Modality-Fair Preference Optimization for Trustworthy MLLM Alignment (MFPO) | Jiang et al. | IJCAI 2025 (V) | Rejected image: keywords are mapped by a modified SAM to regions, and diffusion noise is added **only in those regions**. Image-preference loss plus text-preference loss plus margin loss | Pref | LLaVA-1.5-7B on Object HalBench: CHAIRs 53.6 → 13.4. AMBER hallucination 36.4 → 22.5 | Region-local noise leaves a local edit footprint. There is no control edit elsewhere, so "noised region → absent" is a learnable shortcut | **Closest published design to MedScope's erase view.** The decisive difference is MedScope's matched control edit and held-out inpainter | https://ijcai.org/proceedings/2025/0046.pdf |
| 32 | Mitigating Hallucinations in LVLMs via Entity-Centric Multimodal Preference Optimization (EMPO) | Wu et al. | EMNLP 2025 (V) | Preference along three axes (image, instruction, response). Rejected images: entities are deleted or replaced with Stable Diffusion 2 inpainting and checked by CLIP | Pref | LLaVA-1.5-7B: Object HalBench CHAIRs 19.13 (DPO) → 7.16; MMHal hallucination rate 36.6% → 25.6% | One inpainter (SD2) is used for training *and* implicitly for testing. MME perception drops (1496.7 → 1389.8) | **Very close: inpainting-based object removal as a rejected image.** It lacks a control edit, a held-out inpainter and a discrimination metric | https://aclanthology.org/2025.emnlp-main.982.pdf |
| 33 | Mitigating Hallucination Through Theory-Consistent Symmetric Multimodal Preference Optimization (SymMPO) | Liu et al. | NeurIPS 2025 (V) | Symmetric pairs (two images, two responses) with direct preference supervision consistent with DPO, plus a preference-margin consistency loss | Pref | Better than prior vision-oriented DPO on five benchmarks | Pair construction is generic | High: symmetric pairs map onto real↔erased with "present"↔"absent" | https://neurips.cc/virtual/2025/loc/san-diego/poster/115608 |
| 34 | **Symmetrical Visual Contrastive Optimization: Aligning VLMs with Minimal Contrastive Images (S-VCO)** | Wu et al. | ACL 2025 (V) | Minimal visual-contrast image pairs (MVC dataset); a symmetric objective where each image is preferred for its own text and each text is rejected under the other image | Pref/Data | Up to 22% less hallucination; gains on vision-centric benchmarks that need minimal-pair discrimination | Pairs are natural or edited minimal pairs; held-out-editor generalisation not tested; no control edit | **Highest relevance.** The best published evidence that minimal-pair image training moves *discrimination* (vision-dependent benchmark gains) and not only hallucination counts | https://preview.aclanthology.org/setup/2025.acl-long.1462 |
| 35 | Mitigating Hallucination in Large Multi-Modal Models via Robust Instruction Tuning (LRV-Instruction) | Liu et al. | ICLR 2024 (V) | 400k instructions including *negative* instructions (non-existent objects, manipulated existing objects, manipulated knowledge); GAVIE evaluation | Data | Large hallucination reduction; finding: the positive:negative ratio controls the yes-bias | Negative questions are text-only (the image is unchanged); this mostly calibrates the yes/no criterion | Shows that negative-question data fixes the criterion, not the evidence. MedScope's lesion-free images already cover this | https://iclr.cc/virtual/2024/poster/18947 |
| 36 | Mitigating Object Hallucination in MLLMs via Data-augmented Phrase-level Alignment (HALVA) | Sarkar et al. | ICLR 2025 (V) | Generative augmentation swaps correct phrases for hallucinated ones; phrase-level contrastive alignment loss, with a KL anchor to keep general skills | Data/Pref | Lower CHAIR, better AMBER and MME-hallucination; general benchmarks preserved | Text-side counterfactuals only | Low-medium: the KL-anchored phrase loss is a template for a token-level presence loss | https://proceedings.iclr.cc/paper_files/paper/2025/hash/b73228d026ef49bfa49f95b7e330513e-Abstract-Conference.html |
| 37 | Analyzing and Mitigating Object Hallucination in LVLMs (LURE) | Zhou et al. | ICLR 2024 (R) | Statistical causes (co-occurrence, uncertainty, position); a post-hoc revisor | Data | Lower CHAIR | Captioning; post-hoc | Low: co-occurrence ≈ the anatomical context prior that makes lesions "expected" | https://arxiv.org/abs/2310.00754 |
| 38 | RUBi: Reducing Unimodal Biases for VQA | Cadene et al. | NeurIPS 2019 (R) | A question-only branch masks the main model's logits during training, cutting the gradient on prior-predictable examples | Causal/Ens | VQA-CP v2 ≈ 47 vs ≈ 38–39 baseline (recalled) | Gains concentrate on yes/no; drops in-distribution (Teney, #47) | Analogue of "question names the finding". The question-only branch is the presupposition prior | https://arxiv.org/abs/1906.10169 |
| 39 | Don't Take the Easy Way Out: Ensemble Based Methods for Avoiding Known Dataset Biases (LMH) | Clark et al. | EMNLP 2019 (R) | Product-of-experts with a bias-only model, learned mixing and entropy penalty | Causal/Ens | VQA-CP v2 ≈ 52 (recalled) | VQA-CP gains partly exploit the inverted prior (#47) | Same as #38 | https://arxiv.org/abs/1909.03683 |
| 40 | Counterfactual Samples Synthesizing for Robust VQA (CSS) | Chen et al. | CVPR 2020 (V) | V-CSS masks the *critical* objects (chosen by Grad-CAM) and assigns a changed answer; Q-CSS masks critical question words. Adds training samples | Data/Causal | CSS+LMH reaches ≈ 59 on VQA-CP v2 | Masked regions are an obvious artifact; Teney (#47) and Shrestha (#46) style critiques apply | **Direct ancestor of MedScope's erase view (V-CSS ≈ erase).** It lacks a control mask and a held-out masking method | https://openaccess.thecvf.com/content_CVPR_2020/html/Chen_Counterfactual_Samples_Synthesizing_for_Robust_Visual_Question_Answering_CVPR_2020_paper.html |
| 41 | **Learning What Makes a Difference from Counterfactual Examples and Gradient Supervision (GS)** | Teney et al. | ECCV 2020 (V) | For minimal counterfactual pairs, align the model's input-gradient with the vector between the paired inputs (gradient supervision), so its local sensitivity follows the real causal difference | Causal/Data | Better OOD generalisation on VQA-CP, NLI and sentiment from existing minimal pairs | Gains were modest; it needs pairs; double backprop | **High.** A training signal on *sensitivity*, not on outputs; ESG is a sensitivity measure (Framework B) | https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/1165_ECCV_2020_paper.php |
| 42 | Counterfactual VQA: A Cause-Effect Look at Language Bias (CF-VQA) | Niu et al. | CVPR 2021 (V) | Causal graph; at inference, subtract the natural direct effect of the question (total indirect effect) | Causal | Large VQA-CP v2 gains, mostly on yes/no questions | It is subtraction of a prior, i.e. a criterion shift; drops in-distribution (VQA v2) | Predicts that subtracting a "question names finding" prior shifts the criterion only. Use as a negative-control baseline | https://openaccess.thecvf.com/content/CVPR2021/html/Niu_Counterfactual_VQA_A_Cause-Effect_Look_at_Language_Bias_CVPR_2021_paper.html |
| 43 | Greedy Gradient Ensemble for Robust VQA (GGE) | Han et al. | ICCV 2021 (V) | Greedily fit the bias models first, then fit the base model to the residual gradient; analyses "biased models also over-exploit visual bias" | Causal/Ens | Around 57 on VQA-CP v2 | The ensemble style still mainly acts on answer-prior categories | GGE's finding that the *visual* shortcut is also a bias matches MedScope's edit-artifact risk | https://openaccess.thecvf.com/content/ICCV2021/html/Han_Greedy_Gradient_Ensemble_for_Robust_Visual_Question_Answering_ICCV_2021_paper.html |
| 44 | Introspective Distillation for Robust Question Answering (IntroD) | Niu & Zhang | NeurIPS 2021 (V) | A teacher blends in-distribution and OOD-debiased predictions; the student keeps both ID and OOD accuracy | Causal | Restores ID accuracy while keeping VQA-CP gains | Inherits the teacher's bias mechanism | Low-medium: a template for keeping lesion sensitivity (96%) while adding erase sensitivity | https://proceedings.neurips.cc/paper/2021/hash/878d5691c824ee2aaf770f7d36c151d6-Abstract.html |
| 45 | Eliminating Language Bias for Medical VQA with Counterfactual Contrastive Training (DeCoCT) | Wan et al. | MICCAI 2025 (V) | Splits the effect of a clinical term into localisation plus prior; Key Region Capture Module trained with counterfactual strategies; builds VQA-RAD-CP | Causal/Data | Claimed state of the art on VQA-RAD, SLAKE and VQA-RAD-CP (numbers not on page) | Reviewers raised possible leakage in VQA-RAD-CP, semantic distortion from term masking, and limited scope | Closest medical language-bias paper; still question-side and answer-accuracy based | https://papers.miccai.org/miccai-2025/0283-Paper2827.html |
| 46 | **A Negative Case Analysis of Visual Grounding Methods for VQA** | Shrestha et al. | ACL 2020 (V) | Shows that HINT and SCR "grounding" gains on VQA-CP persist with *random or irrelevant* region cues. The gains come from regularisation, not grounding | Eval | A simple regulariser without grounding matches them | n/a | **Mandatory ablation for any MedScope training method:** a random-region and control-region version of the same loss | https://aclanthology.org/2020.acl-main.727/ |
| 47 | **On the Value of Out-of-Distribution Testing: An Example of Goodhart's Law** | Teney et al. | NeurIPS 2020 (V) | Many VQA-CP methods exploit the known inversion of answer priors between train and test, or tune on the test set; trivial baselines do as well | Eval | Shows that a model which merely inverts the prior is competitive | n/a | **Central to MedScope's argument.** The analogue of "improving utility only through abstention". Supports a pre-registered held-out inpainter and the ESG design | https://proceedings.nips.cc/paper_files/paper/2020/file/045117b0e0a11a242b9765e79cbf113f-Review.html (proceedings record) ; https://mlanthology.org/neurips/2020/teney2020neurips-value |
| 48 | Evaluating Object Hallucination in LVLMs (POPE) | Li et al. | EMNLP 2023 (R) | Polling-based yes/no presence questions with random, popular and adversarial negatives | Eval | The de facto discriminative hallucination benchmark | Accuracy and F1 depend on the yes-ratio; Mirage (#10) shows criterion shifts game it | ESG improves on POPE by controlling for the edit footprint; report POPE-style yes-ratio alongside it | https://arxiv.org/abs/2305.10355 |
| 49 | VLind-Bench: Measuring Language Priors in LVLMs | Lee et al. | Findings NAACL 2025 (V) | Counterfactual images that contradict common sense, with staged sanity checks (commonsense, visual perception, commonsense bias) before the language-prior test | Eval | Nearly all LVLMs rely heavily on language priors | Synthetic images; general domain | The staged-sanity-check design matches MedScope's "physicians find 96% of real lesions" check | https://aclanthology.org/2025.findings-naacl.231 |
| 50 | Are We on the Right Way for Evaluating LVLMs? (MMStar) | Chen et al. | NeurIPS 2024 (V) | Many benchmark items are answerable without the image; proposes vision-indispensable items and multimodal-gain or leakage metrics | Eval | n/a | n/a | Support for reporting an image-ablated baseline next to ESG | https://mlanthology.org/neurips/2024/chen2024neurips-we |
| 51 | HallusionBench: An Advanced Diagnostic Suite for Entangled Language Hallucination and Visual Illusion | Guan et al. | CVPR 2024 (R) | Question pairs on original vs *edited* images (charts, tables, scenes); checks whether answers follow the edit | Eval | Frontier models had low pair accuracy (GPT-4V ≈ 31% question-pair accuracy, recalled) | No control edit; general domain | The nearest general-domain "edit-sensitivity" benchmark. ESG adds the matched-edit control | https://arxiv.org/abs/2310.14566 |

Count: 51 entries. 43 have venues verified this pass (V), including the two workshop papers (#6, #23). 8 were recalled and not re-fetched (R: #1, #2, #21, #37, #38, #39, #48, #51). The model sizes given for mDPO (#25) are also recalled, not checked.

### 2b. Influential arXiv-only or unverified work (not in the main ledger)

- **HA-DPO**: "Beyond Hallucinations: Enhancing LVLMs through Hallucination-Aware DPO" (Zhao et al., arXiv 2311.16839). No peer-reviewed venue found.
- **Delve into Visual Contrastive Decoding for Hallucination Mitigation of LVLMs** (arXiv 2412.06775). Another analysis of VCD's limits.
- **Rethinking CD: A Reproducibility Study and Extension on the Ineffectiveness of Contrastive Decoding at Mitigating Object Hallucinations in MLLMs** (arXiv 2607.25196, 2026). Independently reproduces Mirage (#10).
- **HII-DPO: Eliminate Hallucination via Accurate Hallucination-Inducing Counterfactual Images** (Yang et al., arXiv 2602.10425, Feb 2026).
  - Removes salient objects; Masked-Object-Hallucination (MOH) benchmark; DPO with these images.
  - **The closest work to MedScope's erasure design in the general domain.** It is not peer reviewed, and has no control edit and no held-out-editor test.
- **Context Blindness in DPO: Mitigating Object Hallucination in MLLMs via Context-Calibrated Preference Optimization** (arXiv 2608.12158, 2026). Extends the mDPO critique.
- **Learning from Fine-Grained Visual Discrepancies: In-Context Visual Contrastive Optimization** (arXiv 2605.31312, 2026).
- **Importance Sampling for Multi-Negative Multimodal DPO** (arXiv 2509.25717).
- **Anatomical Region-Guided Contrastive Decoding for Medical VLMs** (arXiv 2512.17189).
- **CheXPO: Preference Optimization for Chest X-ray VLMs with Counterfactual Rationale** (arXiv 2507.06959).
- **Counterfactual Segmentation Reasoning: Diagnosing and Mitigating Pixel-Grounding Hallucination** (arXiv 2506.21546).
- **AutoHallusion** (Wu et al.). Automatic object insertion or removal to induce hallucination. Recalled as Findings of EMNLP 2024, but not verified because the search budget ran out. Check before citing.

---

## 3. Which mechanism classes change true discrimination, not just bias or abstention?

**Lens.** Treat each method as changing either the **criterion** (how readily the model says "present") or the **sensitivity** (d′ or AUROC between real and lesion-absent evidence). ESG = P(absent|erased) − P(absent|control) cancels pure criterion shifts that act equally on both views. A method raises ESG only if it separates erased from control, which is sensitivity to the *specific* evidence.

| Mechanism class | Evidence for criterion or abstention effects | Evidence for a real sensitivity gain | Verdict for MedScope |
|---|---|---|---|
| **Contrastive and guided decoding** (VCD, ICD, SID, M3ID, IBD, PAI's text subtraction, CF-VQA's TIE) | **Strong.** Mirage (#10, NeurIPS 2025): POPE gains are explained by yes-ratio shift and the plausibility constraint; a yes-biasing prompt matches or beats them; no gains on CHAIR or MME; VCD hurts when the model already leans yes. CF-VQA, RUBi and LMH gains concentrate on yes/no questions and fall in-distribution (Teney #47) | None shown with a matched control. Detector-guided variants (HALC, MARINE, CAST) gain only when the *external* model has the evidence | **Expected not to raise ESG.** This matches MedScope's 270-policy result. The two together make a strong "decoding cannot create evidence" claim. Use one or two as baselines only |
| **Attention re-weighting and visual emphasis** (PAI, ClearSight, AGLA, VAR, CCA, IBD) | Evaluated on POPE and CHAIR without reporting yes-ratio or AUROC, so the same confound may apply | Indirect: CCA changes the architecture and retrains, so it could change sensitivity, but there is no minimal-pair evidence | Cheap ablations; low prior of success. Amplifying attention to image tokens cannot help when the image representation does not separate an inpainted lesion area from a real one |
| **Latent readout and representation editing** (DeCo, ProjectAway, VTI, Nullu) | Partly a criterion effect (Nullu removes prior directions) | **Medium-strong, indirect.** ProjectAway (#20) and DeCo (#8) show that *internal* signals in the same model separate real from hallucinated objects better than the output does. This is a "knows but does not say" readout gap, so better readout can raise sensitivity | **The most promising unexplored direction for MedScope.** It is directly testable: probe erased vs control at every layer on the held-out inpainter. If the probe AUROC beats the answer AUROC, a readout fix can raise ESG |
| **Preference and RL with text-only pairs** (RLHF-V, RLAIF-V, HSA-DPO, TL-DPO, HA-DPO, OPA-DPO) | mDPO (#25): multimodal DPO learns *unconditional* (language-only) preferences. OPA-DPO (#29): off-policy pairs are largely ignored under the KL constraint. Most gains are in long-form captioning (fewer object mentions, i.e. more conservative) | Little evidence of discrimination gains on yes/no | **Explains why MedScope's DPO and GRPO failed** without a perceptual cause. The algorithm optimised text preferences, and the cost reward rewards caution |
| **Preference with image-conditional or minimal-pair images** (mDPO, V-DPO, CHiP, BPO, POVID, MFPO, EMPO, SymMPO, S-VCO) | Generic rejected images (noise, crop, distortion; POVID, BPO, CHiP, mDPO) allow a "degraded image → absent" shortcut. Region-local noise (MFPO) and inpainting (EMPO) allow a "local edit footprint → absent" shortcut. None controls for it | **The best available evidence.** S-VCO (#34) improves vision-dependent minimal-pair benchmarks, which need discrimination; SymMPO (#33) and EMPO (#32) show image-side pairs beat text-only DPO | **The most relevant class, with one fatal gap:** no paper uses an edit-matched control image, so none can show its gain is not edit detection. MedScope's control edit is exactly what is missing |
| **Counterfactual and negative data** (LRV, HALVA, LURE, CSS) | LRV: negative *questions* shift the yes/no criterion through the positive:negative ratio. CSS: masked-region artifacts | CSS's V-CSS gives the only VQA-CP evidence that image counterfactuals help beyond question debiasing. Shrestha (#46) shows that related grounding gains survive *random* regions, which is evidence *against* true grounding | Plain SFT on counterfactual views (MedScope's strongest baseline) is CSS's analogue. It needs a random-region and control-region ablation (Shrestha-style) to show it is not regularisation |
| **Sensitivity supervision** (Teney gradient supervision #41; HINT and SCR, critiqued by #46) | HINT and SCR gains reproduced with random cues, so the effect was regularisation | GS (#41) improves OOD generalisation from minimal pairs; modest | Under-explored for VLMs (no VLM-scale paper found). It directly targets the quantity ESG measures (Framework B) |

**Bottom line.**
1. No published method in this strand has shown a sensitivity gain under a test that controls for edit artifacts.
2. The strongest positive evidence is indirect:
   - minimal-pair image-contrast training improves vision-dependent benchmarks (S-VCO; SymMPO, EMPO, MFPO);
   - in the same model, internal states discriminate better than outputs (ProjectAway, DeCo).
3. The strongest negative evidence:
   - Mirage for decoding;
   - mDPO and OPA-DPO for text-pair DPO;
   - Teney (Goodhart) and Shrestha for VQA-CP debiasing and grounding losses.

   Each shows that apparent gains came from changing the criterion or from regularisation.

---

## 4. Gaps no published work fills that MedScope could own

1. **Edit-matched control in counterfactual training *and* evaluation.**
   - Every image-side counterfactual method (CSS, POVID, BPO, CHiP, mDPO, MFPO, EMPO, HII-DPO, HallusionBench, AutoHallusion) compares *original* with *edited*.
   - None includes an equal-shaped edit that leaves the object in place.
   - So none can rule out "edit detected → say absent". ESG plus the control edit is new as an evaluation tool, and also as a *training anchor*.
2. **Held-out-editor generalisation.**
   - No paper found trains on edits from inpainter A and tests on inpainter B.
   - EMPO and HII-DPO use one editing pipeline throughout.
   - This is the counterfactual-data version of Teney's Goodhart critique (#47), and nobody has run it.
3. **Separating sensitivity from criterion in hallucination mitigation.**
   - Mirage did it for decoding after the fact, with yes-ratio.
   - No mitigation paper reports d′ or AUROC together with the criterion c on matched pairs.
   - MedScope can contribute a signal-detection reporting standard: ESG, yes-ratio, and d′ or AUROC on erased vs control, by inpainter.
4. **"Knows but does not say" under edits.**
   - ProjectAway and DeCo show internal states beat outputs for COCO hallucinations.
   - Nobody has tested whether this holds for *inpainted removal*, where the encoder may itself be fooled.
   - Nobody has tested it in medical images, or with a held-out editor.
   - Both outcomes are publishable. A readout gap leads to a readout method; a perceptual gap is a negative result that explains all eight failures at once.
5. **Presupposition prior as a separate quantity.**
   - VQA-CP methods model priors per question type. LVLM work models co-occurrence priors (LURE, POPE-popular or adversarial).
   - The *pragmatic presupposition* prior has not been isolated: asking "Is there a polyp?" itself raises P(yes).
   - It could be measured with matched questions about a finding that cannot be present.
6. **Small-model (≤4B) LoRA regime with image-conditional preference.**
   - mDPO tests a ~3B model; most others use 7-13B with full or large-LoRA tuning.
   - The 4B + LoRA regime with image-conditional and on-policy pairs is untested.
7. **Medical image-side counterfactual alignment.**
   - The medical work found is question-side (DeCoCT) or decoding-only (CAST, arXiv anatomical contrastive decoding, CheXPO rationales).
   - No peer-reviewed medical paper trains with image-side lesion-removal pairs and tests on held-out-editor erasures.

---

## 5. Candidate frameworks for MedScope

**Shared notation.**
- Each lesion image comes as a triplet: **R** (real), **E** (erased), **C** (control edit). L denotes lesion-free images.
- ℓ(x) is the log-odds of "present" for the presence question.
- **Inpainters** are split into training inpainters 𝓘_tr = {A, B, …} and the held-out inpainter 𝓘_ho.

**Primary endpoint for every framework.**
- ESG on held-out-inpainter erasures, with a pre-registered margin over the plain counterfactual-SFT baseline.
- Also reported: d′ or AUROC between E and C, criterion c, real-lesion sensitivity on R, and false-positive rate on L.

**Compute assumptions** (one A100 80GB)
- Qwen3.5-4B in bf16 with LoRA plus gradient checkpointing.
- Plain counterfactual SFT costs **S** GPU-hours. Assume S ≈ 2–6 h for 10–20k triplets per epoch; replace with MedScope's measured value.

### Framework A — Control-Anchored Conditional Preference (CACP): image-side preference whose negative is the erasure and whose anchor is the control edit

**Mechanism**
- Hold the response fixed and vary only the image (mDPO-style conditional preference).
  - The pair "present" | C is preferred over "present" | E.
  - The pair "absent" | E is preferred over "absent" | C.
  - This is symmetric, as in SymMPO and S-VCO.
- Because C and E carry the *same edit footprint* (shape, size, inpainter), the only signal that separates them is the lesion. The edit-detection shortcut has zero gradient by construction.
- Additional terms:
  - an R↔C invariance term, a small KL on ℓ(R) vs ℓ(C), so the control edit does not change the answer;
  - a reward anchor (as in mDPO) so that likelihoods do not collapse;
  - on-policy sampling for the text side (as in OPA-DPO).
- Each batch mixes editors from 𝓘_tr.

**Closest published work and the difference**
- mDPO (#25), SymMPO (#33), S-VCO (#34), MFPO (#31), EMPO (#32).
- All of them contrast *original vs edited* (or noised). None uses an edit-matched control as the positive anchor, and none evaluates on a held-out editor.
- MedScope's earlier DPO is described as DPO on counterfactual views. If those pairs differed in *text* under one image, mDPO and OPA-DPO predict that it failed. CACP is the image-conditional, artifact-controlled version that has not been run.
- **Important:** confirm what MedScope's "paired-view consistency loss" actually anchored on. If it already used C as the anchor, CACP is new only through the image-conditional preference and on-policy parts. Its expected value is then lower.

**Falsifiable prediction**
- Held-out-inpainter ESG ≥ SFT-baseline ESG + 0.10 absolute, with the 95% bootstrap CI excluding 0. d′(E vs C) should increase, while |Δc| < 0.1 and R sensitivity stays ≥ 0.90.
- **Diagnostic ablation:** replace C with R as the anchor (the standard "original vs edited" design). Prediction: in-inpainter ESG matches CACP, but held-out-inpainter ESG drops by ≥ 0.05. This would show the anchor is what transfers.
- **Kill criterion:** if CACP and the R-anchored version are within 0.03 on held-out ESG, the control anchor adds nothing and the bottleneck is perception (go to Framework C's diagnosis).

**Compute.** Roughly 2× S: two forward passes per pair plus a reference model, which can share LoRA-disabled weights. On-policy sampling of one token is cheap. **About 5–15 A100-hours per run;** 3 seeds × 2 ablations ≈ 1.5–4 GPU-days.

### Framework B — Edit-Orthogonal Gradient Supervision (EOGS): supervise *where* the model is sensitive, not what it outputs

**Mechanism**
- Extend Teney's gradient supervision (#41) to VLMs with a control-edit constraint. Let g = ∇_x ℓ(R), the input gradient taken at the vision-encoder patch embeddings rather than pixels, to keep it cheap.
- **Alignment loss:** maximise cos(g, e_R − e_E), the embedding difference caused by erasure.
- **Orthogonality loss:** penalise |cos(g, e_R − e_C)|, so the model's sensitivity is orthogonal to the control-edit difference, which is the artifact direction.
- Add standard SFT cross-entropy on R, E, C and L.
- This trains *sensitivity to the lesion and insensitivity to edits* directly, which is ESG's mechanism. Output-level losses (SFT, DPO, consistency) only constrain the endpoints.

**Closest published work and the difference**
- Teney GS (#41): text and VQA-CP features, no artifact control, no LLM-scale VLM.
- HINT and SCR, which were shown by Shrestha (#46) to work through regularisation.
- New here: (i) the orthogonality-to-control term; (ii) application to a generative VLM; (iii) a held-out-editor test.

**Falsifiable prediction**
- Held-out ESG ≥ SFT + 0.08. The gradient-attribution mass inside the lesion mask goes up on *held-out-editor* E images.
- **Shrestha check:** replace e_R − e_E with a random-region or control-region difference. Prediction: ESG gain < 0.02. If the random version gains as much, the effect is regularisation and the method claim fails.

**Compute.** Double backprop through the 4B LLM to the patch embeddings is about 2.5–3× S. Restrict it to the last N LLM layers plus the projector, or use a finite-difference surrogate ℓ(e_R + ε·(e_R − e_C)) − ℓ(e_R), to stay near 1.5×. **About 8–20 A100-hours per run.**

### Framework C — Probe-First Evidence Readout (PFER): find where erased-vs-control is separable, then read it out

**Step 1 (diagnosis, cheap, publishable either way)**
- Extract hidden states for all R, E, C and L images on the frozen base model and on the SFT model:
  - vision-encoder layers;
  - projector output;
  - every LLM layer at the image tokens and at the last question token.
- Train linear probes for E vs C (and R vs E) on 𝓘_tr. Test them on 𝓘_ho.
- Compare the probe AUROC with the AUROC of ℓ (the output).

**Step 2 (method, only if a readout gap exists)**
- **Evidence head:** a lightweight head on the best layers (attention-pooled image tokens plus question token).
  - Trained with the CACP-style control-anchored loss.
  - Its logit is added to ℓ through a learned gate (this generalises DeCo's layer mixing).
  - Alternatively, a ProjectAway- or VTI-style steering vector built from the mean E−C difference.
- The whole pipeline stays one model. This is a single readout path, not an arbiter over separate agents.

**Closest published work and the difference**
- DeCo (#8), ProjectAway (#20), VTI (#18), Nullu (#19).
- They work on COCO captioning without edit controls. They also *assume* the internal signal exists; PFER *tests* that assumption under held-out-editor erasure first.

**Falsifiable prediction**
- (i) If the best-layer probe AUROC on 𝓘_ho exceeds the output AUROC by ≥ 0.05, the evidence head raises held-out ESG by ≥ 0.07 over SFT.
- (ii) If no layer exceeds the output AUROC by more than 0.02, *no* readout-only method can raise ESG. That would be a principled explanation for MedScope's eight failed attempts, and would shift the work to the encoder or perception side (Framework D).

Both outcomes are pre-registerable.

**Compute**
- Feature extraction: about 1–2 A100-hours for around 20k images × 4 conditions; storage is the main cost, so pool the image tokens.
- Probes: minutes on CPU or GPU.
- Evidence head: well under S, about 1–3 hours.
- **Total about 0.5 GPU-day.** Best value per GPU-hour of all five frameworks.

### Framework D — Editor-Environment Invariance (EEI): treat inpainters as environments

**Mechanism**
- Generate E and C with K ≥ 3 different inpainters. Families should be diverse, e.g. a fast-Fourier-convolution inpainter, a latent-diffusion inpainter, and a classical patch-based or exemplar method.
- Each inpainter is one environment. Train with:
  - (i) a risk-variance penalty across environments (V-REx style) on the E-vs-C discrimination loss;
  - (ii) a gradient-reversal editor-ID adversary on pooled image-token features, using C images only (the lesion is present, so editor identity is the only signal), so the features carry no editor fingerprint.
- Combine with A or B as the base loss.

**Closest published work and the difference**
- Unshuffling (Teney et al., ICCV 2021, recalled; not in the ledger), CSS (#40), GGE's visual-bias observation (#43).
- No paper treats *counterfactual generators* as environments, or adversarially removes editor fingerprints.

**Falsifiable prediction**
- The gap between in-inpainter and held-out-inpainter ESG shrinks by ≥ 50% compared with SFT on the same K editors.
- The editor-ID probe on C features drops to near chance (≤ 1/K + 0.05).
- If held-out ESG does not rise even though the fingerprint is removed, the encoder cannot see inpainted absence, which agrees with a negative Framework C result.

**Compute**
- Inpainting K × N images: the fast inpainter takes minutes; a diffusion inpainter takes about 2–4 s per image, so about 6–12 GPU-hours per 10k images.
- Training: about 1.3× S.
- **About 1–1.5 GPU-days in total, including data generation.**

### Framework E (control / reporting overlay) — SDT-decomposed ESG and a presupposition-neutral prior test

Not a mitigation method on its own. It is the evaluation backbone that makes A–D credible, and it answers the Mirage, Goodhart and Shrestha critiques up front.

**Reporting.** For every method, report:
- ESG, d′ or AUROC (E vs C), and criterion c;
- R sensitivity, L false-positive rate, and yes-ratio;
- each of these separately for the training inpainters and the held-out inpainter.

**Presupposition prior test.** Ask a matched question about a finding that is implausible for the modality ("Is there a polyp?" on a fundus image). Also ask a neutral form ("What abnormalities, if any, are present?"). This isolates the presupposition prior.

**Mandatory baselines.**
- A yes-biasing or no-biasing prompt and a logit-offset (the Mirage spurious baselines).
- A CF-VQA-style prior subtraction (the expected criterion-only shift).
- A random-region version of the winning loss (the Shrestha check).

**Prediction.** Every one of the 8 earlier attempts and the 270 policies moves c with |Δd′| < 0.1. Only methods that pass d′ > SFT + 0.15 on 𝓘_ho count as discrimination gains.

**Compute.** Evaluation only: a few A100-hours.

### Recommended single framework

**"Edit-Matched Counterfactual Evidence Learning" = C (diagnosis) → A (+ optional B term) under D (inpainter environments), reported with E.**

Run C first; it takes about half a GPU-day.
- **If a readout gap exists:** train the A loss (control-anchored, image-conditional, symmetric, on-policy) with the D editor-environment penalty, applied through C's evidence-head pathway.
- **If no gap exists:** report this as the principled explanation for all eight failures. Move to the encoder-side version, which is A/B with vision-encoder LoRA under D. Note that vision-encoder LoRA alone already failed; the new parts are the control anchor and the editor invariance.

**Novelty claim vs the literature.** The first hallucination-mitigation method whose training signal and evaluation both cancel the counterfactual-edit artifact (via the matched control edit), and which is validated on a held-out counterfactual generator with sensitivity and criterion reported separately. Every image-side preference or counterfactual method found in this search (CSS → POVID, BPO, CHiP, mDPO, MFPO, EMPO, S-VCO, SymMPO, HII-DPO) lacks at least two of these three properties.

**Total budget.** About 4–6 A100-days for the full set (C, A with ablations, D with data generation, E evaluation, 3 seeds).
