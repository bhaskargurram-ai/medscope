"""Merge the final LoRA adapter into the base model and save (optionally push) it.

Usage:
    python scripts/export_model.py --model Qwen/Qwen3.5-4B --adapter adapters/grpo/final \
        --out export/MedScope-4B [--push your-hf-username/MedScope-4B] [--summary results/final_test/summary.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CARD = """---
license: apache-2.0
base_model: {base}
tags: [medical, vision-language, agent, research-only]
---

# {name}

A research multimodal medical agent fine-tuned from `{base}`. It answers a question about a medical
image only when it can see the evidence; otherwise it zooms in, asks for clarification, or refers.

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
    base = cls.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="cpu", low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, args.adapter).merge_and_unload()
    processor = AutoProcessor.from_pretrained(args.model)
    out = Path(args.out)
    model.save_pretrained(out, safe_serialization=True)
    processor.save_pretrained(out)

    metrics = "(run notebook 06 to fill this in)"
    if args.summary:
        s = json.loads(Path(args.summary).read_text())["metrics"]
        metrics = "\n".join(["| Metric | Value |", "| --- | --- |"] +
                            [f"| {k} | {v['value']:.3f} |" for k, v in s.items() if v["value"] is not None])
    (out / "README.md").write_text(CARD.format(base=args.model, name=out.name, metrics=metrics))
    print(f"saved merged model to {out}")

    if args.push:
        model.push_to_hub(args.push, private=True)
        processor.push_to_hub(args.push, private=True)
        from huggingface_hub import upload_file
        upload_file(path_or_fileobj=str(out / "README.md"), path_in_repo="README.md", repo_id=args.push)
        print(f"pushed (private) to https://huggingface.co/{args.push}")


if __name__ == "__main__":
    main()
