"""Lead 4 (docs/PREREGISTRATION_v10.md): the parts that need no GPU."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from medscope.agent.episode import Generation
from medscope.data.counterfactual import telea_inpaint
from medscope.data.schema import ViewKind
from medscope.eval.runner import evaluate, load_views
from medscope.mas.arbiter import (ABLATIONS, ARBITER_PROMPT, arbiter_messages, arbiter_sample, reports_text,
                                  stratified_subset, training_drop)
from medscope.mas.evaluate import arbiter_episodes
from medscope.mas.reports import (BLIND_QUESTION, candidate_box, compute_reports, read_reports, verify_images,
                                  view_rng)
from medscope.mas.specialist import patient_split, regions_from_prob, training_images, youden_threshold
from medscope.rewards import load_config, with_vocab
from tests.test_runner_training import build_dataset

CFG = load_config()
YES_BOX = '<final>{"action": "answer", "answer": "Yes", "box": [300, 340, 420, 460], "confidence": 0.8}</final>'


class Reader:
    """Fake reader: 'Yes' with a box to the question, 'No' to the blind question; records what it was asked."""

    def __init__(self):
        self.questions = []

    def generate(self, messages, sample=False):
        q = messages[-1]["content"][-1]["text"]
        self.questions.append(q)
        if BLIND_QUESTION in q:
            return Generation('<final>{"action": "answer", "answer": "No", "confidence": 0.6}</final>')
        return Generation(YES_BOX)


class FakeSpecialist:
    threshold = 0.4

    def report(self, image):
        return {"peak": 0.9, "threshold": 0.4, "found": True, "regions": [{"box": [100, 100, 200, 200], "score": 0.9}]}


REP = {"direct": {"action": "answer", "answer": "Yes", "box": [10, 10, 50, 50], "confidence": 0.9},
       "blind": {"action": "answer", "answer": "No", "box": None, "confidence": 0.7},
       "specialist": {"peak": 0.2, "threshold": 0.4, "found": False, "regions": []},
       "verify": {"box": [10, 10, 50, 50], "source": "direct reader", "note": "",
                  "erased": {"action": "answer", "answer": "Yes", "box": [10, 10, 50, 50], "confidence": 0.8},
                  "control": {"action": "answer", "answer": "Yes", "box": [10, 10, 50, 50], "confidence": 0.8}}}


class TestSpecialistHelpers(unittest.TestCase):
    def test_training_images_use_only_unedited_images(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), n_cases=4))
            items = training_images(views)
            self.assertEqual(len(items), 4)                       # one per original image; edits ignored
            self.assertTrue(all(len(t.mask_paths) == 1 for t in items))
            self.assertTrue(all("original" in t.image_path for t in items))

    def test_patient_split_is_disjoint(self):
        from medscope.mas.specialist import TrainImage
        items = [TrainImage(f"img{i}.png", [], f"p{i // 2}") for i in range(40)]
        tr, va = patient_split(items, val_frac=0.2)
        self.assertEqual(len(tr) + len(va), 40)
        self.assertFalse({t.patient_id for t in tr} & {t.patient_id for t in va})

    def test_regions_from_prob(self):
        p = np.zeros((200, 200), dtype=np.float32)
        p[20:60, 20:60] = 0.9
        p[100:150, 100:180] = 0.7
        p[190:191, 190:191] = 0.95                                # below the minimum area
        regs = regions_from_prob(p)
        self.assertEqual(len(regs), 2)
        self.assertEqual(regs[0].score, 0.9)
        self.assertEqual(regs[0].box, [100, 100, 300, 300])

    def test_youden_threshold(self):
        t = youden_threshold([0.1, 0.2, 0.3, 0.8, 0.9, 0.7], [False, False, False, True, True, True])
        self.assertTrue(0.3 < t <= 0.7)


class TestReports(unittest.TestCase):
    def test_candidate_box_order(self):
        spec = {"found": True, "regions": [{"box": [1, 1, 9, 9], "score": 0.9}]}
        blind = {"action": "answer", "box": [5, 5, 50, 50]}
        self.assertEqual(candidate_box({"action": "answer", "box": [2, 2, 8, 8]}, spec, blind), ([2, 2, 8, 8], "direct reader"))
        self.assertEqual(candidate_box({"action": "answer", "answer": "No"}, spec, blind)[1], "specialist")
        self.assertEqual(candidate_box({"action": "refer"}, {"found": False}, blind)[1], "question-blind reader")
        self.assertEqual(candidate_box({"action": "refer"}, {"found": False}, {"action": "answer"}), (None, None))

    def test_verify_images(self):
        from tests.helpers import synthetic_case
        img, _ = synthetic_case()
        erased, control, note = verify_images(img, [300, 340, 420, 460], telea_inpaint, view_rng("x"))
        self.assertEqual(note, "")
        self.assertFalse(np.array_equal(erased, img))
        self.assertFalse(np.array_equal(control, img))
        self.assertFalse(np.array_equal(erased, control))
        self.assertEqual(verify_images(img, [0, 0, 900, 900], telea_inpaint, view_rng("x"))[2], "region too large to test")

    def test_compute_reports_resumes_and_never_uses_gold(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d, n_cases=2))
            cfg = with_vocab(CFG, views)
            pol = Reader()
            reps = compute_reports(pol, FakeSpecialist(), telea_inpaint, views, cfg, d / "r.jsonl", adapter="a",
                                   batch_size=3, log=lambda m: None)
            self.assertEqual(set(reps), {v.view_id for v in views})
            r = next(iter(reps.values()))
            self.assertEqual(r["direct"]["answer"], "Yes")
            self.assertEqual(r["blind"]["answer"], "No")
            self.assertEqual(r["verify"]["source"], "direct reader")
            self.assertIsNotNone(r["verify"]["erased"])
            self.assertTrue(any(BLIND_QUESTION in q for q in pol.questions))
            text = (d / "r.jsonl").read_text()
            self.assertNotIn("target_removal\"", json.dumps([json.loads(x)["direct"] for x in text.splitlines()]))
            n = len(pol.questions)
            compute_reports(pol, FakeSpecialist(), telea_inpaint, views, cfg, d / "r.jsonl", adapter="a",
                            log=lambda m: None)
            self.assertEqual(len(pol.questions), n)                       # nothing recomputed
            self.assertEqual(len(read_reports(d / "r.jsonl")), len(views))


class TestArbiter(unittest.TestCase):
    def test_reports_text_and_ablations(self):
        full = reports_text(REP)
        self.assertIn('answered "Yes"', full)
        self.assertIn("After an equal edit elsewhere", full)
        self.assertIn("found nothing above its threshold", full)
        noc = reports_text(REP, ABLATIONS["noc"])
        self.assertNotIn("After an equal edit elsewhere", noc)
        self.assertIn("erased the region", noc)
        direct_only = reports_text(REP, ABLATIONS["dir"])
        self.assertEqual(direct_only.count("report not available"), 3)

    def test_drop_rate(self):
        rng = np.random.default_rng(0)
        drops = [training_drop(rng) for _ in range(4000)]
        for part in ("blind", "specialist", "verify", "control"):
            self.assertAlmostEqual(np.mean([part in x for x in drops]), 0.25, delta=0.03)

    def test_sample_targets_follow_the_view(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), n_cases=1))
            by_kind = {v.kind: v for v in views}
            s = arbiter_sample(by_kind[ViewKind.TARGET_REMOVAL], REP, 0, 3)
            self.assertEqual(s.messages[0]["content"][0]["text"], ARBITER_PROMPT)
            self.assertIn('"answer": "No"', s.target)
            self.assertIn('"box"', arbiter_sample(by_kind[ViewKind.ORIGINAL], REP, 0, 3).target)
            self.assertIn("clarify", arbiter_sample(by_kind[ViewKind.DEGRADED], REP, 0, 3).target)
            again = arbiter_sample(by_kind[ViewKind.TARGET_REMOVAL], REP, 0, 3)
            self.assertEqual(s.target, again.target)
            self.assertEqual(s.messages[1]["content"][1]["text"], again.messages[1]["content"][1]["text"])

    def test_stratified_subset(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), n_cases=10))
            sub = stratified_subset(views, 20)
            kinds = {}
            for v in sub:
                kinds[v.kind] = kinds.get(v.kind, 0) + 1
            self.assertEqual(set(kinds.values()), {5})
            self.assertEqual(sub, stratified_subset(views, 20))

    def test_arbiter_episodes_score_like_any_run(self):
        class Arbiter:
            def generate(self, messages, sample=False):
                assert "Team reports:" in messages[-1]["content"][-1]["text"]
                return Generation('<final>{"action": "answer", "answer": "No", "confidence": 0.7}</final>')
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d, n_cases=3))
            cfg = with_vocab(CFG, views)
            reports = {v.view_id: REP for v in views}
            pol = Arbiter()
            s = evaluate(pol, views, cfg, d / "run", {"name": "mas", "split": "test", "precision": "x|mas"},
                         n_bootstrap=20, log=lambda m: None, episodes=arbiter_episodes(pol, cfg, reports, ABLATIONS["full"]))
            self.assertEqual(s["n_views"], len(views))
            self.assertEqual(s["metrics"]["target_hallucination_rate"]["value"], 0.0)   # always "No"
            self.assertEqual(s["metrics"]["ccr"]["value"], 0.0)
            tr = (d / "run" / "transcripts.jsonl").read_text()
            self.assertIn("Team reports", tr)

    def test_messages_hold_the_image(self):
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        m = arbiter_messages(img, "Is there a polyp?", REP)
        self.assertEqual(m[1]["content"][0]["type"], "image")
        self.assertIn("Question: Is there a polyp?", m[1]["content"][1]["text"])


if __name__ == "__main__":
    unittest.main()
