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

---

# Amendment 1 (15 Nov 2026, after a second review; committed before R6-R8 ran)

R1-R4 have run (results in `docs/RESULTS_LOG.md`). A second pass of the review asked for a Med-CAP comparison,
subject-wise splits for every source and a retrained model without the pneumothorax failure. The author asked to
leave IEEE formatting and further clinical validation aside.

## R6. A Med-CAP-style comparator: adaptive prior suppression

Med-CAP (MICCAI 2026) has two parts: evidence-discard training from gradient attribution on a classifier head, which
an agent answering in text does not have, and adaptive prior suppression at decision time, which we test. For each
stage-0 validation case, the question-only prior p is the recipe's single-turn decision log-odds on a uniform grey
image with the case's question and candidate replies (`scripts/fw_stage0.py --stage prior`). Variants
(`medscope/fw/aps.py`): fixed suppression s - a p and Med-CAP's adaptive form s - a0 c (1 - e) p (c: prior
confidence, e: evidence strength); a, a0, the variant and the threshold are chosen on half A of the cases (by hash)
with LaMa views only; results on half B for LaMa and TELEA. **Rule:** the chosen variant passes if the TELEA
erased-vs-ring AUROC rises by at least 0.03 over the raw score with the case-bootstrap interval above zero.
Reported with found, lesion-free claims and ESG at the half-A threshold.

## R7. Leakage sensitivity where patient ids do not exist

SLAKE, Kvasir-SEG/HyperKvasir and BUSI release no patient ids, so their splits stay by near-copy group; a strict
subject-wise split cannot be made without the ids, and the splits are not changed after testing. Instead
(`scripts/leakage_similarity.py`): (1) on training images with patient ids (ChestX-Det, TCGA-LGG), how well DINOv2
image similarity separates same-patient from other-patient pairs; (2) for every main-test case, its most similar
training image of the same source; within each source the top 10%, 25% and 50% most similar test cases are removed
and the main-test comparisons (MedScope-4B vs gemini-4-argon, Claude Opus 5.5, gpt-6-astra) are recomputed from the
stored outcomes, for all sources and for the three sources without ids. **Reading:** if MedScope-4B's ESG advantage
over each comparator keeps its sign and its interval stays above zero after removing the top 25% in every source,
leakage of near-similar images does not explain it.

## R8. A rebalanced model: pneumothorax in every stage (v4.2, post hoc)

v4.1 added SIIM pneumothorax training patients to stage 3 only (27% found on new SIIM patients). v4.2 runs the whole
v4 recipe again (same data, options and seed) with the same 150 + 150 SIIM training patients added to stages 1, 2
and 3 (and to the rejection-sampling pool), from patients in no evaluation (`scripts/prepare_siim_train.py`, same
split as v4.1). **Rule, fixed before any v4.2 test result:** v4.2 passes if its validation net utility is at least
v4's minus 0.02, its lesion-free claims at most v4's plus 0.02, and it finds at least as many SIIM validation
pneumothoraxes as v4.1. It is tested either way on the main test, external, fresh and fresh external sets, the new
SIIM test patients and standard VQA. MedScope-4B (v4) remains the pre-registered model of the paper; v4.2 is reported
as a post hoc remedy.

---

# Amendment 2 (16 Nov 2026, R5 delivery only; committed before pack 4 was built)

Nothing in R5's images, readers, questions, criterion or analysis changes. Only how the answers reach us:

- **Automatic saving.** Each reader gets a personal link (an opaque code, no name). Every answer is saved as it is
  given to a Google Sheet owned by the author (`reader/expert.html`, `reader/apps_script.gs`); readers send nothing
  back and can continue on any device. Each save is a new row; a reader's latest answer per image counts. Codes are
  issued by notebook 49; a TEST code used to check the connection is never scored.
