"""Why does a model miss one finding? A post-hoc diagnosis that trains nothing and changes no result.

Three questions, each answered from stored data:
1. What did each training stage teach about questions naming the finding? The exact training list of every stage is
   rebuilt with train_sft.py's own code (same arguments, same seeds) and its targets are counted: "Yes" (lesion
   image, edit elsewhere), "No" (lesion erased, healthy image) or "ask to clarify" (degraded image).
2. Did the stages lose the finding on the in-domain data too? Detection per asked finding, from stored outcomes.
3. Are the missed lesions unlike the training lesions? Lesion size (share of the image) of the finding in training
   and in the test cases, and detection by size.

    python scripts/diagnose_finding.py --finding pneumothorax \
        --stage "Stage 1" "<train_sft.py arguments>" --stage "Stage 2" "..." --stage "Stage 3" "..." \
        --views VALIDATION_VIEWS... --run "Stage 1=results/v4_s1_val" --run "Stage 3=results/v4_s3_val" \
        --probe-views SIIM_VIEWS... --probe-run "Stage 1=results/v4q_cf_s0_siimfull" ... --out report.md
"""

from __future__ import annotations

import argparse
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from medscope.actions import asked_finding  # noqa: E402
from medscope.eval.runner import load_views, scored_rows  # noqa: E402
from medscope.train.sft import lesion_fraction  # noqa: E402

TARGET = {"original": "Yes", "random_removal": "Yes", "target_removal": "No", "natural_negative": "No",
          "degraded": "clarify"}


def finding_of(question: str | None, finding: str) -> str:
    """'finding' when the question names it, 'abnormality' for 'Is there an abnormality ...', else 'other finding'."""
    asked = (asked_finding(question) or "").lower()
    if finding in asked or finding in (question or "").lower():
        return finding
    if "abnormal" in asked or "abnormal" in (question or "").lower():
        return "abnormality"
    return "other finding"


def is_chest_xray(v) -> bool:
    q = (v.question or "").lower()
    return v.case_id.startswith(("chestxdet", "siim")) or "x-ray" in q or "xray" in q or "radiograph" in q


def pct(a: int, n: int) -> str:
    return f"{a}/{n} ({a / n:.0%})" if n else "-"


def stage_targets(name: str, argstr: str, finding: str) -> tuple[list[str], list[float]]:
    import train_sft
    args = train_sft.parser().parse_args(shlex.split(argstr) + ["--model", "x", "--out", "x"]
                                         + ([] if "--mode" in argstr else ["--mode", "agentic"]))
    views, _, _ = train_sft.training_views(args)
    counts: dict[str, Counter] = defaultdict(Counter)
    sizes = []
    for v in views:
        group = finding_of(v.question, finding)
        if group != finding and not is_chest_xray(v):      # every question naming the finding, any source
            continue
        counts[group][TARGET.get(v.kind.value, "other")] += 1
        if group == finding and v.kind.value == "original" and lesion_fraction(v) is not None:
            sizes.append(lesion_fraction(v))
    rows = []
    for group in (finding, "abnormality", "other finding"):
        c = counts[group]
        n = sum(c.values())
        rows.append(f"| {name} | {group} | {n} | {pct(c['Yes'], n)} | {pct(c['No'], n)} | {pct(c['clarify'], n)} |")
    return rows, sizes


def detection(runs: list[tuple[str, str]], views_files: list[str], finding: str) -> list[str]:
    views = {v.view_id: v for f in views_files for v in load_views(f)}
    rows = []
    for name, run_dir in runs:
        stats: dict[str, Counter] = defaultdict(Counter)
        for r in scored_rows(run_dir):
            v = views.get(r["view_id"])
            if v is None or not (is_chest_xray(v) or finding_of(v.question, finding) == finding):
                continue
            g = finding_of(v.question, finding)
            said_yes = r["action"] == "answer" and not r.get("claims_absent")
            stats[g][r["kind"] + ("_yes" if said_yes else "_no")] += 1
        for g in (finding, "abnormality", "other finding"):
            s = stats[g]
            o = s["original_yes"] + s["original_no"]
            e = s["target_removal_yes"] + s["target_removal_no"]
            h = s["natural_negative_yes"] + s["natural_negative_no"]
            rows.append(f"| {name} | {g} | {pct(s['original_yes'], o)} | {pct(s['target_removal_yes'], e)} | "
                        f"{pct(s['natural_negative_yes'], h)} |")
    return rows


