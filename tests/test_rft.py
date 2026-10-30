import sys
import unittest
from pathlib import Path

import numpy as np

from medscope.agent.episode import run_group
from medscope.agent.trajectories import build_trajectory, replay_samples
from medscope.data.schema import ViewKind
from medscope.rewards import load_config
from tests.test_agent import Scripted, make_view

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from sample_rft import best_episode, pick_views, success  # noqa: E402

CFG = load_config()


class Cycle:
    """Returns the given replies in turn, one per generate call."""

    def __init__(self, replies):
        self.replies, self.i = replies, 0

    def generate(self, messages, sample=False):
        from medscope.agent.episode import Generation
        r = self.replies[self.i % len(self.replies)]
        self.i += 1
        return Generation(r)


class TestRFT(unittest.TestCase):
    def test_replay_matches_synthetic_contexts(self):
        view, img = make_view(ViewKind.ORIGINAL)
        synth = build_trajectory(view, np.random.default_rng(1), image=img, zoom_prob=1.0)
        replayed = replay_samples(view, [s.target for s in synth], CFG, image=img)
        self.assertEqual([len(s.messages) for s in replayed], [len(s.messages) for s in synth])
        self.assertEqual([s.target for s in replayed], [s.target for s in synth])

    def test_keeps_best_success_only(self):
        view, img = make_view(ViewKind.TARGET_REMOVAL)
        replies = ['<final>{"action": "answer", "answer": "Yes"}</final>',
                   '<final>{"action": "refer"}</final>',
                   '<final>{"action": "answer", "answer": "No"}</final>']
        eps = run_group(Cycle(replies), view, CFG, 3, image=img)
        rec = best_episode(view, eps)
        self.assertTrue(rec["kept"])
        self.assertEqual(rec["successes"], 1)                 # refer is safe but not the target
        self.assertIn('"No"', rec["turns"][0])
        none = best_episode(view, eps[:2])
        self.assertFalse(none["kept"])

    def test_success_on_degraded_is_clarify(self):
        view, img = make_view(ViewKind.DEGRADED)
        ep = run_group(Cycle(['<final>{"action": "clarify", "question": "sharper?"}</final>']), view, CFG, 1, image=img)[0]
        self.assertTrue(success(view, ep.outcome))

    def test_pick_views_per_kind(self):
        views = [make_view(k)[0] for k in ViewKind for _ in range(3)]
        picked = pick_views(views, per_kind=2)
        self.assertEqual(len(picked), 2 * len(ViewKind))


if __name__ == "__main__":
    unittest.main()
