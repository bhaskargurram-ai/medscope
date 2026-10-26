"""Generate the Colab notebooks from one place so their setup cells stay identical.

    python notebooks/build_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "Qwen/Qwen3.5-4B"
MEDGEMMA = "google/medgemma-1.5-4b-it"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}


def code(s: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": s.strip("\n").splitlines(keepends=True)}


SETUP = r"""
# --- setup: same in every notebook ---
from google.colab import drive, userdata
drive.mount('/content/drive')
import os, json
DRIVE = '/content/drive/MyDrive/medscope'
WORK = '/content/work'
RESULTS = f'{DRIVE}/results'
ADAPTERS = f'{DRIVE}/adapters'
VIEWS = f'{WORK}/views'
for d in (DRIVE, RESULTS, ADAPTERS, WORK):
    os.makedirs(d, exist_ok=True)

def secret(name):
    try:
        return userdata.get(name)
    except Exception:
        return None

gh = secret('GITHUB_TOKEN')
url = f'https://{gh}@github.com/bhaskargurram-ai/medscope' if gh else 'https://github.com/bhaskargurram-ai/medscope'
if os.path.exists('/content/medscope/.git'):
    !git -C /content/medscope pull -q
else:
    !git clone -q {url} /content/medscope
%cd /content/medscope
!git log --oneline -1
!pip install -q -e .
"""

GPU_STACK = r"""
# --- model libraries and Hugging Face login ---
!pip install -q -U transformers accelerate peft bitsandbytes
hf = secret('HF_TOKEN')
if hf:
    os.environ['HF_TOKEN'] = hf
    from huggingface_hub import login
    login(hf)
else:
    print('No HF_TOKEN secret: MedGemma (gated) will fail to download; Qwen works without it.')
