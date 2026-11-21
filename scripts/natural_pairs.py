"""Natural pairs (review check R9, docs/REVIEW_EXPERIMENTS.md Amendment 4): a real lesion and a real absence from the
same patient, with no editing at all.

  colon  REAL-Colon (60 full colonoscopy videos, 4 centres, per-frame polyp boxes; CC BY 4.0; never used in this
         project). Pair = a frame showing a polyp + a frame of the same video at least 10 s from any boxed frame.
  cxr    NIH ChestX-ray14 follow-up studies (Data_Entry_2017.csv). Pair = a study whose only label is a focal finding
         (pneumothorax, effusion, nodule, mass) + the nearest "No Finding" study of the same patient, same view
         position. Labels are report-mined (not image-read); every ChestX-Det patient is excluded.

Both are written as ordinary views (the lesion image as kind "original", the paired image as "natural_negative",
the pair id in meta["pair"], the video or patient as patient_id), so scripts/evaluate.py runs them unchanged.

    # colonoscopy: annotations first (small), then only the candidate frames of the chosen videos
    python scripts/natural_pairs.py colon-fetch --out DIR [--max-videos 60]
    python scripts/natural_pairs.py colon-build --out DIR
    # chest X-ray
    python scripts/natural_pairs.py cxr-build --csv Data_Entry_2017.csv --images NIH_DIR --exclude VIEWS... --out DIR
    # natural ESG for every run, paired against a reference run, clustered by video or patient
    python scripts/natural_pairs.py score --views V.jsonl --runs name=RUN_DIR ... --ref medscope --out R.md
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medscope.data.loaders.common import stable_index  # noqa: E402
from medscope.data.schema import View, ViewKind  # noqa: E402

FIGSHARE_ARTICLE = 22202866
COLON_Q = "Is there a polyp in this image?"
CXR_FINDINGS = {"Pneumothorax": "a pneumothorax", "Effusion": "a pleural effusion", "Nodule": "a nodule", "Mass": "a mass"}
CXR_CRITICAL = {"Pneumothorax", "Mass"}

# fixed in Amendment 4 before any frame was looked at
MERGE_GAP_S = 2.0          # boxed runs closer than this are one track
MIN_TRACK_S = 1.0          # shorter tracks are skipped
MIN_BOX_FRAC = 0.01        # the lesion frame's largest box covers at least 1% of the frame
NEG_CLEAR_S = 10.0         # the paired frame is at least this far from ANY boxed frame
NEG_WINDOW_S = 30.0        # ...and within this distance of the track (before it; after it if none before)
TRACKS_PER_VIDEO = 3       # the three longest tracks of each video
N_CANDIDATES = 12          # evenly spaced candidate frames per side; the sharpest usable one is kept
CXR_PER_FINDING = 50
MAX_SIDE = 768


# ---------------------------------------------------------------------------------------------- archives

def iter_archive(path: Path) -> Iterator[tuple[str, callable]]:
    """(member name, read()) for a .zip or any tar, streaming (tar.gz is never seeked)."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if not info.is_dir():
                    yield info.filename, (lambda i=info: z.read(i))
        return
    with tarfile.open(path, "r|*") as t:
        for m in t:
            if m.isfile():
                f = t.extractfile(m)
                data = f.read() if f is not None else b""
                yield m.name, (lambda d=data: d)


def frame_number(name: str) -> Optional[int]:
    m = re.search(r"(\d+)\.\w+$", name.rsplit("/", 1)[-1])
    return int(m.group(1)) if m else None


def parse_boxes(xml_bytes: bytes) -> tuple[int, int, list[tuple[float, float, float, float]]]:
    """Image size and every box of one per-frame annotation file (any element with xmin/ymin/xmax/ymax children)."""
    root = ET.fromstring(xml_bytes)
    w = int(float(root.findtext(".//size/width") or root.findtext(".//width") or 0))
    h = int(float(root.findtext(".//size/height") or root.findtext(".//height") or 0))
    boxes = []
    for el in root.iter():
        kids = {c.tag.lower(): (c.text or "").strip() for c in el}
        if {"xmin", "ymin", "xmax", "ymax"} <= kids.keys():
            try:
                boxes.append(tuple(float(kids[k]) for k in ("xmin", "ymin", "xmax", "ymax")))
            except ValueError:
                pass
    return w, h, boxes


