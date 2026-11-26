# How papers of this kind are written: patterns from 37 published papers

Prepared 26 Nov 2026 for manuscript v6. Four groups of papers were read in full (main text) and their craft noted:
how they order an argument, report an estimate, label a planned analysis and report a result that did not confirm.
This file is the synthesis; it supplements `docs/PAPER_STANDARD.md`. Every manuscript revision is checked against
both. Nothing here is quoted from the papers.

## Papers read

**Clinical-journal evaluations of language and vision-language models, with readers (9).** Brin, Eur Radiol 2024;
Zhou, Radiology 2024; Jin, npj Digit Med 2024; Tanno, Nat Med 2024; Christensen, Nat Med 2024; Bluethgen, Nat Biomed
Eng 2024; Goh, JAMA Netw Open 2024; Eisemann, Nat Med 2025; Huang, JAMA Netw Open 2023.

**Papers that expose a hidden failure of imaging AI (9).** Zech, PLoS Med 2018; Winkler, JAMA Dermatol 2019;
Oakden-Rayner, ACM CHIL 2020; DeGrave, Nat Mach Intell 2021; Gichoya, Lancet Digit Health 2022; Seyyed-Kalantari, Nat
Med 2021; Yang, Nat Med 2024; Perez-Garcia (RadEdit), ECCV 2024; Banerjee, JACR 2023.

**Benchmarks and stress tests of vision-language models (10).** Yan (ProbMed) 2024; Xia (CARES) 2024; Chen
(Med-HallMark) 2024; Gu (MedVH) 2024; Jin, npj Digit Med 2024; Gu et al. (The Illusion of Readiness in Health AI)
2025; Nan (RadVUQA) 2024; Guan (HallusionBench) 2024; Li (POPE) 2023; Buckley, Nat Commun 2026. Lotfinia et al. 2026
(chest-radiograph audit with swaps, occlusions and radiologists) was read in part; it is the closest prior work.

**Model development with external validation, in the target journals, and colonoscopy AI (9).** Wang, Gut 2019; Ren,
Radiol Artif Intell 2024; Boyd, Radiol Artif Intell 2024; Saha (PI-CAI), Lancet Oncol 2024; Wu (RadFM), Nat Commun
2025; Urban, Gastroenterology 2018; Zhou (RETFound), Nature 2023; Sellergren (MedGemma) 2025; Hu, Med Image Anal 2024.

## The rules

### Title, abstract, introduction

1. **Title.** A descriptive phrase of 8 to 14 words, or a claim sentence; the design may follow a colon. No question
   mark, no slogan, no method adjective, no product name unless the product is the thing under test.
2. **Abstract.** Context; the gap in one "however" sentence; what was done, with what was held out and how large each
   part is; results as estimate, interval, comparator, in the order of the methods; one scoped conclusion. Every
   percentage carries its denominator or its interval. The headline number stands next to the value a trivial
   strategy earns. The sentence that rules out the obvious objection is in the abstract, with its number.
3. **A result that did not confirm goes in the abstract** in the same sentence form as the ones that did; the
   conclusion then carries the restriction.
4. **Introduction.** Three or four paragraphs that narrow: the clinical problem; what is known and its limit; the gap
   as a logical limit of what current measures can show (not "one more benchmark"); the aim. No results and no
   numbers of our own. The last paragraph states the purpose with one verb per study component. No bulleted list of
   contributions; no "novel", no "first" (at most one "to our knowledge").
5. **Position against the closest work in one sentence each**, by what is held fixed and what is changed, and in one
   compact comparison table with decisive columns.

### Methods

6. **Data before model.** Each dataset with its role, the unit of splitting and each leakage control with its
   purpose. "External" is always attached to a named centre or dataset with counts.
7. **Define each construct once, in one sentence, at first use**, and call a proxy a proxy. Introduce each edit by
   what it holds fixed and what it changes, and name the matched control as the control.
8. **Say what a model that uses the image should do and what one that does not should do**, before the test.
9. **Each model variant, control or ablation is introduced by the question it answers**, in one sentence. Names are
   fixed once, encode the one factor that differs and never change. State a default referent. Variants that are not
   carried forward appear once, in one table, with the selection rule stated before the result.
10. **Readers as a checklist:** number, specialty, certification, years, independence, what they saw and were not
    told, order of cases, the exact questions, and what counts as the reference standard. "Reference standard", not
    "ground truth".
11. **When choices were frozen.** One plain sentence saying the analysis plan, the decision rules and the model
    selection rules were fixed and dated before the data they apply to were seen, where the record is, and which
    analyses were added afterwards. Then label each analysis **pre-specified** or **post hoc** twice: in Methods and
    again where its result is reported. No version numbers of the plan in the main text; the dated list is one
    supplementary table.
12. **A statistics paragraph a reviewer can tick off:** primary outcome, the test or resampling for each comparison,
    what unit is resampled, the number of resamples, two-sided level, how multiple comparisons are treated, software.
    Say which source of variation each interval reflects (test cases, training seeds, folds) and never mix them.
13. **Closed models are unstable instruments:** identifiers, access dates, decoding settings and the prompt are
    given exactly.

### Results

14. **Order Results as Methods were ordered.** Internal before external, edited before unedited, the same measures
    and the same sentence shape in each. Open each subsection with the finding and its table or figure.
15. **One reporting template throughout:** each arm's estimate, then the difference, the 95% interval and the P
    value, in one sentence; n of N with every proportion; "percentage points" for differences between percentages.
16. **Report the share of "present" answers on unedited lesion-free images** next to the headline, so that the
    result cannot be read as a model that says yes, or no, to everything.
17. **Give the alternatives their own block**, strongest first: name the alternative, say why it is plausible, make
    one design change that removes it, report whether the effect persisted. End on the explanation the data fit
    best, never on proof.
18. **Results that did not go our way** take the same form, length and place as the ones that did: estimate, then
    the plain verdict, then at most one tentative reason marked "may". Non-significance is shown by the interval;
    never "trend", never "similar" without a margin. The residual in the improved model is reported next to the
    improvement.
19. **A counted failure analysis** follows any weaker external number; no adjective stands in for the count.
20. **Show the whole programme once**, in one table or figure, so the reader can see that nothing was left out.
21. **Captions are self-sufficient:** what is shown, which dataset and n, what the intervals are, abbreviations
    expanded. Interpretation stays in the text.

### Discussion

22. **First paragraph:** what was done and the headline numbers in two or three flat sentences, including the one
    that went against us; then what the result does not mean.
23. **Comparison with prior work** quotes the earlier studies' numbers and explains a discrepancy when there is one.
24. **Limitations are one paragraph near the end, three to six items, enumerated**, each followed by a fact that
    bounds it: the design reason, the direction of the bias, the analysis done, or what would resolve it.
25. **Close on what evidence is still needed.** No new claim, no call to action about the field. The conclusion is
    never more positive than the Results.

### Words

- Results: "showed", "was higher than", "did not differ", "did not show". Interpretation: "suggests", "is consistent
  with", "may", "is likely". "Significantly" only with a test. "Comparable" only when no superiority test was passed
  and the interval is given.
- Models "answered", "reported", "changed the answer"; they do not "see", "understand" or "know".
- Not used: novel, first, state-of-the-art, robust (of our own findings), rigorous, crucial, alarming, drastic,
  meticulous, comprehensive, leverage, delve, trend toward, ground truth, outperforms (without a test).
- No lab-notebook language in the paper: no check numbers, no pilot or screening jargon, no notebook or commit
  names in the running text.
