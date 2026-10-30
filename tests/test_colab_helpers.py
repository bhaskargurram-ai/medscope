import json
import tempfile
import unittest
from pathlib import Path

from medscope.colab import build_report, read_text, train_log_summary


class TestColabHelpers(unittest.TestCase):
    def test_sft_and_grpo_log_tables(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "train_log.jsonl"
            p.write_text("\n".join(json.dumps({"step": s, "loss": 1.0 / s}) for s in range(10, 60, 10)))
            self.assertIn("| 10-50 |", train_log_summary(p))
            g = Path(d) / "grpo.jsonl"
            g.write_text("\n".join(json.dumps({"step": s, "reward": 0.1 * s, "actions": {"answer": 3, "refer": 1},
                                               "tool_calls": 1.0, "groups_with_signal": 2, "secs": 30})
                                   for s in range(1, 21)) + "\n" + json.dumps({"step": 20, "eval_net_utility": 0.4}))
            table = train_log_summary(g)
            self.assertIn("| 1-10 |", table)
            self.assertIn("75%", table)
            self.assertIn("no training log", train_log_summary(Path(d) / "missing.jsonl"))
            g.write_text(json.dumps({"step": 1, "reward": 1.0, "actions": {"refer": 8}, "tool_calls": 0.5,
                                     "groups_with_signal": 2, "groups_drawn": 5, "secs": 200}))
            self.assertIn("| 2.0 of 5.0 |", train_log_summary(g))

    def test_build_report(self):
        r = build_report("MedScope report - test", [("Section", "body"), ("Missing", read_text("/nope"))])
        self.assertTrue(r.startswith("# MedScope report - test"))
        self.assertIn("## Environment", r)
        self.assertIn("(missing: /nope)", r)


if __name__ == "__main__":
    unittest.main()


class TestByDataset(unittest.TestCase):
    def test_table_per_imaging_type(self):
        from medscope.colab import by_dataset, dataset_of
        self.assertEqual(dataset_of("hkneg_x_abn"), dataset_of("kvasir_1_abn"))
        self.assertEqual(dataset_of("chestxdet00012neg_abn"), "Chest X-ray (ChestX-Det)")
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "m_test"
            run.mkdir()
            rows = [{"view_id": f"lgg1_t__{k}", "case_id": "lgg1_t", "kind": k, "action": "answer", "correct": c,
                     "iou": 0.0, "confidence": 0.9, "tool_calls": 0, "malformed": False, "reward": 1.0,
                     "breakdown": {}, "claims_absent": a}
                    for k, c, a in (("original", True, False), ("target_removal", True, True),
                                    ("random_removal", True, False))]
            (run / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            t = by_dataset(d, ["m_test", "missing"])
            self.assertIn("| m_test | Brain MRI (LGG) | 1 | 1.00 | 1.00 | 0.00 | n/a | 1.00 |", t)
