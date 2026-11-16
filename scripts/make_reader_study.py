"""Reader study (physician readers, no annotation used for training): is a lesion-erased image recognisable as edited,
is the matched control edit as recognisable, and is the erased lesion still visible?

Builds a blinded pack from the main test set: equal numbers, each from a different case and stratified by source, of
  original          unmodified lesion image
  target_removal    the lesion erased (the LaMa erasures the models were tested on)
  random_removal    the matched control: the same shape erased elsewhere with the same tool, lesion intact
  natural_negative  unmodified lesion-free image
Lesion-free images are included so that "no lesion" is not a cue for "edited"; random-removal images so that readers
rate the control edit too (if the control is as recognisable as the erasure, a reader who "spots the edit" cannot
tell which it is). Every image is re-saved the same way (PNG, no metadata) under an opaque name; the page holds no
answer key, and every pack carries an id so answer files from an older pack are never scored against a newer key.

    python scripts/make_reader_study.py --views TEST_VIEWS... --negatives TEST_NEG... --out DIR [--per-kind 32] [--seed 0]
        [--tool diffusion=INPAINT_TEST/diffusion/views.jsonl ...] [--tool-per-kind 40]

--tool adds erased and control-edited images made with another inpainting tool on the same masks (held-out tools:
TELEA, Stable Diffusion); each comes from a case not otherwise in the pack, and the key records the tool, so the
residual finding and edit detectability are reported per tool.
    -> DIR/site/ (index.html, items.json, images/): the page to publish
       DIR/key.json: the answer key (keep private)

    python scripts/make_reader_study.py --score --key DIR/key.json --answers ANSWERS.json... --out report.md

Pack 4 saves answers automatically to a Google Sheet (reader/expert.html, reader/apps_script.gs). Its three tabs,
exported as CSV (readers.csv, profiles.csv, answers.csv), are turned into the same answer files with

    python scripts/make_reader_study.py --from-sheet DIR --out DIR/answers
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("original", "target_removal", "random_removal", "natural_negative")
EDITED = {"target_removal", "random_removal"}
PRESENT = {"original", "random_removal"}
LABEL = {"original": "Unmodified lesion images", "target_removal": "Lesion-erased images",
         "random_removal": "Control-edited images (lesion intact)", "natural_negative": "Unmodified lesion-free images"}
ACCEPTABLE_RESIDUAL = 0.10      # pre-specified: share of erased images on which a reader still sees the finding
# Findings whose erasure is not expected to be clinically clean (diffuse, or with secondary signs): kept in the pack as
# named stress tests and reported apart from the localized findings (polyp, nodule, mass, tumour, cyst ...).
STRESS_FINDINGS = ("pneumothorax", "opacity", "opacities", "covid", "consolidation", "infiltrate", "infiltration",
                   "pneumonia", "effusion", "oedema", "edema", "atelectasis", "fibrosis", "emphysema", "cardiomegaly")
STRESS_SOURCES = ("QaTa-COV19", "SIIM")


def is_stress(view) -> bool:
    from medscope.actions import asked_finding
    f = (asked_finding(view.question) or "").lower()
    return any(k in f for k in STRESS_FINDINGS) or any(src.lower() in source_of(view.case_id).lower() for src in STRESS_SOURCES)


def source_of(case_id: str) -> str:
    from medscope.colab import dataset_of
    return dataset_of(case_id)


def build(args) -> None:
    from PIL import Image
    rng = random.Random(args.seed)
    views = [v for f in args.views + args.negatives for v in load_views(f)]
    yes_cases = {v.case_id for v in views if v.kind.value == "original" and v.answer.strip().lower() == "yes"}
    views = [v for v in views if (v.case_id in yes_cases and v.kind.value in ("original", "target_removal", "random_removal"))
             or (v.kind.value == "natural_negative" and v.answer.strip().lower() == "no")]   # yes/no presence questions only
    by_kind: dict[str, dict[str, list]] = {k: defaultdict(list) for k in KINDS}
    for v in views:
        if v.kind.value in KINDS and Path(v.image_path).exists():
            by_kind[v.kind.value][source_of(v.case_id)].append(v)
    used_cases: set[str] = set()
    for kp in args.exclude_keys:                   # a supplement: no case that an earlier pack already shows
        used_cases |= {k["case_id"] for k in load_key(kp)[1].values()}
    chosen = []
    for kind in ("target_removal", "random_removal", "original", "natural_negative"):   # scarcest kinds first
        # localized findings are drawn first within each source; diffuse ones (stress tests) fill in only afterwards
        pools = {s: sorted(rng.sample(vs, len(vs)), key=lambda v: is_stress(v), reverse=True) for s, vs in by_kind[kind].items()}
        sources = sorted(pools)
        picked = 0
        while picked < args.per_kind and any(pools.values()):
            for s in sources:
                while pools[s] and pools[s][-1].case_id in used_cases:
                    pools[s].pop()
                if pools[s] and picked < args.per_kind:
                    v = pools[s].pop()
                    chosen.append(v)
                    used_cases.add(v.case_id)
                    picked += 1
        if picked < args.per_kind:
            raise SystemExit(f"only {picked} {kind} images available")
    for spec in args.tool:                         # erasures and control edits made with another tool, same masks
        tool, _, path = spec.partition("=")
        tv = [v for v in load_views(path) if v.case_id in yes_cases and Path(v.image_path).exists()]
        for kind in ("target_removal", "random_removal"):
            pools = defaultdict(list)
            for v in tv:
                if v.kind.value == kind:
                    pools[source_of(v.case_id)].append(v)
            pools = {s: sorted(rng.sample(vs, len(vs)), key=lambda v: is_stress(v), reverse=True) for s, vs in pools.items()}
            picked = 0
            while picked < args.tool_per_kind and any(pools.values()):
                for s in sorted(pools):
                    while pools[s] and pools[s][-1].case_id in used_cases:
                        pools[s].pop()
                    if pools[s] and picked < args.tool_per_kind:
                        v = pools[s].pop()
                        v.meta = {**(v.meta or {}), "reader_tool": tool}
                        chosen.append(v)
                        used_cases.add(v.case_id)
                        picked += 1
            if picked < args.tool_per_kind:
                print(f"note: only {picked} {tool} {kind} images available")
    rng.shuffle(chosen)
    pack = hashlib.sha1("|".join(v.view_id for v in chosen).encode()).hexdigest()[:12]
    site = Path(args.out) / "site"
    (site / "images").mkdir(parents=True, exist_ok=True)
    items, key = [], []
    for i, v in enumerate(chosen):
        iid = f"i{i:03d}"
        img = Image.open(v.image_path).convert("RGB")
        img.save(site / "images" / f"{iid}.png", optimize=True)            # same format and no metadata for every kind
        items.append({"id": iid, "image": f"images/{iid}.png", "question": v.question})
        key.append({"id": iid, "kind": v.kind.value, "edited": v.kind.value in EDITED,
                    "finding_present": v.kind.value in PRESENT, "case_id": v.case_id, "view_id": v.view_id,
                    "source": source_of(v.case_id), "question": v.question, "stress": is_stress(v),
                    "tool": (v.meta or {}).get("reader_tool") or ("lama" if v.kind.value in EDITED else None)})
    (site / "items.json").write_text(json.dumps({"pack": pack, "items": items}, indent=1))
    shutil.copy(ROOT / "reader" / "index.html", site / "index.html")
    (Path(args.out) / "key.json").write_text(json.dumps({"pack": pack, "items": key}, indent=1))
    c = Counter((k["source"], k["kind"]) for k in key)
    print(f"pack {pack}: {len(items)} images: " + ", ".join(f"{k}: {sum(1 for x in key if x['kind'] == k)}" for k in KINDS)
          + f"; stress-test items: {sum(1 for x in key if x['stress'])}")
    for (s, k), n in sorted(c.items()):
        print(f"  {s} | {k}: {n}")


def sheet_to_readers(readers: list[dict], profiles: list[dict], answers: list[dict]) -> list[dict]:
    """Rows of the pack-4 Google Sheet -> one answer record per reader, in the answer-file format.

    Every save is a new row; a reader's latest answer per image counts (server time, then the page's own time). Codes
    labelled TEST (the notebook's round-trip check) and codes not in the readers tab are left out."""
    label = {}
    for r in readers:
        code = str(r.get("code", "")).strip()
        if code and str(r.get("label", "")).strip().upper() != "TEST":
            label[code] = str(r.get("label", "")).strip() or code
    prof = {}
    for p in profiles:                              # the latest profile row per reader
        if p.get("reader") in label:
            prof[p["reader"]] = p
    latest: dict[tuple[str, str], dict] = {}
    for a in answers:
        code = str(a.get("reader", "")).strip()
        if code not in label:
            continue
        k = (code, str(a.get("item", "")).strip())
        stamp = (str(a.get("server_time", "")), str(a.get("client_time", "")))
        if k not in latest or stamp >= latest[k]["_stamp"]:
            latest[k] = {**a, "_stamp": stamp}
    out = []
    for code, name in label.items():
        rows = sorted((v for (c, _), v in latest.items() if c == code), key=lambda v: v["_stamp"])
        if not rows:
            continue
        p = prof.get(code, {})
        spec = p.get("specialty", "")
        if p.get("subspecialty"):
            spec = f"{spec} ({p['subspecialty']})"
        out.append({"reader": name, "pack": rows[0].get("pack", ""), "specialty": spec, "years": str(p.get("years", "")),
                    "certified": p.get("certified", ""), "seen_before": p.get("seen_before", ""),
                    "consent": p.get("consent", ""),
                    "answers": [{"id": str(v["item"]).strip(), "edited": str(v["edited"]).strip(),
                                 "finding": str(v["finding"]).strip(), "seconds": v.get("seconds", ""),
                                 "comment": v.get("comment", "")} for v in rows]})
    return out


def from_sheet(args) -> None:
    d = Path(args.from_sheet)
    read = lambda name: list(csv.DictReader(open(d / name, newline="", encoding="utf-8")))  # noqa: E731
    recs = sheet_to_readers(read("readers.csv"), read("profiles.csv"), read("answers.csv"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for r in recs:
        f = out / f"reader_{r['reader']}.json"
        f.write_text(json.dumps(r, indent=1))
        print(f"{f}: {len(r['answers'])} answers ({r['specialty'] or 'specialty not given'}, {r['certified'] or '?'}, "
              f"{r['years'] or '?'} y; earlier round: {r['seen_before'] or '?'}; consent: {r['consent'] or '?'})")


def auc(pos: list[float], neg: list[float]) -> float:
    pairs = [(1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg]
    return sum(pairs) / len(pairs) if pairs else float("nan")


def kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def exact_ci(k: int, n: int) -> tuple[float, float]:
    """Clopper-Pearson 95% interval for k of n (scipy if present, else a binary search on the binomial tail)."""
    if n == 0:
        return float("nan"), float("nan")
    try:
        from scipy.stats import beta
        lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
        hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
        return lo, hi
    except ImportError:
        def tail(p, upper):      # P(X <= k) if upper else P(X >= k) under Binomial(n, p)
            probs = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
            return sum(probs[: k + 1]) if upper else sum(probs[k:])
        def solve(upper):
            lo_, hi_ = 0.0, 1.0
            for _ in range(60):
                mid = (lo_ + hi_) / 2
                if tail(mid, upper) > 0.025:
                    lo_ = mid if upper else lo_
                    hi_ = hi_ if upper else mid
                else:
                    hi_ = mid if upper else hi_
                    lo_ = lo_ if upper else mid
            return (lo_ + hi_) / 2
        return (0.0 if k == 0 else solve(False)), (1.0 if k == n else solve(True))


def load_key(path: str) -> tuple[str | None, dict]:
    raw = json.loads(Path(path).read_text())
    if isinstance(raw, list):                      # the first pack (three kinds, no pack id)
        return None, {k["id"]: k for k in raw}
    return raw.get("pack"), {k["id"]: k for k in raw["items"]}


def load_packs(key_paths: list[str], answer_paths: list[str]) -> tuple[str, dict, list[dict]]:
    """Several packs scored together (a pack and its supplement): item ids are namespaced by pack, an answer file is
    matched to its pack by id, and one reader's files from several packs are pooled into one reader record."""
    keys = {}
    key: dict = {}
    for kp in key_paths:
        pack, k = load_key(kp)
        keys[pack] = k
        key.update({f"{pack}:{i}": {**v, "pack": pack} for i, v in k.items()})
    by_reader: dict[str, dict] = {}
    for f in answer_paths:
        r = json.loads(Path(f).read_text())
        pack = r.get("pack")
        if pack not in keys:
            print(f"skipping {f}: answered on pack {pack!r}, not one of {sorted(map(str, keys))}")
            continue
        rec = by_reader.setdefault(r["reader"], {**r, "answers": [], "packs": []})
        rec["answers"] += [{**a, "id": f"{pack}:{a['id']}"} for a in r["answers"]]
        rec["packs"].append(pack)
        for fld in ("specialty", "years", "certified"):
            if r.get(fld) and not rec.get(fld):
                rec[fld] = r[fld]
    label = " + ".join(str(p) for p in keys)
    return label, key, list(by_reader.values())


def score(args) -> None:
    pack, key, readers = load_packs(args.key, args.answers)
    kinds = [k for k in KINDS if any(x["kind"] == k for x in key.values())]
    n_kind = Counter(x["kind"] for x in key.values())
    out = ["# Reader study", "", f"Pack(s) {pack}: {len(key)} images "
           f"({', '.join(f'{n_kind[k]} {LABEL[k].lower()}' for k in kinds)}); {len(readers)} reader(s): "
           + "; ".join(f"{r['reader']} ({r.get('specialty') or 'specialty not given'}, {r.get('years') or '?'} y, "
                       f"{r.get('certified') or 'certification not given'}, "
                       + (f"took part in an earlier round: {r['seen_before']}, " if r.get("seen_before") else "")
                       + f"{len(r['answers'])} answers)" for r in readers) + ".", "",
           "## 1. Can physicians tell edited images from unmodified ones, and the erasure from the control edit?", "",
           "Edited-rating 1 (definitely real) to 4 (definitely edited); 'called edited' = rating 3 or 4. "
           "AUC 0.5 = chance, 1.0 = always told apart. If the control edit is as recognisable as the erasure "
           "(AUC erasure vs control near 0.5), spotting an edit does not tell a reader which kind it is.", "",
           "| Reader | Answered | Erased called edited | Control called edited | Unmodified called edited | "
           "AUC edited vs unmodified | AUC erased vs control | Accuracy (edited yes/no) |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    binary = {}
    for r in readers:
        ans = {a["id"]: a for a in r["answers"] if a.get("edited") and a["id"] in key}
        rate = {k: [int(ans[i]["edited"]) for i in ans if key[i]["kind"] == k] for k in KINDS}
        er, rr = rate["target_removal"], rate["random_removal"]
        un = rate["original"] + rate["natural_negative"]
        ed = er + rr
        acc = (sum(x >= 3 for x in ed) + sum(x <= 2 for x in un)) / max(1, len(ed) + len(un))
        cell = lambda xs: f"{sum(x >= 3 for x in xs)}/{len(xs)}" if xs else "-"   # noqa: E731
        out.append(f"| {r['reader']} | {len(ans)} | {cell(er)} | {cell(rr)} | {cell(un)} | {auc(ed, un):.2f} | "
                   f"{auc(er, rr):.2f} | {acc:.0%} |")
        binary[r["reader"]] = {i: int(int(ans[i]["edited"]) >= 3) for i in ans}
    out += ["", "## 2. Is the finding visible?", "",
            "Share answering Yes to the clinical question (cannot-tell answers in brackets). Lesion-erased images "
            "are the pre-specified check: a Yes there means the erasure left the finding, or a sign of it, visible.", "",
            "| Reader | " + " | ".join(LABEL[k] for k in kinds) + " |", "| --- |" + " --- |" * len(kinds)]
    residual_k = residual_n = 0
    for r in readers:
        ans = {a["id"]: a for a in r["answers"] if a.get("finding") and a["id"] in key}
        cells = []
        for kind in kinds:
            xs = [ans[i]["finding"] for i in ans if key[i]["kind"] == kind]
            cells.append(f"{sum(x == 'yes' for x in xs)}/{len(xs)} (cannot tell {sum(x == 'unsure' for x in xs)})")
            if kind == "target_removal":
                residual_k += sum(x == "yes" for x in xs)
                residual_n += len(xs)
        out.append(f"| {r['reader']} | " + " | ".join(cells) + " |")
    if residual_n:
        lo, hi = exact_ci(residual_k, residual_n)
        verdict = ("within" if hi <= ACCEPTABLE_RESIDUAL else "NOT within") + f" the pre-specified {ACCEPTABLE_RESIDUAL:.0%} criterion"
        out += ["", f"Residual finding on lesion-erased images, all readers pooled: {residual_k}/{residual_n} = "
                f"{residual_k / residual_n:.1%}, exact 95% CI [{lo:.1%}, {hi:.1%}] ({verdict}; reads of the same image by "
                "several readers are not independent, so the interval is optimistic)."]
        # per image (majority of readers), localized findings apart from the named stress tests; this is the
        # independent-erasure count the criterion is judged on
        per_img: dict[str, list[str]] = defaultdict(list)
        for r in readers:
            for a in r["answers"]:
                if a.get("finding") and a["id"] in key and key[a["id"]]["kind"] == "target_removal":
                    per_img[a["id"]].append(a["finding"])
        for label, want in (("localized findings", False), ("named stress tests (diffuse findings, pneumothorax)", True)):
            ids = [i for i in per_img if bool(key[i].get("stress")) == want]
            if not ids:
                continue
            resid = sum(1 for i in ids if sum(x == "yes" for x in per_img[i]) * 2 > len(per_img[i]))
            lo2, hi2 = exact_ci(resid, len(ids))
            out.append(f"- Per image, majority of readers, {label}: {resid}/{len(ids)} erased images with a residual "
                       f"finding, exact 95% CI [{lo2:.1%}, {hi2:.1%}]" + (" (criterion judged here)" if not want else ""))
    tools = sorted({x.get("tool") for x in key.values() if x["kind"] == "target_removal" and x.get("tool")})
    if len(tools) > 1:
        out += ["", "### By editing tool (all readers pooled; per image by reader majority)", "",
                "| Tool | Erased reads with finding Yes | Erased images, majority Yes | Erased called edited | Control called edited |",
                "| --- | --- | --- | --- | --- |"]
        for t in tools:
            ids = {i for i, x in key.items() if x.get("tool") == t}
            reads = [a for r in readers for a in r["answers"] if a["id"] in ids]
            er = [a for a in reads if key[a["id"]]["kind"] == "target_removal"]
            yes = [a for a in er if a.get("finding") == "yes"]
            maj: dict[str, list] = defaultdict(list)
            for a in er:
                if a.get("finding"):
                    maj[a["id"]].append(a["finding"])
            mres = sum(1 for v in maj.values() if sum(x == "yes" for x in v) * 2 > len(v))
            lo, hi = exact_ci(mres, len(maj))
            ed = lambda k: [int(int(a["edited"]) >= 3) for a in reads if a.get("edited") and key[a["id"]]["kind"] == k]  # noqa: E731
            e1, e2 = ed("target_removal"), ed("random_removal")
            out.append(f"| {t} | {len(yes)}/{len([a for a in er if a.get('finding')])} | {mres}/{len(maj)} "
                       f"[{lo:.1%}, {hi:.1%}] | {sum(e1)}/{len(e1)} | {sum(e2)}/{len(e2)} |")
    if len(binary) >= 2:
        names = list(binary)
        finding = {r["reader"]: {a["id"]: int(a["finding"] == "yes") for a in r["answers"]
                                 if a.get("finding") in ("yes", "no") and a["id"] in key} for r in readers}
        out += ["", "## 3. Agreement between readers (edited yes/no; finding yes/no, cannot-tell left out)", ""]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                common = sorted(set(finding[names[i]]) & set(finding[names[j]]))
                k = kappa([finding[names[i]][c] for c in common], [finding[names[j]][c] for c in common])
                out.append(f"- {names[i]} vs {names[j]}: Cohen's kappa on the finding {k:.2f} on {len(common)} images")
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                common = sorted(set(binary[names[i]]) & set(binary[names[j]]))
                k = kappa([binary[names[i]][c] for c in common], [binary[names[j]][c] for c in common])
                out.append(f"- {names[i]} vs {names[j]}: Cohen's kappa {k:.2f} on {len(common)} images")
    out += ["", "## 4. By source (all readers pooled): edited images called edited", "",
            "| Source | Erased called edited | Control called edited | Unmodified called edited |", "| --- | --- | --- | --- |"]
    by_src: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in readers:
        for a in r["answers"]:
            if a.get("edited") and a["id"] in key:
                k = key[a["id"]]
                group = {"target_removal": "erased", "random_removal": "control"}.get(k["kind"], "unmodified")
                by_src[(k["source"], group)].append(int(int(a["edited"]) >= 3))
    for s in sorted({k[0] for k in by_src}):
        cells = [f"{sum(by_src[(s, g)])}/{len(by_src[(s, g)])}" if by_src[(s, g)] else "-" for g in ("erased", "control", "unmodified")]
        out.append(f"| {s} | " + " | ".join(cells) + " |")
    notes = [(r["reader"], a) for r in readers for a in r["answers"]
             if a.get("comment") and a["id"] in key and key[a["id"]]["kind"] == "target_removal" and a.get("finding") == "yes"]
    if notes:
        out += ["", "## 5. What readers noted on erased images they called Yes (free text, descriptive only)", "",
                "| Image | Source | Tool | Reader | Note |", "| --- | --- | --- | --- | --- |"]
        for name, a in sorted(notes, key=lambda x: x[1]["id"]):
            k = key[a["id"]]
            note = str(a["comment"]).replace("|", "/").replace("\n", " ")
            out.append(f"| {a['id']} | {k['source']} | {k.get('tool') or '-'} | {name} | {note} |")
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", nargs="*", default=[])
    ap.add_argument("--negatives", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-kind", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--key", nargs="*", default=[], help="answer key(s); several packs are scored together")
    ap.add_argument("--tool", action="append", default=[],
                    help="build: name=views.jsonl of erasures/control edits made with another tool (e.g. diffusion=...)")
    ap.add_argument("--tool-per-kind", type=int, default=24, help="build: images per kind for each --tool")
    ap.add_argument("--exclude-keys", nargs="*", default=[], help="build: leave out every case already in these packs")
    ap.add_argument("--answers", nargs="*", default=[])
    ap.add_argument("--from-sheet", help="directory with readers.csv, profiles.csv, answers.csv (pack 4); writes answer files to --out")
    args = ap.parse_args()
    if args.from_sheet:
        from_sheet(args)
    else:
        score(args) if args.score else build(args)


if __name__ == "__main__":
    main()
