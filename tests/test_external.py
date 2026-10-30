import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.loaders import external
from tests.helpers import synthetic_case


class TestExternal(unittest.TestCase):
    def make_medclipseg(self, root: Path, n=6, mask_prefix="mask_"):
        img_dir, lab_dir = root / "BUSBRA" / "Test_Folder" / "img", root / "BUSBRA" / "Test_Folder" / "label"
        img_dir.mkdir(parents=True), lab_dir.mkdir(parents=True)
        for i in range(n):
            img, lesion = synthetic_case(size=200, seed=i)
            Image.fromarray(img).save(img_dir / f"bus_{i:04d}-l.png")
            m = (lesion * 255).astype(np.uint8) if i % 3 else np.zeros_like(lesion, np.uint8)
            Image.fromarray(m).save(lab_dir / f"{mask_prefix}{i:04d}-l.png")

    def test_pairs_and_records(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.make_medclipseg(d / "zip")
            pairs = external.pair_files(*external.find_test_folder(d / "zip"))
            self.assertEqual(len(pairs), 6)
            stats = Counter()
            cases, negs = external.records_from_pairs("breast", pairs, d / "out", cap=10, stats=stats)
            self.assertEqual((len(cases), len(negs)), (4, 2))
            self.assertTrue(all(c.modality == "ultrasound" and c.answer == "Yes" for c in cases))
            self.assertTrue(all(v.answer == "No" and v.case_id.startswith("busbraext") for v in negs))
            self.assertEqual(len({c.case_id for c in cases} | {v.case_id for v in negs}), 6)

    def test_brats_slices(self):
        vol = np.zeros((40, 40, 60), np.float32)
        vol[5:35, 5:35, 10:55] = 100.0
        seg = np.zeros_like(vol)
        seg[15:20, 15:20, 40:44] = 2
        seg[14:22, 14:22, 42] = 1
        pos, neg = external.slices_from_volume(vol, seg)
        self.assertEqual(pos, 42)
        self.assertIsNotNone(neg)
        self.assertEqual(seg[:, :, neg].sum(), 0)
        self.assertGreaterEqual(abs(neg - pos), 10)


if __name__ == "__main__":
    unittest.main()