import torch
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO GPU: Runtime > Change runtime type > L4 or A100')
"""

RESTORE_VIEWS = r"""
# --- restore the views built in notebook 01 (paths inside the manifests point to /content/work/views) ---
if not os.path.exists(f'{VIEWS}/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/slake/views.tar
!wc -l {VIEWS}/*/views_clean.jsonl
"""

SECRETS_NOTE = """
**Before you start:** in the Colab sidebar, open the key icon (Secrets) and add:
- `HF_TOKEN`: a Hugging Face read token. For MedGemma, first accept its terms at https://huggingface.co/google/medgemma-1.5-4b-it
- `GITHUB_TOKEN`: only needed if the repo is private.

Turn on notebook access for both secrets when Colab asks.
"""


def publish(title: str, sections: str) -> dict:
    return code(f"""
from medscope.colab import build_report, publish_doc, read_text, train_log_summary
from medscope.eval.runner import compare_runs
report = build_report({title!r}, [
{sections}
])
open(f'{{RESULTS}}/{title.split(' - ')[-1].replace(' ', '_').lower()}_report.md', 'w').write(report)
publish_doc({title!r}, report)
print(report[:3000])
""")


def nb01() -> list[dict]:
    return [
        md("""
# MedScope 01: build SLAKE counterfactual views

Downloads SLAKE, keeps English abnormality questions with lesion masks, builds four views per case
(original, lesion removed, matched random edit, degraded input) with LaMa inpainting, runs the
automated quality checks, saves everything to Drive and publishes a report as a Google Doc.

**Runtime:** T4 GPU is enough. About 30-60 minutes.
""" + SECRETS_NOTE),
        code(SETUP),
        code("!pip install -q simple-lama-inpainting huggingface_hub"),
        md("## Download SLAKE"),
        code(r"""
from huggingface_hub import hf_hub_download
import zipfile, shutil, pathlib
RAW = f'{WORK}/raw/slake'
os.makedirs(RAW, exist_ok=True)
for f in ['train.json', 'validation.json', 'test.json', 'mask.txt', 'imgs.zip']:
    shutil.copy(hf_hub_download('BoKelvin/SLAKE', f, repo_type='dataset'), f'{RAW}/{f}')
with zipfile.ZipFile(f'{RAW}/imgs.zip') as z:
    z.extractall(RAW)
raw = pathlib.Path(RAW)
if not (raw / 'imgs').exists():
    next(raw.rglob('xmlab*')).parent.rename(raw / 'imgs')
print(len(list((raw / 'imgs').glob('xmlab*'))), 'image folders')
"""),
        md("## Check the files match what the loader expects"),
        code(r"""
import numpy as np
from PIL import Image
q = json.load(open(f'{RAW}/train.json'))
fmt = [f'questions in train: {len(q)}', f'fields: {sorted(q[0].keys())}',
       f"content types: {sorted({str(x.get('content_type')) for x in q})}",
       'mask.txt (first lines):', open(f'{RAW}/mask.txt').read()[:600]]
m = np.asarray(Image.open(f'{RAW}/imgs/' + q[0]['img_name'].replace('source.jpg', 'mask.png')))
fmt.append(f'mask shape {m.shape}, ids {np.unique(m)[:20].tolist()}')
FORMAT_CHECK = '\n'.join(fmt)
print(FORMAT_CHECK)
"""),
        md("## Build case manifests, views and quality checks"),
        code(r"""
!python scripts/prepare_slake.py --root {RAW} --out {WORK}/cases
for split in ['train', 'validation', 'test']:
    !python scripts/build_views.py --manifest {WORK}/cases/cases_{split}.jsonl --out {VIEWS}/{split} --inpainter lama
!python scripts/check_views.py --views {VIEWS}/train/views.jsonl
for split in ['validation', 'test']:
    !python scripts/check_views.py --views {VIEWS}/{split}/views.jsonl --dedup-against {VIEWS}/train/views.jsonl
"""),
        md("## Look at a few examples"),
        code(r"""
import matplotlib.pyplot as plt
from collections import defaultdict
views = [json.loads(l) for l in open(f'{VIEWS}/test/views_clean.jsonl')]
by_case = defaultdict(dict)
for v in views:
    by_case[v['case_id']][v['kind']] = v
kinds = ['original', 'target_removal', 'random_removal', 'degraded']
cases = list(by_case)[:4]
fig, axes = plt.subplots(len(cases), 4, figsize=(12, 3 * len(cases)), squeeze=False)
for r, cid in enumerate(cases):
    for c, k in enumerate(kinds):
        axes[r, c].imshow(Image.open(by_case[cid][k]['image_path']))
        axes[r, c].set_title(k if r == 0 else '')
        axes[r, c].axis('off')
plt.tight_layout()
os.makedirs(RESULTS, exist_ok=True)
plt.savefig(f'{RESULTS}/01_examples.png', dpi=80)
"""),
        md("## Save to Drive and publish the report"),
        code(r"""
os.makedirs(f'{DRIVE}/slake', exist_ok=True)
!tar -C {WORK} -cf {DRIVE}/slake/views.tar views
!cp -r {WORK}/cases {DRIVE}/slake/
!du -sh {DRIVE}/slake/views.tar
def quality(split):
    r = json.load(open(f'{VIEWS}/{split}/quality_report.json'))
    r.pop('cases', None)
    return json.dumps(r, indent=2)
"""),
        publish("MedScope report - 01 data", """
    ('File format check', FORMAT_CHECK),
    ('SLAKE filtering', read_text(f'{WORK}/cases/prepare_report.txt')),
    ('Quality: train', quality('train')),
    ('Quality: validation', quality('validation')),
    ('Quality: test', quality('test')),
"""),
    ]


def nb02() -> list[dict]:
    return [
        md(f"""
# MedScope 02: baselines

Runs two open models zero-shot on the MedScope-Bench test views with the agent prompt:
`{BASE}` (our base model) and `{MEDGEMMA}` (Google's medical model).

**Runtime:** L4 GPU (A100 is faster). Roughly 1-2 hours per model. Results resume if Colab disconnects:
just run all cells again.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code("LIMIT = ''   # e.g. '--limit-cases 50' for a quick first look; '' runs every test case"),
        md("## Qwen3.5-4B, zero-shot"),
        code(f"!python scripts/evaluate.py --model {BASE} --views {{VIEWS}}/test/views_clean.jsonl "
             "--out {RESULTS}/base_qwen35_test --name base-qwen3.5-4b --split test {LIMIT}"),
        md("## MedGemma 1.5 4B, zero-shot"),
        code(f"!python scripts/evaluate.py --model {MEDGEMMA} --views {{VIEWS}}/test/views_clean.jsonl "
             "--out {RESULTS}/base_medgemma15_test --name base-medgemma-1.5-4b --split test {LIMIT}"),
        md("## Publish the report"),
        publish("MedScope report - 02 baselines", """
    ('Leaderboard', compare_runs(RESULTS)),
    ('Qwen3.5-4B details', read_text(f'{RESULTS}/base_qwen35_test/report.md')),
    ('MedGemma 1.5 4B details', read_text(f'{RESULTS}/base_medgemma15_test/report.md')),
"""),
    ]


def nb03() -> list[dict]:
    return [
        md(f"""
# MedScope 03: supervised fine-tuning

Trains two LoRA adapters on `{BASE}` from synthetic trajectories (no teacher model):
- **grounding**: answer + evidence box on answerable views, single turn
- **agentic**: all view kinds, multi-turn with zoom, refer and clarify

Then checks each on 40 validation cases. **Runtime:** L4 or A100, a few hours. Checkpoints go to Drive
every 50 steps; if Colab disconnects, run all cells again and training resumes.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        md("## Grounding adapter"),
        code(f"!python scripts/train_sft.py --model {BASE} --views {{VIEWS}}/train/views_clean.jsonl "
             "--mode grounding --out {ADAPTERS}/sft_grounding"),
        md("## Agentic adapter"),
        code(f"!python scripts/train_sft.py --model {BASE} --views {{VIEWS}}/train/views_clean.jsonl "
             "--mode agentic --out {ADAPTERS}/sft_agentic"),
        md("## Quick validation check"),
        code(f"""
for name in ['grounding', 'agentic']:
    !python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/sft_{{name}}/final --views {{VIEWS}}/validation/views_clean.jsonl --out {{RESULTS}}/sft_{{name}}_val --name sft-{{name}} --split validation --limit-cases 40
"""),
        publish("MedScope report - 03 SFT", """
    ('Grounding training loss', train_log_summary(f'{ADAPTERS}/sft_grounding/train_log.jsonl')),
    ('Agentic training loss', train_log_summary(f'{ADAPTERS}/sft_agentic/train_log.jsonl')),
    ('Leaderboard (all runs so far)', compare_runs(RESULTS)),
    ('Grounding adapter on validation', read_text(f'{RESULTS}/sft_grounding_val/report.md')),
    ('Agentic adapter on validation', read_text(f'{RESULTS}/sft_agentic_val/report.md')),
"""),
    ]


def nb04() -> list[dict]:
    return [
        md("""
# MedScope 04: merge the adapters

Combines the grounding and agentic adapters seven ways (each alone, SVD-weighted sums, concatenation,
TIES-SVD, DARE-TIES-SVD), scores each on 40 validation cases, and keeps the best as the starting point for RL.
These results are also the data for the "does merging damage abstention?" analysis.

**Runtime:** L4, about 2-3 hours. Finished candidates are skipped if you rerun.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code(f"!python scripts/merge_search.py --model {BASE} --grounding {{ADAPTERS}}/sft_grounding/final "
             "--agentic {ADAPTERS}/sft_agentic/final --views {VIEWS}/validation/views_clean.jsonl "
             "--out {ADAPTERS}/merged --results {RESULTS}"),
        publish("MedScope report - 04 merging", """
    ('Best candidate', read_text(f'{ADAPTERS}/merged/best.json')),
    ('Leaderboard (all runs so far)', compare_runs(RESULTS)),
"""),
    ]


def nb05() -> list[dict]:
    return [
        md("""
# MedScope 05: reinforcement learning (GRPO)

Starts from the best merged adapter and trains with the cost-matrix reward: the agent samples groups of
episodes per image (zooming as it likes), rewards are compared within each group, and the policy is
pushed toward the better episodes. A 15-case validation check runs every 50 steps.

**Runtime:** A100 recommended (L4 works, slower). 150 steps is several hours; checkpoints every 10 steps,
so rerunning resumes. Watch the printed reward: it should rise and "malformed" should fall.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code("STEPS = 150"),
        code(f"!python scripts/train_grpo.py --model {BASE} --init {{ADAPTERS}}/merged/best "
             "--views {VIEWS}/train/views_clean.jsonl --out {ADAPTERS}/grpo --steps {STEPS} "
             "--eval-views {VIEWS}/validation/views_clean.jsonl --eval-every 50 --results {RESULTS}"),
        publish("MedScope report - 05 RL", """
    ('Training curve (per 10 steps)', train_log_summary(f'{ADAPTERS}/grpo/train_log.jsonl')),
    ('Leaderboard (all runs so far)', compare_runs(RESULTS)),
"""),
    ]


def nb06() -> list[dict]:
    return [
        md(f"""
# MedScope 06: final test evaluation and export

Evaluates the RL model and its earlier stages on the full test split (the ablation table for the paper),
then merges the final adapter into `{BASE}` and saves the model to Drive. Pushing to Hugging Face is
optional and private by default.

**Runtime:** L4, about 3-4 hours. For the export step, a High-RAM runtime is safer.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code(f"""
runs = [('medscope_grpo_test', 'medscope-grpo', f'{{ADAPTERS}}/grpo/final'),
        ('medscope_merged_test', 'medscope-sft-merged', f'{{ADAPTERS}}/merged/best'),
        ('medscope_sft_agentic_test', 'medscope-sft-agentic', f'{{ADAPTERS}}/sft_agentic/final')]
for out, name, adapter in runs:
    !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{VIEWS}}/test/views_clean.jsonl --out {{RESULTS}}/{{out}} --name {{name}} --split test
"""),
        md("## Export the final model"),
        code("PUSH_TO = ''   # e.g. 'your-hf-username/MedScope-4B' to also upload (private)"),
        code(f"""
push = f'--push {{PUSH_TO}}' if PUSH_TO else ''
!python scripts/export_model.py --model {BASE} --adapter {{ADAPTERS}}/grpo/final --out {{DRIVE}}/export/MedScope-4B --summary {{RESULTS}}/medscope_grpo_test/summary.json {{push}}
"""),
        publish("MedScope report - 06 final", """
    ('Leaderboard (all runs)', compare_runs(RESULTS)),
    ('Final model on test', read_text(f'{RESULTS}/medscope_grpo_test/report.md')),
"""),
    ]


NOTEBOOKS = {
    "01_build_slake_views.ipynb": nb01,
    "02_baselines.ipynb": nb02,
    "03_sft.ipynb": nb03,
    "04_merge.ipynb": nb04,
    "05_rl_grpo.ipynb": nb05,
    "06_final_eval_export.ipynb": nb06,
}


def main() -> None:
    for name, fn in NOTEBOOKS.items():
        nb = {"cells": fn(), "nbformat": 4, "nbformat_minor": 0,
              "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                           "kernelspec": {"display_name": "Python 3", "name": "python3"},
                           "language_info": {"name": "python"}}}
        (HERE / name).write_text(json.dumps(nb, indent=1))
        print("wrote", name)


if __name__ == "__main__":
    main()
