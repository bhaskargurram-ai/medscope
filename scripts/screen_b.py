"""Screening stage B (docs/SCREENING.md): probes of new image evidence on a validation dev set, then the screen.

    python scripts/screen_b.py --views VAL... --negatives VAL_NEG... --dev-dir RESULTS/screen_b/dev \
        --probes RESULTS/screen_b/probes.jsonl --model Qwen/Qwen3.5-4B --adapter ADAPTERS/v4_s1/final \
        --second-model Qwen/Qwen2.5-VL-7B-Instruct --specialist ADAPTERS/specialist_v10 --out RESULTS/screen_b
    # --stage probe runs only the models (GPU); --stage screen only the policies (CPU)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--negatives", nargs="+", required=True)
    ap.add_argument("--cases", type=int, default=200)
    ap.add_argument("--negs", type=int, default=80)
    ap.add_argument("--dev-dir", required=True)
    ap.add_argument("--probes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", choices=["probe", "screen", "both"], default="both")
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--second-model", default="Qwen/Qwen2.5-VL-7B-Instruct")
    ap.add_argument("--specialist", default=None)
    ap.add_argument("--batch-size", type=int, default=12)
    args = ap.parse_args()
    from medscope.screen.probes import compute_probes, dev_views, read_probes
    views = [v for f in args.views for v in load_views(f)]
    negs = [v for f in args.negatives for v in load_views(f)]
    dev = dev_views(views, negs, args.cases, args.negs, args.dev_dir)
    kinds = {}
    for v in dev:
        k = v.kind.value + ("/telea" if v.meta.get("inpainter") == "telea" else "")
        kinds[k] = kinds.get(k, 0) + 1
    print(f"dev set: {len(dev)} views {kinds}")
    cfg = with_vocab(load_config(), views + negs)
    if args.stage in ("probe", "both"):
        from medscope.train.hf_policy import HFPolicy
        policy = HFPolicy(args.model, adapter=args.adapter, max_new_tokens=384)
        second = HFPolicy(args.second_model, max_new_tokens=384) if args.second_model else None
        spec = None
        if args.specialist:
            from medscope.mas.specialist import Specialist
            spec = Specialist(args.specialist)
        compute_probes(policy, second, spec, dev, cfg, args.probes, batch_size=args.batch_size)
    if args.stage in ("screen", "both"):
        from medscope.screen.stage_b import report_b, run_screen_b
        rows = run_screen_b(dev, read_probes(args.probes), cfg)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        ser = [{(k if isinstance(k, str) else "/".join(k)): v for k, v in r.items()} for r in rows]
        (out / "screen_b.json").write_text(json.dumps(ser, indent=1, default=float))
        md = report_b(rows)
        (out / "screen_b.md").write_text(md)
        print(md)


if __name__ == "__main__":
    main()
