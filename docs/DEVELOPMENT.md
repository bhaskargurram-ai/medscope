# MedScope — developer notes

## Goal
Train a 4B open medical VLM agent (base: Qwen3.5-4B) with RL so it answers only with visual evidence, and otherwise zooms, asks for clarification or refers. Plus MedScope-Bench, a counterfactual benchmark. Compute budget: Google Colab (L4/A100). Evaluation is fully automated — no human annotation, no clinician review.

## Conventions
- Python 3.10+, type hints, dataclasses. Core package depends only on numpy, pillow, opencv-python-headless, pyyaml.
- Heavy deps (torch, transformers, peft, bitsandbytes) are imported lazily inside `medscope/train/` and the scripts that need them.
- Images are `np.ndarray` uint8, HxWx3 RGB. Masks are bool HxW.
- Boxes everywhere are `[x1, y1, x2, y2]` ints normalised to 0–1000 on the ORIGINAL full image (also after zooming).
- View kinds: `original`, `target_removal`, `random_removal`, `degraded`.
- Final actions: `answer`, `clarify`, `refer` (`abstain` is accepted and treated as `refer`).
- Messages are model-agnostic dicts with content lists of `{"type": "image", "image": ndarray}` / `{"type": "text", "text": str}`; `HFPolicy.to_hf` converts them.
- Every long-running script resumes from what it already wrote to its `--out` folder.
- Credentialed PhysioNet data (VinDr, MIMIC) must never be sent to external APIs.
- Notebooks are generated: edit `notebooks/build_notebooks.py`, then run it.

## Commands
- Tests: `python -m unittest -v` (pytest also works if installed)
- SLAKE manifests: `python scripts/prepare_slake.py --root <slake dir> --out <dir>`
- Build views: `python scripts/build_views.py --manifest <cases.jsonl> --out <dir> [--inpainter lama]`
- Quality checks: `python scripts/check_views.py --views <views.jsonl> [--dedup-against <train views.jsonl>]`
- Evaluate: `python scripts/evaluate.py --model <hf id> [--adapter <dir>] --views <views_clean.jsonl> --out <dir> --name <run>`
- SFT: `python scripts/train_sft.py --model <hf id> --views <train views> --mode grounding|agentic --out <dir>`
- Merge search: `python scripts/merge_search.py --model ... --grounding <dir> --agentic <dir> --views <val views> --out <dir> --results <dir>`
- GRPO: `python scripts/train_grpo.py --model ... --init <adapter> --views <train views> --out <dir>`
- Export: `python scripts/export_model.py --model ... --adapter <dir> --out <dir> [--push <hf repo>]`
- Leaderboard: `python scripts/compare_runs.py --results <dir>`

## Layout
- `medscope/data/schema.py` case and view records
- `medscope/data/counterfactual.py` view generation
- `medscope/data/inpaint.py` Telea (CPU) or LaMa (GPU) inpainting
- `medscope/data/quality.py` automated view checks (shortcut AUC needs 50+ cases)
- `medscope/data/loaders/slake.py` SLAKE → cases (lesion classes from mask.txt)
- `medscope/env/tools.py` zoom/window tools with budget
- `medscope/actions.py` output parser
- `medscope/rewards.py` cost-matrix reward
- `medscope/agent/` prompt, episode loop (`run_episode`, batched `run_group`), synthetic trajectories
- `medscope/train/hf_policy.py` Hugging Face backend: generation, token log-probs, LoRA
- `medscope/train/sft.py`, `grpo.py`, `common.py` training loops
- `medscope/eval/metrics.py` benchmark metrics + grouped bootstrap; `runner.py` resumable evaluation, reports, leaderboard
- `medscope/colab.py` reports and Google Doc publishing (the Drive connector reads Docs, not .json/.md)
- `configs/reward.yaml` cost matrix; `configs/data.yaml` dataset registry
