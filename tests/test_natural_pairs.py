"""Natural-pair selection (scripts/natural_pairs.py, Amendment 4): track finding, candidate frames, CXR pairing, scoring."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("natural_pairs", ROOT / "scripts" / "natural_pairs.py")
np_ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(np_)


def video(fps=10, n=2000, polyp=(1000, 1200)):
    frames = {f: [] for f in range(n)}
    for f in range(*polyp):
        frames[f] = [(100, 100, 300, 300)]            # 4% of a 1000x1000 frame
    return frames


def test_select_video_pairs_polyp_with_clear_frame_before():
    rows = np_.select_video("001-001", video(), (1000, 1000), fps=10)
    assert len(rows) == 1
    r = rows[0]
    assert r["neg_side"] == "before"
    pos = [int(f) for f in r["pos"]]
    assert all(1049 <= f <= 1150 for f in pos)                       # middle half of the track
    assert all(1000 - 300 <= f <= 1000 - 100 for f in r["neg"])  # 10-30 s before, never near a box
    assert len(pos) <= np_.N_CANDIDATES and len(r["neg"]) <= np_.N_CANDIDATES


def test_select_video_skips_small_boxes_and_short_tracks():
    frames = video()
    for f in range(1000, 1200):
        frames[f] = [(0, 0, 50, 50)]                    # 0.25% of the frame
    assert np_.select_video("v", frames, (1000, 1000), fps=10) == []
    frames = video(polyp=(1000, 1005))                  # 0.5 s
    assert np_.select_video("v", frames, (1000, 1000), fps=10) == []


def test_negative_after_track_when_none_before():
    rows = np_.select_video("v", video(polyp=(50, 400)), (1000, 1000), fps=10)
    assert rows and rows[0]["neg_side"] == "after"
    assert all(399 + 100 <= f <= 399 + 300 for f in rows[0]["neg"])  # track ends at 399


def test_parse_boxes_voc_style():
    xml = b"<annotation><size><width>1352</width><height>1080</height></size><object><name>polyp</name>" \
          b"<bndbox><xmin>10</xmin><ymin>20</ymin><xmax>110</xmax><ymax>220</ymax></bndbox></object></annotation>"
    assert np_.parse_boxes(xml) == (1352, 1080, [(10.0, 20.0, 110.0, 220.0)])
    assert np_.parse_boxes(b"<annotation><size><width>5</width><height>5</height></size></annotation>")[2] == []


def test_cxr_pairs_same_view_nearest_followup_and_exclusion():
    df = pd.DataFrame([
        ("00000001_000.png", "No Finding", 0, 1, "PA"),
        ("00000001_001.png", "Pneumothorax", 1, 1, "PA"),
        ("00000001_002.png", "No Finding", 2, 1, "AP"),
        ("00000002_000.png", "Nodule|Mass", 0, 2, "PA"),     # two labels: not used
        ("00000002_001.png", "No Finding", 1, 2, "PA"),
        ("00000003_000.png", "Effusion", 0, 3, "PA"),
        ("00000003_001.png", "No Finding", 1, 3, "PA"),
    ], columns=["Image Index", "Finding Labels", "Follow-up #", "Patient ID", "View Position"])
    pairs = np_.cxr_pairs(df, exclude={3})
    assert [(p["pos"], p["neg"]) for p in pairs] == [("00000001_001.png", "00000001_000.png")]


def test_natural_esg_rows_and_views_load(tmp_path):
    from medscope.eval.runner import load_views
    vs = np_.pair_views("p1", "g1", "natural_colon", "endoscopy", np_.COLON_Q, "a.png", "b.png", [1, 2, 3, 4], False, {})
    np_.write_views(vs, tmp_path / "v.jsonl")
    loaded = load_views(tmp_path / "v.jsonl")
    assert [v.kind.value for v in loaded] == ["original", "natural_negative"]
    views = {json.loads(l)["view_id"]: json.loads(l) for l in (tmp_path / "v.jsonl").open()}
    scored = [{"view_id": "p1__original", "kind": "original", "action": "answer", "claims_absent": False},
              {"view_id": "p1neg__natural_negative", "kind": "natural_negative", "action": "answer", "correct": True}]
    assert np_.natural_esg_rows(scored, views) == {"p1": (1.0, 0.0, 1.0)}
    est, lo, hi, p = np_.cluster_boot({"a": 1.0, "b": 0.0, "c": 1.0}, {"a": "x", "b": "y", "c": "z"}, n=200)
    assert abs(est - 2 / 3) < 1e-9 and lo <= est <= hi


def test_freetext_finding_of():
    spec2 = importlib.util.spec_from_file_location("freetext", ROOT / "scripts" / "freetext.py")
    ft = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(ft)
    assert ft.finding_of("Is there a polyp in this image?") == "a polyp"
    assert ft.finding_of("Is there a pleural effusion in this chest X-ray?") == "a pleural effusion"
    assert ft.finding_of("Is there a tumor in this brain MRI slice?") == "a tumor"
    assert ft.finding_of("Does the picture contain liver cancer?") == "liver cancer"
    assert ft.finding_of("Is there an abnormality in this colonoscopy image?") is None
    assert ft.finding_of("Is the lung healthy?") is None
    assert ft.parse_yes_no("Yes.") is True and ft.parse_yes_no("no") is False and ft.parse_yes_no("maybe") is None
    cases = ft.case_rows({"a__o": True, "a__e": False}, {"a__o": {"case_id": "a", "kind": "original"},
                                                          "a__e": {"case_id": "a", "kind": "target_removal"}})
    assert cases == {"a": (1.0, 0.0)}


def test_edit_visibility_split_and_case_esg():
    spec3 = importlib.util.spec_from_file_location("edit_visibility", ROOT / "scripts" / "edit_visibility.py")
    ev = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(ev)
    scores = [{"case_id": "a", "kind": "random_removal", "score": 0.2}, {"case_id": "b", "kind": "random_removal", "score": 0.6},
              {"case_id": "a", "kind": "target_removal", "score": 0.3}, {"case_id": "b", "kind": "target_removal", "score": 0.9}]
    low, high, tau = ev.low_visibility_cases(scores)
    assert tau == 0.4 and low == {"a"} and high == {"b"}
    rows = [{"case_id": "a", "kind": "target_removal", "action": "answer", "correct": True},
            {"case_id": "a", "kind": "random_removal", "action": "answer", "claims_absent": False}]
    assert ev.case_esg(rows) == {"a": (1.0, 0.0, 0.0)}


# ------------------------------------------------------------------------------------------- Amendment 6 (v5)

def two_polyps(fps=10, n=6000):
    frames = {f: [] for f in range(n)}
    for f in range(1000, 1200):                       # 20 s track
        frames[f] = [(100, 100, 300, 300)]
    for f in range(3000, 3100):                       # 10 s track
        frames[f] = [(0, 0, 100, 100), (500, 500, 700, 700)]
    return frames


def test_fold_of_cuts_videos_by_number_within_cohort():
    assert [np_.fold_of(f"002-{i:03d}") for i in (1, 5, 6, 10, 11, 15)] == [0, 0, 1, 1, 2, 2]
    assert np_.fold_of("004-014") == np_.fold_of("001-014") == 2


def test_select_training_slots_are_balanced_disjoint_and_follow_the_distances():
    frames, fps = two_polyps(), 10
    slots = np_.select_training("001-001", frames, (1000, 1000), fps)
    kinds = [s["kind"] for s in slots]
    assert kinds.count("pos") == 6 + 5                   # one per 2 s, at most 6 per track
    assert kinds.count("near") == 2 and kinds.count("context") == 2
    assert kinds.count("far") == kinds.count("pos") - 4  # as many lesion-free frames as lesion frames
    cands = [c for s in slots for c in s["cands"]]
    assert len(cands) == len(set(cands)) and all(len(s["cands"]) <= np_.TRAIN_CAND for s in slots)
    boxed = np.array(sorted(f for f, b in frames.items() if b))
    dist = lambda f: np.abs(boxed - f).min() / fps       # noqa: E731
    for s in slots:
        for c in s["cands"]:
            if s["kind"] == "pos":
                assert frames[c]
            elif s["kind"] == "near":
                assert not frames[c] and dist(c) >= np_.NEG_CLEAR_S
            elif s["kind"] == "context":
                assert not frames[c] and np_.CLOSE_MIN_S <= dist(c) <= np_.CLOSE_MAX_S
            else:
                assert not frames[c] and dist(c) >= np_.FAR_CLEAR_S


def test_select_training_small_boxes_and_videos_without_polyps():
    frames = {f: [] for f in range(6000)}
    for f in range(1000, 1200):
        frames[f] = [(0, 0, 50, 50)]                     # 0.25% of the frame: below the training minimum
    assert [s for s in np_.select_training("001-002", frames, (1000, 1000), 10) if s["kind"] == "pos"] == []
    empty = np_.select_training("001-003", {f: [] for f in range(6000)}, (1000, 1000), 10)
    assert [s["kind"] for s in empty] == ["far"] * np_.NEG_ONLY


def test_select_context_frames_sit_just_outside_the_track():
    frames, fps = two_polyps(), 10
    before, after_only = np_.select_context(frames, fps, [(1000, 1199), (3000, 3099)])
    assert before and all(1000 - 100 <= f <= 1000 - 30 for f in before) and len(before) <= np_.N_CANDIDATES
    assert after_only and all(3000 - 100 <= f <= 3000 - 30 for f in after_only)
    start = {f: [] for f in range(2000)}
    for f in range(10, 400):
        start[f] = [(100, 100, 300, 300)]
    (c,) = np_.select_context(start, fps, [(10, 399)])   # nothing 3-10 s before frame 10: taken after the track
    assert c and all(399 + 30 <= f <= 399 + 100 for f in c)


def _png(img):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="PNG")
    return buf.getvalue()


def test_best_frames_keeps_the_sharpest_usable_candidate_per_slot():
    rng = np.random.default_rng(0)
    flat = np.full((120, 160, 3), 120, np.uint8)
    sharp = rng.integers(60, 200, (120, 160, 3), dtype=np.uint8)
    dark = rng.integers(0, 30, (120, 160, 3), dtype=np.uint8)           # sharpest, but too dark to use
    members = [("v/frames/7.jpg", lambda: _png(flat)), ("v/frames/8.jpg", lambda: _png(sharp)),
               ("v/frames/9.jpg", lambda: _png(dark)), ("v/frames/10.jpg", lambda: _png(sharp)),
               ("v/frames/8.xml", lambda: b"<a/>")]
    best = np_.best_frames(iter(members), {7: ["a"], 8: ["a", "b"], 9: ["a"], 11: ["c"]})
    assert best["a"][1] == 8 and best["b"][1] == 8 and "c" not in best
    assert best["a"][2].shape == (120, 160, 3)


def test_video_views_and_folds_keep_training_and_test_videos_apart(tmp_path):
    from medscope.eval.runner import load_views
    img = np.full((60, 80, 3), 120, np.uint8)
    rows, r9 = [], []
    for video in ("001-001", "001-007", "001-013"):
        frames = {5: [(10, 10, 40, 30), (0, 0, 5, 5)], 9: []}
        slots = [{"id": f"{video}_t0s0", "kind": "pos", "cands": [5]}, {"id": f"{video}_far0", "kind": "far", "cands": [9]},
                 {"id": f"{video}_t0near", "kind": "near", "cands": [3]}]            # no usable frame for this one
        pairs = [{"pair": f"{video}_t0", "track": [0, 8]}]
        best = {f"{video}_t0s0": (1.0, 5, img), f"{video}_far0": (1.0, 9, img), f"context:{video}_t0": (1.0, 12, img)}
        train, context, stats = np_.video_views(video, frames, (80, 60), slots, pairs, best, tmp_path)
        assert stats["pos"] == 1 and stats["far"] == 1 and stats["slot without a usable frame"] == 1
        assert train[0]["lesion_box"] == [125, 167, 500, 500] and train[0]["answer"] == "Yes"   # the largest box
        assert train[1]["kind"] == "natural_negative" and train[1]["answer"] == "No"
        rows.append({"video": video, "fold": np_.fold_of(video), "train": train, "context": context, "stats": dict(stats)})
        pid = np_._pid(f"{video}_t0")
        r9 += [v.to_dict() for v in np_.pair_views(pid, "realcolon_" + video, "natural_colon", "endoscopy", np_.COLON_Q,
                                                    "a.png", "b.png", [1, 2, 3, 4], False, {"video": video})]
    report = np_.assemble_folds(r9, rows, tmp_path)
    assert "| 0 | 2 | 2 | 2 | 1 | 1 |" in report
    for k, test_video in enumerate(("001-001", "001-007", "001-013")):
        train = load_views(tmp_path / f"views_train_fold{k}.jsonl")
        test = load_views(tmp_path / f"views_test_fold{k}.jsonl")
        assert {v.patient_id for v in test} == {"realcolon_" + test_video}
        assert "realcolon_" + test_video not in {v.patient_id for v in train} and len(train) == 4
        assert sorted(v.kind.value for v in test) == ["natural_negative", "natural_negative", "original"]
    assert len(load_views(tmp_path / "views_train_all.jsonl")) == 6
    ctx = [json.loads(l) for l in (tmp_path / "views_contextpairs_colon.jsonl").open()]
    assert sum(v["kind"] == "original" for v in ctx) == 3 and sum(bool(v["meta"].get("context")) for v in ctx) == 3


def test_score_pools_fold_runs_and_reports_grounded_detection(tmp_path):
    views = []
    for video in ("001-001", "001-007"):
        pid = np_._pid(f"{video}_t0")
        views += [v.to_dict() for v in np_.pair_views(pid, "realcolon_" + video, "natural_colon", "endoscopy", np_.COLON_Q,
                                                       "a.png", "b.png", [1, 2, 3, 4], False, {"video": video})]
    (tmp_path / "v.jsonl").write_text("".join(json.dumps(v) + "\n" for v in views))

    def run(name, rows):
        d = tmp_path / name
        d.mkdir()
        (d / "scored.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return str(d)

    row = lambda v, **kw: {"view_id": v["view_id"], "kind": v["kind"], "action": "answer", **kw}  # noqa: E731
    f0 = run("f0", [row(views[0], claims_absent=False, iou=0.6), row(views[1], correct=True)])
    f1 = run("f1", [row(views[2], claims_absent=False, iou=0.1), row(views[3], correct=True)])
    other = run("other", [row(views[0], claims_absent=True), row(views[1], correct=True),
                          row(views[2], claims_absent=True), row(views[3], correct=False)])
    assert len(np_.pooled_rows(f"{f0}+{f1}")) == 4 and np_.pooled_rows(f"{f0}+{tmp_path}/missing") is None
    np_.score([str(tmp_path / "v.jsonl")], [f"cv={f0}+{f1}", f"other={other}", f"gone={tmp_path}/missing"], "cv",
              tmp_path / "out.md", "fold", with_boxes=True)
    text = (tmp_path / "out.md").read_text()
    assert "| cv | 2 | 100.0% | 100.0% | 1.000" in text and "| other | 2 | 0.0% | 50.0% | -0.500" in text
    assert "fold 0" in text and "fold 1" in text and "gone" not in text
    assert "| cv | 2 | 2 (100.0%) | 1 (50.0%) |" in text and "| other | 2 | 0 (0.0%) | 0 (0.0%) |" in text


def test_colon_train_end_to_end_on_fake_archives(tmp_path, monkeypatch=None):
    import io, shutil, tarfile
    from PIL import Image
    src, r9, out = tmp_path / "figshare", tmp_path / "r9", tmp_path / "train"
    src.mkdir(); r9.mkdir()
    rng = np.random.default_rng(0)
    files, sel, r9_views = [], [], []
    for video in ("001-001", "001-006", "001-011"):
        ann, frm = src / f"{video}_annotations.tar.gz", src / f"{video}_frames.tar.gz"
        with tarfile.open(ann, "w:gz") as ta, tarfile.open(frm, "w:gz") as tf:
            for f in range(900):
                box = ("<object><bndbox><xmin>20</xmin><ymin>20</ymin><xmax>80</xmax><ymax>70</ymax></bndbox></object>"
                       if 400 <= f < 460 else "")
                xml = f"<annotation><size><width>160</width><height>120</height></size>{box}</annotation>".encode()
                info = tarfile.TarInfo(f"{video}_annotations/{video}_{f}.xml"); info.size = len(xml)
                ta.addfile(info, io.BytesIO(xml))
                buf = io.BytesIO()
                Image.fromarray(rng.integers(60, 200, (120, 160, 3), dtype=np.uint8)).save(buf, format="JPEG")
                info = tarfile.TarInfo(f"{video}_frames/{video}_{f}.jpg"); info.size = buf.tell()
                buf.seek(0)
                tf.addfile(info, buf)
        files += [{"name": p.name, "size": p.stat().st_size, "download_url": str(p)} for p in (ann, frm)]
        sel.append({"video": video, "n_frames": 900, "pairs": [{"pair": f"{video}_t0", "track": [400, 459]}]})
        pid = np_._pid(f"{video}_t0")
        r9_views += [v.to_dict() for v in np_.pair_views(pid, "realcolon_" + video, "natural_colon", "endoscopy", np_.COLON_Q,
                                                          "a.png", "b.png", [1, 2, 3, 4], False, {"video": video})]
    (r9 / "selection.jsonl").write_text("".join(json.dumps(s) + "\n" for s in sel))
    (r9 / "views_natural_colon.jsonl").write_text("".join(json.dumps(v) + "\n" for v in r9_views))
    (r9 / "video_info.csv").write_text("unique_video_name,fps\n001-001,10\n001-006,10\n001-011,10\n")
    old = np_.figshare_files, np_.download
    np_.figshare_files = lambda: files
    np_.download = lambda url, dest: Path(shutil.copy(url, dest))
    try:
        np_.colon_train(r9, out, max_videos=2, workers=1)   # a first session that covers two videos
        assert len((out / "videos.jsonl").read_text().splitlines()) == 2
        np_.colon_train(r9, out, max_videos=60, workers=2)  # resumes: only the third video is new
    finally:
        np_.figshare_files, np_.download = old
    rows = sorted((json.loads(l) for l in (out / "videos.jsonl").open()), key=lambda r: r["video"])
    assert [r["video"] for r in rows] == ["001-001", "001-006", "001-011"] and [r["fold"] for r in rows] == [0, 1, 2]
    for r in rows:
        assert r["stats"]["pos"] == 3 and r["stats"]["context frames for R9 pairs"] == 1   # 6 s track: 3 lesion frames
        assert sum(r["stats"].get(k, 0) for k in ("near", "context", "far")) == 3
        for v in r["train"] + r["context"]:
            assert Path(v["image_path"]).exists()
    assert not list((out / "archives").glob("*"))
    assert "| 2 | 2 | 6 | 6 | 1 | 1 |" in (out / "report_train.txt").read_text()


def test_stream_members_reads_a_tar_over_http_and_a_cut_off_stream_raises(tmp_path):
    import functools, http.server, io, tarfile, threading
    from PIL import Image
    rng = np.random.default_rng(0)
    with tarfile.open(tmp_path / "v_frames.tar.gz", "w:gz") as tf:
        for f in range(40):
            buf = io.BytesIO()
            Image.fromarray(rng.integers(60, 200, (120, 160, 3), dtype=np.uint8)).save(buf, format="JPEG")
            info = tarfile.TarInfo(f"v_frames/v_{f}.jpg"); info.size = buf.tell()
            buf.seek(0)
            tf.addfile(info, buf)
    data = (tmp_path / "v_frames.tar.gz").read_bytes()
    (tmp_path / "cut.tar.gz").write_bytes(data[:len(data) // 2])
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        seen = set()
        best = np_.best_frames(np_.stream_members(f"{base}/v_frames.tar.gz"), {3: ["a"], 30: ["a"], 39: ["b"]}, seen)
        assert seen == {3, 30, 39} and best["a"][1] in (3, 30) and best["b"][1] == 39
        try:
            np_.best_frames(np_.stream_members(f"{base}/cut.tar.gz"), {3: ["a"], 39: ["b"]}, set())
            raise AssertionError("a cut-off archive must not pass silently")
        except AssertionError:
            raise
        except Exception:
            pass
    finally:
        srv.shutdown()
