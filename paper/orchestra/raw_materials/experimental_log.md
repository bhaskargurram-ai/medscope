## 1. Experimental Setup

All numbers below come from the study's public repository (github.com/bhaskargurram-ai/medscope): its results log, pre-registration documents and stored per-view model outputs. Earlier version of this study: arXiv:2611.13006 (preprint v1.0, 8 November 2026). Results added after that version are marked **[new]**.

### 1.1 Task and agent protocol
* One image and one question whose answer depends on a lesion per episode.
* Each turn: brief reasoning plus exactly one tagged JSON action:
  * `zoom` (box on the original image, integer coordinates 0–1000, returns the crop);
  * `window` (centre and width on a 0–255 scale, returns the contrast-adjusted image);
  * at most three tool calls per episode;
  * `answer` (optional evidence box and stated confidence);
  * `refer` (usable image, cannot decide);
  * `clarify` (unusable image or wrong anatomy).
* When the asked finding is not visible the model must say so: "No" to "Is there…?", "Yes" to "Is … healthy?", "No abnormality" to an open question.
* Every model receives the same prompt, tools and turn structure.

### 1.2 Counterfactual views
* **Original:** unchanged; expected: correct answer, box on the lesion.
* **Target removal:** lesion mask dilated by 5 px, inpainted (LaMa); expected: absent.
* **Random removal (control):** the same dilated shape at a random foreground position not touching the dilated lesion, same tool; no lesion pixel changes; expected: original answer.
* **Degraded:** Gaussian blur (σ = max(h,w)/40), Gaussian noise (σ = 60), 8× down/up-sampling, JPEG, motion blur, or an image of another imaging type; expected: clarify.
* **Natural negative:** unedited lesion-free image; expected: absent, with exactly the reward of target removal.
* Lesions under 20 px or over 20% of the image are excluded.
* Training also uses lesion-insertion views (a real lesion moved into a healthy training image) and a second erasure tool, tissue transplant (Poisson-blended tissue from the same image), for half the cases.
* **Automatic quality control (no human checks):**
  * the erased region's contrast against a 6–14 px ring must be ≤ max(1.0, 0.35 × contrast before), and an edit detector must score it below 0.5;
  * no lesion pixel may change in random removal;
  * no near-copies of training images (perceptual hash + pixel correlation);
  * adversarial filtering until a texture classifier separates target from random edits at AUC ≤ 0.6 (test 0.56); a hand-crafted shortcut classifier on training views reached AUC 0.59.

### 1.3 Cost matrix (reward per view; also the selection reward)

| View | Correct / absent answer | Wrong, or claims finding | Refer | Clarify |
| :--- | :--- | :--- | :--- | :--- |
| Original, random removal | +1.0 | −2.0 (−4.0 critical) | −0.3 | −0.3 |
| Target removal, natural negative | +1.0 | −2.0 | +0.5 | −0.5 |
| Degraded | +0.25 | −2.0 | 0.0 | +0.5 |

* Correct answer on an original/random-removal view with box IoU ≥ 0.3 earns +0.5 more (boxes over half the image earn nothing).
* Unparseable output scores −1; each tool call beyond the first costs 0.05.
* The matrix was fixed before any experiment and is not clinician-elicited.

### 1.4 Metrics
* **ESG** = P(absent answer or refer | target removal) − P(absent answer or refer | random removal).
* **Strict ESG**: explicit absent answers only.
* **Erased-lesion claims** = P(claims finding | target removal).
* **Healthy-image claims** = P(claims finding | natural negative).
* **CCR**: share of answerable views (original ∪ random removal) answered correctly.
* **Grounded accuracy**: correct with IoU ≥ 0.3.
* **Net utility**: mean reward over all views.
* **[new]** Denial rates and AUROC computed separately (discrimination vs threshold).

### 1.5 Model and training (MedScope-4B)
* **Base and adapter:** Qwen3.5-4B, LoRA rank 16, α = 32, dropout 0.05, all linear layers of the language model; vision encoder frozen.
* **Trajectories from labels alone:**
  * optional zoom on a jittered box around the lesion (always for lesions under 2% of the image);
  * windowing on 30% of grey-scale images;
  * the expected final action with short template reasoning;
  * half the questions reworded with one of four training paraphrases; three further paraphrases reserved for testing.
* **Stage 1 (SFT):** 16,000 views, one pass (3,706 optimiser steps), lr 2e-4.
* **Stage 2 (rejection-sampling fine-tuning):** k = 4 samples at temperature 1.2; best successful episode kept, hard views repeated ×3; lr 5e-5.
* **Stage 3 (general-VQA replay):** 5,000 views mixing MedScope views with VQA-RAD/SLAKE/PathVQA training-split questions; lr 5e-5.
* **Pre-registered selection** (committed 1 Nov 2026 before any v4 data or model): stage 3 selected if validation net utility U3 ≥ U2 − 0.02 and healthy-image claims H3 ≤ H2 + 0.02.
  * Validation (540 cases, 1,473 views): U/H = 0.585/13.6% (stage 1), 0.610/12.7% (stage 2), 0.613/7.7% (stage 3).
  * Stage 3 = MedScope-4B was tested once on every test set; nothing tuned afterwards.
* **Compute:** one NVIDIA A100 40 GB per stage, about 4 h each (later pilots on A100 80 GB and RTX PRO 6000 96 GB). Software: PyTorch 2.11, Transformers 5.22.1, PEFT 0.21.2. Frontier API runs on the main test cost US$132; all 48 API runs US$373.

