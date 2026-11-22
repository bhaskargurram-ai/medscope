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

import numpy as np

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
NEG_PRE = re.compile(r"\b(no|not|without|free of|negative for|absence of|clear of|nor|resolution of|resolved|"
                     r"evacuation of|re-?expansion of|removal of|"
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
LOOKING = re.compile(r"\b(evaluat\w* for|assess\w* for|(?:examin|survey|inspect|scan|review|check)\w* (?:[\w,-]+ ){0,20}for|look\w* for|search\w* for|"
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
    if (LOOKING.search(before[-160:]) or re.search(r"\bany\b[^.;]{0,30}$", before)) \
            and not NEG_PRE.search(before) and not re.search(r"\b(is|are|was|were)\b", after[:40]):
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
    import sys
    if cli_extra(sys.argv[1:]):
        return
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


# ---------------------------------------------------------------------------------------------------------------
# R23 (Amendment 8): pneumothorax views from CheXthought, and scoring a run on them
# ---------------------------------------------------------------------------------------------------------------
QUESTION = "Is there a pneumothorax in this chest X-ray?"
PAD, MIN_SIDE = 0.05, 0.15          # fixed in Amendment 8


def click_box(points: list, pad: float = PAD, min_side: float = MIN_SIDE) -> Optional[list[int]]:
    """Bounding box (0-1000) of normalised click points, padded and widened to a minimum size; None without points."""
    if not points:
        return None
    xs, ys = [float(p[0]) for p in points], [float(p[1]) for p in points]
    box = []
    for lo, hi in ((min(xs), max(xs)), (min(ys), max(ys))):
        lo, hi = lo - pad, hi + pad
        if hi - lo < min_side:
            mid = (lo + hi) / 2
            lo, hi = mid - min_side / 2, mid + min_side / 2
        lo, hi = max(0.0, lo), min(1.0, hi)
        box.append((lo, hi))
    (x1, x2), (y1, y2) = box
    return [round(x1 * 1000), round(y1 * 1000), round(x2 * 1000), round(y2 * 1000)]


def patient_of(image_id: str) -> str:
    return image_id.split("_")[0]


def in_test(patient: str, share: float = 0.2) -> bool:
    import hashlib
    return int(hashlib.sha1(f"r23:{patient}".encode()).hexdigest(), 16) % 1000 < share * 1000


def select_pneumothorax(reads: list[dict], labels: dict, n_train: int = 1500, n_test: int = 300, seed: int = 0) -> dict:
    """Image ids for each split (Amendment 8). reads: rows of reads.jsonl; labels: label_index() output."""
    import random
    by_img = defaultdict(list)
    for r in reads:
        if r["finding"] == "pneumothorax":
            by_img[r["image_id"]].append(r)
    pos, neg = {}, []
    frontal = {k for k in labels} if labels else set()
    images = {r["image_id"] for r in reads}
    for img in sorted(images):
        if "frontal" not in img:
            continue
        lab = labels.get(chexpert_key(img) or "", {}).get("Pneumothorax")
        rows = by_img.get(img, [])
        if lab == 1:
            pts = [tuple(p) for r in rows if r["status"] == "positive" for p in r["points"]]
            if pts:
                pos[img] = click_box(pts)
        elif (lab is None or lab != lab or lab == 0) and chexpert_key(img) in frontal \
                and not any(r["status"] in ("positive", "uncertain") for r in rows):
            neg.append(img)
    rng = random.Random(seed)
    out = {}
    for split, n in (("train", n_train), ("test", n_test)):
        want_test = split == "test"
        p = sorted(i for i in pos if in_test(patient_of(i)) == want_test)
        q = sorted(i for i in neg if in_test(patient_of(i)) == want_test)
        rng.shuffle(p)
        rng.shuffle(q)
        p = p[:n]
        out[split] = {"pos": {i: pos[i] for i in p}, "neg": q[:len(p)]}
    return out


def views_for(sel: dict, image_path) -> list[dict]:
    """View dicts for one split; image_path(image_id) -> local path."""
    out = []
    for img, box in sel["pos"].items():
        out.append({"view_id": f"cxt{img}__original", "case_id": f"cxt{img}", "patient_id": f"chexpert_{patient_of(img)}",
                    "kind": "original", "image_path": image_path(img), "question": QUESTION, "answer": "Yes",
                    "answer_aliases": [], "lesion_box": box, "critical": True,
                    "meta": {"modality": "xray", "dataset": "chexthought", "finding": "pneumothorax", "image_id": img}})
    for img in sel["neg"]:
        out.append({"view_id": f"cxtneg{img}__natural_negative", "case_id": f"cxtneg{img}",
                    "patient_id": f"chexpert_{patient_of(img)}", "kind": "natural_negative", "image_path": image_path(img),
                    "question": QUESTION, "answer": "No", "answer_aliases": [], "lesion_box": None, "critical": False,
                    "meta": {"modality": "xray", "dataset": "chexthought", "finding": "pneumothorax", "image_id": img}})
    return out


def test_rows(scored: list[dict], views: dict) -> dict[str, dict]:
    """case id -> {'patient', 'kind', 'present', 'safe', 'box'} for the views in `views`."""
    out = {}
    for r in scored:
        v = views.get(r["view_id"])
        if v is None or r["kind"] not in ("original", "natural_negative"):
            continue                       # erased, control-edited and degraded views are not part of this test
        present = r["action"] == "answer" and not r.get("claims_absent")
        out[r["case_id"]] = {"patient": v["patient_id"], "kind": r["kind"], "present": float(present),
                             "safe": float(r["action"] == "refer" or (r["action"] == "answer" and bool(r.get("claims_absent")))),
                             "box": float(present and float(r.get("iou") or 0) >= 0.3)}
    return out


def score_test(views_file: Path, runs: list[str], ref: str) -> str:
    """Sensitivity, specificity (absent or refer on healthy films), Youden and correct boxes, with patient-clustered
    differences from `ref`. runs: name=run_dir."""
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parent))
    from natural_pairs import cluster_boot
    from medscope.eval.runner import read_jsonl, scored_rows
    views = {v["view_id"]: v for v in read_jsonl(views_file)}
    per = {}
    for spec in runs:
        name, d = spec.split("=", 1)
        if Path(d).exists():
            per[name] = test_rows(scored_rows(d), views)
        else:
            print(f"  {d}: not found, left out")

    def youden_terms(rows):
        """Per case: contribution to sensitivity + specificity - 1, scaled so that the mean is Youden."""
        n_pos = sum(r["kind"] == "original" for r in rows.values()) or 1
        n_neg = sum(r["kind"] != "original" for r in rows.values()) or 1
        n = len(rows)
        return {c: (r["present"] * n / n_pos if r["kind"] == "original" else r["safe"] * n / n_neg) - 1.0
                for c, r in rows.items()}

    lines = [f"| Model | Pneumothorax films | called present | with a correct box | Healthy films | absent or referred | "
             f"Youden [95% CI] | {ref} minus model, Youden [95% CI], p | {ref} minus model: pneumothorax films called present "
             f"[95% CI], p | {ref} minus model: healthy films called positive |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    ref_terms = youden_terms(per[ref]) if ref in per else {}
    for name, rows in per.items():
        pos = [r for r in rows.values() if r["kind"] == "original"]
        neg = [r for r in rows.values() if r["kind"] != "original"]
        cl = {c: r["patient"] for c, r in rows.items()}
        terms = youden_terms(rows)
        e, lo, hi, _ = cluster_boot(terms, cl)
        cmp = sens_cmp = neg_cmp = "--"
        if name != ref and ref_terms:
            common = ref_terms.keys() & terms.keys()
            d, dlo, dhi, p = cluster_boot({c: ref_terms[c] - terms[c] for c in common}, cl)
            cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f}"
            rr = per[ref]
            cp = [c for c in common if rows[c]["kind"] == "original"]
            cn = [c for c in common if rows[c]["kind"] != "original"]
            if cp:
                d, dlo, dhi, p = cluster_boot({c: rr[c]["present"] - rows[c]["present"] for c in cp}, cl)
                sens_cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f}"
            if cn:
                d, dlo, dhi, p = cluster_boot({c: rr[c]["present"] - rows[c]["present"] for c in cn}, cl)
                neg_cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}]"
        sens = np.mean([r["present"] for r in pos]) if pos else float("nan")
        spec = np.mean([r["safe"] for r in neg]) if neg else float("nan")
        boxed = sum(r["box"] for r in pos)
        lines.append(f"| {name} | {len(pos)} | {sens:.1%} | {int(boxed)} | {len(neg)} | {spec:.1%} | "
                     f"{e:.3f} [{lo:.3f}, {hi:.3f}] | {cmp} | {sens_cmp} | {neg_cmp} |")
    lines += ["", "Youden = share of pneumothorax films called present + share of healthy films answered 'absent' or "
              "referred - 1. Correct box: called present with a box of IoU >= 0.3 against the radiologists' click box. "
              "2,000 resamples of whole patients."]
    return "\n".join(lines) + "\n"


def cli_extra(argv: list[str]) -> bool:
    """`build-views` and `score-test` subcommands; returns False if argv is not one of them."""
    if not argv or argv[0] not in ("build-views", "score-test"):
        return False
    ap = argparse.ArgumentParser(prog=f"chexthought.py {argv[0]}")
    if argv[0] == "build-views":
        ap.add_argument("--reads", required=True)
        ap.add_argument("--labels", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args(argv[1:])
        reads = [json.loads(l) for l in Path(a.reads).read_text().splitlines() if l.strip()]
        sel = select_pneumothorax(reads, label_index(Path(a.labels)))
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "selection.json").write_text(json.dumps(sel))
        print({s: (len(v["pos"]), len(v["neg"])) for s, v in sel.items()}, "(positives, negatives) per split")
    else:
        ap.add_argument("--views", required=True)
        ap.add_argument("--runs", nargs="+", required=True)
        ap.add_argument("--ref", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args(argv[1:])
        text = score_test(Path(a.views), a.runs, a.ref)
        Path(a.out).write_text(text)
        print(text)
    return True
