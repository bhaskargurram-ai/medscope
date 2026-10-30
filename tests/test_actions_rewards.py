import unittest

import numpy as np

from medscope.actions import answer_matches, parse
from medscope.data.schema import ActionKind, View, ViewKind, iou
from medscope.env.tools import ToolEnv
from medscope.rewards import Outcome, load_config, score

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

    def test_first_action_wins_and_confidence_clamped(self):
        p = parse('<tool>{"name": "zoom", "box": [0,0,10,10]}</tool> then '
                  '<final>{"action": "answer", "answer": "Yes", "box": [300,300,400,400], "confidence": 1.4}</final>')
        self.assertEqual(p.tool.name, "zoom")   # it hasn't seen the zoom yet, so its answer is ignored
        p = parse('<final>{"action": "answer", "answer": "Yes", "box": [300,300,400,400], "confidence": 1.4}</final>')
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

    def test_target_removal_rewards_saying_absent(self):
        refer = self.final('<final>{"action": "refer", "reason": "lesion not visible"}</final>')
        yes = self.final('<final>{"action": "answer", "answer": "yes"}</final>')
        no = self.final('<final>{"action": "answer", "answer": "No, there is no nodule."}</final>')
        self.assertEqual(score(view(ViewKind.TARGET_REMOVAL), no, self.cfg).reward, 1.0)
        self.assertEqual(score(view(ViewKind.TARGET_REMOVAL), refer, self.cfg).reward, 0.5)
        self.assertEqual(score(view(ViewKind.TARGET_REMOVAL), yes, self.cfg).reward, -2.0)
        self.assertEqual(score(view(ViewKind.RANDOM_REMOVAL), refer, self.cfg).reward, -0.3)
        o = score(view(ViewKind.RANDOM_REMOVAL), no, self.cfg)        # lesion still there: "No" is wrong
        self.assertTrue(o.claims_absent)
        self.assertFalse(o.correct)

    def test_degraded_rewards_clarify(self):
        o = score(view(ViewKind.DEGRADED),
                  self.final('<final>{"action": "clarify", "question": "Sharper image?"}</final>'), self.cfg)
        self.assertEqual(o.reward, 0.5)

    def test_tool_penalty_and_malformed(self):
        f = self.final('<final>{"action": "refer"}</final>')
        o = score(view(ViewKind.TARGET_REMOVAL), f, self.cfg, tool_calls=3, refused_calls=1)
        self.assertAlmostEqual(o.reward, 0.5 - 0.05 * 3)
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


class TestAbsence(unittest.TestCase):
    def test_absent_reply_and_claims(self):
        from medscope.actions import absent_reply, claims_absence, polarity
        self.assertEqual(absent_reply("Is there a polyp?", "Yes"), "No")
        self.assertEqual(absent_reply("Is the liver healthy?", "No"), "Yes")
        self.assertIsNone(absent_reply("Which organ is abnormal?", "Liver"))
        self.assertTrue(claims_absence("No polyp is visible", "Is there a polyp?", "Yes"))
        self.assertTrue(claims_absence("Normal", "Is there a polyp?", "Yes"))
        self.assertFalse(claims_absence("Yes", "Is there a polyp?", "Yes"))
        self.assertTrue(claims_absence("The liver looks healthy", "Is the liver healthy?", "No"))
        self.assertFalse(claims_absence("Not healthy, there is a lesion", "Is the liver healthy?", "No"))
        self.assertTrue(claims_absence("No abnormality", "Which organ is abnormal?", "Liver"))
        self.assertFalse(claims_absence("Liver", "Which organ is abnormal?", "Liver"))
        # health questions: "Healthy" means yes (it used to be read as a negation)
        self.assertEqual(polarity("Healthy", "Is the lung healthy?"), "yes")
        self.assertEqual(polarity("Abnormal", "Is the lung healthy?"), "no")
        self.assertEqual(polarity("Normal", "Is there a tumor?"), "no")


class TestFreeTextReplies(unittest.TestCase):
    def test_wordy_replies_read_correctly(self):
        from medscope.actions import polarity
        q = "Is there a pneumothorax in this chest X-ray?"
        self.assertEqual(polarity("Pneumothorax present without mediastinal shift", q), "yes")
        self.assertEqual(polarity("A mass is seen; no pneumothorax", q), "no")
        self.assertEqual(polarity("There is no pneumothorax", q), "no")
        self.assertEqual(polarity("A small left apical pneumothorax", q), "yes")
        self.assertEqual(polarity("Normal chest X-ray", q), "no")
        h = "Is the liver healthy?"
        self.assertEqual(polarity("No abnormality", h), "yes")
        self.assertEqual(polarity("There is a lesion", h), "no")

    def test_grounding_bonus_follows_rejudged_correctness(self):
        from medscope.rewards import rescore
        v = view(ViewKind.ORIGINAL)
        right = score(v, parse(f'<final>{{"action": "answer", "answer": "yes", "box": {v.lesion_box}}}</final>').final, load_config())
        self.assertIn("grounding", right.breakdown)
        flipped = Outcome(**{**right.to_dict(), "correct": False})
        self.assertNotIn("grounding", rescore(v, flipped, load_config()).breakdown)
        self.assertEqual(rescore(v, flipped, load_config()).reward, -2.0)
