"""Framework stage 0: site-matched views, the single-turn score with a fake model, and the decision tree."""

import contextlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from medscope.data.counterfactual import dilate, telea_inpaint
from medscope.data.schema import ViewKind
from medscope.eval.runner import load_views
from medscope.fw.analysis import auroc, decide, model_summary, probe_auroc, report
from medscope.fw.stage0 import (half_mask, new_views, read_scores, reference_view, ring_mask, score_views, scoreable,
                                variant_of)
from medscope.screen.probes import dev_views
from tests.test_runner_training import build_dataset


class FakeTorch:
    no_grad = staticmethod(contextlib.nullcontext)


class Val:
    def __init__(self, x):
        self.x = x

    def sum(self):
        return self.x


class FakePolicy:
    """Prefers 'present' unless the image is dark in its centre (stands in for a model that reads the image)."""
    torch = FakeTorch()

    class model:  # noqa: N801
        @staticmethod
        def eval():
            return None

    def __init__(self):
        self.calls = 0

    def encode(self, messages):
        img = None
        for m in messages:
            for part in m.get("content", []) if isinstance(m.get("content"), list) else []:
                if isinstance(part, dict) and "image" in part:
                    img = part["image"]
        return {"img": img}

    def target_ids(self, text):
        return text

    def token_logprobs_pair(self, messages, a, b, inputs=None):
        self.calls += 1
        img = inputs["img"]
        m = float(np.asarray(img).mean()) if img is not None else 0.0
        return Val(-1.0), Val(-1.0 - (m - 100) / 50)


class TestStage0(unittest.TestCase):
    def test_ring_and_half(self):
        lesion = np.zeros((200, 200), bool)
        lesion[80:120, 70:130] = True
        area = int(dilate(lesion, 5).sum())
        ring = ring_mask(lesion, area)
        self.assertIsNotNone(ring)
        self.assertFalse((ring & dilate(lesion, 2)).any())          # the lesion and a 2-pixel gap stay untouched
        self.assertGreaterEqual(ring.sum(), area)
        self.assertLess(ring.sum(), 1.6 * area)
        half = half_mask(lesion)
        self.assertAlmostEqual(half.sum() / lesion.sum(), 0.5, delta=0.05)
        tiny = np.zeros((20, 20), bool)
        tiny[2:18, 2:18] = True
        self.assertIsNone(ring_mask(tiny, 10_000, max_r=30))

    def test_views_scores_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d, n_cases=6))
            negs = [v for v in views if v.kind is ViewKind.ORIGINAL][:2]
            dev = dev_views(views, negs, n_cases=4, n_neg=2, out_dir=d / "dev")
            extra = new_views(dev, d / "s0", lama=telea_inpaint)
            got = sorted({variant_of(v) for v in extra})
            self.assertEqual(got, [("partial", "lama"), ("restored", "lama"), ("restored", "telea"),
                                   ("ring", "lama"), ("ring", "telea")])
            self.assertTrue(all(Path(v.image_path).exists() for v in extra))
            n_files = len(list((d / "s0").rglob("*.png")))
            new_views(dev, d / "s0", lama=lambda *a: (_ for _ in ()).throw(AssertionError("redone")))
            self.assertEqual(len(list((d / "s0").rglob("*.png"))), n_files)   # files reused
            originals = {v.case_id: v for v in dev if v.kind is ViewKind.ORIGINAL}
            for v in extra:
                self.assertIs(reference_view(v, originals), originals[v.case_id])
                self.assertTrue(scoreable(v, originals))
            pol = FakePolicy()
            allv = [v for v in dev + extra if v.kind is not ViewKind.ORIGINAL or v.case_id in originals]
            sc = score_views(pol, allv, originals, d / "sc.jsonl", log=lambda m: None)
            self.assertEqual(len(sc), len({v.view_id for v in allv}))
            n = pol.calls
            score_views(pol, allv, originals, d / "sc.jsonl", log=lambda m: None)
            self.assertEqual(pol.calls, n)                                     # resumed
            summ = {"recipe": model_summary(read_scores(d / "sc.jsonl")), "base": model_summary(sc)}
            dec = decide(summ, None, agree=0.9)
            self.assertIn("branch", dec)
            self.assertIn("Branch", report(summ, None, dec))

    def test_auroc(self):
        self.assertEqual(auroc(np.array([2, 3]), np.array([0, 1])), 1.0)
        self.assertEqual(auroc(np.array([0, 1]), np.array([2, 3])), 0.0)
        self.assertEqual(auroc(np.array([1, 1]), np.array([1, 1])), 0.5)

    def test_decision_tree(self):
        def summ(site, far, auc=0.8):
            t = {"site_effect": site, "far_effect": far, "site_minus_far": site - far, "auroc_site": auc}
            return {"lama": dict(t), "telea": dict(t)}
        s = {"recipe": summ(0.30, 0.05), "base": summ(0.05, 0.05)}
        self.assertTrue(decide(s, None, 0.9)["site_shortcut_any"])
        self.assertTrue(decide(s, None, 0.9)["branch"].startswith("A:"))
        s2 = {"recipe": summ(0.06, 0.05), "base": summ(0.05, 0.05)}
        probes = {"erased_vs_ring/telea/last": [0.7, 0.9], "erased_vs_ring/telea/image": [0.6, 0.7]}
        self.assertTrue(decide(s2, probes, 0.9)["branch"].startswith("B:"))
        self.assertTrue(decide(s2, None, 0.9)["branch"].startswith("C:"))
        self.assertTrue(decide(s, None, 0.5)["branch"].startswith("invalid"))
        s3 = {"recipe": summ(0.30, 0.05), "base": summ(0.28, 0.05)}         # the base model reacts the same way
        self.assertFalse(decide(s3, None, 0.9)["site_shortcut_any"])

    def test_probe(self):
        rng = np.random.default_rng(0)
        scores, feats = {}, {}
        for i in range(60):
            c = f"c{i}"
            for tool in ("lama", "telea"):
                for variant, y in (("ring", 1), ("erased", 0)):
                    vid = f"{c}_{tool}_{variant}"
                    scores[vid] = {"case_id": c, "variant": variant, "tool": tool, "s": 0.0}
                    x = rng.normal(size=(2, 2, 16)).astype(np.float16)
                    x[1, :, 0] += 3 * y                                       # layer 1 carries the label
                    feats[vid] = x
        self.assertGreater(probe_auroc(feats, scores, "ring", "erased", "lama", "telea", 1, 0), 0.9)
        self.assertLess(abs(probe_auroc(feats, scores, "ring", "erased", "lama", "telea", 0, 0) - 0.5), 0.2)


if __name__ == "__main__":
    unittest.main()