# ---------------------------------------------------------------------------------------------- colonoscopy selection

def tracks_from(boxed: np.ndarray, fps: float) -> list[tuple[int, int]]:
    """Runs of boxed frame numbers (sorted), merging gaps shorter than MERGE_GAP_S, dropping short ones."""
    if len(boxed) == 0:
        return []
    gap = max(1, int(round(MERGE_GAP_S * fps)))
    runs, start, prev = [], boxed[0], boxed[0]
    for f in boxed[1:]:
        if f - prev > gap:
            runs.append((int(start), int(prev)))
            start = f
        prev = f
    runs.append((int(start), int(prev)))
    return [(a, b) for a, b in runs if (b - a + 1) >= MIN_TRACK_S * fps]


def even(xs: list[int], n: int) -> list[int]:
    if len(xs) <= n:
        return list(xs)
    idx = np.linspace(0, len(xs) - 1, n).round().astype(int)
    return [xs[i] for i in idx]


def select_video(video: str, frames: dict[int, list], size: tuple[int, int], fps: float) -> list[dict]:
    """Candidate lesion and lesion-free frames for up to TRACKS_PER_VIDEO tracks of one video (pure, testable)."""
    w, h = size
    all_frames = np.array(sorted(frames))
    boxed = np.array([f for f in all_frames if frames[f]])
    out = []
    tracks = sorted(tracks_from(boxed, fps), key=lambda t: (-(t[1] - t[0]), t[0]))[:TRACKS_PER_VIDEO]
    clear, window = NEG_CLEAR_S * fps, NEG_WINDOW_S * fps

    def dist_to_boxed(f: int) -> float:
        i = np.searchsorted(boxed, f)
        d = [abs(f - boxed[j]) for j in (i - 1, i) if 0 <= j < len(boxed)]
        return min(d) if d else float("inf")

    for k, (a, b) in enumerate(sorted(tracks)):
        q1, q3 = a + (b - a) // 4, b - (b - a) // 4
        pos = []
        for f in all_frames[(all_frames >= q1) & (all_frames <= q3)]:
            big = max(((x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in frames[f]), default=0)
            if frames[f] and w and h and big / (w * h) >= MIN_BOX_FRAC:
                pos.append(int(f))
        before = [int(f) for f in all_frames if a - window <= f < a and dist_to_boxed(f) >= clear]
        after = [int(f) for f in all_frames if b < f <= b + window and dist_to_boxed(f) >= clear]
        neg = before if len(before) >= 3 else after
        if not pos or not neg:
            continue
        out.append({"pair": f"{video}_t{k}", "video": video, "track": [a, b], "fps": fps, "size": [w, h],
                    "neg_side": "before" if neg is before else "after",
                    "pos": {str(f): frames[f] for f in even(pos, N_CANDIDATES)},
                    "neg": even(neg, N_CANDIDATES)})
    return out


def video_fps(info_csv: Path) -> dict[str, float]:
    import pandas as pd
    df = pd.read_csv(info_csv)
    vid = next(c for c in df.columns if "video" in c.lower() or c.lower() in ("id", "unique_id"))
    fps = next(c for c in df.columns if "fps" in c.lower())
    return {str(r[vid]).strip(): float(r[fps]) for _, r in df.iterrows()}


def figshare_files() -> list[dict]:
    import requests
    files, page = [], 1
    while True:
        r = requests.get(f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE}/files",
                         params={"page": page, "page_size": 100}, timeout=60)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            return files
        files += batch
        page += 1


def download(url: str, dest: Path) -> Path:
    import requests
    if dest.exists():
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def archives(out: Path) -> Path:
    """Where downloaded video archives go: NP_ARCHIVES (local disk in the notebooks), else out/archives."""
    return Path(os.environ.get("NP_ARCHIVES", str(out / "archives")))


