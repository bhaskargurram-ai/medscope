# Framework stage 1: pre-registration of the tool-family screen (written 14 November 2026, before any arm is trained)

**Why.** Stage 0 (docs/FRAMEWORK_STAGE0.md, RESULTS_LOG 14 November) met its rule for a site shortcut on TELEA. On
cases both models find, however, training mainly doubled the recipe's sensitivity to TELEA edits wherever they are
(ring 12.5% vs 6.2%, far 8.9% vs 4.5%), with no clear site-specific part. One objective covers both readings: make
**the edit tool and the edit's site carry no label information** during training, so that an unfamiliar tool's
patch is not read as "the lesion is gone".

## Arms (one seed, a screen; continuing the seed-0 recipe adapter `v4_s1/final`)

All three use `scripts/train_cmcc.py` with the same training cases (all 2,739 triplet cases: `--cases 3000` is capped at the 2,739 available, as the control's state.json records), order, learning rate (2e-5), gradient
accumulation (8), lesion-free replay (one every 3 cases) and seed (0). Only the views or the paired-view weights
differ.

| Arm | views of each case | paired-view terms |
| --- | --- | --- |
| `v4q_sftc_s0` (control, already trained) | stored LaMa erasure and far control (transplant cases as stored) | none |
| `v4q_tfr_s0` (tool-family replay) | erasure and control made with one tool per case, the control far or in a ring around the lesion | none |
| `v4q_tfc_s0` (tool-family CMCC) | as `v4q_tfr_s0` | difference in differences, control invariance, first-action term (tau 2.0, weights 0.5) |

**Tool family** (`medscope/fw/toolfamily.py`, `medscope/data/fills.py`): each LaMa case gets one tool and one
control site from a hash of its id: tool in {LaMa, blur (normalised convolution), mean fill with matched noise,
shuffled surrounding pixels}, site in {far (as the benchmark), ring (area-matched, 2 pixels around the lesion,
lesion intact)}; the erasure and the control use the same tool. LaMa-far cases keep their stored views; transplant
cases are kept as stored; a case whose control has no room keeps its stored views. **TELEA and the diffusion
inpainter are not used in training** (held out).

## Evaluation (validation dev set only; the test sets are not touched)

The agent's generated answers (greedy, benchmark prompt) on the stage-0 dev views: 179 validation lesion cases with
yes/no questions (unedited image; LaMa erasure and far control; TELEA erasure and far control; LaMa and TELEA ring
edits) and 80 lesion-free validation images. Control `v4q_sftc_s0` and both arms are run the same way.
`medscope/fw/stage1.py` computes, arm minus control, paired by case (bootstrap 95% intervals, 4,000 resamples):
ESG per tool = P(denied | erasure) - P(denied | far control) on all cases; control-edit denial among cases both
models find unedited; ring denial (descriptive); share of unedited lesions found; share of lesion-free images claimed.

## Rule (fixed now)

An arm **passes the screen** when, against `v4q_sftc_s0`, all of these hold:
1. TELEA ESG rises by at least 0.03;
2. TELEA control-edit denial (cases both find) falls by at least 0.03;
3. LaMa ESG falls by no more than 0.02;
4. the share of unedited lesions found falls by no more than 0.03;
5. the share of lesion-free images claimed rises by no more than 0.03.

A passing arm (if both pass, the one with the larger TELEA ESG gain) goes to a separately pre-registered
confirmation: three seeds, the full test sets, the held-out TELEA and diffusion test sets, and the reader-verified
subset. No arm passing ends this line: the paper reports the screen as a negative result. The recipe and CMCC
(`v4q_cmccn_s0`) may be compared the same way as references (descriptive only). Results go into
`docs/RESULTS_LOG.md` whichever way they fall.
