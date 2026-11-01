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

    def test_v4_caps_keep_the_test_split_and_add_a_fresh_set(self):
        recs = [extra.Record(key=f"lgg{i}", dataset="lgg", modality="mri", image_path="x", mask_path=None,
                             group=f"p{i // 4}", label="tumor", negative=(i % 3 == 0)) for i in range(2000)]
        old = extra.split_and_cap(recs, seed=7)
        new = extra.split_and_cap(recs, seed=7, caps=extra.CAPS_V4, fresh=(60, 40))
        self.assertEqual([r.key for r in old["test"]], [r.key for r in new["test"]])
        self.assertGreater(len(new["train"]), len(old["train"]))
        self.assertTrue({r.key for r in old["validation"]} <= {r.key for r in new["validation"]})
        used = {r.group for r in new["test"]}
        self.assertTrue(new["fresh"])
        self.assertFalse({r.group for r in new["fresh"]} & used)
        self.assertFalse({r.key for r in new["fresh"]} & {r.key for s in ("train", "validation", "test") for r in new[s]})

    def test_paraphrase_view_keeps_ids(self):
        with tempfile.TemporaryDirectory() as d:
            v = build_views(make_case(Path(d), "chestxdet1", 1), Path(d) / "v", np.random.default_rng(0))[1]
            p = paraphrase_view(v, HELD_OUT)
            self.assertEqual(p.view_id, v.view_id)
            self.assertNotEqual(p.question, v.question)
            self.assertEqual(p.meta["original_question"], v.question)


if __name__ == "__main__":
    unittest.main()
