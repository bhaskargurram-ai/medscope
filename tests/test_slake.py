import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.loaders.slake import (
    detect_encoding,
    keep_question,
    lesion_ids,
    load_slake,
    parse_mask_labels,
    read_label_map,
)

MASK_TXT = """30: Left Lung
55: Liver
120 Liver Cancer
200:Brain Edema
"""


def make_release(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "mask.txt").write_text(MASK_TXT, encoding="utf-8")
    for name, label_ids in {"xmlab1": [55, 120], "xmlab2": [30]}.items():
        d = root / "imgs" / name
        d.mkdir(parents=True)
        Image.fromarray(np.full((64, 64, 3), 100, np.uint8)).save(d / "source.jpg")
        lm = np.zeros((64, 64), np.uint8)
        lm[10:40, 10:40] = label_ids[0]
        if len(label_ids) > 1:
            lm[20:28, 20:28] = label_ids[1]
        Image.fromarray(lm).save(d / "mask.png")
    qs = [
        {"qid": 1, "img_name": "xmlab1/source.jpg", "question": "Does the liver look abnormal?",
         "answer": "Yes", "q_lang": "en", "content_type": "Abnormal", "modality": "CT"},
        {"qid": 2, "img_name": "xmlab1/source.jpg", "question": "Is the liver healthy?",
         "answer": "No", "q_lang": "en", "content_type": "Abnormal", "modality": "CT"},
        {"qid": 3, "img_name": "xmlab1/source.jpg", "question": "Which organ is this?",
         "answer": "Liver", "q_lang": "en", "content_type": "Organ", "modality": "CT"},
        {"qid": 4, "img_name": "xmlab2/source.jpg", "question": "Is there a tumor?",
         "answer": "Yes", "q_lang": "en", "content_type": "Abnormal", "modality": "X-Ray"},
        {"qid": 5, "img_name": "xmlab1/source.jpg", "question": "肝脏是否正常？",
         "answer": "否", "q_lang": "zh", "content_type": "Abnormal", "modality": "CT"},
    ]
    (root / "train.json").write_text(json.dumps(qs), encoding="utf-8")


class TestMaskEncodings(unittest.TestCase):
    """mask.png may store ids in different ways; the loader must work out which from the data."""

    IDS = {30: "Left Lung", 55: "Liver", 120: "Liver Cancer"}

    def label_map(self):
        lm = np.zeros((40, 40), np.uint8)
        lm[5:30, 5:30] = 55
        lm[10:15, 10:15] = 120
        lm[30:38, 2:10] = 30
        return lm

    def save(self, d: Path, arr, n=3):
        paths = []
        for i in range(n):
            p = d / f"m{i}.png"
            Image.fromarray(arr).save(p)
            paths.append(p)
        return paths

    def test_detects_each_encoding(self):
        lm = self.label_map()
        rng = np.random.default_rng(0)
        colour = rng.integers(0, 256, (40, 40), dtype=np.uint8)
        cases = {
            "single": lm,
            "red": np.stack([lm, colour, colour[::-1]], -1),
            "blue": np.stack([colour, colour[::-1], lm], -1),
        }
        with tempfile.TemporaryDirectory() as d:
            for expected, arr in cases.items():
                sub = Path(d) / expected
                sub.mkdir()
                enc, why = detect_encoding(self.save(sub, arr), set(self.IDS))
                self.assertEqual(enc, expected, why)
                decoded = read_label_map(sub / "m0.png", enc)
                np.testing.assert_array_equal(decoded, lm)

    def test_rgba_grey_mask(self):
        lm = self.label_map()
        rgba = np.stack([lm, lm, lm, np.full_like(lm, 255)], -1)
        with tempfile.TemporaryDirectory() as d:
            enc, _ = detect_encoding(self.save(Path(d), rgba), set(self.IDS))
            self.assertEqual(enc, "single")

    def test_real_slake_shape_grey_rgba_with_some_odd_masks(self):
        """As seen on Colab: grey RGBA masks fit perfectly, a minority hold unlisted values."""
        lm = self.label_map()
        good = np.stack([lm, lm, lm, np.full_like(lm, 255)], -1)
        odd = np.stack([np.full_like(lm, 100)] * 3 + [np.full_like(lm, 255)], -1)  # 100 is not an id
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            paths = []
            for i, arr in enumerate([good] * 7 + [odd] * 3):
                Image.fromarray(arr).save(d / f"m{i}.png")
                paths.append(d / f"m{i}.png")
            enc, why = detect_encoding(paths, set(self.IDS))  # mean fit 70%, median 100%
            self.assertIn(enc, ("single", "red"), why)

    def test_unknown_colours_fail_with_a_useful_message(self):
        lm = self.label_map()
        palette = {0: (0, 0, 0), 55: (200, 30, 90), 120: (10, 240, 17), 30: (77, 77, 250)}
        rgb = np.zeros((40, 40, 3), np.uint8)
        for i, c in palette.items():
            rgb[lm == i] = c
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as ctx:
                detect_encoding(self.save(Path(d), rgb), set(self.IDS))
        msg = str(ctx.exception)
        self.assertIn("most common colours", msg)
        self.assertIn("(200, 30, 90)", msg)


class TestSlake(unittest.TestCase):
    def test_label_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mask.txt"
            p.write_text(MASK_TXT)
            labels = parse_mask_labels(p)
        self.assertEqual(labels[120], "Liver Cancer")
        self.assertEqual(lesion_ids(labels), {120, 200})

    def test_question_filter(self):
        base = {"q_lang": "en", "content_type": "Abnormal"}
        self.assertTrue(keep_question(base | {"question": "Is there a tumor?", "answer": "Yes"}))
        self.assertFalse(keep_question(base | {"question": "Is there a tumor?", "answer": "No"}))
        self.assertTrue(keep_question(base | {"question": "Is the lung healthy?", "answer": "No"}))
        self.assertFalse(keep_question(base | {"question": "Is the lung healthy?", "answer": "Yes"}))
        self.assertTrue(keep_question(base | {"question": "Where is the abnormality?", "answer": "Left lung"}))

    def test_load_keeps_only_cases_with_lesions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "slake"
            make_release(root)
            splits, report = load_slake(root, Path(d) / "masks")
            cases = splits["train"]
            self.assertEqual(sorted(c.case_id for c in cases), ["slake_1", "slake_2"])
            mask = np.asarray(Image.open(cases[0].mask_path)) > 127
            self.assertEqual(mask.sum(), 64)              # only the 8x8 cancer, not the liver
            self.assertEqual(report.dropped["no lesion pixels in mask"], 1)  # xmlab2 has no lesion
            self.assertEqual(report.lesion_pixels_by_label["Liver Cancer"], 1)

    def test_forced_encoding_and_odd_mask_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "slake"
            make_release(root)
            # turn xmlab1's mask into grey RGBA (as in real SLAKE) and xmlab2's into unlisted values
            lm = np.asarray(Image.open(root / "imgs/xmlab1/mask.png"))
            Image.fromarray(np.stack([lm, lm, lm, np.full_like(lm, 255)], -1)).save(root / "imgs/xmlab1/mask.png")
            Image.fromarray(np.full((64, 64), 99, np.uint8)).save(root / "imgs/xmlab2/mask.png")
            splits, report = load_slake(root, Path(d) / "masks", encoding="red")
            self.assertEqual(sorted(c.case_id for c in splits["train"]), ["slake_1", "slake_2"])
            self.assertEqual(report.dropped["mask values don't match mask.txt"], 1)
            self.assertIn("set by hand", report.summary())


if __name__ == "__main__":
    unittest.main()
