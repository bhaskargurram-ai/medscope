import unittest

import numpy as np

from medscope.agent.episode import run_episodes
from medscope.agent.prompts import start_messages
from medscope.api_policy import AnthropicPolicy, OpenAIPolicy, _ApiPolicy, cost_usd, measured_cost_per_view
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
        self._record(1000, 200)
        return '<final>{"action": "answer", "answer": "No"}</final>'


class TestApiPolicy(unittest.TestCase):
    def test_openai_message_format(self):
        img = np.zeros((20, 30, 3), np.uint8)
        from medscope.api_policy import _ApiPolicy
        plain, high = _ApiPolicy("m"), _ApiPolicy("m", image_detail="high")
        msgs = OpenAIPolicy.to_openai(plain, start_messages(img, "Is there a polyp?"))
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["content"][0]["type"], "image_url")
        self.assertTrue(msgs[1]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertNotIn("detail", msgs[1]["content"][0]["image_url"])       # provider default in the main runs
        self.assertEqual(msgs[1]["content"][1]["text"], "Question: Is there a polyp?")
        msgs = OpenAIPolicy.to_openai(high, start_messages(img, "Is there a polyp?"))
        self.assertEqual(msgs[1]["content"][0]["image_url"]["detail"], "high")

    def test_batch_with_retries_runs_episodes(self):
        import medscope.api_policy as ap
        ap.time.sleep = lambda s: None
        view, img = make_view(ViewKind.TARGET_REMOVAL)
        eps = run_episodes(Fake(), [view, view], load_config(), images=[img, img])
        self.assertTrue(all(e.outcome.correct for e in eps))     # "No" on an erased lesion


if __name__ == "__main__":
    unittest.main()

    def test_anthropic_message_format(self):
        img = np.zeros((20, 30, 3), np.uint8)
        system, msgs = AnthropicPolicy.to_anthropic(start_messages(img, "Is there a polyp?"))
        self.assertTrue(system)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["content"][0]["type"], "image")
        self.assertEqual(msgs[0]["content"][0]["source"]["media_type"], "image/png")
        self.assertEqual(msgs[0]["content"][1]["text"], "Question: Is there a polyp?")

    def test_usage_and_cost(self):
        import json
        import tempfile
        from pathlib import Path
        import medscope.api_policy as ap
        ap.time.sleep = lambda s: None
        f = Fake()
        view, img = make_view(ViewKind.TARGET_REMOVAL)
        run_episodes(f, [view, view], load_config(), images=[img, img])
        self.assertEqual(f.usage["input_tokens"], 1000 * f.usage["requests"])
        self.assertAlmostEqual(cost_usd("claude-opus-5-5", 1_000_000, 1_000_000), 24.0)
        self.assertIsNone(cost_usd("unknown-model", 1, 1))
        with tempfile.TemporaryDirectory() as d:
            Path(d, "usage.json").write_text(json.dumps({"model": "claude-sonnet-5-5", "calls": [
                {"views_run": 10, "requests": 15, "input_tokens": 50_000, "output_tokens": 10_000},
                {"views_run": 0, "requests": 0, "input_tokens": 0, "output_tokens": 0}]}))
            m = measured_cost_per_view(d)
        self.assertAlmostEqual(m["usd_per_view"], (0.05 * 2 + 0.01 * 10) / 10)
        self.assertAlmostEqual(m["requests_per_view"], 1.5)

