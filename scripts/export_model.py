"""Merge the final LoRA adapter into the base model and save (optionally push) it.

Usage:
    python scripts/export_model.py --model Qwen/Qwen3.5-4B --adapter adapters/sft_v2/final \
        --out export/MedScope-4B [--push your-hf-username/MedScope-4B] [--summary results/final_test/summary.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CARD = """---
{license_line}
base_model: {base}
tags: [medical, vision-language, agent, research-only]
---

# {name}

A research multimodal medical agent fine-tuned from `{base}`. It answers a question about a medical
image from what the image shows: it localises a finding that is there, says so when it is not, zooms in
when it needs a closer look, and asks for a better image when the one it has is unusable.

> **Research use only.** Not a medical device. Do not use for diagnosis or treatment.

## Output protocol
The model ends each turn with one tagged JSON object:
`<tool>{{"name": "zoom", "box": [x1, y1, x2, y2]}}</tool>` or
`<final>{{"action": "answer" | "clarify" | "refer", ...}}</final>`. Boxes are 0-1000 on the original image.

## MedScope-Bench results (test split)
{metrics}

Code, benchmark and training notebooks: https://github.com/bhaskargurram-ai/medscope
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--push", default=None, help="Hugging Face repo id to push to")
    ap.add_argument("--summary", default=None, help="summary.json to put in the model card")
    args = ap.parse_args()

    import torch
    import transformers
    from peft import PeftModel
    from transformers import AutoProcessor

    cls = getattr(transformers, "AutoModelForImageTextToText", None) or transformers.AutoModelForMultimodalLM
    # merged in 16-bit on the CPU; the adapter was trained on a 4-bit base, so re-evaluate the export
    base = cls.from_pretrained(args.model, dtype=torch.bfloat16, device_map="cpu")
    model = PeftModel.from_pretrained(base, args.adapter).merge_and_unload()
    processor = AutoProcessor.from_pretrained(args.model)
    out = Path(args.out)
    model.save_pretrained(out)
    processor.save_pretrained(out)

    metrics = "(run notebook 10 to fill this in)"
    if args.summary:
        s = json.loads(Path(args.summary).read_text())["metrics"]
        metrics = "\n".join(["| Metric | Value |", "| --- | --- |"] +
                            [f"| {k} | {v['value']:.3f} |" for k, v in s.items() if v["value"] is not None])
    if "gemma" in args.model.lower():  # MedGemma derivatives fall under Google's HAI-DEF terms
        license_line = "license: other\nlicense_name: health-ai-developer-foundations"
    else:
        license_line = "license: apache-2.0"
    (out / "README.md").write_text(CARD.format(license_line=license_line, base=args.model, name=out.name,
                                               metrics=metrics))
    print(f"saved merged model to {out}")

    if args.push:
        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(args.push, private=True, exist_ok=True)
        api.upload_folder(folder_path=str(out), repo_id=args.push)
        print(f"uploaded (private) to https://huggingface.co/{args.push}")


if __name__ == "__main__":
    main()