- **Two recorded fields added**, neither scored in the pre-registered criterion: whether the reader took part in an
  earlier round (packs 2-3; R5 requires none did, so a "yes" is reported and that reader is analysed apart), and an
  optional free-text note per image. Notes on erased images called "Yes" are reported descriptively (what readers
  saw), answering a question the trainee study left open.
- **Consent** to the use of the answers under a reader code is recorded on the page before the first image.
- The image order is shuffled per reader (seeded by the reader's code, so the same on every device), as before.

---

# Amendment 3 (18 Nov 2026, R5 closing rule and readers; committed before any R5 answer was examined)

One reader has completed pack 4 (code R1, all 212 images, 18 Nov 2026): a board-certified gastroenterologist and
endoscopist. No R5 answer has been opened or scored. Nothing in R5's images, questions, criterion or analysis changes.

- **Closing rule.** R5 closes when two board-certified radiologists (5 or more years after certification) have
  completed all 212 images, or on 10 January 2027, whichever comes first. No answer is examined before R5 closes,
  and the closing date is not moved after any answer is seen. If fewer than two radiologists have finished by then,
  R5 is reported as incomplete, with what was collected and how many readers finished.
- **Endoscopist reader.** The endoscopist reads all 212 images, as every reader does. As pre-registered ("an
  endoscopist for colonoscopy"), the endoscopist's reads count in the criterion for colonoscopy images; reads of other
  sources are reported by specialty and kept out of the radiologist majority.
- **Readers as authors.** Readers who complete the reading and review the manuscript are offered authorship. They read
  blinded (no labels, no edit types, no other reader's answers), and the paper says which readers are authors.

## Amendment 3a (18 Nov 2026, 23:10 ET; committed before any R5 answer was opened)

The endoscopist's reading is complete for the images the protocol assigns to an endoscopist (colonoscopy), and that
result does not depend on any radiologist. So an **interim single-reader analysis of the endoscopist (R1)** is added,
run once now and reported as interim, one reader:

- **Primary (colonoscopy):** share of erased images (LaMa; Stable Diffusion apart) on which R1 calls the finding
  present, with the exact 95% interval, against R5's 10% upper-bound criterion; edit detectability (AUC, edited vs
  unedited); finding calls on unedited lesion and lesion-free images; agreement with the trainee readers where the
  same cases were read.
- **Descriptive only (other sources):** the same measures for brain MRI, chest X-ray, breast ultrasound and SLAKE,
  labelled as outside the reader's specialty and not used in any criterion.
- **Re-scoring:** stored model outputs re-scored on the colonoscopy erasures R1 calls clean, as was done with the
  trainee readers.
- The radiologist part of R5 stays closed under Amendment 3 (two radiologists or 10 January 2027); the closing rule
  does not change after this analysis. The final R5 report uses all readers and supersedes the interim one.

---

# Amendment 4 (19 Nov 2026, 00:15 ET): R9, natural pairs (committed before any frame or film was downloaded)

## R9. Does the advantage hold on real lesions against real absences, with nothing edited?

**Why.** MedScope-4B is trained on counterfactual views made by the pipeline that builds the test. The matched
control edits, held-out tools, untouched lesion-free images and external centres argue against an "edited means
absent" shortcut, but no test so far pairs a real lesion with a real absence in the same patient without any edit.

**Data (never used in this project).**
- **Colonoscopy, primary.** REAL-Colon (60 full videos from 4 centres, per-frame polyp boxes, CC BY 4.0). Per video,
  the 3 longest polyp tracks (boxed runs, gaps under 2 s merged, at least 1 s long). Lesion frame: from the middle
  half of the track, largest box at least 1% of the frame. Paired frame: same video, 10-30 s before the track starts
  (after it ends if no frame qualifies before), and at least 10 s from any boxed frame. Of 12 evenly spaced
  candidates per side, the sharpest (variance of the Laplacian) with mean brightness 40-215 is kept. Question:
  "Is there a polyp in this image?" for both.
- **Chest X-ray, secondary.** NIH ChestX-ray14 follow-up studies. Lesion film: the only label is pneumothorax,
  pleural effusion, nodule or mass. Paired film: the nearest "No Finding" study of the same patient and view
  position. One pair per patient, up to 50 per finding (chosen by a fixed hash). Every patient in any ChestX-Det
  split is excluded, and any pair with a near-copy of an earlier image (any split, SIIM training patients included)
  is dropped. Question: "Is there {finding} in this chest X-ray?", the main test's wording.

**Models.** MedScope-4B (v4, the pre-registered model), v4.2 (reported apart), the untrained Qwen3.5-4B, and
gemini-4-argon, claude-opus-5-5 and gpt-6-astra over their APIs, all with the main test's agent prompt.

**Measure.** Natural ESG = share of lesion-free images answered "absent" or referred, minus the share of lesion
images of the same video or patient answered "absent" or referred (constant policies score 0, as with ESG). Also
reported: lesion found, lesion-free image answered "absent". Paired differences against MedScope-4B, 2,000 bootstrap
resamples of whole videos (colonoscopy) or patients (chest X-ray), two-sided.

**Reading rules, fixed now (colonoscopy).**
- MedScope-4B's natural ESG above every flagship's, each difference's 95% interval above 0: the counterfactual
  advantage carries over to unedited images.
- Above none of them (every interval reaching 0 or below): it does not carry over, and the paper says so.
- Otherwise: mixed, reported comparison by comparison.
- Reported descriptively: MedScope-4B's natural ESG against its counterfactual colonoscopy ESG (0.95 on the main
  test), and against the untrained base model (what training changes).

**Chest X-ray** is reported by finding and pooled, descriptively. MedScope-4B's known pneumothorax failure (0/48 on
the fresh external set) is expected to show; v4.2 is reported beside it. No chest X-ray result changes the
colonoscopy reading.