### 1.6 Data
* **Training and validation sources:**
  * SLAKE CT/MRI; Kvasir-SEG (with HyperKvasir normal landmarks as lesion-free images); ChestX-Det (from NIH ChestX-ray14); BUSI breast ultrasound; TCGA-LGG brain MRI (FLAIR).
  * 1,508 SLAKE and colonoscopy cases plus 1,792 chest X-ray, breast ultrasound and brain MRI cases after checks; 690 lesion-free images from the latter three.
  * Validation: 540 cases (1,473 views).

**Main (internal) test set:**

| Source | Imaging | Cases with mask | Lesion-free | Split level |
| :--- | :--- | :--- | :--- | :--- |
| SLAKE | CT / MRI | 17 | 90 | near-copy groups |
| Kvasir-SEG + HyperKvasir | Colonoscopy | 83 | 91 | near-copy groups |
| ChestX-Det | Chest X-ray | 41 | 50 | patient |
| BUSI | Breast ultrasound | 42 | 15 | near-copy groups |
| TCGA-LGG | Brain MRI (FLAIR) | 36 | 42 | patient |
| **Total** | | **219** | **288** | 507 cases, 1,115 views (degraded views for 170 of 219) |

**Further test sets:**

| Test set | Cases | Sources (cases) | Purpose |
| :--- | :--- | :--- | :--- |
| External centres | 169 | CVC-ClinicDB (40), QaTa-COV19 (20), BUS-BRA (45), BraTS-Africa 2023 (64, 50 tumour-free slices) | New scanners, populations |
| Fresh internal | 76 | ChestX-Det unused test-split patients (36 lesion, 40 lesion-free) | Confirmatory |
| Fresh external | 316 | BraTS 2023 meningioma (82), BUS-UCLM (99), SIIM-ACR pneumothorax (96), ETIS-LaribPolypDB (39) | Confirmatory, new sources |
| Held-out wordings | 373 | Main test with three test-only paraphrases | Question wording |
| Standard VQA | 1,051 | VQA-RAD test (451), SLAKE English test (300), PathVQA test (300) | No regression |
| Held-out editing tools | 125 / 219 | Main-test erasures and controls remade with TELEA and Stable Diffusion inpainting (and tissue transplant) on the same masks | Unseen tools |

* **Leakage checks:**
  * Every unedited image of every split was hashed (64-bit difference hash) across 6,849 images.
  * Exactly one image recurs: a validation lesion-free ChestX-Det image equals one SIIM fresh-external pneumothorax case. Excluding it changes fresh-external ESG by +0.002, CCR by +0.003 and net utility by +0.007.

### 1.7 Models compared
* **Frontier**, evaluated 31 October 2026 through public APIs, identical agent loop, provider defaults:
  * OpenAI gpt-6-sol, gpt-6-astra, gpt-6.1-sol;
  * Anthropic Claude Fable 5.1, Claude Opus 5.5, Claude Sonnet 5.5;
  * Google gemini-4-argon, gemini-3.1-pro-preview, gemini-3.8-flash.
* **Open** (bf16, greedy): Qwen3.5-4B (base), MedGemma 1.5 4B, Lingshu-7B, HuatuoGPT-Vision-7B, Qwen2.5-VL-7B, Qwen3-VL-8B.
* **Trivial policies:** always claim, always absent, always refer.
* **Images:** all models see PNGs with the long side at most 768 px.

### 1.8 Statistics
* 95% CIs from 2,000 bootstrap resamples of cases (all views of a case resampled together).
* Model comparisons: paired bootstrap; p = twice the smaller tail proportion.
* Primary outcomes: ESG, erased-lesion claims and net utility against each of nine frontier models (27 comparisons). All survive Bonferroni at 0.05/27.
* Resampling whole patients or near-copy groups widens intervals by ≤ 0.01 (main test) and ≤ 0.03 (fresh external).
* Seeds: mean ± sd over three seeds.

## 2. Raw Numeric Data

### Table 1: Main test (507 cases, 1,115 views; agent prompt for every model)
Erased % = claims on 219 erased views; Healthy % = claims on 288 unedited lesion-free views; CCR over 438 answerable views.

| Model | CCR | ESG | Erased % | Healthy % | Net utility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MedScope-4B** | 0.849 | **0.758** [0.701, 0.815] | **9.6** [6.1, 13.7] | **7.6** [4.8, 10.9] | **0.732** [0.649, 0.813] |
| gemini-4-argon | 0.874 | 0.470 | 41.1 | 9.0 | 0.565 |
| Claude Sonnet 5.5 | 0.870 | 0.402 | 48.4 | 16.7 | 0.381 |
| gemini-3.1-pro-preview | 0.849 | 0.384 | 51.6 | 26.7 | 0.306 |
| gpt-6-sol | 0.829 | 0.342 | 51.6 | 25.7 | 0.261 |
| Claude Fable 5.1 | 0.856 | 0.342 | 52.1 | 23.3 | 0.255 |
| Claude Opus 5.5 | 0.863 | 0.329 | 53.9 | 23.6 | 0.358 |
| gpt-6.1-sol | 0.888 | 0.324 | 58.9 | 30.9 | 0.276 |
| gpt-6-astra | 0.886 | 0.306 | 58.9 | 27.8 | 0.309 |
| gemini-3.8-flash | 0.868 | 0.269 | 61.6 | 27.8 | 0.263 |
| Lingshu-7B | 0.527 | 0.416 | 32.0 | 12.5 | −0.249 |
| Qwen3.5-4B (base) | 0.758 | 0.338 | 42.0 | 19.4 | 0.134 |
| Qwen3-VL-8B | 0.553 | 0.297 | 12.8 | 12.5 | 0.186 |
| MedGemma 1.5 4B | 0.674 | 0.283 | 54.3 | 24.0 | −0.255 |
| HuatuoGPT-Vision-7B | 0.498 | 0.265 | 30.1 | 22.9 | −0.426 |
| Qwen2.5-VL-7B | 0.144 | 0.146 | 5.5 | 24.7 | −0.742 |
| Always claims the finding | 1.000 | 0.000 | 100 | 100 | −0.478 |
| Always says absent | 0.000 | 0.000 | 0 | 0 | −0.848 |
| Always refers | 0.000 | 0.000 | 0 | 0 | 0.110 |

