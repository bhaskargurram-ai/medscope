# Toward one framework: literature synthesis, what our own data says, and the plan (14 November 2026)

Six literature reviews (published, peer-reviewed work; arXiv-only work listed separately as novelty threats) are in
`docs/litreview/`: (1) medical VLM hallucination, (2) language-prior mitigation in general VLMs, (3) counterfactual
image editing in medicine, (4) grounding and "right for the right reasons", (5) abstention and calibration, (6)
perception limits, vision-encoder adaptation and edit shortcuts. About 280 papers are in their ledgers. The web-search
budget ran out in every strand, so each file marks which venues were confirmed and which are from memory; every
citation used in the paper is checked again before submission.

## 1. What the literature agrees on

1. **Abstention cannot create discrimination.** For any policy that sees only a set of signals,
   ESG <= TV(signals | erased, signals | control) (data-processing inequality; strand 5). Our 270 screened
   policies raised net utility by referring more and left ESG flat: exactly this bound. The same pattern is published
   for general VLMs (contrastive-decoding gains on POPE come from a shift in the share of "yes" answers, Yin et al.,
   NeurIPS 2025) and for medical VLMs (calibration improves, discrimination stays, MICCAI 2025-2026).
2. **Output-level preference or consistency training mostly moves the threshold.** mDPO (EMNLP 2024): multimodal
   DPO learns preferences that ignore the image; Shrestha et al. (ACL 2020) and Teney et al. (NeurIPS 2020):
   grounding and debiasing gains come from regularisation or prior inversion, and random regions work as well. Our
   removal-DPO, GRPO and CMCC results fit this.
3. **Removal-based evaluation leaks the label through the removal itself.** ROAD (ICML 2022): where and how pixels
   were removed predicts the label; Hooker et al. (NeurIPS 2019); Hase et al. (NeurIPS 2021). Agarwal et al.
   (CVPR 2020) separate edits that must not change the answer from edits that must, which is our control edit vs
   erasure, but no medical work does this at the *same site*.
4. **Counterfactual erasures are rarely checked by readers.** Only CT-GAN (USENIX Security 2019) and Becker et al.
   (Eur J Radiol 2019) ask readers whether a removed lesion is still there; Becker shows "readers cannot tell it was
   edited" and "the finding is gone" are separate axes. No paper trains on erasures and reader-checks them.
5. **The model may know more than it says.** Linear probes on VLM internals beat the model's own answers (Zhang et
   al. NeurIPS 2024; ProjectAway and DeCo, ICLR 2025).
6. **Closest published work** (novelty threats): HEAL-MedVQA / LobA (IJCAI 2025, chest X-ray region swap, Yes->No
   flips, no control edit, no reader check, no held-out editor); MMedPO (ICML 2025, DPO with noise in the lesion
   region, accuracy only); S-VCO (ACL 2025), EMPO (EMNLP 2025), MFPO (IJCAI 2025) (minimal-pair image preference
   training, natural images); RadEdit (ECCV 2024, diffusion editing with keep masks, no readers); Teney et al.
   (ECCV 2020, gradient supervision on counterfactual pairs); interchange intervention training (Geiger et al.,
   ICML 2022). arXiv-only: CORAL, BCEA ("Look again before you abstain"), "Uncertainty is not a safety net for
   clinical VQA".

## 2. What our own stored results say (checked before choosing anything)

Recipe seed 0 (`v4q_cf_s0`), main test, 219 cases; "denies" = says absent or refers.

| Tool | denies erased | denies control | ESG | denies control, lesion found on the unedited image | erased claims pointing at the erased site |
| --- | --- | --- | --- | --- | --- |
| LaMa (training tool) | 0.881 | 0.146 | 0.735 | 0.027 (5/186) | 9/22 |
| TELEA (held out) | 0.918 | 0.219 | 0.699 | **0.129 (24/186)**, 13 of them breast ultrasound | 11/13 |
| Diffusion (held out) | 0.743 | 0.152 | 0.592 | 0.043 (7/162) | **41/45** |

- On LaMa the remaining gap is almost all perception: 33 lesions missed on the unedited image account for most
  control denials.
- On TELEA the loss is not hallucination (8% erased claims) but **edit-induced denial**: a TELEA patch elsewhere
  makes the recipe deny a lesion it otherwise finds (13% vs 3% on LaMa), concentrated in breast ultrasound.
- On diffusion, 41 of 45 erased-image claims point at the erased site: the diffusion editor may leave or regenerate
  lesion-like tissue. These images have never been reader-checked, so diffusion "claims" are not yet known to be
  errors.
