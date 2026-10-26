# MedScope

A small open multimodal medical agent that answers only after it has checked the evidence — and zooms in, asks for missing information, or refers the case when the evidence isn't there.

> **Research use only.** MedScope is not a medical device and must not be used for diagnosis or treatment.

## What's in this repo

| Path | What it does |
| --- | --- |
| `medscope/data/` | Case schema and counterfactual view generation (target removal, random removal, degraded input) |
| `medscope/env/` | The agent's evidence tools (zoom, window/contrast) with a call budget |
| `medscope/actions.py` | Parses model output into tool calls and final actions |
| `medscope/rewards.py` | Cost-matrix reward with grounding and format terms, used for RL |
| `medscope/eval/` | MedScope-Bench metrics: coverage, CCR, AURC, abstention specificity gap, grounded accuracy, net utility, bootstrap CIs |
| `medscope/data/loaders/` | Dataset loaders (SLAKE so far) that produce case manifests |
| `medscope/data/quality.py` | Automated view checks: lesion removed, evidence intact, shortcut AUC, duplicates |
| `configs/` | Reward cost matrix and dataset registry |
| `scripts/` | `prepare_slake.py` → `build_views.py` → `check_views.py` |
| `notebooks/` | Colab notebooks that run each step on a GPU |
| `tests/` | Unit tests (run on CPU, no downloads needed) |

## The four views

Every image–question pair becomes four views, each with an expected action:

| View | How it's made | Expected action |
| --- | --- | --- |
| `original` | Unchanged | Answer + evidence box |
| `target_removal` | Lesion inpainted from surrounding tissue | Refer / abstain |
| `random_removal` | Same operator on a lesion-free region of the same size | Answer + evidence box |
| `degraded` | Blur, noise, low resolution or a mismatched image | Ask for clarification |

The random-removal view is the control: if a model abstains on both edited views equally, it is reacting to editing, not to missing evidence.

## Output protocol

The model reasons in free text, then emits exactly one tagged JSON object per turn:

```
<tool>{"name": "zoom", "box": [x1, y1, x2, y2]}</tool>
<tool>{"name": "window", "center": 40, "width": 400}</tool>
<final>{"action": "answer", "answer": "left lower lobe", "box": [x1, y1, x2, y2], "confidence": 0.82}</final>
<final>{"action": "clarify", "question": "Is there a lateral view?"}</final>
<final>{"action": "refer", "reason": "No visible evidence of the finding asked about."}</final>
```

Boxes use integer coordinates normalised to 0–1000 on the image the model was given.

## Quick start

```bash
pip install -e .            # core: numpy, pillow, opencv, pyyaml
python -m unittest -v       # all tests run on CPU

python scripts/prepare_slake.py --root data/raw/slake --out data/cases/slake
python scripts/build_views.py --manifest data/cases/slake/cases_test.jsonl --out data/views/slake_test --inpainter lama
python scripts/check_views.py --views data/views/slake_test/views.jsonl --dedup-against data/views/slake_train/views.jsonl
```

Or open `notebooks/01_build_slake_views.ipynb` in Colab and run all cells.

## Automated quality checks

No human annotation is used anywhere. `check_views.py` keeps a case only if:

- **the lesion is really gone** in the target-removal view: it no longer stands out from the surrounding tissue (a learned detector can be plugged in);
- **the evidence is intact** in the random-removal view: no lesion pixel changed;
- **it is not a duplicate** of a training image (perceptual hash, confirmed by pixel correlation).

Across the whole split it also reports a **shortcut AUC**: how well a classifier tells target-removal edits from random-removal edits by texture alone. It should be at or below 0.6; it needs at least 50 cases to be meaningful. OpenCV Telea inpainting scores about 0.6 on synthetic tests, which is why real builds use LaMa.

Training extras (`pip install -e ".[train]"`) are meant for Colab with a GPU.

## Roadmap

1. ✅ Core: schema, counterfactual views, tools, reward, metrics
2. ✅ SLAKE loader, LaMa inpainting, automated view quality checks, Colab notebook
2b. More loaders: ISIC 2018, IDRiD, VinDr-CXR, VinDr-Mammo; VQA-RAD and PathVQA for accuracy-only evaluation
3. Baseline evaluation harness (Qwen3.5-4B, MedGemma 1.5 4B, frontier APIs on open data)
4. Stage 1–2 SFT on Colab
5. Adapter merging + evolutionary per-layer search
6. GRPO/GSPO with the multi-turn tool loop
7. MedScope-Bench release, model release, papers

## Licence

Apache 2.0 (see `LICENSE`, to be added).
