"""Model answers on erasures the specialist readers accepted (R29, docs/REVIEW_EXPERIMENTS.md Amendment 10).

Pack-4 images whose views are in the main test (LaMa erasures and control edits, unedited lesion and lesion-free
images) are grouped by the specialists' answers: board-certified radiologists judge brain MRI, breast ultrasound,
chest X-ray and SLAKE images; gastroenterologists or endoscopists judge colonoscopy images. An erasure is accepted
when no judge answered "yes", strictly accepted when every judge answered "no". Every stored main-test run is then
scored on each group. Uses stored replies; no model is run.

    python scripts/reader_rescore.py --key key_v4.json --answers answers/*.json --results RESULTS \
        --runs MedScope-4B=v4_final_test MedScope-4B-N=v6_test --comparison v2_gemini_test ... --out r29.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import scored_rows  # noqa: E402
from scripts.make_reader_study import exact_ci, load_key  # noqa: E402
from scripts.reader_verified import claims, found  # noqa: E402

LOWER_BOUND = 0.20          # the rule of docs/READER_VERIFIED.md
MIN_ACCEPTED = 10           # fewer accepted erasures: descriptive only
FINISHED = 0.9              # a reader counts once this share of the pack is answered


def is_colon(item: dict) -> bool:
    s = f"{item.get('source', '')} {item.get('case_id', '')}".lower()
    return "colonoscopy" in s or "kvasir" in s


def judge_kind(reader: dict) -> str | None:
    """'radiology', 'colonoscopy' or None (not a specialist judge for R29)."""
    spec = str(reader.get("specialty", "")).lower()
    cert = str(reader.get("certified", "")).lower()
    if "gastro" in spec or "endoscop" in spec:
        return "colonoscopy"
    if cert == "board-certified radiologist":
        return "radiology"
    return None


def main_test_items(key: dict) -> dict:
    """Key items whose views exist in the main-test runs (everything but the Stable Diffusion views)."""
    return {i: it for i, it in key.items() if str(it.get("tool", "")).lower() not in ("diffusion", "sd", "stable_diffusion")}


def groups(items: dict, readers: list[dict]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """view ids per group, and the number of judges per imaging area."""
    judges = {"radiology": [], "colonoscopy": []}
    for r in readers:
        k = judge_kind(r)
        if k and len(r["answers"]) >= FINISHED * len(items):
            judges[k].append({a["id"]: a for a in r["answers"]})
    g = {k: [] for k in ("accepted", "strict", "called_present", "confirmed_lesion", "confirmed_lesion_free")}
    for i, it in items.items():
        js = judges["colonoscopy" if is_colon(it) else "radiology"]
        answers = [j[i]["finding"] for j in js if i in j and j[i].get("finding")]
        if not answers:
            continue
        yes = sum(a == "yes" for a in answers)
        vid, kind = it["view_id"], it["kind"]
        if kind == "target_removal":
            if yes == 0:
                g["accepted"].append(vid)
                if all(a == "no" for a in answers):
                    g["strict"].append(vid)
            else:
                g["called_present"].append(vid)
        elif kind in ("original", "random_removal") and yes == len(answers):
            g["confirmed_lesion"].append(vid)
        elif kind == "natural_negative" and yes == 0:
            g["confirmed_lesion_free"].append(vid)
    return g, {k: len(v) for k, v in judges.items()}


def rate(rows: dict, vids: list[str], fn) -> tuple[int, int]:
    have = [v for v in vids if v in rows]
    return sum(bool(fn(rows[v])) for v in have), len(have)


def fmt(k: int, n: int) -> str:
    if not n:
        return "-"
    lo, hi = exact_ci(k, n)
    return f"{k}/{n} ({100 * k / n:.1f}%, {100 * lo:.1f}-{100 * hi:.1f})"


def pooled(run_rows: list[dict], vids: list[str], fn, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean over models of the per-image indicator; 95% interval by resampling images."""
    vids = [v for v in vids if any(v in rows for rows in run_rows)]
    if not vids or not run_rows:
        return float("nan"), float("nan"), float("nan")
    M = np.array([[float(fn(rows[v])) if v in rows else np.nan for v in vids] for rows in run_rows])
    per_image = np.nanmean(M, axis=0)
    rng = np.random.default_rng(seed)
    boots = [np.nanmean(per_image[rng.integers(0, len(vids), len(vids))]) for _ in range(n_boot)]
    return float(np.nanmean(per_image)), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def paired_gap(comp_rows: list[dict], ref_rows: dict, vids: list[str], n_boot: int = 2000, seed: int = 0):
    """Comparison models pooled minus the reference model, per image, on the same images; interval by images."""
    vids = [v for v in vids if v in ref_rows and any(v in r for r in comp_rows)]
    if not vids:
        return float("nan"), float("nan"), float("nan"), 0
    comp = np.nanmean(np.array([[float(claims(r[v])) if v in r else np.nan for v in vids] for r in comp_rows]), axis=0)
    ref = np.array([float(claims(ref_rows[v])) for v in vids])
    d = comp - ref
    rng = np.random.default_rng(seed)
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)]
    return float(d.mean()), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)), len(vids)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", required=True)
    ap.add_argument("--answers", nargs="+", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--runs", nargs="*", default=[], help="name=run_dir for our models (first is the reference)")
    ap.add_argument("--comparison", nargs="+", required=True, help="run folder names of the comparison models")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pack, key = load_key(args.key)
    items = main_test_items(key)
    readers = []
    for f in args.answers:
        r = json.loads(Path(f).read_text())
        if pack and r.get("pack") not in (None, pack):
            continue
        readers.append(r)
    g, n_judges = groups(items, readers)
    res = Path(args.results)
    vids_all = {it["view_id"] for it in items.values()}

    def load(run: str) -> dict:
        d = res / run if not Path(run).is_absolute() else Path(run)
        return {r["view_id"]: r for r in scored_rows(d) if r["view_id"] in vids_all}

    comp = [(run, load(run)) for run in args.comparison]
    ours = [(spec.split("=", 1)[0], load(spec.split("=", 1)[1])) for spec in args.runs]

    n_acc = len(g["accepted"])
    out = ["# Model answers on erasures the specialists accepted (R29, Amendment 10)", "",
           f"Judges: {n_judges['radiology']} board-certified radiologist(s) for brain MRI, breast ultrasound, chest X-ray "
           f"and SLAKE images; {n_judges['colonoscopy']} gastroenterologist(s) for colonoscopy images. Pack-4 images in the "
           f"main test: {len(items)} (Stable Diffusion views left out).", "",
           f"Erasures accepted (no judge said yes): **{n_acc}**; strictly accepted (every judge said no): "
           f"{len(g['strict'])}; called present by a judge: {len(g['called_present'])}. Reader-confirmed lesions: "
           f"{len(g['confirmed_lesion'])}; reader-confirmed lesion-free images: {len(g['confirmed_lesion_free'])}.", "",
           "Cells: findings reported k/n (percent, exact 95% CI); on lesions, lesions found.", "",
           "| Model | Accepted erasures | Strictly accepted | Erasures called present by a judge | Confirmed lesions found | "
           "Confirmed lesion-free images: finding reported |", "| --- | --- | --- | --- | --- | --- |"]
    for name, rows in comp + ours:
        out.append(f"| {name} | {fmt(*rate(rows, g['accepted'], claims))} | {fmt(*rate(rows, g['strict'], claims))} | "
                   f"{fmt(*rate(rows, g['called_present'], claims))} | {fmt(*rate(rows, g['confirmed_lesion'], found))} | "
                   f"{fmt(*rate(rows, g['confirmed_lesion_free'], claims))} |")
    out += ["", "## Comparison models pooled (mean over the models; 95% interval by resampling images)", "",
            "| Group | Findings reported |", "| --- | --- |"]
    comp_rows = [rows for _, rows in comp]
    verdict = "not judged (no comparison runs)"
    for label, key_ in (("Accepted erasures", "accepted"), ("Strictly accepted erasures", "strict"),
                        ("Erasures called present by a judge", "called_present"),
                        ("Confirmed lesion-free images", "confirmed_lesion_free")):
        m, lo, hi = pooled(comp_rows, g[key_], claims)
        out.append(f"| {label} | {100 * m:.1f}% ({100 * lo:.1f}-{100 * hi:.1f}) |")
        if key_ == "accepted" and comp_rows:
            if n_acc < MIN_ACCEPTED:
                verdict = f"descriptive only ({n_acc} accepted erasures, fewer than {MIN_ACCEPTED})"
            elif lo > LOWER_BOUND:
                verdict = f"**holds on specialist-accepted erasures** (lower bound {100 * lo:.1f}% > {100 * LOWER_BOUND:.0f}%)"
            else:
                verdict = f"**not shown on specialist-accepted erasures** (lower bound {100 * lo:.1f}% <= {100 * LOWER_BOUND:.0f}%)"
    if ours:
        out += ["", "## Comparison models pooled minus each of our models, same accepted erasures (paired by image)", "",
                "| Model | Difference in findings reported [95% CI] | Images |", "| --- | --- | --- |"]
        for name, rows in ours:
            d, lo, hi, n = paired_gap(comp_rows, rows, g["accepted"])
            out.append(f"| {name} | {100 * d:+.1f} percentage points [{100 * lo:+.1f}, {100 * hi:+.1f}] | {n} |")
    by_src: dict[str, list[int]] = {}
    for it in items.values():
        if it["view_id"] in g["accepted"]:
            s = "Colonoscopy" if is_colon(it) else str(it.get("source", "other"))
            by_src.setdefault(s, [0])[0] += 1
    out += ["", "Accepted erasures by source: " + ", ".join(f"{s} {v[0]}" for s, v in sorted(by_src.items())) + ".", "",
            f"Reading (rule of docs/READER_VERIFIED.md, Amendment 10): the main result {verdict}.", "",
            "Limits: single images without clinical context; few accepted erasures; every model read the same images, "
            "so the pooled interval resamples images, not models."]
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
