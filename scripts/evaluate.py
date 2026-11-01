"""Evaluate a model (optionally with a LoRA adapter) on MedScope views.

Writes outcomes.jsonl, transcripts.jsonl, summary.json and report.md to --out.
Rerunning with the same --out resumes where it stopped.

Usage:
    python scripts/evaluate.py --model Qwen/Qwen3.5-4B --views views/test/views_clean.jsonl \
        --out results/qwen35_base_test --name qwen35-base --split test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views, select_cases  # noqa: E402
from medscope.rewards import load_config  # noqa: E402


def record_usage(policy, out: Path, views_run: int) -> None:
    """Add this call's measured token usage to usage.json (totals and one entry per call) and print it."""
    import json
    from medscope.api_policy import cost_usd
    p = out / "usage.json"
    total = json.loads(p.read_text()) if p.exists() else {}
    call = {**policy.usage, "views_run": views_run,
            "cost_usd": cost_usd(policy.model, policy.usage["input_tokens"], policy.usage["output_tokens"])}
    total.setdefault("calls", []).append(call)
    for k in ("requests", "input_tokens", "output_tokens", "errors", "views_run"):
        total[k] = sum(c.get(k, 0) for c in total["calls"])
    total["model"] = policy.model
    total["cost_usd"] = cost_usd(policy.model, total["input_tokens"], total["output_tokens"])
    p.write_text(json.dumps(total, indent=2))
    cost = "price unknown" if call["cost_usd"] is None else f"${call['cost_usd']:.2f}"
    print(f"API usage for {policy.model} in this call: {views_run} views, {call['requests']} requests, "
          f"{call['input_tokens']:,} input and {call['output_tokens']:,} output tokens, {cost}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--views", required=True, nargs="+", help="one or more views files, evaluated together")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=1536,
                    help="per turn; generous because some models (MedGemma 1.5) think before answering")
    ap.add_argument("--quant", choices=["auto", "4bit", "none"], default="auto",
                    help="auto: 4-bit only on GPUs under 20 GB (T4); 16-bit on L4/A100")
    ap.add_argument("--api", choices=["openai", "anthropic", "gemini"], default=None,
                    help="evaluate a model behind an API (key from OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY); "
                         "--model is its id")
    ap.add_argument("--batch-size", type=int, default=8,
                    help="episodes advanced together; each sees exactly what it would see alone")
    ap.add_argument("--prompt", choices=["agent", "plain", "cautious", "fewshot"], default="agent",
                    help="agent: the benchmark prompt (default); plain: a short native VQA prompt with no "
                         "action format (replies are read as plain prose); cautious: the agent prompt plus a "
                         "warning that the question may name an absent finding; fewshot: the cautious prompt "
                         "plus four solved training examples before each case (needs --fewshot)")
    ap.add_argument("--fewshot", nargs="+", default=None,
                    help="training views and natural-negative files to draw the few-shot examples from")
    ap.add_argument("--tool-budget", type=int, default=None,
                    help="override the tool budget (0 = tools switched off: calls are refused)")
    args = ap.parse_args()
    from medscope.agent.prompts import set_fewshot, set_prompt
    set_prompt(args.prompt)
    fewshot = None
    if args.prompt == "fewshot":
        if not args.fewshot:
            ap.error("--prompt fewshot needs --fewshot TRAIN_VIEWS... TRAIN_NEG...")
        from medscope.agent.fewshot import example_messages, pick_examples
        from medscope.data.schema import ViewKind
        pool = [v for f in args.fewshot for v in load_views(f)]
        examples = pick_examples([v for v in pool if v.kind is not ViewKind.NATURAL_NEGATIVE],
                                 [v for v in pool if v.kind is ViewKind.NATURAL_NEGATIVE])
        fewshot = [v.view_id for v in examples]
        set_fewshot(example_messages(examples), fewshot)
        print("few-shot examples:", ", ".join(f"{v.view_id} ({v.question} -> {v.kind.value})" for v in examples))

    views = select_cases([v for f in args.views for v in load_views(f)], args.limit_cases)
    if args.api:
        from medscope.api_policy import api_policy
        policy = api_policy(args.api, args.model)
        precision = "api"
    else:
        from medscope.train.hf_policy import HFPolicy
        policy = HFPolicy(args.model, adapter=args.adapter, load_in_4bit={"auto": None, "4bit": True, "none": False}[args.quant],
                          max_new_tokens=args.max_new_tokens)
        precision = "4bit" if policy.load_in_4bit else str(policy.dtype).replace("torch.", "")
    meta = {"name": args.name, "model": args.model, "adapter": args.adapter, "split": args.split,
            "views_file": " ".join(args.views), "precision": precision}
    cfg = load_config()
    if args.tool_budget is not None:
        cfg = {**cfg, "tools": {**cfg["tools"], "budget": args.tool_budget,
                                "max_turns": args.tool_budget + 2 if args.tool_budget == 0 else None}}
        meta["tool_budget"] = args.tool_budget
    if args.prompt == "plain":
        cfg = {**cfg, "tools": {**cfg["tools"], "max_turns": 1}}   # one reply, no tools offered
    meta["prompt"] = args.prompt
    if fewshot:
        meta["fewshot"] = fewshot
    summary = evaluate(policy, views, cfg, args.out, meta, batch_size=args.batch_size)
    if args.api:
        record_usage(policy, Path(args.out), summary["n_run"])
    print((Path(args.out) / "report.md").read_text()[:3000])
    print("net utility:", summary["metrics"]["net_utility"]["value"])


if __name__ == "__main__":
    main()
