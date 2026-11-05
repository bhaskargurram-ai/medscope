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


def _stop_on_failure(line: str) -> str:
    """`!python scripts/...` keeps going when the script fails, so later steps fail confusingly.
    Run project scripts through sh(), which streams output and stops the notebook on failure."""
    stripped = line.lstrip()
    if stripped.startswith("!python scripts/"):
        indent = line[:len(line) - len(stripped)]
        body = stripped[1:].rstrip("\n")
        assert '"' not in body, body
        return f'{indent}sh(f"{body}")' + ("\n" if line.endswith("\n") else "")
    return line


def code(s: str) -> dict:
    lines = [_stop_on_failure(l) for l in s.strip("\n").splitlines(keepends=True)]
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": lines}


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

import subprocess, urllib.request
REPO = 'bhaskargurram-ai/medscope'
gh = (secret('GITHUB_TOKEN') or '').strip()
url = f'https://git:{gh}@github.com/{REPO}' if gh else f'https://github.com/{REPO}'

def github_diagnosis():
    # explain why GitHub refused, without printing the token
    if not gh:
        return 'No GITHUB_TOKEN secret found (or notebook access is off for it). The repo is private, so one is needed.'
    def call(path):
        req = urllib.request.Request(f'https://api.github.com{path}', headers={'Authorization': f'Bearer {gh}'})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, {}, dict(e.headers or {})
    kind = 'classic' if gh.startswith('ghp_') else 'fine-grained' if gh.startswith('github_pat_') else 'unknown'
    if kind == 'unknown':
        return ('The secret does not look like a GitHub token (they start with github_pat_ or ghp_). '
                'Re-copy it into the GITHUB_TOKEN secret with no quotes or spaces.')
    status, user, headers = call('/user')
    if status == 401:
        return 'GitHub rejects the token itself: it is mistyped, expired or revoked. Make a new one.'
    who = user.get('login', '?')
    owner = REPO.split('/')[0]
    if who.lower() != owner:
        return f'The token belongs to GitHub account "{who}", not "{owner}". Sign in as {owner} and make the token there.'
    if kind == 'classic':
        scopes = headers.get('X-OAuth-Scopes', headers.get('x-oauth-scopes', '')) or 'none'
        if 'repo' not in [s.strip() for s in scopes.split(',')]:
            return (f'This is a classic token with scopes [{scopes}]; private repos need the "repo" box ticked. '
                    'Make a new classic token with "repo" checked, or a fine-grained one.')
    status, _, _ = call(f'/repos/{REPO}')
    if status == 200:
        return f'The token can see the repo but cannot read its code: set Contents to Read-only.'
    return ('This fine-grained token cannot see the private repo. Under "Repository access" it is probably on '
            'GitHub\'s default "Public repositories"; switch it to "Only select repositories", add medscope, '
            'and set Contents to Read-only. If you made a new token, also paste it into the GITHUB_TOKEN secret.')

def git(*args, cwd=None):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)

if os.path.exists('/content/medscope/.git'):
    # always land exactly on the latest code, whatever an earlier run left behind
    git('remote', 'set-url', 'origin', url, cwd='/content/medscope')
    r = git('fetch', '-q', 'origin', 'main', cwd='/content/medscope')
    if r.returncode == 0:
        r = git('reset', '-q', '--hard', 'origin/main', cwd='/content/medscope')
else:
    r = git('clone', '-q', url, '/content/medscope')
if r.returncode != 0:
    raise SystemExit('Could not download the code from GitHub.\n'
                     + (r.stderr.replace(gh, '***') if gh else r.stderr)
                     + '\nDiagnosis: ' + github_diagnosis())
def sh(cmd):
    # run a project script, show its output live, and stop the notebook if it fails
    # PYTHONUNBUFFERED: otherwise the script's progress lines arrive in big delayed chunks
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                         env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    for out_line in p.stdout:
        print(out_line, end='')
    if p.wait() != 0:
        raise SystemExit(f'This step failed (exit code {p.returncode}):\n  {cmd[:200]}\n'
                         'Nothing after it was run. Copy the error above into the chat.')

# forget any medscope modules an earlier run imported, so the fresh code is used
import sys
for name in [m for m in sys.modules if m == 'medscope' or m.startswith('medscope.')]:
    del sys.modules[name]
%cd /content/medscope
print('code version:', git('log', '--oneline', '-1', cwd='/content/medscope').stdout.strip())
# Colab already has numpy, pillow, opencv and pyyaml; --no-deps avoids a second, clashing OpenCV
!pip install -q -e . --no-deps
import cv2, yaml, numpy, PIL
print('medscope installed; opencv', cv2.__version__)
"""

GPU_STACK = r"""
# --- model libraries and Hugging Face login ---
!pip install -q -U transformers accelerate peft bitsandbytes
# Colab ships an old torchao that PEFT rejects with an error instead of ignoring; this project doesn't use it
!pip uninstall -q -y torchao
hf = secret('HF_TOKEN')
if hf:
    os.environ['HF_TOKEN'] = hf
    from huggingface_hub import login
    login(hf)
else:
    print('No HF_TOKEN secret: MedGemma (gated) will fail to download; Qwen works without it.')
import torch
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO GPU: Runtime > Change runtime type > L4 or A100')
# Fast kernels for Qwen3.5's linear-attention layers (Triton; needs an L4/A100-class GPU).
# If a later cell fails with an error mentioning 'fla' or 'triton', set FAST_KERNELS = False and rerun.
FAST_KERNELS = True
if FAST_KERNELS and torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8:
    !pip install -q flash-linear-attention
    try:
        import fla
        print('flash-linear-attention', fla.__version__)
    except Exception as e:
        print('flash-linear-attention unavailable, using the slower reference code:', e)
        !pip uninstall -q -y flash-linear-attention fla-core
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
from medscope.colab import build_report, by_dataset, negatives_by_domain, publish_doc, read_text, train_log_summary, vqa_table
from medscope.eval.runner import compare_runs
from medscope.eval.compare import significance_table
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
# MedScope 01: build the counterfactual benchmark data

Downloads SLAKE (CT/MRI/X-ray) and Kvasir-SEG (colonoscopy), turns every image with a lesion mask into
questions, splits by groups of near-identical images, builds four views per case (original, lesion
removed, matched random edit, degraded input) with LaMa inpainting, runs the automated quality checks,
saves everything to Drive and publishes a report as a Google Doc.

**Runtime:** T4 GPU is enough. About 30-60 minutes.
""" + SECRETS_NOTE),
        code(SETUP),
        code(r"""
!pip install -q huggingface_hub
# Big-LaMa inpainting model (about 200 MB), cached on Drive so it downloads only once
import torch, numpy as np
from medscope.data.inpaint import LAMA_URL, lama_inpaint
LAMA = f'{DRIVE}/models/big-lama.pt'
if not os.path.exists(LAMA):
    os.makedirs(os.path.dirname(LAMA), exist_ok=True)
    torch.hub.download_url_to_file(LAMA_URL, LAMA)
os.environ['MEDSCOPE_LAMA_PATH'] = LAMA
# smoke test: inpaint a square on a random image; pixels outside the square must not change
test = np.random.default_rng(0).integers(0, 256, (200, 300, 3), dtype=np.uint8)
hole = np.zeros((200, 300), bool); hole[50:90, 100:160] = True
out = lama_inpaint(test, hole)
assert out.shape == test.shape and (out[~hole] == test[~hole]).all()
print('LaMa works on', 'GPU' if torch.cuda.is_available() else 'CPU (slow: switch the runtime to T4)')
"""),
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
        md("""
## Download Kvasir-SEG
1,000 colonoscopy images with polyp masks (46 MB) from the official site. Its server leaves out an
intermediate certificate; the downloader fetches it the way browsers do and still verifies the full chain.
Terms: research and education only; cite Jha et al., *Kvasir-SEG: A Segmented Polyp Dataset*, MMM 2020.
"""),
        code(r"""
from medscope.download import download
from medscope.data.loaders.kvasir import find_roots
KV = f'{WORK}/raw/kvasir'
if not os.path.exists(f'{KV}/done'):
    download('https://datasets.simula.no/downloads/kvasir-seg.zip', f'{KV}/kvasir-seg.zip')
    with zipfile.ZipFile(f'{KV}/kvasir-seg.zip') as z:
        z.extractall(KV)
    open(f'{KV}/done', 'w').close()
roots = find_roots(KV)
n = sum(len(list((r / 'images').iterdir())) for r in roots)
print(f'Kvasir-SEG: {n} images in', [str(r.relative_to(KV)) for r in roots])
"""),
        md("## Build case manifests, views and quality checks"),
        code(r"""
# Questions from every image with a lesion mask; splits by groups of near-identical images.
# SLAKE masks are grey RGBA images whose grey level is the class id in mask.txt.
shutil.rmtree(f'{WORK}/cases', ignore_errors=True)
shutil.rmtree(VIEWS, ignore_errors=True)
r = subprocess.run(['python', 'scripts/prepare_data.py', '--slake', RAW, '--kvasir', KV, '--out', f'{WORK}/cases'],
                   capture_output=True, text=True)
print(r.stdout, r.stderr[-3000:])
if r.returncode != 0:
    raise SystemExit('Preparing the data failed (see the message above). Copy it into the chat so the loader can be fixed.')
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
cases = [c for c in by_case if c.startswith('slake')][:2] + [c for c in by_case if c.startswith('kvasir')][:2]
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
    r.pop('filtered', None)
    return json.dumps(r, indent=2)
"""),
        publish("MedScope report - 01 data", """
    ('File format check', FORMAT_CHECK),
    ('Data preparation (SLAKE + Kvasir-SEG)', read_text(f'{WORK}/cases/prepare_report.txt')),
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


SLAKE_DOWNLOAD = r"""
# --- SLAKE (about 200 MB) ---
from huggingface_hub import hf_hub_download
import zipfile, shutil, pathlib
RAW = f'{WORK}/raw/slake'
if not os.path.exists(f'{RAW}/imgs'):
    os.makedirs(RAW, exist_ok=True)
    for f in ['train.json', 'validation.json', 'test.json', 'mask.txt', 'imgs.zip']:
        shutil.copy(hf_hub_download('BoKelvin/SLAKE', f, repo_type='dataset'), f'{RAW}/{f}')
    with zipfile.ZipFile(f'{RAW}/imgs.zip') as z:
        z.extractall(RAW)
    raw = pathlib.Path(RAW)
    if not (raw / 'imgs').exists():
        next(raw.rglob('xmlab*')).parent.rename(raw / 'imgs')
print(len(list(pathlib.Path(RAW, 'imgs').glob('xmlab*'))), 'SLAKE image folders')
"""

NEGATIVES = "{DRIVE}/slake/negatives"

EVAL_NEGATIVES = r"""
# every model that exists so far, on unedited images without the lesion
NEG = f'{DRIVE}/slake/negatives/views_negatives.jsonl'
# most informative first: the base model and the agentic adapter answer the shortcut question
candidates = [('neg_base_qwen35', 'base-qwen3.5-4b', '%s', None),
              ('neg_sft_agentic', 'sft-agentic', '%s', f'{ADAPTERS}/sft_agentic/final'),
              ('neg_grpo_v2', 'medscope-grpo', '%s', f'{ADAPTERS}/grpo_v2/final'),
              ('neg_grpo', 'grpo-plain', '%s', f'{ADAPTERS}/grpo/final'),
              ('neg_merged', 'medscope-sft-merged', '%s', f'{ADAPTERS}/merged/best'),
              ('neg_sft_grounding', 'sft-grounding', '%s', f'{ADAPTERS}/sft_grounding/final'),
              ('neg_base_medgemma15', 'base-medgemma-1.5-4b', '%m', None)]
best_file = f'{ADAPTERS}/merged/best.json'
merged_is_copy = os.path.exists(best_file) and json.load(open(best_file))['best'] in ('agentic_only', 'grounding_only')
for out, name, model, adapter in candidates:
    if adapter and not os.path.exists(f'{adapter}/adapter_config.json'):
        print(f'skipping {name}: not trained yet')
        continue
    if out == 'neg_merged' and merged_is_copy:
        print('skipping medscope-sft-merged: no merge beat the unmerged adapter, so it is an identical copy')
        continue
    adapter_arg = f'--adapter {adapter}' if adapter else ''
    sh(f"python scripts/evaluate.py --model {model} {adapter_arg} --views {NEG} --out {RESULTS}/{out} --name {name} --split natural_negatives")
""".replace("%m", MEDGEMMA)


