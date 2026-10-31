import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import extra_analysis as ea  # noqa: E402
from medscope.data.schema import View, ViewKind  # noqa: E402
from medscope.eval.metrics import METRICS  # noqa: E402
from medscope.rewards import load_config, with_vocab  # noqa: E402


def views():
    out = []
    for i in range(8):
        for kind in (ViewKind.ORIGINAL, ViewKind.TARGET_REMOVAL, ViewKind.RANDOM_REMOVAL, ViewKind.DEGRADED):
            out.append(View(view_id=f"c{i}__{kind.value}", case_id=f"c{i}", patient_id=f"p{i}", kind=kind,
                            image_path="x", question="Is there a polyp?", answer="Yes", answer_aliases=[],
                            lesion_box=[100, 100, 100 + 40 * (i + 1), 300], critical=False, meta={}))
        out.append(View(view_id=f"n{i}__natural_negative", case_id=f"n{i}", patient_id=f"q{i}",
                        kind=ViewKind.NATURAL_NEGATIVE, image_path="x", question="Is the liver healthy?",
                        answer="Yes", answer_aliases=[], lesion_box=None, critical=False, meta={}))
    return out


class TestExtraAnalysis(unittest.TestCase):
    def setUp(self):
        self.views = views()
        self.cfg = with_vocab(load_config(), self.views)

    def test_trivial_policies_score_zero_esg(self):
        pol = ea.trivial_policies(self.views, self.cfg)
        for name, outs in pol.items():
            self.assertAlmostEqual(METRICS["esg"](outs), 0.0, msg=name)
        self.assertEqual(METRICS["target_hallucination_rate"](pol["always claims the finding"]), 1.0)
        self.assertEqual(METRICS["natural_hallucination_rate"](pol["always claims the finding"]), 1.0)
        self.assertEqual(METRICS["target_hallucination_rate"](pol["always says it is absent"]), 0.0)
        self.assertEqual(METRICS["ccr"](pol["always says it is absent"]), 0.0)
        # always refer: positive under the published matrix, not under "refer -0.3 everywhere"
        by_id = {v.view_id: v for v in self.views}
        table = ea.sensitivity_table({"r": pol["always refers"]}, by_id, self.cfg)
        row = table.splitlines()[-1].split("|")
        self.assertGreater(float(row[2]), 0)
        self.assertLess(float(row[-2]), 0)

    def test_strict_esg_ignores_refer(self):
        pol = ea.trivial_policies(self.views, self.cfg)
        refer_t = [o for o in pol["always refers"] if o.kind == "target_removal"]
        yes_r = [o for o in pol["always claims the finding"] if o.kind == "random_removal"]
        mixed = refer_t + yes_r
        self.assertAlmostEqual(METRICS["esg"](mixed), 1.0)
        self.assertAlmostEqual(ea.strict_esg(mixed), 0.0)

    def test_main_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            vf = d / "views.jsonl"
            vf.write_text("".join(json.dumps(v.to_dict()) + "\n" for v in self.views))
            run = d / "res" / "v2_x_test"
            run.mkdir(parents=True)
            outs = ea.trivial_policies(self.views, self.cfg)["always claims the finding"]
            (run / "outcomes.jsonl").write_text("".join(json.dumps(o.to_dict()) + "\n" for o in outs))
            tr = [{"view_id": v.view_id, "turns": [
                {"role": "assistant", "content": '<tool>{"name": "zoom", "box": [0, 0, 1000, 1000]}</tool>'},
                {"role": "assistant", "content": '<final>{"action": "answer", "answer": "Yes"}</final>'}]}
                for v in self.views]
            (run / "transcripts.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tr))
            sys.argv = ["x", "--results", str(d / "res"), "--views", str(vf), "--runs", "v2_x_test=X",
                        "--out", str(d / "out.md")]
            ea.main()
            md = (d / "out.md").read_text()
            self.assertIn("Trivial policies", md)
            self.assertIn("| X | original | 8 | 1.00 | 1.00 | 0.00 | 1.00 (8 zooms) |", md)
            self.assertIn("Q4", md)


if __name__ == "__main__":
    unittest.main()
