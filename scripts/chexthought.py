"""CheXthought statistics (R22, Amendment 7): what each radiologist said about each finding, and where they clicked.

For every reasoning trace and finding, each sentence that names the finding is read as positive, negative or uncertain
(a rule-based reader of the sentence, not a clinical NLP system), and the click points whose [#n] markers sit in a
positive or uncertain sentence are kept. Per image, the two (or more) readers are compared, and the statements are
checked against the CheXpert labels of CheXpert Plus where a label file is given.

    python scripts/chexthought.py --csv chexthoughtdataset.csv [--labels chexpert_labels.csv] --out DIR
    -> DIR/reads.jsonl (image, reader index, finding, status, points), DIR/stats.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

FINDINGS = {
    "pneumothorax": r"pneumothora(?:x|ces)",
    "pleural effusion": r"(?:pleural )?effusions?",
    "consolidation": r"consolidat\w*",
    "nodule": r"nodul\w*",
    "mass": r"\bmass(?:es)?\b",
    "cardiomegaly": r"cardiomegaly|enlarged (?:cardiac|heart)|cardiac enlargement",
    "edema": r"(?:pulmonary )?o?edema",
    "atelectasis": r"atelecta\w*",
}
CHEXPERT = {"pneumothorax": "Pneumothorax", "pleural effusion": "Pleural Effusion", "consolidation": "Consolidation",
            "nodule": "Lung Lesion", "mass": "Lung Lesion", "cardiomegaly": "Cardiomegaly", "edema": "Edema",
            "atelectasis": "Atelectasis"}
NEG = re.compile(r"\b(no|not|without|free of|negative for|absent|absence of|resolved|clear of|nor|rule[sd]? out|"
                 r"do not (?:see|identify|appreciate)|cannot (?:see|identify)|there is no|there are no|"
                 r"no evidence of|no definite|no sizable|no visible|no gross)\b", re.I)
UNC = re.compile(r"\b(possible|possibly|probable|probably|may|might|could|cannot (?:be )?exclude[d]?|can ?not exclude|"
                 r"uncertain|equivocal|questionable|suspicious for|concern(?:ing)? for|suggest\w*|likely|subtle|"
                 r"indeterminate|versus|vs\.?|differential)\b|\?", re.I)
MARK = re.compile(r"\[#(\d+)\]")
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
STATUS_ORDER = ("positive", "uncertain", "negative")


def sentence_status(sentence: str, term: re.Pattern) -> Optional[str]:
    """positive / negative / uncertain for the first mention of `term` in the sentence, None if not mentioned.
    A negation cue before the mention (same clause) makes it negative; an uncertainty cue anywhere makes it uncertain."""
    m = term.search(sentence)
    if not m:
        return None
    clause_start = max(sentence.rfind(sep, 0, m.start()) for sep in (",", ";", ":", " but ", " whereas ", " although "))
    before = sentence[clause_start + 1 if clause_start >= 0 else 0:m.start()]
    if NEG.search(before):
        return "negative"
    if UNC.search(sentence):
        return "uncertain"
    return "positive"


def read_trace(text: str, points: list[dict]) -> dict[str, dict]:
    """finding -> {'status': overall status, 'points': [(x, y), ...] of the sentences that support it}.
    Overall: positive if any sentence is positive, else uncertain if any is, else negative."""
    by_n = {int(p["n"]): (float(p["x"]), float(p["y"])) for p in points if "n" in p}
    out = {}
    for finding, pat in FINDINGS.items():
        term = re.compile(pat, re.I)
        statuses, pts = [], []
        for s in SENT.split(text or ""):
            st = sentence_status(s, term)
            if st is None:
                continue
            statuses.append(st)
            if st in ("positive", "uncertain"):
                pts += [by_n[int(n)] for n in MARK.findall(s) if int(n) in by_n]
        if statuses:
            overall = next(k for k in STATUS_ORDER if k in statuses)
            out[finding] = {"status": overall, "points": pts}
    return out


def chexpert_key(image_id: str) -> Optional[str]:
    """'patient00002_study1_view2_lateral' -> 'patient00002/study1/view2_lateral' (the path stem used by CheXpert)."""
    m = re.match(r"(patient\d+)_(study\d+)_(view\d+_\w+)$", image_id)
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else None


def label_index(labels_csv: Path) -> dict[str, dict[str, float]]:
    import pandas as pd
    df = pd.read_csv(labels_csv)
    pcol = next(c for c in df.columns if "path" in c.lower())
    out = {}
    for _, r in df.iterrows():
        m = re.search(r"(patient\d+)/(study\d+)/(view\d+_\w+)", str(r[pcol]))
        if m:
            out["/".join(m.groups())] = {v: r.get(v) for v in set(CHEXPERT.values()) if v in df.columns}
    return out


def stats(rows: list[dict], labels: Optional[dict] = None) -> str:
    """Markdown summary of the per-reader statements."""
    per_image = defaultdict(lambda: defaultdict(list))
    for r in rows:
        per_image[r["image_id"]][r["finding"]].append(r["status"])
    readers = Counter(r["image_id"] for r in rows if r["finding"] == "_trace")
    n_img = len(readers)
    lines = [f"Traces: {sum(readers.values()):,}; images: {n_img:,}.", "",
             "| Finding | Traces positive | uncertain | negative | not mentioned | Images: both readers positive | "
             "readers disagree (one positive or uncertain, one negative or silent) | positive traces with click points |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for f in FINDINGS:
        c = Counter(r["status"] for r in rows if r["finding"] == f)
        mentioned = sum(c.values())
        not_mentioned = sum(readers.values()) - mentioned
        both = disagree = 0
        for img, n in readers.items():
            st = per_image[img].get(f, []) + ["silent"] * (n - len(per_image[img].get(f, [])))
            pos = [s in ("positive", "uncertain") for s in st]
            if all(s == "positive" for s in st):
                both += 1
            elif any(pos) and not all(pos):
                disagree += 1
        with_pts = sum(1 for r in rows if r["finding"] == f and r["status"] == "positive" and r["points"])
        lines.append(f"| {f} | {c['positive']:,} | {c['uncertain']:,} | {c['negative']:,} | {not_mentioned:,} | "
                     f"{both:,} | {disagree:,} | {with_pts:,} |")
    if labels:
        lines += ["", "Against the CheXpert labels (image level: 1 positive, 0 negative, -1 uncertain; blank = not "
                  "mentioned in the report). Share of traces whose statement matches:", "",
                  "| Finding | Label 1: trace positive or uncertain | Label 0 or blank: trace negative or silent | Images labelled 1 |",
                  "| --- | --- | --- | --- |"]
        for f in FINDINGS:
            col = CHEXPERT[f]
            hit_pos = n_pos = hit_neg = n_neg = 0
            imgs_pos = set()
            for img, n in readers.items():
                lab = labels.get(chexpert_key(img) or "", {}).get(col)
                if lab is None:
                    continue
                st = per_image[img].get(f, []) + ["silent"] * (n - len(per_image[img].get(f, [])))
                if lab == 1:
                    imgs_pos.add(img)
                    n_pos += len(st)
                    hit_pos += sum(s in ("positive", "uncertain") for s in st)
                elif lab != lab or lab == 0:            # NaN (blank) or 0
                    n_neg += len(st)
                    hit_neg += sum(s in ("negative", "silent") for s in st)
            lines.append(f"| {f} | {hit_pos / n_pos:.1%} of {n_pos:,} | {hit_neg / n_neg:.1%} of {n_neg:,} | {len(imgs_pos):,} |"
                         if n_pos and n_neg else f"| {f} | -- | -- | {len(imgs_pos):,} |")
    lines += ["", "Statements are read by rules (negation cue before the finding in the same clause = negative; an "
              "uncertainty cue in the sentence = uncertain); spot-check before using them as labels. Nodule and mass "
              "both map to CheXpert's Lung Lesion."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--labels", default=None, help="CheXpert labels CSV (Path column plus one column per finding)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import pandas as pd
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.csv)
    rows = []
    for i, r in enumerate(df.itertuples(index=False)):
        try:
            pts = json.loads(r.spatial_annotations) if isinstance(r.spatial_annotations, str) else []
        except json.JSONDecodeError:
            pts = []
        rows.append({"image_id": r.image_id, "trace": i, "finding": "_trace", "status": "", "points": []})
        for f, v in read_trace(r.chain_of_thought_reasoning, pts).items():
            rows.append({"image_id": r.image_id, "trace": i, "finding": f, "status": v["status"], "points": v["points"]})
        if i % 20000 == 0:
            print(f"{i:,} traces read", flush=True)
    (out / "reads.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows if r["finding"] != "_trace"))
    labels = label_index(Path(args.labels)) if args.labels else None
    text = stats(rows, labels)
    (out / "stats.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
