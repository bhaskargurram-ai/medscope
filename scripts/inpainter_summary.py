"""Held-out inpainters: does evidence sensitivity survive erasures made by a tool the model never saw?

For each model, its LaMa run (the main test) and its runs on the same cases with the edited views
remade by other inpainters (scripts/reinpaint_views.py; run names <prefix>_inp_<inpainter>_<rest>). Only the
two edited views count: ESG, erased-lesion claims and denials after an edit elsewhere, on the cases
every compared run has.

    python scripts/inpainter_summary.py --results RESULTS --inpainters telea transplant diffusion \
        --model "MedScope-4B=v2_medscope3_test" --model "gpt-6-astra=v2_gpt6astra_test" ... \
        --ref MedScope-4B --out RESULTS/inpainters.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402

EDITED = ("target_removal", "random_removal")
SHOW = [("esg", "ESG"), ("target_hallucination_rate", "Erased-lesion claims"),
        ("random_denial_rate", "Denies after edit elsewhere")]


def run_name(base: str, inpainter: str) -> str:
    """v2_medscope3_test -> v2_inp_telea_medscope3_test; v4_final_test -> v4_inp_telea_final_test."""
    if inpainter == "lama":
        return base
    head, rest = base.split("_", 1)
    return f"{head}_inp_{inpainter}_{rest}"


def edited(outs):
    return [o for o in outs if o.kind in EDITED]


def fmt_p(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--inpainters", nargs="+", required=True)
    ap.add_argument("--model", action="append", required=True, help='"label=LaMa run name"')
    ap.add_argument("--ref", required=True, help="label of the model compared with every other one")
    ap.add_argument("--training-tools", nargs="+", default=["lama"], help="inpainting tools the reference model trained on")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = Path(args.results)
    tools = ["lama"] + [t for t in args.inpainters if t != "lama"]
    models = [tuple(m.split("=", 1)) for m in args.model]

    outs: dict[tuple[str, str], list] = {}
    for label, base in models:
        for t in tools:
            p = res / run_name(base, t)
            if (p / "outcomes.jsonl").exists():
                outs[(label, t)] = edited(load_outcomes(p))
    present = [t for t in tools if t == "lama" or any((m, t) in outs for m, _ in models)]
    # same cases everywhere: those every available run covers
    cases = set.intersection(*[{o.case_id for o in v} for v in outs.values()]) if outs else set()
    outs = {k: [o for o in v if o.case_id in cases] for k, v in outs.items()}

    seen = ", ".join(args.training_tools)
    lines = [f"Edited views only, on the {len(cases)} cases every run covers. Tools used in training: {seen}; "
             "every other tool was never seen in training.", "",
             "| Model | " + " | ".join(f"{n}: " + " / ".join(present) for _, n in SHOW) + " |",
             "| --- | " + " | ".join("---" for _ in SHOW) + " |"]
    for label, _ in models:
        cells = []
        for m, _ in SHOW:
            vals = [outs.get((label, t)) for t in present]
            cells.append(" / ".join("n/a" if v is None else f"{METRICS[m](v):.3f}" for v in vals))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines += ["", "Change with each held-out tool, same model and cases (held-out minus LaMa, paired bootstrap):", "",
              "| Model | Tool | " + " | ".join(n for _, n in SHOW) + " |",
              "| --- | --- | " + " | ".join("---" for _ in SHOW) + " |"]
    for label, _ in models:
        for t in present[1:]:
            if (label, t) in outs and (label, "lama") in outs:
                cells = []
                for m, _ in SHOW:
                    d = paired_bootstrap(outs[(label, t)], outs[(label, "lama")], m)
                    cells.append(f"{d['diff']:+.3f} (p {fmt_p(d['p'])})" if "diff" in d else "n/a")
                lines.append(f"| {label} | {t} | " + " | ".join(cells) + " |")

    lines += ["", f"{args.ref} minus each other model, per tool (paired bootstrap):", "",
              "| Other | Tool | " + " | ".join(n for _, n in SHOW) + " |",
              "| --- | --- | " + " | ".join("---" for _ in SHOW) + " |"]
    for label, _ in models:
        if label == args.ref:
            continue
        for t in present:
            if (label, t) in outs and (args.ref, t) in outs:
                cells = []
                for m, _ in SHOW:
                    d = paired_bootstrap(outs[(args.ref, t)], outs[(label, t)], m)
                    cells.append(f"{d['diff']:+.3f} (p {fmt_p(d['p'])})" if "diff" in d else "n/a")
                lines.append(f"| {label} | {t} | " + " | ".join(cells) + " |")
    md = "\n".join(lines)
    Path(args.out).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
