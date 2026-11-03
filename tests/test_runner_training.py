import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from medscope.agent.episode import Generation, run_group
from medscope.data.schema import Case, ViewKind
from medscope.data.views import build_views
from medscope.eval.runner import compare_runs, evaluate, load_views, remaining, select_cases
from medscope.rewards import load_config
from medscope.train.common import lr_at
from medscope.train.grpo import collect_groups, group_advantages
from medscope.train.sft import estimate_samples, mode_views, samples_for, view_order
from tests.helpers import synthetic_case

CFG = load_config()


class Oracle:
    """Fake policy: refers on edited images whose lesion is gone, else answers 'Yes' with no box."""

    def __init__(self):
        self.calls = 0

    def generate(self, messages, sample=False):
        self.calls += 1
        return Generation('<final>{"action": "answer", "answer": "Yes", "confidence": 0.7}</final>')


class Batched(Oracle):
    def generate_n(self, messages, n, sample=True):
        self.calls += 1
        return [Generation('<final>{"action": "refer"}</final>') for _ in range(n)]


def build_dataset(root: Path, n_cases: int = 6):
    from PIL import Image
    rng = np.random.default_rng(0)
    views = []
    for i in range(n_cases):
        img, les = synthetic_case(seed=i + 1)
        Image.fromarray(img).save(root / f"img{i}.png")
        Image.fromarray((les * 255).astype(np.uint8)).save(root / f"m{i}.png")
        case = Case(case_id=f"c{i}", patient_id=f"p{i}", dataset="synthetic", modality="ct",
                    image_path=str(root / f"img{i}.png"), question="Is there a tumor?", answer="Yes",
                    mask_path=str(root / f"m{i}.png"))
        views += build_views(case, root / "views", rng)
    path = root / "views.jsonl"
    path.write_text("\n".join(json.dumps(v.to_dict()) for v in views))
    return path


class TestRunner(unittest.TestCase):
    def test_evaluate_writes_results_and_resumes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d))
            self.assertEqual(len(views), 24)
            pol = Oracle()
            s = evaluate(pol, views, CFG, d / "run", {"name": "oracle", "split": "test"}, n_bootstrap=50, log=lambda m: None)
            self.assertEqual(s["n_views"], 24)
            self.assertEqual(s["metrics"]["ccr"]["value"], 1.0)    # always answers yes, correctly
            self.assertEqual(s["metrics"]["asg"]["value"], 0.0)    # never refers
            report = (d / "run" / "report.md").read_text()
            self.assertIn("Abstention specificity gap", report)
            self.assertIn("target_removal", report)
            calls = pol.calls
            evaluate(pol, views, CFG, d / "run", {"name": "oracle", "split": "test"}, n_bootstrap=50, log=lambda m: None)
            self.assertEqual(pol.calls, calls)                        # nothing rerun
            self.assertEqual(len((d / "run" / "outcomes.jsonl").read_text().splitlines()), 24)
            table = compare_runs(d)
            self.assertIn("| oracle | test | 6 |", table)

    def test_api_errors_are_redone(self):
        class Flaky(Oracle):                      # the first 5 requests fail (e.g. no API credit)
            def generate(self, messages, sample=False):
                self.calls += 1
                if self.calls <= 5:
                    return Generation("[API error: PermissionDeniedError: credit balance too low]")
                return super().generate(messages, sample)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d))
            quiet = dict(n_bootstrap=20, log=lambda m: None)
            pol = Flaky()
            s = evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "api"}, **quiet)
            self.assertGreater(s["metrics"]["malformed_rate"]["value"], 0)
            self.assertEqual(len(remaining(views, d / "run", "api")), 5)
            msgs = []
            s = evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "api"}, n_bootstrap=20, log=msgs.append)
            self.assertIn("19 views already done, 5 to run", msgs)   # only the failed episodes were redone
            self.assertEqual(remaining(views, d / "run", "api"), [])
            self.assertEqual(s["metrics"]["malformed_rate"]["value"], 0)
            self.assertEqual(len((d / "run" / "outcomes.jsonl").read_text().splitlines()), 24)

    def test_pilot_subset_carries_over_into_full_run(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d))
            quiet = dict(n_bootstrap=20, log=lambda m: None)
            pol = Oracle()
            evaluate(pol, views[:8], CFG, d / "run", {"name": "a", "precision": "bf16"}, **quiet)
            s = evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "bf16"}, **quiet)
            self.assertEqual(pol.calls, 24)               # 8 pilot + 16 new, none redone
            self.assertEqual(s["n_views"], 24)

    def test_remaining_matches_what_evaluate_would_run(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d))
            quiet = dict(n_bootstrap=20, log=lambda m: None)
            self.assertEqual(len(remaining(views, d / "run")), 24)
            evaluate(Oracle(), views[:8], CFG, d / "run", {"name": "a"}, **quiet)
            self.assertEqual(len(remaining(views, d / "run")), 16)
            self.assertEqual(remaining(views[:8], d / "run"), [])
            self.assertEqual(len(remaining(views[:8], d / "run", precision="bf16")), 8)

    def test_changed_precision_or_view_is_redone(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            views = load_views(build_dataset(d))[:8]
            quiet = dict(n_bootstrap=20, log=lambda m: None)
            pol = Oracle()
            evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "4bit"}, **quiet)
            s = evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "bf16"}, **quiet)
            self.assertEqual(pol.calls, 16)               # everything redone at the new precision
            self.assertEqual(s["n_views"], 8)
            self.assertEqual(len((d / "run" / "outcomes.jsonl").read_text().splitlines()), 8)
            self.assertEqual(len((d / "run" / "stale_outcomes.jsonl").read_text().splitlines()), 8)
            views[0].meta["degradation"] = "noise"         # a rebuilt view with different content
            evaluate(pol, views, CFG, d / "run", {"name": "a", "precision": "bf16"}, **quiet)
            self.assertEqual(pol.calls, 17)

    def test_select_cases_keeps_whole_cases(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d)))
            sub = select_cases(views, 2)
            self.assertEqual(len({v.case_id for v in sub}), 2)
            self.assertEqual(len(sub), 8)
            self.assertEqual([v.view_id for v in sub], [v.view_id for v in select_cases(views, 2)])

    def test_run_group_batches_first_turn(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), 1))
            pol = Batched()
            eps = run_group(pol, views[1], CFG, n=4)
            self.assertEqual(pol.calls, 1)
            self.assertEqual(len(eps), 4)
            self.assertTrue(all(e.outcome.action == "refer" for e in eps))


