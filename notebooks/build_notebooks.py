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
from medscope.colab import build_report, negatives_by_domain, publish_doc, read_text, train_log_summary
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

**Runtime:** L4, about 3-4 hours. For the export step, a High-RAM runtime is safer.
""" + SECRETS_NOTE),
        code(SETUP), code(GPU_STACK), code(RESTORE_VIEWS),
        code(f"""
# every model on the FULL test split with the same scoring rules: the paper's main table.
# Runs that finished earlier on a subset (e.g. the 40-case baseline pilot) carry over.
runs = [('medscope_grpo_v2_test', 'medscope-grpo', {BASE!r}, f'{{ADAPTERS}}/grpo_v2/final'),
        ('grpo_plain_test', 'grpo-plain', {BASE!r}, f'{{ADAPTERS}}/grpo/final'),
        ('medscope_merged_test', 'medscope-sft-merged', {BASE!r}, f'{{ADAPTERS}}/merged/best'),
        ('medscope_sft_agentic_test', 'medscope-sft-agentic', {BASE!r}, f'{{ADAPTERS}}/sft_agentic/final'),
        ('base_qwen35_test', 'base-qwen3.5-4b', {BASE!r}, None),
        ('base_medgemma15_test', 'base-medgemma-1.5-4b', {MEDGEMMA!r}, None)]
for out, name, model, adapter in runs:
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


NOTEBOOKS = {
    "01_build_slake_views.ipynb": nb01,
    "02_baselines.ipynb": nb02,
    "02b_natural_negatives.ipynb": nb02b,
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
