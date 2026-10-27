import unittest

import numpy as np

from medscope.data.inpaint import get_inpainter, lama_inputs, lama_output


class TestLamaPlumbing(unittest.TestCase):
    """The torch-free parts of the LaMa runner: padding, layout, cropping, pixel preservation."""

    def test_inputs_are_padded_to_multiple_of_8(self):
        img = np.random.default_rng(0).integers(0, 256, (61, 90, 3), dtype=np.uint8)
        mask = np.zeros((61, 90), bool)
        mask[10:20, 30:40] = True
        x, m = lama_inputs(img, mask)
        self.assertEqual(x.shape, (1, 3, 64, 96))
        self.assertEqual(m.shape, (1, 1, 64, 96))
        self.assertEqual(x.dtype, np.float32)
        self.assertTrue(0 <= x.min() and x.max() <= 1)
        self.assertEqual(set(np.unique(m)), {0.0, 1.0})
        np.testing.assert_allclose(x[0, :, :61, :90].transpose(1, 2, 0), img / 255.0, rtol=1e-6)

    def test_grayscale_input(self):
        x, _ = lama_inputs(np.full((16, 16), 128, np.uint8), np.zeros((16, 16), bool))
        self.assertEqual(x.shape, (1, 3, 16, 16))

    def test_output_cropped_and_outside_pixels_kept(self):
        img = np.random.default_rng(1).integers(0, 256, (61, 90, 3), dtype=np.uint8)
        mask = np.zeros((61, 90), bool)
        mask[10:20, 30:40] = True
        x, _ = lama_inputs(img, mask)
        fake_model_output = np.full_like(x[0], 0.5)  # a "model" that paints everything mid-grey
        out = lama_output(fake_model_output, img, mask)
        self.assertEqual(out.shape, img.shape)
        self.assertEqual(out.dtype, np.uint8)
        np.testing.assert_array_equal(out[~mask], img[~mask])
        self.assertTrue((out[mask] == 127).all())

    def test_get_inpainter(self):
        self.assertTrue(callable(get_inpainter("lama")))
        with self.assertRaises(ValueError):
            get_inpainter("magic")


if __name__ == "__main__":
    unittest.main()
