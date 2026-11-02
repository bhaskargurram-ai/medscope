"""Prepare (and optionally upload) the MedScope release on Hugging Face.

  <user>/MedScope-4B      LoRA adapter of the final model (stage 3, with general-VQA replay)
  <user>/MedScope-4B-R    LoRA adapter of the verification checkpoint (stage 2, rejection sampling)
  <user>/MedScope-Bench   benchmark manifests (views without images: the images are rebuilt from the public
                          sources with the repository's scripts, since the source licences differ), and every
                          evaluation run: summary, judged outcomes and transcripts

Repositories are created private; make them public when the paper is submitted.

Usage:
    python scripts/release_hf.py --final ADAPTERS/sft_v3/final --verify ADAPTERS/rft_train/final \
        --results RESULTS --views TEST_VIEWS... --external EXT_VIEWS... --out release [--upload]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.agent.prompts import SYSTEM_PROMPT  # noqa: E402

BASE = "Qwen/Qwen3.5-4B"
GITHUB = "https://github.com/bhaskargurram-ai/medscope"
SHOW = [("ccr", "Correct on real lesions (CCR)"), ("esg", "Evidence sensitivity gap (ESG)"),
        ("target_hallucination_rate", "Claims an erased lesion"), ("natural_hallucination_rate", "Claims a finding on a healthy image"),
        ("grounded_accuracy", "Grounded accuracy (IoU >= 0.3)"), ("clarify_rate_degraded", "Asks to clarify on degraded input"),
        ("net_utility", "Net utility")]

MODEL_CARD = """---
license: apache-2.0
base_model: {base}
library_name: peft
tags: [medical, vision-language, agent, hallucination, research-only]
---

# {name}

{blurb}

> **Research use only.** Not a medical device. Do not use for diagnosis or treatment.

MedScope is a 4B multimodal medical agent trained to report a finding only when the image shows it. It was trained
on counterfactual views built automatically from public segmentation datasets: the lesion erased by inpainting, a
matched edit of the same shape elsewhere, degraded copies, and unedited lesion-free images. No human annotation was used.

## Results (MedScope-Bench, 507 internal test cases / 169 external cases)

| Metric | Internal test | External centres |
| --- | --- | --- |
{rows}

Nine frontier models (OpenAI, Anthropic, Google) evaluated through the same agent loop claim an erased lesion in 41-62%
of cases on the internal test. Full tables, code and notebooks: {github}

## Usage

This repository holds a LoRA adapter for `{base}` (vision encoder frozen during training).

```python
import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

base = AutoModelForImageTextToText.from_pretrained("{base}", dtype=torch.bfloat16, device_map="auto")
model = PeftModel.from_pretrained(base, "{repo}")
processor = AutoProcessor.from_pretrained("{base}")
```

Use the system prompt in `system_prompt.txt`. Each turn the model writes one tagged action:
`<tool>{{"name": "zoom", "box": [x1, y1, x2, y2]}}</tool>`, `<tool>{{"name": "window", "center": c, "width": w}}</tool>` or
`<final>{{"action": "answer" | "clarify" | "refer", ...}}</final>`, with boxes in 0-1000 coordinates of the original image.
The agent loop (tools, parsing, scoring) is in the GitHub repository (`medscope/agent/episode.py`).

## Limitations

Evaluated on public datasets with their labels as the reference standard; no clinician review. Weakest on very small
lesions, diffuse findings (e.g. COVID-19 opacities) and SLAKE CT/MRI. 2D images only.
"""

BENCH_CARD = """---
license: other
tags: [medical, benchmark, hallucination, vision-language]
---

# MedScope-Bench

Counterfactual evidence views for testing whether a medical vision-language model reports only what the image shows.
For every image with an expert lesion mask: the original, the lesion erased by LaMa inpainting, a matched edit of the
same shape elsewhere (control), and a degraded copy; plus unedited lesion-free images from the same sources.
Headline metric: the evidence sensitivity gap (ESG), zero for any model that always says yes, always says no, always
abstains or reacts to edits.

## Contents

- `manifests/`: the internal test, external test, fresh internal and fresh external test views, and the main-test
  edits remade with held-out inpainting tools (Telea, tissue transplant, Stable Diffusion) (question, expected answer, lesion box, view kind, source
  case id). **Images are not redistributed**: the source datasets have different licences. Rebuild them with
  `scripts/prepare_data.py`, `scripts/prepare_extra.py`, `scripts/prepare_external.py` and `scripts/build_views.py` from {github}.
- `runs/<run>/`: for every model evaluated (MedScope checkpoints, ablations, 6 open and 9 frontier models, robustness
  variants): `summary.json` (metrics with 95% bootstrap CIs), `scored.jsonl` (judged decision per view) and
  `transcripts.jsonl` (every turn). Every number in the paper can be recomputed from these files.
- `reports/`: the published report tables.

