"""Tests for the checks of Amendment 7 (R17-R21): leave-one-centre-out files, question type, the image-blind control
and the look reward. No GPU and no image files are needed."""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import blind_views  # noqa: E402
import natural_pairs  # noqa: E402
import question_type  # noqa: E402
from medscope.actions import ToolCall, tool_text  # noqa: E402
from medscope.agent.trajectories import build_trajectory  # noqa: E402
from medscope.data.schema import View, ViewKind  # noqa: E402
from medscope.train import look  # noqa: E402


def nview(video, kind, i, pair=None, slot="pos"):
    meta = {"video": video, "fold": natural_pairs.fold_of(video), "slot": slot}
    if pair:
        meta["pair"] = pair
    return {"view_id": f"{video}_{kind}_{i}", "case_id": f"{video}_{i}", "patient_id": f"realcolon_{video}", "kind": kind,
            "image_path": "x.png", "question": "Is there a polyp in this image?", "answer": "Yes" if kind == "original" else "No",
            "answer_aliases": [], "lesion_box": None, "critical": False, "meta": meta}


class LeaveOneCentreOut(unittest.TestCase):
    def setUp(self):
        self.videos = [f"{c:03d}-{n:03d}" for c in (1, 2, 3, 4) for n in (1, 2, 3)]
        self.rows = [{"video": v, "fold": natural_pairs.fold_of(v),
                      "train": [nview(v, "original", 0), nview(v, "natural_negative", 1, slot="far")],
                      "context": [nview(v, "natural_negative", 9, pair=f"p{v}", slot="context")]} for v in self.videos]
        self.r9 = [x for v in self.videos for x in (nview(v, "original", 5, pair=f"p{v}"),
                                                     nview(v, "natural_negative", 6, pair=f"p{v}"))]

    def test_no_centre_is_shared_and_every_pair_is_tested_once(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            report = natural_pairs.assemble_centres(self.r9, self.rows, out)
            seen = []
            for c in ("001", "002", "003", "004"):
                tr = [json.loads(l) for l in (out / f"views_train_loco{c}.jsonl").read_text().splitlines()]
                te = [json.loads(l) for l in (out / f"views_test_loco{c}.jsonl").read_text().splitlines()]
                self.assertEqual({natural_pairs.cohort_of(v["meta"]["video"]) for v in te}, {c})
                self.assertNotIn(c, {natural_pairs.cohort_of(v["meta"]["video"]) for v in tr})
                self.assertEqual(len(tr), 9 * 2)                       # the three other centres, two frames a video
                self.assertEqual(sum(v["kind"] == "original" for v in te), 3)
                self.assertEqual(len(te), 3 * 3)                       # the pair and its context frame
                seen += [v["view_id"] for v in te if v["kind"] == "original"]
            self.assertEqual(sorted(seen), sorted(v["view_id"] for v in self.r9 if v["kind"] == "original"))
            self.assertIn("| 001 | 9 | 9 | 9 | 3 | 3 |", report)

    def test_cohort_of(self):
        self.assertEqual(natural_pairs.cohort_of("003-014"), "003")


def scored(case, kind, action, correct=None, claims_absent=None):
    return {"view_id": f"{case}__{kind}", "case_id": case, "kind": kind, "action": action, "correct": correct,
            "claims_absent": claims_absent}


class QuestionType(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(question_type.question_type("Is there a polyp in this image?"), "finding-specific")
        self.assertEqual(question_type.question_type("Is there an abnormality in this image?"), "generic")
        self.assertEqual(question_type.question_type("Does this picture look normal?"), "generic")
        self.assertEqual(question_type.question_type("Is the lung healthy?"), "generic")

    def test_esg_is_computed_within_each_stratum(self):
        views, good, bad = [], [], []
        for i in range(20):
            q = "Is there a polyp in this image?" if i < 10 else "Is there an abnormality in this image?"
            for kind in ("original", "target_removal", "random_removal"):
                views.append({"view_id": f"c{i}__{kind}", "case_id": f"c{i}", "kind": kind, "question": q,
                              "meta": {"modality": "endoscopy"}})
            views.append({"view_id": f"n{i}__natural_negative", "case_id": f"n{i}", "kind": "natural_negative",
                          "question": q, "meta": {"modality": "endoscopy"}})
            # the good model: denies every erasure, keeps every intact lesion, never claims on a lesion-free image
            good += [scored(f"c{i}", "target_removal", "answer", correct=True, claims_absent=True),
                     scored(f"c{i}", "random_removal", "answer", correct=True, claims_absent=False),
                     scored(f"n{i}", "natural_negative", "answer", correct=True, claims_absent=True)]
            # the other: claims every erasure of a finding-specific case, behaves like the good one on generic cases
            claims = i < 10
            bad += [scored(f"c{i}", "target_removal", "answer", correct=not claims, claims_absent=not claims),
                    scored(f"c{i}", "random_removal", "answer", correct=True, claims_absent=False),
                    scored(f"n{i}", "natural_negative", "answer", correct=not claims, claims_absent=not claims)]
        text = question_type.report(views, {"good": good, "bad": bad}, "good")
        specific, generic = text.split("### Generic questions")[0], text.split("### Generic questions")[1].split("###")[0]
        self.assertIn("finding-specific: 10 lesion and 10 lesion-free; generic: 10 lesion and 10 lesion-free", text)
        self.assertIn("| good | 10 | 1.000 [1.000, 1.000] | 0.0% | 10 | 0.0% | -- |", specific)
        self.assertIn("| bad | 10 | 0.000 [0.000, 0.000] | 100.0% | 10 | 100.0% | +1.000 [+1.000, +1.000]", specific)
        self.assertIn("| bad | 10 | 1.000 [1.000, 1.000] | 0.0% | 10 | 0.0% | +0.000 [+0.000, +0.000]", generic)
        self.assertIn("### endoscopy: finding-specific questions", text)


class ImageBlind(unittest.TestCase):
    def setUp(self):
        v = lambda case, kind, answer, mod, q="Is there a polyp in this image?": {  # noqa: E731
            "view_id": f"{case}__{kind}", "case_id": case, "patient_id": f"p_{case}", "kind": kind,
            "image_path": f"{case}_{kind}.png", "question": q, "answer": answer, "answer_aliases": [], "lesion_box": None,
            "critical": False, "meta": {"modality": mod}}
        self.views = [v("a", "original", "Yes", "endoscopy"), v("a", "target_removal", "No", "endoscopy"),
                      v("b", "original", "No", "xray", "Is the lung healthy?"), v("b", "target_removal", "Yes", "xray"),
                      v("c", "original", "Yes", "mri")]                               # c has no erasure: not a lesion case
        self.negs = [v("n1", "natural_negative", "No", "endoscopy"), v("n2", "natural_negative", "No", "xray"),
                     v("n3", "natural_negative", "No", "mri")]

    def test_only_yes_questions_with_an_erasure_and_a_swap_of_another_imaging_type(self):
        rows = blind_views.blind_rows(self.views, self.negs, lambda v: f"blank_{v['case_id']}.png")
        self.assertEqual([r["case_id"] for r in rows], ["ablank", "aswap"])
        blank, swap = rows
        self.assertEqual((blank["kind"], blank["answer"], blank["image_path"]), ("natural_negative", "No", "blank_a.png"))
        self.assertEqual(blank["question"], "Is there a polyp in this image?")
        self.assertEqual(blank["meta"]["source_case"], "a")
        self.assertNotEqual(swap["meta"]["swap_modality"], "endoscopy")
        self.assertIn(swap["image_path"], ("n2_natural_negative.png", "n3_natural_negative.png"))
        again = blind_views.blind_rows(self.views, list(reversed(self.negs)), lambda v: "x")
        self.assertEqual(again[1]["meta"]["swap_from"], swap["meta"]["swap_from"])    # the same choice every time

    def test_decisions_and_the_paired_difference(self):
        self.assertEqual(blind_views.decision(scored("x", "natural_negative", "answer", correct=False)), "claimed")
        self.assertEqual(blind_views.decision(scored("x", "natural_negative", "answer", correct=True)), "denied")
        self.assertEqual(blind_views.decision(scored("x", "natural_negative", "refer")), "referred")
        self.assertEqual(blind_views.decision(scored("x", "natural_negative", "clarify")), "clarify")
        views, blind, main = [], [], []
        for i in range(10):
            for variant in blind_views.VARIANTS:
                views.append({"view_id": f"c{i}{variant}__natural_negative",
                              "meta": {"blind": variant, "source_case": f"c{i}"}})
            blind += [scored(f"c{i}blank", "natural_negative", "clarify"),                        # never claims on grey
                      scored(f"c{i}swap", "natural_negative", "answer", correct=i >= 2)]           # claims on 2 of 10
            main += [scored(f"c{i}", "target_removal", "answer", correct=i >= 5),                  # claims 5 of 10 erasures
                     scored(f"n{i}", "natural_negative", "answer", correct=i >= 1)]                # 1 of 10 lesion-free
        m = blind_views.model_rows(views, blind, main)
        self.assertEqual(sum(m["blank"].values()), 0)
        self.assertEqual(sum(m["swap"].values()), 2)
        self.assertEqual(sum(m["erased"].values()), 5)
        self.assertAlmostEqual(m["lesion_free"], 0.1)
        text = blind_views.report(views, {"model": m})
        self.assertIn("| model | 10 | 0.0% / 0.0% / 0.0% / 100.0% | 20.0% / 80.0% / 0.0% / 0.0% | 50.0% | 10.0% | +0.500 [", text)


def view(kind, box=None, meta=None):
    return View(view_id=f"v__{kind.value}", case_id="v", patient_id="p", kind=kind, image_path="none.png",
                question="Is there a polyp in this image?", answer="Yes" if kind is ViewKind.ORIGINAL else "No",
                answer_aliases=[], lesion_box=box, critical=False, meta=meta or {})


class LookReward(unittest.TestCase):
    ZOOM_ON = "Let me look. " + tool_text(ToolCall("zoom", {"box": [380, 380, 620, 620]}))
    ZOOM_OFF = "Let me look. " + tool_text(ToolCall("zoom", {"box": [0, 0, 200, 200]}))
    BOX = [400, 400, 600, 600]

    def test_zoom_boxes_and_coverage(self):
        self.assertEqual(look.zoom_boxes([self.ZOOM_ON, "no tool here", self.ZOOM_OFF]), [[380, 380, 620, 620], [0, 0, 200, 200]])
        self.assertEqual(look.covered_share([380, 380, 620, 620], self.BOX), 1.0)
        self.assertEqual(look.covered_share([0, 0, 500, 1000], self.BOX), 0.5)
        self.assertEqual(look.covered_share([0, 0, 200, 200], self.BOX), 0.0)

    def test_bonus_for_a_zoom_on_the_lesion_or_the_erased_site(self):
        for kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL, ViewKind.TARGET_REMOVAL):
            v = view(kind, self.BOX)
            self.assertEqual(look.look_bonus(v, [self.ZOOM_ON], "answer", False), look.HIT)
            self.assertEqual(look.look_bonus(v, [self.ZOOM_OFF], "answer", False), 0.0)
            self.assertEqual(look.look_bonus(v, [], "answer", False), 0.0)

    def test_bonus_for_inspecting_a_lesion_free_image_before_denying_it(self):
        v = view(ViewKind.NATURAL_NEGATIVE)
        self.assertEqual(look.look_bonus(v, [self.ZOOM_OFF], "answer", True), look.INSPECT)
        self.assertEqual(look.look_bonus(v, [self.ZOOM_OFF], "answer", False), 0.0)      # inspected, then claimed: nothing
        self.assertEqual(look.look_bonus(v, [self.ZOOM_OFF], "refer", None), 0.0)
        self.assertEqual(look.look_bonus(v, [], "answer", True), 0.0)                    # denied without looking: nothing
        self.assertEqual(look.look_bonus(view(ViewKind.DEGRADED), [self.ZOOM_OFF], "clarify", None), 0.0)
        vqa = view(ViewKind.NATURAL_NEGATIVE, meta={"benchmark": "slake"})
        self.assertEqual(look.look_bonus(vqa, [self.ZOOM_OFF], "answer", True), 0.0)

    def test_random_region_is_inside_the_image(self):
        rng = np.random.default_rng(0)
        for _ in range(200):
            x1, y1, x2, y2 = look.random_region(rng)
            self.assertTrue(0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000)
            self.assertTrue(300 <= x2 - x1 <= 500 and x2 - x1 == y2 - y1)

    def test_look_first_trajectories(self):
        img = np.full((64, 64, 3), 90, dtype=np.uint8)
        img[..., 0] = 140                                                              # colour image: no window call
        neg = view(ViewKind.NATURAL_NEGATIVE)
        plain = build_trajectory(neg, np.random.default_rng(1), image=img)
        same = build_trajectory(neg, np.random.default_rng(1), image=img, look_first=0.0)
        self.assertEqual([s.target for s in plain], [s.target for s in same])           # 0 changes nothing
        self.assertEqual(len(plain), 1)                                                 # answered without a look
        looked = build_trajectory(neg, np.random.default_rng(1), image=img, look_first=1.0)
        self.assertEqual(len(looked), 2)
        self.assertEqual(len(look.zoom_boxes([looked[0].target])), 1)                   # a zoom, then the answer
        self.assertIn("answer", looked[1].target)
        vqa = build_trajectory(view(ViewKind.NATURAL_NEGATIVE, meta={"benchmark": "slake"}), np.random.default_rng(1),
                               image=img, look_first=1.0)
        self.assertEqual(len(vqa), 1)                                                   # general VQA is left alone


if __name__ == "__main__":
    unittest.main()
