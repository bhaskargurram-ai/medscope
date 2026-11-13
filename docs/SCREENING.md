# Fast screening funnel (written 13 November 2026, before stage A was run)

After eight method runs since the preprint, none meeting its pre-registered rule, ideas are screened cheaply before
any long run. The test sets (main test, external centres, fresh external, held-out tools) are **not used** in any
screening stage; they are used once, for the final 1-3 ideas, under a new pre-registration.

| Stage | What | Data | Cost |
| --- | --- | --- | --- |
| A | Decision policies on the stored agent reports (rules and small learned combiners) | validation views | CPU, minutes |
| B | Inference-time ideas needing new model answers (prompts, test-time averaging, a second reader, thresholds) | 300 validation views + held-out-tool erasures of validation cases | 1-2 h GPU |
| C | Short training variants | validation | 2-3 h GPU |
| Final | 1-3 shortlisted ideas, pre-registered, run once | all test sets | 5-10 h |

**Pass rule for stage A (fixed now).** Against keeping the direct reader's answer (the recipe): net utility +0.03
or more **and** evidence sensitivity gap +0.02 or more, sensitivity on unedited lesions (CCR) not lower by more than
0.03, claims on lesion-free images not higher by more than 0.03. The ESG condition is there because every failed
method so far moved the answer threshold without separating erased from present lesions better. A policy is picked
on half A of the validation cases (split by a hash of the case id) and must pass again on half B. Learned combiners
are fit on half A only (their half-A numbers come from two-fold cross-fitting inside A).

**Known weakness.** The validation erasures were made with LaMa, the verifier's own inpainter; policies using the
verifier must hold on held-out-tool erasures (stage B data) before they go further.

**Reporting.** Every stage's number of ideas screened and passed goes into the paper.
