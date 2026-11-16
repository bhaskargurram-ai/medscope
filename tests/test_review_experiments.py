"""Code added for the external review (docs/REVIEW_EXPERIMENTS.md): layer-wise vision learning rates, the TV lower
bound, hard negatives, the encoder comparison helpers, the R1/R2 rules and the reader pack with a second tool."""

import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from medscope.eval.runner import load_views
from medscope.fw.analysis import answer_gap, probe_oof, tv_lower_bound, tv_report, youden_threshold
from medscope.fw.review import passes_r1, passes_r2, report
from medscope.fw.stage1 import compare
from medscope.train.sft import lr_scales
from tests.test_fw_stage1 import answers
from tests.test_runner_training import build_dataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


class TestLayerDecay(unittest.TestCase):
    NAMES = ["m.language_model.layers.3.q_proj.lora_A.weight", "m.visual.blocks.0.attn.qkv.lora_A.weight",
             "m.visual.blocks.1.attn.qkv.lora_A.weight", "m.visual.blocks.2.attn.qkv.lora_A.weight",
             "m.visual.patch_embed.proj.lora_A.weight", "m.visual.merger.mlp.0.lora_A.weight"]

    def test_decay(self):
        s = lr_scales(self.NAMES, 0.1, 0.5)
        self.assertEqual(s[self.NAMES[0]], 1.0)                      # language model at the full rate
        self.assertAlmostEqual(s[self.NAMES[3]], 0.1)                # top block
        self.assertAlmostEqual(s[self.NAMES[2]], 0.05)
        self.assertAlmostEqual(s[self.NAMES[1]], 0.025)
        self.assertAlmostEqual(s[self.NAMES[4]], 0.0125)             # patch embedding below block 0
        self.assertAlmostEqual(s[self.NAMES[5]], 0.1)                # projector with the top block

    def test_no_decay_is_the_old_behaviour(self):
        s = lr_scales(self.NAMES, 0.1, 1.0)
        self.assertEqual({s[n] for n in self.NAMES[1:]}, {0.1})
        self.assertEqual(set(lr_scales(self.NAMES).values()), {1.0})


def probe_data(sep: float, n_cases: int = 60, dim: int = 12, seed: int = 0):
    """Synthetic hidden features: erased views shifted by `sep` along one direction, ring views not."""
    rng = np.random.default_rng(seed)
    feats, scores = {}, {}
    for i in range(n_cases):
        c = f"case{i}"
        for tool in ("lama", "telea"):
            for variant, shift in (("erased", sep), ("ring", 0.0)):
                vid = f"{c}_{tool}_{variant}"
                x = rng.normal(size=(2, 2, dim))
                x[:, :, 0] += shift
                feats[vid] = x
                scores[vid] = {"view_id": vid, "case_id": c, "variant": variant, "tool": tool, "s": 0.0}
    return feats, scores


class TestTVBound(unittest.TestCase):
    def test_threshold(self):
        p = np.array([0.1, 0.2, 0.8, 0.9])
        y = np.array([0, 0, 1, 1])
        self.assertTrue(0.2 < youden_threshold(p, y) <= 0.8)

    def test_bound_tracks_separation(self):
        f0, s0 = probe_data(0.0)
        f1, s1 = probe_data(4.0)
        j0 = tv_lower_bound(probe_oof(f0, s0, "erased", "ring", "lama", "telea", 0, 0))
        j1 = tv_lower_bound(probe_oof(f1, s1, "erased", "ring", "lama", "telea", 0, 0))
        self.assertLess(abs(j0[0]), 0.25)                 # no separation: bound near zero
        self.assertGreater(j1[0], 0.8)                    # strong separation: bound near one
        self.assertLessEqual(j1[1], j1[0])
        self.assertGreaterEqual(j1[2], j1[0])
        self.assertEqual(j1[3], 60)
        res = probe_oof(f1, s1, "erased", "ring", "lama", "telea", 0, 0)
        self.assertEqual(len(res["case"]), 120)           # every test view once, out of fold
        # no case is both trained and tested in a fold: the folds are by case
        self.assertEqual(len(set(res["case"])), 60)

    def test_answer_gap_and_report(self):
        a = answers(0.9, {"lama": 0.05, "telea": 0.2}, 0.9, 0.1)
        g = answer_gap(a, "telea", "ring")
        self.assertGreater(g[0], 0.4)
        self.assertEqual(g[3], 60)
        f1, s1 = probe_data(4.0, n_cases=30)
        tv = {"erased_vs_ring/telea/last": {"by_layer": [(0.9, 0.8, 1.0, 30)], "best_layer": 0, "best": (0.9, 0.8, 1.0, 30)}}
        md = tv_report(tv, {"telea/ring": g}, 1)
        self.assertIn("lower bound", md)
        self.assertIn("erased vs ring", md)