**Known limits, stated in advance.** Natural pairs differ in more than the lesion (view, lighting, bowel
preparation); a paired frame may hold a small polyp that was not annotated (REAL-Colon boxes the polyps that were
removed); NIH labels are mined from reports, not read from the images.

**Fixed.** No parameter above changes after any frame, film or answer is seen. If the annotation files cannot be
parsed as expected, only the parser changes, before any image is evaluated, and the change is logged. Every result is
reported, whatever it shows. Code: `scripts/natural_pairs.py`, notebook 52.

---

# Amendment 5 (20 Nov 2026, 11:45 ET): R12-R15, robustness of the headline (committed before any of them ran)

None of these changes the pre-registered model: MedScope-4B (v4) stays the reported model, and every result below is
reported whatever it shows. All run in notebook 53, together with R9 (Amendment 4) and the public release.

## R12. Training seeds of the full recipe

**Why.** The headline model is one end-to-end training run; only stage 1 has three seeds.
**What.** The whole v4 recipe (stages 1, 2 with rejection sampling, 3; same data, options and commands as v4) is rerun
with training seeds 1 and 2. Each seed's model is its stage-3 adapter (no selection step). Each is tested on the main
test, external centres, fresh internal and fresh external sets.
**Reported.** CCR, ESG, erased-lesion claims, lesion-free claims and net utility for seeds 0 (MedScope-4B), 1 and 2,
with mean and standard deviation, and each seed against gemini-4-argon, claude-opus-5-5 and gpt-6-astra (paired).
**Reading.** The headline holds across seeds if every seed's main-test ESG is above each of the three flagships' with
the paired 95% interval above 0. Otherwise the paper reports which seeds do not, and the headline is stated as the mean.

## R13. Edit visibility (low-visibility erasures)