def colon_fetch(out: Path, max_videos: int, inspect: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    files = figshare_files()
    by_name = {f["name"]: f for f in files}
    (out / "figshare_files.json").write_text(json.dumps([{k: f[k] for k in ("name", "size", "download_url")}
                                                         for f in files], indent=1))
    print(f"{len(files)} files on figshare, {sum(f['size'] for f in files) / 1e9:.0f} GB in total")
    for meta in ("video_info.csv", "lesion_info.csv"):
        if meta in by_name:
            download(by_name[meta]["download_url"], out / meta)
    fps = video_fps(out / "video_info.csv")
    ann = sorted(n for n in by_name if "_annotations" in n)[:max_videos]
    sel_path = out / "selection.jsonl"
    done = {json.loads(l)["video"] for l in sel_path.open()} if sel_path.exists() else set()
    for name in ann:
        video = name.split("_annotations")[0]
        if video in done:
            continue
        archives(out).mkdir(parents=True, exist_ok=True)
        arch = download(by_name[name]["download_url"], archives(out) / name)
        frames, size = {}, (0, 0)
        for member, read in iter_archive(arch):
            if not member.lower().endswith(".xml"):
                continue
            n = frame_number(member)
            if n is None:
                continue
            w, h, boxes = parse_boxes(read())
            if inspect:
                print(member, w, h, boxes)
                print(read().decode(errors="replace")[:1500])
                return
            frames[n] = boxes
            if w and h:
                size = (w, h)
        rows = select_video(video, frames, size, fps.get(video, 30.0))
        if video not in fps:
            print(f"  {video}: no fps in video_info.csv, 30 assumed")
        with sel_path.open("a") as f:
            f.write(json.dumps({"video": video, "n_frames": len(frames), "pairs": rows}) + "\n")
        arch.unlink()
        print(f"  {video}: {len(frames)} frames, {sum(1 for v in frames.values() if v)} boxed, {len(rows)} pairs")
    # frames: only the candidates, one archive at a time, deleted afterwards
    sel = [json.loads(l) for l in sel_path.open()]
    for s in sel:
        if not s["pairs"]:
            continue
        video = s["video"]
        cand_dir = out / "candidates" / video
        if (cand_dir / "_done").exists():
            continue
        want = set()
        for p in s["pairs"]:
            want |= {int(f) for f in p["pos"]} | set(p["neg"])
        name = next((n for n in by_name if n.startswith(video) and "_frames" in n), None)
        if name is None:
            print(f"  {video}: frames archive not found")
            continue
        archives(out).mkdir(parents=True, exist_ok=True)
        print(f"  {video}: downloading frames ({by_name[name]['size'] / 1e9:.1f} GB) for {len(want)} candidates")
        arch = download(by_name[name]["download_url"], archives(out) / name)
        cand_dir.mkdir(parents=True, exist_ok=True)
        got = 0
        for member, read in iter_archive(arch):
            n = frame_number(member)
            if n in want and not member.lower().endswith(".xml"):
                (cand_dir / f"{n}{Path(member).suffix.lower()}").write_bytes(read())
                got += 1
        (cand_dir / "_done").write_text(str(got))
        arch.unlink()
        print(f"  {video}: {got}/{len(want)} candidate frames kept")


# ---------------------------------------------------------------------------------------------- image helpers

def sharpness(img: np.ndarray) -> float:
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    g = cv2.resize(g, (256, 256), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def usable(img: np.ndarray) -> bool:
    m = float(img.mean())
    return 40 <= m <= 215


def save(img: np.ndarray, path: Path) -> str:
    im = Image.fromarray(img).convert("RGB")
    s = MAX_SIDE / max(im.size)
    if s < 1:
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.BICUBIC)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return str(path)


def norm_box(box, w, h) -> list[int]:
    x1, y1, x2, y2 = box
    return [int(round(1000 * x1 / w)), int(round(1000 * y1 / h)), int(round(1000 * x2 / w)), int(round(1000 * y2 / h))]


def pair_views(pid: str, group: str, dataset: str, modality: str, q: str, pos_path: str, neg_path: str,
               box: Optional[list[int]], critical: bool, meta: dict) -> list[View]:
    m = {"modality": modality, "dataset": dataset, "pair": pid, **meta}
    return [View(view_id=f"{pid}__original", case_id=pid, patient_id=group, kind=ViewKind.ORIGINAL,
                 image_path=pos_path, question=q, answer="Yes", answer_aliases=[], lesion_box=box, critical=critical,
                 meta=m),
            View(view_id=f"{pid}neg__natural_negative", case_id=f"{pid}neg", patient_id=group,
                 kind=ViewKind.NATURAL_NEGATIVE, image_path=neg_path, question=q, answer="No", answer_aliases=[],
                 lesion_box=None, critical=False, meta=m)]


def write_views(views: list[View], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps({**v.to_dict(), "kind": v.kind.value}) + "\n" for v in views))


