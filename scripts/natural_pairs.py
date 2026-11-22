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
    # Amendment 6 (v5): training frames from every REAL-Colon video, three folds, context frames for the R9 pairs
    python scripts/natural_pairs.py colon-train --r9 DIR --out TRAIN_DIR
    python scripts/natural_pairs.py score --views V.jsonl --runs v5cv=FOLD0+FOLD1+FOLD2 ... --ref v5cv --boxes --out R.md
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


# ---------------------------------------------------------------------------------------------- v5 (Amendment 6)
# Natural pairs for TRAINING, and context-matched lesion-free frames for the R9 pairs. Fixed in Amendment 6 before any
# training frame was drawn.

FOLDS = 3                  # videos 1-5, 6-10, 11-15 of each cohort
TRAIN_TRACKS = 10          # the ten longest tracks of a video
TRAIN_SEG_S = 2.0          # one lesion frame per 2 s of track ...
TRAIN_PER_TRACK = 6        # ... at most six per track
TRAIN_MIN_BOX = 0.005      # the lesion frame's largest box covers at least 0.5% of the frame
TRAIN_CAND = 6             # candidates per kept frame; the sharpest usable one is kept
CLOSE_MIN_S = 3.0          # context-matched lesion-free frame: this far from the nearest boxed frame ...
CLOSE_MAX_S = 10.0         # ... and no farther than this (and within this distance of the track's ends)
FAR_CLEAR_S = 30.0         # "far" lesion-free frames: at least this far from any boxed frame
NEG_ONLY = 12              # lesion-free frames from a video without any track


