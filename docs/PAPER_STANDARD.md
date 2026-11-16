# Writing standard for the MedScope papers

Adopted 15 Nov 2026 from the pre-submission checklist of Touhid Alam's "Q1 Paper Anatomy" teaching editions
(https://github.com/Touhid-Alam/Q1-Paper-Anatomy). Every manuscript revision is checked against it. The second column
says where `paper/v2/paper.tex` meets each item.

| Item | Where the paper meets it |
| --- | --- |
| **1. Gap -> Fix -> Verify chain.** Related work synthesises methodological weaknesses; every gap and contribution maps to a method section and to a table, figure or ablation. | Table 1 (gap, what the framework adds, where tested, finding); Section 2 ends each part with the gap it leaves; Table 2 compares the closest work point by point. |
| **2. Data provenance and zero leakage.** Say why each dataset; split before any preprocessing or augmentation; split clinical data by patient; fit scalers, grids and thresholds on training folds only. | Section 4.1: why these sources; "Data leakage and patient-level splits" (split before any view is built, every fitted quantity on training or validation only, per-patient splits where ids exist, cross-set audit, patient bootstrap); review check R7 (similarity-based exclusion where ids do not exist). |
| **3. Defensive tables and figures.** Literature table with validation and limitation columns; design table with a justification column; captions state the takeaway. | Table 2 (validation, limitation); Table 4 (design choices: value, why, where checked); every figure caption opens with its finding. |
| **4. Fair baselines and controls.** Identical splits, seeds and preprocessing; equal-volume baselines; general and clinical-cost metrics. | One agent loop, prompt, tools and image size for every model; matched-compute controls for every arm; the "absent"-matched arm; ESG, claims, CCR, net utility under a cost matrix and five alternatives. |
| **5. XAI and error analysis.** Report what the analysis found; validate it; analyse failure modes. | Probes report where separation is and is not (Sections 4.5, 4.6); the encoder comparison; "Where MedScope-4B fails" (Section 5.2); pneumothorax audit. |
| **6. Calibrated tone and reproducibility.** No hyperbole; hedged priority claims; specific limitations; seeds, hardware, dataset links and code archived. | Hyperbolic adjectives removed (15 Nov); limitations numbered and specific; Reproducibility Statement with data availability (sources and the copies used), seeds, hardware, software versions and per-view outputs. |

Checks for every new section, table or figure:
- Does it close a gap named in Table 1, and does Table 1 point to it?
- Is every number traceable to `docs/RESULTS_LOG.md` or a stored output?
- Is every fitted choice made on training or validation data, and is that said?
- Does the caption open with the takeaway?
- No "novel", "first", "rigorous", "robust", "crucial", "severe", "demonstrates" where "suggests" or a plain verb fits.
