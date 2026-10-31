"""Can a frontier model see the edits? Each view is shown alone and the model gives the probability
that the image was digitally edited (a region painted over / inpainted).

  random_removal vs original:   both show the lesion, only one is edited -> is the edit visible?
  target_removal vs original:   the lesion is erased in one -> edit, or lesion absence, visible?
  target_removal vs random_removal: both edited -> does erasing the lesion look different?

AUC near 0.5 means the model cannot tell. Complements the learned ResNet-18 test (scripts/edit_detector.py).

Usage:
    python scripts/edit_guess.py --api openai --model gpt-6.1-sol --views TEST_VIEWS... --out RESULTS/edit_guess_gpt
Reruns skip images already scored.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.schema import ViewKind  # noqa: E402
from medscope.data.views import load_image  # noqa: E402
from medscope.eval.runner import load_views, read_jsonl, select_cases  # noqa: E402

PROMPT = ("You are an expert in medical imaging and in image forensics. Some of the images you will see have "
          "been digitally edited: a region was painted over (inpainted) so that it blends with the surrounding "
          "tissue. Others are unedited.")
QUESTION = ("What is the probability, from 0 to 100, that this image has been digitally edited in this way? "
            "Reply with the number only.")
KINDS = (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL, ViewKind.TARGET_REMOVAL)


def parse_prob(text: str):
    m = re.search(r"\d+(?:\.\d+)?", text or "")
    return min(100.0, float(m.group())) / 100 if m else None


def auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    p, n = np.array(pos)[:, None], np.array(neg)[None, :]
    return float((p > n).mean() + 0.5 * (p == n).mean())


def auc_ci(pos, neg, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [auc(list(rng.choice(pos, len(pos))), list(rng.choice(neg, len(neg)))) for _ in range(n)]
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def report(recs: list[dict], model: str) -> str:
    by = defaultdict(list)
    for r in recs:
        if r["prob"] is not None:
            by[r["kind"]].append(r["prob"])
    lines = [f"Model: {model}. Probability that the image was edited, by view kind:", "",
             "| View kind | Images | Mean probability | Unparsed replies |", "| --- | --- | --- | --- |"]
    for k in KINDS:
        n_bad = sum(1 for r in recs if r["kind"] == k.value and r["prob"] is None)
        xs = by[k.value]
        lines.append(f"| {k.value} | {len(xs)} | {np.mean(xs):.3f} | {n_bad} |" if xs else f"| {k.value} | 0 | n/a | {n_bad} |")
    lines += ["", "| Comparison | What a high AUC would mean | AUC [95% CI] |", "| --- | --- | --- |"]
    for a, b, meaning in (("random_removal", "original", "the edit itself is visible"),
                          ("target_removal", "original", "edit or lesion absence is visible"),
                          ("target_removal", "random_removal", "erasing the lesion looks different from erasing elsewhere")):
        pos, neg = by[a], by[b]
        if pos and neg:
            lo, hi = auc_ci(pos, neg)
            lines.append(f"| {a} vs {b} | {meaning} | {auc(pos, neg):.3f} [{lo:.3f}, {hi:.3f}] |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", choices=["openai", "anthropic", "gemini"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from medscope.agent.prompts import image, text
    from medscope.api_policy import api_policy

    views = [v for f in args.views for v in load_views(f) if v.kind in KINDS]
    views = select_cases(views, args.limit_cases)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "scores.jsonl"
    done = {r["view_id"] for r in read_jsonl(path)}
    todo = [v for v in views if v.view_id not in done]
    print(f"{len(done)} images already scored, {len(todo)} to go")
    policy = api_policy(args.api, args.model)
    with open(path, "a") as f:
        for b in range(0, len(todo), 16):
            chunk = todo[b:b + 16]
            convs = [[{"role": "system", "content": [text(PROMPT)]},
                      {"role": "user", "content": [image(load_image(v.image_path)), text(QUESTION)]}] for v in chunk]
            for v, g in zip(chunk, policy.generate_batch(convs)):
                f.write(json.dumps({"view_id": v.view_id, "case_id": v.case_id, "kind": v.kind.value,
                                    "reply": g.text[:200], "prob": parse_prob(g.text)}) + "\n")
            f.flush()
            print(f"  {min(b + 16, len(todo))}/{len(todo)}", flush=True)
    md = report(read_jsonl(path), args.model)
    (out / "edit_guess.md").write_text(md + "\n")
    print(md)
    print(f"API usage: {policy.usage}")


if __name__ == "__main__":
    main()
