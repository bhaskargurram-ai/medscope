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
