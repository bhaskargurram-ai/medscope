import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.counterfactual import (
    make_degraded,
    make_random_removal,
    make_target_removal,
)
from medscope.data.schema import Case, ViewKind, mask_to_box
from medscope.data.views import build_views
from tests.helpers import synthetic_case


class TestCounterfactual(unittest.TestCase):
    def setUp(self):
        self.image, self.lesion = synthetic_case()
        self.rng = np.random.default_rng(1)

    def test_target_removal_erases_lesion(self):
        edited, edit_mask = make_target_removal(self.image, self.lesion)
        self.assertGreater(self.image[self.lesion].mean(), 200)
        self.assertLess(edited[self.lesion].mean(), 160)        # back to tissue level
        self.assertTrue(edit_mask[self.lesion].all())
        untouched = ~edit_mask
        np.testing.assert_array_equal(edited[untouched], self.image[untouched])

    def test_random_removal_keeps_lesion_and_matches_shape(self):
        result = make_random_removal(self.image, self.lesion, self.rng)
        self.assertIsNotNone(result)
        edited, edit_mask = result
        _, target_mask = make_target_removal(self.image, self.lesion)
        self.assertEqual(edit_mask.sum(), target_mask.sum())    # same edit size
        self.assertFalse((edit_mask & self.lesion).any())        # lesion untouched
        self.assertGreater(edited[self.lesion].mean(), 200)

    def test_random_removal_gives_up_when_no_room(self):
        image, lesion = synthetic_case(size=64, lesion_center=(32, 32), lesion_radius=26)
        self.assertIsNone(make_random_removal(image, lesion, self.rng, max_tries=50))

    def test_degradations(self):
        for kind in ("blur", "noise", "lowres"):
            out = make_degraded(self.image, kind, self.rng)
            self.assertEqual(out.shape, self.image.shape)
            self.assertFalse(np.array_equal(out, self.image), kind)
        other = np.full((100, 80, 3), 50, np.uint8)
        out = make_degraded(self.image, "mismatch", self.rng, other_image=other)
        self.assertEqual(out.shape, self.image.shape)
        with self.assertRaises(ValueError):
            make_degraded(self.image, "mismatch", self.rng)

    def test_build_views_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            Image.fromarray(self.image).save(d / "img.png")
            Image.fromarray((self.lesion * 255).astype(np.uint8)).save(d / "mask.png")
            case = Case(case_id="c1", patient_id="p1", dataset="synthetic", modality="xray",
                        image_path=str(d / "img.png"), question="Is there a nodule?",
                        answer="yes", mask_path=str(d / "mask.png"))
            views = build_views(case, d / "views", self.rng)
            self.assertEqual([v.kind for v in views], list(ViewKind))
            for v in views:
                self.assertTrue(Path(v.image_path).exists())
                json.dumps(v.to_dict())  # serialisable
            self.assertEqual(views[0].lesion_box, mask_to_box(self.lesion))


if __name__ == "__main__":
    unittest.main()
