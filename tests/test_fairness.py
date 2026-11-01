"""Held-out inpainters and few-shot prompting (notebook 20)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.agent import prompts
from medscope.agent.episode import run_episode, Generation
from medscope.agent.fewshot import example_messages, pick_examples, reply
from medscope.data.counterfactual import dilate
from medscope.data.inpaint import diffusion_crop, feather_paste, get_inpainter, transplant_inpaint
from medscope.data.schema import Case, ViewKind
from medscope.data.views import build_views
from medscope.eval.runner import load_views, prompt_key
from medscope.rewards import load_config
from tests.helpers import synthetic_case

ROOT = Path(__file__).resolve().parent.parent


class TestHeldOutInpainters(unittest.TestCase):
    def setUp(self):
        self.image, self.lesion = synthetic_case()
        self.hole = dilate(self.lesion, 5)

    def test_transplant_fills_hole_with_tissue_not_lesion(self):
        out = transplant_inpaint(self.image, self.hole, avoid=self.lesion, seed=3)
        keep = ~dilate(self.hole, 4)
        np.testing.assert_array_equal(out[keep], self.image[keep])
        self.assertLess(out[self.lesion].mean(), 170)          # the bright lesion is gone
        self.assertTrue((out[..., 0] == out[..., 1]).all())     # a grey image stays grey

    def test_transplant_is_deterministic_and_seeded(self):
        a = transplant_inpaint(self.image, self.hole, avoid=self.lesion, seed=1)
        b = transplant_inpaint(self.image, self.hole, avoid=self.lesion, seed=1)
        np.testing.assert_array_equal(a, b)

    def test_transplant_gives_up_without_room(self):
        with self.assertRaises(ValueError):
            transplant_inpaint(self.image, np.ones(self.lesion.shape, bool))

    def test_feather_paste_only_touches_the_edge(self):
        fill = np.zeros_like(self.image)
        out = feather_paste(self.image, fill, self.hole, grow=2)
        np.testing.assert_array_equal(out[~dilate(self.hole, 2)], self.image[~dilate(self.hole, 2)])
        self.assertTrue((out[self.hole] == 0).all())

    def test_diffusion_crop_stays_inside(self):
        m = np.zeros((300, 200), bool)
        m[5:20, 180:195] = True
        y0, y1, x0, x1 = diffusion_crop(m)
        self.assertTrue(0 <= y0 < y1 <= 300 and 0 <= x0 < x1 <= 200)
        self.assertEqual(y1 - y0, x1 - x0)
        self.assertTrue(m[y0:y1, x0:x1].sum() == m.sum())

    def test_get_inpainter_names(self):
        for name in ("telea", "lama", "transplant", "diffusion"):
            self.assertTrue(callable(get_inpainter(name)))

    def test_reinpaint_script_keeps_ids_and_masks(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            Image.fromarray(self.image).save(d / "img.png")
            Image.fromarray((self.lesion * 255).astype(np.uint8)).save(d / "mask.png")
            case = Case(case_id="c1", patient_id="p1", dataset="synthetic", modality="xray",
                        image_path=str(d / "img.png"), question="Is there a nodule?",
                        answer="yes", mask_path=str(d / "mask.png"))
            views = build_views(case, d / "views", np.random.default_rng(0))
            (d / "views.jsonl").write_text("".join(json.dumps(v.to_dict()) + "\n" for v in views))
            for tool in ("telea", "transplant"):
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / "reinpaint_views.py"), "--views",
                                    str(d / "views.jsonl"), "--inpainter", tool, "--out", str(d / tool)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                new = load_views(d / tool / "views.jsonl")
                self.assertEqual(sorted(v.view_id for v in new),
                                 sorted(v.view_id for v in views if v.kind in (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL)))
                old = {v.view_id: v for v in views}
                for v in new:
                    self.assertEqual(v.meta["inpainter"], tool)
                    self.assertEqual(v.meta["edit_box"], old[v.view_id].meta["edit_box"])
                    self.assertNotEqual(v.image_path, old[v.view_id].image_path)
                    a, b = np.asarray(Image.open(v.image_path)), np.asarray(Image.open(old[v.view_id].image_path))
                    em = np.asarray(Image.open(v.meta["edit_mask"])) > 127
                    np.testing.assert_array_equal(a[~dilate(em, 4)], b[~dilate(em, 4)])


class TestFewShot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.views, self.negs = [], []
        for i, prefix in enumerate(["kvasir", "busi", "lgg"]):
            img, lesion = synthetic_case(seed=i + 1)
            Image.fromarray(img).save(d / f"{prefix}.png")
            Image.fromarray((lesion * 255).astype(np.uint8)).save(d / f"{prefix}_m.png")
            case = Case(case_id=f"{prefix}_{i}", patient_id=f"p{i}", dataset=prefix, modality=prefix,
                        image_path=str(d / f"{prefix}.png"), question="Is there a lesion?", answer="Yes",
                        mask_path=str(d / f"{prefix}_m.png"))
            self.views += build_views(case, d / "views", np.random.default_rng(i))
        from dataclasses import replace
        healthy = replace(self.views[0], view_id="lggneg_1__natural_negative", case_id="lggneg_1",
                          kind=ViewKind.NATURAL_NEGATIVE, answer="No", lesion_box=None)
        self.negs = [healthy]

    def tearDown(self):
        prompts.set_fewshot([], [])
        prompts.set_prompt("agent")
        self.tmp.cleanup()

    def test_examples_cover_the_lesson(self):
        ex = pick_examples(self.views, self.negs)
        self.assertEqual([v.kind for v in ex], [ViewKind.ORIGINAL, ViewKind.TARGET_REMOVAL,
                                                ViewKind.RANDOM_REMOVAL, ViewKind.NATURAL_NEGATIVE])
        self.assertEqual(ex[0].case_id, ex[1].case_id)
        self.assertTrue(ex[0].case_id.startswith("kvasir"))
        self.assertNotEqual(ex[2].case_id, ex[0].case_id)
        self.assertIn('"answer": "No"', reply(ex[1]))
        self.assertIn('"box"', reply(ex[2]))
        self.assertEqual(ex, pick_examples(self.views, self.negs))     # deterministic

    def test_examples_precede_the_case_and_stay_out_of_transcripts(self):
        ex = pick_examples(self.views, self.negs)
        prompts.set_prompt("fewshot")
        prompts.set_fewshot(example_messages(ex), [v.view_id for v in ex])
        seen = []

        class Echo:
            def generate(self, messages, sample=False):
                seen.append(list(messages))
                return Generation('<final>{"action": "answer", "answer": "No", "confidence": 0.5}</final>')

        ep = run_episode(Echo(), self.views[1], load_config())
        msgs = seen[0]
        self.assertEqual(len(msgs), 1 + 8 + 1)
        self.assertEqual([m["role"] for m in msgs[1:9]], ["user", "assistant"] * 4)
        self.assertEqual(msgs[-1]["content"][1]["text"], f"Question: {self.views[1].question}")
        t = ep.transcript()
        self.assertEqual(t[0]["role"], "user")
        self.assertEqual(len(t), 2)                       # the case and the model's reply only

    def test_result_key_changes_with_examples_and_not_otherwise(self):
        base = prompt_key()
        prompts.set_prompt("fewshot")
        k1 = prompt_key()
        prompts.set_fewshot([], ["a", "b"])
        k2 = prompt_key()
        prompts.set_fewshot([], [])
        prompts.set_prompt("agent")
        self.assertEqual(prompt_key(), base)
        self.assertNotEqual(k1, k2)
        self.assertNotEqual(base, k1)


if __name__ == "__main__":
    unittest.main()
