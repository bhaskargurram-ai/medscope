"""Review check R19 (docs/REVIEW_EXPERIMENTS.md, Amendment 7): an image-blind control.

A model that claims an erased lesion may be answering from the question alone, or from what is left in the image.
For every main-test lesion case whose closed question is answered "Yes" on the unedited image, this builds two extra
views that ask the same question of an image that cannot show the finding:

  blank    a uniform mid-grey image of the same size
  swapped  a lesion-free main-test image of another imaging type (fixed choice by a hash of the case id)

Both are stored as lesion-free views (expected answer "No"), so the usual evaluation and judging apply.

    python scripts/blind_views.py build --views TEST_VIEWS --negatives TEST_NEG --out DIR
    python scripts/evaluate.py ... --views DIR/views_blind.jsonl --out RESULTS/blind_<model>
    python scripts/blind_views.py report --views DIR/views_blind.jsonl --results RESULTS \
        --runs MedScope-4B=blind_v4:v4_final_test gemini-4-argon=blind_gemini:v2_gemini_test ... --out FILE.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from edit_visibility import boot  # noqa: E402

GREY = 128
VARIANTS = ("blank", "swap")


def modality_of(view: dict) -> str:
    """The imaging type, from the case id (views do not all carry meta['modality'])."""
    from medscope.colab import dataset_of
    return dataset_of(view["case_id"])


def pick_swap(case_id: str, modality: str, negatives: list[dict]) -> dict:
    """A lesion-free view of another imaging type, the same one every time for this case."""
    pool = sorted((n for n in negatives if modality_of(n) != modality), key=lambda n: n["view_id"])
    if not pool:
        raise SystemExit(f"no lesion-free image of another imaging type for {case_id} ({modality})")
    return pool[int(hashlib.sha1(case_id.encode()).hexdigest(), 16) % len(pool)]


def blind_rows(views: list[dict], negatives: list[dict], blank_path) -> list[dict]:
    """The blank and swapped views for every eligible lesion case. `blank_path(view) -> str` gives (and may create)
    the grey image for a case; kept as a callable so the selection can be tested without image files."""
    erased = {v["case_id"] for v in views if v["kind"] == "target_removal"}
    out = []
    for v in sorted(views, key=lambda r: r["view_id"]):
        if v["kind"] != "original" or v["case_id"] not in erased or str(v["answer"]).strip().lower() != "yes":
            continue
        swap = pick_swap(v["case_id"], modality_of(v), negatives)
        for variant, image, extra in (("blank", blank_path(v), {}),
                                      ("swap", swap["image_path"], {"swap_from": swap["view_id"],
                                                                    "swap_modality": modality_of(swap)})):
            cid = f"{v['case_id']}{variant}"
            out.append({"view_id": f"{cid}__natural_negative", "case_id": cid, "patient_id": v["patient_id"],
                        "kind": "natural_negative", "image_path": image, "question": v["question"], "answer": "No",
                        "answer_aliases": [], "lesion_box": None, "critical": False,
                        "meta": {"modality": modality_of(v), "dataset": "blind", "blind": variant,
                                 "source_case": v["case_id"], **extra}})
    return out


def build(view_files: list[str], negative_files: list[str], out: Path) -> None:
    from PIL import Image
    from medscope.eval.runner import read_jsonl
    views = [r for f in view_files for r in read_jsonl(Path(f))]
    negatives = [r for f in negative_files for r in read_jsonl(Path(f)) if r["kind"] == "natural_negative"]
    (out / "images").mkdir(parents=True, exist_ok=True)

    def blank_path(v: dict) -> str:
        p = out / "images" / f"{v['case_id']}_blank.png"
        if not p.exists():
            with Image.open(v["image_path"]) as im:
                Image.new("RGB", im.size, (GREY, GREY, GREY)).save(p)
        return str(p)

    rows = blind_rows(views, negatives, blank_path)
    (out / "views_blind.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    n = len(rows) // 2
    print(f"{n} lesion cases with a 'Yes' question -> {len(rows)} views ({n} blank, {n} swapped) in {out / 'views_blind.jsonl'}")


def decision(row: dict) -> str:
    """claimed / denied / referred / clarify for a view whose expected answer is 'absent'."""
    if row["action"] != "answer":
        return "referred" if row["action"] == "refer" else "clarify"
    return "denied" if row.get("correct") else "claimed"


def other_type(meta: dict) -> bool:
    """True if the swapped-in image is of another imaging type than the lesion case (checked from the case ids)."""
    from medscope.colab import dataset_of
    return dataset_of(meta["swap_from"].split("__")[0]) != dataset_of(meta["source_case"])


def model_rows(views: list[dict], blind: list[dict], main: list[dict]) -> dict:
    """Per-case claim indicators for one model: blank, swapped (blind run) and erased, lesion-free (main run)."""
    info = {v["view_id"]: v["meta"] for v in views}
    out = {"blank": {}, "swap": {}, "erased": {}, "decisions": {"blank": [], "swap": []}}
    for r in blind:
        m = info.get(r["view_id"])
        if m is None:
            continue
        if m["blind"] == "swap" and m.get("swap_from") and not other_type(m):
            continue                     # a swapped image of the same imaging type is not image-blind: left out
        d = decision(r)
        out[m["blind"]][m["source_case"]] = float(d == "claimed")
        out["decisions"][m["blind"]].append(d)
    sources = set(out["blank"]) | set(out["swap"])
    for r in main:
        if r["kind"] == "target_removal" and r["case_id"] in sources:
            out["erased"][r["case_id"]] = float(r["action"] == "answer" and not r.get("correct"))
    free = [float(r["action"] == "answer" and not r.get("correct")) for r in main if r["kind"] == "natural_negative"]
    out["lesion_free"] = float(np.mean(free)) if free else float("nan")
    return out


def report(views: list[dict], per_model: dict[str, dict]) -> str:
    share = lambda ds, k: (ds.count(k) / len(ds)) if ds else float("nan")  # noqa: E731
    lines = ["| Model | Cases | Blank image: claimed / denied / referred / asks for a better image | Swapped image: claimed / "
             "denied / referred / asks | Erased lesion: claimed | Lesion-free image: claimed | Erased minus blank, claimed "
             "[95% CI], p |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, m in per_model.items():
        cells = []
        for variant in VARIANTS:
            ds = m["decisions"][variant]
            cells.append(" / ".join(f"{share(ds, k):.1%}" for k in ("claimed", "denied", "referred", "clarify")) + f" (n = {len(ds)})")
        common = m["erased"].keys() & m["blank"].keys()
        erased = float(np.mean([m["erased"][c] for c in common])) if common else float("nan")
        cmp = "--"
        if common:
            d, lo, hi, p = boot({c: m["erased"][c] - m["blank"][c] for c in common})
            cmp = f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}], p = {p:.3f}"
        lines.append(f"| {name} | {len(common)} | {cells[0]} | {cells[1]} | {erased:.1%} | {m['lesion_free']:.1%} | {cmp} |")
    lines += ["", "Blank: a uniform grey image of the same size. Swapped: a lesion-free main-test image of another imaging "
              "type (cases whose swapped-in image turned out to be of the same imaging type are left out of that column). Both ask the question of the lesion case. Erased and lesion-free rates are the stored main-test "
              "answers (erased: the same cases). Erased minus blank: paired over cases, 2,000 resamples. Reading "
              "(Amendment 7): an erased-claim rate above the blank-claim rate with the interval above zero means the "
              "erased claims are not explained by the question alone."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("build")
    a.add_argument("--views", nargs="+", required=True)
    a.add_argument("--negatives", nargs="+", required=True)
    a.add_argument("--out", required=True)
    a = sub.add_parser("report")
    a.add_argument("--views", required=True)
    a.add_argument("--results", required=True)
    a.add_argument("--runs", nargs="+", required=True, help="name=blind_run:main_run (folders under --results)")
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.views, args.negatives, Path(args.out))
        return
    from medscope.eval.runner import read_jsonl, scored_rows
    views = read_jsonl(Path(args.views))
    per_model = {}
    for spec in args.runs:
        name, runs = spec.split("=", 1)
        blind, main_run = runs.split(":", 1)
        b, m = Path(args.results) / blind, Path(args.results) / main_run
        if not b.exists() or not m.exists():
            print(f"  {name}: {blind if not b.exists() else main_run} not found, left out")
            continue
        per_model[name] = model_rows(views, scored_rows(b), scored_rows(m))
    text = report(views, per_model)
    Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