**Why.** A trained CNN can tell control-edited from unedited images (AUC 0.83), so the model could in principle use
edit traces.
**What.** A ResNet-18 edit-trace detector is trained on control-edited vs unedited training views (both show the
lesion), seed 0, 5 epochs, then scores every main-test view. An erasure is low-visibility when its score is at or
below the median score of the main-test control edits. Stored decisions (no new model runs) of MedScope-4B and the
three flagships are re-scored on cases with a low-visibility erasure. Code: `scripts/edit_visibility.py`.
**Reading.** Edit visibility does not explain the advantage if, on low-visibility cases, MedScope-4B's ESG is above
each flagship's with the paired 95% interval above 0. Erased-lesion claims on low-visibility vs other erasures are
reported for every model.

## R14. Open-ended request instead of a yes/no question

**Why.** Every question so far is closed ("Is there a polyp?").
**What.** On the same 150 main-test cases as the robustness checks (select_cases, seed 0), the unedited lesion image
and its erasure are given with "Describe any abnormal findings in this image." (plain prompt, one reply, no tools).
Cases with a generic closed question (abnormality, healthy, normal) are left out. A text-only judge (gpt-6-astra,
blind to the model and to the image) says whether each reply states that the finding named in the case's closed
question is present. Models: MedScope-4B, the untrained Qwen3.5-4B, gemini-4-argon, claude-opus-5-5, gpt-6-astra.
Code: `scripts/freetext.py`.
**Measure.** Free-text ESG = share of unedited images whose reply reports the finding minus the share of erasures whose
reply still reports it; paired bootstrap over cases.
**Reading.** The effect is not tied to the yes/no format if MedScope-4B's free-text ESG is above each flagship's with
the paired 95% interval above 0. MedScope-4B was trained only on the agent format, so a lower free-text ESG is
reported as a limit of format transfer, not hidden.

## R15. Reproduction from the public release

**What.** After the public Hugging Face release, the MedScope-4B adapter is downloaded from the hub (not from the
training folders) and run on the main test with the evaluation code as released.
**Reading.** Reproduced if main-test ESG is within 0.02 of the reported 0.758 and at least 97% of per-view decisions
(action and stated presence) match the stored run. Greedy decoding on a different GPU can change a few tokens, which
is why the rule is not exact equality.

---

# Amendment 6 (21 Nov 2026, 18:00 ET): R16, MedScope-v5 with natural pairs in training (post hoc; committed before any training frame was drawn or any v5 model trained)

**Status of R9.** Unchanged. By the Amendment 4 rule, MedScope-4B's counterfactual advantage does not carry over to
natural colonoscopy pairs (natural ESG 0.243 against 0.320-0.466 for the flagships; equal to the untrained base
model). That result stays in the paper as reported. MedScope-4B (v4) stays the pre-registered model.

**What was looked at before this plan was written.** The R9 tables and the per-pair answers of MedScope-4B, the
untrained base model and claude-opus-5-5 on the 103 pairs (model outputs and the annotated boxes; no change to any
pair). They show: MedScope-4B claims a polyp on 2 of 103 lesion-free frames (base 15, claude-opus-5-5 20) but calls
only 36 of 103 real polyps present (claude-opus-5-5 73); 5 of the 34 smallest. It answers "absent" without a tool call
on 53 polyp frames; when it zooms it is right on 31 of 42. Its training holds no real lesion paired with a real
lesion-free image of the same patient: training polyps are large, centred still images, and lesion-free colonoscopy
images come from another source. The same pattern as pneumothorax (v4 0/100, v4.2 53/100 after training coverage).

**Question.** Does adding natural pairs to training carry the advantage over to unedited images of unseen patients?

**Folds, fixed now.** REAL-Colon videos are cut by their number within each cohort: videos 1-5 (fold 0), 6-10
(fold 1), 11-15 (fold 2). The primary measure pools all 103 R9 pairs, so the cut cannot select pairs.

