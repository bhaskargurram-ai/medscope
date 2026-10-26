import unittest

import numpy as np

from medscope.actions import answer_matches, parse
from medscope.data.schema import ActionKind, View, ViewKind, iou
from medscope.env.tools import ToolEnv
from medscope.rewards import load_config, score

BOX = [300, 300, 400, 400]


def view(kind: ViewKind, critical: bool = False) -> View:
    return View(view_id=f"c1__{kind.value}", case_id="c1", patient_id="p1", kind=kind,
                image_path="x.png", question="Is there a nodule?", answer="yes",
                answer_aliases=["present"], lesion_box=BOX, critical=critical)


class TestParse(unittest.TestCase):
    def test_tool_call(self):
        p = parse('I should look closer. <tool>{"name": "zoom", "box": [100, 100, 500, 500]}</tool>')
        self.assertEqual(p.tool.name, "zoom")
        self.assertEqual(p.tool.args["box"], [100, 100, 500, 500])

    def test_final_answer_and_last_tag_wins(self):
        p = parse('<tool>{"name": "zoom", "box": [0,0,10,10]}</tool> then '
                  '<final>{"action": "answer", "answer": "Yes", "box": [300,300,400,400], "confidence": 1.4}</final>')
        self.assertEqual(p.final.kind, ActionKind.ANSWER)
        self.assertEqual(p.final.confidence, 1.0)  # clamped

    def test_abstain_maps_to_refer(self):
        self.assertEqual(parse('<final>{"action": "abstain"}</final>').final.kind, ActionKind.REFER)

    def test_malformed(self):
        for text in ["no tags", "<final>{bad json}</final>", '<final>{"action": "guess"}</final>',
                     '<final>{"action": "answer"}</final>', '<tool>{"name": "zoom", "box": [5, 5, 1, 1]}</tool>']:
            self.assertTrue(parse(text).malformed, text)

    def test_answer_matching(self):
        self.assertTrue(answer_matches(" YES. ", "yes"))
        self.assertTrue(answer_matches("present", "yes", ["present"]))
        self.assertFalse(answer_matches("no", "yes"))


class TestReward(unittest.TestCase):
    cfg = load_config()

    def final(self, text):
        return parse(text).final

    def test_correct_grounded_answer(self):
        o = score(view(ViewKind.ORIGINAL), self.final(
            '<final>{"action": "answer", "answer": "yes", "box": [300,300,400,400]}</final>'), self.cfg)
        self.assertEqual(o.reward, 1.5)
        self.assertTrue(o.correct)

    def test_huge_box_gets_no_grounding_bonus(self):
        o = score(view(ViewKind.ORIGINAL), self.final(
            '<final>{"action": "answer", "answer": "yes", "box": [0,0,1000,1000]}</final>'), self.cfg)
        self.assertEqual(o.reward, 1.0)

    def test_wrong_answer_on_critical_case(self):
        o = score(view(ViewKind.ORIGINAL, critical=True),
                  self.final('<final>{"action": "answer", "answer": "no"}</final>'), self.cfg)
        self.assertEqual(o.reward, -4.0)

    def test_target_removal_rewards_referral(self):
        refer = self.final('<final>{"action": "refer", "reason": "lesion not visible"}</final>')
        answer = self.final('<final>{"action": "answer", "answer": "yes"}</final>')
        self.assertEqual(score(view(ViewKind.TARGET_REMOVAL), refer, self.cfg).reward, 1.0)
        self.assertEqual(score(view(ViewKind.TARGET_REMOVAL), answer, self.cfg).reward, -2.0)
        self.assertEqual(score(view(ViewKind.RANDOM_REMOVAL), refer, self.cfg).reward, -0.3)

    def test_degraded_rewards_clarify(self):
        o = score(view(ViewKind.DEGRADED),
                  self.final('<final>{"action": "clarify", "question": "Sharper image?"}</final>'), self.cfg)
        self.assertEqual(o.reward, 0.5)

    def test_tool_penalty_and_malformed(self):
        f = self.final('<final>{"action": "refer"}</final>')
        o = score(view(ViewKind.TARGET_REMOVAL), f, self.cfg, tool_calls=3, refused_calls=1)
        self.assertAlmostEqual(o.reward, 1.0 - 0.05 * 3)
        self.assertEqual(score(view(ViewKind.ORIGINAL), None, self.cfg, malformed=True).reward, -1.0)


class TestTools(unittest.TestCase):
    def test_zoom_window_and_budget(self):
        img = np.random.default_rng(0).integers(0, 255, (200, 300, 3), dtype=np.uint8)
        env = ToolEnv(img, budget=2)
        r = env.call("zoom", {"box": [0, 0, 500, 500]})
        self.assertTrue(r.ok)
        self.assertEqual(max(r.image.shape[:2]), 448)
        self.assertTrue(env.call("window", {"center": 128, "width": 64}).ok)
        r = env.call("zoom", {"box": [0, 0, 500, 500]})
        self.assertFalse(r.ok)
        self.assertEqual(env.refused, 1)
        self.assertFalse(ToolEnv(img).call("teleport", {}).ok)

    def test_iou(self):
        self.assertEqual(iou(BOX, BOX), 1.0)
        self.assertEqual(iou(BOX, [0, 0, 100, 100]), 0.0)
        self.assertAlmostEqual(iou([0, 0, 100, 100], [50, 0, 150, 100]), 1 / 3)


if __name__ == "__main__":
    unittest.main()
