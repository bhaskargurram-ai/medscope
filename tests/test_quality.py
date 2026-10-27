import unittest

import numpy as np

from medscope.data.counterfactual import make_random_removal, make_target_removal
from medscope.data.quality import (
    check_case,
    correlation,
    dhash,
    edit_features,
    filter_shortcut,
    hamming,
    near_duplicates,
    shortcut_auc,
)
from tests.helpers import synthetic_case


class TestCaseChecks(unittest.TestCase):
    def setUp(self):
        self.image, self.lesion = synthetic_case()
        rng = np.random.default_rng(3)
        self.target, _ = make_target_removal(self.image, self.lesion)
        self.random, self.random_mask = make_random_removal(self.image, self.lesion, rng)

    def test_good_views_pass(self):
        res = check_case("c", self.image, self.target, self.random, self.lesion, self.random_mask)
        self.assertTrue(res.lesion_removed, res)
        self.assertTrue(res.evidence_intact)
        self.assertTrue(res.passed)
        self.assertLess(res.contrast_after, res.contrast_before)

    def test_unremoved_lesion_fails(self):
        res = check_case("c", self.image, self.image, self.random, self.lesion, self.random_mask)
        self.assertFalse(res.lesion_removed)

    def test_damaged_evidence_fails(self):
        broken = self.random.copy()
        broken[self.lesion] = 0
        res = check_case("c", self.image, self.target, broken, self.lesion, self.random_mask)
        self.assertFalse(res.evidence_intact)
        self.assertGreater(res.lesion_pixels_changed, 0)

    def test_detector_hook(self):
        res = check_case("c", self.image, self.target, self.random, self.lesion, self.random_mask,
                         detector_fn=lambda img, m: 0.9)
        self.assertFalse(res.lesion_removed)


class TestShortcut(unittest.TestCase):
    def _feats(self, n, leak: bool):
        t, r = [], []
        for i in range(n):
            rng = np.random.default_rng(i)
            img, lesion = synthetic_case(lesion_center=(int(rng.integers(70, 120)), int(rng.integers(70, 180))),
                                         lesion_radius=int(rng.integers(8, 16)))
            tgt, tmask = make_target_removal(img, lesion)
            rnd, rmask = make_random_removal(img, lesion, rng)
            if leak:  # paint every target edit flat black: an obvious, learnable artifact
                tgt = tgt.copy()
                tgt[tmask] = 0
            t.append(edit_features(tgt, tmask))
            r.append(edit_features(rnd, rmask))
        return np.array(t), np.array(r)

    def test_matched_operator_is_hard_to_tell_apart(self):
        auc = shortcut_auc(*self._feats(40, leak=False))
        self.assertLess(abs(auc - 0.5), 0.2, auc)

    def test_leaky_edits_are_caught(self):
        self.assertGreater(shortcut_auc(*self._feats(40, leak=True)), 0.9)

    def test_filtering_removes_mostly_the_leaky_cases(self):
        clean_t, clean_r = self._feats(70, leak=False)
        leak_t, leak_r = self._feats(20, leak=True)
        t, r = np.vstack([clean_t, leak_t]), np.vstack([clean_r, leak_r])   # cases 70..89 leak
        before = shortcut_auc(t, r)
        keep, history = filter_shortcut(t, r, target_auc=0.6, max_drop_frac=0.3)
        dropped = set(range(90)) - set(keep.tolist())
        self.assertGreater(before, 0.6)
        self.assertLessEqual(history[-1], 0.6)
        self.assertEqual(history[0], before)
        self.assertLessEqual(len(dropped), 27)                           # respects the 30% cap
        self.assertGreaterEqual(len(dropped & set(range(70, 90))) / len(dropped), 0.7)

    def test_filtering_leaves_clean_data_alone(self):
        t, r = self._feats(60, leak=False)
        keep, history = filter_shortcut(t, r, target_auc=0.7)
        self.assertEqual(len(keep), 60)
        self.assertEqual(len(history), 1)


class TestDuplicates(unittest.TestCase):
    def test_dhash_survives_resize_and_finds_dupes(self):
        img, _ = synthetic_case()
        import cv2
        small = cv2.resize(img, (128, 128))
        other, _ = synthetic_case(lesion_center=(170, 60), lesion_radius=30)
        self.assertLessEqual(hamming(dhash(img), dhash(small)), 4)
        found = near_duplicates({"test1": dhash(small), "test2": dhash(np.fliplr(other).copy())},
                                {"train1": dhash(img)})
        self.assertEqual(found, {"test1": "train1"})

    def test_confirm_rejects_different_patients(self):
        a, _ = synthetic_case(seed=1)
        b, _ = synthetic_case(seed=2)
        self.assertGreater(correlation(a, a), 0.999)
        self.assertLess(correlation(a, b), 0.98)
        found = near_duplicates({"q": dhash(a)}, {"r": dhash(a)}, confirm=lambda q, r: False)
        self.assertEqual(found, {})


if __name__ == "__main__":
    unittest.main()
