"""What does reader adjudication change? Rescoring on reader-verified cases.

The reader study (scripts/make_reader_study.py) has physicians say, for every image in the pack, whether the asked
finding is visible (yes / no / cannot tell) and whether the image looks edited. This script turns those answers into
an adjudication of the benchmark's synthetic labels and shows what it changes:

1. For every lesion-erased image in the pack: confirmed (no reader sees the finding), disputed (a majority of
   readers see it) or indeterminate (any "cannot tell", or a split), by imaging source. Control-edited images are
   adjudicated the same way for the opposite claim (the finding should remain visible).
2. Every model comparison recomputed on the pack's cases three ways: all pack cases, reader-confirmed cases only,
   and confirmed plus indeterminate (the two plausible assignments of indeterminate cases), so a reader can see
   whether the conclusions depend on the labels the readers doubted.
3. Sensitivity on unedited lesion images, by asked finding, next to the erased-lesion claim rate for the same
   finding, for every run: separates "misses the finding" from "claims it after erasure".

    python scripts/adjudicate.py --key PACK/key.json --answers ANSWERS/*.json --results RESULTS \\
        --views TEST_VIEWS... --ref v4_final_test --runs v2_gpt6astra_test v2_claudeopus_test ... --out adjudication.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from medscope.actions import asked_finding  # noqa: E402
from medscope.eval.compare import load_outcomes, paired_bootstrap  # noqa: E402
from medscope.eval.runner import load_views  # noqa: E402

METRICS = ("esg", "target_hallucination_rate", "net_utility", "ccr")
LABEL = {"esg": "ESG", "target_hallucination_rate": "Erased-lesion claims", "net_utility": "Net utility", "ccr": "CCR"}


def load_key(path: str) -> tuple[str | None, dict]:
    raw = json.loads(Path(path).read_text())
    if isinstance(raw, list):
        return None, {k["id"]: k for k in raw}
    return raw.get("pack"), {k["id"]: k for k in raw["items"]}


def load_packs(key_paths, answer_paths):
    from make_reader_study import load_packs as _lp            # same merging rules as the scoring script
    return _lp(key_paths, answer_paths)


def adjudicate(key: dict, readers: list[dict]) -> dict[str, dict]:
    """item id -> {'status': confirmed | disputed | indeterminate, 'yes': n, 'no': n, 'unsure': n}.
    Erased images are confirmed when no reader sees the finding; control-edited and original images when every
    reader does; lesion-free images when no reader does."""
    votes: dict[str, Counter] = defaultdict(Counter)
    for r in readers:
        for a in r["answers"]:
            if a.get("finding") in ("yes", "no", "unsure") and a["id"] in key:
                votes[a["id"]][a["finding"]] += 1
    out = {}
    for iid, k in key.items():
        v = votes.get(iid, Counter())
        n = sum(v.values())
        should_see = k["kind"] in ("original", "random_removal")
        if n == 0:
            status = "unread"
        elif v["unsure"] or (v["yes"] and v["no"]):
            status = "indeterminate"
        elif (v["yes"] > 0) == should_see:
            status = "confirmed"
        else:
            status = "disputed"
        out[iid] = {"status": status, **{s: v[s] for s in ("yes", "no", "unsure")}, "n": n}
    return out


def fmt(r: dict) -> str:
    if "diff" not in r:
        return "-"
    return f"{r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] p={'<0.001' if r['p'] < 0.001 else f'{r['p']:.3f}'}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", nargs="+", required=True, help="answer key(s); several packs are scored together")
    ap.add_argument("--answers", nargs="*", default=[])
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True, help="the test views the pack was drawn from")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--labels", nargs="*", default=[], help="run=label")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    labels = dict(x.split("=", 1) for x in args.labels)
    pack, key, readers = load_packs(args.key, args.answers)
    adj = adjudicate(key, readers)
    out = ["# Reader adjudication of the synthetic labels", "",
           f"Pack(s) {pack}: {len(key)} images, {len(readers)} reader(s). An erased image is confirmed when no "
           "reader sees the asked finding, disputed when every reader does, indeterminate when readers split or any says "
           "cannot tell. Control-edited and unedited lesion images are confirmed when every reader sees the finding; "
           "lesion-free images when none does.", ""]

    # 1. status by kind and source
    out += ["## 1. Label status by kind and source", "", "| Kind | Source | Images | Confirmed | Disputed | Indeterminate | Unread |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    by = defaultdict(Counter)
    for iid, k in key.items():
        by[(k["kind"], k["source"])][adj[iid]["status"]] += 1
        by[(k["kind"], "all")][adj[iid]["status"]] += 1
    for (kind, src), c in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] != "all", kv[0][1])):
        out.append(f"| {kind} | {src} | {sum(c.values())} | {c['confirmed']} | {c['disputed']} | {c['indeterminate']} | {c['unread']} |")
    disputed = [f"{key[i]['case_id']} ({key[i]['source']}, {key[i]['kind']}: yes {a['yes']}, no {a['no']}, cannot tell {a['unsure']})"
                for i, a in adj.items() if a["status"] == "disputed"]
    if disputed:
        out += ["", "Disputed: " + "; ".join(disputed) + "."]

    # 2. comparisons on the pack's cases under three label assignments
    erased = {i: k for i, k in key.items() if k["kind"] == "target_removal"}
    cases_all = sorted({k["case_id"] for k in erased.values()})
    cases_conf = sorted({k["case_id"] for i, k in erased.items() if adj[i]["status"] == "confirmed"})
    cases_conf_ind = sorted({k["case_id"] for i, k in erased.items() if adj[i]["status"] in ("confirmed", "indeterminate")})
    sets = [("all pack cases", cases_all), ("reader-confirmed erasures only", cases_conf),
            ("confirmed + indeterminate", cases_conf_ind)]
    runs = {r: load_outcomes(Path(args.results) / r) for r in [args.ref, *args.runs] if (Path(args.results) / r).exists()}
    out += ["", "## 2. Model comparisons on the pack's cases, by label assignment", "",
            f"{labels.get(args.ref, args.ref)} minus each model, paired bootstrap over the listed cases "
            "(the pack holds one erased image per case; its other views are scored with it).", ""]
    for name, cases in sets:
        keep = set(cases)
        out += [f"**{name}** ({len(cases)} cases)", "", "| Model | " + " | ".join(LABEL[m] for m in METRICS) + " |",
                "| --- |" + " --- |" * len(METRICS)]
        ref = [o for o in runs.get(args.ref, []) if o.case_id in keep]
        for r in args.runs:
            if r not in runs:
                out.append(f"| {labels.get(r, r)} | (no results) |")
                continue
            other = [o for o in runs[r] if o.case_id in keep]
            cells = [fmt(paired_bootstrap(ref, other, m)) if cases else "-" for m in METRICS]
            out.append(f"| {labels.get(r, r)} | " + " | ".join(cells) + " |")
        out.append("")

    # 3. sensitivity on unedited lesion images by finding, next to erased-lesion claims
    views = {v.view_id: v for f in args.views for v in load_views(f)}
    out += ["## 3. Unedited lesion sensitivity and erased-lesion claims by asked finding (full test set)", "",
            "Sensitivity = correct answers on unedited lesion images (original views) for that finding; erased claims = "
            "answers that still claim the finding after erasure. A finding the model misses when present cannot be "
            "credited for 'not claiming it' when erased.", ""]
    for r, outs in runs.items():
        sens, claims = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
        for o in outs:
            v = views.get(o.view_id)
            fnd = (asked_finding(v.question) if v else None) or "other"
            if o.kind == "original" and o.action == "answer":
                sens[fnd][1] += 1
                sens[fnd][0] += bool(o.correct)
            elif o.kind == "original":
                sens[fnd][1] += 1
            if o.kind == "target_removal":
                claims[fnd][1] += 1
                claims[fnd][0] += bool(o.action == "answer" and not o.claims_absent)
        rows = sorted(set(sens) | set(claims), key=lambda f: -sens[f][1])[:15]
        out += [f"**{labels.get(r, r)}**", "", "| Finding | Sensitivity on unedited lesion images | Erased-lesion claims |",
                "| --- | --- | --- |"]
        for f in rows:
            s, c = sens[f], claims[f]
            out.append(f"| {f} | {s[0]}/{s[1]}" + (f" ({s[0] / s[1]:.0%})" if s[1] else "") + f" | {c[0]}/{c[1]}"
                       + (f" ({c[0] / c[1]:.0%})" if c[1] else "") + " |")
        out.append("")
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