class TestHardNegatives(unittest.TestCase):
    def test_pick_and_swap(self):
        from build_hardneg import pick_hard_negatives, swap_view
        ce = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
        cs = {"a": "Kvasir", "b": "BUSI"}
        ne = {"n1": np.array([1.0, 0.0]), "n2": np.array([0.9, 0.1]), "n3": np.array([0.0, 1.0]), "n4": np.array([1.0, 0.0])}
        ns = {"n1": "Kvasir", "n2": "Kvasir", "n3": "Kvasir", "n4": "BUSI"}
        p = pick_hard_negatives(ce, cs, ne, ns, max_sim=0.995)
        self.assertEqual(p["a"][0], "n2")                 # n1 is identical (excluded); n2 is the nearest same-source image
        self.assertEqual(p["b"][0], "n4")                 # only BUSI candidate, though dissimilar
        p2 = pick_hard_negatives(ce, cs, ne, ns, 0.995, {"a": "P1"}, {"n2": "P1"})
        self.assertEqual(p2["a"][0], "n3")                # same patient left out
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), n_cases=3))
            o = next(v for v in views if v.kind.value == "original")
            neg = replace(o, view_id="neg", image_path="/x/neg.png")
            sw = swap_view(o, neg, 0.9)
            self.assertEqual((sw.question, sw.answer, sw.lesion_box), (o.question, o.answer, o.lesion_box))
            self.assertEqual(sw.kind.value, "target_removal")
            self.assertEqual(sw.image_path, "/x/neg.png")
            self.assertEqual(sw.meta["hard_negative"], "neg")


class TestEncoderHelpers(unittest.TestCase):
    def test_crop_box(self):
        from encoder_compare import crop_box
        l, t, r, b = crop_box([400, 400, 500, 500], 1000, 800)
        self.assertEqual(r - l, b - t)                    # square
        self.assertTrue(0 <= l and r <= 1000 and 0 <= t and b <= 800)
        self.assertLessEqual(l, 400 * 1.0)
        l, t, r, b = crop_box([990, 990, 1000, 1000], 300, 300)   # at the corner: shifted inside
        self.assertEqual((r, b), (300, 300))

    def test_paired_boot(self):
        from encoder_compare import paired_boot
        rng = np.random.default_rng(0)
        y = np.array([1, 0] * 50)
        cases = np.repeat(np.arange(50), 2).astype(str)
        good = y + rng.normal(0, 0.3, 100)
        bad = rng.normal(0, 1, 100)
        r = paired_boot({"qwen": (bad, y, cases), "other": (good, y, cases)}, "qwen", n=200)
        self.assertGreater(r["other"]["auc"], 0.9)
        self.assertGreater(r["other"]["diff_lo"], 0.2)
        self.assertEqual(r["qwen"]["diff"], 0.0)


class TestReviewRules(unittest.TestCase):
    def test_r1_r2(self):
        ctl = answers(0.8, {"lama": 0.05, "telea": 0.3}, 0.7, 0.1)
        better_esg = answers(0.8, {"lama": 0.05, "telea": 0.05}, 0.7, 0.1)
        r = compare(better_esg, ctl)
        self.assertTrue(passes_r1(r)["pass"])
        self.assertFalse(passes_r2(r)["pass"])            # R2 needs more lesions found
        sees_more = compare(answers(0.95, {"lama": 0.05, "telea": 0.3}, 0.7, 0.1), ctl)
        self.assertTrue(passes_r2(sees_more)["checks"]["found up >= 0.03"])
        self.assertFalse(passes_r1(compare(ctl, ctl))["pass"])
        self.assertIn("PASSES", report("R1", "ctl", {"arm": r}, passes_r1))


