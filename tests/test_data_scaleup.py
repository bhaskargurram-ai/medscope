import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.loaders.common import assign_splits, near_duplicate_groups, stable_index
from medscope.data.loaders.kvasir import scan_kvasir
from medscope.data.loaders.slake import cases_for_image, scan_lesion_images, template_questions
from tests.helpers import synthetic_case

ROOT = Path(__file__).resolve().parent.parent
MASK_TXT = "70:Liver\n95:Brain Edema\n175:Liver Cancer\n185:Brain Enhancing Tumor\n"


def make_slake(root: Path, n: int = 12):
    """Fake SLAKE: grey RGBA masks; images 0/1 are near-copies (neighbouring slices)."""
    (root / "imgs").mkdir(parents=True)
    (root / "mask.txt").write_text(MASK_TXT)
    qs = []
    for i in range(n):
        d = root / "imgs" / f"xmlab{i}"
        d.mkdir()
        img, les = synthetic_case(seed=100 if i == 1 else i + 1, lesion_center=(90 + i, 100), lesion_radius=10)
        if i == 1:
            img, les = synthetic_case(seed=1, lesion_center=(91, 100), lesion_radius=10)  # near-copy of 0
        Image.fromarray(img).save(d / "source.jpg", quality=95)
        lm = np.where(les, 175 if i % 2 else 185, 70).astype(np.uint8)
        if i == n - 1:
            lm[:] = 255  # a mask with values mask.txt doesn't list
        Image.fromarray(np.stack([lm, lm, lm, np.full_like(lm, 255)], -1)).save(d / "mask.png")
        qs.append({"qid": i, "img_name": f"xmlab{i}/source.jpg", "question": "Is there a tumor?", "answer": "Yes",
                   "q_lang": "en", "content_type": "Abnormality", "modality": "MRI"})
    (root / "train.json").write_text(json.dumps(qs))


def make_kvasir(root: Path, n: int = 6):
    for sub in ("images", "masks"):
        (root / "Kvasir-SEG" / sub).mkdir(parents=True)
    for i in range(n):
        img, les = synthetic_case(size=300, seed=i + 1, lesion_center=(120, 140), lesion_radius=30)
        Image.fromarray(img).save(root / "Kvasir-SEG" / "images" / f"cju{i}.jpg")
        Image.fromarray((les * 255).astype(np.uint8)).save(root / "Kvasir-SEG" / "masks" / f"cju{i}.jpg")


class TestGrouping(unittest.TestCase):
    def test_near_copies_share_a_group_and_split(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i, (seed, c) in enumerate([(1, (90, 100)), (1, (92, 100)), (2, (90, 100)), (3, (120, 60))]):
                img, _ = synthetic_case(seed=seed, lesion_center=c)
                p = Path(d) / f"{i}.png"
                Image.fromarray(img).save(p)
                paths.append(p)
            groups = near_duplicate_groups(paths)
        self.assertEqual(groups[0], groups[1])
        self.assertEqual(len(set(groups)), 3)
        split = assign_splits(groups)
        self.assertEqual(split[groups[0]], split[groups[1]])

    def test_split_fractions(self):
        groups = list(range(200))
        split = assign_splits(groups, seed=0)
        counts = {s: sum(1 for g in groups if split[g] == s) for s in ("train", "validation", "test")}
        self.assertEqual(counts["test"], 30)
        self.assertEqual(counts["validation"], 30)
        self.assertEqual(counts["train"], 140)

    def test_stable_index(self):
        self.assertEqual(stable_index("xmlab7", 3), stable_index("xmlab7", 3))
        self.assertEqual({stable_index(f"k{i}", 3) for i in range(30)}, {0, 1, 2})


class TestSlakeTemplates(unittest.TestCase):
    def test_templates(self):
        qs = template_questions("Brain Enhancing Tumor")
        self.assertEqual(qs[1][2], "Brain")
        self.assertIn("a tumor in the brain", qs[2][1])
        self.assertIn("edema", template_questions("Brain Edema")[2][1])

    def test_scan_and_cases(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "slake"
            make_slake(root)
            recs, stats, note = scan_lesion_images(root, Path(d) / "masks")
            self.assertEqual(len(recs), 11)
            self.assertEqual(stats["mask values don't match mask.txt"], 1)
            self.assertIn("255=", note)
            rec = recs[0]
            self.assertTrue(rec.critical)
            train = cases_for_image(rec, "train", 0)
            self.assertEqual(len(train), 3)
            self.assertEqual(train[0].question, "Is there a tumor?")       # SLAKE's own question first
            test = cases_for_image(rec, "test", 0)
            self.assertEqual(len(test), 1)
            self.assertEqual(test[0].case_id, cases_for_image(rec, "test", 0)[0].case_id)
            mask = np.asarray(Image.open(rec.mask_path)) > 127
            self.assertGreater(mask.sum(), 100)


class TestKvasir(unittest.TestCase):
    def test_scan_finds_nested_folder_and_downscales(self):
        with tempfile.TemporaryDirectory() as d:
            make_kvasir(Path(d) / "raw")
            recs, stats = scan_kvasir(Path(d) / "raw", Path(d) / "out", max_side=200)
            self.assertEqual(stats["kept"], 6)
            with Image.open(recs[0].image_path) as im:
                self.assertEqual(max(im.size), 200)
            with Image.open(recs[0].mask_path) as mm, Image.open(recs[0].image_path) as im:
                self.assertEqual(mm.size, im.size)


class TestPrepareScript(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            make_slake(d / "slake", n=20)
            make_kvasir(d / "kvasir", n=10)
            r = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_data.py"), "--slake", str(d / "slake"),
                                "--kvasir", str(d / "kvasir"), "--out", str(d / "cases")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("groups of near-copies", r.stdout)
            ids = {}
            for split in ("train", "validation", "test"):
                rows = [json.loads(l) for l in (d / "cases" / f"cases_{split}.jsonl").read_text().splitlines()]
                ids[split] = {row["patient_id"] for row in rows}
            self.assertFalse(ids["train"] & ids["test"])
            self.assertFalse(ids["train"] & ids["validation"])
            self.assertIn("kvasir_seg", (d / "cases" / "prepare_report.txt").read_text())


if __name__ == "__main__":
    unittest.main()
