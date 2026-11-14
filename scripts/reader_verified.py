"""Reader-verified analysis (docs/READER_VERIFIED.md): every main-test run scored only on the reader-study images,
with the physicians' answers deciding which erasures count as clean. Uses stored replies; no model is run.

    python scripts/reader_verified.py --key reader/key_v2.json --answers reader/answers/*.json \
        --results RESULTS --out RESULTS/reader_verified.md
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

LOWER_BOUND = 0.20


def reader_groups(keys: dict, answers: list[dict]) -> dict[str, list[str]]:
    """view ids per reader-defined group (see docs/READER_VERIFIED.md)."""
    yes = {i: sum(a.get(i, {}).get("finding") == "yes" for a in answers) for i in keys}
    n = len(answers)
    g: dict[str, list[str]] = {k: [] for k in ("clean", "majority_clean", "residual", "confirmed_lesion", "confirmed_healthy")}
    for i, it in keys.items():
        vid, kind = it["view_id"], it["kind"]
        if kind == "target_removal":
            if yes[i] == 0:
                g["clean"].append(vid)
            if yes[i] < n:
                g["majority_clean"].append(vid)
            if yes[i] == n:
                g["residual"].append(vid)
        elif kind in ("original", "random_removal") and yes[i] >= 1:
            g["confirmed_lesion"].append(vid)
        elif kind == "natural_negative" and yes[i] == 0:
            g["confirmed_healthy"].append(vid)
    return g


def runs_on(results: Path, ids: set[str], min_cover: float = 0.9) -> list[tuple[str, bool, dict]]:
    """(run name, frontier?, view_id -> scored row) for main-test runs with the benchmark prompt covering the images."""
    out = []
    for d in sorted(results.iterdir()):
        s = d / "summary.json"
        if not d.is_dir() or not s.exists():
            continue
        try:
            meta = json.loads(s.read_text()).get("meta", {})
        except json.JSONDecodeError:
            continue
        vf = str(meta.get("views_file", ""))
        if meta.get("split") != "test" or "inpaint" in vf or d.name.startswith("v4q_inp_") or meta.get("prompt", "agent") != "agent":
            continue
        if meta.get("ablation") or meta.get("fewshot") or meta.get("tool_budget") is not None:
            continue
        allrows = {r["view_id"]: r for r in scored_rows(d)}
        rows = {k: v for k, v in allrows.items() if k in ids}
        if len(rows) >= min_cover * len(ids):
            FULL[d.name] = allrows
            out.append((d.name, meta.get("precision") == "api", rows))
    return out


FULL: dict[str, dict] = {}       # run name -> every scored row of the run (for the checks below)


def source(case_id: str) -> str:
    for pre, name in (("kvasir", "Colonoscopy"), ("hyperkvasir", "Colonoscopy"), ("busi", "Breast ultrasound"),
                      ("chestxdet", "Chest X-ray"), ("lgg", "Brain MRI"), ("slake", "SLAKE CT/MRI")):
        if case_id.startswith(pre):
            return name
    return "other"


def checks(keys: dict, answers: list[dict], runs) -> list[str]:
    """Checks for confounds in the reader-verified comparison (added after the first result, 14 November 2026)."""
    out = ["", "## Checks for confounds (added after the first result; descriptive)", ""]
    n = len(answers)
    erased = [(i, it) for i, it in keys.items() if it["kind"] == "target_removal"]
    grp = {i: ("clean" if sum(a[i]["finding"] == "yes" for a in answers) == 0 else
               "residual" if sum(a[i]["finding"] == "yes" for a in answers) == n else "split") for i, _ in erased}
    # 1. which imaging types end up in each group
    out += ["**1. Imaging type of the erased images in each reader group**", "",
            "| Group | " + " | ".join(sorted({source(it['case_id']) for _, it in erased})) + " |",
            "| --- | " + " | ".join("---" for _ in sorted({source(it['case_id']) for _, it in erased})) + " |"]
    srcs = sorted({source(it["case_id"]) for _, it in erased})
    for gname in ("clean", "split", "residual"):
        out.append(f"| {gname} | " + " | ".join(str(sum(1 for i, it in erased if grp[i] == gname and source(it['case_id']) == s))
                                               for s in srcs) + " |")
    broad = sum(1 for i, it in erased if grp[i] == "residual" and "abnormalit" in it["question"].lower())
    out += ["", f"Residual erasures asked as 'Is there an abnormality ...?': {broad} of "
                f"{sum(1 for i in grp if grp[i] == 'residual')} (another finding in the image makes 'yes' correct "
                "for physicians and models alike).", ""]
    # 2. paired: did each frontier model see the lesion on the unedited image of the same case?
    fr = [(name, FULL[name]) for name, f, _ in runs if f]
    if fr:
        out += ["**2. Frontier models, same cases: claim on the erasure, split by whether the model found the lesion "
                "on the unedited image of the same case (main test)**", "",
                "| Group | Found unedited lesion: claims after erasure | Missed unedited lesion: claims after erasure |",
                "| --- | --- | --- |"]
        for gname in ("clean", "split", "residual"):
            a = b = na = nb = 0
            for i, it in erased:
                if grp[i] != gname:
                    continue
                for _, rows in fr:
                    o, e = rows.get(f"{it['case_id']}__original"), rows.get(it["view_id"])
                    if not o or not e:
                        continue
                    if found(o):
                        na += 1
                        a += claims(e)
                    else:
                        nb += 1
                        b += claims(e)
            out.append(f"| {gname} | {a}/{na} ({100 * a / max(na, 1):.0f}%) | {b}/{nb} ({100 * b / max(nb, 1):.0f}%) |")
        # 3. the whole main test by imaging type
        out += ["", "**3. Whole main test (all erasures, not only the reader images), frontier models pooled: claims after "
                "erasure by imaging type. Readers judged colonoscopy erasures clean (erased images called positive no "
                "more often than lesion-free ones).**", "",
                "| Imaging type | Erasures | Frontier claims after erasure | Frontier finds unedited lesion |", "| --- | --- | --- | --- |"]
        by = {}
        for _, rows in fr:
            for vid, r in rows.items():
                if r.get("kind") not in ("target_removal", "original"):
                    continue
                s = source(r["case_id"])
                d = by.setdefault(s, {"e": 0, "ec": 0, "o": 0, "of": 0, "cases": set()})
                if r["kind"] == "target_removal":
                    d["e"] += 1
                    d["ec"] += claims(r)
                    d["cases"].add(r["case_id"])
                else:
                    d["o"] += 1
                    d["of"] += found(r)
        for s, d in sorted(by.items()):
            out.append(f"| {s} | {len(d['cases'])} | {100 * d['ec'] / max(d['e'], 1):.0f}% | {100 * d['of'] / max(d['o'], 1):.0f}% |")
    return out


def claims(r: dict) -> bool:       # still claims the finding (erased) / claims it on a healthy image
    return r.get("action") == "answer" and not r.get("correct")


def found(r: dict) -> bool:
    return r.get("action") == "answer" and bool(r.get("correct"))


def rate(rows: dict, vids: list[str], fn) -> tuple[int, int]:
    have = [v for v in vids if v in rows]
    return sum(fn(rows[v]) for v in have), len(have)


def fmt(k: int, n: int) -> str:
    if not n:
        return "-"
    lo, hi = exact_ci(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, {100 * lo:.0f}-{100 * hi:.0f})"


def pooled(runs, vids: list[str], fn, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean over models of the per-image claim indicator; interval by resampling images."""
    M = np.array([[float(fn(rows[v])) if v in rows else np.nan for v in vids] for _, _, rows in runs])
    if M.size == 0:
        return float("nan"), float("nan"), float("nan")
    per_image = np.nanmean(M, axis=0)
    rng = np.random.default_rng(seed)
    boots = [np.nanmean(per_image[rng.integers(0, len(vids), len(vids))]) for _ in range(n_boot)]
    return float(np.nanmean(per_image)), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", nargs="+", required=True)
    ap.add_argument("--answers", nargs="+", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    keys, packs = {}, set()
    for kp in args.key:
        pack, items = load_key(kp)
        packs.add(pack)
        keys.update(items)
    answers, readers = [], []
    for ap_ in args.answers:
        a = json.loads(Path(ap_).read_text())
        if packs and a.get("pack") not in packs:
            continue
        answers.append({x["id"]: x for x in a["answers"]})
        readers.append(f"{a.get('reader')} ({a.get('specialty')}, experience {a.get('years')})")
    g = reader_groups(keys, answers)
    runs = runs_on(Path(args.results), {it["view_id"] for it in keys.values()})
    out = ["# Reader-verified analysis (docs/READER_VERIFIED.md)", "",
           f"Readers: {', '.join(readers)}. Images: {len(keys)}. Reader-clean erasures (neither reader saw the finding): "
           f"**{len(g['clean'])}**; majority-clean: {len(g['majority_clean'])}; residual (both saw it): {len(g['residual'])}; "
           f"reader-confirmed lesions: {len(g['confirmed_lesion'])}; reader-confirmed healthy images: {len(g['confirmed_healthy'])}.", "",
           f"{len(runs)} main-test runs with the benchmark prompt cover these images "
           f"({sum(f for _, f, _ in runs)} frontier models). Cells: claims k/n (percent, exact 95% interval).", "",
           "| Run | Frontier | Claims on reader-clean erasures | Majority-clean | Residual erasures | Finds reader-confirmed lesions | Claims on reader-confirmed healthy |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, fr, rows in sorted(runs, key=lambda x: (not x[1], x[0])):
        out.append(f"| {name} | {'yes' if fr else ''} | {fmt(*rate(rows, g['clean'], claims))} | "
                   f"{fmt(*rate(rows, g['majority_clean'], claims))} | {fmt(*rate(rows, g['residual'], claims))} | "
                   f"{fmt(*rate(rows, g['confirmed_lesion'], found))} | {fmt(*rate(rows, g['confirmed_healthy'], claims))} |")
    fr_runs = [r for r in runs if r[1]]
    open_runs = [r for r in runs if not r[1]]
    out += ["", "## Pooled (mean over models, 95% interval by resampling images)", "",
            "| Group | Reader-clean erasures | Majority-clean | Residual |", "| --- | --- | --- | --- |"]
    verdict = "not decided (no frontier runs found)"
    for label, rs in (("Frontier models", fr_runs), ("Open and MedScope models", open_runs)):
        if not rs:
            continue
        cells = []
        for grp in ("clean", "majority_clean", "residual"):
            m, lo, hi = pooled(rs, g[grp], claims)
            cells.append(f"{100 * m:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})")
            if label == "Frontier models" and grp == "clean":
                verdict = (f"**holds on reader-verified images** (lower bound {100 * lo:.0f}% > {100 * LOWER_BOUND:.0f}%)"
                           if lo > LOWER_BOUND else
                           f"**does not hold on reader-verified images** (lower bound {100 * lo:.0f}% <= {100 * LOWER_BOUND:.0f}%)")
        out.append(f"| {label} ({len(rs)}) | " + " | ".join(cells) + " |")
    out += ["", f"Pre-registered reading: the headline that frontier models claim erased findings {verdict}.", "",
            "Limits: two trainee readers, single images without clinical context, and few reader-clean erasures; "
            "every model read the same images, so the pooled interval resamples images, not models."]
    out += checks(keys, answers, runs)
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
