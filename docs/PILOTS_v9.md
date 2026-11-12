# MedScope v9 pilots: adapting the vision encoder, and reinforcement learning with checkable rewards

Written and committed on 11 November 2026, before either arm was trained. These are **pilots**: one seed each,
exploratory, on test sets that earlier experiments have already used. Nothing here is a confirmatory result. A lead
that meets its go signal gets a separate pre-registration (three seeds, matched control) before it can enter the
paper as a finding.

Both leads come from correspondence with Yixiao He (first author of the removal-based preference-training baseline
used in this paper), who suggested that low-rank adaptation may be too restrictive for visual capabilities and that
online reinforcement learning with verifiable rewards may suit a task whose outcomes can be scored by rule.

## Lead 2: can the model learn to see more? (notebook 39a)

**Why.** The paper's main weakness is perception: MedScope-4B detected 0 of 48 pneumothorax films on the fresh
external set and trails frontier models on real lesions at new centres. Every arm so far used a rank-16 adapter on
the language model with the vision encoder and projector frozen, so no arm could change what the model perceives.

**Arms** (stage 1 only, seed 0, the pre-registered stage-1 recipe otherwise unchanged: same views, steps, schedule):

| Run | Adapter |
| --- | --- |
| `v4q_cf_s0` (exists) | rank 16, vision frozen: the recipe |
| `v4q_r64_s0` | rank 64, vision frozen: the capacity control |
| `v4q_r64v_s0` | rank 64, with adapters on the vision encoder and projector as well |

The vision encoder is adapted through low-rank adapters, not fully unfrozen: full fine-tuning of the 4B model does
not fit a 40 GB GPU, and adapter weights keep the released-model format. If this pilot is positive, full unfreezing
of the vision encoder is the next step.

**Go signal** (`v4q_r64v_s0` against `v4q_r64_s0`, and both against the recipe): higher sensitivity on unedited
lesions on the fresh external set (CCR up by at least 0.05) or any SIIM pneumothorax detected at stage 1 beyond the
recipe's 10 of 48, **without** erased-lesion claims rising by more than 0.03 on the main test or the held-out tools.
If the rank-64 control alone gives the gain, the result is about capacity, not about vision.

### One declared retry of the vision arm (notebook 39d), written on 11 November 2026 before it ran

**What happened.** `v4q_r64_s0` matched the recipe (no gain from capacity). `v4q_r64v_s0` collapsed: ESG 0.000 on
every set, answers fixed by the question's wording. Notebook 39c ruled out a save or load fault (692 saved adapter
tensors, 196 of them on the vision side and non-zero, all loaded equal to the saved values; loss of the loaded model
on 200 training views 0.235 against 0.179 for the frozen-vision arm). The collapse is a property of the trained
model. The mean training loss did not reveal it because most target tokens are format tokens.

**Hypothesis.** The vision adapters were trained at the language model's learning rate (2e-4). That is high for a
pretrained vision encoder and may have degraded its features early, after which the language model fitted the
question-conditional answer rates.

**The retry.** `v4q_r64vl_s0`: as `v4q_r64v_s0` (rank 64, adapters on the vision encoder and projector, seed 0, same
views, order, steps and schedule), with the vision-side adapters at one tenth of the learning rate (2e-5 peak, same
warm-up and decay shape; `--vision-lr-scale 0.1`). Language-side adapters unchanged at 2e-4.

**Rule.** Same go signal as above, against `v4q_r64_s0` and the recipe. This is the only retry: if the arm collapses
again or misses the go signal, lead 2 with low-rank vision adapters is closed as negative and no other learning
rate, rank or schedule is tried under this plan. A full unfreeze of the vision encoder would be a new plan.

## Lead 3: reinforcement learning with the cost matrix as reward (notebook 39b)

**Why.** Four training ideas built on supervised or preference losses did not beat plain supervised training on the
counterfactual views. The cost matrix already scores every episode by rule, so the agent can be trained on its own
sampled episodes (GRPO). An early GRPO attempt (notebook 05) gave no learning signal, but it predates the
counterfactual views, the current reward and dynamic sampling of groups with signal.

**Arm.** `v4q_grpo_s0`: the seed-0 recipe adapter continued with GRPO on the stage-1 lesion cases (base views and
transplant copies) with lesion-free images mixed in at 20%; 150 steps, 4 groups with signal per step (up to 12
drawn), 4 episodes per group, learning rate 1e-5, KL weight 0.05 to the starting adapter. Brain MRI (TCGA-LGG) cases
are left out of the reward: the one reader so far judged erased glioma slices as still showing a finding more often
than healthy slices (3 of 7 against 1 of 7), so those labels are the least trustworthy.

**Comparison.** Against the replay-only continuation `v4q_sftc_s0` (the matched-compute control of C4, same starting
adapter) and the recipe `v4q_cf_s0`.

**Go signal:** on the pooled held-out tools, erased-lesion claims not higher than the control's and net utility
higher by at least 0.05, with sensitivity on unedited lesions not lower by more than 0.03; and no rise of more than
0.03 in healthy-image claims on the main test. The training log must also show groups with signal in most steps;
if it does not, the pilot is reported as "no learning signal" again.

## What is not claimed

One seed, reused test sets, labels checked by one trainee reader. A pilot that meets its go signal justifies a
confirmatory run and nothing more.
