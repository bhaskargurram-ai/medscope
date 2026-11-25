"""Amendment 9 (R24-R27): the kept share of erased views, LDPolypVideo natural pairs, the three-seed vote."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.schema import ViewKind
from medscope.data.views import build_views
from tests.helpers import synthetic_case
from tests.test_v4 import make_case

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


np_ = load("natural_pairs")
sv = load("seed_vote")


# ---------------------------------------------------------------------------------------------- training mix

def mix_args(**kw):
    base = dict(paraphrase_prob=0.0, balance_health=False, oversample_small=1, min_absent_share=0.0, min_erased_share=0.0)
    return Namespace(**{**base, **kw})


def test_min_erased_share_repeats_only_erased_views():
    from dataclasses import replace
    from train_sft import mix_summary, v4_mix
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0)) + \
            build_views(make_case(d, "chestxdet2", 2), d / "v", np.random.default_rng(1))
        free = [replace(views[0], view_id=f"n{i}__natural_negative", case_id=f"n{i}", kind=ViewKind.NATURAL_NEGATIVE,
                        answer="No", lesion_box=None) for i in range(40)]
        plain = v4_mix(views + free, mix_args(min_absent_share=0.35))
        # the lesion-free images alone fill the 'absent' share, so no erased view is repeated: the dilution
        assert sum(v.kind is ViewKind.TARGET_REMOVAL for v in plain) == 2
        kept = v4_mix(views + free, mix_args(min_absent_share=0.35, min_erased_share=0.25))
        s = mix_summary(kept)
        assert s["erased_share"] >= 0.25 and s["erased_share"] < 0.30
        assert len({v.view_id for v in kept}) == len(kept)
        added = [v for v in kept if "#e" in v.view_id]
        assert added and all(v.kind is ViewKind.TARGET_REMOVAL for v in added)
        assert s["kinds"]["natural_negative"] == 40                    # nothing else is repeated or dropped
        assert v4_mix(views + free, mix_args(min_erased_share=0.01)) == views + free   # already above the share


def test_mix_without_the_option_is_unchanged():
    from train_sft import v4_mix
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0))
        old = Namespace(paraphrase_prob=0.0, balance_health=False, oversample_small=1, min_absent_share=0.5)
        assert [v.view_id for v in v4_mix(views, old)] == [v.view_id for v in v4_mix(views, mix_args(min_absent_share=0.5))]


def test_mix_only_writes_the_mix_and_loads_no_model():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0))
        f = d / "views.jsonl"
        f.write_text("".join(json.dumps({**v.to_dict(), "kind": v.kind.value}) + "\n" for v in views))
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "train_sft.py"), "--model", "none", "--views", str(f),
                            "--mode", "agentic", "--out", str(d / "unused"), "--min-absent-share", "0.35",
                            "--mix-only", str(d / "mix.json")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        mix = json.loads((d / "mix.json").read_text())
        assert mix["views"] >= len(views) and 0.3 <= mix["erased_share"] <= 0.5
        assert not (d / "unused").exists()


# ---------------------------------------------------------------------------------------------- LDPolypVideo

def test_parse_ld_annotation_variants():
    assert np_.parse_ld("0\n") == (False, [])
    assert np_.parse_ld("1\n100 120 300 340\n") == (True, [(100.0, 120.0, 300.0, 340.0)])
    assert np_.parse_ld("2\n10 10 50 50\n60,60,90,95\n") == (True, [(10.0, 10.0, 50.0, 50.0), (60.0, 60.0, 90.0, 95.0)])
    assert np_.parse_ld("100 120 300 340\n") == (True, [(100.0, 120.0, 300.0, 340.0)])     # no count line
    assert np_.parse_ld("") == (None, [])
    assert np_.parse_ld("1\n") == (True, [])                                              # a polyp, box missing


def test_box_format_is_decided_on_all_boxes():
    size = (560, 480)
    corners = [(100, 100, 300, 300), (10, 20, 200, 400), (300, 50, 550, 470)] * 50
    assert np_.ld_box_format(corners, [size] * len(corners)) == "corners"
    xywh = [(300, 200, 100, 80), (400, 300, 150, 150), (10, 20, 30, 40)] * 50
    assert np_.ld_box_format(xywh, [size] * len(xywh)) == "xywh"
    yolo = [(0.5, 0.5, 0.2, 0.3)] * 20
    assert np_.ld_box_format(yolo, [size] * 20) == "yolo"
    assert np_.ld_box_format([(900, 900, 100, 100)] * 10, [size] * 10) == "unknown"
    assert np_.ld_corners((300, 200, 100, 80), size, "xywh") == (300, 200, 400, 280)
    assert np_.ld_corners((0.5, 0.5, 0.2, 0.5), size, "yolo") == (224.0, 120.0, 336.0, 360.0)
    assert np_.ld_corners((1, 2, 3, 4), size, "unknown") is None


def clip(n=200, polyp=(60, 160), box=(100, 100, 250, 250)):
    flags = {f: (polyp[0] <= f < polyp[1]) for f in range(1, n + 1)}
    return flags, {f: [box] for f, p in flags.items() if p}


def test_select_ld_video_lesion_from_the_middle_and_a_clear_frame():
    flags, boxes = clip()
    sel = np_.select_ld_video(flags, boxes, (560, 480))
    assert sel["track"] == [60, 159]
    assert all(84 <= f <= 135 for f in sel["pos"]) and len(sel["pos"]) <= np_.N_CANDIDATES
    assert all(f <= 60 - np_.LD_CLEAR or f >= 159 + np_.LD_CLEAR for f in sel["neg"])
    assert all(flags[f] is False for f in sel["neg"])


def test_select_ld_video_reasons_for_no_pair():
    flags, boxes = clip(polyp=(1, 201))
    assert np_.select_ld_video(flags, boxes, (560, 480)) == "no polyp-free frame far enough from a polyp frame"
    flags, boxes = clip(polyp=(60, 65))
    assert np_.select_ld_video(flags, boxes, (560, 480)) == "no track long enough"
    flags, boxes = clip(box=(0, 0, 20, 20))                                 # 0.15% of the frame
    assert np_.select_ld_video(flags, boxes, (560, 480)) == "no polyp frame with a large enough box"
    assert isinstance(np_.select_ld_video(flags, None, (560, 480)), dict)   # box format unknown: no size rule
    assert np_.select_ld_video({f: False for f in range(50)}, {}, (560, 480)) == "no polyp frame"
    flags, boxes = clip(polyp=(60, 160))
    for f in list(flags):
        if not flags[f]:
            flags[f] = None if f % 3 == 0 else False                       # unreadable labels count as not clear
    assert np_.select_ld_video(flags, boxes, (560, 480)) == "no polyp-free frame far enough from a polyp frame"


def test_ldpolyp_build_writes_pairs_that_score():
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / "src", Path(d) / "out"
        for split, video, has_free in (("TrainValid", "1", True), ("TrainValid", "2", False), ("Test", "101", True)):
            (src / split / "Images" / video).mkdir(parents=True)
            (src / split / "Annotations" / video).mkdir(parents=True)
            for f in range(1, 61):
                polyp = f > 25 or not has_free
                img, _ = synthetic_case(seed=int(video) * 100 + f, lesion_radius=30 if polyp else 1)
                Image.fromarray(img).save(src / split / "Images" / video / f"{f:04d}.jpg")
                (src / split / "Annotations" / video / f"{f:04d}.txt").write_text("1\n60 70 120 130\n" if polyp else "0\n")
        np_.ldpolyp_build(src, out)
        views = [json.loads(line) for line in (out / "views_natural_ldpolyp.jsonl").open()]
        rep = json.loads((out / "report_ldpolyp.json").read_text())
        assert rep["pairs"] == 2 and rep["box_format"] == "corners" and rep["confirmatory"] is False
        assert rep["no_pair"]["no polyp-free frame far enough from a polyp frame"] == 1
        assert [v["kind"] for v in views] == ["original", "natural_negative"] * 2
        assert {v["meta"]["split"] for v in views} == {"TrainValid", "Test"}
        assert len({v["patient_id"] for v in views}) == 2 and all(Path(v["image_path"]).exists() for v in views)
        pos = views[0]
        assert pos["lesion_box"] == [234, 273, 469, 508] and pos["meta"]["pair"] == views[1]["meta"]["pair"]
        # the views run through the usual scorer: a model that finds the polyp and clears the other frame scores 1
        rows = [{"view_id": v["view_id"], "kind": v["kind"], "action": "answer", "correct": True,
                 "claims_absent": v["kind"] == "natural_negative"} for v in views]
        esg = np_.natural_esg_rows(rows, {v["view_id"]: v for v in views})
        assert all(r[2] == 1.0 for r in esg.values()) and len(esg) == 2
        assert np_.stratum_of(views[0], "split") in ("TrainValid", "Test")


# ---------------------------------------------------------------------------------------------- three-seed vote

def row(view="v1", action="answer", absent=False, correct=True, kind="original", reward=1.0):
    return {"view_id": view, "case_id": view.split("__")[0], "kind": kind, "action": action, "correct": correct, "iou": 0.0,
            "confidence": 0.9, "tool_calls": 0, "malformed": action is None, "reward": reward, "breakdown": {},
            "claims_absent": absent if action == "answer" else None}


def test_vote_majority_and_fallbacks():
    present, absent, refer, ask = row(), row(absent=True, correct=False), row(action="refer"), row(action="clarify")
    assert sv.vote([present, absent, present]) is present
    assert sv.vote([absent, present, absent]) is absent
    assert sv.vote([refer, refer, present]) is refer
    assert sv.vote([present, absent, refer]) is refer            # no majority: the cautious decision
    assert sv.vote([present, absent, ask]) is ask
    assert sv.vote([present, absent]) is present                 # two seeds, no majority, nobody refers
    assert sv.decision_class(row(action=None)) == "other"


def test_vote_run_is_read_like_any_other_run():
    from medscope.eval.compare import significance_table
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        claims = {"s0": [True, False, False], "s1": [False, False, True], "s2": [False, True, False]}
        for name, cl in claims.items():
            (d / name).mkdir()
            rows = [row(f"c{i}__natural_negative", absent=not c, correct=not c, kind="natural_negative",
                        reward=-1.0 if c else 1.0) for i, c in enumerate(cl)]
            rows += [row(f"c{i}__target_removal", absent=True, kind="target_removal") for i in range(3)]
            rows += [row(f"c{i}__random_removal", kind="random_removal") for i in range(3)]
            (d / name / "outcomes.jsonl").write_text("".join(json.dumps({**r, "vkey": "x"}) + "\n" for r in rows))
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_vote.py"), "--runs", str(d / "s0"), str(d / "s1"),
                            str(d / "s2"), "--out", str(d / "vote"), "--name", "vote"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        s = json.loads((d / "vote" / "summary.json").read_text())
        # every seed claims a finding on one lesion-free image (33%), never the same one: the vote claims none
        assert s["metrics"]["natural_hallucination_rate"]["value"] == 0.0
        assert s["metrics"]["esg"]["value"] == 1.0 and s["n_views"] == 9
        assert s["meta"]["agreement"]["two classes"] == 3
        assert "natural_hallucination_rate" in significance_table(d, "vote", ["s0"])
