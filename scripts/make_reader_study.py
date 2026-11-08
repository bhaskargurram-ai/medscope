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
    -> DIR/site/ (index.html, items.json, images/): the page to publish
       DIR/key.json: the answer key (keep private)

    python scripts/make_reader_study.py --score --key DIR/key.json --answers ANSWERS.json... --out report.md
"""

from __future__ import annotations

import argparse
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
                    "source": source_of(v.case_id), "question": v.question, "stress": is_stress(v)})
    (site / "items.json").write_text(json.dumps({"pack": pack, "items": items}, indent=1))
    shutil.copy(ROOT / "reader" / "index.html", site / "index.html")
    (Path(args.out) / "key.json").write_text(json.dumps({"pack": pack, "items": key}, indent=1))
    c = Counter((k["source"], k["kind"]) for k in key)
    print(f"pack {pack}: {len(items)} images: " + ", ".join(f"{k}: {sum(1 for x in key if x['kind'] == k)}" for k in KINDS)
          + f"; stress-test items: {sum(1 for x in key if x['stress'])}")
    for (s, k), n in sorted(c.items()):
        print(f"  {s} | {k}: {n}")


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


def score(args) -> None:
    pack, key = load_key(args.key)
    readers = []
    for f in args.answers:
        r = json.loads(Path(f).read_text())
        if pack and r.get("pack") != pack:
            print(f"skipping {f}: answered on pack {r.get('pack')!r}, this key is pack {pack!r}")
            continue
        readers.append(r)
    kinds = [k for k in KINDS if any(x["kind"] == k for x in key.values())]
    n_kind = Counter(x["kind"] for x in key.values())
    out = ["# Reader study", "", f"Pack {pack or '(first pack)'}: {len(key)} images "
           f"({', '.join(f'{n_kind[k]} {LABEL[k].lower()}' for k in kinds)}); {len(readers)} reader(s).", "",
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
    if len(binary) >= 2:
        names = list(binary)
        out += ["", "## 3. Agreement between readers (edited yes/no)", ""]
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
    ap.add_argument("--key")
    ap.add_argument("--answers", nargs="*", default=[])
    args = ap.parse_args()
    score(args) if args.score else build(args)


if __name__ == "__main__":
    main()
