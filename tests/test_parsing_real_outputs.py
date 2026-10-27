"""Regression tests from real model outputs seen in the first baseline run (notebook 02, Oct 2026).

Each of these was scored "malformed" or "wrong" by the first harness although the model's
decision was readable; the harness, not the model, was at fault.
"""

import unittest

from medscope.actions import answer_matches, answer_vocabulary, parse, polarity, strip_thinking
from medscope.data.schema import ActionKind

RIVALS = answer_vocabulary(["Polyp", "Brain", "Liver", "Kidney", "Lung", "Yes"])


class TestRealOutputs(unittest.TestCase):
    def test_qwen_unclosed_tags_several_actions(self):
        text = ('<tool>{"name": "zoom", "box": [200, 300, 700, 700]}\n'
                '<tool>{"name": "window", "center": 450, "width": 150}\n'
                '<final>{"action": "answer", "answer": "A polypoid lesion is visible in the colon.", '
                '"box": [200, 300, 700, 700], "confidence": 0.9}')
        p = parse(text)
        self.assertFalse(p.malformed, p.error)
        self.assertEqual(p.tool.name, "zoom")                       # the first action is what it does
        self.assertEqual(p.tool.args["box"], [200, 300, 700, 700])

    def test_qwen_closing_tag_on_next_line(self):
        p = parse('<tool>{"name": "zoom", "box": [500, 350, 999, 999]}\n</tool>')
        self.assertEqual(p.tool.args["box"], [500, 350, 999, 999])

    def test_qwen_stray_think_close(self):
        text = ('<tool>{"name": "zoom", "box": [200, 300, 700, 700]}\n\n</think>\n\n'
                '<final>{"action": "answer", "answer": "A polyp", "box": [300, 300, 700, 700], "confidence": 0.9}')
        p = parse(text)
        self.assertFalse(p.malformed)
        self.assertEqual(p.final.kind, ActionKind.ANSWER)          # text before </think> was thinking

    def test_medgemma_json_code_block(self):
        text = '```json\n{"action": "answer", "answer": "Mass in the stomach", "box": [268, 385, 698, 723], "confidence": 0.95}\n```'
        p = parse(text)
        self.assertEqual(p.final.answer, "Mass in the stomach")
        self.assertEqual(p.final.box, [268, 385, 698, 723])
        p = parse('```json\n{"action": "clarify", "question": "The image is too blurry."}\n```')
        self.assertEqual(p.final.kind, ActionKind.CLARIFY)

    def test_medgemma_thinking_then_answer(self):
        text = ('<unused94>thought\nThe user wants me to identify an abnormality. Plan: use the zoom tool '
                '{"name": "zoom"} maybe.\n<unused95>The polyp is visible. '
                '<final>{"action": "answer", "answer": "Polyp", "confidence": 0.8}</final>')
        p = parse(text)
        self.assertEqual(p.final.answer, "Polyp")                 # JSON inside the thinking is ignored

    def test_medgemma_thinking_cut_off(self):
        text = "thought\nThe user wants me to identify any abnormalities in the provided medical image.\n"
        p = parse(text)
        self.assertTrue(p.malformed)
        self.assertIn("still thinking", p.error)
        body, unfinished = strip_thinking("<unused94>thought\nlong reasoning")
        self.assertTrue(unfinished)

    def test_truncated_json_is_malformed(self):
        p = parse('<final>{"action": "answer", "answer": "Large colonic polyp", "box": [400, 350, 999, 999], "confidence": 0.')
        self.assertTrue(p.malformed)

    def test_prose_braces_are_not_actions(self):
        self.assertTrue(parse('The set {liver, spleen} looks fine.').malformed)
        self.assertTrue(parse('Result: {"organ": "liver"}').malformed)


class TestAnswerMatching(unittest.TestCase):
    def test_free_text_answers(self):
        self.assertTrue(answer_matches("A polypoid lesion is visible in the colon.", "Polyp", [], RIVALS))
        self.assertTrue(answer_matches("Large colonic polyp", "Polyp", [], RIVALS))
        self.assertTrue(answer_matches("A polyp", "Polyp", [], RIVALS))
        self.assertFalse(answer_matches("Mass in the stomach", "Polyp", [], RIVALS))
        self.assertTrue(answer_matches("The left kidney", "Kidney", [], RIVALS))

    def test_hedging_across_options_is_wrong(self):
        self.assertFalse(answer_matches("Either the liver or the kidney", "Liver", [], RIVALS))
        self.assertTrue(answer_matches("Liver", "Liver", [], RIVALS))

    def test_yes_no(self):
        self.assertTrue(answer_matches("Yes, there is a tumor in the liver.", "Yes", [], RIVALS))
        self.assertTrue(answer_matches("A tumor is present.", "Yes", [], RIVALS))
        self.assertFalse(answer_matches("No tumor is seen.", "Yes", [], RIVALS))
        self.assertTrue(answer_matches("No, the liver is not healthy.", "No", [], RIVALS))
        self.assertEqual(polarity("There is an abnormality"), "yes")
        self.assertEqual(polarity("The image appears normal"), "no")
        self.assertIsNone(polarity("Hepatic lesion"))


if __name__ == "__main__":
    unittest.main()
