import unittest

from medscope.eval.metrics import (
    abstention_specificity_gap,
    aurc,
    bootstrap,
    covered_correct_rate,
    grounded_accuracy,
    summarise,
)
from medscope.rewards import Outcome


def out(case, kind, action, correct=None, iou=0.0, conf=None, reward=0.0):
    return Outcome(f"{case}__{kind}", case, kind, action, correct, iou, conf, 0, action is None, reward, {})


def evidence_sensitive_model(n=20):
    """Answers correctly when the lesion is there, refers when it is removed."""
    outs = []
    for i in range(n):
        c = f"c{i}"
        outs += [out(c, "original", "answer", True, 0.6, 0.9, 1.5),
                 out(c, "random_removal", "answer", True, 0.5, 0.8, 1.5),
                 out(c, "target_removal", "refer", reward=1.0),
                 out(c, "degraded", "clarify", reward=0.5)]
    return outs


def always_refer_model(n=20):
    outs = []
    for i in range(n):
        for k in ("original", "random_removal", "target_removal", "degraded"):
            outs.append(out(f"c{i}", k, "refer"))
    return outs


class TestMetrics(unittest.TestCase):
    def test_evidence_sensitive_scores_high(self):
        s = summarise(evidence_sensitive_model())
        self.assertEqual(s["ccr"], 1.0)
        self.assertEqual(s["asg"], 1.0)
        self.assertEqual(s["grounded_accuracy"], 1.0)
        self.assertEqual(s["clarify_rate_degraded"], 1.0)
        self.assertEqual(s["aurc"], 0.0)

    def test_constant_referral_gets_zero_gap_and_zero_ccr(self):
        outs = always_refer_model()
        self.assertEqual(abstention_specificity_gap(outs), 0.0)
        self.assertEqual(covered_correct_rate(outs), 0.0)

    def test_grounded_accuracy_needs_overlap(self):
        outs = [out("c1", "original", "answer", True, iou=0.1)]
        self.assertEqual(grounded_accuracy(outs), 0.0)

    def test_aurc_needs_confidence(self):
        self.assertIsNone(aurc([out("c1", "original", "answer", True, conf=None)]))
        good_first = [out("a", "original", "answer", True, conf=0.9),
                      out("b", "original", "answer", False, conf=0.1)]
        bad_first = [out("a", "original", "answer", True, conf=0.1),
                     out("b", "original", "answer", False, conf=0.9)]
        self.assertLess(aurc(good_first), aurc(bad_first))

    def test_bootstrap_keeps_cases_together(self):
        res = bootstrap(evidence_sensitive_model(), n_resamples=200)
        self.assertEqual(res["asg"]["value"], 1.0)
        self.assertEqual(res["asg"]["ci_low"], 1.0)  # every case behaves the same


if __name__ == "__main__":
    unittest.main()