**Paired differences, MedScope-4B minus model:**
* **Against each frontier model:**
  * ESG +0.288 to +0.489, all p<0.001 (gemini-4-argon +0.288 [0.208, 0.367]);
  * erased-lesion claims −0.315 to −0.521, all p<0.001;
  * net utility +0.168 to +0.477, all p<0.001;
  * CCR differences −0.039 to +0.021, all p≥0.12 (intervals reach −0.09; equivalence not established);
  * healthy-image claims lower than eight of nine (p≤0.001); vs gemini-4-argon −0.014, p=0.59.
* **Against the base model:** ESG +0.420 [0.338, 0.498].
* **Against MedGemma 1.5 4B:** ESG +0.475.
* **Ranking reversal:** ranking by erased-lesion claims alone prefers Qwen2.5-VL-7B (5.5%, ESG 0.146) to MedScope-4B.
* **Degraded views:** MedScope-4B asks to clarify on all 170 of 170.

### Table 2: Main test by imaging type (ESG / erased-lesion claims fraction / net utility)

| Imaging (cases) | MedScope-4B | gemini-4-argon | Claude Opus 5.5 | gpt-6-astra |
| :--- | :--- | :--- | :--- | :--- |
| Colonoscopy (174) | 0.95 / 0.01 / 1.06 | 0.69 / 0.31 / 0.83 | 0.57 / 0.40 / 0.53 | 0.40 / 0.58 / 0.40 |
| Brain MRI (78) | 0.75 / 0.14 / 0.75 | 0.42 / 0.47 / 0.56 | 0.31 / 0.61 / 0.51 | 0.50 / 0.31 / 0.43 |
| Breast ultrasound (57) | 0.74 / 0.14 / 0.78 | 0.40 / 0.48 / 0.53 | 0.29 / 0.62 / 0.40 | 0.12 / 0.83 / 0.28 |
| Chest X-ray (91) | 0.51 / 0.17 / 0.40 | 0.20 / 0.49 / 0.21 | −0.05 / 0.66 / −0.12 | 0.15 / 0.66 / 0.14 |
| SLAKE CT/MRI (107) | 0.47 / 0.12 / 0.22 | 0.35 / 0.41 / 0.38 | 0.24 / 0.59 / 0.32 | 0.29 / 0.47 / 0.17 |

### Table 3: Stage-1 training arms on the main test (507 cases; three-seed arms mean ± sd)

| Arm | CCR | ESG | Erased % | Healthy % | Net utility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Qwen3.5-4B, with counterfactual views (3 seeds) | 0.871 ± 0.022 | 0.741 ± 0.019 | 13.2 ± 3.2 | 13.9 ± 4.0 | 0.684 ± 0.021 |
| Qwen3.5-4B, without (3 seeds) | 0.955 ± 0.008 | 0.279 ± 0.107 | 67.6 ± 11.9 | 35.9 ± 3.9 | 0.341 ± 0.090 |
| Without, "absent" share matched (seed 0) | 0.945 | 0.215 | 73.5 | 31.6 | 0.321 |
| Erasures only (seed 0) | 0.788 | 0.708 | 6.8 | 5.9 | 0.667 |
| Control edits only, matched (seed 0) | 0.897 | 0.744 | 15.1 | 11.8 | 0.727 |
| Control edits only, unmatched (seed 0) | 0.904 | 0.753 | 15.1 | 12.5 | 0.739 |
| Without, then removal-based DPO (3 seeds) | 0.903 ± 0.014 | 0.661 ± 0.037 | 24.2 ± 5.3 | 19.4 ± 4.3 | 0.637 ± 0.033 |
| MedGemma 1.5 4B, with counterfactual views | 0.806 | 0.721 | 7.8 | 5.9 | 0.698 |
| MedGemma 1.5 4B, without | 0.947 | 0.374 | 57.5 | 31.6 | 0.409 |
| MedGemma 1.5 4B, untrained | 0.674 | 0.283 | 54.3 | 24.0 | −0.255 |

* **Recipe vs without counterfactual views, per seed:** ESG +0.525, +0.539, +0.324 (all p<0.001).
* **"Absent" share matched:** ESG difference +0.521 [0.440, 0.600].
* **MedGemma replication:** with vs without counterfactual views +0.347 [0.276, 0.425].
* **Stages 2–3 vs stage 1 on the main test:** net utility +0.040 (p=0.15), ESG +0.023 (p=0.39).
* **External centres (three seeds), with vs without:** ESG 0.622 ± 0.030 vs 0.389 ± 0.043.

### Table 4: 2×2 factorial of training-only components (stage 1, seed 0; main test; denial after a Telea edit elsewhere on 125 cases, Telea never used in training)

| Control edits | Insertions | CCR | ESG | Erased % | Healthy % | Denies intact lesion after Telea edit % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| no | no (erasures only) | 0.788 | 0.708 | 6.8 | 5.9 | 43.2 |
| no | yes | 0.806 | 0.735 | 7.3 | 11.1 | 43.2 |
| yes | no | 0.897 | 0.744 | 15.1 | 11.8 | 16.0 |
| yes | yes (recipe) | 0.847 | 0.735 | 11.9 | 9.4 | 23.2 |

