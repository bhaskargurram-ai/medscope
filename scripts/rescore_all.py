"""Recompute every run's summary and report from its stored decisions and transcripts.

No model is loaded: answer matching, plain-prose replies, rewards and metrics are re-derived
under the current code, the same way for every model. Run after a scoring fix.

Usage:
    python scripts/rescore_all.py --results /content/drive/MyDrive/medscope/results [--pattern 'v2_*']
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import evaluate, load_views  # noqa: E402
from medscope.agent.prompts import set_fewshot, set_prompt  # noqa: E402
from medscope.rewards import load_config  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--pattern", default="v2_*")
    args = ap.parse_args()
    cfg = load_config()
    for s in sorted(Path(args.results).glob(f"{args.pattern}/summary.json")):
        meta = json.loads(s.read_text())["meta"]
        files = str(meta.get("views_file", "")).split()
        missing = [f for f in files if not Path(f).exists()]
        if not files or missing:
            print(f"skip {s.parent.name}: views not available ({missing or 'none recorded'})")
            continue
        views = [v for f in files for v in load_views(f)]
        set_prompt(meta.get("prompt", "agent"))   # results are keyed by the prompt they were run with
        set_fewshot([], meta.get("fewshot", []))  # and by the few-shot examples, if any (ids suffice)
        old = json.loads(s.read_text())["metrics"]["net_utility"]["value"]
        new = evaluate(None, views, cfg, s.parent, meta, log=lambda m: None)
        nu = new["metrics"]["net_utility"]["value"]
        print(f"{s.parent.name}: net utility {old:+.3f} -> {nu:+.3f}, "
              f"malformed {new['metrics']['malformed_rate']['value']:.3f}, plain prose {new['metrics']['free_text_rate']['value']:.3f}")


if __name__ == "__main__":
    main()
