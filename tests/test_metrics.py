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


class TestEvidenceSensitivity(unittest.TestCase):
    def test_esg_rewards_reading_the_lesion_not_constant_replies(self):
        from medscope.eval.metrics import evidence_sensitivity_gap

        def model(target, random_absent):
            outs = []
            for i in range(10):
                c = f"c{i}"
                o = out(c, "random_removal", "answer", not random_absent)
                o.claims_absent = random_absent
                t = out(c, "target_removal", "answer", target)
                outs += [o, t]
            return outs
        self.assertEqual(evidence_sensitivity_gap(model(True, False)), 1.0)    # "No" only when erased
        self.assertEqual(evidence_sensitivity_gap(model(True, True)), 0.0)     # always "No"
        self.assertEqual(evidence_sensitivity_gap(model(False, False)), 0.0)   # always "Yes"
        self.assertEqual(evidence_sensitivity_gap(always_refer_model()), 0.0)


class TestRejudgeFromTranscripts(unittest.TestCase):
    def test_old_rows_are_rejudged_under_current_rules(self):
        import json
        import tempfile
        from pathlib import Path

        from medscope.data.schema import View, ViewKind
        from medscope.eval.runner import evaluate, view_key
        from medscope.rewards import load_config

        cfg = load_config()
        views = [View(f"c1__{k.value}", "c1", "p1", k, "x.png", "Is there a polyp?", "Yes", [], [100, 100, 300, 300], False)
                 for k in (ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL)]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rows, trs = [], []
            for v, reply, old_correct in ((views[0], "No", False), (views[1], "No polyp", False)):
                rows.append({**out("c1", v.kind.value, "answer", old_correct).to_dict(), "view_id": v.view_id,
                             "vkey": view_key(v)})
                trs.append({"view_id": v.view_id, "vkey": view_key(v), "kind": v.kind.value, "question": v.question,
                            "gold": v.answer, "error": None,
                            "turns": [{"role": "assistant", "content": f'<final>{{"action": "answer", "answer": "{reply}"}}</final>'}]})
            (d / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            (d / "transcripts.jsonl").write_text("\n".join(json.dumps(t) for t in trs))
            s = evaluate(None, views, cfg, d, {"name": "x"}, n_bootstrap=5, log=lambda m: None)
            m = s["metrics"]
            self.assertEqual(m["target_absent_rate"]["value"], 1.0)     # "No" on the erased lesion: right
            self.assertEqual(m["random_denial_rate"]["value"], 1.0)     # "No polyp" with it intact: denial
            self.assertEqual(m["esg"]["value"], 0.0)


class TestTokenConfidence(unittest.TestCase):
    def test_answer_prob_covers_only_the_answer_tokens(self):
        from medscope.confidence import answer_prob
        pieces = ["Looks", " fine.", " <final>", '{"action": "answer", "answer": "', "Ye", "s", '", "confidence": 0.8}', "</final>"]
        probs = [0.1, 0.1, 0.9, 0.9, 0.5, 0.8, 0.99, 0.99]
        self.assertAlmostEqual(answer_prob(pieces, probs), (0.5 * 0.8) ** 0.5, places=6)
        self.assertIsNone(answer_prob(["<final>", '{"action": "refer"}', "</final>"], [0.9, 0.9, 0.9]))

    def test_aurc_prob_ranks_by_probability(self):
        from medscope.eval.metrics import aurc_prob
        good = out("a", "original", "answer", True); good.answer_prob = 0.9
        bad = out("b", "original", "answer", False); bad.answer_prob = 0.2
        self.assertAlmostEqual(aurc_prob([good, bad]), (0 + 0.5) / 2)
        bad.answer_prob = None
        self.assertIsNone(aurc_prob([good, bad]))


class TestPairedBootstrap(unittest.TestCase):
    def test_clear_difference_is_significant(self):
        from medscope.eval.compare import paired_bootstrap
        good = [out(f"c{i}", "original", "answer", True, reward=1.0) for i in range(40)]
        bad = [out(f"c{i}", "original", "answer", i % 4 == 0, reward=1.0 if i % 4 == 0 else -2.0) for i in range(40)]
        r = paired_bootstrap(good, bad, "net_utility", n=300)
        self.assertGreater(r["diff"], 0)
        self.assertLess(r["p"], 0.01)
        same = paired_bootstrap(good, good, "ccr", n=100)
        self.assertEqual(same["diff"], 0.0)


class TestFreeTextFallback(unittest.TestCase):
    def test_free_text_final(self):
        from medscope.actions import free_text_final
        a = free_text_final("The image shows a polypoid lesion in the colon.")
        self.assertEqual(a.kind.value, "answer")
        self.assertEqual(free_text_final("The image is too blurry to identify anything.").kind.value, "clarify")
        self.assertIsNone(free_text_final("<think>still going"))
        self.assertIsNone(free_text_final("   "))

    def test_stored_prose_replies_are_rescored(self):
        import json
        import tempfile
        from pathlib import Path

        from medscope.actions import NO_ACTION
        from medscope.data.schema import View, ViewKind
        from medscope.eval.runner import evaluate, view_key
        from medscope.rewards import load_config

        views = [View("c1__original", "c1", "p1", ViewKind.ORIGINAL, "x.png", "What abnormality is visible?", "Polyp",
                      [], [100, 100, 300, 300], False),
                 View("c1__target_removal", "c1", "p1", ViewKind.TARGET_REMOVAL, "x.png", "Is there a polyp?", "Yes",
                      [], [100, 100, 300, 300], False)]
        replies = ["The image shows a polypoid lesion.", "Yes, a polyp is visible in the image."]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rows, trs = [], []
            for v, reply in zip(views, replies):
                o = out("c1", v.kind.value, None, reward=-1.0)
                rows.append({**o.to_dict(), "view_id": v.view_id, "vkey": view_key(v)})
                trs.append({"view_id": v.view_id, "vkey": view_key(v), "kind": v.kind.value, "question": v.question,
                            "gold": v.answer, "error": NO_ACTION, "turns": [{"role": "assistant", "content": reply}]})
            (d / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            (d / "transcripts.jsonl").write_text("\n".join(json.dumps(t) for t in trs))
            m = evaluate(None, views, load_config(), d, {"name": "x"}, n_bootstrap=5, log=lambda s: None)["metrics"]
            self.assertEqual(m["malformed_rate"]["value"], 0.0)
            self.assertEqual(m["free_text_rate"]["value"], 1.0)
            self.assertEqual(m["ccr"]["value"], 1.0)                       # "polypoid lesion" names the polyp
            self.assertEqual(m["target_hallucination_rate"]["value"], 1.0)  # claims the erased polyp
