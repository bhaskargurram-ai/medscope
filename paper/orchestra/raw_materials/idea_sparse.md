## Problem Statement

Medical vision–language models (VLMs) are asked closed questions such as "Is there a polyp?" or "Is there a breast mass?". In the image–text data these models learn from, a question that names a finding is itself strong evidence that the finding is present, so a model can answer from the question rather than from the pixels. A confident report of a finding that is not in the image is the most dangerous error a clinical assistant can make.

Standard medical VQA benchmarks (VQA-RAD, SLAKE, PathVQA) mostly ask about findings that are present, so leaning on the question scores well. Hallucination benchmarks (POPE, CARES, ProbMed, MedVH, MedHEval, Med-HallMark) change the question or the answer while the image stays the same, so they cannot tell whether a correct "No" came from the image or from a prior about the question. Testing whether an answer depends on the image needs image pairs that differ only in the finding; such pairs cannot be acquired clinically, and image edits introduce their own confound: a model may learn to notice *that an image was edited* rather than *whether the lesion is there*.

Two further gaps make results in this area hard to trust:
1. **Abstention looks like improvement.** A model (or a decision rule on top of it) can reduce false claims simply by saying "absent" or "refer" more often. Aggregate utility then rises without the model getting any better at telling an erased lesion from a present one. Published mitigation methods rarely separate discrimination from a change of threshold.
2. **The counterfactual labels themselves are rarely checked.** Automatic lesion erasure may leave residual or secondary signs of the finding; almost no counterfactual work in medical imaging asks physicians whether the finding is still visible.

## Core Hypothesis

We hypothesize that evidence sensitivity, whether a model's answer follows the visible evidence or the question, can be measured and attributed rigorously only with a framework that (a) varies the image while holding the question fixed, (b) controls every property of the edit except the presence of the finding (same tool, same shape, and, new here, the same place), (c) tests on editing tools never seen in training, (d) checks the erasures with physicians, and (e) separates real discrimination from a shift of the answer threshold. Under such a framework, we expect that:
- frontier general VLMs claim erased findings at high rates whatever the prompt;
- a small model trained on automatically built counterfactual views acquires a much stronger evidence-gated disposition;
- the methods that look like further improvements (preference optimisation, consistency losses, reinforcement learning, multi-agent verification, abstention rules, test-time evidence) mostly move the threshold rather than the discrimination, and the framework can show where the remaining limit lies (perception, in the visual representation).

## Proposed Methodology (High-Level Technical Approach)

We propose a **Counterfactual Evidence Framework** with five parts, plus a trained reference agent built with it.

**1. Counterfactual views with symmetric controls (data).** From public segmentation datasets, for each case (image, expert lesion mask, a question whose answer depends on the lesion):
* *Original* (unchanged; expected: the answer with a box on the lesion).
* *Target removal*: the lesion mask dilated by 5 pixels is inpainted (LaMa); expected: "absent".
* *Random-removal control*: the same dilated shape moved elsewhere on tissue and inpainted with the same tool; no lesion pixel changes; expected: the original answer.
* *Degraded* (blur, noise, low resolution, wrong anatomy; expected: ask to clarify).
* *Natural negatives*: unedited lesion-free images with exactly the reward of target removal, so answering "absent" to anything that looks edited earns nothing overall.
* Automatic quality control: contrast-based erasure check, an edit detector, adversarial filtering of texture shortcuts, patient- or near-copy-group splits.

**2. Metrics that separate evidence from threshold.**
* Evidence Sensitivity Gap: ESG = P(absent or refer | erasure) − P(absent or refer | control edit). It is zero for every constant policy and, in expectation, for any policy that ignores the image or reacts to both edits alike.
* Reported with erased-lesion claims, healthy-image claims, accuracy on answerable views (CCR), grounding, and a clinical cost-matrix utility.
* **New in this version:** discrimination (AUROC of erased vs control, and of erased vs a same-site control) reported separately from denial rates.
* **An abstention ceiling (simple proposition):** for any decision policy π that sees only a set of signals S, ESG(π) ≤ TV(S | erasure, S | control), the total-variation distance between the two signal distributions (data-processing inequality). Abstention rules built on existing signals therefore cannot raise ESG beyond what those signals already separate, while they can raise utility through the referral reward.

