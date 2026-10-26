# MedScope — developer notes

## Goal
Train a 4B open medical VLM agent (base: Qwen3.5-4B) with RL so it answers only with visual evidence, and otherwise zooms, asks for clarification or refers. Plus MedScope-Bench, a counterfactual benchmark. Compute budget: Google Colab (L4/A100). Evaluation is fully automated — no human annotation, no clinician review.

## Conventions
- Python 3.10+, type hints, dataclasses. Core package depends only on numpy, pillow, opencv-python-headless, pyyaml.
- Heavy deps (torch, transformers, trl, peft, unsloth) are optional and imported lazily inside `medscope/train/`.
- Images are `np.ndarray` uint8, HxWx3 RGB. Masks are bool HxW.
- Boxes everywhere are `[x1, y1, x2, y2]` ints normalised to 0–1000 on the image the model saw.
- View kinds: `original`, `target_removal`, `random_removal`, `degraded`.
- Final actions: `answer`, `clarify`, `refer` (`abstain` is accepted and treated as `refer`).
- Credentialed PhysioNet data (VinDr, MIMIC) must never be sent to external APIs.

## Commands
- Tests: `python -m unittest -v` (pytest also works if installed)
- SLAKE manifests: `python scripts/prepare_slake.py --root <slake dir> --out <dir>`
- Build views: `python scripts/build_views.py --manifest <cases.jsonl> --out <dir> [--inpainter lama]`
- Quality checks: `python scripts/check_views.py --views <views.jsonl> [--dedup-against <train views.jsonl>]`

## Layout
- `medscope/data/schema.py` case and view records
- `medscope/data/counterfactual.py` view generation
- `medscope/data/inpaint.py` Telea (CPU) or LaMa (GPU) inpainting
- `medscope/data/quality.py` automated view checks (shortcut AUC needs 50+ cases)
- `medscope/data/loaders/slake.py` SLAKE → cases (lesion classes from mask.txt)
- `medscope/env/tools.py` zoom/window tools with budget
- `medscope/actions.py` output parser
- `medscope/rewards.py` cost-matrix reward
- `medscope/eval/metrics.py` benchmark metrics + grouped bootstrap
- `configs/reward.yaml` cost matrix; `configs/data.yaml` dataset registry