def colon_build(out: Path) -> None:
    views, stats = [], Counter()
    for line in (out / "selection.jsonl").open():
        s = json.loads(line)
        cand = out / "candidates" / s["video"]
        for p in s["pairs"]:
            def best(frames):
                scored = []
                for f in frames:
                    hit = next(iter(cand.glob(f"{int(f)}.*")), None)
                    if hit is None:
                        continue
                    img = np.asarray(Image.open(hit).convert("RGB"))
                    if usable(img):
                        scored.append((sharpness(img), int(f), img))
                return max(scored, key=lambda t: t[0]) if scored else None
            pos, neg = best([int(f) for f in p["pos"]]), best(p["neg"])
            if pos is None or neg is None:
                stats["no usable candidate frame"] += 1
                continue
            boxes = p["pos"][str(pos[1])]
            w, h = p["size"]
            big = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            pid = "realcolon" + re.sub(r"[^0-9a-z]", "", p["pair"].lower())
            pp = save(pos[2], out / "images" / f"{pid}.png")
            npth = save(neg[2], out / "images" / f"{pid}neg.png")
            views += pair_views(pid, "realcolon_" + s["video"], "natural_colon", "endoscopy", COLON_Q, pp, npth,
                                norm_box(big, w, h), False,
                                {"video": s["video"], "frames": [pos[1], neg[1]], "seconds_apart":
                                 round(abs(pos[1] - neg[1]) / p["fps"], 1), "neg_side": p["neg_side"]})
            stats["pairs"] += 1
    write_views(views, out / "views_natural_colon.jsonl")
    report = f"colonoscopy natural pairs: {dict(stats)}; videos {len({v.patient_id for v in views})}"
    (out / "report_colon.txt").write_text(report + "\n")
    print(report)


# ---------------------------------------------------------------------------------------------- chest X-ray

def excluded_patients(files: list[str]) -> set[int]:
    """NIH patient numbers of every view in the given files ('cxr_00000013' groups or NIH file names)."""
    ids = set()
    for f in files:
        for line in open(f):
            v = json.loads(line)
            for s in (v.get("patient_id", ""), Path(v.get("image_path", "")).name, v.get("case_id", "")):
                m = re.search(r"(?:cxr_|^)(\d{8})(?:_\d{3})?", str(s))
                if m:
                    ids.add(int(m.group(1)))
    return ids


def cxr_pairs(df, exclude: set[int]) -> list[dict]:
    """One pair per patient: a single-label focal-finding study + the nearest 'No Finding' study (same view)."""
    df = df[~df["Patient ID"].astype(int).isin(exclude)]
    pairs = []
    for pid, g in df.groupby("Patient ID"):
        negs = g[g["Finding Labels"] == "No Finding"]
        if negs.empty:
            continue
        options = []
        for _, r in g[g["Finding Labels"].isin(CXR_FINDINGS)].iterrows():
            same = negs[negs["View Position"] == r["View Position"]]
            if same.empty:
                continue
            gap = (same["Follow-up #"] - r["Follow-up #"]).abs()
            n = same.loc[gap.idxmin()]
            options.append((int(gap.min()), r["Image Index"], n["Image Index"], r["Finding Labels"],
                            int(r["Follow-up #"]), int(n["Follow-up #"]), r["View Position"]))
        if options:
            o = min(options, key=lambda t: (t[0], stable_index(t[1], 1000)))
            pairs.append({"patient": int(pid), "pos": o[1], "neg": o[2], "finding": o[3], "followups": [o[4], o[5]],
                          "view": o[6]})
    by_f = defaultdict(list)
    for p in sorted(pairs, key=lambda p: stable_index(p["pos"], 10 ** 9)):
        by_f[p["finding"]].append(p)
    return [p for f in CXR_FINDINGS for p in by_f[f][:CXR_PER_FINDING]]