class TestReaderPackTool(unittest.TestCase):
    def test_second_tool_in_pack(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            vf = build_dataset(d, n_cases=12)
            views = load_views(vf)
            # a fake "diffusion" copy of the edited views (same cases, same images; only the tool label differs)
            tool = [replace(v, view_id=v.view_id + "#sd") for v in views if v.kind.value in ("target_removal", "random_removal")]
            tf = d / "sd.jsonl"
            tf.write_text("".join(json.dumps(v.to_dict()) + "\n" for v in tool))
            from medscope.data.schema import ViewKind
            negs = [replace(v, view_id=v.view_id + "#n", case_id=v.case_id + "n", kind=ViewKind.NATURAL_NEGATIVE, answer="No")
                    for v in views if v.kind.value == "original"]
            nf = d / "neg.jsonl"
            nf.write_text("".join(json.dumps(v.to_dict()) + "\n" for v in negs))
            if not negs:
                self.skipTest("synthetic dataset has no lesion-free images")
            out = d / "pack"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_reader_study.py"), "--views", str(vf),
                                "--negatives", str(nf), "--out", str(out), "--per-kind", "1", "--tool", f"diffusion={tf}",
                                "--tool-per-kind", "2"], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            key = json.loads((out / "key.json").read_text())["items"]
            tools = [k["tool"] for k in key if k["kind"] == "target_removal"]
            self.assertIn("diffusion", tools)
            self.assertIn("lama", tools)
            self.assertEqual(len({k["case_id"] for k in key}), len(key))     # every image from a different case


if __name__ == "__main__":
    unittest.main()


class TestAPS(unittest.TestCase):
    def test_prior_removes_case_offsets(self):
        from medscope.fw.aps import evaluate, half, report
        rng = np.random.default_rng(0)
        scores, priors = {}, {}
        for i in range(200):
            c = f"c{i}"
            off = rng.normal(0, 8)                   # a case-level offset (like the reply-length bias)
            priors[c] = off + rng.normal(0, 0.1)
            for tool in ("lama", "telea"):
                for variant, base in (("erased", -2.0), ("ring", 2.0), ("control", 2.0)):
                    vid = f"{c}_{tool}_{variant}"
                    scores[vid] = {"view_id": vid, "case_id": c, "variant": variant, "tool": tool,
                                   "s": off + base + rng.normal(0, 1)}
            scores[f"{c}_o"] = {"view_id": f"{c}_o", "case_id": c, "variant": "original", "tool": None, "s": off + 2 + rng.normal(0, 1)}
        res = evaluate(scores, priors)
        self.assertEqual(res["fit"]["a"], 1.0)                                    # the full prior is subtracted
        self.assertLess(res["methods"]["raw"]["auroc_telea_ring"], 0.75)        # offsets swamp the evidence
        self.assertGreater(res["methods"]["fixed"]["auroc_telea_ring"], 0.95)   # suppression restores it
        self.assertTrue(res["rule"]["pass"])
        self.assertIn("PASSES", report(res))
        self.assertIn(half("c1"), ("A", "B"))

    def test_no_offsets_no_gain(self):
        from medscope.fw.aps import evaluate
        rng = np.random.default_rng(1)
        scores, priors = {}, {}
        for i in range(160):
            c = f"c{i}"
            priors[c] = rng.normal(0, 3)             # a prior unrelated to the scores
            for tool in ("lama", "telea"):
                for variant, base in (("erased", -1.0), ("ring", 1.0), ("control", 1.0)):
                    vid = f"{c}_{tool}_{variant}"
                    scores[vid] = {"view_id": vid, "case_id": c, "variant": variant, "tool": tool, "s": base + rng.normal(0, 1)}
        res = evaluate(scores, priors)
        self.assertFalse(res["rule"]["pass"])


class TestLeakage(unittest.TestCase):
    def test_nearest_and_exclusion(self):
        from leakage_similarity import calibration, exclusion_sets, nearest_same_source
        tr = np.eye(4)
        te = np.array([[1, 0, 0, 0], [0, 0.6, 0.8, 0], [0, 0, 0, 1.0]])
        s = nearest_same_source(te, ["A", "A", "B"], tr, ["A", "A", "B", "B"])
        self.assertAlmostEqual(s[0], 1.0)
        self.assertAlmostEqual(s[1], 0.6)                                  # only same-source training images count
        self.assertAlmostEqual(s[2], 1.0)
        drop = exclusion_sets(["x", "y", "z"], np.array([0.9, 0.5, 0.7]), ["A", "A", "B"], 0.5)
        self.assertIn("x", drop)
        self.assertNotIn("y", drop)
        drop2 = exclusion_sets(["x", "y", "z"], np.array([0.9, 0.5, 0.7]), ["SLAKE CT", "SLAKE CT", "LGG"], 0.5, ("SLAKE",))
        self.assertNotIn("z", drop2)
        rng = np.random.default_rng(0)
        centres = rng.normal(size=(10, 16))
        e = np.concatenate([centres + rng.normal(0, 0.05, (10, 16)) for _ in range(3)])
        e /= np.linalg.norm(e, axis=1, keepdims=True)
        cal = calibration(e, [f"p{i}" for i in range(10)] * 3)
        self.assertGreater(cal["auroc"], 0.95)