### Table 5: Edited views by inpainting tool, 125 cases (ESG / erased-lesion claims %)

| Model | LaMa (training) | Transplant (training) | Telea (unseen) | Stable Diffusion (unseen) |
| :--- | :--- | :--- | :--- | :--- |
| MedScope-4B | 0.752 / 7.2 | 0.720 / 8.0 | 0.664 / 7.2 | 0.640 / 17.6 |
| gemini-4-argon | 0.536 / 32.8 | 0.488 / 32.8 | 0.560 / 8.8 | 0.392 / 40.0 |
| Claude Opus 5.5 | 0.376 / 45.6 | 0.264 / 56.8 | 0.296 / 41.6 | 0.352 / 46.4 |
| gpt-6-astra | 0.312 / 55.2 | 0.240 / 64.0 | 0.256 / 60.8 | 0.256 / 61.6 |
| Stage 1, recipe | 0.720 / 12.0 | 0.744 / 8.0 | 0.696 / 7.2 | 0.568 / 24.8 |
| Stage 1, control edits only | 0.712 / 17.6 | 0.736 / 9.6 | 0.768 / 7.2 | 0.704 / 16.0 |
| Stage 1, insertions only | 0.696 / 6.4 | 0.664 / 4.8 | 0.512 / 5.6 | 0.600 / 11.2 |
| Stage 1, erasures only | 0.688 / 7.2 | 0.656 / 4.8 | 0.544 / 2.4 | 0.712 / 4.8 |
| Stage 1, without counterfactual views | 0.272 / 69.6 | 0.200 / 76.8 | 0.144 / 83.2 | 0.232 / 73.6 |

