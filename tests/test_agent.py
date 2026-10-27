import unittest

import numpy as np

from medscope.agent.episode import Generation, run_episode
from medscope.agent.trajectories import build_trajectory, pad_box
from medscope.data.schema import View, ViewKind, mask_to_box
from medscope.rewards import load_config
from tests.helpers import synthetic_case

CFG = load_config()


class Scripted:
    """A fake policy that replies with pre-written turns, recording what it saw."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def generate(self, messages, sample=False):
        self.seen.append(len(messages))
        return Generation(self.replies.pop(0) if self.replies else "")


def make_view(kind: ViewKind, degradation="blur"):
    img, lesion = synthetic_case()
    v = View(view_id=f"c1__{kind.value}", case_id="c1", patient_id="p1", kind=kind, image_path="unused",
             question="Is there a tumor?", answer="Yes", answer_aliases=[], lesion_box=mask_to_box(lesion),
             critical=False, meta={"degradation": degradation})
    return v, img


class TestEpisode(unittest.TestCase):
    def test_zoom_then_answer(self):
        view, img = make_view(ViewKind.ORIGINAL)
        box = view.lesion_box
        pol = Scripted([
            'Look closer. <tool>{"name": "zoom", "box": [200, 200, 600, 600]}</tool>',
            f'Visible. <final>{{"action": "answer", "answer": "yes", "box": {box}, "confidence": 0.9}}</final>',
        ])
        ep = run_episode(pol, view, CFG, image=img)
        self.assertEqual(ep.tool_calls, 1)
        self.assertEqual(ep.outcome.reward, 1.5)
        self.assertEqual(pol.seen, [2, 4])             # system+question, then +assistant+tool result
        self.assertEqual(ep.messages[3]["content"][0]["type"], "image")
        # history keeps only the action that ran, not the prose or anything after it
        self.assertEqual(ep.messages[2]["content"][0]["text"], '<tool>{"name": "zoom", "box": [200, 200, 600, 600]}</tool>')

    def test_answer_written_before_zoom_result_is_dropped_from_history(self):
        view, img = make_view(ViewKind.ORIGINAL)
        pol = Scripted([
            '<tool>{"name": "zoom", "box": [200, 200, 600, 600]}\n<final>{"action": "answer", "answer": "no"}',
            '<final>{"action": "answer", "answer": "yes"}</final>',
        ])
        ep = run_episode(pol, view, CFG, image=img)
        self.assertEqual(ep.tool_calls, 1)
        self.assertNotIn('"no"', ep.messages[2]["content"][0]["text"])
        self.assertEqual(ep.final.answer, "yes")
        self.assertEqual(ep.transcript()[0]["content"], "[image] Question: Is there a tumor?")

    def test_malformed_and_turn_limit(self):
        view, img = make_view(ViewKind.ORIGINAL)
        ep = run_episode(Scripted(["I think yes."]), view, CFG, image=img)
        self.assertTrue(ep.malformed)
        self.assertEqual(ep.outcome.reward, -1.0)
        looping = Scripted(['<tool>{"name": "zoom", "box": [0, 0, 500, 500]}</tool>'] * 10)
        ep = run_episode(looping, view, CFG, image=img)
        self.assertTrue(ep.malformed)
        self.assertEqual(len(ep.turns), CFG["tools"]["budget"] + 1)


class TestTrajectories(unittest.TestCase):
    def replay(self, kind, seed, **kw):
        view, img = make_view(kind, **kw)
        samples = build_trajectory(view, np.random.default_rng(seed), image=img)
        ep = run_episode(Scripted([s.target for s in samples]), view, CFG, image=img)
        return samples, ep

    def test_every_kind_replays_to_its_expected_action(self):
        for kind in ViewKind:
            for seed in range(6):  # covers with and without zoom
                samples, ep = self.replay(kind, seed)
                self.assertFalse(ep.malformed, (kind, seed, ep.error))
                self.assertEqual(ep.final.kind, view_expected(kind), kind)
                self.assertGreater(ep.outcome.reward, 0, (kind, seed))
                # each sample's context matches what the episode showed the model
                for s, t in zip(samples, ep.turns):
                    self.assertEqual(len(s.messages), t.context_len)

    def test_degraded_reason_matches_degradation(self):
        samples, _ = self.replay(ViewKind.DEGRADED, 0, degradation="mismatch")
        self.assertIn("correct image", samples[0].target)

    def test_direct_only_has_no_tools(self):
        view, img = make_view(ViewKind.ORIGINAL)
        for seed in range(5):
            s = build_trajectory(view, np.random.default_rng(seed), direct_only=True, image=img)
            self.assertEqual(len(s), 1)
            self.assertNotIn("<tool>", s[0].target)

    def test_pad_box(self):
        self.assertEqual(pad_box([400, 400, 500, 500]), [350, 350, 550, 550])
        self.assertEqual(pad_box([0, 0, 20, 20]), [0, 0, 85, 85])


def view_expected(kind):
    return {ViewKind.ORIGINAL: "answer", ViewKind.RANDOM_REMOVAL: "answer",
            ViewKind.TARGET_REMOVAL: "refer", ViewKind.DEGRADED: "clarify"}[kind]


if __name__ == "__main__":
    unittest.main()
