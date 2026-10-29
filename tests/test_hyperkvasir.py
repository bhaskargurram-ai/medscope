import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.colab import negatives_by_domain
from medscope.data.loaders.hyperkvasir import class_of, is_dark_or_blank, scan_landmarks
from tests.helpers import synthetic_case
from tests.test_natural_negatives import make_slake_with_negatives

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from train_grpo import mix_in  # noqa: E402


def make_landmarks(root: Path, n: int = 12):
    for i in range(n):
        c = ("cecum", "retroflex-rectum", "ileum")[i % 3]
        d = root / "labeled-images" / "lower-gi-tract" / "anatomical-landmarks" / c
        d.mkdir(parents=True, exist_ok=True)
        img, _ = synthetic_case(size=300, seed=200 + i)
        Image.fromarray(img).save(d / f"img{i}.jpg")
    dark = root / "labeled-images" / "lower-gi-tract" / "anatomical-landmarks" / "ileum" / "black.jpg"
    Image.fromarray(np.zeros((300, 300, 3), np.uint8)).save(dark)
    other = root / "labeled-images" / "lower-gi-tract" / "pathological-findings" / "polyps"
    other.mkdir(parents=True)
    Image.fromarray(synthetic_case(seed=999)[0]).save(other / "p.jpg")


class TestHyperKvasir(unittest.TestCase):
    def test_class_of(self):
        self.assertEqual(class_of("labeled-images/lower-gi-tract/anatomical-landmarks/normal-cecum/x.jpg"), "cecum")
        self.assertEqual(class_of("lower-gi-tract/anatomical-landmarks/cecum/x.jpg"), "cecum")
        self.assertEqual(class_of("a/retroflex-rectum/x.jpg"), "retroflex-rectum")
        self.assertIsNone(class_of("labeled-images/lower-gi-tract/pathological-findings/polyps/x.jpg"))

    def test_scan_skips_polyps_and_downscales(self):
        with tempfile.TemporaryDirectory() as d:
            make_landmarks(Path(d) / "hk")
            items, stats = scan_landmarks(Path(d) / "hk", Path(d) / "out", max_side=200)
            self.assertEqual(sum(stats.values()), 13)                 # 12 + the dark frame, no polyp
            self.assertEqual(sum(is_dark_or_blank(p) for _, p, _ in items), 1)
            with Image.open(items[0][1]) as im:
                self.assertEqual(max(im.size), 200)

    def test_build_negatives_with_hyperkvasir_splits(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            make_slake_with_negatives(d / "slake")
            make_landmarks(d / "hk", n=40)
            r = subprocess.run([sys.executable, str(ROOT / "scripts/build_negatives.py"), "--slake", str(d / "slake"),
                                "--out", str(d / "neg"), "--hyperkvasir", str(d / "hk")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = {s: [json.loads(l) for l in (d / "neg" / f).read_text().splitlines()]
                    for s, f in [("test", "views_negatives.jsonl"), ("train", "views_negatives_train.jsonl"),
                                 ("val", "views_negatives_val.jsonl")]}
            self.assertEqual(sum(r["case_id"].startswith("slakeneg_") for r in rows["test"]), 2)  # SLAKE stays test
            self.assertFalse(any(r["case_id"].startswith("slakeneg_") for r in rows["train"]))
            self.assertGreater(len(rows["train"]), len(rows["val"]))
            groups = {s: {r["patient_id"] for r in rs if r["case_id"].startswith("hkneg_")} for s, rs in rows.items()}
            self.assertFalse(groups["train"] & groups["test"])
            self.assertTrue(all(r["answer"] == "No" for r in rows["train"]))
            self.assertIn("HyperKvasir", (d / "neg" / "negatives_report.txt").read_text())

    def test_mix_in_share(self):
        views, negs = list(range(80)), ["n1", "n2", "n3"]
        mixed = mix_in(views, negs, 0.2)
        self.assertEqual(len(mixed), 100)
        self.assertEqual(sum(isinstance(x, str) for x in mixed), 20)
        self.assertEqual(mix_in(views, [], 0.2), views)

    def test_negatives_by_domain(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "neg_sft_agentic"
            run.mkdir()
            recs = [{"view_id": "v1", "case_id": "slakeneg_a", "action": "refer", "correct": None},
                    {"view_id": "v2", "case_id": "slakeneg_b", "action": "answer", "correct": False},
                    {"view_id": "v3", "case_id": "hkneg_c", "action": "answer", "correct": True}]
            (run / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
            table = negatives_by_domain(d)
            self.assertIn("| sft_agentic | SLAKE CT/MRI (cross-domain) | 2 | 50% | 50% | 50% |", table)
            self.assertIn("| sft_agentic | HyperKvasir colonoscopy (in-domain) | 1 | 0% | 100% | 0% |", table)


if __name__ == "__main__":
    unittest.main()


class TestDomainTableUsesCurrentTestSet(unittest.TestCase):
    def test_stale_views_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "neg_base"
            run.mkdir()
            recs = [{"view_id": "hkneg_a__natural_negative", "case_id": "hkneg_a", "action": "refer", "correct": None},
                    {"view_id": "hkneg_old__natural_negative", "case_id": "hkneg_old", "action": "answer", "correct": False}]
            (run / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
            views = Path(d) / "views.jsonl"
            views.write_text(json.dumps({"view_id": "hkneg_a__natural_negative"}))
            self.assertIn("| base | HyperKvasir colonoscopy (in-domain) | 1 | 0% | 100% | 100% |",
                          negatives_by_domain(d, views))