def nb02b() -> list[dict]:
    return [
        md(f"""
# MedScope 02b: natural negatives (is "refer" real, or an edit-detection shortcut?)

A model trained to refer when a lesion is digitally erased might only be spotting the *edit*.
This test uses **unedited** images that have no lesion:
- **SLAKE** CT/MRI images, with SLAKE's own questions whose answers say the finding isn't there
  ("Does the picture contain liver cancer?" -> "No"): a cross-domain test.
- **HyperKvasir** normal colonoscopy landmarks (cecum, rectum, ileum), asked "Is there a polyp?" -> "No":
  an in-domain test. Its train split is also what notebook 05 mixes into RL.

A model that learned a shortcut will claim the finding here, because there is no edit to detect.
Evaluates every model trained so far (skips the ones that don't exist yet), reusing finished
results. Rerun it after notebook 05 to add the RL model. **Runtime:** A100 or L4, about 1-2 hours
the first time (HyperKvasir download is about 4 GB), much less on reruns.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS), code(SLAKE_DOWNLOAD),
        md("## HyperKvasir normal landmarks (once; saved to Drive)"),
        code("""
from medscope.data.loaders.hyperkvasir import fetch_landmarks
HK = f'{DRIVE}/raw/hyperkvasir_landmarks'
fetch_landmarks(HK)   # incremental: only downloads classes that are still short (e.g. cecum)
for c in sorted(os.listdir(HK)):
    if os.path.isdir(f'{HK}/{c}'):
        print(c, len(os.listdir(f'{HK}/{c}')), 'images')
"""),
        md("## Build the natural negatives (once; saved to Drive)"),
        code(f"""
NEG_DIR = f'{NEGATIVES}'
NEG_VERSION = '2'   # 2 = SLAKE + HyperKvasir with cecum (version 1 had rectum and ileum only)
marker = f'{{NEG_DIR}}/NEG_VERSION'
if not os.path.exists(marker) or open(marker).read().strip() != NEG_VERSION:
    sh(f"python scripts/build_negatives.py --slake {{RAW}} --out {{NEG_DIR}} --dedup-against {{VIEWS}}/train/views.jsonl --hyperkvasir {{HK}}")
    open(marker, 'w').write(NEG_VERSION)
print(open(f'{{NEG_DIR}}/negatives_report.txt').read())
"""),
        md("## Evaluate"),
        code(EVAL_NEGATIVES.replace("%s", BASE)),
        publish("MedScope report - 02b natural negatives", """
    ('How the negatives were built', read_text(f'{DRIVE}/slake/negatives/negatives_report.txt')),
    ('Natural negatives by domain', negatives_by_domain(RESULTS, f'{DRIVE}/slake/negatives/views_negatives.jsonl')),
    ('Leaderboard (all runs so far)', compare_runs(RESULTS)),
    ('Base Qwen3.5-4B on natural negatives', read_text(f'{RESULTS}/neg_base_qwen35/report.md')),
    ('Base MedGemma 1.5 4B on natural negatives', read_text(f'{RESULTS}/neg_base_medgemma15/report.md')),
    ('SFT agentic on natural negatives', read_text(f'{RESULTS}/neg_sft_agentic/report.md')),
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
pushed toward the better episodes. A validation check (15 counterfactual cases + 30 natural negatives)
runs at the end.

**Dynamic sampling (run 2).** The first run (plain GRPO, 4 episodes per image, 2 images per step) barely
moved the model: the SFT agent makes the same choice in nearly every episode, so only about 1 in 5 groups
had any signal, and validation at steps 50 and 100 was identical. This run samples 8 episodes per image
and keeps drawing images (up to 6 per step) until 2 of them have signal, so every step trains on
disagreement. It saves to `adapters/grpo_v2`; the first run stays in `adapters/grpo` as the comparison.

20% of training images are **natural negatives** (unedited HyperKvasir colonoscopy with no polyp, built
by notebook 02b). Claiming the finding costs the same on them as on lesion-removed images, and refusing
pays the same, so the agent can't profit from detecting edits.

**Runtime:** A100 recommended. About 4-5 hours (50 steps of up to 6 groups); checkpoints every 5 steps,
so rerunning resumes. Each line reads `signal 2/5`: 2 of the 5 groups drawn that step had signal.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code("""
NEG_DIR = f'{DRIVE}/slake/negatives'
marker = f'{NEG_DIR}/NEG_VERSION'
if not os.path.exists(marker) or open(marker).read().strip() != '2':
    raise SystemExit('Natural-negative training images are missing or outdated (no cecum views): '
                     'run notebook 02b first, it builds them.')
print(open(f'{NEG_DIR}/negatives_report.txt').read())

# run 1 (plain GRPO) may have been stopped during its final validation, after its step-150 checkpoint
# was saved: that checkpoint is its final adapter
import shutil
v1 = f'{ADAPTERS}/grpo'
if not os.path.exists(f'{v1}/final/adapter_config.json') and os.path.exists(f'{v1}/checkpoint/adapter_config.json'):
    state = json.load(open(f'{v1}/state.json'))
    if state.get('step') == state.get('steps'):
        shutil.copytree(f'{v1}/checkpoint', f'{v1}/final')
        print(f"run 1 finished all {state['steps']} steps; its checkpoint is now {v1}/final")
STEPS = 50
"""),
        code(f"!python scripts/train_grpo.py --model {BASE} --init {{ADAPTERS}}/merged/best "
             "--views {VIEWS}/train/views_clean.jsonl --out {ADAPTERS}/grpo_v2 --steps {STEPS} "
             "--group-size 8 --views-per-step 2 --max-draws 6 --lr 2e-5 --save-every 5 "
             "--negatives {NEG_DIR}/views_negatives_train.jsonl --eval-negatives {NEG_DIR}/views_negatives_val.jsonl "
             "--eval-views {VIEWS}/validation/views_clean.jsonl --eval-every {STEPS} --results {RESULTS}/grpo_v2"),
        publish("MedScope report - 05 RL", """
    ('Run 2 (dynamic sampling): training curve (per 5 steps)', train_log_summary(f'{ADAPTERS}/grpo_v2/train_log.jsonl', window=5)),
    ('Run 2: validation at the end', read_text(f'{RESULTS}/grpo_v2/grpo_val_step{STEPS:04d}/report.md')),
    ('Run 1 (plain GRPO): training curve (per 10 steps)', train_log_summary(f'{ADAPTERS}/grpo/train_log.jsonl')),
    ('Leaderboard (all runs so far)', compare_runs(RESULTS)),
"""),
    ]


def nb06() -> list[dict]:
    return [
        md(f"""
# MedScope 06: final test evaluation and export

Evaluates the RL model, its earlier stages and both baselines on the full test split (the paper's main table),
then merges the final adapter into `{BASE}` and saves the model to Drive. Pushing to Hugging Face is
optional and private by default.

**Runtime:** A100, roughly 6-8 hours in total; every run resumes where it stopped, so rerun after a
disconnect. Models run in order of importance (final model, SFT agent, baselines, then plain GRPO), so
the main table fills first. For the export step, a High-RAM runtime is safer.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code(f"""
# every model on the FULL test split with the same scoring rules: the paper's main table.
# Runs that finished earlier on a subset (e.g. the 40-case baseline pilot) carry over.
runs = [('medscope_grpo_v2_test', 'medscope-grpo', {BASE!r}, f'{{ADAPTERS}}/grpo_v2/final'),
        ('medscope_sft_agentic_test', 'medscope-sft-agentic', {BASE!r}, f'{{ADAPTERS}}/sft_agentic/final'),
        ('base_qwen35_test', 'base-qwen3.5-4b', {BASE!r}, None),
        ('base_medgemma15_test', 'base-medgemma-1.5-4b', {MEDGEMMA!r}, None),
        ('grpo_plain_test', 'grpo-plain', {BASE!r}, f'{{ADAPTERS}}/grpo/final'),
        ('medscope_merged_test', 'medscope-sft-merged', {BASE!r}, f'{{ADAPTERS}}/merged/best')]
best_file = f'{{ADAPTERS}}/merged/best.json'
merged_is_copy = os.path.exists(best_file) and json.load(open(best_file))['best'] in ('agentic_only', 'grounding_only')
for out, name, model, adapter in runs:
    if out == 'medscope_merged_test' and merged_is_copy:
        print('skipping medscope-sft-merged: no merge beat the unmerged adapter, so it is an identical copy')
        continue
    adapter_arg = f'--adapter {{adapter}}' if adapter else ''
    !python scripts/evaluate.py --model {{model}} {{adapter_arg}} --views {{VIEWS}}/test/views_clean.jsonl --out {{RESULTS}}/{{out}} --name {{name}} --split test
"""),
        md("## Natural negatives (unedited images without the lesion)"),
        code("""
if os.path.exists(f'{DRIVE}/slake/negatives/views_negatives.jsonl'):
""" + "\n".join("    " + l for l in EVAL_NEGATIVES.replace("%s", BASE).strip("\n").splitlines()) + """
else:
    print('No natural negatives on Drive yet: run notebook 02b once, then rerun this cell.')
"""),
        md("## Export the final model"),
        code("PUSH_TO = ''   # e.g. 'your-hf-username/MedScope-4B' to also upload (private)"),
        code(f"""
push = f'--push {{PUSH_TO}}' if PUSH_TO else ''
!python scripts/export_model.py --model {BASE} --adapter {{ADAPTERS}}/grpo_v2/final --out {{DRIVE}}/export/MedScope-4B --summary {{RESULTS}}/medscope_grpo_v2_test/summary.json {{push}}
"""),
        publish("MedScope report - 06 final", """
    ('Leaderboard (all runs)', compare_runs(RESULTS)),
    ('Final model on test', read_text(f'{RESULTS}/medscope_grpo_v2_test/report.md')),
    ('Natural negatives by domain', negatives_by_domain(RESULTS, f'{DRIVE}/slake/negatives/views_negatives.jsonl')),
    ('Final model on natural negatives', read_text(f'{RESULTS}/neg_grpo_v2/report.md')),
"""),
    ]


# ---------------------------------------------------------------------------------------------
# Version 2 pipeline: more imaging types, "No" when the lesion is absent, rejection sampling
# ---------------------------------------------------------------------------------------------

RESTORE_ALL = r"""
# --- restore all benchmark data (SLAKE + Kvasir views from notebook 01, the rest from notebook 07) ---
if not os.path.exists(f'{VIEWS}/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/slake/views.tar
VX = f'{WORK}/views_extra'
if not os.path.exists(f'{VX}/test/views_clean.jsonl'):
    if not os.path.exists(f'{DRIVE}/extra/extra.tar'):
        raise SystemExit('The chest X-ray / ultrasound / brain MRI data is missing: run notebook 07 first.')
    !tar -C {WORK} -xf {DRIVE}/extra/extra.tar
NEG_HK, NEG_X = f'{DRIVE}/slake/negatives', f'{WORK}/extra/negatives'
TRAIN_VIEWS = f'{VIEWS}/train/views_clean.jsonl {VX}/train/views_clean.jsonl'
VAL_VIEWS = f'{VIEWS}/validation/views_clean.jsonl {VX}/validation/views_clean.jsonl'
TEST_VIEWS = f'{VIEWS}/test/views_clean.jsonl {VX}/test/views_clean.jsonl'
TRAIN_NEG = f'{NEG_HK}/views_negatives_train.jsonl {NEG_X}/views_negatives_train.jsonl'
VAL_NEG = f'{NEG_HK}/views_negatives_val.jsonl {NEG_X}/views_negatives_val.jsonl'
TEST_NEG = f'{NEG_HK}/views_negatives.jsonl {NEG_X}/views_negatives.jsonl'
for name in ('TRAIN_VIEWS', 'VAL_VIEWS', 'TEST_VIEWS', 'TRAIN_NEG', 'VAL_NEG', 'TEST_NEG'):
    files = globals()[name].split()
    n = sum(sum(1 for _ in open(f)) for f in files)
    print(f'{name}: {n} views in {len(files)} files')
"""

LAMA_CELL = r"""
# Big-LaMa inpainting model (about 200 MB), cached on Drive so it downloads only once
import torch, numpy as np
from medscope.data.inpaint import LAMA_URL, lama_inpaint
LAMA = f'{DRIVE}/models/big-lama.pt'
if not os.path.exists(LAMA):
    os.makedirs(os.path.dirname(LAMA), exist_ok=True)
    torch.hub.download_url_to_file(LAMA_URL, LAMA)
os.environ['MEDSCOPE_LAMA_PATH'] = LAMA
test = np.random.default_rng(0).integers(0, 256, (200, 300, 3), dtype=np.uint8)
hole = np.zeros((200, 300), bool); hole[50:90, 100:160] = True
assert (lama_inpaint(test, hole)[~hole] == test[~hole]).all()
print('LaMa works on', 'GPU' if torch.cuda.is_available() else 'CPU (slow: switch the runtime to a GPU)')
"""


def nb07() -> list[dict]:
    return [
        md("""
# MedScope 07: three more imaging types

Adds **chest X-ray** (ChestX-Det: NIH ChestX-ray14 images with 13 finding masks), **breast ultrasound**
(BUSI) and **brain MRI** (TCGA-LGG FLAIR slices). Each comes from a public, ungated Hugging Face mirror
with lesion masks and lesion-free images, so each gives counterfactual cases *and* natural negatives.
Patients (or groups of near-identical images) never cross splits. Same view builder, LaMa inpainting
and quality checks as notebook 01.

**Runtime:** any GPU (T4 is enough). About 1 hour; downloads about 2 GB.
""" + SECRETS_NOTE),
        code(SETUP),
        code("!pip install -q huggingface_hub pyarrow"),
        code(LAMA_CELL),
        md("## Download, select and split"),
        code(r"""
import shutil
EXTRA, VX = f'{WORK}/extra', f'{WORK}/views_extra'
shutil.rmtree(VX, ignore_errors=True)
!python scripts/prepare_extra.py --out {EXTRA} --cache {WORK}/raw/extra
!wc -l {EXTRA}/cases_*.jsonl {EXTRA}/negatives/*.jsonl
"""),
        md("## Build views and run the quality checks"),
        code(r"""
for split in ['train', 'validation', 'test']:
    !python scripts/build_views.py --manifest {EXTRA}/cases_{split}.jsonl --out {VX}/{split} --inpainter lama
!python scripts/check_views.py --views {VX}/train/views.jsonl
for split in ['validation', 'test']:
    !python scripts/check_views.py --views {VX}/{split}/views.jsonl --dedup-against {VX}/train/views.jsonl
"""),
        md("## Look at a few examples"),
        code(r"""
import matplotlib.pyplot as plt
from PIL import Image
from collections import defaultdict
views = [json.loads(l) for l in open(f'{VX}/test/views_clean.jsonl')]
by_case = defaultdict(dict)
for v in views:
    by_case[v['case_id']][v['kind']] = v
kinds = ['original', 'target_removal', 'random_removal', 'degraded']
cases = [next(c for c in by_case if c.startswith(p)) for p in ('chestxdet', 'busi', 'lgg') if any(c.startswith(p) for c in by_case)]
fig, axes = plt.subplots(len(cases), 4, figsize=(12, 3 * len(cases)), squeeze=False)
for r, cid in enumerate(cases):
    for c, k in enumerate(kinds):
        axes[r, c].imshow(Image.open(by_case[cid][k]['image_path']))
        axes[r, c].set_title(f"{k}\n{by_case[cid][k]['question'][:40]}" if c == 0 else k, fontsize=8)
        axes[r, c].axis('off')
plt.tight_layout()
plt.savefig(f'{RESULTS}/07_examples.png', dpi=80)
"""),
        md("## Save to Drive and publish the report"),
        code(r"""
os.makedirs(f'{DRIVE}/extra', exist_ok=True)
!tar -C {WORK} -cf {DRIVE}/extra/extra.tar extra/images extra/negatives extra/extra_report.txt views_extra
!du -sh {DRIVE}/extra/extra.tar
def quality(split):
    r = json.load(open(f'{VX}/{split}/quality_report.json'))
    r.pop('cases', None)
    r.pop('filtered', None)
    return json.dumps(r, indent=2)
"""),
        publish("MedScope report - 07 more data", """
    ('Datasets', read_text(f'{EXTRA}/extra_report.txt')),
    ('Quality: train', quality('train')),
    ('Quality: validation', quality('validation')),
    ('Quality: test', quality('test')),
"""),
    ]


def nb08() -> list[dict]:
    return [
        md(f"""
# MedScope 08: SFT v2 (every imaging type, says "No" when the lesion is absent)

Trains a fresh agentic LoRA adapter on `{BASE}` from synthetic trajectories over all five imaging types
(CT/MRI, colonoscopy, chest X-ray, breast ultrasound, brain MRI), plus natural negatives. New target
behaviour: when the finding is not in the image (lesion erased, or a healthy image) the agent **says so**
("No") instead of only referring. Both kinds get the same reply and the same reward, so spotting edits
earns nothing. Then checks it on the full validation set, next to the first agentic adapter.

**Runtime:** A100. Training about 3 hours, validation about 1 hour. Checkpoints every 50 steps;
rerun all cells to resume.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        md("## Train"),
        code(f"!python scripts/train_sft.py --model {BASE} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} "
             "--mode agentic --out {ADAPTERS}/sft_v2"),
        md("## Validation (new adapter, then the first agentic adapter for comparison)"),
        code(f"""
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/sft_v2/final --views {{VAL_VIEWS}} {{VAL_NEG}} --out {{RESULTS}}/v2_sft_v2_val --name medscope-sft-v2 --split validation
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/sft_agentic/final --views {{VAL_VIEWS}} {{VAL_NEG}} --out {{RESULTS}}/v2_sft_v1_val --name sft-v1-refer --split validation
"""),
        publish("MedScope report - 08 SFT v2", """
    ('Training loss', train_log_summary(f'{ADAPTERS}/sft_v2/train_log.jsonl', window=20)),
    ('Validation by imaging type', by_dataset(RESULTS, ['v2_sft_v2_val', 'v2_sft_v1_val'])),
    ('SFT v2 on validation', read_text(f'{RESULTS}/v2_sft_v2_val/report.md')),
    ('First agentic adapter on the same validation set', read_text(f'{RESULTS}/v2_sft_v1_val/report.md')),
"""),
    ]


def nb09() -> list[dict]:
    return [
        md(f"""
# MedScope 09: rejection-sampling fine-tuning

RL could not move the SFT agent (it makes the same choice in nearly every sample, so group-relative
advantages vanish). Rejection sampling still learns from those views: the SFT v2 model tries 150
training views of each kind 4 times; whenever any try succeeds, its best episode (in the model's own
words and tool use) is kept. The adapter is then fine-tuned on those episodes plus 3,000 synthetic ones
at a low learning rate, and checked on validation. The better of SFT v2 and this model on validation
becomes the final model for notebook 10.

**Runtime:** A100. Sampling about 2 hours, training about 1 hour, validation about 1 hour. Every step resumes.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        md("## Sample"),
        code(f"!python scripts/sample_rft.py --model {BASE} --adapter {{ADAPTERS}}/sft_v2/final --views {{TRAIN_VIEWS}} "
             "--negatives {TRAIN_NEG} --per-kind 150 --k 4 --out {ADAPTERS}/rft/samples.jsonl"),
        md("## Fine-tune on the kept episodes"),
        code(f"!python scripts/train_sft.py --model {BASE} --init {{ADAPTERS}}/sft_v2/final --views {{TRAIN_VIEWS}} "
             "--negatives {TRAIN_NEG} --subsample 3000 --replays {ADAPTERS}/rft/samples.jsonl --lr 5e-5 "
             "--mode agentic --out {ADAPTERS}/rft_train"),
        md("## Validation and choice of the final model"),
        code(f"""
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/rft_train/final --views {{VAL_VIEWS}} {{VAL_NEG}} --out {{RESULTS}}/v2_rft_val --name medscope-rft --split validation
scores = {{}}
for name, run in [('sft_v2', 'v2_sft_v2_val'), ('rft_train', 'v2_rft_val')]:
    p = f'{{RESULTS}}/{{run}}/summary.json'
    if os.path.exists(p):
        scores[name] = json.load(open(p))['metrics']['net_utility']['value']
best = max(scores, key=scores.get)
json.dump({{'adapter': f'{{ADAPTERS}}/{{best}}/final', 'chosen': best, 'validation_net_utility': scores}},
          open(f'{{ADAPTERS}}/final_choice.json', 'w'), indent=2)
print('validation net utility:', scores, '-> final model:', best)
"""),
        publish("MedScope report - 09 RFT", """
    ('Rejection sampling: success per view kind', read_text(f'{ADAPTERS}/rft/rft_summary.md')),
    ('Fine-tuning loss', train_log_summary(f'{ADAPTERS}/rft_train/train_log.jsonl', window=10)),
    ('Final model choice', read_text(f'{ADAPTERS}/final_choice.json')),
    ('Validation by imaging type', by_dataset(RESULTS, ['v2_rft_val', 'v2_sft_v2_val', 'v2_sft_v1_val'])),
    ('RFT model on validation', read_text(f'{RESULTS}/v2_rft_val/report.md')),
"""),
    ]


BASELINES = [
    ("v2_base_qwen35_test", "qwen3.5-4b", BASE),
    ("v2_base_medgemma15_test", "medgemma-1.5-4b", MEDGEMMA),
    ("v2_lingshu7b_test", "lingshu-7b", "lingshu-medical-mllm/Lingshu-7B"),
    ("v2_huatuo7b_test", "huatuogpt-vision-7b", "FreedomIntelligence/HuatuoGPT-Vision-7B-Qwen2.5VL"),
    ("v2_qwen25vl7b_test", "qwen2.5-vl-7b", "Qwen/Qwen2.5-VL-7B-Instruct"),
    ("v2_qwen3vl8b_test", "qwen3-vl-8b", "Qwen/Qwen3-VL-8B-Instruct"),
]


def nb10() -> list[dict]:
    runs = "\n".join(f"    ({out!r}, {name!r}, {model!r}, None)," for out, name, model in BASELINES)
    all_runs = ["v2_medscope_test"] + [b[0] for b in BASELINES] + ["v2_sft_v1_test"]
    return [
        md(f"""
# MedScope 10: final test evaluation and export

Every model on the full test set of all five imaging types plus the natural negatives, with the same
prompt and scoring: the final MedScope model, six open baselines (general and medical, 4-8B) and the
first refer-only adapter as an ablation. Then merges the final adapter into `{BASE}` and saves it.

**Runtime:** A100, about 8-12 hours in total (about 1 hour per model). Every run resumes where it
stopped; models run in order of importance, so the main table fills first. A High-RAM runtime is
safer for the export step.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        code(f"""
choice = json.load(open(f'{{ADAPTERS}}/final_choice.json')) if os.path.exists(f'{{ADAPTERS}}/final_choice.json') else {{'adapter': f'{{ADAPTERS}}/sft_v2/final'}}
FINAL = choice['adapter']
print('final model adapter:', FINAL)
runs = [('v2_medscope_test', 'medscope-4b', {BASE!r}, FINAL),
{runs}
        ('v2_sft_v1_test', 'ablation-refer-only-sft', {BASE!r}, f'{{ADAPTERS}}/sft_agentic/final')]
failed = []
for out, name, model, adapter in runs:
    adapter_arg = f'--adapter {{adapter}}' if adapter else ''
    try:
        !python scripts/evaluate.py --model {{model}} {{adapter_arg}} --views {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/{{out}} --name {{name}} --split test
    except SystemExit:
        failed.append(name)   # keep going: one model that fails to load must not cost the others
        import torch; torch.cuda.empty_cache()
print('failed:', failed or 'none')
if failed and 'medscope-4b' in failed:
    raise SystemExit('The MedScope run failed: copy the error above into the chat.')
"""),
        md("## Are the edits detectable? A learned detector (about 20 minutes)"),
        code(r"""
if os.path.exists(f'{RESULTS}/v2_edit_detector/edit_detector.md'):
    print('edit-trace test already done; delete results/v2_edit_detector to redo it')
else:
    !python scripts/edit_detector.py --train {TRAIN_VIEWS} --test {TEST_VIEWS} --out {RESULTS}/v2_edit_detector
"""),
        md("## Export the final model"),
        code("PUSH_TO = ''   # e.g. 'your-hf-username/MedScope-4B' to also upload (private)"),
        code(f"""
push = f'--push {{PUSH_TO}}' if PUSH_TO else ''
!python scripts/export_model.py --model {BASE} --adapter {{FINAL}} --out {{DRIVE}}/export/MedScope-4B --summary {{RESULTS}}/v2_medscope_test/summary.json {{push}}
"""),
        publish("MedScope report - 10 final", f"""
    ('Leaderboard (test)', compare_runs(RESULTS, 'v2_*_test')),
    ('MedScope vs each model (paired bootstrap over cases)', significance_table(RESULTS, 'v2_medscope_test', {all_runs[1:]!r})),
    ('By imaging type', by_dataset(RESULTS, {all_runs!r})),
    ('Learned edit detector', read_text(f'{{RESULTS}}/v2_edit_detector/edit_detector.md')),
    ('MedScope on test', read_text(f'{{RESULTS}}/v2_medscope_test/report.md')),
"""),
    ]


def nb00_sync() -> list[dict]:
    return [
        md("""
# MedScope: copy the Drive files to Hugging Face (to continue on RunPod or another GPU)

Uploads everything the remaining steps need from `My Drive/medscope` to a **private** Hugging Face
dataset repo: the benchmark views, natural negatives, the trained adapters (including the SFT v2
checkpoint, so training resumes where it stopped). About 5 GB.

**Runtime: CPU is fine** (Runtime > Change runtime type > CPU); no GPU credits needed.

**Before you start:** add a Colab secret `HF_WRITE_TOKEN`: a Hugging Face token with **write** access
(huggingface.co > Settings > Access Tokens > Create new token > Write).
"""),
        code(r"""
from google.colab import drive, userdata
drive.mount('/content/drive')
!pip install -q -U huggingface_hub
import os
from huggingface_hub import HfApi, login
token = userdata.get('HF_WRITE_TOKEN')
login(token)
api = HfApi()
user = api.whoami()['name']
REPO = f'{user}/medscope-work'
api.create_repo(REPO, repo_type='dataset', private=True, exist_ok=True)
DRIVE = '/content/drive/MyDrive/medscope'
for f in ['slake/views.tar', 'extra/extra.tar', 'slake/negatives/views_negatives.jsonl',
          'adapters/sft_agentic/final/adapter_config.json']:
    print(('ok      ' if os.path.exists(f'{DRIVE}/{f}') else 'MISSING ') + f)
print('sft_v2 so far:', open(f'{DRIVE}/adapters/sft_v2/state.json').read() if os.path.exists(f'{DRIVE}/adapters/sft_v2/state.json') else 'not started')
"""),
        code(r"""
# resumable: rerun this cell if it stops; files already uploaded are skipped
api.upload_large_folder(folder_path=DRIVE, repo_id=REPO, repo_type='dataset',
                        allow_patterns=['slake/views.tar', 'slake/negatives/**', 'extra/extra.tar',
                                        'adapters/sft_agentic/final/**', 'adapters/sft_v2/**',
                                        'adapters/merged/best.json', 'adapters/grpo/final/**',
                                        'adapters/grpo_v2/final/**', 'results/v2_*/**'])
print('done. On the GPU machine set:  HF_WORK_REPO=' + REPO)
"""),
    ]


# Frontier models behind an API: (run name, provider, model id). The first OpenAI and Gemini rows keep
# their earlier run names, so the 150 cases already done are reused.
FRONTIER = [
    ("v2_openai_test", "openai", "gpt-6-sol"),
    ("v2_gpt6astra_test", "openai", "gpt-6-astra"),
    ("v2_gpt61sol_test", "openai", "gpt-6.1-sol"),
    ("v2_claudefable_test", "anthropic", "claude-fable-5-1"),
    ("v2_claudeopus_test", "anthropic", "claude-opus-5-5"),
    ("v2_claudesonnet_test", "anthropic", "claude-sonnet-5-5"),
    ("v2_gemini_test", "gemini", "gemini-4-argon"),
    ("v2_gemini31pro_test", "gemini", "gemini-3.1-pro-preview"),
    ("v2_gemini38flash_test", "gemini", "gemini-3.8-flash"),
]
FRONTIER_RUNS = [r for r, _, _ in FRONTIER]


def nb12_frontier() -> list[dict]:
    return [
        md("""
# MedScope 12: frontier models (OpenAI, Anthropic, Google) on MedScope-Bench

Nine frontier models, three per provider, get the same agent prompt, images, tools and scoring as
every other model, on the **full test set**, so the comparison with MedScope is paired on every case.

**Runtime: CPU is fine** (no GPU credits): the models run on the providers' servers.

**Cost is measured, not guessed.** Step 1 runs a 20-case pilot per model and prints, from the
providers' own token counts and the official list prices, the exact cost per view and the projected
cost of the full run. Step 2 (set `RUN_FULL = True`) runs everything and prints what was spent.
Run before 1 December 2026: gemini-4-argon's price doubles then.

**Before you start:** add Colab secrets `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and `GEMINI_API_KEY`
(key icon). Only providers with a key are run. Images from the datasets are sent to the providers
for this research evaluation; the datasets' licences allow research use. Every step resumes.
"""),
        code(SETUP),
        code("!pip install -q -U openai anthropic google-genai"),
        code(RESTORE_ALL),
        code(r"""
from medscope.api_policy import available_models, cost_table, PRICES
KEYS = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY'}
for name in KEYS.values():
    if secret(name):
        os.environ[name] = secret(name)
PROVIDERS = [p for p, k in KEYS.items() if os.environ.get(k)]
print('providers with a key:', PROVIDERS)
for p in PROVIDERS:
    names = available_models(p) or []
    print(p, [n for n in names if any(t in n for t in ('gpt', 'claude', 'gemini')) and 'audio' not in n and 'tts' not in n][-25:])
"""),
        md("Model ids below were the newest models with image input in October 2026; if one is missing from the lists above, replace it with the closest id shown."),
        code(f"""
FRONTIER = {FRONTIER!r}
PILOT_CASES = 20
RUN_FULL = False       # set True to run all cases (the pilot in step 1 is optional: skip it if cost is not a concern)
from medscope.eval.runner import load_views, select_cases
ALL_VIEWS = select_cases([v for f in (TEST_VIEWS, TEST_NEG) for v in load_views(f)], None)
RUNS = [(r, p, m) for r, p, m in FRONTIER if p in PROVIDERS]
print(len(ALL_VIEWS), 'test views,', len({{v.case_id for v in ALL_VIEWS}}), 'cases;', len(RUNS), 'models to run')
"""),
        md("## Step 1: 20-case pilot per model and the exact cost of the full run"),
        code(r"""
for run, p, m in RUNS:
    try:
        !python scripts/evaluate.py --api {p} --model {m} --views {TEST_VIEWS} {TEST_NEG} --limit-cases {PILOT_CASES} --out {RESULTS}/pilot/{run} --name {p}-{m} --split test --batch-size 8
    except SystemExit:
        print(f'{m} failed: see the error above')
COSTS = cost_table(RUNS, f'{RESULTS}/pilot', RESULTS, ALL_VIEWS)
open(f'{RESULTS}/frontier_costs.md', 'w').write(COSTS)
from IPython.display import Markdown, display
display(Markdown(COSTS))
"""),
        md("## Step 2: full test set (only when `RUN_FULL = True`)"),
        code(r"""
from IPython.display import Markdown, display
if RUN_FULL:
    for run, p, m in RUNS:
        try:
            !python scripts/evaluate.py --api {p} --model {m} --views {TEST_VIEWS} {TEST_NEG} --out {RESULTS}/{run} --name {p}-{m} --split test --batch-size 8
        except SystemExit:
            print(f'{m} failed: see the error above')
    COSTS = cost_table(RUNS, f'{RESULTS}/pilot', RESULTS, ALL_VIEWS)
    open(f'{RESULTS}/frontier_costs.md', 'w').write(COSTS)
    display(Markdown(COSTS))
else:
    print('RUN_FULL is False: read the cost table above, then set RUN_FULL = True and rerun from the FRONTIER cell')
"""),
        publish("MedScope report - 12 frontier", """
    ('API cost (measured)', read_text(f'{RESULTS}/frontier_costs.md')),
    ('Leaderboard (test)', compare_runs(RESULTS, 'v2_*_test')),
    ('MedScope vs frontier models on the same cases (paired bootstrap)', significance_table(RESULTS, 'v2_medscope_test', [r for r, _, _ in RUNS])),
    ('By imaging type', by_dataset(RESULTS, ['v2_medscope_test'] + [r for r, _, _ in RUNS])),
"""),
    ]


def nb11_generalization() -> list[dict]:
    model_rows = "\n".join(f"    ({out.replace('_test', '')!r}, {name!r}, {model!r}, None)," for out, name, model in BASELINES)
    ext_runs = ["v2_medscope_ext"] + [b[0].replace("_test", "_ext") for b in BASELINES]
    vqa_runs = ["v2_medscope_vqa"] + [b[0].replace("_test", "_vqa") for b in BASELINES]
    return [
        md(f"""
# MedScope 11: generalisation (external centres, standard medical VQA)

1. **External validation:** the same test on data from other centres that no model was trained on:
   colonoscopy from Barcelona (CVC-ClinicDB), chest X-ray from Qatar (QaTa-COV19), breast ultrasound
   from Brazil (BUS-BRA) and brain MRI from Sub-Saharan Africa (BraTS-Africa 2023). Up to 50 lesion
   images and 50 lesion-free images per source; same view builder and checks.
2. **Standard medical VQA:** VQA-RAD (all 451 test questions), SLAKE official English test and
   PathVQA test (300 sampled each), to show the training did not cost general ability.

Every model: the final MedScope model and the six open baselines. Run notebook 09 first (it picks the
final model). **Runtime:** A100, about 8-10 hours; every step resumes.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code("!pip install -q nibabel datasets pyarrow huggingface_hub"),
        code(LAMA_CELL), code(RESTORE_ALL),
        md("## External data (built once, then restored from Drive)"),
        code(r"""
EXT, VEXT = f'{WORK}/external', f'{WORK}/views_external'
if not os.path.exists(f'{VEXT}/test/views_clean.jsonl') and os.path.exists(f'{DRIVE}/external/external.tar'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
if not os.path.exists(f'{VEXT}/test/views_clean.jsonl'):
    !python scripts/prepare_external.py --out {EXT} --cache {WORK}/raw/external --cap 50
    !python scripts/build_views.py --manifest {EXT}/cases_test.jsonl --out {VEXT}/test --inpainter lama
    !python scripts/check_views.py --views {VEXT}/test/views.jsonl
    os.makedirs(f'{DRIVE}/external', exist_ok=True)
    !tar -C {WORK} -cf {DRIVE}/external/external.tar external/images external/negatives external/external_report.txt views_external
print(open(f'{EXT}/external_report.txt').read())
EXT_VIEWS = f'{VEXT}/test/views_clean.jsonl {EXT}/negatives/views_negatives_external.jsonl'
"""),
        md("## Standard VQA sets (built once)"),
        code(r"""
VQA = f'{WORK}/vqa'
if not os.path.exists(f'{VQA}/views_vqa.jsonl') and os.path.exists(f'{DRIVE}/external/vqa.tar'):
    !tar -C {WORK} -xf {DRIVE}/external/vqa.tar
if not os.path.exists(f'{VQA}/views_vqa.jsonl'):
    from huggingface_hub import hf_hub_download
    import zipfile, shutil, pathlib
    RAW = f'{WORK}/raw/slake'
    if not os.path.exists(f'{RAW}/imgs'):
        os.makedirs(RAW, exist_ok=True)
        for f in ['test.json', 'imgs.zip']:
            shutil.copy(hf_hub_download('BoKelvin/SLAKE', f, repo_type='dataset'), f'{RAW}/{f}')
        with zipfile.ZipFile(f'{RAW}/imgs.zip') as z:
            z.extractall(RAW)
        raw = pathlib.Path(RAW)
        if not (raw / 'imgs').exists():
            next(raw.rglob('xmlab*')).parent.rename(raw / 'imgs')
    !python scripts/build_vqa.py --out {VQA} --slake {WORK}/raw/slake --per-set 300
    !tar -C {WORK} -cf {DRIVE}/external/vqa.tar vqa
!wc -l {VQA}/views_vqa.jsonl
"""),
        md("## Evaluate every model (external first, then VQA)"),
        code(f"""
choice = json.load(open(f'{{ADAPTERS}}/final_choice.json')) if os.path.exists(f'{{ADAPTERS}}/final_choice.json') else {{'adapter': f'{{ADAPTERS}}/sft_v2/final'}}
FINAL = choice['adapter']
models = [('v2_medscope', 'medscope-4b', {BASE!r}, FINAL),
{model_rows}
]
failed = []
for suffix, views in (('ext', EXT_VIEWS), ('vqa', f'{{VQA}}/views_vqa.jsonl')):
    for out, name, model, adapter in models:
        adapter_arg = f'--adapter {{adapter}}' if adapter else ''
        try:
            !python scripts/evaluate.py --model {{model}} {{adapter_arg}} --views {{views}} --out {{RESULTS}}/{{out}}_{{suffix}} --name {{name}} --split {{suffix}}
        except SystemExit:
            failed.append(f'{{name}} ({{suffix}})')
            import torch; torch.cuda.empty_cache()
print('failed:', failed or 'none')
"""),
        publish("MedScope report - 11 generalisation", f"""
    ('External data', read_text(f'{{EXT}}/external_report.txt')),
    ('External validation leaderboard', compare_runs(RESULTS, 'v2_*_ext')),
    ('MedScope vs each model on external data (paired bootstrap)', significance_table(RESULTS, 'v2_medscope_ext', {ext_runs[1:]!r})),
    ('External validation by source', by_dataset(RESULTS, {ext_runs!r})),
    ('Standard medical VQA', vqa_table(RESULTS, {vqa_runs!r})),
"""),
    ]


def nb13_paper_tables() -> list[dict]:
    baseline_test = [b[0] for b in BASELINES]
    return [
        md("""
# MedScope 13: paper tables

Recomputes every result from the stored decisions and transcripts under the final scoring rules
(no model is run): replies written in plain prose instead of the action format are read as the
model's decision, identically for every model. Reruns the learned edit-trace test, then publishes
all paper tables in one report: main test, significance, per imaging type, external centres,
standard VQA, frontier models, the ablation and the edit-trace test. The final MedScope model is the
one recorded in adapters/final_choice.json (SFT v3 if notebook 15 chose it).

**Runtime:** any GPU (T4 is enough; the edit-trace test trains a small CNN), about 30-40 minutes.
"""),
        code(SETUP), code(RESTORE_ALL),
        code(r"""
for tar, check in ((f'{DRIVE}/external/external.tar', f'{WORK}/views_external/test/views_clean.jsonl'),
                   (f'{DRIVE}/external/vqa.tar', f'{WORK}/vqa/views_vqa.jsonl')):
    if not os.path.exists(check) and os.path.exists(tar):
        !tar -C {WORK} -xf {tar}
!python scripts/rescore_all.py --results {RESULTS}
"""),
        code(f"""
choice = json.load(open(f'{{ADAPTERS}}/final_choice.json'))
M = choice.get('prefix', 'v2_medscope')
print('final MedScope model:', choice['adapter'], '->', M)
BASE_TEST = {baseline_test!r}
TEST_RUNS = [f'{{M}}_test'] + BASE_TEST + {FRONTIER_RUNS!r} + ['v2_sft_v1_test', 'v2_sft_v2_test', 'v2_nocf_test']
EXT_RUNS = [f'{{M}}_ext'] + [r.replace('_test', '_ext') for r in BASE_TEST] + ['v2_sft_v2_ext', 'v2_nocf_ext']
VQA_RUNS = [f'{{M}}_vqa'] + [r.replace('_test', '_vqa') for r in BASE_TEST]
if M != 'v2_medscope':
    TEST_RUNS.append('v2_medscope_test'); EXT_RUNS.append('v2_medscope_ext'); VQA_RUNS.append('v2_medscope_vqa')
"""),
        md("## Do the edits leave a visible trace? (learned classifier, about 20 minutes)"),
        code(r"""
if os.path.exists(f'{RESULTS}/v2_edit_detector/edit_detector.md'):
    print('edit-trace test already done; delete results/v2_edit_detector to redo it')
else:
    !python scripts/edit_detector.py --train {TRAIN_VIEWS} --test {TEST_VIEWS} --out {RESULTS}/v2_edit_detector
"""),
        publish("MedScope report - 13 paper tables", """
    ('Final model', read_text(f'{ADAPTERS}/final_choice.json')),
    ('Main test: leaderboard', compare_runs(RESULTS, 'v2_*_test')),
    ('Main test: MedScope vs each model (paired bootstrap over cases)', significance_table(RESULTS, f'{M}_test', TEST_RUNS[1:])),
    ('Main test: by imaging type', by_dataset(RESULTS, TEST_RUNS)),
    ('External centres: leaderboard', compare_runs(RESULTS, 'v2_*_ext')),
    ('External centres: MedScope vs each model', significance_table(RESULTS, f'{M}_ext', EXT_RUNS[1:])),
    ('External centres: by source', by_dataset(RESULTS, EXT_RUNS)),
    ('Ablation: counterfactual training vs the same fine-tuning without it (test)', significance_table(RESULTS, 'v2_sft_v2_test', ['v2_nocf_test'])),
    ('Ablation on external centres', significance_table(RESULTS, 'v2_sft_v2_ext', ['v2_nocf_ext'])),
    ('Standard medical VQA', vqa_table(RESULTS, VQA_RUNS)),
    ('Frontier models: measured API cost', read_text(f'{RESULTS}/frontier_costs.md')),
    ('Edit-trace test', read_text(f'{RESULTS}/v2_edit_detector/edit_detector.md')),
    ('MedScope on test (full report)', read_text(f'{RESULTS}/{M}_test/report.md')),
"""),
    ]


def nb14_ablation() -> list[dict]:
    return [
        md(f"""
# MedScope 14: ablation (is it the counterfactual training, or just fine-tuning?)

Trains the same model with the same recipe and the same number of optimizer steps as SFT v2, on the
same images, but **without the counterfactual views**: only original lesion images (answer + box),
real healthy images ("No") and degraded images (ask to clarify). No lesion-removed and no random-edit
views. Then tests it and SFT v2 side by side on the main test set and the external centres.

If the ablation still claims erased lesions (low evidence sensitivity gap) while SFT v2 does not,
the gain comes from the counterfactual training itself, not from in-domain fine-tuning.

**Runtime:** A100, about 5 hours (training about 2-3 hours, three evaluations). Everything resumes.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        code(r"""
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
if not os.path.exists(f'{WORK}/views_external/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
"""),
        md("## Train without counterfactual views (same steps as SFT v2)"),
        code(f"!python scripts/train_sft.py --model {BASE} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} "
             "--kinds original natural_negative degraded --epochs 3 --max-steps 1980 --mode agentic --out {ADAPTERS}/sft_nocf"),
        md("## Test: ablation and SFT v2, main test set and external centres"),
        code(f"""
for out, name, adapter in [('v2_nocf', 'ablation-no-counterfactual-sft', f'{{ADAPTERS}}/sft_nocf/final'),
                           ('v2_sft_v2', 'medscope-sft-v2', f'{{ADAPTERS}}/sft_v2/final')]:
    !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/{{out}}_test --name {{name}} --split test
    !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{EXT_VIEWS}} --out {{RESULTS}}/{{out}}_ext --name {{name}} --split ext
"""),
        publish("MedScope report - 14 ablation", """
    ('Training loss (ablation)', train_log_summary(f'{ADAPTERS}/sft_nocf/train_log.jsonl', window=20)),
    ('Main test: SFT v2 vs the ablation (paired bootstrap)', significance_table(RESULTS, 'v2_sft_v2_test', ['v2_nocf_test'])),
    ('External centres: SFT v2 vs the ablation', significance_table(RESULTS, 'v2_sft_v2_ext', ['v2_nocf_ext'])),
    ('Main test by imaging type', by_dataset(RESULTS, ['v2_sft_v2_test', 'v2_nocf_test', 'v2_medscope_test'])),
    ('Ablation on test (full report)', read_text(f'{RESULTS}/v2_nocf_test/report.md')),
"""),
    ]


def nb16_robustness() -> list[dict]:
    plain_rows = "\n".join(f"    ({out.replace('v2_', 'v2_plain_')!r}, {name!r}, {model!r}),"
                           for out, name, model in BASELINES)
    return [
        md(f"""
# MedScope 16: robustness checks reviewers ask for (GPU)

1. **Tools switched off at test time.** MedScope (RFT and v3) on the main test with every tool call
   refused, so the gain from zooming and windowing can be separated from the training itself.
2. **Open baselines with their own plain prompt.** Each open model gets a short native VQA prompt with no
   action format, one reply, read as plain prose, so no model is judged on following our format.
3. **Extra analyses from stored results** (no model run): decisions per view kind, strict ESG (only
   explicit "not there" answers count), always-yes / always-no / always-refer / always-clarify policies,
   net utility under other cost matrices, tool use, and results by lesion size.

Run notebook 13 first. **Runtime:** A100, about 4-6 hours; every step resumes.
Run notebook 17 (CPU, API models) at the same time if you like.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        md("## 1. Tools switched off (MedScope RFT and v3)"),
        code(f"""
choice = json.load(open(f'{{ADAPTERS}}/final_choice.json'))
RFT = choice.get('previous_adapter', f'{{ADAPTERS}}/rft_train/final')
V3 = choice['adapter']
for out, name, adapter in [('v2_medscope_notools_test', 'medscope-4b-rft-no-tools', RFT),
                           ('v2_medscope3_notools_test', 'medscope-4b-v3-no-tools', V3)]:
    !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{TEST_VIEWS}} {{TEST_NEG}} --tool-budget 0 --out {{RESULTS}}/{{out}} --name {{name}} --split test
"""),
        md("## 2. Open baselines with a plain native prompt (one reply, no action format)"),
        code(f"""
PLAIN = [
{plain_rows}
]
for out, name, model in PLAIN:
    try:
        !python scripts/evaluate.py --model {{model}} --views {{TEST_VIEWS}} {{TEST_NEG}} --prompt plain --out {{RESULTS}}/{{out}} --name {{name}}-plain --split test
    except SystemExit:
        print(f'{{name}} failed: see above')
"""),
        md("## 3. Extra analyses (CPU, from stored results)"),
        code(f"""
RUNS = ['v2_medscope3_test=MedScope-4B v3', 'v2_medscope_test=MedScope-4B RFT', 'v2_sft_v2_test=SFT (stage 1)',
        'v2_nocf_test=No counterfactual views', 'v2_medscope_notools_test=RFT, tools off', 'v2_medscope3_notools_test=v3, tools off',
        'v2_base_qwen35_test=Qwen3.5-4B', 'v2_gemini_test=gemini-4-argon', 'v2_gpt6astra_test=gpt-6-astra',
        'v2_claudeopus_test=claude-opus-5-5', 'v2_claudesonnet_test=claude-sonnet-5-5']
RUNS += [f"{{out}}={{name}} (plain prompt)" for out, name, _ in PLAIN]
TOOL_RUNS = ['v2_medscope3_test=MedScope-4B v3', 'v2_medscope_test=MedScope-4B RFT', 'v2_gemini_test=gemini-4-argon',
             'v2_claudeopus_test=claude-opus-5-5', 'v2_gpt6astra_test=gpt-6-astra', 'v2_claudesonnet_test=claude-sonnet-5-5']
!python scripts/rescore_all.py --results {{RESULTS}}
q = lambda xs: ' '.join(f'"{{x}}"' for x in xs)
!python scripts/extra_analysis.py --results {{RESULTS}} --views {{TEST_VIEWS}} {{TEST_NEG}} --runs {{q(RUNS)}} --tool-runs {{q(TOOL_RUNS)}} --out {{RESULTS}}/extra_analysis.md > /dev/null
"""),
        publish("MedScope report - 16 robustness", """
    ('Tools switched off vs on (paired)', significance_table(RESULTS, 'v2_medscope_test', ['v2_medscope_notools_test']) + '\\n\\n' + significance_table(RESULTS, 'v2_medscope3_test', ['v2_medscope3_notools_test'])),
    ('Open baselines: agent prompt vs their own plain prompt', compare_runs(RESULTS, 'v2_*_test')),
    ('MedScope vs open baselines under their plain prompt (paired)', significance_table(RESULTS, 'v2_medscope3_test', [r for r, _, _ in PLAIN])),
    ('Extra analyses', read_text(f'{RESULTS}/extra_analysis.md')),
"""),
    ]


def nb17_frontier_checks() -> list[dict]:
    return [
        md("""
# MedScope 17: frontier-model checks (CPU, API)

1. **External centres:** one flagship per provider (gpt-6-astra, claude-opus-5-5, gemini-4-argon) on the 169
   external cases, to show their erased-lesion claims hold outside the main test set.
2. **Cautious prompt:** the same three models on 150 test cases with an added warning that the question may
   name a finding that is not in the image. Does better prompting close the gap?
3. **Can a frontier model see the edits?** gemini-4-argon and gpt-6.1-sol rate how likely each image was
   edited (original, lesion erased, same-size edit elsewhere), as a second edit-trace test.
4. **Example figure** of real views per imaging type, saved to results/figures for the paper.

**Runtime: CPU.** About 1-2 hours. **Cost:** about $35-45 in total (measured costs are printed).
Colab secrets `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` as in notebook 12. Every step resumes.
"""),
        code(SETUP),
        code("!pip install -q -U openai anthropic google-genai"),
        code(RESTORE_ALL),
        code(r"""
for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY'):
    if secret(name):
        os.environ[name] = secret(name)
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
if not os.path.exists(f'{WORK}/views_external/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
FLAGSHIPS = [('gpt6astra', 'openai', 'gpt-6-astra'), ('claudeopus', 'anthropic', 'claude-opus-5-5'),
             ('gemini', 'gemini', 'gemini-4-argon')]
FLAGSHIPS = [f for f in FLAGSHIPS if os.environ.get({'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY'}[f[1]])]
print('models:', [m for _, _, m in FLAGSHIPS])
"""),
        md("## 1. External centres"),
        code(r"""
for tag, p, m in FLAGSHIPS:
    !python scripts/evaluate.py --api {p} --model {m} --views {EXT_VIEWS} --out {RESULTS}/v2_{tag}_ext --name {p}-{m} --split ext --batch-size 8 | tail -4
"""),
        md("## 2. Cautious prompt (150 test cases; compared with the same model's standard run on the same cases)"),
        code(r"""
for tag, p, m in FLAGSHIPS:
    !python scripts/evaluate.py --api {p} --model {m} --views {TEST_VIEWS} {TEST_NEG} --limit-cases 150 --prompt cautious --out {RESULTS}/v2_cautious_{tag}_test --name {p}-{m}-cautious --split test --batch-size 8 | tail -4
"""),
        md("## 3. Can a frontier model see the edits?"),
        code(r"""
for tag, p, m in [('gemini', 'gemini', 'gemini-4-argon'), ('gpt61sol', 'openai', 'gpt-6.1-sol')]:
    if [f for f in FLAGSHIPS if f[1] == p]:
        !python scripts/edit_guess.py --api {p} --model {m} --views {TEST_VIEWS} --out {RESULTS}/edit_guess_{tag} | tail -12
"""),
        md("## 4. Figure with real example views (for the paper)"),
        code(r"""
!python scripts/example_figure.py --views {TEST_VIEWS} --negatives {TEST_NEG} --out {RESULTS}/figures
from IPython.display import Image as _Img, display
display(_Img(f'{RESULTS}/figures/examples.png', width=900))
"""),
        publish("MedScope report - 17 frontier checks", """
    ('External centres: leaderboard', compare_runs(RESULTS, 'v2_*_ext')),
    ('External centres: MedScope v3 vs flagships (paired)', significance_table(RESULTS, 'v2_medscope3_ext', [f'v2_{t}_ext' for t, _, _ in FLAGSHIPS])),
    ('Cautious prompt vs standard prompt, same model, same 150 cases', '\\n\\n'.join(significance_table(RESULTS, f'v2_cautious_{t}_test', [{'gpt6astra': 'v2_gpt6astra_test', 'claudeopus': 'v2_claudeopus_test', 'gemini': 'v2_gemini_test'}[t]]) for t, _, _ in FLAGSHIPS)),
    ('MedScope v3 vs cautious-prompt flagships (paired, 150 cases)', significance_table(RESULTS, 'v2_medscope3_test', [f'v2_cautious_{t}_test' for t, _, _ in FLAGSHIPS])),
    ('Edit visibility: gemini-4-argon', read_text(f'{RESULTS}/edit_guess_gemini/edit_guess.md')),
    ('Edit visibility: gpt-6.1-sol', read_text(f'{RESULTS}/edit_guess_gpt61sol/edit_guess.md')),
"""),
    ]


def nb18_seeds() -> list[dict]:
    return [
        md("""
# MedScope 18: training-seed variability (ablation with three seeds)

The main ablation (counterfactual views vs none) used one training seed. This notebook trains the same two
stage-1 recipes with seeds 1 and 2 and tests each on the main test set and the external centres, so the paper can
report mean and standard deviation over three seeds (seed 0 is the existing pair from notebooks 08 and 14).

**Order:** seed 1 with CF, seed 1 without CF, seed 2 with CF, seed 2 without CF. Each pair alone already gives a
two-seed result. **Runtime:** A100, about 4-5 hours per model (training about 3.5 h, testing about 1.3 h), about
18-20 hours in total; every step resumes, so it can be split over several sessions.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        code(r"""
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
if not os.path.exists(f'{WORK}/views_external/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
"""),
        code(f"""
JOBS = [(1, 'cf'), (1, 'nocf'), (2, 'cf'), (2, 'nocf')]
for seed, arm in JOBS:
    name = f'sft_v2_s{{seed}}' if arm == 'cf' else f'nocf_s{{seed}}'
    out = f'{{ADAPTERS}}/{{name}}'
    if not os.path.exists(f'{{out}}/final/adapter_config.json'):
        if arm == 'cf':
            !python scripts/train_sft.py --model {BASE} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} --mode agentic --seed {{seed}} --out {{out}}
        else:
            !python scripts/train_sft.py --model {BASE} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} --kinds original natural_negative degraded --epochs 3 --max-steps 1980 --mode agentic --seed {{seed}} --out {{out}}
    !python scripts/evaluate.py --model {BASE} --adapter {{out}}/final --views {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/v2_{{name}}_test --name {{name}} --split test
    !python scripts/evaluate.py --model {BASE} --adapter {{out}}/final --views {{EXT_VIEWS}} --out {{RESULTS}}/v2_{{name}}_ext --name {{name}} --split ext
"""),
        code(r"""
for split in ('test', 'ext'):
    !python scripts/seed_summary.py --results {RESULTS} --arm 'With CF=v2_sft_v2_{split},v2_sft_v2_s1_{split},v2_sft_v2_s2_{split}' --arm 'Without CF=v2_nocf_{split},v2_nocf_s1_{split},v2_nocf_s2_{split}' --out {RESULTS}/seeds_{split}.md
"""),
        publish("MedScope report - 18 seeds", """
    ('Main test: three seeds per arm', read_text(f'{RESULTS}/seeds_test.md')),
    ('External centres: three seeds per arm', read_text(f'{RESULTS}/seeds_ext.md')),
"""),
    ]


def nb19_release() -> list[dict]:
    neg_runs = ["v2_medscope3_test", "v2_medscope_test"] + FRONTIER_RUNS + [b[0] for b in BASELINES]
    return [
        md("""
# MedScope 19: label spot-check and release (CPU)

1. **Label check (automatic, no human judgement).** The nine frontier models act as an independent panel: a
   "healthy" test image that at least 7 of them call abnormal is treated as a disputed label, and every result and
   paired test is recomputed without those images. MedScope does not vote.
2. **Release.** Prepares and uploads, as **private** Hugging Face repositories: the MedScope-4B and MedScope-4B-R
   adapters with model cards, and MedScope-Bench (view manifests without images, and every evaluation run). Make them
   public when the paper is submitted.

**Runtime: CPU**, 10-20 minutes, no input needed. Needs the Colab secret `HF_TOKEN` with **write** access (huggingface.co/settings/tokens).
"""),
        code(SETUP), code("!pip install -q -U huggingface_hub"), code(RESTORE_ALL),
        code(r"""
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
if not os.path.exists(f'{WORK}/views_external/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
if secret('HF_TOKEN'):
    os.environ['HF_TOKEN'] = secret('HF_TOKEN')
"""),
        md("## 1. Label check (automatic)"),
        code(f"""
NEG_RUNS = {neg_runs!r}
JUDGES = {FRONTIER_RUNS!r}
LC = f'{{RESULTS}}/label_check'
!python scripts/label_check.py consensus --views {{TEST_NEG}} --results {{RESULTS}} --judges {{' '.join(JUDGES)}} --min-votes 7 --runs {{' '.join(NEG_RUNS)}} --ref v2_medscope3_test --out {{LC}}
"""),
        md("## 2. Release (private repositories)"),
        code(r"""
choice = json.load(open(f'{ADAPTERS}/final_choice.json'))
FINAL = choice['adapter']
VERIFY = choice.get('previous_adapter', f'{ADAPTERS}/rft_train/final')
UPLOAD = True     # False: only prepare the folders in Drive
flag = '--upload' if UPLOAD and os.environ.get('HF_TOKEN') else ''
!python scripts/release_hf.py --final {FINAL} --verify {VERIFY} --results {RESULTS} --views {TEST_VIEWS} {TEST_NEG} --external {EXT_VIEWS} --out {DRIVE}/release {flag}
"""),
        publish("MedScope report - 19 release", """
    ('Label check: results without disputed labels (7 of 9 frontier models call the healthy image abnormal)', read_text(f'{RESULTS}/label_check/sensitivity_auto.md')),
    ('Model card (MedScope-4B)', read_text(f'{DRIVE}/release/MedScope-4B/README.md')),
"""),
    ]


def nb15_sft_v3() -> list[dict]:
    return [
        md(f"""
# MedScope 15: SFT v3 (keep general ability: replay of ordinary medical questions)

The final model lost some general medical VQA ability (open questions dropped, e.g. "Where are the
kidneys?" -> "No abnormality"): every training question was about a lesion. SFT v3 continues training
the current final model (low learning rate, about 800 steps) on a mix of its task views and ordinary
questions from the **training** splits of VQA-RAD, SLAKE and PathVQA (rehearsal), with no image
near-identical to any evaluation image and no SLAKE image used in our validation or test sets.

**Decision rule, fixed before testing:** SFT v3 becomes the final model if its validation net utility is
no more than 0.02 below the current final model's. If so it is tested on the main test set, the
external centres and standard VQA, and exported. Notebook 13 then uses it automatically.

**Runtime:** A100, about 4 hours (training about 1.2 h, validation 40 min, tests about 2 h). Resumes.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code("!pip install -q datasets pyarrow"), code(RESTORE_ALL),
        code(r"""
for tar, check in ((f'{DRIVE}/external/external.tar', f'{WORK}/views_external/test/views_clean.jsonl'),
                   (f'{DRIVE}/external/vqa.tar', f'{WORK}/vqa/views_vqa.jsonl')):
    if not os.path.exists(check):
        !tar -C {WORK} -xf {tar}
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
VQA_VIEWS = f'{WORK}/vqa/views_vqa.jsonl'
"""),
        md("## Replay set: ordinary questions from the training splits (built once)"),
        code(r"""
REPLAY = f'{DRIVE}/external/vqa_train/views_vqa_train.jsonl'
if not os.path.exists(REPLAY):
    from huggingface_hub import hf_hub_download
    import zipfile, shutil, pathlib
    RAW = f'{WORK}/raw/slake'
    os.makedirs(RAW, exist_ok=True)
    for f in ['train.json', 'test.json', 'imgs.zip']:
        if not os.path.exists(f'{RAW}/{f}'):
            shutil.copy(hf_hub_download('BoKelvin/SLAKE', f, repo_type='dataset'), f'{RAW}/{f}')
    if not os.path.exists(f'{RAW}/imgs'):
        with zipfile.ZipFile(f'{RAW}/imgs.zip') as z:
            z.extractall(RAW)
        raw = pathlib.Path(RAW)
        if not (raw / 'imgs').exists():
            next(raw.rglob('xmlab*')).parent.rename(raw / 'imgs')
    !python scripts/build_vqa.py --out {DRIVE}/external/vqa_train --split train --slake {RAW} --per-set 2000 --exclude-images {VAL_VIEWS} {TEST_VIEWS} {VAL_NEG} {TEST_NEG} {EXT_VIEWS} {VQA_VIEWS}
!wc -l {REPLAY}
"""),
        md("## Train SFT v3"),
        code(f"""
# continue from the current final model (keeps its gains) on a mix of task views and ordinary questions
INIT = json.load(open(f'{{ADAPTERS}}/final_choice.json'))
INIT = INIT.get('previous_adapter', INIT['adapter']) if INIT.get('chosen') == 'sft_v3' else INIT['adapter']
print('starting from', INIT)
!python scripts/train_sft.py --model {BASE} --init {{INIT}} --views {{TRAIN_VIEWS}} {{REPLAY}} --negatives {{TRAIN_NEG}} --subsample 5000 --lr 5e-5 --mode agentic --out {{ADAPTERS}}/sft_v3
"""),
        md("## Validation and decision"),
        code(f"""
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/sft_v3/final --views {{VAL_VIEWS}} {{VAL_NEG}} --out {{RESULTS}}/v2_sft_v3_val --name medscope-sft-v3 --split validation
choice = json.load(open(f'{{ADAPTERS}}/final_choice.json'))
current = max(choice['validation_net_utility'].values())
v3 = json.load(open(f'{{RESULTS}}/v2_sft_v3_val/summary.json'))['metrics']['net_utility']['value']
USE_V3 = v3 >= current - 0.02
print(f'validation net utility: current final {{current:.3f}}, SFT v3 {{v3:.3f}} ->', 'SFT v3 becomes the final model' if USE_V3 else 'keep the current final model')
if USE_V3:
    choice.update({{'adapter': f'{{ADAPTERS}}/sft_v3/final', 'chosen': 'sft_v3', 'prefix': 'v2_medscope3',
                   'previous': choice.get('chosen'), 'previous_adapter': choice['adapter']}})
    choice['validation_net_utility']['sft_v3'] = v3
    json.dump(choice, open(f'{{ADAPTERS}}/final_choice.json', 'w'), indent=2)
"""),
        md("## Test the new final model (only if chosen) and export it"),
        code(f"""
if USE_V3:
    A = f'{{ADAPTERS}}/sft_v3/final'
    for split, views in (('test', f'{{TEST_VIEWS}} {{TEST_NEG}}'), ('ext', EXT_VIEWS), ('vqa', VQA_VIEWS)):
        !python scripts/evaluate.py --model {BASE} --adapter {{A}} --views {{views}} --out {{RESULTS}}/v2_medscope3_{{split}} --name medscope-4b-v3 --split {{split}}
    !python scripts/export_model.py --model {BASE} --adapter {{A}} --out {{DRIVE}}/export/MedScope-4B --summary {{RESULTS}}/v2_medscope3_test/summary.json
"""),
        publish("MedScope report - 15 SFT v3", """
    ('Decision', read_text(f'{ADAPTERS}/final_choice.json')),
    ('Validation by imaging type', by_dataset(RESULTS, ['v2_sft_v3_val', 'v2_rft_val'])),
    ('Main test: v3 vs the previous final model', significance_table(RESULTS, 'v2_medscope3_test', ['v2_medscope_test'])),
    ('External centres: v3 vs the previous final model', significance_table(RESULTS, 'v2_medscope3_ext', ['v2_medscope_ext'])),
    ('Standard medical VQA', vqa_table(RESULTS, ['v2_medscope3_vqa', 'v2_medscope_vqa', 'v2_base_qwen35_vqa'])),
"""),
    ]


FLAGSHIP_TAGS = [("gpt6astra", "openai", "gpt-6-astra"), ("claudeopus", "anthropic", "claude-opus-5-5"),
                 ("gemini", "gemini", "gemini-4-argon")]


def nb20_fairness() -> list[dict]:
    return [
        md("""
# MedScope 20: fairness checks (held-out inpainters, few-shot frontier models)

Two questions a reviewer will ask:

1. **Did MedScope learn the inpainting tool instead of the lesion?** Every training and test view was made with
   LaMa. Here the two edited views of every main-test case (lesion erased, same edit elsewhere) are remade on
   exactly the same edit masks with three tools MedScope never saw: **Telea** (classical OpenCV), **transplant**
   (tissue copied from elsewhere in the same image, Poisson-blended; no generator) and **diffusion** (Stable
   Diffusion inpainting). MedScope (both versions) and three frontier flagships are tested on them.
2. **Were the frontier models only disadvantaged by seeing no examples?** The same flagships get the cautious prompt
   plus four solved examples from the *training* split (a lesion, the same image with it erased, an edit elsewhere
   with the lesion intact, a healthy image) before every case, on the same 150 test cases as the cautious-prompt run.

**Runs on any runtime and resumes.** On a CPU runtime (e.g. while notebook 18 holds the A100) it does everything
except the diffusion views and the MedScope runs; run it again on a GPU afterwards to finish those. **Cost:** about
$40 for the few-shot runs and about $16 per held-out tool for the frontier runs (about $90 in total; the estimate is
printed before spending). gemini-4-argon's price doubles on 1 December, so run the API parts before then.
Colab secrets: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (and `HF_TOKEN` on the GPU run).
"""),
        code(SETUP), code(GPU_STACK), code("!pip install -q -U openai anthropic google-genai diffusers"),
        code(RESTORE_ALL),
        code(f"""
for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY'):
    if secret(name):
        os.environ[name] = secret(name)
FLAGSHIPS = {FLAGSHIP_TAGS!r}
FLAGSHIPS = [f for f in FLAGSHIPS if os.environ.get({{'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY'}}[f[1]])]
HAVE_GPU = torch.cuda.is_available()
INP = f'{{DRIVE}}/inpaint_test'
print('frontier models:', [m for _, _, m in FLAGSHIPS], '| GPU:', HAVE_GPU)
"""),
        md("## 1. Remake the edited test views with three held-out inpainting tools (same masks)"),
        code(r"""
READY = []
for t in ['telea', 'transplant', 'diffusion']:
    if t == 'diffusion' and not HAVE_GPU:
        print('diffusion: needs a GPU, skipped in this session (rerun this notebook on a GPU)')
        continue
    try:
        !python scripts/reinpaint_views.py --views {TEST_VIEWS} --inpainter {t} --out {INP}/{t}
        READY.append(t)
    except SystemExit:
        print(f'{t} failed: see above')
VARIANTS = ' '.join(f'--variant {t}={INP}/{t}/views.jsonl' for t in READY)
!python scripts/inpainter_figure.py --views {TEST_VIEWS} {VARIANTS} --out {RESULTS}/figures
from IPython.display import Image as _Img, display
display(_Img(f'{RESULTS}/figures/inpainters.png', width=900))
"""),
        md("## 2. Few-shot frontier models (cautious prompt + four solved training examples; same 150 cases)"),
        code(r"""
for tag, p, m in FLAGSHIPS:
    !python scripts/evaluate.py --api {p} --model {m} --views {TEST_VIEWS} {TEST_NEG} --limit-cases 150 --prompt fewshot --fewshot {TRAIN_VIEWS} {TRAIN_NEG} --out {RESULTS}/v2_fewshot_{tag}_test --name {p}-{m}-fewshot --split test --batch-size 8
"""),
        md("## 3. MedScope on the held-out tools (GPU)"),
        code(f"""
if HAVE_GPU:
    choice = json.load(open(f'{{ADAPTERS}}/final_choice.json'))
    MODELS = [('medscope3', choice['adapter']), ('medscope', choice.get('previous_adapter', f'{{ADAPTERS}}/rft_train/final')),
              ('sft_v2', f'{{ADAPTERS}}/sft_v2/final'), ('nocf', f'{{ADAPTERS}}/sft_nocf/final')]   # stage 1 with and without CF
    for t in READY:
        for tag, adapter in MODELS:
            !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{INP}}/{{t}}/views.jsonl --vocab-from {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/v2_inp_{{t}}_{{tag}}_test --name {{tag}}-{{t}} --split test
else:
    print('No GPU in this session: MedScope runs skipped. Rerun this notebook on an A100 after notebook 18.')
"""),
        md("## 4. Frontier flagships on the held-out tools"),
        code(r"""
PER_VIEW = {'gpt-6-astra': 0.0145, 'claude-opus-5-5': 0.0139, 'gemini-4-argon': 0.0079}   # measured in notebook 12
from medscope.eval.runner import load_views, remaining
est = 0.0
for t in READY:
    vs = load_views(f'{INP}/{t}/views.jsonl')
    for tag, p, m in FLAGSHIPS:
        est += len(remaining(vs, f'{RESULTS}/v2_inp_{t}_{tag}_test', 'api')) * PER_VIEW[m]
print(f'estimated cost of the frontier runs still to do: ${est:.0f}')
for t in READY:
    for tag, p, m in FLAGSHIPS:
        !python scripts/evaluate.py --api {p} --model {m} --views {INP}/{t}/views.jsonl --vocab-from {TEST_VIEWS} {TEST_NEG} --out {RESULTS}/v2_inp_{t}_{tag}_test --name {p}-{m}-{t} --split test --batch-size 8
"""),
        md("## 5. Summary"),
        code(r"""
INP_LIST = ' '.join(READY)
!python scripts/inpainter_summary.py --results {RESULTS} --inpainters {INP_LIST} --model 'MedScope-4B=v2_medscope3_test' --model 'MedScope-4B-R=v2_medscope_test' --model 'Stage 1 with CF=v2_sft_v2_test' --model 'Stage 1 without CF=v2_nocf_test' --model 'gpt-6-astra=v2_gpt6astra_test' --model 'claude-opus-5-5=v2_claudeopus_test' --model 'gemini-4-argon=v2_gemini_test' --ref MedScope-4B --out {RESULTS}/inpainters.md
"""),
        publish("MedScope report - 20 fairness", """
    ('Held-out inpainting tools (edited views only)', read_text(f'{RESULTS}/inpainters.md')),
    ('Few-shot vs standard prompt, same model, same 150 cases', '\\n\\n'.join(significance_table(RESULTS, f'v2_fewshot_{t}_test', [f'v2_{t}_test']) for t, _, _ in FLAGSHIPS)),
    ('Few-shot vs cautious prompt, same model, same 150 cases', '\\n\\n'.join(significance_table(RESULTS, f'v2_fewshot_{t}_test', [f'v2_cautious_{t}_test']) for t, _, _ in FLAGSHIPS)),
    ('MedScope-4B vs few-shot flagships (paired, 150 cases)', significance_table(RESULTS, 'v2_medscope3_test', [f'v2_fewshot_{t}_test' for t, _, _ in FLAGSHIPS])),
    ('MedScope-4B-R vs few-shot flagships (paired, 150 cases)', significance_table(RESULTS, 'v2_medscope_test', [f'v2_fewshot_{t}_test' for t, _, _ in FLAGSHIPS])),
"""),
    ]


def nb21_medgemma() -> list[dict]:
    return [
        md(f"""
# MedScope 21: the same recipe on a second base model (MedGemma 1.5 4B)

All MedScope results use one base model (Qwen3.5-4B). This notebook trains **MedGemma 1.5 4B** with exactly the
stage-1 recipe, with and without the counterfactual views (same data, same steps, same LoRA settings), and tests
both on the main test set and the external centres. If counterfactual training lifts MedGemma the way it lifted
Qwen, the method is not specific to one model. Untrained MedGemma (notebook 10/11) is the zero-shot reference.

Run after notebook 18 (both need the A100). **Runtime:** A100, about 9-10 hours (two trainings of about 3.5 h,
four test runs); every step resumes, so it can be split over sessions. Needs `HF_TOKEN` with the MedGemma terms
accepted (https://huggingface.co/{MEDGEMMA}).
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL),
        code(r"""
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
if not os.path.exists(f'{WORK}/views_external/test/views_clean.jsonl'):
    !tar -C {WORK} -xf {DRIVE}/external/external.tar
"""),
        md("## Quick check that MedGemma trains (3 steps on 50 views, about 2 minutes; skipped once training has started)"),
        code(f"""
if not os.path.exists(f'{{ADAPTERS}}/mg_cf/state.json'):
    !python scripts/train_sft.py --model {MEDGEMMA} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} --subsample 50 --max-steps 3 --grad-accum 2 --mode agentic --out {{WORK}}/mg_smoke
    print('MedGemma training works')
"""),
        md("## Train with and without counterfactual views, then test both"),
        code(f"""
for arm in ('cf', 'nocf'):
    out = f'{{ADAPTERS}}/mg_{{arm}}'
    if not os.path.exists(f'{{out}}/final/adapter_config.json'):
        if arm == 'cf':
            !python scripts/train_sft.py --model {MEDGEMMA} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} --mode agentic --out {{out}}
        else:
            !python scripts/train_sft.py --model {MEDGEMMA} --views {{TRAIN_VIEWS}} --negatives {{TRAIN_NEG}} --kinds original natural_negative degraded --epochs 3 --max-steps 1980 --mode agentic --out {{out}}
    !python scripts/evaluate.py --model {MEDGEMMA} --adapter {{out}}/final --views {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/v2_mg_{{arm}}_test --name medgemma-{{arm}} --split test
    !python scripts/evaluate.py --model {MEDGEMMA} --adapter {{out}}/final --views {{EXT_VIEWS}} --out {{RESULTS}}/v2_mg_{{arm}}_ext --name medgemma-{{arm}} --split ext
"""),
        publish("MedScope report - 21 medgemma", f"""
    ('Training loss (MedGemma, counterfactual views)', train_log_summary(f'{{ADAPTERS}}/mg_cf/train_log.jsonl', window=20)),
    ('Main test: MedGemma with vs without counterfactual views (paired)', significance_table(RESULTS, 'v2_mg_cf_test', ['v2_mg_nocf_test', 'v2_base_medgemma15_test'])),
    ('External centres: MedGemma with vs without counterfactual views (paired)', significance_table(RESULTS, 'v2_mg_cf_ext', ['v2_mg_nocf_ext', 'v2_base_medgemma15_ext'])),
    ('Main test: Qwen recipe vs MedGemma recipe (stage 1, both with CF)', significance_table(RESULTS, 'v2_sft_v2_test', ['v2_mg_cf_test'])),
    ('Main test: MedGemma with CF vs frontier flagships (paired)', significance_table(RESULTS, 'v2_mg_cf_test', {[f"v2_{t}_test" for t, _, _ in FLAGSHIP_TAGS]!r})),
    ('Main test by imaging type', by_dataset(RESULTS, ['v2_mg_cf_test', 'v2_mg_nocf_test', 'v2_base_medgemma15_test', 'v2_sft_v2_test'])),
"""),
    ]


# ---------------------------------------------------------------------------------------------
# v4: one model, trained to remove the audited weaknesses, selected on validation, tested on everything
# ---------------------------------------------------------------------------------------------

RESTORE_V4 = r"""
# --- restore the v4 data built in notebook 22 ---
V4 = f'{WORK}/v4'
if not os.path.exists(f'{V4}/views/train/views_clean.jsonl'):
    if not os.path.exists(f'{DRIVE}/v4/v4.tar'):
        raise SystemExit('The v4 data is missing: run notebook 22 first.')
    !tar -C {WORK} -xf {DRIVE}/v4/v4.tar
TRAIN_V4_BASE = f'{VIEWS}/train/views_clean.jsonl {V4}/views/train/views_clean.jsonl'
TRAIN_V4 = f'{TRAIN_V4_BASE} {V4}/train_tp/views.jsonl {V4}/inserted/views.jsonl'
TRAIN_NEG_V4 = f'{NEG_HK}/views_negatives_train.jsonl {V4}/extra/negatives/views_negatives_train.jsonl'
VAL_V4 = f'{VIEWS}/validation/views_clean.jsonl {V4}/views/validation/views_clean.jsonl'
VAL_NEG_V4 = f'{NEG_HK}/views_negatives_val.jsonl {V4}/extra/negatives/views_negatives_val.jsonl'
FRESH = f'{V4}/views/fresh/views_clean.jsonl {V4}/extra/negatives/views_negatives_fresh.jsonl'
EXT2 = f'{V4}/views_external2/test/views_clean.jsonl {V4}/external2/negatives/views_negatives_external.jsonl'
for name in ('TRAIN_V4', 'TRAIN_NEG_V4', 'VAL_V4', 'VAL_NEG_V4', 'FRESH', 'EXT2'):
    files = globals()[name].split()
    print(f'{name}: ' + ', '.join(f'{sum(1 for _ in open(f)) if os.path.exists(f) else "missing"}' for f in files))
"""

RESTORE_EVAL = r"""
for tar, check in ((f'{DRIVE}/external/external.tar', f'{WORK}/views_external/test/views_clean.jsonl'),
                   (f'{DRIVE}/external/vqa.tar', f'{WORK}/vqa/views_vqa.jsonl')):
    if not os.path.exists(check):
        !tar -C {WORK} -xf {tar}
EXT_VIEWS = f'{WORK}/views_external/test/views_clean.jsonl {WORK}/external/negatives/views_negatives_external.jsonl'
VQA_VIEWS = f'{WORK}/vqa/views_vqa.jsonl'
"""

# the pre-registered v4 stage-1 recipe (docs/PREREGISTRATION_v4.md); notebooks 23 and 25 use exactly this
S1_ARGS = ("--views {TRAIN_V4} --negatives {TRAIN_NEG_V4} --mode agentic --subsample 16000 --window-prob 0.3 "
           "--small-zoom --oversample-small 2 --paraphrase-prob 0.5")
S1_NOCF_ARGS = ("--views {TRAIN_V4_BASE} --negatives {TRAIN_NEG_V4} --kinds original natural_negative degraded "
                "--epochs 3 --max-steps {S1_STEPS} --schedule-steps {S1_TOTAL} --mode agentic --window-prob 0.3 --small-zoom --oversample-small 2 "
                "--paraphrase-prob 0.5")


def nb22_v4_data() -> list[dict]:
    return [
        md("""
# MedScope 22: v4 data

Builds everything the v4 model is trained, selected and confirmed on (docs/PREREGISTRATION_v4.md):

1. **More images** from the existing training splits of ChestX-Det, BUSI and TCGA-LGG (every training image instead
   of the first 500), a **larger validation set** (100 + 100 per source) and a **fresh internal test set** from
   test-split patients the existing test set does not use. The existing test images do not change.
2. **A second inpainting tool in training**: tissue transplant for half of the training cases (LaMa for all).
   Telea and Stable Diffusion stay unseen: they are test-only.
3. **Lesion-insertion views** (training only): a real lesion moved into a healthy training image, answer "present".
4. **A fresh external test set** from public sources never used before (see the report for which).

New training views use the extended set of degradations; validation and test views use the original protocol.

**Runtime:** A100 or L4 (LaMa), about 3-4 hours; downloads a few GB. Every step can be rerun.
""" + SECRETS_NOTE),
        code(SETUP),
        code("!pip install -q huggingface_hub pyarrow nibabel"),
        code(LAMA_CELL),
        code(RESTORE_ALL),
        code(r"""
V4 = f'{WORK}/v4'
os.makedirs(V4, exist_ok=True)
"""),
        md("## 1. More training and validation images, and a fresh internal test set"),
        code(r"""
# the existing test set stays exactly as it is: its patients are removed from every v4 split (and every earlier
# image's patient from the fresh set); the script stops if any existing test image is missing or different
vx = lambda split: f'{VX}/{split}/views.jsonl' if os.path.exists(f'{VX}/{split}/views.jsonl') else f'{VX}/{split}/views_clean.jsonl'
PROTECT_TEST = f"{vx('test')} {NEG_X}/views_negatives.jsonl"
PROTECT_SEEN = f"{vx('train')} {vx('validation')} {NEG_X}/views_negatives_train.jsonl {NEG_X}/views_negatives_val.jsonl"
!python scripts/prepare_extra.py --out {V4}/extra --cache {WORK}/raw/extra --v4 --protect-test {PROTECT_TEST} --protect-seen {PROTECT_SEEN}
!wc -l {V4}/extra/cases_*.jsonl {V4}/extra/negatives/*.jsonl
key = lambda c: c.split('neg_')[0] if 'neg_' in c else c.rsplit('_', 1)[0]
keys = lambda files: {key(json.loads(l)['case_id']) for f in files.split() for l in open(f) if l.strip()}
old_test = keys(PROTECT_TEST)
for split, f in (('train', 'cases_train.jsonl'), ('validation', 'cases_validation.jsonl'), ('fresh', 'cases_fresh.jsonl'),
                 ('train negatives', 'negatives/views_negatives_train.jsonl'), ('validation negatives', 'negatives/views_negatives_val.jsonl'),
                 ('fresh negatives', 'negatives/views_negatives_fresh.jsonl')):
    clash = keys(f'{V4}/extra/{f}') & old_test
    if clash:
        raise SystemExit(f'{len(clash)} existing test images ended up in the v4 {split}; stop and report this.')
print('split check passed: no existing test image (or its patient) is in v4 train, validation or fresh')
!python scripts/build_views.py --manifest {V4}/extra/cases_train.jsonl --out {V4}/views/train --inpainter lama --v4-degradations
for split in ['validation', 'fresh']:
    !python scripts/build_views.py --manifest {V4}/extra/cases_{split}.jsonl --out {V4}/views/{split} --inpainter lama
!python scripts/check_views.py --views {V4}/views/train/views.jsonl --dedup-against {TEST_VIEWS} {TEST_NEG}
!python scripts/check_views.py --views {V4}/views/validation/views.jsonl --dedup-against {V4}/views/train/views_clean.jsonl {VIEWS}/train/views_clean.jsonl
!python scripts/check_views.py --views {V4}/views/fresh/views.jsonl --dedup-against {V4}/views/train/views_clean.jsonl {VIEWS}/train/views_clean.jsonl
"""),
        md("## 2. Second inpainting tool for training (tissue transplant, half of the cases)"),
        code(r"""
!python scripts/reinpaint_views.py --views {VIEWS}/train/views_clean.jsonl {V4}/views/train/views_clean.jsonl --inpainter transplant --fraction 0.5 --id-suffix '#tp' --out {V4}/train_tp
"""),
        md("## 3. Lesion-insertion views (training only)"),
        code(r"""
TRAIN_NEG_V4 = f'{NEG_HK}/views_negatives_train.jsonl {V4}/extra/negatives/views_negatives_train.jsonl'
!python scripts/insert_lesions.py --views {VIEWS}/train/views_clean.jsonl {V4}/views/train/views_clean.jsonl --negatives {TRAIN_NEG_V4} --out {V4}/inserted --max-per-dataset 300
"""),
        md("## 4. Fresh external test set (sources never used before)"),
        code(r"""
!python scripts/prepare_external2.py --out {V4}/external2 --cache {WORK}/raw/external2 --cap 50
!python scripts/build_views.py --manifest {V4}/external2/cases_test.jsonl --out {V4}/views_external2/test --inpainter lama
REF = f'{V4}/views/train/views_clean.jsonl {VIEWS}/train/views_clean.jsonl {TEST_VIEWS} {TEST_NEG} {TRAIN_NEG_V4}'
!python scripts/check_views.py --views {V4}/views_external2/test/views.jsonl --dedup-against {REF}
# lesion-free images of the fresh external set: drop near-copies of any training or test image (SIIM and ChestX-Det share NIH sources)
!python scripts/dedup_negatives.py --negatives {V4}/external2/negatives/views_negatives_external.jsonl --against {REF}
"""),
        md("## 5. Examples, save to Drive and report"),
        code(r"""
import matplotlib.pyplot as plt
from PIL import Image
from medscope.eval.runner import load_views
ins = load_views(f'{V4}/inserted/views.jsonl')[:4]
tp = [v for v in load_views(f'{V4}/train_tp/views.jsonl') if v.kind.value == 'target_removal'][:4]
fig, axes = plt.subplots(2, 4, figsize=(12, 6), squeeze=False)
for c, v in enumerate(ins):
    axes[0, c].imshow(Image.open(v.image_path)); axes[0, c].set_title('inserted: ' + v.question[:30], fontsize=7)
for c, v in enumerate(tp):
    axes[1, c].imshow(Image.open(v.image_path)); axes[1, c].set_title('transplant erasure', fontsize=7)
for ax in axes.flat:
    ax.axis('off')
plt.tight_layout(); plt.savefig(f'{RESULTS}/22_examples.png', dpi=80)
os.makedirs(f'{DRIVE}/v4', exist_ok=True)
!tar -C {WORK} -cf {DRIVE}/v4/v4.tar v4
!du -sh {DRIVE}/v4/v4.tar
def quality(path):
    r = json.load(open(path))
    r.pop('cases', None); r.pop('filtered', None)
    return json.dumps(r, indent=2)
"""),
        publish("MedScope report - 22 v4 data", """
    ('Datasets (more training images, larger validation, fresh internal test)', read_text(f'{V4}/extra/extra_report.txt')),
    ('Quality: v4 training views', quality(f'{V4}/views/train/quality_report.json')),
    ('Quality: v4 validation views', quality(f'{V4}/views/validation/quality_report.json')),
    ('Quality: fresh internal test', quality(f'{V4}/views/fresh/quality_report.json')),
    ('Fresh external sources', read_text(f'{V4}/external2/external_report.txt')),
    ('Quality: fresh external test', quality(f'{V4}/views_external2/test/quality_report.json')),
"""),
    ]


def nb23_v4_train() -> list[dict]:
    s1 = S1_ARGS
    return [
        md(f"""
# MedScope 23: train MedScope v4 and select it on validation

The recipe and the selection rule were fixed before training (docs/PREREGISTRATION_v4.md):

1. **Stage 1** (SFT from `{BASE}`): v4 data, windowing trajectories, always zoom on small lesions (and repeat them),
   paraphrased questions.
2. **Stage 2** (rejection sampling): more tries on healthy and lesion-erased images, higher temperature, episodes
   from views the model mostly failed repeated.
3. **Stage 3** (general-VQA replay): at least 35% "absent" targets, health questions balanced Yes/No.

Each stage is checked on the v4 validation set; `scripts/select_v4.py` applies the pre-registered rule. **No test
set is touched here.**

**Runtime:** A100, about 12-14 hours in total; every step resumes, so it can be split over sessions.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL), code(RESTORE_V4),
        md("## Stage 1"),
        code(f"""
!python scripts/train_sft.py --model {BASE} {s1} --out {{ADAPTERS}}/v4_s1
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/v4_s1/final --views {{VAL_V4}} {{VAL_NEG_V4}} --out {{RESULTS}}/v4_s1_val --name v4-stage1 --split validation
"""),
        md("## Stage 2: rejection sampling"),
        code(f"""
!python scripts/sample_rft.py --model {BASE} --adapter {{ADAPTERS}}/v4_s1/final --views {{TRAIN_V4}} --negatives {{TRAIN_NEG_V4}} --per-kind 200 --per-kind-override natural_negative=500 target_removal=300 --k 4 --temperature 1.2 --out {{ADAPTERS}}/v4_rft/samples.jsonl
!python scripts/train_sft.py --model {BASE} --init {{ADAPTERS}}/v4_s1/final --views {{TRAIN_V4}} --negatives {{TRAIN_NEG_V4}} --subsample 3000 --replays {{ADAPTERS}}/v4_rft/samples.jsonl --hard-repeat 3 --lr 5e-5 --mode agentic --window-prob 0.3 --small-zoom --paraphrase-prob 0.5 --out {{ADAPTERS}}/v4_s2
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/v4_s2/final --views {{VAL_V4}} {{VAL_NEG_V4}} --out {{RESULTS}}/v4_s2_val --name v4-stage2 --split validation
"""),
        md("## Stage 3: general-VQA replay, negatives-aware"),
        code(f"""
REPLAY = f'{{DRIVE}}/external/vqa_train/views_vqa_train.jsonl'
if not os.path.exists(REPLAY):
    raise SystemExit('The replay set is missing: it was built in notebook 15.')
!python scripts/train_sft.py --model {BASE} --init {{ADAPTERS}}/v4_s2/final --views {{TRAIN_V4}} {{REPLAY}} --negatives {{TRAIN_NEG_V4}} --subsample 5000 --lr 5e-5 --mode agentic --min-absent-share 0.35 --balance-health --window-prob 0.3 --small-zoom --paraphrase-prob 0.5 --out {{ADAPTERS}}/v4_s3
!python scripts/evaluate.py --model {BASE} --adapter {{ADAPTERS}}/v4_s3/final --views {{VAL_V4}} {{VAL_NEG_V4}} --out {{RESULTS}}/v4_s3_val --name v4-stage3 --split validation
"""),
        md("## Pre-registered selection"),
        code(r"""
# amendment 1 (docs/PREREGISTRATION_v4.md): the earlier final model on the same v4 validation set
V3 = json.load(open(f'{ADAPTERS}/final_choice.json'))['adapter']
!python scripts/evaluate.py --model Qwen/Qwen3.5-4B --adapter {V3} --views {VAL_V4} {VAL_NEG_V4} --out {RESULTS}/v3_on_v4_val --name medscope-4b-v3 --split validation
!python scripts/select_v4.py --results {RESULTS} --adapters {ADAPTERS} --incumbent v3_on_v4_val --incumbent-adapter {V3} --out {ADAPTERS}/final_choice_v4.json
"""),
        publish("MedScope report - 23 v4 training", """
    ('Selection (pre-registered rule)', read_text(f'{ADAPTERS}/final_choice_v4.json')),
    ('Stage 1 training loss', train_log_summary(f'{ADAPTERS}/v4_s1/train_log.jsonl', window=20)),
    ('Rejection sampling', read_text(f'{ADAPTERS}/v4_rft/rft_summary.md')),
    ('Validation by imaging type', by_dataset(RESULTS, ['v4_s1_val', 'v4_s2_val', 'v4_s3_val'])),
    ('Validation: stage 3 vs stage 2 (paired)', significance_table(RESULTS, 'v4_s3_val', ['v4_s2_val', 'v4_s1_val'])),
    ('Validation: v4 stages vs v3 on the same set (paired)', significance_table(RESULTS, 'v3_on_v4_val', ['v4_s1_val', 'v4_s2_val', 'v4_s3_val'])),
    ('Validation by imaging type, v3 and v4 stages', by_dataset(RESULTS, ['v3_on_v4_val', 'v4_s1_val', 'v4_s2_val', 'v4_s3_val'])),
"""),
    ]


def gated(parts: tuple[str, ...], src: str) -> dict:
    """A code cell that runs only in the listed parts (or when PART is 'all'): one notebook, opened in several
    Colab sessions with a different PART each, splits its work over several GPUs."""
    body = "".join("    " + l if l.strip() else l for l in src.strip("\n").splitlines(keepends=True))
    return code(f"if PART in {('all',) + parts!r}:\n" + body)


def nb24_v4_eval() -> list[dict]:
    flag_runs = [f"v2_{t}_test" for t, _, _ in FLAGSHIP_TAGS]
    base_runs = [b[0] for b in BASELINES]
    open_tags = [b[0].replace("v2_", "").replace("_test", "") for b in BASELINES]
    open_rows = "\n".join(f"    ({tag!r}, {name!r}, {model!r})," for tag, (_, name, model) in zip(open_tags, BASELINES))
    sig = lambda ref, runs: f"significance_table(RESULTS, {ref!r}, {runs!r})"
    return [
        md("""
# MedScope 24: the selected v4 model on every test (final evaluation)

One model, one adapter (`final_choice_v4.json`, chosen on validation by the pre-registered rule), tested once on
everything. Every MedScope number in the paper comes from this notebook.

| Section | Test | What it answers |
| --- | --- | --- |
| 1 | Main test (507 cases), external centres (169), **fresh internal**, **fresh external**, standard VQA, tools off | one model everywhere |
| 2 | Erasures remade by Telea, transplant and Stable Diffusion; question wordings never used in training | inpainting-tool and template shortcuts |
| 3 | Six open models on the fresh tests, and on standard VQA with their own plain prompt | fair open-model comparison |
| 4 | Three frontier flagships on the fresh tests, held-out wordings, **highest reasoning effort**, and standard VQA | fair frontier comparison |
| 5 | Label-noise check, without-degraded-views utility, clarify by degradation, cost matrices, lesion size, tool use, clean-looking erasures | robustness |
| 6 | Release of the v4 model and the benchmark (private Hugging Face repositories) | reproducibility |

Few-shot and cautious-prompt frontier runs (notebooks 17 and 20) are reused and compared with v4 on the same cases.

**Run it in parallel (recommended):** open this notebook in four Colab sessions at once, set `PART` in the first
cell differently in each, and choose *Run all* in each. Every part writes its own result folders in Drive, so they
never touch each other.

| PART | Runtime | Runs | Time |
| --- | --- | --- | --- |
| `A` | A100 | sections 1-2 (the v4 model) | ~3-4 h |
| `B1` | A100 | section 3, open models 1-3 | ~2-3 h |
| `B2` | A100 | section 3, open models 4-6 | ~2-3 h |
| `C` | CPU | section 4 (API) | ~3-5 h |
| `report` | CPU | sections 5-6 and the report, **after the four parts above have finished** | ~45 min |

`PART = 'all'` runs everything in one session (about 10-12 hours). API cost about $90-130 (estimate printed before
spending). Every step resumes. Colab secrets: `HF_TOKEN` (write access, for the release), `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`.
""" + SECRETS_NOTE),
        code("""
PART = 'all'  #@param ["all", "A", "B1", "B2", "C", "report"]
"""),
        code(SETUP), code(GPU_STACK), code("!pip install -q -U openai anthropic google-genai huggingface_hub"),
        code(RESTORE_ALL), code(RESTORE_V4), code(RESTORE_EVAL),
        code(f"""
import torch
GPU_GB = torch.cuda.get_device_properties(0).total_memory / 2 ** 30 if torch.cuda.is_available() else 0
BATCH = 24 if GPU_GB >= 38 else 8      # more episodes per batch on an A100/H100: same replies, faster
print('PART:', PART, '| GPU memory:', round(GPU_GB), 'GB | episodes per batch:', BATCH)
for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'HF_TOKEN'):
    if secret(name):
        os.environ[name] = secret(name)
FLAGSHIPS = {FLAGSHIP_TAGS!r}
FLAGSHIPS = [f for f in FLAGSHIPS if os.environ.get({{'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY'}}[f[1]])]
choice = json.load(open(f'{{ADAPTERS}}/final_choice_v4.json'))
FINAL = choice['adapter']
print('final model:', choice['chosen'], FINAL, '| frontier models:', [m for _, _, m in FLAGSHIPS])
INP = f'{{DRIVE}}/inpaint_test'
PARA = f'{{V4}}/paraphrase/views.jsonl'
PER_VIEW = {{'gpt-6-astra': 0.0145, 'claude-opus-5-5': 0.0139, 'gemini-4-argon': 0.0079}}   # measured in notebook 12
from medscope.eval.runner import load_views, remaining
def cost(views, run, model, factor=1.0):
    vs = [v for f in views.split() for v in load_views(f)]
    return len(remaining(vs, f'{{RESULTS}}/{{run}}', 'api')) * PER_VIEW[model] * factor
"""),
        md("## 1. The final model on every test set (PART A)"),
        gated(("A",), f"""
SETS = [('test', f'{{TEST_VIEWS}} {{TEST_NEG}}', ''), ('ext', EXT_VIEWS, ''), ('fresh', FRESH, ''), ('ext2', EXT2, ''),
        ('vqa', VQA_VIEWS, ''), ('notools_test', f'{{TEST_VIEWS}} {{TEST_NEG}}', '--tool-budget 0')]
for split, views, extra in SETS:
    !python scripts/evaluate.py --model {BASE} --adapter {{FINAL}} --views {{views}} {{extra}} --out {{RESULTS}}/v4_final_{{split}} --name medscope-v4 --split {{split}} --batch-size {{BATCH}}
"""),
        md("## 2. Held-out inpainting tools and held-out question wordings (PART A)"),
        gated(("A",), f"""
for t in ['telea', 'transplant', 'diffusion']:
    if not os.path.exists(f'{{INP}}/{{t}}/views.jsonl'):
        raise SystemExit(f'{{t}}: held-out-tool views missing, run notebook 20 (on a GPU for diffusion) first')
    !python scripts/evaluate.py --model {BASE} --adapter {{FINAL}} --views {{INP}}/{{t}}/views.jsonl --vocab-from {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/v4_inp_{{t}}_final_test --name medscope-v4-{{t}} --split test --batch-size {{BATCH}}
!python scripts/paraphrase_views.py --views {{TEST_VIEWS}} {{TEST_NEG}} --out {{PARA}}
!python scripts/evaluate.py --model {BASE} --adapter {{FINAL}} --views {{PARA}} --vocab-from {{TEST_VIEWS}} {{TEST_NEG}} --out {{RESULTS}}/v4_final_para_test --name medscope-v4-paraphrase --split test --batch-size {{BATCH}}
"""),
        md("## 3. Open models: fresh test sets, and standard VQA with their own plain prompt (PART B1: models 1-3, B2: 4-6)"),
        gated(("B1", "B2"), f"""
OPEN = [
{open_rows}
]
OPEN = {{'B1': OPEN[:3], 'B2': OPEN[3:]}}.get(PART, OPEN)
failed = []
for tag, name, model in OPEN:
    for split, views, extra in (('fresh', FRESH, ''), ('ext2', EXT2, ''), ('vqaplain', VQA_VIEWS, '--prompt plain')):
        try:
            !python scripts/evaluate.py --model {{model}} --views {{views}} {{extra}} --out {{RESULTS}}/v2_{{tag}}_{{split}} --name {{name}} --split {{split}} --batch-size {{min(BATCH, 16)}}
        except SystemExit:
            failed.append(f'{{name}} ({{split}})')
            import torch; torch.cuda.empty_cache()
print('failed:', failed or 'none')
"""),
        md("""## 4. Frontier flagships (API)

a. the fresh internal and fresh external tests; b. the held-out wordings (150 cases); c. **highest reasoning effort**
(OpenAI `reasoning_effort=high`, Anthropic effort `max`, Gemini thinking level `high`) on the same 150 test cases as
the cautious and few-shot runs; d. standard VQA, same agent loop as every other model. (PART C, CPU is fine)"""),
        gated(("C",), r"""
TEST = f'{TEST_VIEWS} {TEST_NEG}'
if not os.path.exists(PARA):      # built in section 2; a separate API session builds its own (same, deterministic)
    !python scripts/paraphrase_views.py --views {TEST_VIEWS} {TEST_NEG} --out {PARA}
plan = []
for tag, p, m in FLAGSHIPS:
    plan += [(tag, p, m, 'fresh', FRESH, f'v2_{tag}_fresh', '', 1.0), (tag, p, m, 'ext2', EXT2, f'v2_{tag}_ext2', '', 1.0),
             (tag, p, m, 'test', PARA, f'v2_para_{tag}_test', f'--vocab-from {TEST} --limit-cases 150', 1.0),
             (tag, p, m, 'test', TEST, f'v2_high_{tag}_test', '--limit-cases 150 --effort high', 4.0),
             (tag, p, m, 'vqa', VQA_VIEWS, f'v2_{tag}_vqa', '', 1.0)]
print(f"estimated API cost still to spend: ${sum(cost(v, r, m, f) for _, _, m, _, v, r, _, f in plan):.0f} "
      "(high effort estimated at 4x; the measured cost is in each run's usage.json)")
failed = []
for tag, p, m, split, views, run, extra, _ in plan:
    suffix = {'v2_high_': '-high', 'v2_para_': '-paraphrase'}.get(run[:8], '')
    try:
        !python scripts/evaluate.py --api {p} --model {m} --views {views} {extra} --out {RESULTS}/{run} --name {p}-{m}{suffix} --split {split} --batch-size 8
    except SystemExit:
        failed.append(run)
print('failed:', failed or 'none')
!python scripts/api_errors.py --results {RESULTS}
"""),
        md("## 5. Robustness analyses from stored results (PART report, after A, B1, B2 and C)"),
        gated(("report",), f"""
need = ['v4_final_test', 'v4_final_ext', 'v4_final_fresh', 'v4_final_ext2', 'v4_final_vqa', 'v4_final_notools_test',
        'v4_final_para_test'] + [f'v4_inp_{{t}}_final_test' for t in ('telea', 'transplant', 'diffusion')] \\
    + [f'v2_{{t}}_{{s}}' for t in {open_tags!r} for s in ('fresh', 'ext2', 'vqaplain')] \\
    + [f'{{r}}' for t, _, _ in FLAGSHIPS for r in (f'v2_{{t}}_fresh', f'v2_{{t}}_ext2', f'v2_para_{{t}}_test', f'v2_high_{{t}}_test', f'v2_{{t}}_vqa')]
done = lambda r: os.path.exists(f'{{RESULTS}}/{{r}}/summary.json') and json.load(open(f'{{RESULTS}}/{{r}}/summary.json'))['n_views'] > 0
missing = [r for r in need if not done(r)]
print('runs not finished yet:', missing or 'none')
if missing and PART == 'report':
    print('WARNING: the parts above have not all finished; the report will have gaps until this cell is rerun')
!python scripts/rescore_all.py --results {{RESULTS}} --pattern 'v4_final*'
!python scripts/rescore_all.py --results {{RESULTS}} --pattern 'v2_*'      # every compared run judged by the same current rules
JUDGES = {FRONTIER_RUNS!r}
!python scripts/label_check.py consensus --views {{TEST_NEG}} --results {{RESULTS}} --judges {{' '.join(JUDGES)}} --min-votes 7 --runs v4_final_test v2_medscope3_test {{' '.join(JUDGES)}} --ref v4_final_test --out {{RESULTS}}/label_check_v4
RUNS = ['v4_final_test=MedScope v4', 'v4_final_notools_test=MedScope v4, tools off'] + [f'{{r}}={{r}}' for r in JUDGES]
q = lambda xs: ' '.join(f'"{{x}}"' for x in xs)
!python scripts/extra_analysis.py --results {{RESULTS}} --views {{TEST_VIEWS}} {{TEST_NEG}} --runs {{q(RUNS)}} --tool-runs {{q(RUNS[:1] + RUNS[2:])}} --out {{RESULTS}}/extra_analysis_v4.md > /dev/null
!python scripts/inpainter_summary.py --results {{RESULTS}} --inpainters telea transplant diffusion --model 'MedScope v4=v4_final_test' --model 'MedScope v3=v2_medscope3_test' --model 'gpt-6-astra=v2_gpt6astra_test' --model 'claude-opus-5-5=v2_claudeopus_test' --model 'gemini-4-argon=v2_gemini_test' --ref 'MedScope v4' --training-tools lama transplant --out {{RESULTS}}/inpainters_v4.md
if os.path.exists(f'{{RESULTS}}/edit_guess_gemini/scores.jsonl'):
    !python scripts/clean_split.py --scores {{RESULTS}}/edit_guess_gemini/scores.jsonl --results {{RESULTS}} --runs {{' '.join(r.split('=')[0] + '=' + r.split('=')[1].replace(' ', '_') for r in RUNS)}} --out {{RESULTS}}/clean_split_v4.md
# net utility without the degraded views, and asking to clarify by degradation type, on every test set
OPEN_TAGS = {open_tags!r}
FLAG = {[t for t, _, _ in FLAGSHIP_TAGS]!r}
for split, views in (('test', f'{{TEST_VIEWS}} {{TEST_NEG}}'), ('ext', EXT_VIEWS), ('fresh', FRESH), ('ext2', EXT2)):
    runs = [f'v4_final_{{split}}=MedScope v4'] + ([f'v2_medscope3_{{split}}=MedScope v3'] if split in ('test', 'ext') else []) \\
        + [f'v2_{{t}}_{{split}}={{t}}' for t in FLAG + OPEN_TAGS]
    !python scripts/breakdowns.py --results {{RESULTS}} --views {{views}} --runs {{q(runs)}} --ref v4_final_{{split}} --out {{RESULTS}}/breakdowns_{{split}}.md > /dev/null
!python scripts/example_figure.py --views {{TEST_VIEWS}} --negatives {{TEST_NEG}} --out {{RESULTS}}/figures
"""),
        md("## 6. Release: the v4 model and the benchmark (private Hugging Face repositories; make public on submission; PART report)"),
        gated(("report",), r"""
UPLOAD = True     # False: only prepare the folders in Drive
flag = '--upload' if UPLOAD and os.environ.get('HF_TOKEN') else ''
MORE = (f"--more fresh_internal={FRESH.replace(' ', ',')} --more fresh_external={EXT2.replace(' ', ',')} "
        + ' '.join(f'--more heldout_inpainter_{t}={INP}/{t}/views.jsonl' for t in ['telea', 'transplant', 'diffusion']))
BLURB = ('MedScope v4: counterfactual SFT (LaMa and tissue-transplant erasures, matched edits elsewhere, lesion insertions, '
         'degradations, paraphrased questions, window and zoom tools), rejection-sampling fine-tuning and general medical '
         'VQA replay; selected on validation by a pre-registered rule.')
!python scripts/release_hf.py --final {FINAL} --final-runs v4_final_test v4_final_ext --final-blurb '{BLURB}' --results {RESULTS} --views {TEST_VIEWS} {TEST_NEG} --external {EXT_VIEWS} {MORE} --out {DRIVE}/release_v4 {flag}
"""),
        gated(("report",), "".join(publish("MedScope report - 24 v4 everywhere", f"""
    ('Final model', read_text(f'{{ADAPTERS}}/final_choice_v4.json')),
    ('Main test: v4 vs every model (paired)', {sig('v4_final_test', FRONTIER_RUNS + base_runs + ['v2_medscope3_test', 'v2_medscope_test'])}),
    ('Main test by imaging type', by_dataset(RESULTS, ['v4_final_test', 'v2_medscope3_test'] + {flag_runs!r})),
    ('External centres: v4 vs flagships and open models (paired)', {sig('v4_final_ext', [r.replace('_test', '_ext') for r in flag_runs + base_runs] + ['v2_medscope3_ext'])}),
    ('External centres by source', by_dataset(RESULTS, ['v4_final_ext', 'v2_medscope3_ext'] + {[r.replace('_test', '_ext') for r in flag_runs]!r})),
    ('Fresh internal test (confirmatory)', {sig('v4_final_fresh', [f"v2_{t}_fresh" for t, _, _ in FLAGSHIP_TAGS] + [f"v2_{t}_fresh" for t in open_tags])}),
    ('Fresh internal by imaging type', by_dataset(RESULTS, ['v4_final_fresh'] + {[f"v2_{t}_fresh" for t, _, _ in FLAGSHIP_TAGS]!r})),
    ('Fresh external test (confirmatory)', {sig('v4_final_ext2', [f"v2_{t}_ext2" for t, _, _ in FLAGSHIP_TAGS] + [f"v2_{t}_ext2" for t in open_tags])}),
    ('Fresh external by source', by_dataset(RESULTS, ['v4_final_ext2'] + {[f"v2_{t}_ext2" for t, _, _ in FLAGSHIP_TAGS]!r})),
    ('Standard VQA: every model in the same agent loop', vqa_table(RESULTS, ['v4_final_vqa', 'v2_medscope3_vqa'] + {[f"v2_{t}_vqa" for t, _, _ in FLAGSHIP_TAGS] + [f"v2_{t}_vqa" for t in open_tags]!r})),
    ('Standard VQA: open models with their own plain prompt', vqa_table(RESULTS, {[f"v2_{t}_vqaplain" for t in open_tags]!r})),
    ('Held-out inpainting tools', read_text(f'{{RESULTS}}/inpainters_v4.md')),
    ('Held-out question wordings: v4 vs its own original-wording run (paired)', {sig('v4_final_para_test', ['v4_final_test'])}),
    ('Held-out wordings: v4 vs flagships (paired, 150 cases)', {sig('v4_final_para_test', [f"v2_para_{t}_test" for t, _, _ in FLAGSHIP_TAGS])}),
    ('Highest-reasoning-effort flagships vs v4 (paired, 150 cases)', {sig('v4_final_test', [f"v2_high_{t}_test" for t, _, _ in FLAGSHIP_TAGS])}),
    ('Highest effort vs default effort, same model, same 150 cases', '\\n\\n'.join(significance_table(RESULTS, f'v2_high_{{t}}_test', [f'v2_{{t}}_test']) for t in {[t for t, _, _ in FLAGSHIP_TAGS]!r})),
    ('Few-shot flagships vs v4 (paired, 150 cases)', {sig('v4_final_test', [f"v2_fewshot_{t}_test" for t, _, _ in FLAGSHIP_TAGS])}),
    ('Cautious-prompt flagships vs v4 (paired, 150 cases)', {sig('v4_final_test', [f"v2_cautious_{t}_test" for t, _, _ in FLAGSHIP_TAGS])}),
    ('Tools switched off', {sig('v4_final_test', ['v4_final_notools_test'])}),
    ('Without degraded views, and clarify by degradation: main test', read_text(f'{{RESULTS}}/breakdowns_test.md')),
    ('Without degraded views, and clarify by degradation: external centres', read_text(f'{{RESULTS}}/breakdowns_ext.md')),
    ('Without degraded views, and clarify by degradation: fresh internal', read_text(f'{{RESULTS}}/breakdowns_fresh.md')),
    ('Without degraded views, and clarify by degradation: fresh external', read_text(f'{{RESULTS}}/breakdowns_ext2.md')),
    ('Label check (without disputed healthy images)', read_text(f'{{RESULTS}}/label_check_v4/sensitivity_auto.md')),
    ('Clean-looking vs visible erasures', read_text(f'{{RESULTS}}/clean_split_v4.md')),
    ('Extra analyses (decisions, cost matrices, tool use, lesion size)', read_text(f'{{RESULTS}}/extra_analysis_v4.md')),
    ('Highest-effort flagships: leaderboard', compare_runs(RESULTS, 'v2_high_*')),
    ('Model card (released)', read_text(f'{{DRIVE}}/release_v4/MedScope-4B/README.md')),
""")["source"])),
    ]


def nb25_v4_recipe() -> list[dict]:
    s1, nocf = S1_ARGS, S1_NOCF_ARGS      # inserted as text into the f-strings below: braces stay single
    tgt = ("--views {TRAIN_V4_BASE} {V4}/train_tp/views.jsonl --negatives {TRAIN_NEG_V4} "
           "--kinds original target_removal natural_negative degraded --epochs 3 --max-steps {S1_STEPS} "
           "--schedule-steps {S1_TOTAL} --mode agentic --window-prob 0.3 --small-zoom --oversample-small 2 "
           "--paraphrase-prob 0.5")
    nocf_abs = nocf + " --min-absent-share {CF_ABSENT}"
    return [
        md(f"""
# MedScope 25: the v4 recipe, like-for-like (ablations, seeds, second base model)

Everything here is stage 1 of the v4 recipe, compared at stage 1: same data pools, same number of optimiser steps,
same learning-rate schedule (checked in the notebook).

| Arm | Training views | Question it answers |
| --- | --- | --- |
| **With CF** (notebook 23 stage 1, seeds 0-2) | originals, lesion erased, edit elsewhere, insertions, degraded, healthy | the recipe |
| **Without CF** (seeds 0-2) | originals, degraded, healthy | do counterfactual views matter? |
| **Without CF, absent-matched** | as above, healthy images repeated to the With-CF share of "absent" answers | is the gain only more "No" answers? |
| **Erasures only** | originals, lesion erased (LaMa and transplant), degraded, healthy: no edits elsewhere, no insertions | do the control edits stop an "edited means absent" shortcut? |
| **MedGemma 1.5 4B**, with and without CF | as With CF / Without CF | does the recipe transfer to a second base model? |

Each model is tested on the main test, the external centres and the fresh external test; the With CF, Without CF,
absent-matched and erasures-only arms (seed 0) also on the erasures remade by three held-out inpainting tools.

**Run it in parallel (recommended):** about 50 A100-hours in total (nine trainings of about 3.5-4 hours, plus
tests). Open this notebook in several Colab sessions at once (one A100 each), set `PARTS` to the number of sessions
and `PART` to 1, 2, ... in each, and choose *Run all* in each. The jobs are split so every session has about the same
amount of work; each writes only its own folders in Drive. With 3 sessions it takes about 19 hours, with 4 about 16,
with 5 about 12 (the first cell after setup prints which jobs each part gets). When all have finished, run the notebook once more with `PART = 'report'` (CPU is fine) for the
summaries and the report. `PART = 'all'` runs everything in one session. Every step resumes.
MedGemma needs `HF_TOKEN` with its terms accepted (https://huggingface.co/{MEDGEMMA}).
""" + SECRETS_NOTE),
        code("""
PARTS = 4     #@param {type:"integer"}
PART = 'all'  #@param ["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "report"] {allow-input: true}
"""),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL), code(RESTORE_V4), code(RESTORE_EVAL),
        code(r"""
from medscope.eval.runner import load_views
_s1 = json.load(open(f'{ADAPTERS}/v4_s1/state.json'))
S1_STEPS, S1_TOTAL = _s1['opt_step'], _s1['total_steps']    # every other arm takes as many steps on the same LR schedule
pool = [v for f in (TRAIN_V4 + ' ' + TRAIN_NEG_V4).split() for v in load_views(f)]
CF_ABSENT = round(sum(v.kind.value in ('target_removal', 'natural_negative') for v in pool) / len(pool), 3)
print('stage-1 steps:', S1_STEPS, '| schedule length:', S1_TOTAL, "| share of 'absent' answers with CF:", CF_ABSENT)
INP = f'{DRIVE}/inpaint_test'
def test_all(model, adapter, name, heldout=False):
    head, rest = name.split('_', 1)                       # v4q_cf_s0 -> held-out-tool runs v4q_inp_telea_cf_s0_test
    sets = [('test', f'{TEST_VIEWS} {TEST_NEG}', '', f'{name}_test'), ('ext', EXT_VIEWS, '', f'{name}_ext'),
            ('ext2', EXT2, '', f'{name}_ext2')]
    if heldout:
        sets += [('test', f'{INP}/{t}/views.jsonl', f'--vocab-from {TEST_VIEWS} {TEST_NEG}', f'{head}_inp_{t}_{rest}_test')
                 for t in ('telea', 'transplant', 'diffusion')]
    for split, views, extra, run in sets:
        !python scripts/evaluate.py --model {model} --adapter {adapter} --views {views} {extra} --out {RESULTS}/{run} --name {name} --split {split} --batch-size {BATCH}
GPU_GB = torch.cuda.get_device_properties(0).total_memory / 2 ** 30 if torch.cuda.is_available() else 0
BATCH = 24 if GPU_GB >= 38 else 8      # more test episodes per batch on an A100/H100: same replies, faster
"""),
        md("## Which jobs this session runs"),
        code(f"""
# (model, tag, arm, seed, estimated hours); 'test' = only testing notebook 23's stage 1 (seed 0 with CF)
JOBS = [('{BASE}', 'v4q', 'test', 0, 2.5), ('{BASE}', 'v4q', 'nocf', 0, 6.5), ('{BASE}', 'v4q', 'nocfabs', 0, 6.5),
        ('{BASE}', 'v4q', 'tgt', 0, 6.5), ('{BASE}', 'v4q', 'cf', 1, 5), ('{BASE}', 'v4q', 'nocf', 1, 5),
        ('{BASE}', 'v4q', 'cf', 2, 5), ('{BASE}', 'v4q', 'nocf', 2, 5),
        ('{MEDGEMMA}', 'v4mg', 'cf', 0, 5.5), ('{MEDGEMMA}', 'v4mg', 'nocf', 0, 5.5)]
load = [0.0] * PARTS
owner = {{}}
for i in sorted(range(len(JOBS)), key=lambda i: -JOBS[i][4]):     # longest first, each to the least-loaded part
    k = min(range(PARTS), key=lambda k: load[k])
    owner[i], load[k] = k + 1, load[k] + JOBS[i][4]
for k in range(1, PARTS + 1):
    print(f'part {{k}} (~{{load[k - 1]:.0f}} h):', ', '.join(f'{{j[1]}}_{{j[2]}}_s{{j[3]}}' for i, j in enumerate(JOBS) if owner[i] == k))
# '+' runs parts at the same time on one GPU ('3+4'); ',' runs parts one after the other ('2,9+6': 2 then 9, next to 6)
TOKENS = [[p.strip() for p in t.split(',')] for t in str(PART).split('+')]
MY_PARTS = [p for t in TOKENS for p in t]
MINE = [j for i, j in enumerate(JOBS) if PART == 'all' or str(owner[i]) in MY_PARTS]
GROUPS = [MINE] if PART == 'all' else [[j for i, j in enumerate(JOBS) if str(owner[i]) in t] for t in TOKENS]
print('this session (PART', PART, '):', [f'{{j[1]}}_{{j[2]}}_s{{j[3]}}' for j in MINE] or 'no training or testing')
"""),
        md("## Quick check that MedGemma trains (3 steps on 50 views; only in the session that trains MedGemma)"),
        code(f"""
if any(j[1] == 'v4mg' for j in MINE) and not os.path.exists(f'{{ADAPTERS}}/v4mg_cf_s0/state.json'):
    !python scripts/train_sft.py --model {MEDGEMMA} --views {{TRAIN_V4}} --negatives {{TRAIN_NEG_V4}} --subsample 50 --max-steps 3 --grad-accum 2 --mode agentic --out {{WORK}}/mg_smoke
    print('MedGemma training works')
"""),
        md("## Train and test this session's jobs"),
        code(f"""
ARGS = {{'cf': f'{s1}', 'nocf': f'{nocf}', 'nocfabs': f'{nocf_abs}', 'tgt': f'{tgt}'}}
import threading, subprocess, time
def gpu_monitor(stop):        # GPU use every 5 minutes, printed and saved to Drive (results/gpu_log_part<PART>.txt)
    while not stop.wait(300):
        q = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,power.draw',
                            '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
        line = time.strftime('%H:%M') + ' GPU util, memory used, memory total, power: ' + q
        print(line, flush=True)
        with open(f"{{RESULTS}}/gpu_log_part{{str(PART).replace('+', '_').replace(',', '_')}}.txt", 'a') as f:
            f.write(line + '\\n')
def run_jobs(jobs):
    for model, tag, arm, seed, _ in jobs:
        if arm == 'test':
            test_all(model, f'{{ADAPTERS}}/v4_s1/final', 'v4q_cf_s0', heldout=True)     # seed 0 with CF = notebook 23's stage 1
            continue
        name = f'{{tag}}_{{arm}}_s{{seed}}'
        out = f'{{ADAPTERS}}/{{name}}'
        if not os.path.exists(f'{{out}}/final/adapter_config.json'):
            a = ARGS[arm]
            !python scripts/train_sft.py --model {{model}} {{a}} --seed {{seed}} --out {{out}}
        done = json.load(open(f'{{out}}/state.json'))['opt_step']
        if abs(done - S1_STEPS) > 0.02 * S1_STEPS:
            raise SystemExit(f'{{name}} took {{done}} steps, stage 1 took {{S1_STEPS}}: not like-for-like, stop and report this')
        test_all(model, f'{{out}}/final', name, heldout=(tag == 'v4q' and seed == 0))
def start_mps():
    # NVIDIA MPS lets the training processes of this tab run their GPU kernels at the same time instead of taking
    # turns; it changes no result. Used only if this runtime has it and a test process works through it.
    if len([g for g in GROUPS if g]) < 2 or not shutil.which('nvidia-cuda-mps-control'):
        return False
    env = {{'CUDA_MPS_PIPE_DIRECTORY': '/tmp/mps_pipe', 'CUDA_MPS_LOG_DIRECTORY': '/tmp/mps_log'}}
    for d in env.values():
        os.makedirs(d, exist_ok=True)
    os.environ.update(env)
    subprocess.run(['nvidia-cuda-mps-control', '-d'], capture_output=True)
    ok = subprocess.run([sys.executable, '-c', 'import torch; x = torch.ones(1024, device="cuda"); print(float(x.sum()))'],
                        capture_output=True, text=True, timeout=300).returncode == 0
    if not ok:
        subprocess.run('echo quit | nvidia-cuda-mps-control', shell=True, capture_output=True)
        for k in env:
            os.environ.pop(k, None)
    return ok
import shutil, sys
n_jobs = max(1, len([g for g in GROUPS if g]))
os.environ['OMP_NUM_THREADS'] = str(max(2, (os.cpu_count() or 8) // n_jobs))   # share the CPU cores between the jobs
print(f'{{n_jobs}} job(s) at once on this GPU | CPU cores: {{os.cpu_count()}} ({{os.environ["OMP_NUM_THREADS"]}} threads per job)')
print('NVIDIA MPS (GPU kernels of the parts run at the same time):', 'on' if start_mps() else 'off')
stop = threading.Event()
threading.Thread(target=gpu_monitor, args=(stop,), daemon=True).start()
errors = []
def guarded(jobs):
    try:
        run_jobs(jobs)
    except BaseException as e:      # noqa: BLE001 - reported after every part has finished
        errors.append(e)
threads = [threading.Thread(target=guarded, args=(g,)) for g in GROUPS if g]
for t in threads:
    t.start()
for t in threads:
    t.join()
stop.set()
if errors:
    raise SystemExit(f'{{len(errors)}} part(s) failed: ' + ' | '.join(str(e)[:300] for e in errors))
"""),
        md("## Summaries and report (PART report, after every part has finished)"),
        gated(("report",), r"""
missing = [f'{j[1]}_{"cf" if j[2] == "test" else j[2]}_s{j[3]}_{s}' for j in JOBS for s in ('test', 'ext', 'ext2')
           if not os.path.exists(f'{RESULTS}/{j[1]}_{"cf" if j[2] == "test" else j[2]}_s{j[3]}_{s}/summary.json')]
print('runs not finished yet:', missing or 'none')
for split in ('test', 'ext', 'ext2'):
    !python scripts/seed_summary.py --results {RESULTS} --arm 'With CF=v4q_cf_s0_{split},v4q_cf_s1_{split},v4q_cf_s2_{split}' --arm 'Without CF=v4q_nocf_s0_{split},v4q_nocf_s1_{split},v4q_nocf_s2_{split}' --out {RESULTS}/v4_seeds_{split}.md
!python scripts/inpainter_summary.py --results {RESULTS} --inpainters telea transplant diffusion --model 'With CF=v4q_cf_s0_test' --model 'Without CF=v4q_nocf_s0_test' --model 'Without CF, absent-matched=v4q_nocfabs_s0_test' --model 'Erasures only=v4q_tgt_s0_test' --ref 'With CF' --training-tools lama transplant --out {RESULTS}/inpainters_v4_ablation.md
"""),
        gated(("report",), "".join(publish("MedScope report - 25 v4 recipe", f"""
    ('Main test: three seeds per arm', read_text(f'{{RESULTS}}/v4_seeds_test.md')),
    ('External centres: three seeds per arm', read_text(f'{{RESULTS}}/v4_seeds_ext.md')),
    ('Fresh external: three seeds per arm', read_text(f'{{RESULTS}}/v4_seeds_ext2.md')),
    ('Main test: With CF vs every ablation arm (seed 0, paired)', significance_table(RESULTS, 'v4q_cf_s0_test', ['v4q_nocf_s0_test', 'v4q_nocfabs_s0_test', 'v4q_tgt_s0_test'])),
    ('External centres: With CF vs every ablation arm (seed 0, paired)', significance_table(RESULTS, 'v4q_cf_s0_ext', ['v4q_nocf_s0_ext', 'v4q_nocfabs_s0_ext', 'v4q_tgt_s0_ext'])),
    ('Fresh external: With CF vs every ablation arm (seed 0, paired)', significance_table(RESULTS, 'v4q_cf_s0_ext2', ['v4q_nocf_s0_ext2', 'v4q_nocfabs_s0_ext2', 'v4q_tgt_s0_ext2'])),
    ('Held-out inpainting tools, ablation arms', read_text(f'{{RESULTS}}/inpainters_v4_ablation.md')),
    ('MedGemma with vs without counterfactual views (main test)', significance_table(RESULTS, 'v4mg_cf_s0_test', ['v4mg_nocf_s0_test', 'v2_base_medgemma15_test'])),
    ('MedGemma with vs without counterfactual views (external centres)', significance_table(RESULTS, 'v4mg_cf_s0_ext', ['v4mg_nocf_s0_ext', 'v2_base_medgemma15_ext'])),
    ('MedGemma with vs without counterfactual views (fresh external)', significance_table(RESULTS, 'v4mg_cf_s0_ext2', ['v4mg_nocf_s0_ext2', 'v2_base_medgemma15_ext2'])),
    ('Qwen vs MedGemma base, same v4 stage-1 recipe', significance_table(RESULTS, 'v4q_cf_s0_test', ['v4mg_cf_s0_test'])),
    ('Stage 1 vs the final model (what stages 2-3 add)', significance_table(RESULTS, 'v4_final_test', ['v4q_cf_s0_test'])),
""")["source"])),
    ]


def nb24c_frontier() -> list[dict]:
    """Notebook 24, section 4 only (frontier API runs), as its own notebook for a CPU session."""
    c = nb24_v4_eval()
    pick = lambda i: c[i]
    assert "PART = 'all'" in "".join(c[1]["source"]) and "if PART in ('all', 'C')" in "".join(c[16]["source"])
    return [md("""
# MedScope 24c: frontier flagships only (API, CPU runtime)

Section 4 of notebook 24 on its own: gpt-6-astra, claude-opus-5-5 and gemini-4-argon on the fresh internal and fresh
external tests, the held-out question wordings (150 cases), their highest reasoning setting (150 cases) and standard
VQA. Runs on a **CPU** runtime; every run resumes and finished runs are skipped. Colab secrets `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`. When it has finished, run notebook 24 with `PART = 'report'`.
"""), code("PART = 'C'"), pick(2), pick(4), pick(5), pick(6), pick(7), pick(8), pick(15), pick(16)]


def nb25_part(parts: str, jobs: str):
    """Notebook 25 fixed to one set of parts (PARTS = 9), so each tab needs no settings."""
    def build() -> list[dict]:
        cells = nb25_v4_recipe()
        i = next(k for k, c in enumerate(cells) if "PARTS = " in "".join(c["source"]) and "#@param" in "".join(c["source"]))
        cells[i] = code(f"PARTS = 9\nPART = {parts!r}      # this notebook's jobs: {jobs}")
        cells.insert(0, md(f"""
# MedScope 25 (part {parts.replace(',', ', then ').replace('+', ' and ')}): {jobs}

Part of notebook 25 fixed to these jobs: open it in its own tab on an **A100 or G4** runtime and choose **Run all**.
Nothing to set. The jobs run at the same time on the one GPU (a Qwen job needs about 16 GB, so two fit on a 40 GB
A100). Finished work is skipped and interrupted training resumes from its last checkpoint. With two 40 GB GPUs: 25e and
25f, then 25g and 25h for what is left.
"""))
        return cells
    return build


def nb24r_report() -> list[dict]:
    """Notebook 24 fixed to PART = 'report' (CPU): analyses, the final report and the release."""
    cells = nb24_v4_eval()
    assert "PART = 'all'" in "".join(cells[1]["source"])
    cells[1] = code("PART = 'report'")
    cells[0] = md("""
# MedScope 24r: final report of notebook 24 (CPU)

Run after notebooks 24 and 24c have finished. **CPU runtime, Run all, nothing to set.** Builds every paired
comparison, the breakdowns, the label check and the figures from the stored results, publishes the report, and
uploads the v4 model and the benchmark to private Hugging Face repositories (Colab secret `HF_TOKEN` with write
access and Notebook access switched on). About 45 minutes.
""")
    return cells


def nb26_siim_fullres() -> list[dict]:
    full_runs = ["v4_final_siimfull", "v4q_cf_s0_siimfull", "v4q_nocf_s0_siimfull", "v2_base_qwen35_siimfull",
                 "v2_gemini_siimfull"]
    low_runs = ["v4_final_ext2", "v4q_cf_s0_ext2", "v4q_nocf_s0_ext2", "v2_base_qwen35_ext2", "v2_gemini_ext2"]
    return [
        md("""
# MedScope 26: SIIM pneumothorax at original resolution (post-hoc analysis)

**Not part of the pre-registered evaluation; no model is changed.** On the fresh external test every Qwen-based model
(the base model, both stage-1 arms and MedScope v4) missed nearly all SIIM pneumothoraxes. That test used a 256-pixel
copy of SIIM. This notebook rebuilds exactly the same images from the original SIIM-ACR files (1024 pixels, saved at
768 like every other image in this project), builds the same views, and tests the same models, to see whether
resolution is the cause.

**Needs:** an A100 or L4 runtime, about 1 hour; the Colab secrets `KAGGLE_USERNAME` and `KAGGLE_KEY` (kaggle.com ->
your profile -> Settings -> API -> *Create New Token*; the downloaded kaggle.json holds both values) with Notebook
access switched on, plus `HF_TOKEN` (and `GEMINI_API_KEY` for the optional gemini-4-argon run, about $2). Downloads
the SIIM-ACR training DICOMs (Kaggle dataset seesee/siim-train-test, about 2 GB).
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code("!pip install -q kaggle pydicom"), code(LAMA_CELL), code(RESTORE_ALL),
        code(RESTORE_V4),
        md("## 1. Original SIIM-ACR images"),
        code(r"""
import glob
for k in ('KAGGLE_USERNAME', 'KAGGLE_KEY', 'GEMINI_API_KEY'):
    if secret(k):
        os.environ[k] = secret(k)
import subprocess
SIIM = f'{WORK}/raw/siim_full'
SOURCES = ['jesperdramsch/siim-acr-pneumothorax-segmentation-data', 'seesee/siim-train-test']   # SIIM-ACR DICOMs + RLE masks
MANUAL = f'{DRIVE}/siim'      # or put the Kaggle download here yourself: archive.zip, or the unzipped folder
dcm = lambda: glob.glob(f'{SIIM}/**/*.dcm', recursive=True)
if not dcm() and os.path.isdir(MANUAL):
    for z in glob.glob(f'{MANUAL}/*.zip'):
        local = f'{WORK}/raw/{os.path.basename(z)}'       # copy off Drive first: unzip on a Drive file can fail mid-read
        if not os.path.exists(local) or os.path.getsize(local) != os.path.getsize(z):
            print('copying', z, f'({os.path.getsize(z) / 2 ** 30:.1f} GB)')
            os.makedirs(os.path.dirname(local), exist_ok=True)
            subprocess.run(['cp', z, local], check=True)
        print('unzipping', local)
        r = subprocess.run(['unzip', '-q', '-o', local, '-d', SIIM], capture_output=True, text=True)
        if r.returncode not in (0, 1) and not dcm():    # 1 = warnings only; 2 with files extracted = minor zip damage
            raise SystemExit(f'unzip failed ({r.returncode}): {(r.stderr or r.stdout)[-500:]}\n'
                             'The zip on Drive may be incomplete: check its size, or download it again.')
        if r.returncode:
            print(f'unzip finished with code {r.returncode} (continuing: {len(dcm())} DICOM files extracted)')
    if not dcm() and glob.glob(f'{MANUAL}/**/*.dcm', recursive=True):
        SIIM = MANUAL
if not dcm():
    if not os.environ.get('KAGGLE_KEY'):
        raise SystemExit(f'Put the SIIM-ACR download (archive.zip) in {MANUAL}, or add the Colab secrets KAGGLE_USERNAME '
                         'and KAGGLE_KEY with Notebook access switched on, then rerun this cell.')
    os.makedirs(SIIM, exist_ok=True)
    for ds in SOURCES:
        r = subprocess.run(['kaggle', 'datasets', 'download', '-d', ds, '-p', SIIM, '--unzip'], capture_output=True, text=True)
        if dcm():
            print('downloaded', ds)
            break
        print(ds, 'not available:', (r.stderr or r.stdout).strip()[-300:])
if not dcm():
    raise SystemExit(f'No SIIM-ACR DICOMs (see above). Download "SIIM ACR Pneumothorax Segmentation Data" from '
                     'https://www.kaggle.com/datasets/jesperdramsch/siim-acr-pneumothorax-segmentation-data (Download '
                     f'button -> archive.zip), put archive.zip in {MANUAL} on Drive, and rerun this cell.')
print(len(dcm()), 'DICOM files;', glob.glob(f'{SIIM}/**/*.csv', recursive=True))
"""),
        md("## 2. The same SIIM cases at original resolution, and their views"),
        code(r"""
FULL = f'{V4}/siim_full'
!python scripts/siim_fullres.py --views {EXT2} --siim {SIIM} --out {FULL}
!python scripts/build_views.py --manifest {FULL}/cases_test.jsonl --out {FULL}/views --inpainter lama
!python scripts/check_views.py --views {FULL}/views/views.jsonl
SIIMFULL = f'{FULL}/views/views_clean.jsonl {FULL}/negatives/views_negatives_external.jsonl'
"""),
        md("## 3. The same models (GPU), and gemini-4-argon (API, optional)"),
        code(f"""
import torch
BATCH = 24 if torch.cuda.get_device_properties(0).total_memory / 2 ** 30 >= 38 else 8
FINAL = json.load(open(f'{{ADAPTERS}}/final_choice_v4.json'))['adapter']
MODELS = [('v4_final', FINAL), ('v4q_cf_s0', f'{{ADAPTERS}}/v4_s1/final'), ('v4q_nocf_s0', f'{{ADAPTERS}}/v4q_nocf_s0/final'),
          ('v2_base_qwen35', None)]
for run, adapter in MODELS:
    a = f'--adapter {{adapter}}' if adapter else ''
    !python scripts/evaluate.py --model {BASE} {{a}} --views {{SIIMFULL}} --out {{RESULTS}}/{{run}}_siimfull --name {{run}}-siimfull --split siimfull --batch-size {{BATCH}}
if os.environ.get('GEMINI_API_KEY'):
    !python scripts/evaluate.py --api gemini --model gemini-4-argon --views {{SIIMFULL}} --out {{RESULTS}}/v2_gemini_siimfull --name gemini-4-argon-siimfull --split siimfull --batch-size 8
"""),
        md("## 4. 256 pixels vs original resolution"),
        code(f"""
from medscope.eval.runner import scored_rows
# the same cases in both columns: only the SIIM cases found in the original-resolution data
MATCHED = {{json.loads(l)['case_id'].replace('siimfull', 'siimext', 1) for l in open(f'{{FULL}}/cases_test.jsonl') if l.strip()}}
def present(run, prefix):
    if not os.path.exists(f'{{RESULTS}}/{{run}}'):
        return 0, 0
    rows = [r for r in scored_rows(f'{{RESULTS}}/{{run}}') if r['case_id'].startswith(prefix) and r['kind'] == 'original'
            and r['case_id'].replace('siimfull', 'siimext', 1) in MATCHED]
    return sum(r['action'] == 'answer' and not r.get('claims_absent') for r in rows), len(rows)
lines = [f'Same {{len(MATCHED)}} pneumothorax cases in both columns.', '',
         '| Model | Pneumothorax called present, 256 px | at original resolution |', '| --- | --- | --- |']
for low, full in zip({low_runs!r}, {full_runs!r}):
    (a, n), (b, m) = present(low, 'siimext'), present(full, 'siimfull')
    lines.append(f'| {{full.replace("_siimfull", "")}} | {{a}}/{{n}} ({{a / max(n, 1):.0%}}) | {{b}}/{{m}} ({{b / max(m, 1):.0%}}) |')
SIIM_TABLE = '\\n'.join(lines)
open(f'{{RESULTS}}/siim_fullres.md', 'w').write(SIIM_TABLE + '\\n')
print(SIIM_TABLE)
"""),
        publish("MedScope report - 26 SIIM full resolution", f"""
    ('Matched cases', read_text(f'{{FULL}}/report.txt')),
    ('Pneumothorax called present: 256 px vs original resolution', read_text(f'{{RESULTS}}/siim_fullres.md')),
    ('All metrics by source (SIIM rows: siimext = 256 px, siimfull = original resolution)', by_dataset(RESULTS, {low_runs + full_runs!r})),
"""),
    ]


PTX_PROBE_CELL = r"""
# GPU (about 15 min on an L4): stage 2 on the original-resolution SIIM cases, and every model asked a second question on
# the same pneumothorax images ("Is there an abnormality in this chest X-ray?"): is the miss about the image or the word?
!cd /content/medscope && git fetch -q && git reset -q --hard origin/main
import json, torch
from dataclasses import replace
from medscope.eval.runner import load_views
FULL = f'{V4}/siim_full'
SIIMFULL = f'{FULL}/views/views_clean.jsonl {FULL}/negatives/views_negatives_external.jsonl'
PROBE = f'{FULL}/probe_abnormality.jsonl'
with open(PROBE, 'w') as f:
    for v in load_views(f'{FULL}/views/views_clean.jsonl'):
        if v.kind.value == 'original':
            f.write(json.dumps(replace(v, view_id=v.view_id.replace('__original', 'abn__original'),
                                       question='Is there an abnormality in this chest X-ray?').to_dict()) + '\n')
BATCH = 24 if torch.cuda.get_device_properties(0).total_memory / 2 ** 30 >= 38 else 8
FINAL = json.load(open(f'{ADAPTERS}/final_choice_v4.json'))['adapter']
STAGES = [('v4q_cf_s0', f'{ADAPTERS}/v4_s1/final'), ('v4_s2', f'{ADAPTERS}/v4_s2/final'), ('v4_final', FINAL),
          ('v2_base_qwen35', None)]
!python scripts/evaluate.py --model Qwen/Qwen3.5-4B --adapter {ADAPTERS}/v4_s2/final --views {SIIMFULL} --out {RESULTS}/v4_s2_siimfull --name v4-stage2-siimfull --split siimfull --batch-size {BATCH}
for run, adapter in STAGES:
    a = f'--adapter {adapter}' if adapter else ''
    !python scripts/evaluate.py --model Qwen/Qwen3.5-4B {a} --views {PROBE} --out {RESULTS}/{run}_siimabn --name {run}-siimabn --split siimabn --batch-size {BATCH}
"""

PTX_DIAG_CELL = r"""
# CPU (a few minutes): what each stage was trained on, in-domain detection by stage, lesion size; report to Drive
import subprocess, sys
S1 = f"--views {TRAIN_V4} --negatives {TRAIN_NEG_V4} --mode agentic --subsample 16000 --window-prob 0.3 --small-zoom --oversample-small 2 --paraphrase-prob 0.5"
S2 = (f"--views {TRAIN_V4} --negatives {TRAIN_NEG_V4} --subsample 3000 --replays {ADAPTERS}/v4_rft/samples.jsonl --hard-repeat 3 "
      "--mode agentic --window-prob 0.3 --small-zoom --paraphrase-prob 0.5")
S3 = (f"--views {TRAIN_V4} {DRIVE}/external/vqa_train/views_vqa_train.jsonl --negatives {TRAIN_NEG_V4} --subsample 5000 "
      "--mode agentic --min-absent-share 0.35 --balance-health --window-prob 0.3 --small-zoom --paraphrase-prob 0.5")
R = RESULTS
runs = [('Stage 1, validation', 'v4_s1_val'), ('Stage 2, validation', 'v4_s2_val'), ('Stage 3, validation', 'v4_s3_val'),
        ('Stage 1, main test', 'v4q_cf_s0_test'), ('Final, main test', 'v4_final_test'), ('Final, fresh internal', 'v4_final_fresh')]
probes = [('Base Qwen', 'v2_base_qwen35_siimfull'), ('Stage 1', 'v4q_cf_s0_siimfull'), ('Stage 2', 'v4_s2_siimfull'),
          ('Final', 'v4_final_siimfull'), ('Base Qwen, abnormality question', 'v2_base_qwen35_siimabn'),
          ('Stage 1, abnormality question', 'v4q_cf_s0_siimabn'), ('Stage 2, abnormality question', 'v4_s2_siimabn'),
          ('Final, abnormality question', 'v4_final_siimabn')]
cmd = [sys.executable, 'scripts/diagnose_finding.py', '--finding', 'pneumothorax',
       '--stage', 'Stage 1', S1, '--stage', 'Stage 2', S2, '--stage', 'Stage 3 (final)', S3,
       '--views', *f'{VAL_V4} {VAL_NEG_V4} {TEST_VIEWS} {TEST_NEG} {FRESH}'.split(),
       *[a for n, r in runs if os.path.exists(f'{R}/{r}') for a in ('--run', f'{n}={R}/{r}')],
       '--probe-views', *SIIMFULL.split(), PROBE,
       *[a for n, r in probes if os.path.exists(f'{R}/{r}') for a in ('--probe-run', f'{n}={R}/{r}')],
       '--out', f'{R}/26b_pneumothorax_diagnosis.md']
subprocess.run(cmd, check=True, cwd='/content/medscope')
"""


def nb26b_diagnosis() -> list[dict]:
    """Why the final model misses pneumothorax (post hoc, nothing trained): run after notebook 26."""
    return [
        md("""
# MedScope 26b: why is pneumothorax missed? (post-hoc diagnosis)

Run after notebook 26, on an A100 or L4 (about 20 minutes). Trains nothing and changes no result. Writes
`results/26b_pneumothorax_diagnosis.md`:
1. what each training stage was trained to answer to questions naming pneumothorax (each stage's exact training list);
2. pneumothorax detection by stage on validation, the main test and the fresh internal test;
3. lesion size in training vs the SIIM cases, and detection by size;
4. the same SIIM images asked "Is there an abnormality?" instead: a miss of the image or of the word.
"""),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL), code(RESTORE_V4),
        code("assert os.path.exists(f'{V4}/siim_full/views/views_clean.jsonl') or os.path.exists(f'{RESULTS}/v4_final_siimfull/summary.json'), 'run notebook 26 first'"),
        code(PTX_PROBE_CELL), code(PTX_DIAG_CELL),
    ]


def nb27_v41() -> list[dict]:
    """Post-hoc remedy for the missed pneumothorax: v4.1 = stage 3 redone with SIIM pneumothorax training cases."""
    c26 = nb26_siim_fullres()
    siim_data = next(c for c in c26 if "MANUAL =" in "".join(c["source"]))
    siim_full = next(c for c in c26 if "siim_fullres.py" in "".join(c["source"]))
    s3 = ("--views {TRAIN_V4} {REPLAY} --negatives {TRAIN_NEG_V4} --subsample 5000 --lr 5e-5 --mode agentic "
          "--min-absent-share 0.35 --balance-health --window-prob 0.3 --small-zoom --paraphrase-prob 0.5")
    tests = ["test", "ext", "fresh", "ext2", "siimfull", "siimte"]
    return [
        md("""
# MedScope 27: v4.1, a post-hoc fix for the missed pneumothorax

**Post hoc, separate from the pre-registered evaluation; v4 stays the main model.** Notebook 26b showed that v4 misses
pneumothorax because training held almost no pneumothorax images (4, all large) and validation none, and that the
last stage (stage 3) turned the earlier stages' partial detection into none. v4.1 redoes only stage 3, from the same
stage 2, with the same data, settings and seed, plus SIIM-ACR pneumothorax images (and as many lesion-free ones) from
patients that appear nowhere in the evaluation. It is then tested on new SIIM patients and on every earlier test, to
check that nothing else got worse.

Also here: the control for the open question of notebook 26b (does v4 call every chest X-ray abnormal?).

**Needs:** an A100 (about 4-5 hours, every step resumes), `HF_TOKEN`, the SIIM-ACR `archive.zip` in
`MyDrive/medscope/siim/` (as for notebook 26). Optional `GEMINI_API_KEY` adds gemini-4-argon on the new SIIM test (about $2).
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code("!pip install -q kaggle pydicom"), code(LAMA_CELL), code(RESTORE_ALL),
        code(RESTORE_V4), code(RESTORE_EVAL),
        md("## 1. SIIM-ACR images, and the SIIM cases of notebook 26"),
        siim_data,
        code("FULL = f'{V4}/siim_full'\nif not os.path.exists(f'{FULL}/views/views_clean.jsonl'):\n" +
             "".join("    " + l for l in "".join(siim_full["source"]).splitlines(keepends=True)) +
             "\nSIIMFULL = f'{FULL}/views/views_clean.jsonl {FULL}/negatives/views_negatives_external.jsonl'"),
        md("""## 2. The open question of notebook 26b (GPU, about 5 minutes)

Asked "Is there an abnormality?", v4 said yes on 35 of the 42 pneumothorax images. Here the same question on the 48
SIIM images without pneumothorax: if v4 says yes about as often there, the "yes" carries no information."""),
        code(r"""
import json, torch
from dataclasses import replace
from medscope.eval.runner import load_views, scored_rows
BATCH = 24 if torch.cuda.get_device_properties(0).total_memory / 2 ** 30 >= 38 else 8
FINAL = json.load(open(f'{ADAPTERS}/final_choice_v4.json'))['adapter']
CTRL = f'{FULL}/probe_abnormality_healthy.jsonl'
with open(CTRL, 'w') as f:
    for v in load_views(f'{FULL}/negatives/views_negatives_external.jsonl'):
        f.write(json.dumps(replace(v, view_id=v.view_id.replace('__natural_negative', 'abn__natural_negative'),
                                   question='Is there an abnormality in this chest X-ray?').to_dict()) + '\n')
for run, adapter in [('v4_final', FINAL), ('v4q_cf_s0', f'{ADAPTERS}/v4_s1/final'), ('v2_base_qwen35', None)]:
    a = f'--adapter {adapter}' if adapter else ''
    !python scripts/evaluate.py --model Qwen/Qwen3.5-4B {a} --views {CTRL} --out {RESULTS}/{run}_siimabnneg --name {run}-siimabnneg --split siimabnneg --batch-size {BATCH}
said_yes = lambda run, kind: [r['action'] == 'answer' and not r.get('claims_absent') for r in scored_rows(f'{RESULTS}/{run}') if r['kind'] == kind] if os.path.exists(f'{RESULTS}/{run}') else []
lines = ['| Model | "Abnormal": pneumothorax images | "Abnormal": images without pneumothorax |', '| --- | --- | --- |']
for run in ('v4_final', 'v4q_cf_s0', 'v2_base_qwen35'):
    p, n = said_yes(f'{run}_siimabn', 'original'), said_yes(f'{run}_siimabnneg', 'natural_negative')
    lines.append(f'| {run} | {sum(p)}/{len(p)} | {sum(n)}/{len(n)} |')
CTRL_TABLE = '\n'.join(lines)
open(f'{RESULTS}/siim_abnormality_control.md', 'w').write(CTRL_TABLE + '\n')
print(CTRL_TABLE)
"""),
        md("## 3. SIIM training, validation and new test patients (none in any earlier evaluation)"),
        code(r"""
ST = f'{V4}/siim_train'
if not os.path.exists(f'{ST}/test/cases.jsonl'):
    !python scripts/prepare_siim_train.py --siim {SIIM} --exclude-views {EXT2} {SIIMFULL} --out {ST} --train 150 --val 50 --test 100
for split in ('train', 'val', 'test'):
    extra = '--v4-degradations' if split == 'train' else ''
    if not os.path.exists(f'{ST}/{split}/views/views_clean.jsonl'):
        !python scripts/build_views.py --manifest {ST}/{split}/cases.jsonl --out {ST}/{split}/views --inpainter lama {extra}
        !python scripts/check_views.py --views {ST}/{split}/views/views.jsonl
SIIM_TRAIN = f'{ST}/train/views/views_clean.jsonl {ST}/train/negatives.jsonl'
SIIM_VAL = f'{ST}/val/views/views_clean.jsonl {ST}/val/negatives.jsonl'
SIIM_TEST = f'{ST}/test/views/views_clean.jsonl {ST}/test/negatives.jsonl'
!cat {ST}/report.txt
"""),
        md("## 4. v4.1: stage 3 again, from the same stage 2, plus the SIIM training cases (GPU, about 1.5 hours)"),
        code(f"""
REPLAY = f'{{DRIVE}}/external/vqa_train/views_vqa_train.jsonl'
if not os.path.exists(f'{{ADAPTERS}}/v41_s3/final/adapter_config.json'):
    !python scripts/train_sft.py --model {BASE} --init {{ADAPTERS}}/v4_s2/final {s3} --extra-views {{SIIM_TRAIN}} --out {{ADAPTERS}}/v41_s3
V41 = f'{{ADAPTERS}}/v41_s3/final'
"""),
        md("""## 5. Validation and the rule fixed before any v4.1 test result

v4.1 passes if, on the v4 validation set, its net utility is at least v4's minus 0.02 and its rate of claimed findings
on healthy images at most v4's plus 0.02 (the pre-registered stage rule), and it detects more pneumothoraxes than v4
on the SIIM validation patients. It is tested either way; the paper reports whether it passed."""),
        code(f"""
!python scripts/evaluate.py --model {BASE} --adapter {{V41}} --views {{VAL_V4}} {{VAL_NEG_V4}} --out {{RESULTS}}/v41_val --name medscope-v4.1 --split validation --batch-size {{BATCH}}
for run, adapter in [('v41', V41), ('v4_final', FINAL)]:
    !python scripts/evaluate.py --model {BASE} --adapter {{adapter}} --views {{SIIM_VAL}} --out {{RESULTS}}/{{run}}_siimval --name {{run}}-siimval --split siimval --batch-size {{BATCH}}
m = lambda run, k: json.load(open(f'{{RESULTS}}/{{run}}/summary.json'))['metrics'][k]['value']
det = lambda run: (lambda p: sum(p) / max(1, len(p)))(said_yes(run, 'original'))
U41, U4, H41, H4 = m('v41_val', 'net_utility'), m('v4_s3_val', 'net_utility'), m('v41_val', 'natural_hallucination_rate'), m('v4_s3_val', 'natural_hallucination_rate')
passed = U41 >= U4 - 0.02 and H41 <= H4 + 0.02 and det('v41_siimval') > det('v4_final_siimval')
RULE = (f'validation net utility {{U41:.3f}} (v4 {{U4:.3f}}), healthy-image claims {{H41:.1%}} (v4 {{H4:.1%}}), '
        f'SIIM validation pneumothorax detected {{det("v41_siimval"):.0%}} (v4 {{det("v4_final_siimval"):.0%}}): '
        + ('PASSED' if passed else 'NOT PASSED'))
json.dump({{'adapter': V41, 'passed': passed, 'rule': RULE}}, open(f'{{ADAPTERS}}/v41_choice.json', 'w'), indent=1)
print(RULE)
"""),
        md("## 6. Every test (GPU, about 1.5 hours) and gemini-4-argon on the new SIIM patients (optional)"),
        code(f"""
SETS = {{'test': f'{{TEST_VIEWS}} {{TEST_NEG}}', 'ext': EXT_VIEWS, 'fresh': FRESH, 'ext2': EXT2, 'siimfull': SIIMFULL, 'siimte': SIIM_TEST}}
for split in {tests!r}:
    !python scripts/evaluate.py --model {BASE} --adapter {{V41}} --views {{SETS[split]}} --out {{RESULTS}}/v41_{{split}} --name medscope-v4.1 --split {{split}} --batch-size {{BATCH}}
!python scripts/evaluate.py --model {BASE} --adapter {{FINAL}} --views {{SIIM_TEST}} --out {{RESULTS}}/v4_final_siimte --name medscope-v4 --split siimte --batch-size {{BATCH}}
!python scripts/evaluate.py --model {BASE} --views {{SIIM_TEST}} --out {{RESULTS}}/v2_base_qwen35_siimte --name qwen3.5-4b --split siimte --batch-size {{BATCH}}
if secret('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = secret('GEMINI_API_KEY')
    !python scripts/evaluate.py --api gemini --model gemini-4-argon --views {{SIIM_TEST}} --out {{RESULTS}}/v2_gemini_siimte --name gemini-4-argon --split siimte --batch-size 8
!python scripts/evaluate.py --model {BASE} --adapter {{V41}} --views {{VQA_VIEWS}} --out {{RESULTS}}/v41_vqa --name medscope-v4.1 --split vqa --batch-size {{BATCH}}
lines = ['| Model | New SIIM patients: pneumothorax found | New SIIM patients: healthy called positive | Notebook 26 SIIM cases: found |',
         '| --- | --- | --- | --- |']
rate = lambda run, kind: (lambda p: f'{{sum(p)}}/{{len(p)}} ({{sum(p) / max(1, len(p)):.0%}})')(said_yes(run, kind))
for tag in ('v41', 'v4_final', 'v2_base_qwen35', 'v2_gemini'):
    lines.append(f'| {{tag}} | {{rate(tag + "_siimte", "original")}} | {{rate(tag + "_siimte", "natural_negative")}} | {{rate(tag + "_siimfull", "original")}} |')
PTX_TABLE = '\\n'.join(lines)
open(f'{{RESULTS}}/v41_pneumothorax.md', 'w').write(PTX_TABLE + '\\n')
print(PTX_TABLE)
"""),
        publish("MedScope report - 27 v4.1 pneumothorax fix", f"""
    ('Post hoc: what v4.1 is', 'Stage 3 of v4 redone from the same stage 2 with the same data, settings and seed, plus 150 SIIM pneumothorax images and 150 lesion-free SIIM images from patients in no earlier evaluation. v4 remains the pre-registered model.'),
    ('SIIM patients', read_text(f'{{ST}}/report.txt')),
    ('Does v4 call every chest X-ray abnormal? (open question of notebook 26b)', read_text(f'{{RESULTS}}/siim_abnormality_control.md')),
    ('Rule fixed before any v4.1 test result', RULE),
    ('Pneumothorax: new SIIM patients and the notebook 26 cases', read_text(f'{{RESULTS}}/v41_pneumothorax.md')),
    ('Main test: v4.1 vs v4 (paired)', significance_table(RESULTS, 'v41_test', ['v4_final_test'])),
    ('External centres: v4.1 vs v4 (paired)', significance_table(RESULTS, 'v41_ext', ['v4_final_ext'])),
    ('Fresh internal: v4.1 vs v4 (paired)', significance_table(RESULTS, 'v41_fresh', ['v4_final_fresh'])),
    ('Fresh external: v4.1 vs v4 (paired; its SIIM part shares the source with v4.1 training, not the patients)', significance_table(RESULTS, 'v41_ext2', ['v4_final_ext2'])),
    ('New SIIM patients: v4.1 vs v4 (paired)', significance_table(RESULTS, 'v41_siimte', ['v4_final_siimte', 'v2_base_qwen35_siimte'])),
    ('All metrics by source', by_dataset(RESULTS, ['v41_test', 'v4_final_test', 'v41_ext2', 'v4_final_ext2', 'v41_siimte', 'v4_final_siimte'])),
    ('Standard VQA: v4.1 vs v4', vqa_table(RESULTS, ['v41_vqa', 'v4_final_vqa'])),
"""),
    ]


def nb28_reader_study() -> list[dict]:
    """Reader study: build the blinded page from the main test set, publish it, and later score the answers."""
    return [
        md("""
# MedScope 28: reader study (physicians)

Two questions per image, answered by physician readers on a web page: has the image been digitally edited, and is the
finding there? The page mixes, in equal numbers (32 each, 128 in all) and from different cases: unmodified lesion
images, lesion-erased images (the LaMa erasures the models were tested on), control-edited images (the same shape
erased elsewhere with the same tool, lesion intact) and unmodified lesion-free images. Lesion-free images mean "no
lesion" is not a cue for "edited"; control-edited images let readers rate the control edit as well as the erasure.
The page holds no answer key; the key stays in Drive. This is pack 2 (the first pack had no control-edited images);
every answer file names its pack, and files from the first pack are not scored against this key.

**Before you start (once):**
1. On GitHub create an empty **public** repository named `medscope-reader` (no README).
2. Your Colab secret `GITHUB_TOKEN` needs write access to it (fine-grained token: *Contents: Read and write* on
   `medscope-reader`), with Notebook access switched on.
3. After section 1 has run: in `medscope-reader` -> Settings -> Pages, choose *Deploy from a branch*, branch `main`,
   folder `/ (root)`, Save. The page appears at `https://bhaskargurram-ai.github.io/medscope-reader/` within a minute.

**Runtime:** CPU is fine. Section 1 takes about 5 minutes and republishes the page (readers who had started the
first pack start again; their saved progress is kept apart). Run section 2 after the readers have sent their answer
files: put them (`reader_XX.json`) in `MyDrive/medscope/reader/answers/`.
"""),
        code(SETUP), code(RESTORE_ALL),
        md("## 1. Build the page and publish it"),
        code(r"""
RS = f'{DRIVE}/reader'
os.makedirs(f'{RS}/answers', exist_ok=True)
PACK = f'{WORK}/reader_pack2'
KEY = f'{RS}/key_v2.json'            # pack 2: four kinds; the first pack's key.json and site.tar stay as they are
if not os.path.exists(KEY):
    !python scripts/make_reader_study.py --views {TEST_VIEWS} --negatives {TEST_NEG} --out {PACK} --per-kind 32 --seed 0
    !cp {PACK}/key.json {KEY}
    !cd {PACK}/site && tar -cf {RS}/site_v2.tar .
elif not os.path.exists(f'{PACK}/site/index.html'):
    os.makedirs(f'{PACK}/site', exist_ok=True)
    !tar -C {PACK}/site -xf {RS}/site_v2.tar
    !cp reader/index.html {PACK}/site/index.html
tok = (secret('GITHUB_TOKEN') or '').strip()
if not tok:
    raise SystemExit('Add the Colab secret GITHUB_TOKEN (write access to medscope-reader), then rerun this cell.')
remote = f'https://x-access-token:{tok}@github.com/bhaskargurram-ai/medscope-reader.git'
r = subprocess.run(f'cd {PACK}/site && rm -rf .git && git init -q -b main && git add -A && '
                   'git -c user.name="Bhaskar Gurram" -c user.email="bhaskargurram.g123@gmail.com" commit -q -m "Reader study" && '
                   f'git push -q --force {remote} main', shell=True, capture_output=True, text=True)
print(r.stderr.replace(tok, '***') or 'published')
if r.returncode:
    raise SystemExit('Push failed: check that medscope-reader exists and the token can write to it.')
print('Readers open: https://bhaskargurram-ai.github.io/medscope-reader/  (after Pages is switched on, step 3 above)')
"""),
        md("## 2. Score the answers (after the readers have sent their files)"),
        code(r"""
import glob
answers = sorted(glob.glob(f'{RS}/answers/*.json'))
print(len(answers), 'answer file(s):', [os.path.basename(a) for a in answers])
if answers:
    !python scripts/make_reader_study.py --score --key {KEY} --answers {' '.join(answers)} --out {RESULTS}/reader_study.md
"""),
    ]


def nb29_review() -> list[dict]:
    """Three checks asked for by the independent review: a factorial ablation that separates the control edit from
    lesion insertion, a linear probe on the frozen vision encoder, and patient-level bootstrap intervals."""
    c = nb25_v4_recipe()
    ctrl = ("--views {TRAIN_V4_BASE} {V4}/train_tp/views.jsonl --negatives {TRAIN_NEG_V4} "
            "--kinds original target_removal random_removal natural_negative degraded --epochs 3 --max-steps {S1_STEPS} "
            "--schedule-steps {S1_TOTAL} --mode agentic --window-prob 0.3 --small-zoom --oversample-small 2 --paraphrase-prob 0.5")
    ins = ("--views {TRAIN_V4_BASE} {V4}/train_tp/views.jsonl {V4}/inserted/views.jsonl --negatives {TRAIN_NEG_V4} "
           "--kinds original target_removal natural_negative degraded --epochs 3 --max-steps {S1_STEPS} "
           "--schedule-steps {S1_TOTAL} --mode agentic --window-prob 0.3 --small-zoom --oversample-small 2 --paraphrase-prob 0.5")
    frontier = [r for r, _, _ in FRONTIER]
    return [
        md("""
# MedScope 29: review checks (factorial ablation, encoder probe, patient-level bootstrap)

Three analyses the independent review of the manuscript asked for. Nothing here changes the selected model or any
confirmatory number; every result goes into the paper's robustness and limitations sections.

| Part | What | Why | GPU time |
| --- | --- | --- | --- |
| 1 | Two more stage-1 arms, like-for-like with notebook 25: **control edits without insertions** and **insertions without control edits** | notebook 25's erasures-only arm removed both at once; this separates them (2 x 2 with the recipe and erasures-only arms) | about 6.5 h each, run at the same time on one A100 |
| 2 | **Linear probe on the frozen vision encoder**: can the features the adapter receives tell edited from unedited images? | the paper argued the frozen encoder limits edit detection; this measures it | about 15 min |
| 3 | **Patient-level bootstrap** of the paper's main comparisons | several images can come from one patient; the case-level intervals may be too narrow | CPU, about 20 min |

Open it on an **A100** runtime and choose **Run all**. Nothing to set. Every step resumes: a second run skips what is
done. The report is published to Drive at the end (`results/29_review_checks_report.md`).
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_ALL), code(RESTORE_V4), code(RESTORE_EVAL),
        c[7],                                   # S1_STEPS, test_all, BATCH
        md("## 1. Factorial ablation: the two missing arms, trained together on one GPU"),
        code(f"""
ARGS = {{'ctrl': f'{ctrl}', 'ins': f'{ins}'}}
import threading, subprocess, time, shutil, sys
def train_and_test(arm):
    name = f'v4q_{{arm}}_s0'
    out = f'{{ADAPTERS}}/{{name}}'
    if not os.path.exists(f'{{out}}/final/adapter_config.json'):
        a = ARGS[arm]
        !python scripts/train_sft.py --model {BASE} {{a}} --seed 0 --out {{out}}
    done = json.load(open(f'{{out}}/state.json'))['opt_step']
    if abs(done - S1_STEPS) > 0.02 * S1_STEPS:
        raise SystemExit(f'{{name}} took {{done}} steps, stage 1 took {{S1_STEPS}}: not like-for-like, stop and report this')
    test_all('{BASE}', f'{{out}}/final', name, heldout=True)
os.environ['OMP_NUM_THREADS'] = str(max(2, (os.cpu_count() or 8) // 2))
errors = []
def guarded(arm):
    try:
        train_and_test(arm)
    except BaseException as e:      # noqa: BLE001 - reported after both arms have finished
        errors.append(f'{{arm}}: {{str(e)[:300]}}')
threads = [threading.Thread(target=guarded, args=(arm,)) for arm in ('ctrl', 'ins')]
for t in threads:
    t.start()
for t in threads:
    t.join()
if errors:
    raise SystemExit(' | '.join(errors))
print('both arms trained and tested')
"""),
        md("## 2. Linear probe on the frozen vision encoder"),
        code(f"""
PROBE = f'{{RESULTS}}/encoder_probe'
if not os.path.exists(f'{{PROBE}}/probe.md'):
    REF = 'For comparison, a ResNet-18 fine-tuned on the same task separates random-removal from original views with test AUC 0.83 [0.80, 0.87] (paper, Section 5.4).'
    !python scripts/encoder_probe.py --model {BASE} --train {{TRAIN_V4_BASE}} --test {{TEST_VIEWS}} --out {{PROBE}} --per-kind 600 --reference '{{REF}}'
print(open(f'{{PROBE}}/probe.md').read())
"""),
        md("## 3. Patient-level bootstrap of the paper's comparisons (CPU)"),
        code(f"""
sets = [
    f"Main test, MedScope-4B vs nine frontier models=v4_final_test:{','.join(frontier)}:{{TEST_VIEWS}} {{TEST_NEG}}",
    f"Main test, recipe vs ablation arms=v4q_cf_s0_test:v4q_nocf_s0_test,v4q_nocfabs_s0_test,v4q_tgt_s0_test,v4q_ctrl_s0_test,v4q_ins_s0_test:{{TEST_VIEWS}} {{TEST_NEG}}",
    f"External centres, MedScope-4B vs flagships=v4_final_ext:v2_gpt6astra_ext,v2_claudeopus_ext,v2_gemini_ext:{{EXT_VIEWS}}",
    f"Fresh internal, MedScope-4B vs flagships=v4_final_fresh:v2_gpt6astra_fresh,v2_claudeopus_fresh,v2_gemini_fresh:{{FRESH}}",
    f"Fresh external, MedScope-4B vs flagships=v4_final_ext2:v2_gpt6astra_ext2,v2_claudeopus_ext2,v2_gemini_ext2:{{EXT2}}",
]
import shlex
!python scripts/cluster_bootstrap.py --results {{RESULTS}} {{' '.join('--set ' + shlex.quote(x) for x in sets)}} --out {{RESULTS}}/patient_bootstrap.md
"""),
        md("## 4. Summaries and report"),
        code(r"""
!python scripts/inpainter_summary.py --results {RESULTS} --inpainters telea transplant diffusion --model 'Recipe (control edits + insertions)=v4q_cf_s0_test' --model 'Control edits, no insertions=v4q_ctrl_s0_test' --model 'Insertions, no control edits=v4q_ins_s0_test' --model 'Erasures only=v4q_tgt_s0_test' --model 'Without CF=v4q_nocf_s0_test' --ref 'Recipe (control edits + insertions)' --training-tools lama transplant --out {RESULTS}/inpainters_factorial.md
"""),
        publish("MedScope report - 29 review checks", f"""
    ('Factorial ablation, main test: recipe vs each arm (paired)', significance_table(RESULTS, 'v4q_cf_s0_test', ['v4q_ctrl_s0_test', 'v4q_ins_s0_test', 'v4q_tgt_s0_test', 'v4q_nocf_s0_test'])),
    ('Factorial ablation, main test: control edits vs insertions (paired)', significance_table(RESULTS, 'v4q_ctrl_s0_test', ['v4q_ins_s0_test', 'v4q_tgt_s0_test'])),
    ('Factorial ablation, external centres: recipe vs each arm', significance_table(RESULTS, 'v4q_cf_s0_ext', ['v4q_ctrl_s0_ext', 'v4q_ins_s0_ext', 'v4q_tgt_s0_ext'])),
    ('Factorial ablation, fresh external: recipe vs each arm', significance_table(RESULTS, 'v4q_cf_s0_ext2', ['v4q_ctrl_s0_ext2', 'v4q_ins_s0_ext2', 'v4q_tgt_s0_ext2'])),
    ('Held-out inpainting tools, all five arms', read_text(f'{{RESULTS}}/inpainters_factorial.md')),
    ('Linear probe on the frozen vision encoder', read_text(f'{{RESULTS}}/encoder_probe/probe.md')),
    ('Patient-level bootstrap', read_text(f'{{RESULTS}}/patient_bootstrap.md')),
"""),
    ]


def nb30_audit() -> list[dict]:
    """One ZIP for an auditor without repository or Drive access: repository snapshot, git history, the reports and every
    evaluation run's metrics and rescored per-view outcomes (transcripts and adapters are left out)."""
    return [
        md("""
# MedScope 30: audit package

Builds one ZIP that lets a reviewer without access to GitHub or Drive trace every number in the paper:

- the repository at its current commit (code, notebooks, docs, paper source), plus `git log` and the full history of
  the pre-registration file (`git log -p`), with commit hashes and dates;
- the reports behind the tables: notebooks 23, 24, 25, 26, 26b, 27, 29 and the seed, inpainter, probe and
  patient-bootstrap summaries;
- every evaluation run under `results/`: `summary.json` (metrics with bootstrap CIs), `report.md`, `scored.jsonl`
  (one rescored row per view: action, correctness, reward, claims), `outcomes.jsonl` and `transcripts.jsonl` (every
  model reply, so answers can be re-parsed);
- the view manifests of every split (`views*.jsonl`, `negatives*.jsonl`: view ids, case ids, patient or near-copy
  group ids, questions, answers, lesion boxes; image paths but no images), so splits, patient mapping and the
  patient-level bootstrap can be rerun;
- the encoder probe's cached features (`features_*.npz`), so the probe can be refitted without a GPU.

Model adapters and images are left out (in Drive and the public datasets). The reader-study answer key is left out
while readers are blinded.

**Runtime:** CPU. About 10 minutes. The ZIP is written to `MyDrive/medscope/audit/`; download it from Drive and send
it to the reviewer with `docs/reviews/RESPONSE_v09.md`.
""" + SECRETS_NOTE),
        code(SETUP), code(RESTORE_ALL), code(RESTORE_V4), code(RESTORE_EVAL),
        code(r"""
import glob, zipfile, time
commit = git('rev-parse', '--short', 'HEAD', cwd='/content/medscope').stdout.strip()
AUD = f'{DRIVE}/audit'
os.makedirs(AUD, exist_ok=True)
zpath = f'{AUD}/medscope_audit_{commit}_{time.strftime("%Y%m%d")}.zip'
skip_dirs = ('.git', '__pycache__', '.ipynb_checkpoints')
n_runs = 0
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    # 1. repository snapshot and history
    for root, dirs, files in os.walk('/content/medscope'):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            full = os.path.join(root, f)
            z.write(full, 'repo/' + os.path.relpath(full, '/content/medscope'))
    z.writestr('history/git_log.txt', git('log', '--format=%H %ci %an %s', cwd='/content/medscope').stdout)
    z.writestr('history/preregistration_history.patch', git('log', '-p', '--format=commit %H%n%ci%n%s%n', '--',
                                                            'docs/PREREGISTRATION_v4.md', cwd='/content/medscope').stdout)
    z.writestr('history/HEAD.txt', commit + '\n')
    # 2. reports and summaries at the top of results/
    for f in sorted(glob.glob(f'{RESULTS}/*.md') + glob.glob(f'{RESULTS}/*.json') + glob.glob(f'{RESULTS}/*.txt')):
        z.write(f, 'results/' + os.path.basename(f))
    # 3. every run: metrics, report, rescored rows, raw outcomes
    for run in sorted(d for d in glob.glob(f'{RESULTS}/*') if os.path.isdir(d)):
        kept = [f for f in ('summary.json', 'report.md', 'scored.jsonl', 'outcomes.jsonl', 'transcripts.jsonl')
                if os.path.exists(f'{run}/{f}')]
        for f in kept:
            z.write(f'{run}/{f}', f'results/{os.path.basename(run)}/{f}')
        for sub in ('probe.md', 'probe.json', 'features_train.npz', 'features_test.npz'):   # the encoder probe folder
            if os.path.exists(f'{run}/{sub}'):
                z.write(f'{run}/{sub}', f'results/{os.path.basename(run)}/{sub}')
        n_runs += bool(kept)
    # 3b. view manifests of every split: ids, patient/group ids, questions, answers, boxes (image paths, no images)
    n_man = 0
    for f in sorted(set(glob.glob(f'{WORK}/**/views*.jsonl', recursive=True) + glob.glob(f'{WORK}/**/negatives*.jsonl', recursive=True)
                        + glob.glob(f'{WORK}/**/views_negatives*.jsonl', recursive=True) + glob.glob(f'{DRIVE}/slake/negatives/*.jsonl'))):
        z.write(f, 'manifests/' + os.path.relpath(f, '/content').replace('drive/MyDrive/medscope/', 'drive_'))
        n_man += 1
    for f in glob.glob(f'{DRIVE}/inpaint_test/*/views.jsonl'):
        z.write(f, 'manifests/inpaint_test/' + f.split('/')[-2] + '/views.jsonl')
        n_man += 1
    # 4. the reader-study key stays out (it would unblind the readers); say so
    z.writestr('README_AUDIT.txt', f'''MedScope audit package, repository commit {commit}.
repo/       the repository at this commit (code, notebooks, docs, paper/method_paper.tex and .pdf)
history/    git log of every commit; the full patch history of docs/PREREGISTRATION_v4.md
results/    every evaluation run: summary.json (metrics, 95% bootstrap CIs), report.md, scored.jsonl (one rescored
            row per view), outcomes.jsonl (raw), transcripts.jsonl (every model reply); the reports of notebooks
            23-29 at the top level; results/encoder_probe/features_*.npz = the probe's cached encoder features
manifests/  the view manifests of every split (view id, case id, patient or near-copy group id, kind, question,
            answer, lesion box, image path). Images are not included: they are the public datasets' own files.
Not included: model adapters (in Drive) and the reader-study answer key (would unblind readers).
Historical runs: the four neg_* runs (notebook 02b, October 2026) were summarised on an earlier 181-view version of
the natural-negative set; their outcomes.jsonl holds 218 rows from the later set. They are not used in the paper.
Run names: v4_final_* = the selected model; v2_<model>_<set> = comparators; v4q_<arm>_s<seed>_<set> = stage-1 arms;
v4mg_* = MedGemma arms; *_inp_<tool>_* = held-out inpainting tools. Sets: test (main), ext (external centres),
fresh (fresh internal), ext2 (fresh external), vqa, notools.
''')
print(f'{zpath}: {os.path.getsize(zpath) / 2**20:.0f} MB, {n_runs} runs, {n_man} manifests')
"""),
    ]


def nb26_local() -> list[dict]:
    """Notebook 26 for your own computer (one NVIDIA GPU, 12 GB or more), with Jupyter instead of Colab."""
    return [
        md("""
# MedScope 26 (local GPU): SIIM pneumothorax at original resolution (post-hoc analysis)

Notebook 26 for your own computer instead of Colab. Needs an NVIDIA GPU with 12 GB or more (RTX 4070 or better),
Linux or WSL2, Python 3.10+, about 15 GB free disk, and your medscope Google Drive folder on this computer (Google
Drive for desktop, or a downloaded copy). Run the cells in order; a rerun continues where it stopped. About 2-3 hours
on an RTX 4070 (the 256-pixel control on the same GPU included).

Kaggle key: `~/.kaggle/kaggle.json` (kaggle.com -> Settings -> API -> Create New Token), or set `KAGGLE_USERNAME`
and `KAGGLE_KEY` below. `GEMINI_API_KEY` (optional, about $2) adds gemini-4-argon, run over the API while the GPU works.
"""),
        code(r"""
import os
if os.path.basename(os.getcwd()) == 'notebooks':
    os.chdir('..')                                                # run from the repository folder
DRIVE = os.path.expanduser('~/GoogleDrive/My Drive/medscope')   # your medscope Drive folder (has v4/, adapters/, results/)
WORK = os.path.expanduser('~/medscope_work')                     # local scratch (about 15 GB)
# os.environ['KAGGLE_USERNAME'] = '...'; os.environ['KAGGLE_KEY'] = '...'
# os.environ['GEMINI_API_KEY'] = '...'
assert os.path.isdir(f'{DRIVE}/adapters') and os.path.exists(f'{DRIVE}/v4/v4.tar'), 'DRIVE must be the medscope folder'
"""),
        code(r"""
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-e', '.[train]', 'pydicom', 'kaggle', 'pyarrow',
                'huggingface_hub', 'flash-linear-attention'], check=True)
import torch
print(torch.__version__, torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA GPU')
"""),
        code(r"""
import subprocess, sys
p = subprocess.Popen([sys.executable, 'scripts/siim_fullres_local.py', '--drive', DRIVE, '--work', WORK],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
for line in p.stdout:
    print(line, end='')
assert p.wait() == 0, 'failed: see the output above; rerunning this cell continues where it stopped'
"""),
        code(r"""
print(open(f'{DRIVE}/results/26_siim_full_resolution_report.md').read())
"""),
    ]


NOTEBOOKS = {
    "00_sync_drive_to_hf.ipynb": nb00_sync,
    "01_build_slake_views.ipynb": nb01,
    "02_baselines.ipynb": nb02,
    "02b_natural_negatives.ipynb": nb02b,
    "03_sft.ipynb": nb03,
    "04_merge.ipynb": nb04,
    "05_rl_grpo.ipynb": nb05,
    "07_more_datasets.ipynb": nb07,
    "08_sft_v2.ipynb": nb08,
    "09_rejection_sampling.ipynb": nb09,
    "10_final_eval_export.ipynb": nb10,
    "11_generalization.ipynb": nb11_generalization,
    "12_frontier_models.ipynb": nb12_frontier,
    "13_paper_tables.ipynb": nb13_paper_tables,
    "14_ablation.ipynb": nb14_ablation,
    "15_sft_v3_replay.ipynb": nb15_sft_v3,
    "16_robustness.ipynb": nb16_robustness,
    "17_frontier_checks.ipynb": nb17_frontier_checks,
    "18_seeds.ipynb": nb18_seeds,
    "19_release.ipynb": nb19_release,
    "20_fairness.ipynb": nb20_fairness,
    "21_medgemma.ipynb": nb21_medgemma,
    "22_v4_data.ipynb": nb22_v4_data,
    "23_v4_train.ipynb": nb23_v4_train,
    "24_v4_everywhere.ipynb": nb24_v4_eval,
    "24c_frontier_only.ipynb": nb24c_frontier,
    "24r_report.ipynb": nb24r_report,
    "25_v4_recipe.ipynb": nb25_v4_recipe,
    "25a_parts_2_3.ipynb": nb25_part("2+3", "no CF with matched 'absent' answers, and erasures only (seed 0)"),
    "25b_parts_4_5.ipynb": nb25_part("4+5", "MedGemma 1.5 4B with and without counterfactual views"),
    "25c_parts_6_7.ipynb": nb25_part("6+7", "seed 1 with and without counterfactual views"),
    "25d_parts_8_9.ipynb": nb25_part("8+9", "seed 2 with and without counterfactual views"),
    "25e_parts_2_to_5.ipynb": nb25_part("2+3+4+5", "four jobs on one GPU: no CF with matched 'absent' answers, "
                                                   "erasures only, MedGemma with and without CF"),
    "25f_parts_6_to_9.ipynb": nb25_part("6+7+8+9", "four jobs on one GPU: seeds 1 and 2, with and without CF"),
    "25g_seeds.ipynb": nb25_part("6+9", "seed 1 with CF and seed 2 without CF, both at once (about 7 hours on an A100)"),
    "25h_ablations.ipynb": nb25_part("2,3", "no CF with matched 'absent' answers (resumes from its checkpoint, then its "
                                     "tests), then the held-out inpainting tests of the erasures-only arm (about 3.5 hours)"),
    "26_siim_fullres.ipynb": nb26_siim_fullres,
    "26L_siim_fullres_local.ipynb": nb26_local,
    "26b_pneumothorax_diagnosis.ipynb": nb26b_diagnosis,
    "27_v41_pneumothorax_fix.ipynb": nb27_v41,
    "28_reader_study.ipynb": nb28_reader_study,
    "29_review_checks.ipynb": nb29_review,
    "30_audit_package.ipynb": nb30_audit,
    "25r_report.ipynb": nb25_part("report", "the summaries, paired tests and report (CPU; run after 25g and 25h)"),
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
