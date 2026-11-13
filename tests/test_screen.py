"""Screening stage A: policies, gold-free reading of reports, and the pass rule."""

import tempfile
import unittest
from pathlib import Path

from medscope.data.schema import ViewKind
from medscope.eval.runner import load_views
from medscope.rewards import load_config, with_vocab
from medscope.screen.stage_a import (ABSENT, FOLLOW, PRESENT, REFER, absent_text, features, final_for, half_of,
                                     passes, report_md, rule_policies, run_screen, says_present)
from tests.test_runner_training import build_dataset

CFG = load_config()


def rep_for(view):
    """Reports where the direct reader always claims, and the other agents tell the truth."""
    present = view.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL)
    yes = {"action": "answer", "answer": "Yes", "box": [300, 340, 420, 460], "confidence": 0.8}
    no = {"action": "answer", "answer": "No", "confidence": 0.8}
    return {"direct": yes, "blind": yes if present else no,
            "specialist": {"peak": 0.99 if present else 0.1, "threshold": 0.9, "found": present,
                           "regions": [{"box": [300, 340, 420, 460], "score": 0.99}] if present else []},
            "verify": {"box": [300, 340, 420, 460], "source": "direct reader", "note": "",
                       "erased": no if present else yes, "control": yes}}


class TestStageA(unittest.TestCase):
    def test_reading_replies_without_gold(self):
        self.assertTrue(says_present({"action": "answer", "answer": "Yes"}, "Is there a polyp?"))
        self.assertFalse(says_present({"action": "answer", "answer": "No polyp seen"}, "Is there a polyp?"))
        self.assertTrue(says_present({"action": "answer", "answer": "No"}, "Is the liver healthy?"))
        self.assertFalse(says_present({"action": "answer", "answer": "Yes"}, "Is the liver healthy?"))
        self.assertIsNone(says_present({"action": "refer"}, "Is there a polyp?"))
        self.assertEqual(absent_text("Is the liver healthy?"), "Yes")
        self.assertEqual(absent_text("What abnormality is seen?"), "No abnormality")

    def test_policies_and_screen(self):
        with tempfile.TemporaryDirectory() as d:
            views = [v for v in load_views(build_dataset(Path(d), n_cases=12))]
            reps = {v.view_id: rep_for(v) for v in views}
            cfg = with_vocab(CFG, views)
            f = features(views[1], reps[views[1].view_id])
            self.assertEqual(final_for(ABSENT, f).answer, "No")
            self.assertEqual(final_for(REFER, f).kind.value, "refer")
            self.assertEqual(final_for(PRESENT, f).answer, "Yes")
            pols = rule_policies()
            self.assertGreater(len(pols), 80)
            rows = run_screen(views, reps, cfg, log=lambda m: None)
            self.assertEqual(rows[0]["policy"], "baseline")
            # with truthful agents a specialist veto must beat always-yes on erased-lesion claims
            veto = next(r for r in rows if r["policy"] == f"veto: direct claims, specialist peak < 0.5 -> {ABSENT}")
            self.assertLess(veto["A"]["target_hallucination_rate"] + veto["B"]["target_hallucination_rate"],
                            rows[0]["A"]["target_hallucination_rate"] + rows[0]["B"]["target_hallucination_rate"])
            self.assertIn("policies screened", report_md(rows))
            self.assertEqual(pols["baseline: keep the direct reader"](f), FOLLOW)

    def test_halves_and_rule(self):
        self.assertIn(half_of("case1"), "AB")
        self.assertEqual(half_of("case1"), half_of("case1"))
        base = {"net_utility": 0.5, "esg": 0.5, "ccr": 0.8, "natural_hallucination_rate": 0.1}
        self.assertTrue(passes({"net_utility": 0.55, "esg": 0.53, "ccr": 0.79, "natural_hallucination_rate": 0.1}, base))
        self.assertFalse(passes({"net_utility": 0.6, "esg": 0.5, "ccr": 0.8, "natural_hallucination_rate": 0.1}, base))
        self.assertFalse(passes({"net_utility": 0.6, "esg": 0.6, "ccr": 0.7, "natural_hallucination_rate": 0.1}, base))


if __name__ == "__main__":
    unittest.main()