**3. A same-site control (new).** The benchmark's control edit is always elsewhere, while the erasure is always at the lesion, so "edited where the question points" could be learned as "absent". We add a **ring control**: the same tool fills an area-matched ring starting 2 pixels outside the lesion, leaving the lesion intact. With the restored view (the erasure with the lesion's own pixels put back) and a half-erasure (graded evidence), this tests whether a model's denials follow the edit's location or the evidence.

**4. Held-out editing tools.** Training uses LaMa and tissue transplant only; testing adds TELEA (classical PDE inpainting) and Stable Diffusion inpainting. A tool-family variant (blur, mean-fill, pixel-shuffle fills) tests whether making the tool uninformative during training transfers to unseen tools.

**5. Physician verification and representation probes.**
* A blinded reader study asks physicians, per image, whether it was edited and whether the finding is present (unedited lesion, erased, control-edited and lesion-free images). Results are re-scored on reader-clean erasures.
* Layer-wise linear probes on the model's hidden states (last prompt token, mean of image tokens) test whether the model's internal features separate erased from intact lesions better than its answers do (a read-out gap) and how much the untrained base model already separates.

**6. Pre-registration and a staged screening funnel.** Every confirmatory check had its arms, endpoints, minimum effects and decision rule committed to a public repository before the arms existed. Cheap screens (hundreds of decision policies on validation data, split into halves) precede expensive training runs.

**Reference agent (MedScope-4B).**
* Qwen3.5-4B with LoRA (vision encoder frozen) and two image tools (zoom, contrast window), acting in a fixed agent protocol: brief reasoning plus one tagged JSON action per turn (zoom, window, answer with box and confidence, refer, clarify).
* Trained on trajectories derived from dataset labels alone. Stage 1: supervised fine-tuning on counterfactual views. Stage 2: rejection-sampling fine-tuning. Stage 3: general-VQA replay.
* Selected by a pre-registered validation rule and tested once against nine frontier and six open VLMs through the identical agent loop.

**Methods tested within the framework (all pre-registered, all against matched controls):**
* matched vs unmatched control edits;
* removal-based DPO (the closest published method) and DPO on top of the recipe;
* a control-matched counterfactual consistency loss (CMCC);
* more adapter capacity, and LoRA on the vision encoder (two learning rates);
* GRPO on the cost-matrix reward;
* a counterfactual multi-agent reader (direct reader, question-blind reader, lesion segmenter, erase-and-re-ask verifier, trained arbiter; two versions);
* 270 abstention/decision policies on stored and new test-time evidence;
* tool-family counterfactual training with and without the paired-view loss.

## Expected Contribution

* **A measurement framework for evidence sensitivity in medical VLMs:**
  * counterfactual views with a matched control and symmetric lesion-free negatives;
  * a same-site ring control;
  * held-out editing tools;
  * physician verification of the counterfactual labels;
  * discrimination reported apart from threshold;
  * an abstention ceiling;
  * representation probes that locate where evidence is lost.

  None of the closest published works combines these. Closest:
  * HEAL-MedVQA / LobA (IJCAI 2025): chest X-ray region swap, no control edit, no reader check, no held-out editor.
  * MMedPO (ICML 2025): lesion-region noise in preference pairs, accuracy only.
  * S-VCO (ACL 2025), EMPO (EMNLP 2025), MFPO (IJCAI 2025): minimal-pair image preference training on natural images.
  * RadEdit (ECCV 2024): diffusion editing for stress tests, no readers.
  * Agarwal et al. (CVPR 2020): invariant vs covariant VQA edits, natural images.
  * ROAD (ICML 2022): removal-based evaluation leaks the label through the removal.
* **An empirical finding about frontier models:** nine frontier VLMs claim about half of erased findings under every prompting condition tested, while a 4B agent trained on automatically built counterfactual views claims about one in ten. This is qualified by the reader study: erasure is reader-supported for colonoscopy, where the frontier models still claim 45% of erased findings.
* **A pre-registered negative map:** across twelve trained or system arms and 270 decision policies, every method that improved utility did so by moving the answer threshold, not the separation of erased from present lesions. The model's internal features separate them no better than its answers, and the untrained base model's features almost as well. The remaining limit is perception (about 15–20% of real lesions are missed on unedited images, and every miss also lowers ESG), not the training objective.
* **A transparent account of failures:** a complete miss of pneumothorax on a fresh external set traced to training coverage; physicians still seeing a finding on about 40% of erasures outside colonoscopy; the limits this places on what ESG can certify.