- Earlier ablation: stage 1 trained on erasures **without** control edits denies 47% of TELEA control edits; the
  model readily learns "edited -> absent".
- Reader study: the recipe says absent on 9 of 13 erasures where both physicians still see the finding. Either the
  readers over-call or the model answers from the edit.

**Rival explanations** for the ESG plateau, with what distinguishes them:
R1 label noise (residual findings after erasure; reader-clean subsets), R2 a site-of-edit shortcut (erasures are
edited at the lesion, controls elsewhere: a same-site, lesion-kept edit should be denied if the model uses it), R3
inpainter fingerprint (held-out tool effects), R4 question prior (lesion-free images), R5 perception (missed lesions
on unedited images; probes on vision features), R6 threshold vs discrimination (AUROC vs denial rates).
Stage 0 (docs/FRAMEWORK_STAGE0.md) tests R2, R5 and R6 in about an hour, on validation images only.

## 3. The framework: site-matched, graded counterfactual evidence learning

One idea ties the six strands together: **the edit must be independent of the label.** Today the erasure is the only
edit at the lesion site, so "edited where the question points" predicts "absent". The framework makes every
property of the edit (tool, size, shape, *site*) carry no label information, grades how much evidence is removed,
and only then asks the model to depend on the evidence.

**Data: counterfactual quadruplets per case**, all from the same tool family:

| View | edit | lesion | target |
| --- | --- | --- | --- |
| original | none | present | present |
| erasure | lesion region | removed | absent (weighted by erasure validity) |
| same-site sham (ring) | area-matched ring around the lesion | intact | present |
| far control | lesion-shaped region elsewhere | intact | present |
| partial erasure | part of the lesion | partly removed | present, with an order constraint |

**Objective** (the component chosen by stage 0):
- L_traj: the agent's trajectories on all views (as the recipe).
- L_site: difference in differences against the **same-site** sham: softplus(tau - (s(sham) - s(erased))),
  plus invariance (s(original) - s(sham))^2 and (s(original) - s(far))^2. CMCC used only the far control, which
  leaves the site shortcut open; this is the change that stage 0 tests the need for.
- L_grade: s(original) >= s(partial) >= s(erased) (ranking hinge), so evidence is graded, not binary.
- Validity weighting: each erasure's "absent" target is weighted by an estimate that the erasure is clean
  (agreement across tools, a lesion detector on the erased region, calibrated on the reader labels); erasures
  judged unclean become "present" or are dropped (strand 3).
- Branch B only (read-out gap): the same terms on a probe over internal features (an evidence head), or an
  interchange intervention on lesion-region visual tokens (strand 4), instead of the output log-odds.
- Tool family: training tools LaMa, transplant and simple fills (blur, mean fill); evaluation tools TELEA and
  diffusion stay held out.

**Evaluation** (also a contribution): ESG site alongside ESG far; AUROC and denial rates reported separately
(discrimination vs threshold); the abstention ceiling (section 1.1) estimated from the signals; held-out tools;
reader-clean and colonoscopy (reader-supported) subsets; the 270-policy screen as the abstention baseline.

**Diagram for the paper** (one figure): left, the five views of one case with the edit masks outlined (site sham and
far control in one colour, erasure in another); middle, the shared VLM scoring s(x) on each view; right, the three
loss terms as arrows between view scores (difference in differences against the site sham, invariance to sham and far
control, the graded order), with the validity weight on the erasure arrow; below, the evaluation panel (ESG site/far,
held-out tools, reader-verified subset).

## 4. What is new against the closest work

- No published counterfactual method, medical or general, uses an edit at the **same site that keeps the finding**;
  LobA, MMedPO, S-VCO, EMPO and MFPO compare the original with the edited image only, and our own CMCC used a control
  elsewhere.
- No work trains on erasures with **reader-calibrated validity**, or grades erasures with an order constraint in a VLM.
- No work reports a **held-out-editor** evaluation with discrimination and threshold separated, or states the
  abstention ceiling for evidence removal.

## 5. Plan and costs (A100 hours)

1. Stage 0 (notebook 44): about 1 hour, validation only, no training. Decides the branch.
2. Stage 1 screen (one seed, short runs, validation dev set): the chosen objective against the matched-compute
   replay control, each loss term ablated; about 6-10 hours.
3. Stage 2 confirmation: pre-registered (rules fixed before running), three seeds, all test sets; about 25-35 hours.

## 6. If stage 0 says "perception-limited"

Then the site shortcut is not what holds ESG back, and the honest framework is about perception: the probe results
say whether the evidence is in the vision features (then train the read-out) or not (then the encoder: staged,
anchored adaptation, strand 6 F2). The evaluation contributions in section 3 stand either way.
