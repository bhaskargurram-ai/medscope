"""Screening stage B: dev set with TELEA copies, probes with fake models, and the screen."""

import tempfile
import unittest
from pathlib import Path

from medscope.agent.episode import Generation
from medscope.data.schema import ViewKind
from medscope.eval.runner import load_views
from medscope.rewards import load_config, with_vocab
from medscope.screen.probes import compute_probes, control_box, dev_views, read_probes, subset_of, tta_images
from medscope.screen.stage_b import report_b, rule_policies_b, run_screen_b
from tests.helpers import synthetic_case
from tests.test_runner_training import build_dataset

CFG = load_config()


class Yes:
    def __init__(self):
        self.n = 0

    def generate(self, messages, sample=False):
        self.n += 1
        return Generation('<final>{"action": "answer", "answer": "Yes", "box": [300, 340, 420, 460], "confidence": 0.8}</final>')


class Spec:
    def report(self, img):
        return {"peak": 0.4}


class TestStageB(unittest.TestCase):
    def test_dev_set_and_probes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d, n_cases=6))
            negs = [v for v in views if v.kind is ViewKind.ORIGINAL][:2]      # stand-ins (kind is checked)
            dev = dev_views(views, negs, n_cases=4, n_neg=2, out_dir=d / "dev")
            subs = [subset_of(v) for v in dev]
            self.assertEqual(subs.count("telea"), 8)                           # 4 cases x (erasure, control)
            self.assertEqual(subs.count("lama"), 8)
            self.assertTrue(all(Path(v.image_path).exists() for v in dev))
            cfg = with_vocab(CFG, views)
            pol, sec = Yes(), Yes()
            pr = compute_probes(pol, sec, Spec(), dev, cfg, d / "p.jsonl", batch_size=5, log=lambda m: None)
            self.assertEqual(set(pr), {v.view_id for v in dev})
            r = next(iter(pr.values()))
            self.assertEqual(len(r["tta"]), 3)
            self.assertIsNotNone(r["crop"])
            self.assertEqual(r["second"]["answer"], "Yes")
            n = pol.n
            compute_probes(pol, sec, Spec(), dev, cfg, d / "p.jsonl", log=lambda m: None)
            self.assertEqual(pol.n, n)                                         # resumed, nothing rerun
            rows = run_screen_b(dev, read_probes(d / "p.jsonl"), cfg, log=lambda m: None)
            self.assertEqual(rows[0]["policy"], "baseline")
            self.assertGreater(len(rule_policies_b()), 30)
            self.assertIn("policies screened", report_b(rows))

    def test_altered_copies_and_control_box(self):
        img, _ = synthetic_case()
        self.assertEqual([t.shape for t in tta_images(img)], [img.shape] * 3)
        import numpy as np
        cb = control_box(img, [300, 340, 420, 460], np.random.default_rng(0))
        self.assertIsNotNone(cb)
        self.assertAlmostEqual(cb[2] - cb[0], 120, delta=4)


if __name__ == "__main__":
    unittest.main()
