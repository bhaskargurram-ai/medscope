import io
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from medscope.data.loaders import extra
from medscope.data.schema import View, ViewKind
from tests.helpers import synthetic_case

ROOT = Path(__file__).resolve().parent.parent


def png(arr) -> dict:
    b = io.BytesIO()
    Image.fromarray(arr).save(b, format="PNG")
    return {"bytes": b.getvalue(), "path": None}


def cxr_rows(n=40):
    rows = []
    for i in range(n):
        img, lesion = synthetic_case(size=300, seed=i)
        row = {"image": png(img[..., 0]), "image_id": f"{i // 2:08d}_{i % 2:03d}.png", "is_negative": i % 4 == 0}
        for c in list(extra.CXR_FOCAL) + list(extra.CXR_DIFFUSE):
            row[f"{c}_mask"] = None
        if not row["is_negative"]:
            row["nodule_mask"] = png((lesion * 255).astype(np.uint8))
            if i % 10 == 5:
                row["cardiomegaly_mask"] = png((lesion * 255).astype(np.uint8))   # diffuse: skipped
        rows.append(row)
    return rows


def lgg_rows(n=30):
    rows = []
    for i in range(n):
        img, lesion = synthetic_case(size=256, seed=100 + i)
        tumour = i % 3 != 0
        rows.append({"image": png(img), "mask": png((lesion * 255 * tumour).astype(np.uint8)),
                     "patient_id": f"P{i // 6}", "has_tumor": tumour})
    return rows


class TestExtraDatasets(unittest.TestCase):
    def test_chest_xray_rows(self):
        with tempfile.TemporaryDirectory() as d:
            recs, stats = extra.scan("chestxdet", cxr_rows(), Path(d))
            self.assertEqual(stats["chest X-ray: diffuse finding (cannot be erased)"], 4)
            self.assertEqual(sum(r.negative for r in recs), 10)
            pos = [r for r in recs if not r.negative]
            self.assertTrue(all(r.label == "nodule" and r.mask_path for r in pos))
            self.assertEqual(recs[0].group, "cxr_00000000")      # patient id from the NIH file name
            with Image.open(pos[0].image_path) as im:
                self.assertEqual(im.mode, "RGB")

    def test_split_keeps_patients_together_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            recs, _ = extra.scan("lgg", lgg_rows(), d / "images")
            splits = extra.split_and_cap(recs, seed=1)
            where = {}
            for s, rs in splits.items():
                for r in rs:
                    where.setdefault(r.group, set()).add(s)
            self.assertTrue(all(len(v) == 1 for v in where.values()))
            per_patient = Counter((r.group, r.negative) for rs in splits.values() for r in rs)
            self.assertTrue(all(n <= 5 for n in per_patient.values()))
            counts = extra.write_outputs(splits, d)
            self.assertTrue((d / "cases_train.jsonl").exists())
            negs = [View.from_dict(json.loads(l)) for f in (d / "negatives").glob("*.jsonl")
                    for l in f.read_text().splitlines()]
            self.assertTrue(negs and all(v.kind is ViewKind.NATURAL_NEGATIVE and v.answer == "No" for v in negs))
            train = [json.loads(l) for l in (d / "cases_train.jsonl").read_text().splitlines()]
            self.assertEqual(len(train), len({c["image_path"] for c in train}))   # one question per image
            self.assertIn("train", counts)

    def test_built_cases_go_through_the_view_builder(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            recs, _ = extra.scan("lgg", lgg_rows(12), d / "images")
            pos = [r for r in recs if not r.negative][:2]
            with open(d / "cases.jsonl", "w") as f:
                for r in pos:
                    for c in extra.cases_for(r, "test"):
                        f.write(json.dumps(c.to_dict()) + "\n")
            res = subprocess.run([sys.executable, str(ROOT / "scripts/build_views.py"), "--manifest", str(d / "cases.jsonl"),
                                  "--out", str(d / "views")], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            kinds = Counter(json.loads(l)["kind"] for l in (d / "views" / "views.jsonl").read_text().splitlines())
            self.assertEqual(kinds["target_removal"], kinds["original"])
            self.assertGreater(kinds["original"], 0)

    def test_negative_questions_are_stable(self):
        self.assertEqual(extra.negative_question("chestxdet", "k1"), extra.negative_question("chestxdet", "k1"))
        tag, q = extra.negative_question("busi", "k2")
        self.assertIn("ultrasound", q)


if __name__ == "__main__":
    unittest.main()


class TestMismatchAndResume(unittest.TestCase):
    def test_mismatch_image_comes_from_another_imaging_type(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            recs, _ = extra.scan("lgg", lgg_rows(12), d / "images")
            cx, _ = extra.scan("chestxdet", cxr_rows(8), d / "images")
            cases = [c for r in recs + cx if not r.negative for c in extra.cases_for(r, "test")]
            with open(d / "cases.jsonl", "w") as f:
                for c in cases:
                    f.write(json.dumps(c.to_dict()) + "\n")
            res = subprocess.run([sys.executable, str(ROOT / "scripts/build_views.py"), "--manifest", str(d / "cases.jsonl"),
                                  "--out", str(d / "views")], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            views = [json.loads(l) for l in (d / "views" / "views.jsonl").read_text().splitlines()]
            mism = [v for v in views if v["meta"].get("degradation") == "mismatch"]
            self.assertTrue(mism)
            self.assertTrue(all(v["meta"]["mismatch_from"] != v["meta"]["modality"] for v in mism))

    def test_old_mismatch_views_and_cut_off_lines(self):
        from medscope.eval.runner import load_views
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "v.jsonl"
            base = {"case_id": "c", "patient_id": "p", "image_path": "x", "question": "Is there a polyp?",
                    "answer": "Yes", "answer_aliases": [], "lesion_box": None, "critical": False}
            rows = [{**base, "view_id": "a", "kind": "degraded", "meta": {"degradation": "mismatch"}},
                    {**base, "view_id": "b", "kind": "degraded", "meta": {"degradation": "blur"}},
                    {**base, "view_id": "c", "kind": "degraded",
                     "meta": {"degradation": "mismatch", "mismatch_from": "mri", "modality": "xray"}}]
            p.write_text("\n".join(json.dumps(r) for r in rows) + '\n{"view_id": "d", "ki')
            self.assertEqual([v.view_id for v in load_views(p)], ["b", "c"])
