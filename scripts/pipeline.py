"""Run the rest of the version 2 pipeline (notebooks 08-10) on any GPU machine, e.g. a RunPod pod.

Same steps and arguments as the Colab notebooks; every step resumes where it stopped, so rerun the
same command after any interruption. State lives in a private Hugging Face dataset repo (uploaded
from Google Drive by notebooks/00_sync_drive_to_hf.ipynb) and is synced back after every step.
Reports are pushed to the `runs` branch of the GitHub repo.

Environment:
    HF_TOKEN       Hugging Face token with write access
    HF_WORK_REPO   the dataset repo with the Drive files, e.g. your-name/medscope-work
    GITHUB_TOKEN   token that can push to the medscope repo (Contents: read and write); optional

Usage:
    python scripts/pipeline.py               # everything left: SFT v2, RFT, final test, export
    python scripts/pipeline.py --until 08    # stop after a stage (08, 09 or 10)
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "Qwen/Qwen3.5-4B"
MEDGEMMA = "google/medgemma-1.5-4b-it"
# view files store absolute Colab paths; the same paths are recreated here as links
DRIVE = Path("/content/drive/MyDrive/medscope")
WORK = Path("/content/work")
STORE = Path(os.environ.get("MEDSCOPE_STORE", "/workspace"))
RESULTS, ADAPTERS = DRIVE / "results", DRIVE / "adapters"
VIEWS, VX = WORK / "views", WORK / "views_extra"
NEG_HK, NEG_X = DRIVE / "slake" / "negatives", WORK / "extra" / "negatives"
TRAIN_VIEWS = f"{VIEWS}/train/views_clean.jsonl {VX}/train/views_clean.jsonl"
VAL_VIEWS = f"{VIEWS}/validation/views_clean.jsonl {VX}/validation/views_clean.jsonl"
TEST_VIEWS = f"{VIEWS}/test/views_clean.jsonl {VX}/test/views_clean.jsonl"
TRAIN_NEG = f"{NEG_HK}/views_negatives_train.jsonl {NEG_X}/views_negatives_train.jsonl"
VAL_NEG = f"{NEG_HK}/views_negatives_val.jsonl {NEG_X}/views_negatives_val.jsonl"
TEST_NEG = f"{NEG_HK}/views_negatives.jsonl {NEG_X}/views_negatives.jsonl"

BASELINES = [
    ("v2_base_qwen35_test", "qwen3.5-4b", BASE),
    ("v2_base_medgemma15_test", "medgemma-1.5-4b", MEDGEMMA),
    ("v2_lingshu7b_test", "lingshu-7b", "lingshu-medical-mllm/Lingshu-7B"),
    ("v2_huatuo7b_test", "huatuogpt-vision-7b", "FreedomIntelligence/HuatuoGPT-Vision-7B-Qwen2.5VL"),
    ("v2_qwen25vl7b_test", "qwen2.5-vl-7b", "Qwen/Qwen2.5-VL-7B-Instruct"),
    ("v2_qwen3vl8b_test", "qwen3-vl-8b", "Qwen/Qwen3-VL-8B-Instruct"),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd: str) -> None:
    """Run a project script, streaming its output; stop on failure."""
    log(f"$ {cmd}")
    p = subprocess.run(shlex.split(cmd), cwd=ROOT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    if p.returncode != 0:
        raise SystemExit(f"step failed (exit code {p.returncode}): {cmd}")


# ---- storage: Hugging Face dataset repo <-> local disk ------------------------------------

def link_paths() -> None:
    """Recreate the Colab paths stored in the view files, pointing at the persistent volume."""
    for link, target in ((DRIVE, STORE / "drive"), (WORK, STORE / "work")):
        target.mkdir(parents=True, exist_ok=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            link.symlink_to(target)


def fetch() -> None:
    from huggingface_hub import snapshot_download
    repo = os.environ["HF_WORK_REPO"]
    marker = STORE / ".medscope_fetched"
    if not marker.exists():   # once per machine: later the local copy is newer than the repo
        log(f"downloading {repo}")
        snapshot_download(repo, repo_type="dataset", local_dir=str(STORE / "drive"), max_workers=8)
        marker.touch()
    for tar, check in ((DRIVE / "slake" / "views.tar", VIEWS / "test" / "views_clean.jsonl"),
                       (DRIVE / "extra" / "extra.tar", VX / "test" / "views_clean.jsonl")):
        if not check.exists():
            log(f"extracting {tar.name}")
            with tarfile.open(tar) as t:
                t.extractall(STORE / "work")
    for name in ("TRAIN_VIEWS", "VAL_VIEWS", "TEST_VIEWS", "TRAIN_NEG", "VAL_NEG", "TEST_NEG"):
        files = globals()[name].split()
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            raise SystemExit(f"{name}: missing {missing}")
        log(f"{name}: {sum(sum(1 for _ in open(f)) for f in files)} views")


def sync_up(what: str) -> None:
    """Save adapters and results back to the dataset repo, so losing the machine loses nothing."""
    from huggingface_hub import HfApi
    repo = os.environ["HF_WORK_REPO"]
    log(f"syncing {what} to {repo}")
    HfApi().upload_folder(folder_path=str(STORE / "drive"), repo_id=repo, repo_type="dataset",
                          allow_patterns=["adapters/**", "results/v2_*/**", "results/*_report.md"],
                          commit_message=f"pipeline: {what}")


def push_report(title: str, text: str) -> None:
    """Write the report, and push it to the `runs` branch of the GitHub repo if a token is set."""
    slug = title.split(" - ")[-1].replace(" ", "_").lower()
    path = RESULTS / f"{slug}_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(text[:4000])
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        log("no GITHUB_TOKEN: report saved locally and to the dataset repo only")
        return
    repo_dir = STORE / "runs_branch"
    url = f"https://git:{token}@github.com/bhaskargurram-ai/medscope"
    git = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, capture_output=True, text=True)  # noqa: E731
    if not repo_dir.exists():
        r = subprocess.run(["git", "clone", "--branch", "runs", "--single-branch", url, str(repo_dir)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            subprocess.run(["git", "clone", url, str(repo_dir)], capture_output=True, text=True)
            git("checkout", "--orphan", "runs")
            git("rm", "-rf", "--quiet", ".")
    git("pull", "--quiet", "origin", "runs")
    (repo_dir / "reports").mkdir(exist_ok=True)
    (repo_dir / "reports" / f"{slug}_report.md").write_text(text)
    for run in RESULTS.glob("v2_*"):
        s = run / "summary.json"
        if s.exists():
            (repo_dir / "reports" / "summaries").mkdir(exist_ok=True)
            (repo_dir / "reports" / "summaries" / f"{run.name}.json").write_text(s.read_text())
    git("add", "-A")
    git("-c", "user.name=Bhaskar Gurram", "-c", "user.email=bhaskargurram.g123@gmail.com",
        "commit", "--quiet", "-m", f"report: {title}")
    r = git("push", "--quiet", "origin", "runs")
    log("report pushed to the runs branch" if r.returncode == 0 else
        f"could not push the report (token needs Contents: read and write): {r.stderr.strip()[:200]}")


def report(title: str, sections: list[tuple[str, str]]) -> None:
    from medscope.colab import build_report
    push_report(title, build_report(title, sections))


def evaluate(model: str, adapter: str | None, views: str, out: str, name: str, split: str) -> None:
    adapter_arg = f"--adapter {adapter}" if adapter else ""
    sh(f"python scripts/evaluate.py --model {model} {adapter_arg} --views {views} "
       f"--out {RESULTS}/{out} --name {name} --split {split}")


# ---- stages -------------------------------------------------------------------------------

def stage_08() -> None:
    from medscope.colab import by_dataset, read_text, train_log_summary
    sh(f"python scripts/train_sft.py --model {BASE} --views {TRAIN_VIEWS} --negatives {TRAIN_NEG} "
       f"--mode agentic --out {ADAPTERS}/sft_v2")
    sync_up("SFT v2 trained")
    evaluate(BASE, f"{ADAPTERS}/sft_v2/final", f"{VAL_VIEWS} {VAL_NEG}", "v2_sft_v2_val", "medscope-sft-v2", "validation")
    evaluate(BASE, f"{ADAPTERS}/sft_agentic/final", f"{VAL_VIEWS} {VAL_NEG}", "v2_sft_v1_val", "sft-v1-refer", "validation")
    report("MedScope report - 08 SFT v2", [
        ("Training loss", train_log_summary(ADAPTERS / "sft_v2" / "train_log.jsonl", window=20)),
        ("Validation by imaging type", by_dataset(RESULTS, ["v2_sft_v2_val", "v2_sft_v1_val"])),
        ("SFT v2 on validation", read_text(RESULTS / "v2_sft_v2_val" / "report.md")),
        ("First agentic adapter on the same validation set", read_text(RESULTS / "v2_sft_v1_val" / "report.md")),
    ])
    sync_up("SFT v2 validated")


def stage_09() -> None:
    from medscope.colab import by_dataset, read_text, train_log_summary
    sh(f"python scripts/sample_rft.py --model {BASE} --adapter {ADAPTERS}/sft_v2/final --views {TRAIN_VIEWS} "
       f"--negatives {TRAIN_NEG} --per-kind 150 --k 4 --out {ADAPTERS}/rft/samples.jsonl")
    sync_up("rejection samples")
    sh(f"python scripts/train_sft.py --model {BASE} --init {ADAPTERS}/sft_v2/final --views {TRAIN_VIEWS} "
       f"--negatives {TRAIN_NEG} --subsample 3000 --replays {ADAPTERS}/rft/samples.jsonl --lr 5e-5 "
       f"--mode agentic --out {ADAPTERS}/rft_train")
    sync_up("RFT trained")
    evaluate(BASE, f"{ADAPTERS}/rft_train/final", f"{VAL_VIEWS} {VAL_NEG}", "v2_rft_val", "medscope-rft", "validation")
    scores = {}
    for name, run in (("sft_v2", "v2_sft_v2_val"), ("rft_train", "v2_rft_val")):
        p = RESULTS / run / "summary.json"
        if p.exists():
            scores[name] = json.loads(p.read_text())["metrics"]["net_utility"]["value"]
    best = max(scores, key=scores.get)
    (ADAPTERS / "final_choice.json").write_text(json.dumps(
        {"adapter": f"{ADAPTERS}/{best}/final", "chosen": best, "validation_net_utility": scores}, indent=2))
    log(f"validation net utility {scores} -> final model: {best}")
    report("MedScope report - 09 RFT", [
        ("Rejection sampling: success per view kind", read_text(ADAPTERS / "rft" / "rft_summary.md")),
        ("Fine-tuning loss", train_log_summary(ADAPTERS / "rft_train" / "train_log.jsonl", window=10)),
        ("Final model choice", read_text(ADAPTERS / "final_choice.json")),
        ("Validation by imaging type", by_dataset(RESULTS, ["v2_rft_val", "v2_sft_v2_val", "v2_sft_v1_val"])),
        ("RFT model on validation", read_text(RESULTS / "v2_rft_val" / "report.md")),
    ])
    sync_up("RFT validated")


def stage_10() -> None:
    from medscope.colab import by_dataset, read_text
    from medscope.eval.runner import compare_runs
    choice_file = ADAPTERS / "final_choice.json"
    final = json.loads(choice_file.read_text())["adapter"] if choice_file.exists() else f"{ADAPTERS}/sft_v2/final"
    runs = [("v2_medscope_test", "medscope-4b", BASE, final)] + [(o, n, m, None) for o, n, m in BASELINES] + \
           [("v2_sft_v1_test", "ablation-refer-only-sft", BASE, f"{ADAPTERS}/sft_agentic/final")]
    failed = []
    for out, name, model, adapter in runs:
        try:
            evaluate(model, adapter, f"{TEST_VIEWS} {TEST_NEG}", out, name, "test")
        except SystemExit as e:   # one model failing to load must not cost the others
            failed.append(name)
            log(str(e))
            if name == "medscope-4b":
                raise
        sync_up(f"test: {name}")
        report("MedScope report - 10 final", [
            ("Leaderboard (test)", compare_runs(RESULTS)),
            ("By imaging type", by_dataset(RESULTS, [r[0] for r in runs])),
            ("Failed runs", ", ".join(failed) or "none"),
            ("MedScope on test", read_text(RESULTS / "v2_medscope_test" / "report.md")),
        ])
    summary = RESULTS / "v2_medscope_test" / "summary.json"
    push = f"--push {os.environ['HF_MODEL_REPO']}" if os.environ.get("HF_MODEL_REPO") else ""
    sh(f"python scripts/export_model.py --model {BASE} --adapter {final} --out {DRIVE}/export/MedScope-4B "
       f"--summary {summary} {push}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", default="08", choices=["08", "09", "10"])
    ap.add_argument("--until", default="10", choices=["08", "09", "10"])
    args = ap.parse_args()
    for var in ("HF_TOKEN", "HF_WORK_REPO"):
        if not os.environ.get(var):
            raise SystemExit(f"set {var} first (see the top of this file)")
    link_paths()
    fetch()
    for stage, fn in (("08", stage_08), ("09", stage_09), ("10", stage_10)):
        if args.start <= stage <= args.until:
            log(f"==== stage {stage} ====")
            fn()
    log("done")


if __name__ == "__main__":
    main()
