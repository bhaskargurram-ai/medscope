"""Amendment 10 (R29): grouping pack-4 images by the specialist readers' answers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import reader_rescore as rr  # noqa: E402


def item(i, kind, source, tool=None):
    return {"id": i, "kind": kind, "view_id": f"v{i}", "case_id": f"c{i}", "source": source, "tool": tool}


KEY = {
    "1": item("1", "target_removal", "Brain MRI (LGG)", "lama"),
    "2": item("2", "target_removal", "Chest X-ray (ChestX-Det)", "lama"),
    "3": item("3", "target_removal", "Colonoscopy (Kvasir-SEG, HyperKvasir)", "lama"),
    "4": item("4", "target_removal", "Brain MRI (LGG)", "diffusion"),
    "5": item("5", "original", "Brain MRI (LGG)"),
    "6": item("6", "natural_negative", "Chest X-ray (ChestX-Det)"),
}


def reader(spec, cert, answers):
    return {"specialty": spec, "certified": cert, "answers": [{"id": i, "finding": f} for i, f in answers.items()]}


RAD = reader("Radiology", "board-certified radiologist", {"1": "no", "2": "yes", "3": "yes", "4": "no", "5": "yes", "6": "unsure"})
GI = reader("Gastroenterology / endoscopy", "board-certified other specialty", {"1": "yes", "2": "no", "3": "unsure", "4": "yes", "5": "no", "6": "yes"})
TRAINEE = reader("Internal medicine", "in training", {k: "yes" for k in KEY})


def test_stable_diffusion_views_left_out():
    assert set(rr.main_test_items(KEY)) == {"1", "2", "3", "5", "6"}


def test_judges_by_imaging_area():
    items = rr.main_test_items(KEY)
    g, n = rr.groups(items, [RAD, GI, TRAINEE])
    assert n == {"radiology": 1, "colonoscopy": 1}           # the trainee is not a judge
    # radiology images judged by the radiologist, colonoscopy by the gastroenterologist
    assert g["accepted"] == ["v1", "v3"]                      # v3: "cannot tell" counts as not yes
    assert g["strict"] == ["v1"]
    assert g["called_present"] == ["v2"]
    assert g["confirmed_lesion"] == ["v5"]
    assert g["confirmed_lesion_free"] == ["v6"]               # radiologist "unsure" is not yes


def test_unfinished_reader_not_a_judge():
    partial = reader("Radiology", "board-certified radiologist", {"1": "yes"})
    g, n = rr.groups(rr.main_test_items(KEY), [RAD, partial])
    assert n["radiology"] == 1 and "v1" in g["accepted"]


def test_paired_gap_and_pooled():
    claim = {"action": "answer", "correct": False}
    deny = {"action": "answer", "correct": True}
    comp = [{"v1": claim, "v3": claim}, {"v1": claim, "v3": deny}]
    ref = {"v1": deny, "v3": deny}
    d, lo, hi, n = rr.paired_gap(comp, ref, ["v1", "v3"])
    assert n == 2 and abs(d - 0.75) < 1e-9 and lo <= d <= hi
    m, lo, hi = rr.pooled(comp, ["v1", "v3"], rr.claims)
    assert abs(m - 0.75) < 1e-9
