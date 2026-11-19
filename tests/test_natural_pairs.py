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