Sources: SLAKE, Kvasir-SEG, HyperKvasir, ChestX-Det, BUSI, TCGA-LGG (internal); CVC-ClinicDB, QaTa-COV19, BUS-BRA,
BraTS-Africa 2023 (external); ETIS-LaribPolypDB, BUS-UCLM, BraTS 2023 meningioma, SIIM-ACR pneumothorax (fresh
external). Cite the original datasets when using these views.
"""


def card_rows(results: Path, test_run: str, ext_run: str) -> str:
    def load(run):
        p = results / run / "summary.json"
        return json.loads(p.read_text())["metrics"] if p.exists() else {}
    t, e = load(test_run), load(ext_run)

    def fmt(m, k):
        if k not in m or m[k]["value"] is None:
            return "n/a"
        v = m[k]["value"]
        return f"{v:.1%}" if "rate" in k else f"{v:.3f}"
    return "\n".join(f"| {label} | {fmt(t, k)} | {fmt(e, k)} |" for k, label in SHOW)


def build_model(out: Path, adapter: Path, repo: str, name: str, blurb: str, results: Path, test_run: str, ext_run: str):
    out.mkdir(parents=True, exist_ok=True)
    for f in adapter.iterdir():
        if f.is_file() and (f.suffix in (".json", ".safetensors", ".bin", ".model") or f.name.startswith("adapter")):
            shutil.copy2(f, out / f.name)
    (out / "system_prompt.txt").write_text(SYSTEM_PROMPT + "\n")
    (out / "README.md").write_text(MODEL_CARD.format(base=BASE, name=name, blurb=blurb, repo=repo, github=GITHUB,
                                                     rows=card_rows(results, test_run, ext_run)))


def build_bench(out: Path, results: Path, views: list[str], external: list[str], more: dict | None = None):
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    for split, files in (("test", views), ("external", external), *(more or {}).items()):
        rows = []
        for f in files:
            for line in Path(f).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    r["image_path"] = Path(r["image_path"]).name    # local paths are not meaningful elsewhere
                    r["meta"] = {k: v for k, v in (r.get("meta") or {}).items() if not str(v).startswith("/")}
                    rows.append(r)
        (out / "manifests" / f"{split}_views.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    n_runs = 0
    for run in sorted([*results.glob("v2_*"), *results.glob("v4*")]):
        if not (run / "summary.json").exists():
            continue
        dst = out / "runs" / run.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("summary.json", "scored.jsonl", "transcripts.jsonl", "usage.json", "report.md"):
            if (run / f).exists():
                shutil.copy2(run / f, dst / f)
        n_runs += 1
    (out / "reports").mkdir(exist_ok=True)
    for f in results.glob("*.md"):
        if f.exists():
            shutil.copy2(f, out / "reports" / f.name)
    (out / "README.md").write_text(BENCH_CARD.format(github=GITHUB))
    return n_runs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final", required=True, help="adapter folder of the final model (stage 3)")
    ap.add_argument("--verify", default=None, help="adapter folder of the verification checkpoint (stage 2); optional")
    ap.add_argument("--final-runs", nargs=2, default=["v2_medscope3_test", "v2_medscope3_ext"], metavar=("TEST", "EXT"),
                    help="result runs whose numbers go into the final model's card")
    ap.add_argument("--final-blurb", default="Final model: counterfactual SFT, rejection-sampling fine-tuning and "
                                             "general medical VQA replay.")
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--external", nargs="+", required=True)
    ap.add_argument("--more", action="append", default=[], metavar="NAME=FILE[,FILE]",
                    help="further test manifests, e.g. fresh_internal=a.jsonl,b.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--user", default=None, help="Hugging Face user or organisation (default: the token's owner)")
    ap.add_argument("--upload", action="store_true", help="create the private repositories and upload")
    args = ap.parse_args()

    results, out = Path(args.results), Path(args.out)
    user = args.user
    if args.upload and not user:
        from huggingface_hub import HfApi
        user = HfApi().whoami()["name"]
    user = user or "your-username"
    repos = {"final": f"{user}/MedScope-4B", "verify": f"{user}/MedScope-4B-R", "bench": f"{user}/MedScope-Bench"}

    build_model(out / "MedScope-4B", Path(args.final), repos["final"], "MedScope-4B", args.final_blurb,
                results, *args.final_runs)
    if args.verify:
        build_model(out / "MedScope-4B-R", Path(args.verify), repos["verify"], "MedScope-4B-R",
                    "Verification checkpoint (before VQA replay): fewer false findings on healthy images, weaker on "
                    "open general questions. Use MedScope-4B for general medical VQA.",
                    results, "v2_medscope_test", "v2_medscope_ext")
    more = {k: v.split(",") for k, _, v in (m.partition("=") for m in args.more)}
    n = build_bench(out / "MedScope-Bench", results, args.views, args.external, more)
    print(f"prepared {out}: adapters, benchmark manifests and {n} evaluation runs")

    if args.upload:
        from huggingface_hub import HfApi
        api = HfApi()
        parts = [("final", "MedScope-4B", "model")] + ([("verify", "MedScope-4B-R", "model")] if args.verify else []) \
            + [("bench", "MedScope-Bench", "dataset")]
        for key, folder, kind in parts:
            api.create_repo(repos[key], repo_type=kind, private=True, exist_ok=True)
            api.upload_folder(folder_path=str(out / folder), repo_id=repos[key], repo_type=kind)
            print(f"uploaded (private): https://huggingface.co/{'datasets/' if kind == 'dataset' else ''}{repos[key]}")


if __name__ == "__main__":
    main()