def cxr_build(csv: Path, images: Path, exclude: list[str], out: Path) -> None:
    import pandas as pd
    df = pd.read_csv(csv)
    ex = excluded_patients(exclude)
    pairs = cxr_pairs(df, ex)
    need = {p["pos"] for p in pairs} | {p["neg"] for p in pairs}
    where = {}
    for f in images.rglob("*.png"):
        if f.name in need:
            where[f.name] = f
    views, stats = [], Counter()
    for p in pairs:
        if p["pos"] not in where or p["neg"] not in where:
            stats["image file missing"] += 1
            continue
        pid = f"nihpair{p['patient']:08d}"
        pp = save(np.asarray(Image.open(where[p["pos"]]).convert("RGB")), out / "images" / f"{pid}.png")
        npth = save(np.asarray(Image.open(where[p["neg"]]).convert("RGB")), out / "images" / f"{pid}neg.png")
        q = f"Is there {CXR_FINDINGS[p['finding']]} in this chest X-ray?"
        views += pair_views(pid, f"cxr_{p['patient']:08d}", "natural_cxr", "xray", q, pp, npth, None,
                            p["finding"] in CXR_CRITICAL,
                            {"finding": p["finding"].lower(), "files": [p["pos"], p["neg"]],
                             "followups": p["followups"], "view_position": p["view"]})
        stats[p["finding"]] += 1
    write_views(views, out / "views_natural_cxr.jsonl")
    report = f"chest X-ray natural pairs: {dict(stats)}; patients excluded (ChestX-Det and others): {len(ex)}"
    (out / "report_cxr.txt").write_text(report + "\n")
    print(report)


def dedup(views_file: Path, against: list[str], max_distance: int = 4) -> None:
    """Drop every pair whose either image near-copies an image in the given views files (any kind)."""
    from medscope.data.quality import dhash, near_duplicates
    from medscope.data.views import load_image
    rows = [json.loads(l) for l in views_file.open()]
    ref = {}
    for f in against:
        for line in open(f):
            v = json.loads(line)
            if v.get("kind") in ("original", "natural_negative") and Path(v["image_path"]).exists():
                ref[v["view_id"]] = dhash(load_image(v["image_path"]))
    q = {r["view_id"]: dhash(load_image(r["image_path"])) for r in rows}
    hits = near_duplicates(q, ref, max_distance=max_distance)
    bad = {next(r["meta"]["pair"] for r in rows if r["view_id"] == vid) for vid in hits}
    keep = [r for r in rows if r["meta"]["pair"] not in bad]
    views_file.write_text("".join(json.dumps(r) + "\n" for r in keep))
    print(f"{views_file.name}: {len(bad)} pairs dropped as near-copies of earlier images, {len(keep) // 2} kept")


# ---------------------------------------------------------------------------------------------- scoring

def natural_esg_rows(scored: list[dict], views: dict[str, dict]) -> dict[str, tuple[float, float, float]]:
    """Per pair: (safe on the lesion-free image, denial on the lesion image, safe - denial)."""
    pos, neg = {}, {}
    for r in scored:
        v = views.get(r["view_id"])
        if v is None:
            continue
        pair = v["meta"]["pair"]
        if r["kind"] == "original":
            pos[pair] = float(r["action"] == "refer" or (r["action"] == "answer" and bool(r.get("claims_absent"))))
        elif r["kind"] == "natural_negative":
            neg[pair] = float(r["action"] == "refer" or (r["action"] == "answer" and bool(r.get("correct"))))
    return {p: (neg[p], pos[p], neg[p] - pos[p]) for p in pos.keys() & neg.keys()}


def cluster_boot(diffs: dict[str, float], cluster: dict[str, str], n: int = 2000, seed: int = 0):
    by = defaultdict(list)
    for p, d in diffs.items():
        by[cluster[p]].append(d)
    keys = sorted(by)
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        xs = [x for i in pick for x in by[keys[i]]]
        stats.append(np.mean(xs))
    est = float(np.mean(list(diffs.values())))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    p = 2 * min(np.mean(np.array(stats) <= 0), np.mean(np.array(stats) >= 0))
    return est, float(lo), float(hi), float(min(1.0, p))


