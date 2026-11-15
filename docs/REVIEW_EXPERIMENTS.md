# Experiments added after the external review (pre-registration)

Committed before any of these experiments ran. They answer an external review of the manuscript (15 Nov 2026).
Each is reported whatever its outcome. None changes the reported model (MedScope-4B = v4 stage 3) or reuses a test
set for selection: R1 and R2 are screened on the validation dev set only; R3 and R4 are measurements; R5 is a new
reader study.

Lead 2 of `docs/PILOTS_v9.md` (vision adapters) was closed after its one declared retry (notebook 39d). R2 below is
a **new** experiment prompted by the review, declared here, not a further retry under the v9 plan.

## R1. A CORAL-style comparator: hard-negative image swaps

**Question.** CORAL (Zafar et al., arXiv:2607.03647) trains a medical VLM to change its answer when the whole image
is swapped for a CLIP-retrieved hard negative. Its weights are not public. Does that training signal, added to our
pipeline, raise held-out discrimination?

**Arm `v4q_hns_s0` (name in the screen: `hardneg`).** Exactly the replay-only control `v4q_sftc_s0` (the stage-1
recipe `v4_s1` continued on the same 3,000 triplet cases, same order, same replay, lr 2e-5, grad-accum 8, seed 0)
plus one term: for each case, the most similar lesion-free training image of the same source and another patient
(CLIP `openai/clip-vit-base-patch32` cosine similarity < 0.995; `scripts/build_hardneg.py`) is scored with the
case's question and candidate replies, and `0.5 * softplus(2 - (s(original) - s(swap)))` is added (the answer must
not stay "present" when the image is swapped). The paired-view weights of CMCC are 0.

**Screen.** Generated agent answers on the validation dev set (the stage-0 views: original, LaMa and TELEA erasure,
control and ring edits, lesion-free images), arm vs the replay-only control, paired by case
(`medscope/fw/review.py`, `scripts/fw_review.py`).

**Rule (point estimates).** Passes if TELEA ESG rises by at least 0.03, LaMa ESG does not fall by more than 0.02,
unedited lesions found do not fall by more than 0.03, and lesion-free claims do not rise by more than 0.03.
A pass justifies a three-seed confirmation on the held-out tools; it does not change the paper's model.

## R2. Can a gently adapted vision encoder see more?

**Question.** The paper attributes the remaining limit to perception with a frozen general-domain encoder. Does
adapting the vision encoder with layer-wise learning-rate decay improve perception (lesions found on unedited
images) without losing discrimination?

**Arm `v4_vlrd_s0` (name in the screen: `vision_lrd`).** The pre-registered stage-1 recipe (same 16,000 views,
same options, seed 0, rank-16 LoRA on the language model at lr 2e-4) with LoRA also on the vision encoder and
projector (`--lora-vision`): the top vision block and the projector at 2e-5 (`--vision-lr-scale 0.1`), each block
below at 0.9 times the one above, the patch embedding one factor lower (`--vision-layer-decay 0.9`).

**Comparator.** The stage-1 recipe `v4_s1` (frozen encoder, same data and seed), answers already generated in
notebook 44b.

**Rule (point estimates).** Passes if unedited lesions found rise by at least 0.03, LaMa ESG and TELEA ESG each do
not fall by more than 0.02, and lesion-free claims do not rise by more than 0.03. Reported either way; a pass
justifies a three-seed run of the full recipe with this setting.

## R3. Is the limit specific to this encoder? Frozen encoders compared

**Measurement** (`scripts/encoder_compare.py`). The same linear probe on frozen image features of four encoders:
Qwen3.5-4B's own vision module, BiomedCLIP, RAD-DINO and DINOv2-base; whole image and a lesion-centred crop (same
crop box for the three views of a case). Trained on training views (up to 600 per kind), tested on main-test views
made with LaMa and with the held-out tools (TELEA, Stable Diffusion). Pairs: erasure vs control edit (primary),
erasure vs unedited, control edit vs unedited. AUC with case-bootstrap intervals and the paired difference from
Qwen's encoder.

**Reading.** If an alternative encoder separates erasure from control edit better than Qwen's on a held-out tool by
at least 0.05 AUC with the paired interval above zero (either pooling), the perception limit is at least partly a
property of this encoder and the paper says so; otherwise we report no evidence that another frozen encoder holds
more of this separation. The probe uses only the test images' features, never their answers.

## R4. The abstention ceiling, measured

**Measurement** (`scripts/fw_stage0.py --stage tvbound`). For the recipe and the base model, on the stage-0
validation views: per layer and token, the out-of-sample TPR - FPR of a linear probe (threshold chosen on the
training folds) separating erasure from ring (and from control) edits. Any fixed event bounds the total-variation
distance from below, so this is an estimated lower bound on TV(hidden | erasure, hidden | ring). It is compared with
the model's own denial gap on the same views (from its generated answers).

**Reading.** A bound close to the denial gap (difference under 0.05) means the answers use about as much separation
as the hidden states linearly hold, consistent with Proposition 1 and with no read-out gap; a bound above the gap by
0.05 or more, with its interval above the gap, would be a read-out gap. The bound is linear: the true TV may be
higher, and the paper says so.

## R5. Expert reader study (pack 4)

**Readers.** At least two board-certified radiologists (5 or more years after certification), recruited by the
author; a gastroenterologist or endoscopist for colonoscopy if available. None has seen packs 2 or 3. Readers record
specialty, years and certification on the page.

**Images.** From the main test set, each from a different case, stratified by source: 36 each of unedited lesion
images, LaMa erasures, LaMa control edits and unedited lesion-free images, plus 36 Stable Diffusion erasures and 36
Stable Diffusion control edits (same masks; `make_reader_study.py --tool diffusion=...`). If fewer cases are
available for a kind, all available are used and the count is reported. Same blinded page as before (PNG, no
metadata, shuffled per reader, no key on the page).

**Criterion.** Per tool, the share of erased images on which the reader majority still calls the finding present,
localized findings apart from the named stress tests; acceptable if the exact 95% upper bound is at most 10% (with
36 images, possible only with no residual image). Reported with edit detectability (AUC), agreement on edits and on
the finding (Cohen's kappa), and by source. Results replace nothing: they are added to the trainee study, and the
reader-verified re-scoring is repeated on the expert labels.
