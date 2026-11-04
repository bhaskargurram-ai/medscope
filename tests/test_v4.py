"""v4 recipe: data options, insertion, paraphrases, degradations, selection rule."""

import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.actions import absent_reply, asked_finding
from medscope.agent.trajectories import build_trajectory
from medscope.data.counterfactual import DEGRADATIONS_V4, make_degraded
from medscope.data.loaders import extra
from medscope.data.paraphrase import HELD_OUT, TRAIN, paraphrase, paraphrase_view
from medscope.data.schema import Case, ViewKind
from medscope.data.views import build_views
from medscope.eval.runner import load_views
from tests.helpers import synthetic_case

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def make_case(d: Path, name: str, seed: int, radius: int = 14, question="Is there a nodule in this chest X-ray?"):
    img, lesion = synthetic_case(seed=seed, lesion_radius=radius)
    Image.fromarray(img).save(d / f"{name}.png")
    Image.fromarray((lesion * 255).astype(np.uint8)).save(d / f"{name}_m.png")
    return Case(case_id=name, patient_id=name, dataset="chestxdet", modality="xray", image_path=str(d / f"{name}.png"),
                question=question, answer="Yes", mask_path=str(d / f"{name}_m.png"))


class TestV4(unittest.TestCase):
    def test_paraphrases_are_scored_like_the_original(self):
        q = "Is there a nodule in this chest X-ray?"
        for t in TRAIN + HELD_OUT:
            p = paraphrase(q, (t,), "k")
            self.assertEqual(absent_reply(p, "Yes"), "No")
            self.assertEqual(asked_finding(p), "nodule")
        self.assertIsNone(paraphrase("Which organ is abnormal?", TRAIN, "k"))
        self.assertFalse(set(TRAIN) & set(HELD_OUT))

    def test_new_degradations(self):
        img = synthetic_case()[0]
        rng = np.random.default_rng(0)
        for k in DEGRADATIONS_V4:
            if k == "mismatch":
                continue
            out = make_degraded(img, k, rng)
            self.assertEqual(out.shape, img.shape)

    def test_window_and_small_zoom_trajectories(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0))
            orig = views[0]
            turns = build_trajectory(orig, np.random.default_rng(0), zoom_prob=0.6, window_prob=1.0)
            self.assertIn('"name": "window"', turns[0].target)          # window replaces the zoom
            self.assertEqual(len(turns), 2)
            self.assertIn('"answer": "Yes"', turns[-1].target)
            forced = build_trajectory(orig, np.random.default_rng(0), zoom_prob=1.0, window_prob=1.0)
            self.assertIn('"name": "zoom"', forced[0].target)           # small lesions: always the zoom
            from medscope.agent.trajectories import is_gray
            img = np.full((8, 8, 3), 100, np.uint8)
            img[..., 0] += 3                                              # inpainting leaves tiny channel differences
            self.assertTrue(is_gray(img))
            img[..., 2] = 200
            self.assertFalse(is_gray(img))
            plain = build_trajectory(orig, np.random.default_rng(0), zoom_prob=0.0)
            self.assertEqual(len(plain), 1)

    def test_v4_mix(self):
        from train_sft import v4_mix
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = build_views(make_case(d, "chestxdet1", 1, radius=6), d / "v", np.random.default_rng(0)) + \
                build_views(make_case(d, "chestxdet2", 2, radius=40), d / "v", np.random.default_rng(1))
            args = Namespace(paraphrase_prob=1.0, balance_health=False, oversample_small=2, min_absent_share=0.5)
            mixed = v4_mix(views, args)
            self.assertTrue(all(v.question != "Is there a nodule in this chest X-ray?" for v in mixed))
            small = [v for v in mixed if v.case_id == "chestxdet1" and v.kind is not ViewKind.DEGRADED
                     and "#a" not in v.view_id]
            self.assertEqual(len(small), 2 * 3)                       # original, erased, control, each twice
            absent = sum(v.kind is ViewKind.TARGET_REMOVAL for v in mixed)
            self.assertGreaterEqual(absent / len(mixed), 0.49)
            self.assertEqual(len({v.view_id for v in mixed}), len(mixed))

    def test_insertion_views(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = build_views(make_case(d, "chestxdet1_abn", 1), d / "v", np.random.default_rng(0))
            host, _ = synthetic_case(seed=5, lesion_radius=1)
            host[...] = np.where(host > 200, 110, host)               # a lesion-free image
            Image.fromarray(host).save(d / "host.png")
            from dataclasses import replace
            neg = replace(views[0], view_id="chestxdet9neg_abn__natural_negative", case_id="chestxdet9neg_abn",
                          kind=ViewKind.NATURAL_NEGATIVE, image_path=str(d / "host.png"), answer="No", lesion_box=None)
            (d / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in views))
            (d / "neg.jsonl").write_text(json.dumps(neg.to_dict()) + "\n")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "insert_lesions.py"), "--views", str(d / "views.jsonl"),
                                "--negatives", str(d / "neg.jsonl"), "--out", str(d / "ins")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            ins = load_views(d / "ins" / "views.jsonl")
            self.assertEqual(len(ins), 1)
            v = ins[0]
            self.assertIs(v.kind, ViewKind.ORIGINAL)
            self.assertTrue(v.meta["inserted"])
            img = np.asarray(Image.open(v.image_path))
            m = np.asarray(Image.open(v.meta["lesion_mask"])) > 127
            self.assertGreater(img[m].mean(), host[m].mean() + 40)    # the lesion is there now

    def test_selection_rule(self):
        from select_v4 import choose
        self.assertEqual(choose({"stage 1": (0.70, 0.10), "stage 2": (0.72, 0.09), "stage 3": (0.71, 0.10)}), "stage 3")
        self.assertEqual(choose({"stage 1": (0.70, 0.10), "stage 2": (0.72, 0.09), "stage 3": (0.75, 0.15)}), "stage 2")
        self.assertEqual(choose({"stage 1": (0.70, 0.10), "stage 2": (0.60, 0.09), "stage 3": (0.50, 0.30)}), "stage 1")

    def test_v4_split_protects_the_existing_test_set(self):
        import sys as _s
        _s.path.insert(0, str(ROOT / "scripts"))
        from prepare_extra import protect
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            recs = []
            for i in range(400):
                p = d / f"lgg{i:05d}.png"
                Image.fromarray((np.random.default_rng(i).random((16, 16, 3)) * 255).astype(np.uint8)).save(p)
                recs.append(extra.Record(key=f"lgg{i:05d}", dataset="lgg", modality="mri", image_path=str(p), mask_path=None,
                                         group=f"p{i // 4}", label="tumor", negative=(i % 3 == 0)))
            test_keys = {f"lgg{i:05d}": str(d / f"lgg{i:05d}.png") for i in range(0, 400, 37)}
            kept, excluded, _ = protect("lgg", recs, test_keys, {})
            gone = {f"p{int(k[3:]) // 4}" for k in test_keys}
            self.assertFalse({r.group for r in kept} & gone)
            new = extra.split_and_cap(kept, seed=7, caps=extra.CAPS_V4, fresh=(60, 40), fresh_exclude=excluded)
            self.assertEqual(new["test"], [])
            self.assertTrue(new["fresh"])
            keys = [r.key for s in new.values() for r in s]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertFalse(set(keys) & set(test_keys))
            # a changed source (same key, different image) stops the build
            bad = {k: str(d / "lgg00001.png") for k in list(test_keys)[:5]}
            with self.assertRaises(SystemExit):
                protect("lgg", recs, bad, {})

    def test_breakdowns(self):
        from medscope.rewards import Outcome
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0))
            (d / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in views))
            for run, act in (("a", "clarify"), ("b", "answer")):
                (d / run).mkdir()
                rows = [Outcome(view_id=v.view_id, case_id=v.case_id, kind=v.kind.value, action=act, correct=True, iou=0.0,
                                confidence=None, tool_calls=0, malformed=False, reward=1.0 if act == "clarify" else 0.5,
                                breakdown={}).to_dict() for v in views]
                (d / run / "outcomes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "breakdowns.py"), "--results", str(d), "--views",
                                str(d / "views.jsonl"), "--runs", "a=A", "b=B", "--ref", "a", "--out", str(d / "o.md")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            md = (d / "o.md").read_text()
            self.assertIn("| A | 1.000 | 1.000 |", md)
            self.assertIn("100% (1)", md)

    def test_prefetched_training_samples_match_the_plain_loop(self):
        import os
        import threading
        from medscope.train.sft import prepared_views, view_order
        class Fake:
            def target_ids(self, text):
                return [len(text)]
            def encode_cpu(self, messages):
                return {"n": len(messages), "q": messages[-1]["content"][-1].get("text", "")[:20]}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = build_views(make_case(d, "chestxdet1", 1), d / "v", np.random.default_rng(0)) + \
                build_views(make_case(d, "chestxdet2", 2, radius=40), d / "v", np.random.default_rng(1))
            order = view_order(views, 2, 0)
            def run(flag):
                os.environ["MEDSCOPE_PREFETCH"] = flag
                out = [(vi, [(s.target, t, inp) for s, t, inp in p]) for vi, p in
                       prepared_views(Fake(), order, 3, "agentic", 0, None, None, 0.3, True, threading.Event())]
                os.environ.pop("MEDSCOPE_PREFETCH")
                return out
            plain, fast = run("0"), run("1")
            self.assertEqual(plain, fast)
            self.assertEqual([vi for vi, _ in fast], list(range(3, len(order))))

    def test_siim_fullres_rebuilds_the_same_cases(self):
        import siim_fullres
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            v = build_views(make_case(d, "siimext00003", 1, question="Is there a pneumothorax in this chest X-ray?"),
                            d / "v", np.random.default_rng(0))
            orig = replace(v[0], view_id="siimext00003_ptx__original", case_id="siimext00003_ptx", patient_id="siim_1.2.3")
            neg = replace(v[0], view_id="siimext00004neg_ptx__natural_negative", case_id="siimext00004neg_ptx",
                          patient_id="siim_1.2.4", kind=ViewKind.NATURAL_NEGATIVE, answer="No", lesion_box=None)
            (d / "views.jsonl").write_text("".join(json.dumps(x.to_dict()) + "\n" for x in (orig, neg)))
            siim = d / "siim"
            siim.mkdir()
            for uid in ("1.2.3", "1.2.4", "9.9.9"):
                (siim / f"{uid}.dcm").write_bytes(b"")
            (siim / "train-rle.csv").write_text("ImageId, EncodedPixels\n1.2.3, 4100 30 994 30\n1.2.4, -1\n")
            siim_fullres.read_dicom = lambda p: np.full((128, 128), 90, np.uint8)
            argv = sys.argv
            sys.argv = ["x", "--views", str(d / "views.jsonl"), "--siim", str(siim), "--out", str(d / "out")]
            try:
                siim_fullres.main()
            finally:
                sys.argv = argv
            cases = [json.loads(l) for l in (d / "out" / "cases_test.jsonl").read_text().splitlines()]
            negs = load_views(d / "out" / "negatives" / "views_negatives_external.jsonl")
            self.assertEqual([c["case_id"] for c in cases], ["siimfull00003_ptx"])
            self.assertEqual(cases[0]["question"], "Is there a pneumothorax in this chest X-ray?")
            m = np.asarray(Image.open(cases[0]["mask_path"])) > 127
            self.assertEqual(m.sum(), 60)
            self.assertEqual([n.case_id for n in negs], ["siimfull00004neg_ptx"])

    def test_paraphrase_view_keeps_ids(self):
        with tempfile.TemporaryDirectory() as d:
            v = build_views(make_case(Path(d), "chestxdet1", 1), Path(d) / "v", np.random.default_rng(0))[1]
            p = paraphrase_view(v, HELD_OUT)
            self.assertEqual(p.view_id, v.view_id)
            self.assertNotEqual(p.question, v.question)
            self.assertEqual(p.meta["original_question"], v.question)


if __name__ == "__main__":
    unittest.main()
