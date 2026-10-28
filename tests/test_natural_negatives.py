import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.actions import parse
from medscope.agent.episode import Generation
from medscope.data.loaders.slake import keep_negative_question, scan_natural_negatives
from medscope.data.schema import View, ViewKind
from medscope.eval.runner import evaluate, load_views
from medscope.rewards import load_config, score
from tests.helpers import synthetic_case

ROOT = Path(__file__).resolve().parent.parent
CFG = load_config()


def make_slake_with_negatives(root: Path):
    """xmlab0: healthy liver (negative question). xmlab1: liver cancer in the mask, so its
    'No' question must be rejected. xmlab2: healthy, asked 'Is the liver healthy?' -> Yes."""
    (root / "imgs").mkdir(parents=True)
    (root / "mask.txt").write_text("70:Liver\n175:Liver Cancer\n")
    qs = []
    for i in range(3):
        d = root / "imgs" / f"xmlab{i}"
        d.mkdir()
        img, les = synthetic_case(seed=i + 1)
        Image.fromarray(img).save(d / "source.jpg", quality=95)
        lm = np.where(les, 175 if i == 1 else 70, 0).astype(np.uint8)
        Image.fromarray(np.stack([lm, lm, lm, np.full_like(lm, 255)], -1)).save(d / "mask.png")
    base = {"q_lang": "en", "content_type": "Abnormality", "modality": "CT"}
    qs += [base | {"qid": 1, "img_name": "xmlab0/source.jpg", "question": "Does the picture contain liver cancer?", "answer": "No"},
           base | {"qid": 2, "img_name": "xmlab1/source.jpg", "question": "Is there a tumor in the lung?", "answer": "No"},
           base | {"qid": 3, "img_name": "xmlab2/source.jpg", "question": "Is the liver healthy?", "answer": "Yes"},
           base | {"qid": 4, "img_name": "xmlab2/source.jpg", "question": "Which organ is this?", "answer": "Liver",
                   "content_type": "Organ"}]
    (root / "train.json").write_text(json.dumps(qs))


class AlwaysYes:
    def generate(self, messages, sample=False):
        return Generation('<final>{"action": "answer", "answer": "Yes", "confidence": 0.9}</final>')


def neg_view(answer="No"):
    return View("n1__natural_negative", "n1", "p1", ViewKind.NATURAL_NEGATIVE, "x.png",
                "Is there a tumor in the liver?", answer, [], None, False)


class TestNaturalNegatives(unittest.TestCase):
    def test_question_filter(self):
        base = {"q_lang": "en", "content_type": "Abnormality"}
        self.assertTrue(keep_negative_question(base | {"question": "Is there a tumor?", "answer": "No"}))
        self.assertTrue(keep_negative_question(base | {"question": "Is the lung healthy?", "answer": "Yes"}))
        self.assertFalse(keep_negative_question(base | {"question": "Is there a tumor?", "answer": "Yes"}))
        self.assertFalse(keep_negative_question(base | {"question": "Is the lung healthy?", "answer": "No"}))

    def test_both_sources_must_agree(self):
        with tempfile.TemporaryDirectory() as d:
            make_slake_with_negatives(Path(d) / "slake")
            items, stats = scan_natural_negatives(Path(d) / "slake")
            self.assertEqual(sorted(k for k, _, _ in items), ["xmlab0", "xmlab2"])
            self.assertEqual(stats["mask shows a lesion (question is about something else)"], 1)

    def test_rewards(self):
        no = parse('<final>{"action": "answer", "answer": "No tumor is seen."}</final>').final
        yes = parse('<final>{"action": "answer", "answer": "Yes"}</final>').final
        refer = parse('<final>{"action": "refer"}</final>').final
        self.assertEqual(score(neg_view(), no, CFG).reward, 1.0)
        self.assertEqual(score(neg_view(), yes, CFG).reward, -2.0)       # hallucinated finding
        self.assertEqual(score(neg_view(), refer, CFG).reward, 0.5)

    def test_end_to_end_always_yes_model_hallucinates(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            make_slake_with_negatives(d / "slake")
            r = subprocess.run([sys.executable, str(ROOT / "scripts/build_negatives.py"),
                                "--slake", str(d / "slake"), "--out", str(d / "neg")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            views = load_views(d / "neg" / "views_negatives.jsonl")
            self.assertEqual(len(views), 2)
            s = evaluate(AlwaysYes(), views, CFG, d / "run", {"name": "yes", "split": "natural_negatives"},
                         n_bootstrap=20, log=lambda m: None)
            m = s["metrics"]
            # "Yes" is a hallucination for "contain liver cancer?" (No) but right for "liver healthy?" (Yes)
            self.assertEqual(m["natural_hallucination_rate"]["value"], 0.5)
            self.assertEqual(m["natural_correct_rate"]["value"], 0.5)
            self.assertIn("natural_negative", (d / "run" / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
