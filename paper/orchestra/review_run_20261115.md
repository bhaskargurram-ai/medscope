# Check of the PaperOrchestra draft (run of 15 Nov 2026, final_paper.pdf, 27 pages)

Every number, figure and reference was checked against `docs/RESULTS_LOG.md`, the preprint (`paper/method_paper.tex`), the
reader answer files and `docs/litreview/`. **Tables 3–15 match the data exactly; Figures 2 and 3 match the data.**
What follows must be fixed before the draft is shared.

## A. Must fix: wrong or invented content

| # | Where | Problem | Correct |
| --- | --- | --- | --- |
| 1 | Figure 4A | Most arm positions are not data: e.g. multi-agent v10 plotted at held-out CCR ≈ 73% (its held-out CCR was the control's +0.022), GRPO, rank-64 and vision-LoRA points have no held-out CCR/claims pair in the log, tool-family arms are validation numbers drawn on held-out axes, the "270 policies" ellipse is invented. "Iso-ESG contours" on CCR-vs-erased-claims axes are meaningless (ESG is not a function of those two). | Replace with a plot of real paired differences (arm − its control: ΔESG and Δerased claims, with CIs) only for arms that have them; screening funnel as its own panel. |
| 2 | Figure 1 | Image-generator text errors ("DPD, CMCC, GBPO", "corve seik", "Agpot Ouput", "MedScope-48", "Usabie"); wrong numbers ("129 images", should be 128; "claim 48%", should be 45%); example "medical" images are generated, not from the data. | Redraw as a clean vector diagram (TikZ), real example views or none. |
| 3 | References | Wrong or invented entries: **MedHEval** (fake arXiv id 2409.12345; actual Chang et al., arXiv:2503.02157, 2025); **Med-HallMark** (fake id 2408.09876; actual Chen et al., arXiv:2406.10185, 2024); **HEAL-MedVQA** (invented authors "Lim" and id 2410.01234; actual Nguyen et al., "Localizing Before Answering…", IJCAI 2025, arXiv:2505.00744); **MMedPO** (wrong id/year; actual Zhu et al., ICML 2025, PMLR 267); **S-VCO** (wrong authors/id/year; actual Wu et al., ACL 2025); **ChestX-Det** (cites the ChestX-Det10 note; the dataset paper is Lian et al., IEEE TMI 2021); **ProbMed** (garbled authors "Xuehai and"; venue Findings of ACL 2025); **self-citation** (wrong title; actual "Seeing Is Not Believing: Counterfactual Lesion Erasure Teaches a Small Medical Vision–Language Agent to Report Only What the Image Shows"). EMPO and MFPO are named without citations. | Replace with the verified entries (venues from `docs/litreview/`). |
| 4 | §4.2, Fig. 5B2 and caption | "all nine frontier models remain flat within ESG 0.20–0.56 in every lesion-size quartile" | It was the **three flagships** (gemini-4-argon, Claude Opus 5.5, gpt-6-astra). |
| 5 | §4.5 pneumothorax | Lists low resolution as a cause ("hurt early stages"); says the abnormality is "partially perceived but suppressed under the specific term". | The preprint's analysis: resolution does **not** explain the final model's miss (0% at 256 px and at full resolution). The abnormality question shows it registers something; it does **not** identify the cue. |
| 6 | §1 contribution 4, §5.1 | "finding on 54.7% of pooled reads (13/32 by majority) **outside colonoscopy**" | Both numbers are over **all** sources, colonoscopy included. |
| 7 | §4.4 GRPO | "breaches the healthy-image claim guard (+0.054)" | The go signal was missed on **erased-lesion claims** (+0.022 vs control); the main-test healthy guard (+0.021) passed; +0.054 is fresh-external healthy claims. |
| 8 | §4.2 tools off | Net utility falls "due to fewer grounded boxes on small lesions" | Log: it says "absent" more often on lesion views (21% vs 15%). |
| 9 | App. A.2 | The five cost matrices are described as varying the penalty −1 to −4, the grounding bonus and tool costs. | Actual: wrong-answer penalty −2, −1, −0.5, plus two referral variants (referral on lesion-free images paid 0; referral −0.3 everywhere). |
| 10 | Abstract, §1, §4.4, §5.2, Fig. 4 caption | "270 **post-hoc** decision policies" | They were screened on validation data under a pass rule fixed before the screen (App. A.1 itself says pre-registered). |
| 11 | §2.4, §4.4 | Abstention ceiling "validated empirically" / "exactly as predicted by Proposition 1" | The total-variation distance was never estimated; the flat ESG is **consistent with** the bound, not a verification of it. |
| 12 | §4.3, §5.1 | Stable Diffusion "hallucinates / regenerates lesion-like textures inside the mask" | Only that 41/45 claims point at the erased site; diffusion erasures were never reader-checked (could be residual or regenerated tissue). |

## B. Should fix: overstatement or inaccuracy

| # | Where | Problem | Suggested |
| --- | --- | --- | --- |
| 13 | §2.4, §4.5, §5.2, Fig. 4C | "the frozen vision encoder already extracts nearly all separation; SFT simply aligns the read-out"; "discrimination bounded by the vision representation" | Probes were on the language model's hidden states, not the encoder. Supported: no read-out gap (≤ 0.028), base-model features nearly as separable (0.83–0.87 vs 0.85–0.90). |
| 14 | §5.1 | "unambiguous proof"; secondary signs (mass effect, oedema, pleural asymmetry, acoustic shadowing) stated as what readers saw; the 9 lesion-specific residual items explained by "surrounding cues or incomplete mask coverage" | Readers gave no reasons: present these as hypotheses; "strong evidence" instead of "unambiguous proof". |
| 15 | §3.2 | CCR = "Correct Classification Rate" | "covered-and-correct rate" (share of answerable views answered correctly). |
| 16 | Fig. 5, Table 8, App. B.4 | Readers called "residents" | Known: internal medicine and radiology, 1 year each ("trainee physicians"). |
| 17 | App. B.3–B.4, Fig. 5B2 box | Mentions "Table 13 of the experimental log", "Table 8" etc. | Remove references to the input log. |
| 18 | §3.1 QC | "ResNet-18 texture classifier" for adversarial filtering | Log: "a texture classifier"; the ResNet-18 is the separate edit detector (AUC 0.83). |
| 19 | Abstract, §1 | "p < 0.001 across all 27 primary comparisons" | 26 with no resample crossing zero; net utility vs gemini-4-argon p = 0.001: write "p ≤ 0.001". |
| 20 | Table 2 | Fresh external "168 masked / 148 lesion-free" | Log: 168 lesion cases and 150 lesion-free images built, 316 cases evaluated; check the 148 from the stored views before keeping it. |
| 21 | Fig. 5A3 | Unlabelled MedScope bar on majority-clean erasures | No such number in the log: remove or compute it from the stored replies. |
| 22 | §4.1 | "exact API request/response logs are archived" | "stored per-view transcripts and scored outputs". |
| 23 | Table 6 | Multi-agent v10/v11 "control baseline: Stage-1 Recipe" | Held-out comparisons were against the replay-only control `v4q_sftc_s0`; CCR guards against the recipe. |
| 24 | Table 15 | "CMCC (Stage 1)" | CMCC continues the stage-1 recipe adapter ("CMCC continuation"). |
| 25 | §4.5 | κ = 0.10 "chance-level" | "slight agreement". |
| 26 | §4.1 | SLAKE "abdominal/pelvic CT and MRI" | SLAKE CT/MRI (several body regions). |

## C. Checked and correct

Tables 3 (main test), 4 (stage-1 arms and factorial), 5 (held-out tools and loss breakdown), 7 (stage 0 and probes), 8
(readers), 9 (generalisation and pneumothorax), 10–15; Figure 2 (both panels); Figure 3 (all panels); Figure 5A1, A2,
B1; Proposition 1 and its proof; the pre-registration timeline in App. A.1; dataset, protocol and training details in §3.
