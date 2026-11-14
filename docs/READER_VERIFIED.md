# Reader-verified analysis of the main test (written 14 November 2026, before any model was scored this way)

Two physicians (trainees, 1 year each) read pack 2 of the reader study (128 main-test images: 32 each of unmodified
lesion images, LaMa-erased images, control-edited images and unmodified lesion-free images; key
`reader/key_v2.json`). The pre-registered erasure criterion failed (about 40% of erased images still showed a
finding to both readers). This analysis uses the readers' judgement as the label instead of assuming every erasure
is clean, as `docs/PREREGISTRATION_v8.md` already planned for its new cohort.

## Definitions (fixed now)

- **Reader-clean erasure** (primary): neither reader answered "yes, the finding is there" (each said "no" or
  "cannot tell").
- **Majority-clean erasure** (secondary): not both readers answered "yes".
- **Residual erasure**: both readers answered "yes".
- **Reader-confirmed lesion**: an unmodified lesion image or control-edited image that at least one reader called
  present; **reader-confirmed healthy**: a lesion-free image that neither reader called present.

## What is computed, for every model run on the main test with the benchmark prompt

On exactly these images (the stored replies; no model is run): the share of reader-clean, majority-clean and
residual erasures on which the model still claims the finding; its sensitivity on reader-confirmed lesions; its
claims on reader-confirmed healthy images. Exact 95% intervals per model; the frontier models are also pooled with
a bootstrap over images (2,000 resamples, seed 0), since all models read the same images.

## How the result will be read (fixed now)

- The paper's headline ("frontier models claim erased findings") **holds on reader-verified images** if the pooled
  frontier-model claim rate on reader-clean erasures has a 95% lower bound above 20%.
- It **does not hold** if that lower bound is 20% or less; the headline is then restated as a claim about edited
  images only.
- Separately reported: whether models claim residual erasures more often than clean ones (a model that tracks what
  physicians see should).

Two trainee readers and a small verified set (about 10 reader-clean erasures in pack 2) make this a limited check;
pack 3 and senior readers would enlarge it. Results go into `docs/RESULTS_LOG.md` whichever way they fall.
