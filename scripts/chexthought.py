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
    "pneumothorax": r"(?<!hydro)pneumothora(?:x|ces)",
    "pleural effusion": r"(?<!pericardial )(?:pleural )?effusions?",
    "consolidation": r"consolidat\w*",
    "nodule": r"(?<!reticulo)(?<!micro)\bnodul(?:e|es|ar)\b(?! opacities related)",
    "mass": r"\bmass(?:es)?\b(?! effect)(?!-like)",
    "cardiomegaly": r"cardiomegaly|enlarged (?:cardiac|heart)|cardiac enlargement|heart (?:size )?is enlarged",
    "edema": r"(?:pulmonary |interstitial )?o?edema",
    "atelectasis": r"atelecta\w*",
}
CHEXPERT = {"pneumothorax": "Pneumothorax", "pleural effusion": "Pleural Effusion", "consolidation": "Consolidation",
            "nodule": "Lung Lesion", "mass": "Lung Lesion", "cardiomegaly": "Cardiomegaly", "edema": "Edema",
            "atelectasis": "Atelectasis"}
# NegEx-style: a negation cue before the finding negates it unless a termination word comes between them;
# a post-negation after the finding (same scope) negates it too. Uncertainty and "looking for" are checked first.
NEG_PRE = re.compile(r"\b(no|not|without|free of|negative for|absence of|clear of|nor|"
                     r"do not (?:see|identify|appreciate|note)|cannot (?:see|identify)|"
                     r"no (?:evidence|sign|signs) of|neither)\b", re.I)
NEG_POST = re.compile(r"^[^.;]{0,60}?\b(is|are|was|were|has|have)\s+(?:been\s+)?(?:now\s+)?(absent|not\s+(?:seen|identified|"
                      r"present|visible|evident|demonstrated|appreciated)|resolved|excluded|ruled out)\b", re.I)
TERMINATE = re.compile(r"\b(but|however|whereas|although|though|except|apart from|aside from|yet|while|which|"
                       r"there is|there are|i see|i note|i identify|consistent with|compatible with|representing)\b|;|:", re.I)
UNC = re.compile(r"\b(possible|possibly|probable|probably|may|might|could|cannot (?:be )?(?:fully |entirely )?exclude[d]?|"
                 r"can ?not (?:be )?(?:fully )?exclude[d]?|(?:to|ability to) exclude|not (?:be )?excluded|uncertain\w*|"
                 r"equivocal|questionable|suspicious for|suspect\w*|concern(?:ing)? for|suggest\w*|likely|"
                 r"indeterminate|versus|vs\.?|differential|whether|either|favou?r\w*)\b|\?", re.I)
LOOKING = re.compile(r"\b(evaluat\w* for|assess\w* for|examin\w* (?:\w+ ){0,6}for|look\w* for|check\w* for|search\w* for|"
                     r"to assess|to evaluate|such as|complications?|in (?:the )?setting of suspected|"
                     r"risk of|history of|known history)\b", re.I)
MARK = re.compile(r"\[#(\d+)\]")
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
STATUS_ORDER = ("positive", "uncertain", "negative")


def sentence_status(sentence: str, term: re.Pattern) -> Optional[str]:
    """positive / negative / uncertain for the first mention of `term` in the sentence, None if not mentioned or only
    looked for ("I examine the right hemithorax for pneumothorax")."""
    s = MARK.sub("", sentence)
    m = term.search(s)
    if not m:
        return None
    before, after = s[:m.start()], s[m.end():]
    if LOOKING.search(before[-80:]) and not re.search(r"\b(is|are|was|were)\b", after[:40]):
        return None
    neg = None
    for cue in NEG_PRE.finditer(before):
        neg = cue
    if neg is not None and not TERMINATE.search(before[neg.end():]):
        # "cannot exclude" style cues are uncertainty, not negation
        if not re.search(r"\b(cannot|can ?not)\b", neg.group(0), re.I):
            return "negative"
    if NEG_POST.search(after) and not re.search(r"\bnot (?:be )?(?:fully )?excluded\b", after[:60], re.I):
        return "uncertain" if re.search(r"\bcannot be (?:fully )?excluded\b", after[:60], re.I) else "negative"
    if UNC.search(s) or re.search(r"\b(?:or|and/or)\b", s[max(0, m.start() - 30):m.end() + 30], re.I):
        return "uncertain"       # "atelectasis or consolidation": one of two alternatives
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


def read_labels(path: Path):
    """CheXpert labels as a DataFrame: a CSV, a JSON list, or JSON lines (the CheXbert files of CheXpert Plus)."""
    import pandas as pd
    if path.suffix == ".csv":
        return pd.read_csv(path)
    try:
        return pd.read_json(path, lines=True)
    except ValueError:
        return pd.read_json(path)


def label_index(labels_csv: Path) -> dict[str, dict[str, float]]:
    df = read_labels(labels_csv)
    pcol = next((c for c in df.columns if "path" in c.lower()), None)
    if pcol is None:
        raise SystemExit(f"{labels_csv}: no image path column (columns: {list(df.columns)[:12]})")
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
    labels = None
    if args.labels:
        try:
            labels = label_index(Path(args.labels))
        except SystemExit as e:              # a wrong labels file should not throw away the statement statistics
            print(f"labels left out: {e}")
    text = stats(rows, labels)
    (out / "stats.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