* **MedScope-4B vs the flagships:** better on every tool (ESG +0.10 to +0.48, p≤0.049).
* **gemini-4-argon on Telea:** erased claims fall from 33% to 9% (it recognises Telea's smooth fills as edits).
* **Edit visibility:**
  * A ResNet-18 separates random-removal from original views at AUC 0.83 [0.80, 0.87].
  * A linear probe on the frozen vision encoder's pooled features separates them at AUC 0.60 [0.58, 0.63], and target- vs random-removal at 0.86 [0.83, 0.89].
  * Zero-shot, gemini-4-argon and gpt-6.1-sol separate random-removal from originals at AUC 0.52–0.55 and erased views from originals at 0.70–0.75.
* **Clean-looking erasures:** on erasures that gemini-4-argon rates unedited (61 of 219), MedScope-4B claims the lesion in 15% (8% on visible ones) vs 41–64% for the nine frontier models.

### Table 6: Pre-registered checks C1–C3 (stage 1, seed 0)
Denial = intact lesion denied or referred after a control edit. Held-out tools = Telea + diffusion pooled (219 cases).

| Set | Arm | CCR | ESG | Erased % | Denial % | Net utility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Main test | Matched control | 0.897 | 0.744 | 15.1 | 10.5 | 0.727 |
| | Unmatched control | 0.904 | 0.753 | 15.1 | 9.1 | 0.739 |
| | Recipe | 0.847 | 0.735 | 11.9 | 14.6 | 0.692 |
| | No CF, then removal-based DPO | 0.900 | 0.658 | 23.7 | 10.0 | 0.602 |
| | Recipe, then removal-based DPO (C3) | 0.872 | 0.753 | 11.4 | 13.2 | 0.700 |
| Held-out tools | Matched control | 0.859 | 0.749 | 11.0 | 13.7 | 0.733 |
| | Unmatched control | 0.868 | 0.761 | 10.5 | 12.9 | 0.772 |
| | Recipe | 0.810 | 0.649 | 16.3 | 18.8 | 0.566 |
| | No CF, then removal-based DPO | 0.895 | 0.666 | 23.4 | 10.0 | 0.644 |
| | Recipe, then removal-based DPO (C3) | 0.837 | 0.595 | 24.4 | 16.1 | 0.502 |
| Fresh external | Matched control | 0.488 | 0.405 | 8.3 | 51.2 | −0.083 |
| | Unmatched control | 0.670 | 0.411 | 27.4 | 31.5 | 0.165 |
| | Recipe | 0.560 | 0.381 | 16.7 | 45.2 | 0.061 |
| | No CF, then removal-based DPO | 0.461 | 0.369 | 8.9 | 54.2 | −0.087 |
| | Recipe, then removal-based DPO (C3) | 0.542 | 0.381 | 15.5 | 46.4 | 0.057 |

* **C1 (matching the control edit):** "inconclusive"; within seed noise everywhere except SIIM pneumothorax, where the unmatched arm shows a response bias.
* **C2 (recipe vs removal-based DPO), fresh-external ESG:**
  * single seed: +0.012 [−0.053, 0.077];
  * three seeds: 0.381 ± 0.018 vs 0.355 ± 0.015; every seed's interval includes 0;
  * "no difference shown".
  * Error profiles differ: on new data DPO is more conservative (erased claims 12.9 ± 7.9% vs 20.0 ± 4.0%, sensitivity 0.485 ± 0.086 vs 0.587 ± 0.026).
* **C3 (DPO on top of the recipe):** fails. Held-out-tool erased claims 24.4% vs 16.3%, +0.080 [0.046, 0.118].

### Table 7: Pre-registered check C4: control-matched counterfactual consistency (CMCC) vs matched-compute replay-only control
Held-out tools pooled (219 cases), three seed pairs.

| Seed | Endpoint | CMCC | Control | Difference [95% CI] | p |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | Erased-lesion claims | 0.122 | 0.151 | −0.029 [−0.062, +0.002] | 0.085 |
| 1 | Erased-lesion claims | 0.137 | 0.078 | +0.059 [+0.031, +0.089] | <0.001 |
| 2 | Erased-lesion claims | 0.120 | 0.115 | +0.005 [−0.029, +0.040] | 0.818 |
| Pooled | Erased-lesion claims | 0.126 | 0.115 | +0.011 [−0.009, +0.030] | 0.265 |
| Pooled | ESG | 0.729 | 0.709 | +0.020 [−0.006, +0.047] | 0.143 |
| Pooled | Control-edit denial | 0.143 | 0.176 | −0.033 [−0.054, −0.012] | 0.001 |
| Pooled | CCR | 0.854 | 0.824 | +0.030 [+0.010, +0.051] | 0.004 |
| Pooled | Net utility | 0.712 | 0.661 | +0.051 [+0.002, +0.100] | 0.042 |
| Guard, main test | Healthy-image claims | 0.131 | 0.079 | +0.052 [+0.032, +0.075] | <0.001 |
| Guard, fresh external | Erased-lesion claims | 0.141 | 0.067 | +0.073 [+0.045, +0.106] | <0.001 |

* C4 fails: every endpoint moved toward answering "present".
* The objective is CMCC: L = L_traj + 0.5·softplus(2 − (s(C) − s(E))) + 0.5·(s(O) − s(C))² + 0.5·first-action term, where s(x) = log p(present reply) − log p(absent reply).

### Table 8: Robustness of the frontier comparison (same 150 cases; ESG / erased-lesion claims %)
MedScope-4B on these cases: 0.750 / 7.4.

| Model | Default | Cautious prompt | Solved examples | Highest reasoning | Highest image setting | Plain prompt |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| gemini-4-argon | 0.441 / 41.2 | 0.412 / 42.6 | 0.456 / 36.8 | 0.456 / 39.7 | 0.485 / 38.2 | 0.338 / 52.9 |
| Claude Opus 5.5 | 0.338 / 54.4 | 0.382 / 44.1 | 0.309 / 52.9 | 0.397 / 51.5 | – | 0.412 / 38.2 |
| gpt-6-astra | 0.338 / 52.9 | 0.397 / 47.1 | 0.500 / 38.2 | 0.324 / 58.8 | 0.397 / 51.5 | 0.250 / 66.2 |

* **Under every condition:** MedScope-4B leads every flagship on ESG (p≤0.001) and net utility (p≤0.034).
* **Held-out wordings (373 cases):** net utility unchanged, +0.006 [−0.033, 0.041].
* **Tools refused at test time:** ESG 0.753 vs 0.758 (p=0.92); net utility −0.092 (p=0.003).
* **Lesion size:** MedScope-4B ESG by lesion-area quartile 0.545 / 0.741 / 0.836 / 0.909; erased claims 18.2% (smallest) to 1.8% (largest). The flagships stay within ESG 0.20–0.56 in every quartile.
* **Cost matrix:** MedScope-4B ranks first under all five matrices tested.
* **Selective prediction:** MedScope-4B's stated confidence ranks errors worse than the flagships' (AURC 0.065 vs 0.020–0.033).

### Table 9: Generalisation (MedScope-4B and the flagships)

| Test set | Model | CCR | ESG | Erased % | Healthy % | Net utility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| External centres (169) | MedScope-4B | 0.727 | 0.597 | 11.8 | 4.0 | 0.530 |
| | gemini-4-argon | 0.950 | 0.370 | 58.8 | 18.0 | 0.544 |
| | Claude Opus 5.5 | 0.966 | 0.412 | 53.8 | 30.0 | 0.544 |
| | gpt-6-astra | 0.945 | 0.277 | 66.4 | 24.0 | 0.424 |
| Fresh internal (76) | MedScope-4B | 0.681 | 0.472 | 19.4 | 12.5 | 0.402 |
| | gemini-4-argon | 0.639 | 0.056 | 61.1 | 12.5 | 0.048 |
| | Claude Opus 5.5 | 0.653 | 0.000 | 63.9 | 25.0 | −0.023 |
| | gpt-6-astra | 0.847 | 0.083 | 75.0 | 17.5 | 0.219 |
| Fresh external (316) | MedScope-4B | 0.476 | 0.393 | 8.3 | 4.7 | −0.053 |
| | gemini-4-argon | 0.741 | 0.435 | 31.5 | 9.5 | 0.310 |
| | Claude Opus 5.5 | 0.696 | 0.292 | 42.3 | 18.9 | 0.056 |
| | gpt-6-astra | 0.634 | 0.268 | 35.7 | 34.5 | −0.106 |

* **Fresh external by source (CCR / net utility), MedScope-4B vs gemini-4-argon:**
  * BUS-UCLM 0.73/0.67 vs 0.71/0.55;
  * ETIS 0.69/0.38 vs 0.97/0.75;
  * BraTS meningioma 0.53/−0.03 vs 0.62/0.09;
  * SIIM pneumothorax 0.00/−1.10 vs 0.66/−0.06.
* **Fresh-external net utility vs gemini-4-argon:** −0.363 [−0.496, −0.233].
* **External centres by source (MedScope-4B ESG):** CVC-ClinicDB 0.85, BraTS-Africa 0.71, BUS-BRA 0.58, QaTa-COV19 0.05 (diffuse COVID-19 opacities erase poorly).
* **Standard VQA, closed / open / all:**
  * MedScope-4B: VQA-RAD 0.741/0.230/0.514; SLAKE 0.881/0.644/0.730; PathVQA 0.801/0.125/0.477.
  * Base Qwen3.5-4B: 0.657/0.260/0.481; 0.826/0.424/0.570; 0.545/0.021/0.293.
  * MedScope-4B saw these benchmarks' training splits in replay.

### Table 10: Pneumothorax failure (SIIM, called present; the 42 cases recovered at original resolution)

| Model | 256-px copy | Original resolution |
| :--- | :--- | :--- |
| Qwen3.5-4B (base) | 0% | 12% |
| Stage 1 without counterfactual views | 0% | 5% |
| Stage 1 with counterfactual views | 19% | 40% |
| Stage 2 | not run | 40% |
| MedScope-4B (stage 3) | 0% | 0% |
| gemini-4-argon | 69% | 69% |

* MedScope-4B answered a confident "No" on all 48 SIIM pneumothorax films (answer probability about 1.0).
* **Training coverage (post hoc):**
  * questions naming pneumothorax: 54 of ~7,000 chest X-ray training views in stage 1, trained to "No" 80% of the time;
  * only 4 pneumothorax lesion images in stage 1;
  * no validation pneumothorax lesion images.
* **"Is there an abnormality?"** answered yes on 35/42 pneumothorax vs 28/48 SIIM negatives (Fisher p=0.012).

### Table 11 [new]: Pilots after the preprint (one seed each, against the replay-only control or the recipe; each with a go signal fixed before training)

| Lead | Arm | Main result | Verdict |
| :--- | :--- | :--- | :--- |
| Adapter capacity | Rank 64, vision frozen | Main test ESG 0.731 vs 0.735 (recipe), erased claims 10.5% vs 11.9%; "detects" 25/48 SIIM pneumothorax but also claims 21/48 erased and 12/48 healthy (SIIM ESG 0.042: response bias) | no go |
| Vision encoder LoRA, lr 2e-4 | Rank 64 + vision adapters | ESG 0.000 on every set: answers from the question alone (tumour/mass/"lesion" always present; polyp/effusion always absent) | collapse, no go |
| Vision encoder LoRA, lr 2e-5 | Same, vision lr ×0.1 | No collapse (main test ESG 0.776); fresh-external CCR 0.488 vs 0.560 (−0.071, p=0.03); pneumothorax 7/48 vs 10/48; erased claims 6.8% vs 11.9% (more conservative, not more perceptive) | no go |
| GRPO on the cost-matrix reward (150 steps) | vs replay control | Held-out tools: net utility ≈ +0.056, CCR up, erased claims +0.022; fresh external: net utility +0.124, ESG +0.083, healthy claims +0.054 | go signal narrowly missed |
| Counterfactual multi-agent reader v10 | Direct reader + question-blind reader + lesion segmenter + erase-and-re-ask verifier + trained arbiter | Held-out tools: net utility +0.090 [+0.004, +0.180]; external centres CCR 0.513 vs 0.769; fresh-external CCR 0.378 vs 0.560; pneumothorax 3/48 | no go |
| Multi-agent v11 | Arbiter trained on out-of-sample reports | Held-out tools: net utility +0.042 [−0.033, +0.119], erased claims +0.061 [+0.027, +0.096], ESG −0.002; main-test net utility 0.809 (best of any arm, but the verifier uses the main test's own inpainter) | no go |

* **Multi-agent ablations:** only the segmenter contributed (removing it: −0.055 / −0.066 net utility).
* **The verifier where it acted:** withdrew about 80% of claims after erasing their region and kept about 95% after a control edit. The direct reader rarely claimed an erased lesion with a box (20/219), so the verifier seldom acted.

### Table 12 [new]: Screening funnel of 270 decision policies (validation data only; pass rule: net utility +0.03, ESG +0.02, CCR not −0.03, lesion-free claims not +0.03, on half A and confirmed on half B)

| Stage | Signals | Policies | Pass half A | Confirm half B | Best half-B change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A | Stored outputs: recipe, question-blind reader, segmenter, verifier | 128 (rules, logistic, boosted trees, refer bands) | 19 | 0 | Net utility 0.539 → up to 0.706 (erased claims 11.2% → 3.9%, CCR 0.773 → 0.727); ESG at most +0.026 |
| B | New test-time evidence: 3 altered copies (mirror, crop, contrast), close-up of the claimed region and an equal control close-up, cautious prompt, answer-token probability, a second model (Qwen2.5-VL-7B), segmenter score | 142 | 0 | 0 | TELEA: net utility 0.444 → up to 0.686 by abstaining more; ESG 0.600 for the recipe, most combiners 0.55–0.61 |

### Table 13 [new]: Physician reader study (pack 2: 128 main-test images, 32 per kind; blinded web page; random order)

Readers: R1 internal medicine, 1 year; R2 radiology, 1 year.

| Reader | Erased called edited | Control called edited | Unmodified called edited | AUC edited vs unmodified | AUC erased vs control | Finding "yes": unmodified lesion | erased | control-edited | lesion-free |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R1 | 12/32 | 3/32 | 11/64 | 0.54 | 0.64 | 29/32 | 19/32 | 31/32 | 16/32 |
| R2 | 19/32 | 12/32 | 28/64 | 0.55 | 0.61 | 26/32 (3 cannot tell) | 16/32 (8 cannot tell) | 27/32 | 7/32 (9 cannot tell) |

* **Residual finding on erased images:**
  * pooled reads: 35/64 = 54.7% [41.7, 67.2];
  * per image by majority: 13/32 [23.7%, 59.4%];
  * the pre-specified criterion (≤ 10%) fails.
* **Agreement:** Cohen's κ 0.10 on "edited", 0.47 on "finding present". Physicians cannot tell edited from unedited images (AUC 0.54–0.55).
* **By source**, finding present on erased vs lesion-free images (R1 | R2):
  * colonoscopy: erased 1/6 | 2/6 vs lesion-free 2/6 | 0/6 (erasure works);
  * breast ultrasound: 6/7 | 4/7 vs 5/7 | 1/7;
  * chest X-ray: 5/6 | 4/6 vs 4/6 | 3/6;
  * brain MRI: 3/7 | 5/7 vs 1/7 | 1/7;
  * SLAKE: 4/6 | 1/6 vs 4/6 | 2/6.
* **Reader-verified re-scoring** (stored replies, no model re-run; 10 reader-clean, 19 majority-clean, 13 residual erasures):
  * frontier models pooled (9) claim 26% [10, 42] of reader-clean, 36% of majority-clean and 82% of residual erasures; the pre-registered lower bound > 20% was not met (10 images);
  * open and MedScope models pooled: 12% clean, 19% majority-clean, 40% residual;
  * MedScope-4B: 0/10 clean, 4/13 residual, finds 56/63 reader-confirmed lesions, 0/16 claims on reader-confirmed healthy images.
* **Confound checks:**
  * the clean group is mostly colonoscopy; 4 of 13 residual items ask "Is there an abnormality?";
  * frontier models that found the lesion on the unedited image still claim it after erasure in 30% (19/63) of reader-clean cases;
  * whole main test, colonoscopy (the type readers judged erasure valid for): frontier models pooled claim 45% of 83 erased lesions while finding 96% of unedited ones; other types: brain MRI 46%, breast ultrasound 71%, chest X-ray 60%, SLAKE 49%.

### Table 14 [new]: Where the recipe's held-out-tool ESG is lost (stage-1 recipe, seed 0; main test; stored outputs)
Denies = absent or refer.

| Tool | Denies erased | Denies control | ESG | Denies control where the lesion is found unedited | Erased claims pointing at the erased site |
| :--- | :--- | :--- | :--- | :--- | :--- |
| LaMa (training) | 0.881 | 0.146 | 0.735 | 0.027 (5/186) | 9/22 |
| TELEA (held out) | 0.918 | 0.219 | 0.699 | 0.129 (24/186; 13 breast ultrasound) | 11/13 |
| Diffusion (held out) | 0.743 | 0.152 | 0.592 | 0.043 (7/162) | 41/45 |

* On LaMa the remaining gap is mostly perception: 33 of 219 lesions are missed on the unedited image.
* On TELEA it is edit-induced denial.
* Diffusion erasures have not been reader-checked.

### Table 15 [new]: Framework stage 0, site-matched edits (validation only: 179 lesion cases with yes/no questions, 80 lesion-free images; agent generated answers; "Recipe" here and in Table 16 = the stage-1 recipe adapter, seed 0, not the final MedScope-4B)

New views per case:
* ring = same tool fills an area-matched ring 2 px outside the lesion (lesion intact);
* restored = the erasure with the lesion's pixels put back;
* partial = half the lesion erased (LaMa only).

Denial counted among cases whose unedited image the model answers present (recipe 143 cases, base 127). The recipe's generated answers agree with its earlier answers on the same views on 97.2% of views.

| Model | Tool | Found unedited | Denial: far control | Ring | Restored | Partial | Erased | Ring − far [95% CI] | ESG far | ESG site | AUROC far | AUROC site |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Recipe | LaMa | 0.799 | 0.042 | 0.077 | 0.070 | 0.196 | 0.867 | 0.035 [−0.021, 0.091] | 0.665 | 0.648 | 0.853 | 0.845 |
| Recipe | TELEA | 0.799 | 0.126 | 0.203 | 0.140 | – | 0.923 | 0.077 [0.000, 0.154] | 0.654 | 0.642 | 0.847 | 0.824 |
| Base (untrained) | LaMa | 0.709 | 0.023 | 0.047 | – | – | – | 0.023 [0.000, 0.070] | – | – | – | – |
| Base (untrained) | TELEA | 0.709 | 0.070 | 0.116 | – | – | – | 0.047 [−0.070, 0.186] | – | – | – | – |

* **Pre-registered rule:** site shortcut if the recipe's ring denial is ≥ 0.10, ≥ 0.05 above its far denial and ≥ 0.05 above the base model's.
  * Met on TELEA only (0.203; +0.077; +0.087). Not met on LaMa.
* **Post hoc, on the 112 cases both models find:**
  * TELEA ring denial: recipe 12.5% vs base 6.2% (+0.062 [−0.009, 0.134]); far: 8.9% vs 4.5%.
  * Site-specific part ((ring − far) recipe minus base): +0.018 [−0.080, 0.116].
  * Recipe TELEA ring denials: 12 of 17 chest X-rays, 0/33 breast ultrasound, 2/34 colonoscopy, 0/24 brain MRI.
  * Reading: training roughly doubles sensitivity to an unfamiliar tool's edits wherever they are; no evidence of a site-specific shortcut.

**Linear probes on hidden features** (logistic regression; trained on LaMa views; 5-fold grouped by case; 8 layers):

| Probe | Test tool | Recipe, last token (best layer) | Recipe, image tokens (best) | Base model, last token | Base model, image tokens |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Erased vs ring | LaMa | 0.898 | 0.901 | 0.829 | 0.870 |
| Erased vs ring | TELEA | 0.816 | 0.852 | 0.808 | 0.831 |
| Erased vs control | LaMa | 0.898 | 0.887 | 0.827 | 0.853 |
| Erased vs control | TELEA | 0.812 | 0.851 | 0.771 | 0.804 |
| Ring vs original | LaMa | 0.618 | 0.629 | 0.573 | 0.617 |
| Ring vs original | TELEA | 0.802 | 0.761 | 0.633 | 0.707 |

* **Read-out gap** (best probe minus the recipe's output AUROC, TELEA erased vs ring): +0.028 (image tokens), −0.008 (last token). The pre-registered threshold of 0.05 is not met.

**Within-case changes of the single-turn decision log-odds** (s(view) − s(original), nats; same reply text within a case; descriptive):

| Model | Tool | Erasure | Far control | Ring | Restored | Partial |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Recipe | LaMa | −14.10 | −0.09 | −0.43 | +0.87 | −4.05 |
| Recipe | TELEA | −10.76 | −2.41 | −1.53 | +1.34 | – |
| Base | LaMa | −3.58 | −0.07 | +0.17 | +0.69 | −0.41 |
| Without CF (stage 1) | TELEA | −10.34 | −1.37 | −0.94 | +1.25 | – |
| Erasures only | TELEA | −11.88 | −4.77 | −3.94 | −0.62 | – |
| CMCC | TELEA | −6.08 | −0.31 | −0.12 | +0.57 | – |

* An earlier attempt to use the sign of this score as a decision failed its validity check (63% agreement with the agent's answers, rule 80%): the present reply carries box tokens and is about 11 nats less likely on every image. Only within-case differences are used.

### Table 16 [new]: Framework stage 1, tool-family counterfactual training (validation; one seed)
Setup:
* Arms continue the recipe on exactly the replay-only control's 2,739 training cases, order and settings.
* Erasure and control made with one tool per case from {LaMa, blur fill, mean fill with noise, shuffled pixels}, the control far or in a ring.
* TELEA and diffusion are never used in training.

Differences are arm − control, paired by case, bootstrap 95% CI.

| Quantity | Tool-family replay | Tool-family + CMCC | Control |
| :--- | :--- | :--- | :--- |
| Unedited lesions found | 0.821 (+0.028 [0.000, 0.056]) | 0.765 (−0.028 [−0.073, 0.017]) | 0.793 |
| Lesion-free images claimed | 0.025 (+0.013) | 0.087 (+0.075 [0.013, 0.150]) | 0.013 |
| ESG, LaMa | 0.637 (−0.022 [−0.073, 0.028]) | 0.654 (−0.006) | 0.659 |
| ESG, TELEA (held out) | 0.665 (+0.017 [−0.034, 0.067]) | 0.659 (+0.011 [−0.056, 0.084]) | 0.648 |
| Erasure denied, LaMa | 0.821 (−0.050 [−0.095, −0.006]) | 0.899 (+0.028) | 0.872 |
| Erasure denied, TELEA | 0.899 (−0.011) | 0.950 (+0.039 [0.000, 0.078]) | 0.911 |
| Control edit denied (found), TELEA | 0.078 (−0.021 [−0.057, 0.007]) | 0.107 (+0.008) | 0.099 |
| Ring edit denied (found), TELEA | 0.163 (−0.028 [−0.064, 0.000]) | 0.214 (+0.061 [0.023, 0.107]) | 0.191 / 0.153 |

* **Pre-registered pass rule:** TELEA ESG +0.03, TELEA control denial −0.03, LaMa ESG ≥ −0.02, found ≥ −0.03, lesion-free claims ≤ +0.03.
  * Tool-family replay fails (1, 2, 3).
  * Tool-family + CMCC fails (1, 2, 5).
* The ring column differs between arms because each comparison uses the cases both models find.

## 3. Qualitative Observations

* **Frontier models report what the question names.**
  * Nine frontier VLMs detect real lesions about as well as the 4B agent (CCR 0.83–0.89) but claim 41–62% of erased lesions.
  * This holds under a cautious prompt, solved examples, highest reasoning, highest image setting, a plain free-text prompt and reworded questions.
  * The pattern holds where erasure is reader-validated (colonoscopy: 45% claims vs 96% detection).
* **Counterfactual views are the active ingredient of the trained agent:**
  * removing them collapses ESG on every seed and on a second base model;
  * matching the share of "absent" answers does not reproduce the effect;
  * control edits reduce the "edited means absent" shortcut (Telea denial 43% → 16–23%);
  * matching the control's shape and tool was not shown to matter.
* **Every attempted improvement moved the threshold, not the discrimination.** DPO, consistency losses, GRPO, vision adapters, multi-agent verification, 270 abstention and test-time-evidence policies, and tool-family training all changed how often the model says "present" or "absent" and traded erased claims against sensitivity. None raised ESG on held-out tools beyond its matched control.
  * Utility gains came from referral and conservatism, as the abstention ceiling predicts.
* **The limit is in the representation, not the read-out:**
  * linear probes on the recipe's hidden states separate erased from intact lesions no better than its answers (gap ≤ 0.03);
  * the untrained base model's features separate them almost as well (0.83–0.87 vs 0.85–0.90);
  * training mainly changes how the evidence is read out;
  * about 15–20% of real lesions are missed on unedited images, and each miss also lowers ESG.
* **The counterfactual labels are noisy outside colonoscopy.** Physicians cannot tell edited from unedited images, yet still see a finding on about 40% of erasures (by majority), with poor inter-reader agreement on edits. This caps what ESG can certify and argues for reader-verified or generator-specific validity estimates.
* **Held-out tools fail in different ways:**
  * TELEA's smooth patches cause denials of present lesions;
  * diffusion edits produce claims located exactly at the erased site, which may be residual or regenerated tissue rather than hallucination.
* **Failure transparency:** a confirmatory fresh test exposed a complete pneumothorax miss (0/48), linked post hoc to training coverage (4 positive images) and a conservative final stage. Validation sets need positives of every critical finding.