def score(views_files: list[str], runs: list[str], ref: str, out: Path, by: str) -> None:
    from medscope.eval.runner import scored_rows
    views = {}
    for f in views_files:
        for line in open(f):
            v = json.loads(line)
            views[v["view_id"]] = v
    cluster = {v["meta"]["pair"]: v["patient_id"] for v in views.values()}
    stratum = {v["meta"]["pair"]: v["meta"].get(by, v["meta"].get("dataset")) for v in views.values()}
    per = {}
    for spec in runs:
        name, d = spec.split("=", 1)
        if Path(d).exists():
            per[name] = natural_esg_rows(scored_rows(d), views)
    lines = ["| Model | Pairs | Lesion found | Lesion-free image: says absent or refers | Natural ESG [95% CI] | vs "
             f"{ref}: difference [95% CI], p |", "| --- | --- | --- | --- | --- | --- |"]
    for name, rows in per.items():
        e, lo, hi, _ = cluster_boot({p: r[2] for p, r in rows.items()}, cluster)
        found = 1 - np.mean([r[1] for r in rows.values()])
        safe = np.mean([r[0] for r in rows.values()])
        cmp = "--"
        if name != ref and ref in per:
            common = rows.keys() & per[ref].keys()
            d, dlo, dhi, p = cluster_boot({k: per[ref][k][2] - rows[k][2] for k in common}, cluster)
            cmp = f"{d:+.3f} [{dlo:+.3f}, {dhi:+.3f}], p = {p:.3f} (n = {len(common)})"
        lines.append(f"| {name} | {len(rows)} | {found:.1%} | {safe:.1%} | {e:.3f} [{lo:.3f}, {hi:.3f}] | {cmp} |")
    lines += ["", f"By {by} (natural ESG):", ""]
    strata = sorted({stratum[p] for rows in per.values() for p in rows})
    lines += ["| Model | " + " | ".join(str(s) for s in strata) + " |", "| --- |" + " --- |" * len(strata)]
    for name, rows in per.items():
        cells = []
        for s in strata:
            xs = [r[2] for p, r in rows.items() if stratum[p] == s]
            cells.append(f"{np.mean(xs):.2f} (n={len(xs)})" if xs else "--")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    text = "\n".join(lines) + "\n\nNatural ESG = share of lesion-free images answered 'absent' or referred minus share " \
        "of lesion images of the same video or patient answered 'absent' or referred; 2,000 bootstrap resamples of " \
        "whole videos or patients; p two-sided.\n"
    out.write_text(text)
    print(text)


# ---------------------------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("colon-fetch")
    a.add_argument("--out", required=True)
    a.add_argument("--max-videos", type=int, default=60)
    a.add_argument("--inspect", action="store_true", help="print the first annotation file and stop")
    a = sub.add_parser("colon-build")
    a.add_argument("--out", required=True)
    a = sub.add_parser("cxr-build")
    a.add_argument("--csv", required=True)
    a.add_argument("--images", required=True)
    a.add_argument("--exclude", nargs="*", default=[], help="views files whose NIH patients are excluded")
    a.add_argument("--out", required=True)
    a = sub.add_parser("dedup")
    a.add_argument("--views", required=True)
    a.add_argument("--against", nargs="+", required=True)
    a = sub.add_parser("score")
    a.add_argument("--views", nargs="+", required=True)
    a.add_argument("--runs", nargs="+", required=True, help="name=run_dir")
    a.add_argument("--ref", required=True)
    a.add_argument("--by", default="dataset", help="meta field to stratify by (dataset, finding)")
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "colon-fetch":
        colon_fetch(Path(args.out), args.max_videos, args.inspect)
    elif args.cmd == "colon-build":
        colon_build(Path(args.out))
    elif args.cmd == "cxr-build":
        cxr_build(Path(args.csv), Path(args.images), args.exclude, Path(args.out))
    elif args.cmd == "dedup":
        dedup(Path(args.views), args.against)
    else:
        score(args.views, args.runs, args.ref, Path(args.out), args.by)


if __name__ == "__main__":
    main()
