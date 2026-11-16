# Response to the external review of 15 Nov 2026 ("Comprehensive Editorial Review and Submission Readiness Analysis")

| Review point | Assessment | Action |
| --- | --- | --- |
| Reader study underpowered; first-year trainees; no Stable Diffusion erasures | Correct | R5: expert pack 4 (board-certified radiologists, 216 images incl. 72 diffusion), notebook 49; limitation kept in the paper until results exist |
| Perception limit may be an artifact of the frozen encoder | Fair | Claim narrowed in the paper; R2 (vision adapters with layer-wise decay, notebook 48) and R3 (four frozen encoders compared, notebook 47) |
| "Unfreezing collapsed the model, so the authors froze it" | Inaccurate: frozen by design; the 2e-5 retry did not collapse | None beyond the text already in the paper |
| Compare against CORAL and Med-CAP | CORAL weights not public; Med-CAP is a classic VQA model (UpDn/MedCLIP) that cannot run the agent protocol | Both cited with PriVE-Bench and MedCausalX; R1 tests CORAL's training signal inside the pipeline (notebook 48) |
| CoMedPO | No such paper found | Not cited |
| Patient-level leakage | Largely answered by existing audits (crosswalk, patient bootstrap); three sources release no patient ids | New paragraph in Section 4.1 |
| Pneumothorax failure must be fixed | The v4.1 remedy already existed (27% found; failed the selection rule) | Reported as exploratory in Section 4.5 and limitations; v4 stays the reported model |
| Estimate the TV bound | Feasible as a lower bound from out-of-sample probes | R4 (notebook 47) |
| CLAIM checklist | Correct | Appendix B |
| IEEE TMI 10-page limit incl. references | Correct (ieeetmi.org submission checklist) | Venue left to the author; MedIA has no strict limit |
| Gated DeltaNet / multi-token prediction analysis | Not related to any claim | Not done |

Experiments R1-R5 are pre-registered in `docs/REVIEW_EXPERIMENTS.md`.

## Results (15 Nov 2026)
- R1 (CORAL-style swap): no pass; TELEA ESG -0.028 [-0.073, 0.017].
- R2 (vision LoRA, layer-wise decay): no pass; lesions found +0.017 [-0.034, 0.067].
- R3 (frozen encoders): Qwen's encoder best on erasure vs control edit everywhere; no alternative better.
- R4 (ceiling measured): recipe's denial gap equals the probe TV bound (no read-out gap); base model's answers use
  little of the separation its hidden states hold.
- R5 (expert readers): pending recruitment.

## Second pass (Amendment 1) results (16 Nov 2026)
- R6 (Med-CAP-style prior suppression): no pass; TELEA erased-vs-ring AUROC +0.003 [-0.018, 0.024]; the adaptive form
  lowers LaMa AUROC; the fixed form finds more lesions but lowers TELEA ESG (threshold shift).
- R7 (leakage without patient ids): reading met; after removing the 25% most similar test cases per source, every ESG
  advantage keeps its sign with the interval above zero (+0.306 to +0.456). Similarity does not identify patients
  (AUROC 0.53), so same-patient pairs that do not look alike remain possible; stated in the paper.
- R8 (v4.2 rebalanced, post hoc): passed its rule; 53/100 pneumothoraxes on new SIIM patients (v4.1 26, v4 0) with
  5/100 healthy films called positive; main test unchanged (ESG 0.740 vs 0.758, n.s.); external centres better (ESG
  +0.143); BraTS meningioma worse. v4 stays the reported model.
Paper: Section 4.6, Appendix Table 4, Fig. 4B.