**Training frames, fixed now** (`scripts/natural_pairs.py colon-train`; tracks as in Amendment 4):
- Per video, the 10 longest tracks. Per track, one lesion frame per 2 s of track, at most 6: the track's frames whose
  largest box covers at least 0.5% of the frame are cut into that many consecutive parts; in each part, of 6 evenly
  spaced candidates, the sharpest with mean brightness 40-215 is kept.
- Lesion-free frames, as many as lesion frames per video: per track one "near" frame (the Amendment 4 rule: 10-30 s
  before the track, after it if fewer than 3 qualify, at least 10 s from any boxed frame) and one "context" frame
  (within 10 s of the track's ends and 3-10 s from the nearest boxed frame); the rest "far" frames spread over the
  frames at least 30 s from any boxed frame. A video without tracks gives 12 far frames. Same candidate rule.
- Question and answers as in R9 ("Is there a polyp in this image?"; Yes with the largest box / No).

**Models.** The v4.2 stage-3 command (notebook 51: from the v4.2 stage-2 adapter, same data, options and seed, SIIM
patients included) with the natural training frames added in full:
- v5-fold-k (k = 0, 1, 2): frames of the videos outside fold k.
- MedScope-v5: frames of all 60 videos. This is the model tested on every other set.
One run each. No option is tuned, no checkpoint is chosen, and no other variant is trained under this amendment.

**Primary measure.** Natural ESG on the 103 R9 pairs, each pair answered by the fold model that never saw its video
("MedScope-v5, cross-validated"). The flagships' and MedScope-4B's stored R9 answers are used as they are. Paired
differences, 2,000 bootstrap resamples of whole videos, two-sided.

**Reading rule, fixed now.**
- Cross-validated v5 above every flagship, each difference's 95% interval above 0: with natural pairs in training, the
  advantage holds on unedited images of unseen patients from the same centres.
- Above none of them (every interval reaching 0 or below): it does not, and the paper says so.
- Otherwise: mixed, reported comparison by comparison.

**Guard on MedScope-v5 (validation only, before any of its test results; the R8 rule).** Validation net utility not
more than 0.02 below v4's and lesion-free claims not more than 2 points above v4's. If the guard fails, v5 is reported
as failing it. MedScope-v5 is then run on the main test, external centres, fresh internal, fresh external, the new SIIM
patients and standard VQA, and compared with v4 and v4.2 (paired). A main-test ESG more than 0.05 below v4's is
reported as a trade of counterfactual discipline for sensitivity.

**Secondary, descriptive (no reading rule).**
- Grounded detection: polyps called present with a box of IoU >= 0.3 against the annotated polyp, for every model
  (a model answering from context, not from the polyp, cannot place the box).
- Context-matched lesion-free frames for the R9 pairs: per pair, a frame within 10 s of the track's ends and 3-10 s
  from the nearest boxed frame (before the track; after it if fewer than 3 qualify), the sharpest usable of 12
  candidates. Share answered "absent" or referred, and natural ESG against these frames, for cross-validated v5, v4,
  v4.2, the base model and the three flagships (new API calls on these frames only).
- Natural ESG by fold and by cohort.

**Known limits, stated in advance.** v5 is designed after the R9 result was seen, and the 103 pairs are used a second
time; cross-validation over unseen videos, a single run and no tuning limit this, but do not remove it. The fold
models are trained on videos of the same four centres drawn by rules close to the test's, while the flagships are
used as they are (as in the main test). Three fold models stand in for one. Frames near a track may show a polyp
that was not boxed. No centre is held out.

**Fixed.** One attempt. Every result is reported, whatever it shows. R12 (training seeds of v4) is still owed and is
run after this. Code: `scripts/natural_pairs.py`, notebooks 54a (data) and 54b (training and tests).

# Amendment 7 (22 Nov 2026, 11:06 ET): R17-R22, after an independent review of manuscript v5 (committed before any of them ran)

An independent review of manuscript v5 (two reviewers who saw only the manuscript) asked for: confirmation of v5
with no centre shared; natural pairs without counterfactual views; results by question type; an image-blind control;
the training seeds (R12, Amendment 5, still owed and unchanged); and the finished expert reader study (R5,
unchanged, open). S. Sharma (CheXthought) suggested rewarding the inspection of the relevant region and not only the
answer. This amendment fixes the plan for each before any of it runs. Nothing below changes an earlier result:
MedScope-4B (v4) stays the pre-registered model, and v5 stays post hoc.

## R17. Counterfactual views x natural pairs (what each contributes)

**Question.** Do natural pairs help without counterfactual views, and do counterfactual views add anything once
natural pairs are in training?

**Arms (stage-1 models, seed 0).** Two exist: A, stage 1 without counterfactual views (`v4q_nocf_s0`), and B, the
stage-1 recipe with them (`v4_s1`). Two are new, each trained three times on the folds of Amendment 6 (videos 1-5,
6-10, 11-15 of each centre left out in turn): C = A continued with natural frames, D = B continued with natural
frames. The continuation is the same for both except for the kinds of the replayed views: 5,000 views of the arm's
own stage-1 training set (C: original, lesion-free and degraded views only; D: all kinds), learning rate 5e-5,
agentic trajectories, window probability 0.3, small-lesion zoom, paraphrase probability 0.5, plus the fold's natural
training frames in full (the frames of Amendment 6, nothing redrawn). No SIIM patients and no VQA replay, as in
stage 1.

**Tests.** The 103 R9 pairs: A and B as they are; C and D cross-validated (each pair answered by the fold model
that never saw its video). The fold-0 models of C and D on the main test.

**Primary measure and reading.** Natural ESG of D minus C on the 103 pairs, 2,000 resamples of whole videos. Interval
above zero: counterfactual views add to evidence sensitivity on unedited images beyond natural pairs. Interval
includes zero: not shown (the difference and interval are reported; no claim of equivalence). Interval below zero:
they cost.

**Secondary, descriptive.** C minus A and D minus B (what natural pairs add at each level); polyp claimed on
polyp-free frames (counts) and grounded detection for all four; main-test ESG and erased-lesion claims of the fold-0
models of C and D against A and B.

**Known limits.** Stage-1 models, not the three-stage recipe; one seed; same four centres; the 103 pairs are used
again.

## R18. v5 with no centre shared (leave-one-centre-out)

The v5 recipe of Amendment 6 (stage 3 of v4.2 plus natural frames; same data, options, seed) is trained four times,
each without every video of one centre (cohorts 001-004), from the training frames already drawn. Each R9 pair is
answered by the model that never saw its centre ("v5, leave-one-centre-out").

**Primary measure and reading.** Natural ESG of these answers against the stored answers of the three flagships, by
the rule of Amendments 4 and 6: above every flagship with the interval above zero, the advantage carries over to
unseen centres; above none, it does not; otherwise mixed.

**Secondary, descriptive.** Leave-one-centre-out minus cross-validated v5 (what holding out the centre costs); by
centre; grounded detection; the context-matched frames with the stored flagship answers.

**Known limits.** The same dataset and the same 103 pairs (a third use); the flagships are used as they are. One
attempt, nothing tuned.

**R18b (specified, not yet built).** A second public colonoscopy video set with per-frame polyp boxes that no model
here has used (candidates: PolypGen, LDPolypVideo, SUN-SEG; access terms not yet checked). The pair rules of
Amendment 4, v5 (all videos) as it is, the same reading rule. It is registered with the dataset named before any
frame is drawn.

## R19. Image-blind control

For every main-test lesion case whose closed question is answered "Yes" on the unedited image, two extra views ask
the same question: **blank** (a uniform mid-grey image of the same size) and **swapped** (a lesion-free main-test
image of another imaging type, chosen by a fixed hash of the case id). Agent protocol unchanged. Models: the nine
frontier models, MedScope-4B and the untrained base.

**Reported.** Per model, the share of blank and of swapped views on which the finding is claimed, denied, referred
or a better image is asked for, next to its stored claim rates on erased and on lesion-free images, and the paired
difference erased-claim rate minus blank-claim rate (2,000 resamples of cases).

**Reading, fixed in advance.** The blank-image claim rate is the part of a model's claims that needs no image. If a
model's erased-claim rate is above its blank-claim rate with the interval above zero, its erased claims are not
explained by the question alone, and the manuscript says "claims without support in the image" for that model, not
"answers from the question". If the two rates do not differ, the question-prior reading stands for that model.

## R20. Results by question type

Main-test cases are split by their closed question: **finding-specific** (names a finding) or **generic** (matches
"abnormal", "healthy" or "normal"; the rule already used for R14 in `scripts/freetext.py`). Stored answers only.

**Reported.** Per stratum and model: cases, ESG, erased-lesion claims, lesion-free claims; MedScope-4B minus each of
the nine frontier models on ESG (2,000 resamples of cases); the same for colonoscopy alone.

**Reading.** The headline holds on finding-specific questions if MedScope-4B's ESG is above each of the three
flagships' on that stratum with the interval above zero (the flagships of R13); all nine are reported. If it holds
only with generic questions included, the manuscript's headline is restricted to what holds.

## R21. Rewarding the look (pilot; a suggestion of S. Sharma)

**Motivation.** On the R9 polyp frames MedScope-4B answers "absent" without a tool call on 53 of 103 and finds 31 of
the 42 it zooms on: it decides before it looks.

**Arms (one seed each; fold 0 of Amendment 6, so the 38 pairs of fold 0 are unseen by every arm).**
- **L1, look-first training.** Fold 0's stage 3 of Amendment 6 again with one change: every training trajectory on a
  lesion or erased view zooms on the (former) lesion box with probability at least 0.8, and a lesion-free view is
  inspected (a zoom on a random region, 30-50% of the image on a side) with probability 0.8 before the answer
  "absent".
- **L2, process reward.** GRPO from the fold-0 model `v5_f0_s3`: 150 steps, the settings of pilot 39b, on the main
  training views plus fold 0's natural training frames. Reward = the cost-matrix reward, plus 0.5 if a zoom covers at
  least half of the lesion box (lesion and control-edited views) or of the erased site (erased views) before the
  answer, plus 0.25 if a lesion-free view is inspected at all before it is denied.
- **L0, control for L2.** The same GRPO run with the cost-matrix reward only.

**Go signal (L1 and L2, each against `v5_f0_s3` on the same 38 pairs).** Natural ESG higher by at least 0.05, AND at
least 3 more polyp frames called present with a correct box (IoU >= 0.3), AND on validation net utility not lower
than `v5_f0_s3`'s by more than 0.02 and lesion-free claims not higher by more than 0.02. L2 must also be above L0 on
natural ESG, or the gain is GRPO's and not the process reward's. A go leads to a three-fold run registered
separately; a no go is reported as a one-seed pilot.

**Known limits.** 38 pairs; one seed; the R9 pairs are used again.

## R22. CheXthought (S. Sharma's ideas 2-4): access and schema only

No experiment yet. Notebook 57 checks access to CheXthought and prints its tables. Training on reader disagreement
(idea 3) and region or gaze supervision of the encoder (idea 4) are registered once the schema is known. Targeted
model editing (idea 2) is not planned for this version.

**Fixed.** One attempt each. Every result is reported, whatever it shows. Code: `scripts/natural_pairs.py`
(`colon-loco`), `scripts/question_type.py`, `scripts/blind_views.py`, `medscope/train/look.py`; notebooks 55a
(R20, R19), 55b (R18), 55c (R17), 56 (R21), 57 (R22); R12 and the chest X-ray rebuild stay in notebooks 53b and 53c.
