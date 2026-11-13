# MedScope v10 pilot: a counterfactual multi-agent reader (lead 4)

Written and committed on 13 November 2026, before any component below was trained or run. The git history of this
file is the record. This is a **pilot**: one seed, test sets that earlier experiments have already used. A go signal
justifies a separate confirmatory pre-registration (three seeds, matched control), not a claim in the paper.

## Why

Five training changes (C1-C4, lead 2) did not beat plain supervised training on counterfactual views, and lead 3
(GRPO) narrowly missed its go signal. All of them change what one model does in one pass. The paper's weak point is
perception (0-10 of 48 pneumothorax films found on the fresh external set) and question-driven claims. Lead 4 changes
the structure instead: several agents, each built to remove one known cause of a false claim, and a deciding agent
that weighs them.

## Prior work this must be distinguished from (checked 13 November 2026)

- **Counter-evidence verification** (Zhou et al., MICCAI 2026): grounds each claim with MAIRA-2, blacks out the region,
  re-queries the model, and treats a claim that survives as language-driven. Training-free, chest X-ray only, and
  **no matched control edit** (a reviewer asked; the authors deferred it). A black mask is itself an unusual input,
  so a changed answer may be a reaction to any edit.
- **Counterfactual visual grounding uncertainty** (Song et al., arXiv 2606.28520): text-level counterfactual
  descriptions on the unmodified image; detection only.
- **Multi-agent / expert-tool medical VLMs** (VILA-M3, RadAgents, PASS): specialist models and agents, no
  hallucination test under erasure.

What lead 4 adds, and what the go signal tests: (1) a **matched control edit** in the verifier, so a claim counts as
image-supported only if it disappears when its region is erased *and* survives an equal edit elsewhere; (2) a
**question-blind reader**; (3) a **trained** deciding agent; (4) evaluation on five imaging types with **erasures
made by inpainting tools the system never uses** (held-out tools).

## The system

All language agents are Qwen3.5-4B. The sub-agents use the frozen stage-1 recipe adapter (`adapters/v4_s1/final`,
seed 0); only the deciding agent is trained.

1. **Direct reader**: the recipe adapter answers the question as asked (this is the recipe itself).
2. **Question-blind reader**: the recipe adapter is asked only "Is there any abnormality in this image?", so the
   finding named in the question cannot drive its answer.
3. **Specialist**: a lesion segmenter (DeepLabV3, ResNet-50, ImageNet-initialised), trained only on the unedited
   training images and their lesion masks plus the training natural negatives, never on edited images. Reports up to
   three regions with scores, or that nothing passed its threshold. The image-level threshold is fixed on a
   patient-disjoint 10% of the training images (Youden's J) before any test image is seen.
4. **Counterfactual verifier**: takes one region to test (the direct reader's box if it gave one, otherwise the
   specialist's top region if above threshold, otherwise the blind reader's box; none = nothing to verify), erases it
   with LaMa (the training inpainter), places an equal-shaped edit elsewhere on tissue with the same rule used to build
   the control views, and asks the direct reader the original question on both images. Reports both answers.
5. **Deciding agent (arbiter)**: sees the image, the question and the four reports and gives the usual final action
   (answer, clarify, refer). Trained by supervised fine-tuning from the recipe adapter on 4,000 training views
   (stratified by view kind, fixed seed) with the real reports of agents 1-4 on those views and the gold final action
   as the target; 2 epochs, learning rate 1e-4, the recipe's schedule shape. During training each of reports 2, 3 and
   4 is left out with probability 0.25, and the verifier's control half with probability 0.25, so the ablations below
   are inputs the arbiter has seen. Run name `v4q_mas_s0`. Reports never use the gold answer.

Degraded views go through the same pipeline; the arbiter is trained to ask for a clearer image on them.

## Arms and ablations (fixed now)

| Run | Reports given to the arbiter |
| --- | --- |
| `v4q_mas_s0` (full) | 1, 2, 3, 4 |
| `v4q_masnob_s0` | 1, 3, 4 (no question-blind reader) |
| `v4q_masnos_s0` | 1, 2, 4 (no specialist) |
| `v4q_masnov_s0` | 1, 2, 3 (no verifier) |
| `v4q_masnoc_s0` | 1, 2, 3, 4 without the control half (verification as in Zhou et al.) |
| `v4q_masdir_s0` | 1 only (arbiter training without the other agents' evidence) |

Comparators: the recipe `v4q_cf_s0` and the replay-only continuation `v4q_sftc_s0` (extra training from the same
adapter, the control of C4; its compute is not matched to the arbiter's, so `v4q_masdir_s0`, the same arbiter
training with the other agents' reports withheld at test time, is the closer check that the agents, not the extra
training, carry any gain). The full system is tested on the main test, the external centres, the
fresh external set and the two held-out tools (TELEA, diffusion); the ablations on the fresh external set and the two
held-out tools.

**Circularity.** The verifier erases with LaMa, which also made the main-test erasures, so a verifier could react to
LaMa's own traces there. The go signal therefore uses only the held-out tools (TELEA, diffusion) and the fresh
external set; the main test is reported as a guard-rail.

## Go signal

On the two held-out tools pooled (TELEA + diffusion, all cases), `v4q_mas_s0` against `v4q_sftc_s0`:

- net utility higher by at least 0.05, **and**
- erased-lesion claims not higher (point estimate), **and**
- sensitivity on unedited lesions (CCR) not lower by more than 0.03;

and on guard-rails: healthy-image claims on the main test not higher by more than 0.03, and CCR on the fresh external
set not lower than the recipe's by more than 0.03.

**Which agent carries it.** An agent counts as contributing if removing it lowers pooled held-out net utility by at
least 0.03. The matched control counts as contributing if `v4q_masnoc_s0` has erased-lesion claims or net utility
worse than the full system by at least 0.03 on the pooled held-out tools. If the gain is there but no single
agent's removal costs 0.03, the result is reported as "the combination, not any one agent".

**Also reported** (not part of the go signal): the specialist's own claim rate on erased versus unedited and
control-edited images (its own evidence sensitivity gap); how often the arbiter overrides each agent; SIIM pneumothorax
detected on the fresh external set; extra compute per case.

## What is not claimed

One seed, reused test sets, erasures checked by one trainee reader so far. A go signal leads to a confirmatory
pre-registration (three seeds, a matched-compute control trained on the same views without reports) and nothing more.
Departures from this plan are logged in `docs/RESULTS_LOG.md`.
