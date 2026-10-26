"""Checks for the parts of hf_policy that don't need torch or a GPU."""

import re
import types
import unittest

from medscope.train.hf_policy import VISION_REGEX, pick_dtype


def fake_torch(capability, available=True):
    cuda = types.SimpleNamespace(is_available=lambda: available, get_device_capability=lambda: capability)
    return types.SimpleNamespace(cuda=cuda, bfloat16="bf16", float16="fp16", float32="fp32")


class TestPureHelpers(unittest.TestCase):
    def test_dtype_by_gpu(self):
        self.assertEqual(pick_dtype(fake_torch((8, 9)), "Qwen/Qwen3.5-4B"), "bf16")          # L4
        self.assertEqual(pick_dtype(fake_torch((8, 0)), "google/medgemma-1.5-4b-it"), "bf16")  # A100
        self.assertEqual(pick_dtype(fake_torch((7, 5)), "Qwen/Qwen3.5-4B"), "fp16")          # T4
        self.assertEqual(pick_dtype(fake_torch((7, 5)), "google/medgemma-1.5-4b-it"), "fp32")  # T4, Gemma overflow
        self.assertEqual(pick_dtype(fake_torch((0, 0), available=False), "Qwen/Qwen3.5-4B"), "fp16")

    def test_vision_modules_are_excluded_from_lora(self):
        excluded = ["model.visual.blocks.0.attn.qkv", "model.vision_tower.encoder.layers.3.mlp.fc1",
                    "model.multi_modal_projector.mm_input_projection"]
        kept = ["model.language_model.layers.0.self_attn.q_proj", "model.layers.5.linear_attn.in_proj_qkvz"]
        for name in excluded:
            self.assertIsNotNone(re.fullmatch(VISION_REGEX, name), name)
        for name in kept:
            self.assertIsNone(re.fullmatch(VISION_REGEX, name), name)


if __name__ == "__main__":
    unittest.main()