def fold_of(video: str) -> int:
    """'003-012' -> 2: videos 1-5, 6-10, 11-15 of each cohort."""
    m = re.search(r"(\d+)\D+(\d+)", video)
    if m is None:
        raise ValueError(f"cannot read a video number from {video!r}")
    return min(FOLDS - 1, max(0, (int(m.group(2)) - 1) // 5))


def _distances(all_frames: np.ndarray, boxed: np.ndarray) -> np.ndarray:
    """Distance (in frames) from every frame to the nearest boxed frame (inf if the video has none)."""
    if len(boxed) == 0:
        return np.full(len(all_frames), np.inf)
    i = np.searchsorted(boxed, all_frames)
    left = np.where(i > 0, np.abs(all_frames - boxed[np.clip(i - 1, 0, len(boxed) - 1)]), np.inf)
    right = np.where(i < len(boxed), np.abs(boxed[np.clip(i, 0, len(boxed) - 1)] - all_frames), np.inf)
    return np.minimum(left, right)


def _slots(eligible: list[int], n: int, cand: int, used: set[int]) -> list[list[int]]:
    """Cut the unused eligible frames into n consecutive parts; `cand` evenly spaced candidates from each."""
    free = [int(f) for f in eligible if int(f) not in used]
    if not free or n <= 0:
        return []
    out = []
    for part in np.array_split(np.array(free), min(n, len(free))):
        c = even([int(f) for f in part], cand)
        used.update(c)
        out.append(c)
    return out


def select_training(video: str, frames: dict[int, list], size: tuple[int, int], fps: float) -> list[dict]:
    """Training slots of one video (pure, testable). Each slot lists candidate frames; the sharpest usable one becomes
    a training image. kind "pos" = a polyp frame; "near", "context", "far" = lesion-free frames. Candidate sets of
    different slots never share a frame."""
    w, h = size
    all_frames = np.array(sorted(frames))
    boxed = np.array([f for f in all_frames if frames[f]])
    dist = _distances(all_frames, boxed)
    used: set[int] = set()
    slots: list[dict] = []
    tracks = sorted(sorted(tracks_from(boxed, fps), key=lambda t: (-(t[1] - t[0]), t[0]))[:TRAIN_TRACKS])
    for k, (a, b) in enumerate(tracks):
        ok = [int(f) for f in all_frames[(all_frames >= a) & (all_frames <= b)]
              if frames[f] and w and h
              and max((x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in frames[f]) / (w * h) >= TRAIN_MIN_BOX]
        n = min(TRAIN_PER_TRACK, max(1, int((b - a + 1) / fps / TRAIN_SEG_S)))
        for j, c in enumerate(_slots(ok, n, TRAIN_CAND, used)):
            slots.append({"id": f"{video}_t{k}s{j}", "kind": "pos", "cands": c})
    n_pos = len(slots)
    clear, window = NEG_CLEAR_S * fps, NEG_WINDOW_S * fps
    lo, hi = CLOSE_MIN_S * fps, CLOSE_MAX_S * fps
    for k, (a, b) in enumerate(tracks):
        if len([s for s in slots if s["kind"] != "pos"]) >= n_pos:
            break
        before = all_frames[(all_frames >= a - window) & (all_frames < a) & (dist >= clear)].tolist()
        after = all_frames[(all_frames > b) & (all_frames <= b + window) & (dist >= clear)].tolist()
        for c in _slots(before if len(before) >= 3 else after, 1, TRAIN_CAND, used):
            slots.append({"id": f"{video}_t{k}near", "kind": "near", "cands": c})
        ctx = (dist >= lo) & (dist <= hi) & (((all_frames >= a - hi) & (all_frames < a))
                                             | ((all_frames > b) & (all_frames <= b + hi)))
        for c in _slots(all_frames[ctx].tolist(), 1, TRAIN_CAND, used):
            slots.append({"id": f"{video}_t{k}ctx", "kind": "context", "cands": c})
    n_far = max(0, n_pos - (len(slots) - n_pos)) if len(tracks) else NEG_ONLY
    for j, c in enumerate(_slots(all_frames[dist >= FAR_CLEAR_S * fps].tolist(), n_far, TRAIN_CAND, used)):
        slots.append({"id": f"{video}_far{j}", "kind": "far", "cands": c})
    return slots


def select_context(frames: dict[int, list], fps: float, tracks: list[tuple[int, int]]) -> list[list[int]]:
    """Per track, candidate lesion-free frames from the same stretch of the examination: within CLOSE_MAX_S of the
    track's ends and CLOSE_MIN_S to CLOSE_MAX_S from the nearest boxed frame (before the track; after it if fewer than
    3 qualify before)."""
    all_frames = np.array(sorted(frames))
    boxed = np.array([f for f in all_frames if frames[f]])
    dist = _distances(all_frames, boxed)
    lo, hi = CLOSE_MIN_S * fps, CLOSE_MAX_S * fps
    ok = (dist >= lo) & (dist <= hi)
    out = []
    for a, b in tracks:
        before = all_frames[ok & (all_frames >= a - hi) & (all_frames < a)].tolist()
        after = all_frames[ok & (all_frames > b) & (all_frames <= b + hi)].tolist()
        out.append(even([int(f) for f in (before if len(before) >= 3 else after)], N_CANDIDATES))
    return out


def read_annotations(arch: Path) -> tuple[dict[int, list], tuple[int, int]]:
    """Boxes of every frame of one annotation archive, and the frame size."""
    frames, size = {}, (0, 0)
    for member, read in iter_archive(arch):
        if not member.lower().endswith(".xml"):
            continue
        n = frame_number(member)
        if n is None:
            continue
        w, h, boxes = parse_boxes(read())
        frames[n] = boxes
        if w and h:
            size = (w, h)
    return frames, size


def shrink(img: np.ndarray) -> np.ndarray:
    im = Image.fromarray(img).convert("RGB")
    s = MAX_SIDE / max(im.size)
    if s < 1:
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.BICUBIC)
    return np.asarray(im)


def best_frames(members: Iterator[tuple[str, callable]], slot_of: dict[int, list[str]],
                seen: Optional[set] = None) -> dict[str, tuple[float, int, np.ndarray]]:
    """One pass over a video's frames: per slot, its sharpest usable candidate as (sharpness, frame number, image at
    MAX_SIDE). Sharpness and brightness are judged on the full frame, as in colon-build. `seen` collects the wanted
    frame numbers that were met (to tell a complete pass from a cut-off one)."""
    best: dict[str, tuple[float, int, np.ndarray]] = {}
    for member, read in members:
        n = frame_number(member)
        if n not in slot_of or member.lower().endswith(".xml"):
            continue
        if seen is not None:
            seen.add(n)
        img = np.asarray(Image.open(io.BytesIO(read())).convert("RGB"))
        if not usable(img):
            continue
        s, small = sharpness(img), None
        for sid in slot_of[n]:
            if sid not in best or s > best[sid][0]:
                small = shrink(img) if small is None else small
                best[sid] = (s, n, small)
    return best


def _pid(pair: str) -> str:
    return "realcolon" + re.sub(r"[^0-9a-z]", "", pair.lower())


def video_views(video: str, frames: dict[int, list], size: tuple[int, int], slots: list[dict], pairs: list[dict],
                best: dict[str, tuple[float, int, np.ndarray]], out: Path) -> tuple[list[dict], list[dict], Counter]:
    """Training views and context views of one video from the chosen frames (images written under `out`)."""
    w, h = size
    fold, group = fold_of(video), "realcolon_" + video
    train, context, stats = [], [], Counter()
    for s in slots:
        hit = best.get(s["id"])
        if hit is None:
            stats["slot without a usable frame"] += 1
            continue
        _, fno, img = hit
        vid = "rctrain" + re.sub(r"[^0-9a-z]", "", s["id"].lower())
        path = save(img, out / "images" / f"{vid}.png")
        meta = {"modality": "endoscopy", "dataset": "natural_colon_train", "video": video, "fold": fold,
                "frame": fno, "slot": s["kind"]}
        if s["kind"] == "pos":
            big = max(frames[fno], key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            v = View(view_id=f"{vid}__original", case_id=vid, patient_id=group, kind=ViewKind.ORIGINAL,
                     image_path=path, question=COLON_Q, answer="Yes", answer_aliases=[],
                     lesion_box=norm_box(big, w, h), critical=False, meta=meta)
        else:
            v = View(view_id=f"{vid}__natural_negative", case_id=vid, patient_id=group,
                     kind=ViewKind.NATURAL_NEGATIVE, image_path=path, question=COLON_Q, answer="No",
                     answer_aliases=[], lesion_box=None, critical=False, meta=meta)
        train.append(v.to_dict())
        stats[s["kind"]] += 1
    for p in pairs:
        hit = best.get("context:" + p["pair"])
        if hit is None:
            stats["pair without a context frame"] += 1
            continue
        pid = _pid(p["pair"])
        path = save(hit[2], out / "context" / f"{pid}ctx.png")
        v = View(view_id=f"{pid}ctx__natural_negative", case_id=f"{pid}ctx", patient_id=group,
                 kind=ViewKind.NATURAL_NEGATIVE, image_path=path, question=COLON_Q, answer="No", answer_aliases=[],
                 lesion_box=None, critical=False,
                 meta={"modality": "endoscopy", "dataset": "natural_colon", "pair": pid, "video": video,
                       "frames": [hit[1]], "context": True})
        context.append(v.to_dict())
        stats["context frames for R9 pairs"] += 1
    return train, context, stats


def assemble_folds(r9_views: list[dict], rows: list[dict], out: Path) -> str:
    """Write the training and test files of every fold from the per-video rows; returns the report."""
    train = [v for r in rows for v in r["train"]]
    r9_pairs = {v["meta"]["pair"] for v in r9_views}
    context = [v for r in rows for v in r["context"] if v["meta"]["pair"] in r9_pairs]

    def write(path: Path, vs: list[dict]) -> None:
        path.write_text("".join(json.dumps(v) + "\n" for v in vs))

    write(out / "views_train_all.jsonl", train)
    write(out / "views_context_colon.jsonl", context)
    write(out / "views_contextpairs_colon.jsonl", [v for v in r9_views if v["kind"] == "original"] + context)
    lines = [f"REAL-Colon training frames (Amendment 6): {len(rows)} videos, "
             f"{sum(v['kind'] == 'original' for v in train)} polyp frames, "
             f"{sum(v['kind'] != 'original' for v in train)} lesion-free frames "
             f"({dict(Counter(v['meta']['slot'] for v in train if v['kind'] != 'original'))}); "
             f"{len(context)} context frames for the {len(r9_pairs)} R9 pairs.", "",
             "| Fold | Training videos | Training polyp frames | Training lesion-free frames | Test videos | Test pairs |",
             "| --- | --- | --- | --- | --- | --- |"]
    for k in range(FOLDS):
        tr = [v for v in train if v["meta"]["fold"] != k]
        te = [v for v in r9_views if fold_of(v["meta"]["video"]) == k]
        te_ctx = [v for v in context if fold_of(v["meta"]["video"]) == k]
        shared = {v["patient_id"] for v in tr} & {v["patient_id"] for v in te + te_ctx}
        if shared:
            raise SystemExit(f"fold {k}: videos in both training and test: {sorted(shared)[:5]}")
        write(out / f"views_train_fold{k}.jsonl", tr)
        write(out / f"views_test_fold{k}.jsonl", te + te_ctx)
        lines.append(f"| {k} | {len({v['patient_id'] for v in tr})} | {sum(v['kind'] == 'original' for v in tr)} | "
                     f"{sum(v['kind'] != 'original' for v in tr)} | {len({v['patient_id'] for v in te})} | "
                     f"{sum(v['kind'] == 'original' for v in te)} |")
    return "\n".join(lines) + "\n"


def cohort_of(video: str) -> str:
    """'001-014' -> '001': the centre (cohort) of a REAL-Colon video."""
    return str(video).split("-")[0]


def assemble_centres(r9_views: list[dict], rows: list[dict], out: Path) -> str:
    """Leave-one-centre-out files (R18, Amendment 7) from the per-video rows already drawn for Amendment 6:
    for each centre, the training frames of every other centre and the R9 pairs (with their context frames) of
    that centre. Nothing is redrawn. Returns the report."""
    train = [v for r in rows for v in r["train"]]
    r9_pairs = {v["meta"]["pair"] for v in r9_views}
    context = [v for r in rows for v in r["context"] if v["meta"]["pair"] in r9_pairs]

    def write(path: Path, vs: list[dict]) -> None:
        path.write_text("".join(json.dumps(v) + "\n" for v in vs))

    centres = sorted({cohort_of(r["video"]) for r in rows})
    lines = [f"Leave-one-centre-out (Amendment 7, R18): {len(centres)} centres, {len(rows)} videos, "
             f"{len(train)} training frames already drawn (Amendment 6).", "",
             "| Centre held out | Training videos | Training polyp frames | Training lesion-free frames | Test videos | Test pairs |",
             "| --- | --- | --- | --- | --- | --- |"]
    for c in centres:
        tr = [v for v in train if cohort_of(v["meta"]["video"]) != c]
        te = [v for v in r9_views if cohort_of(v["meta"]["video"]) == c]
        te_ctx = [v for v in context if cohort_of(v["meta"]["video"]) == c]
        if {cohort_of(v["meta"]["video"]) for v in tr} & {c} or {v["patient_id"] for v in tr} & {v["patient_id"] for v in te + te_ctx}:
            raise SystemExit(f"centre {c}: in both training and test")
        write(out / f"views_train_loco{c}.jsonl", tr)
        write(out / f"views_test_loco{c}.jsonl", te + te_ctx)
        lines.append(f"| {c} | {len({v['patient_id'] for v in tr})} | {sum(v['kind'] == 'original' for v in tr)} | "
                     f"{sum(v['kind'] != 'original' for v in tr)} | {len({v['patient_id'] for v in te})} | "
                     f"{sum(v['kind'] == 'original' for v in te)} |")
    return "\n".join(lines) + "\n"


def colon_loco(r9_views_file: Path, folder: Path) -> None:
    rows = [json.loads(l) for l in (folder / "videos.jsonl").open() if l.strip()]
    r9_views = [json.loads(l) for l in r9_views_file.open() if l.strip()]
    report = assemble_centres(r9_views, rows, folder)
    (folder / "report_loco.txt").write_text(report)
    print(report)


def lazy_members(path: Path) -> Iterator[tuple[str, callable]]:
    """(member name, read()) of a frames archive; a member's bytes are read only when read() is called, which must
    happen before the next member is taken (as best_frames does)."""
    if zipfile.is_zipfile(path):
        yield from iter_archive(path)
        return
    with tarfile.open(path, "r|*", bufsize=1 << 20) as t:
        for m in t:
            if m.isfile():
                yield m.name, (lambda m=m: t.extractfile(m).read())


def stream_members(url: str) -> Iterator[tuple[str, callable]]:
    """lazy_members() straight from the download, without writing the archive to disk (tar archives only)."""
    import requests
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with tarfile.open(fileobj=r.raw, mode="r|*", bufsize=1 << 20) as t:
            for m in t:
                if m.isfile():
                    yield m.name, (lambda m=m: t.extractfile(m).read())


_DISK = __import__("threading").Lock()      # at most one archive on local disk at a time


def fetch(url: str, dest: Path, tries: int = 3) -> Path:
    """download(), tried again after a dropped connection."""
    import time
    for attempt in range(tries):
        try:
            return download(url, dest)
        except Exception as e:  # noqa: BLE001 - network errors of any kind
            if attempt == tries - 1:
                raise
            print(f"  download of {dest.name} failed ({type(e).__name__}: {str(e)[:100]}); trying again", flush=True)
            time.sleep(20 * (attempt + 1))


def train_video(video: str, by_name: dict, fps: float, pairs: list[dict], out: Path) -> dict:
    """Everything for one video: annotations, slots, one pass over its frames archive, images and views."""
    ann = next(n for n in by_name if n.startswith(video) and "_annotations" in n)
    archives(out).mkdir(parents=True, exist_ok=True)
    arch = fetch(by_name[ann]["download_url"], archives(out) / ann)
    frames, size = read_annotations(arch)
    arch.unlink()
    slots = select_training(video, frames, size, fps)
    slot_of = defaultdict(list)
    for s in slots:
        for c in s["cands"]:
            slot_of[c].append(s["id"])
    for p, cands in zip(pairs, select_context(frames, fps, [tuple(p["track"]) for p in pairs])):
        for c in cands:
            slot_of[c].append("context:" + p["pair"])
    fname = next((n for n in by_name if n.startswith(video) and "_frames" in n), None)
    if fname is None or not slot_of:
        why = "frames archive not found" if fname is None else "no frame to draw"
        return {"video": video, "fold": fold_of(video), "train": [], "context": [], "stats": {why: 1}}
    print(f"  {video}: fold {fold_of(video)}, {len(slots)} training slots, {len(pairs)} R9 pairs; downloading frames "
          f"({by_name[fname]['size'] / 1e9:.1f} GB)", flush=True)
    best = None
    if os.environ.get("NP_STREAM", "1") == "1" and ".tar" in fname:
        seen: set = set()
        try:      # read the archive as it downloads; nothing is written to disk
            best = best_frames(stream_members(by_name[fname]["download_url"]), slot_of, seen)
            if len(seen) < len(slot_of):
                print(f"  {video}: the stream held {len(seen)} of {len(slot_of)} wanted frames; reading it from disk "
                      "instead", flush=True)
                best = None
        except Exception as e:  # noqa: BLE001 - a dropped connection or a cut-off archive
            print(f"  {video}: streaming failed ({type(e).__name__}: {str(e)[:100]}); downloading the archive instead",
                  flush=True)
    if best is None:
        with _DISK:
            arch = fetch(by_name[fname]["download_url"], archives(out) / fname)
            best = best_frames(lazy_members(arch), slot_of)
            arch.unlink()
    train, context, stats = video_views(video, frames, size, slots, pairs, best, out)
    return {"video": video, "fold": fold_of(video), "train": train, "context": context, "stats": dict(stats)}


def colon_train(r9: Path, out: Path, max_videos: int, workers: int = 3) -> None:
    """Amendment 6: training frames from every video, and context-matched lesion-free frames for the R9 pairs.
    Each video is handled on its own (annotations, then one pass over its frames archive, read as it downloads),
    `workers` at a time; rerunning resumes with the videos not yet done."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out.mkdir(parents=True, exist_ok=True)
    files = figshare_files()
    by_name = {f["name"]: f for f in files}
    if not (r9 / "video_info.csv").exists():
        download(by_name["video_info.csv"]["download_url"], r9 / "video_info.csv")
    fps = video_fps(r9 / "video_info.csv")
    r9_pairs = {}
    for line in (r9 / "selection.jsonl").open():
        s = json.loads(line)
        r9_pairs[s["video"]] = s["pairs"]
    rows_path = out / "videos.jsonl"
    done = {json.loads(l)["video"] for l in rows_path.open()} if rows_path.exists() else set()
    videos = [n.split("_annotations")[0] for n in sorted(n for n in by_name if "_annotations" in n)[:max_videos]]
    todo = [v for v in videos if v not in done]
    print(f"{len(videos)} videos, {len(done & set(videos))} already done, "
          f"{sum(f['size'] for n, f in by_name.items() if '_frames' in n and n.split('_frames')[0] in todo) / 1e9:.0f} GB to read")
    ex = ThreadPoolExecutor(max(1, workers))
    try:
        futures = [ex.submit(train_video, v, by_name, fps.get(v, 30.0), r9_pairs.get(v, []), out) for v in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            with rows_path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"  {row['video']} done ({i}/{len(todo)}): {row['stats']}", flush=True)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    rows = sorted((json.loads(l) for l in rows_path.open()), key=lambda r: r["video"]) if rows_path.exists() else []
    rows = [r for r in rows if r["video"] in set(videos)]
    if len(rows) < len(videos):
        raise SystemExit(f"{len(rows)} of {len(videos)} videos done: run this step again to finish the rest.")
    r9_views = [json.loads(l) for l in (r9 / "views_natural_colon.jsonl").open()]
    report = assemble_folds(r9_views, rows, out)
    (out / "report_train.txt").write_text(report)
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


def dedup(views_file: Path, against: list[str], max_distance: int = 4, min_correlation: float = 0.98) -> None:
    """Drop every pair whose either image near-copies an image in the given views files (any kind)."""
    from medscope.data.quality import correlation, dhash, near_duplicates
    from medscope.data.views import load_image
    rows = [json.loads(l) for l in views_file.open()]
    ref, ref_path = {}, {}
    for f in against:
        for line in open(f):
            v = json.loads(line)
            if v.get("kind") in ("original", "natural_negative") and Path(v["image_path"]).exists():
                ref[v["view_id"]] = dhash(load_image(v["image_path"]))
                ref_path[v["view_id"]] = v["image_path"]
    q = {r["view_id"]: dhash(load_image(r["image_path"])) for r in rows}
    q_path = {r["view_id"]: r["image_path"] for r in rows}
    # a coarse hash match between two chest X-rays of different patients is common, so every match is confirmed by
    # pixel correlation (>= 0.98, as in check_views.py) before a pair is dropped
    confirm = lambda qid, rid: correlation(load_image(q_path[qid]), load_image(ref_path[rid])) >= min_correlation  # noqa: E731
    hits = near_duplicates(q, ref, max_distance=max_distance, confirm=confirm)
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


def pooled_rows(dirs: str) -> Optional[list[dict]]:
    """Scored rows of one run, or of several runs joined with '+' (cross-validation folds, or a run on the lesion
    frames plus a run on other lesion-free frames). None if any of them is missing."""
    from medscope.eval.runner import scored_rows
    parts = dirs.split("+")
    if not all(Path(d).exists() for d in parts):
        return None
    rows = {}
    for d in parts:
        for r in scored_rows(d):
            rows[r["view_id"]] = r
    return list(rows.values())


def stratum_of(view: dict, by: str):
    m = view["meta"]
    if by == "cohort" and "video" in m:
        return "cohort " + str(m["video"]).split("-")[0]
    if by == "fold" and "video" in m:
        return f"fold {fold_of(str(m['video']))}"
    return m.get(by, m.get("dataset"))


def grounded(scored: list[dict], views: dict[str, dict], min_iou: float = 0.3) -> tuple[int, int, int]:
    """(lesion images, called present, called present with a box of IoU >= min_iou against the annotated lesion)."""
    n = present = hit = 0
    for r in scored:
        v = views.get(r["view_id"])
        if v is None or r["kind"] != "original":
            continue
        n += 1
        if r["action"] == "answer" and not r.get("claims_absent"):
            present += 1
            hit += float(r.get("iou") or 0) >= min_iou
    return n, present, hit


def score(views_files: list[str], runs: list[str], ref: str, out: Path, by: str, with_boxes: bool = False) -> None:
    views = {}
    for f in views_files:
        for line in open(f):
            v = json.loads(line)
            views[v["view_id"]] = v
    cluster = {v["meta"]["pair"]: v["patient_id"] for v in views.values()}
    stratum = {v["meta"]["pair"]: stratum_of(v, by) for v in views.values()}
    per, raw = {}, {}
    for spec in runs:
        name, d = spec.split("=", 1)
        rows = pooled_rows(d)
        if rows is None:
            print(f"  {name}: results missing ({d}), left out")
            continue
        raw[name] = rows
        per[name] = natural_esg_rows(rows, views)
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
    if with_boxes:
        lines += ["", "Grounded detection (lesion images called present, and with a box of IoU >= 0.3 against the "
                  "annotated lesion):", "", "| Model | Lesion images | Called present | Present with a correct box |",
                  "| --- | --- | --- | --- |"]
        for name, rows in raw.items():
            n, present, hit = grounded(rows, views)
            lines.append(f"| {name} | {n} | {present} ({present / max(1, n):.1%}) | {hit} ({hit / max(1, n):.1%}) |")
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
    a.add_argument("--by", default="dataset", help="meta field to stratify by (dataset, finding), or cohort / fold")
    a.add_argument("--boxes", action="store_true", help="add grounded detection (present with a box of IoU >= 0.3)")
    a.add_argument("--out", required=True)
    a = sub.add_parser("colon-train")
    a.add_argument("--r9", required=True, help="the R9 colonoscopy folder (selection.jsonl, views_natural_colon.jsonl)")
    a.add_argument("--out", required=True)
    a.add_argument("--max-videos", type=int, default=60)
    a.add_argument("--workers", type=int, default=3, help="videos handled at the same time")
    a = sub.add_parser("colon-loco", help="leave-one-centre-out files from the frames colon-train drew (R18)")
    a.add_argument("--r9", required=True, help="views_natural_colon.jsonl")
    a.add_argument("--dir", required=True, help="the colon_train folder (videos.jsonl)")
    args = ap.parse_args()
    if args.cmd == "colon-fetch":
        colon_fetch(Path(args.out), args.max_videos, args.inspect)
    elif args.cmd == "colon-build":
        colon_build(Path(args.out))
    elif args.cmd == "cxr-build":
        cxr_build(Path(args.csv), Path(args.images), args.exclude, Path(args.out))
    elif args.cmd == "dedup":
        dedup(Path(args.views), args.against)
    elif args.cmd == "colon-train":
        colon_train(Path(args.r9), Path(args.out), args.max_videos, args.workers)
    elif args.cmd == "colon-loco":
        colon_loco(Path(args.r9), Path(args.dir))
    else:
        score(args.views, args.runs, args.ref, Path(args.out), args.by, args.boxes)


if __name__ == "__main__":
    main()