class TestTrainingPieces(unittest.TestCase):
    def test_group_advantages(self):
        self.assertEqual(group_advantages([1.0, 1.0, 1.0]), [0.0, 0.0, 0.0])
        adv = group_advantages([1.0, -2.0, 1.0, -2.0])
        self.assertAlmostEqual(sum(adv), 0.0)
        self.assertGreater(adv[0], 0)
        self.assertLess(adv[1], 0)

    def test_collect_groups_plain_and_dynamic(self):
        # rewards per view position: positions 0,1,3 give identical rewards (no signal), 2 and 4 differ
        table = {0: [1, 1], 1: [0, 0], 2: [1, -2], 3: [1, 1], 4: [0, 1], 5: [1, -1]}
        calls = []

        def rollout(pos):
            calls.append(pos)
            return table[pos]

        groups, cur = collect_groups(rollout, lambda r: r, 0, want=2)          # plain: exactly 2 groups
        self.assertEqual((len(groups), cur, calls), (2, 2, [0, 1]))
        calls.clear()
        groups, cur = collect_groups(rollout, lambda r: r, 0, want=2, max_draws=10)
        self.assertEqual(calls, [0, 1, 2, 3, 4])                               # stops at 2 with signal
        self.assertEqual(cur, 5)
        self.assertEqual(sum(any(a != 0 for a in adv) for _, adv in groups), 2)
        calls.clear()
        groups, cur = collect_groups(rollout, lambda r: r, 0, want=2, max_draws=3)
        self.assertEqual((calls, cur), ([0, 1, 2], 3))                         # capped

    def test_lr_schedule(self):
        lrs = [lr_at(s, 100, 1e-4) for s in range(100)]
        self.assertLess(lrs[0], lrs[3])                     # warmup
        self.assertAlmostEqual(max(lrs), 1e-4, places=8)
        self.assertGreater(lrs[-1], 0.9e-5)                 # decays to 10%, not zero
        self.assertLess(lrs[-1], 2e-5)

    def test_sft_data_selection(self):
        with tempfile.TemporaryDirectory() as d:
            views = load_views(build_dataset(Path(d), 3))
            g = mode_views(views, "grounding")
            self.assertTrue(all(v.kind in (ViewKind.ORIGINAL, ViewKind.RANDOM_REMOVAL) for v in g))
            self.assertEqual(len(mode_views(views, "agentic")), 12)
            self.assertEqual(estimate_samples(g, "grounding"), 6)
            order = view_order(views, epochs=2, seed=0)
            self.assertEqual(len(order), 24)
            a = [s.target for s in samples_for(views[0], "agentic", 0, 5)]
            b = [s.target for s in samples_for(views[0], "agentic", 0, 5)]
            self.assertEqual(a, b)                          # deterministic, so resume is exact
            for v in g:
                for s in samples_for(v, "grounding", 0, 0):
                    self.assertNotIn("<tool>", s.target)


if __name__ == "__main__":
    unittest.main()
