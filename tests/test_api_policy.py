import unittest

import numpy as np

from medscope.agent.episode import run_episodes
from medscope.agent.prompts import start_messages
from medscope.api_policy import OpenAIPolicy, _ApiPolicy
from medscope.data.schema import ViewKind
from medscope.rewards import load_config
from tests.test_agent import make_view


class Fake(_ApiPolicy):
    def __init__(self):
        super().__init__("fake", workers=4)
        self.calls = 0

    def _call(self, messages):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("rate limited")   # retried
        return '<final>{"action": "answer", "answer": "No"}</final>'


class TestApiPolicy(unittest.TestCase):
    def test_openai_message_format(self):
        img = np.zeros((20, 30, 3), np.uint8)
        msgs = OpenAIPolicy.to_openai(start_messages(img, "Is there a polyp?"))
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["content"][0]["type"], "image_url")
        self.assertTrue(msgs[1]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(msgs[1]["content"][1]["text"], "Question: Is there a polyp?")

    def test_batch_with_retries_runs_episodes(self):
        import medscope.api_policy as ap
        ap.time.sleep = lambda s: None
        view, img = make_view(ViewKind.TARGET_REMOVAL)
        eps = run_episodes(Fake(), [view, view], load_config(), images=[img, img])
        self.assertTrue(all(e.outcome.correct for e in eps))     # "No" on an erased lesion


if __name__ == "__main__":
    unittest.main()
