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
from medscope.colab import build_report, by_dataset, negatives_by_domain, publish_doc, read_text, train_log_summary
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
    ('Training loss', train_log_summary(f'{ADAPTERS}/sft_v2/train_log.jsonl', window=200)),
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
    ('Fine-tuning loss', train_log_summary(f'{ADAPTERS}/rft_train/train_log.jsonl', window=50)),
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
        md("## Export the final model"),
        code("PUSH_TO = ''   # e.g. 'your-hf-username/MedScope-4B' to also upload (private)"),
        code(f"""
push = f'--push {{PUSH_TO}}' if PUSH_TO else ''
!python scripts/export_model.py --model {BASE} --adapter {{FINAL}} --out {{DRIVE}}/export/MedScope-4B --summary {{RESULTS}}/v2_medscope_test/summary.json {{push}}
"""),
        publish("MedScope report - 10 final", f"""
    ('Leaderboard (test)', compare_runs(RESULTS)),
    ('By imaging type', by_dataset(RESULTS, {all_runs!r})),
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
