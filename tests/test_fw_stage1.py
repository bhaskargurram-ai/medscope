"""Framework stage 1: fill tools, tool-family views for the control's cases, and the screen rule."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from medscope.data.counterfactual import telea_inpaint
from medscope.data.fills import FILLS
from medscope.eval.runner import load_views
from medscope.fw.stage1 import compare, passes, report
from medscope.fw.toolfamily import TOOLS, assignment, build_toolfamily, select_cases, tool_counts, write_views
from medscope.train.cmcc import build_triplets
from tests.test_runner_training import build_dataset


class TestFills(unittest.TestCase):
    def test_only_the_mask_changes_and_gray_stays_gray(self):
        rng = np.random.default_rng(0)
        g = rng.integers(0, 256, (120, 160), dtype=np.uint8)
        img = np.stack([g] * 3, axis=-1)
        m = np.zeros((120, 160), bool)
        m[40:70, 50:90] = True
        for name, fn in FILLS.items():
            out = fn(img, m)
            self.assertEqual(out.shape, img.shape, name)
            self.assertTrue((out[~m] == img[~m]).all(), name)
            self.assertFalse((out[m] == img[m]).all(), name)
            self.assertTrue((out[..., 0] == out[..., 1]).all() and (out[..., 1] == out[..., 2]).all(), name)
        col = rng.integers(0, 256, (60, 60, 3), dtype=np.uint8)
        mm = np.zeros((60, 60), bool)
        mm[20:35, 20:35] = True
        self.assertTrue((FILLS["mean"](col, mm, seed=3) == FILLS["mean"](col, mm, seed=3)).all())   # deterministic

    def test_assignment(self):
        seen = {assignment(f"case{i}") for i in range(400)}
        self.assertEqual(len(seen), len(TOOLS) * 2)
        self.assertEqual(assignment("x"), assignment("x"))


class TestToolFamily(unittest.TestCase):
    def test_views_for_the_same_cases(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d, n_cases=10))
            trip = build_triplets(views)
            sel = select_cases(trip, 6, 0)
            self.assertEqual(len(sel), 6)
            self.assertEqual([t.case_id for t in sel], [t.case_id for t in select_cases(trip, 6, 0)])
            tf = build_toolfamily(sel, d / "tf", lama=telea_inpaint, log=lambda m: None)
            write_views(tf, d / "tf" / "views.jsonl")
            again = build_triplets(load_views(d / "tf" / "views.jsonl"))
            self.assertEqual(sorted(t.case_id for t in again), sorted(t.case_id for t in sel))   # same cases
            for t in again:
                tool, site = assignment(t.case_id)
                if t.erased.view_id.endswith("__tf_target"):
                    self.assertEqual(t.erased.meta["inpainter"], tool)
                    self.assertEqual(t.control.meta["tf_site"], site)
                    self.assertTrue(Path(t.control.image_path).exists())
                else:
                    self.assertEqual((tool, site), ("lama", "far"))                   # stored views kept
            self.assertGreater(sum(tool_counts(tf).values()), 0)


def answers(found, ctl_deny, esg_e, neg_claim, n=60):
    """Synthetic answers: s > 0 means present."""
    rng = np.random.default_rng(1)
    out = {}
    for i in range(n):
        c = f"c{i}"
        f = rng.random() < found
        rows = [("original", None, 1 if f else -1)]
        for tool in ("lama", "telea"):
            rows += [("erased", tool, -1 if rng.random() < esg_e else 1),
                     ("control", tool, -1 if rng.random() < ctl_deny[tool] else 1),
                     ("ring", tool, -1 if rng.random() < ctl_deny[tool] else 1)]
        for v, t, s in rows:
            vid = f"{c}_{t}_{v}"
            out[vid] = {"view_id": vid, "case_id": c, "variant": v, "tool": t, "s": s}
    for i in range(20):
        vid = f"n{i}"
        out[vid] = {"view_id": vid, "case_id": vid, "variant": "negative", "tool": None,
                    "s": 1 if rng.random() < neg_claim else -1}
    return out


class TestRule(unittest.TestCase):
    def test_rule(self):
        ctl = answers(0.9, {"lama": 0.05, "telea": 0.3}, 0.9, 0.1)
        good = answers(0.9, {"lama": 0.05, "telea": 0.0}, 0.9, 0.1)
        r = compare(good, ctl)
        self.assertLess(r["ctl_denial_telea"][2], -0.1)
        self.assertGreater(r["esg_telea"][2], 0.1)
        self.assertTrue(passes(r)["pass"])
        same = compare(ctl, ctl)
        self.assertFalse(passes(same)["pass"])
        self.assertEqual(same["esg_telea"][2], 0.0)
        worse = compare(answers(0.5, {"lama": 0.0, "telea": 0.0}, 0.9, 0.1), ctl)
        self.assertFalse(passes(worse)["checks"]["found not down > 0.03"])
        self.assertIn("PASSES", report({"good": r}, "ctl"))


if __name__ == "__main__":
    unittest.main()
