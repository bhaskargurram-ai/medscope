"""Reader study (physician readers, no annotation used for training): is a lesion-erased image recognisable as edited,
and is the erased lesion still visible?

Builds a blinded pack from the main test set: equal numbers of unmodified lesion images, lesion-erased images (the
LaMa erasures the models were tested on) and unmodified lesion-free images, each from a different case, stratified
by source. Lesion-free images are included so that "no lesion" is not a cue for "edited". Every image is re-saved
the same way (PNG, no metadata) under an opaque name; the page holds no answer key.

    python scripts/make_reader_study.py --views TEST_VIEWS... --negatives TEST_NEG... --out DIR [--per-kind 32] [--seed 0]
    -> DIR/site/ (index.html, items.json, images/): the page to publish
       DIR/key.json: the answer key (keep private)

    python scripts/make_reader_study.py --score --key DIR/key.json --answers ANSWERS.json... --out report.md
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.eval.runner import load_views  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("original", "target_removal", "natural_negative")


def source_of(case_id: str) -> str:
    from medscope.colab import dataset_of
    return dataset_of(case_id)


def build(args) -> None:
    from PIL import Image
    rng = random.Random(args.seed)
    views = [v for f in args.views + args.negatives for v in load_views(f)]
    yes_cases = {v.case_id for v in views if v.kind.value == "original" and v.answer.strip().lower() == "yes"}
    views = [v for v in views if (v.case_id in yes_cases and v.kind.value in ("original", "target_removal"))
             or (v.kind.value == "natural_negative" and v.answer.strip().lower() == "no")]   # yes/no presence questions only
    by_kind: dict[str, dict[str, list]] = {k: defaultdict(list) for k in KINDS}
    for v in views:
        if v.kind.value in KINDS and Path(v.image_path).exists():
            by_kind[v.kind.value][source_of(v.case_id)].append(v)
    used_cases: set[str] = set()
    chosen = []
    for kind in ("target_removal", "original", "natural_negative"):      # erasures first: the scarcest kind per source
        pools = {s: rng.sample(vs, len(vs)) for s, vs in by_kind[kind].items()}
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
    site = Path(args.out) / "site"
    (site / "images").mkdir(parents=True, exist_ok=True)
    items, key = [], []
    for i, v in enumerate(chosen):
        iid = f"i{i:03d}"
        img = Image.open(v.image_path).convert("RGB")
        img.save(site / "images" / f"{iid}.png", optimize=True)            # same format and no metadata for every kind
        items.append({"id": iid, "image": f"images/{iid}.png", "question": v.question})
        key.append({"id": iid, "kind": v.kind.value, "edited": v.kind.value == "target_removal",
                    "finding_present": v.kind.value == "original", "case_id": v.case_id, "view_id": v.view_id,
                    "source": source_of(v.case_id), "question": v.question})
    (site / "items.json").write_text(json.dumps({"items": items}, indent=1))
    shutil.copy(ROOT / "reader" / "index.html", site / "index.html")
    (Path(args.out) / "key.json").write_text(json.dumps(key, indent=1))
    c = Counter((k["source"], k["kind"]) for k in key)
    print(f"{len(items)} images: " + ", ".join(f"{k}: {sum(1 for x in key if x['kind'] == k)}" for k in KINDS))
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


def score(args) -> None:
    key = {k["id"]: k for k in json.loads(Path(args.key).read_text())}
    readers = [json.loads(Path(f).read_text()) for f in args.answers]
    out = ["# Reader study", "", f"{len(key)} images; {len(readers)} reader(s).", "",
           "## 1. Can physicians tell lesion-erased images from unmodified ones?", "",
           "Edited-rating 1 (definitely real) to 4 (definitely edited). AUC 0.5 = chance, 1.0 = always recognised.", "",
           "| Reader | Answered | Erased called edited | Unmodified called edited | AUC (erased vs unmodified) | Accuracy |",
           "| --- | --- | --- | --- | --- | --- |"]
    binary = {}
    for r in readers:
        ans = {a["id"]: a for a in r["answers"] if a.get("edited")}
        er = [int(ans[i]["edited"]) for i in ans if key[i]["edited"]]
        un = [int(ans[i]["edited"]) for i in ans if not key[i]["edited"]]
        acc = (sum(x >= 3 for x in er) + sum(x <= 2 for x in un)) / max(1, len(er) + len(un))
        out.append(f"| {r['reader']} | {len(ans)} | {sum(x >= 3 for x in er)}/{len(er)} | {sum(x >= 3 for x in un)}/{len(un)} | "
                   f"{auc(er, un):.2f} | {acc:.0%} |")
        binary[r["reader"]] = {i: int(int(ans[i]["edited"]) >= 3) for i in ans}
    out += ["", "## 2. Is the erased finding still visible?", "",
            "Share answering Yes to the clinical question.", "",
            "| Reader | Unmodified lesion images | Lesion-erased images | Unmodified lesion-free images |",
            "| --- | --- | --- | --- |"]
    for r in readers:
        ans = {a["id"]: a for a in r["answers"] if a.get("finding")}
        cells = []
        for kind in KINDS:
            xs = [ans[i]["finding"] for i in ans if key[i]["kind"] == kind]
            cells.append(f"{sum(x == 'yes' for x in xs)}/{len(xs)} (cannot tell {sum(x == 'unsure' for x in xs)})")
        out.append(f"| {r['reader']} | " + " | ".join(cells) + " |")
    if len(binary) >= 2:
        names = list(binary)
        out += ["", "## 3. Agreement between readers (edited yes/no)", ""]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                common = sorted(set(binary[names[i]]) & set(binary[names[j]]))
                k = kappa([binary[names[i]][c] for c in common], [binary[names[j]][c] for c in common])
                out.append(f"- {names[i]} vs {names[j]}: Cohen's kappa {k:.2f} on {len(common)} images")
    out += ["", "## 4. By source (all readers pooled): erased images called edited", "", "| Source | Erased called edited |",
            "| --- | --- |"]
    by_src: dict[str, list[int]] = defaultdict(list)
    for r in readers:
        for a in r["answers"]:
            if a.get("edited") and key[a["id"]]["edited"]:
                by_src[key[a["id"]]["source"]].append(int(int(a["edited"]) >= 3))
    for s, xs in sorted(by_src.items()):
        out.append(f"| {s} | {sum(xs)}/{len(xs)} |")
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
