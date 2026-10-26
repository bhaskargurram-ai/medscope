import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.loaders.slake import keep_question, lesion_ids, load_slake, parse_mask_labels

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


if __name__ == "__main__":
    unittest.main()