def size_bins(sizes: list[float]) -> str:
    if not sizes:
        return "-"
    import numpy as np
    q = np.percentile(sizes, [25, 50, 75])
    return f"n={len(sizes)}, median {q[1]:.1%} (IQR {q[0]:.1%}-{q[2]:.1%}), over 20%: {sum(s > 0.2 for s in sizes)}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--finding", required=True)
    ap.add_argument("--stage", nargs=2, action="append", default=[], metavar=("NAME", "TRAIN_SFT_ARGS"))
    ap.add_argument("--views", nargs="*", default=[], help="views files of the in-domain runs")
    ap.add_argument("--run", action="append", default=[], help="NAME=RUN_DIR, in-domain")
    ap.add_argument("--probe-views", nargs="*", default=[], help="views files of the test cases that were missed")
    ap.add_argument("--probe-run", action="append", default=[], help="NAME=RUN_DIR on the probe views")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    f = args.finding
    out = [f"# Why is {f} missed? (post-hoc diagnosis, nothing trained)", ""]

    train_sizes: list[float] = []
    if args.stage:
        out += ["## 1. What each training stage teaches", "",
                f"Training views of each stage (its exact training list): every question naming {f}, and the other chest X-ray questions, "
                "and the answer the stage is trained to give.", "",
                "| Stage | Question asks about | Views | Target Yes | Target No | Target: ask to clarify |",
                "| --- | --- | --- | --- | --- | --- |"]
        for name, argstr in args.stage:
            try:
                rows, sizes = stage_targets(name, argstr, f)
            except (OSError, KeyError, SystemExit) as e:      # e.g. a training file no longer on Drive
                rows, sizes = [f"| {name} | (training list not rebuilt: {e}) | | | | |"], []
            out += rows
            train_sizes = train_sizes or sizes
        out.append("")

    if args.run:
        out += ["## 2. In-domain detection by stage", "",
                "Share answered 'present': lesion images (higher is better), lesion erased and healthy images "
                "(lower is better).", "",
                "| Model | Question asks about | Lesion images: present | Lesion erased: present | Healthy: present |",
                "| --- | --- | --- | --- | --- |"]
        out += detection([tuple(r.split("=", 1)) for r in args.run], args.views, f) + [""]

    if args.probe_views:
        probe = {v.view_id: v for p in args.probe_views for v in load_views(p)}
        sizes = {vid: lesion_fraction(v) for vid, v in probe.items() if v.kind.value == "original"}
        out += ["## 3. Lesion size: training vs the missed test cases", "",
                f"- {f} lesion images in training (stage 1 list): {size_bins(train_sizes)}",
                f"- test cases: {size_bins([s for s in sizes.values() if s is not None])}", ""]
        if args.probe_run:
            import numpy as np
            edges = list(np.percentile([s for s in sizes.values() if s is not None], [33, 67]))
            label = lambda s: "small" if s < edges[0] else ("medium" if s < edges[1] else "large")  # noqa: E731
            out += [f"Detection by lesion size (thirds: under {edges[0]:.1%}, {edges[0]:.1%}-{edges[1]:.1%}, "
                    f"over {edges[1]:.1%}):", "", "| Model | Question | small | medium | large | all |",
                    "| --- | --- | --- | --- | --- | --- |"]
            for spec in args.probe_run:
                name, run_dir = spec.split("=", 1)
                by: dict[tuple[str, str], list[int]] = defaultdict(list)
                for r in scored_rows(run_dir):
                    v = probe.get(r["view_id"])
                    if v is None or r["kind"] != "original" or sizes.get(r["view_id"]) is None:
                        continue
                    yes = int(r["action"] == "answer" and not r.get("claims_absent"))
                    q = finding_of(v.question, f)
                    by[(q, label(sizes[r["view_id"]]))].append(yes)
                    by[(q, "all")].append(yes)
                for q in sorted({k[0] for k in by}):
                    cells = [pct(sum(by[(q, b)]), len(by[(q, b)])) for b in ("small", "medium", "large", "all")]
                    out.append(f"| {name} | {q} | " + " | ".join(cells) + " |")
            out.append("")
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
