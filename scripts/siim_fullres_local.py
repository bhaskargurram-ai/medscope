"""Notebook 26 (post-hoc SIIM check at original resolution) on your own computer with one NVIDIA GPU (12 GB or more).

Same models, same settings as Colab (bf16, never 4-bit), same views pipeline; every stage is skipped when its output
already exists, so rerunning continues where it stopped. Work that does not need the GPU runs at the same time as the
GPU work: the downloads (v4 data, SIIM-ACR, Qwen, LaMa) run together, and the optional gemini-4-argon run (API) runs
while the GPU tests the local models.

    python scripts/siim_fullres_local.py --drive "G:/My Drive/medscope"            # Google Drive for desktop
    python scripts/siim_fullres_local.py --drive ~/medscope_drive --work ~/medscope_work

--drive is your medscope Drive folder (synced by Google Drive for desktop, or a local copy) holding
  v4/v4.tar, adapters/final_choice_v4.json, adapters/v4_s3/final, adapters/v4_s1/final, adapters/v4q_nocf_s0/final,
  results/<the five *_ext2 runs> and (optional) models/big-lama.pt. Results are copied to <drive>/results.
Kaggle key: ~/.kaggle/kaggle.json, or the KAGGLE_USERNAME and KAGGLE_KEY environment variables, or --siim DIR with
  the SIIM-ACR DICOMs and train-rle.csv already downloaded (Kaggle jesperdramsch/siim-acr-pneumothorax-segmentation-data).
GEMINI_API_KEY in the environment adds gemini-4-argon (about $2).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COLAB_WORK, COLAB_DRIVE = "/content/work", "/content/drive/MyDrive/medscope"
BASE = "Qwen/Qwen3.5-4B"
LOCAL_MODELS = [("v4_final", "final"), ("v4q_cf_s0", "adapters/v4_s1/final"),
                ("v4q_nocf_s0", "adapters/v4q_nocf_s0/final"), ("v2_base_qwen35", None)]
SIIM_SOURCES = ["jesperdramsch/siim-acr-pneumothorax-segmentation-data", "seesee/siim-train-test"]
EXT2_FILES = ["v4/views_external2/test/views_clean.jsonl", "v4/external2/negatives/views_negatives_external.jsonl"]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def run(cmd: list[str], env: dict | None = None) -> None:
    log("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT, env={**os.environ, **(env or {})})


# ---------- stage 1: everything to download, at the same time ----------

def extract_ext2(drive: Path, work: Path) -> None:
    """Only the fresh external test (jsonl files and its 256-pixel SIIM images) out of the 4.9 GB v4.tar."""
    if all((work / f).exists() for f in EXT2_FILES):
        return
    tar_path = drive / "v4" / "v4.tar"
    if not tar_path.exists():
        raise SystemExit(f"{tar_path} not found: point --drive at your medscope Drive folder")
    log(f"reading {tar_path} (4.9 GB, one pass) for the fresh external test")
    keep = ("v4/views_external2/", "v4/external2/")
    with tarfile.open(tar_path) as tar:
        for m in tar:
            if m.name.lstrip("./").startswith(keep):
                tar.extract(m, work)
    log("fresh external test extracted")


def get_siim(siim: Path) -> None:
    if any(siim.rglob("*.dcm")):
        return
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        raise SystemExit("pip install kaggle")
    api = KaggleApi()
    api.authenticate()            # ~/.kaggle/kaggle.json or KAGGLE_USERNAME / KAGGLE_KEY
    siim.mkdir(parents=True, exist_ok=True)
    for ds in SIIM_SOURCES:
        try:
            log(f"downloading SIIM-ACR (Kaggle {ds})")
            api.dataset_download_files(ds, path=str(siim), unzip=True, quiet=False)
        except Exception as e:  # noqa: BLE001 - try the next copy of the data
            log(f"{ds} not available: {e}")
        if any(siim.rglob("*.dcm")):
            break
    n = sum(1 for _ in siim.rglob("*.dcm"))
    if not n:
        raise SystemExit("no SIIM-ACR DICOMs downloaded (see above)")
    log(f"SIIM-ACR: {n} DICOM files")


def get_qwen() -> None:
    from huggingface_hub import snapshot_download
    snapshot_download(BASE)
    log(f"{BASE} cached")


def get_lama(drive: Path, work: Path) -> Path:
    dst = work / "models" / "big-lama.pt"
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    src = drive / "models" / "big-lama.pt"
    if src.exists():
        shutil.copy(src, dst)
    else:
        import torch
        from medscope.data.inpaint import LAMA_URL
        torch.hub.download_url_to_file(LAMA_URL, str(dst))
    log("LaMa ready")
    return dst


# ---------- stage 2: Colab paths -> local paths ----------

def localise(src: Path, dst: Path, work: Path, prefix: str | None = None) -> Path:
    """Copy of a views file with /content/work paths pointing at the local work folder (optionally one source only)."""
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    if prefix:
        rows = [r for r in rows if r["case_id"].startswith(prefix)]
    text = "".join(json.dumps(r) + "\n" for r in rows).replace(COLAB_WORK, work.as_posix())
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return dst


def adapter_path(drive: Path, spec: str | None) -> str | None:
    if spec is None:
        return None
    if spec == "final":
        spec = json.loads((drive / "adapters" / "final_choice_v4.json").read_text())["adapter"]
        spec = spec.replace(COLAB_DRIVE + "/", "")
    p = drive / spec
    if not (p / "adapter_config.json").exists():
        raise SystemExit(f"adapter not found: {p}")
    return str(p)


# ---------- stage 4: evaluation ----------

def evaluate(name: str, views: list[Path], out: Path, split: str, adapter: str | None = None, api: bool = False,
             batch: int = 4) -> None:
    cmd = [sys.executable, "scripts/evaluate.py", "--views", *views, "--out", out, "--name", name, "--split", split]
    if api:
        cmd += ["--api", "gemini", "--model", "gemini-4-argon", "--batch-size", "8"]
    else:
        cmd += ["--model", BASE, "--quant", "none", "--batch-size", str(batch)]   # bf16 as on Colab, never 4-bit
        if adapter:
            cmd += ["--adapter", adapter]
    run(cmd)


def publish(results: Path, drive_results: Path, runs: list[str]) -> None:
    drive_results.mkdir(parents=True, exist_ok=True)
    for r in runs:
        if (results / r / "summary.json").exists():
            shutil.copytree(results / r, drive_results / r, dirs_exist_ok=True)


def present_rate(run_dir: Path, prefix: str) -> tuple[int, int]:
    from medscope.eval.runner import scored_rows
    rows = [r for r in scored_rows(run_dir) if r["case_id"].startswith(prefix) and r["kind"] == "original"]
    return sum(r["action"] == "answer" and not r.get("claims_absent") for r in rows), len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drive", required=True, type=Path, help="your medscope Drive folder")
    ap.add_argument("--work", type=Path, default=ROOT / "work_local")
    ap.add_argument("--siim", type=Path, default=None, help="SIIM-ACR folder (default: <work>/raw/siim_full)")
    ap.add_argument("--batch-size", type=int, default=None, help="default: 8 on 20 GB+ GPUs, 4 below")
    ap.add_argument("--skip-256", action="store_true",
                    help="skip re-testing the 256-pixel SIIM cases on this GPU (same-hardware control)")
    args = ap.parse_args()
    drive, work = args.drive.expanduser().resolve(), args.work.expanduser().resolve()
    siim = (args.siim or work / "raw" / "siim_full").expanduser().resolve()
    results = work / "results"
    work.mkdir(parents=True, exist_ok=True)

    import torch
    if not torch.cuda.is_available():
        raise SystemExit("no CUDA GPU visible to PyTorch (install the CUDA build of torch)")
    p = torch.cuda.get_device_properties(0)
    gb = p.total_memory / 2 ** 30
    log(f"GPU: {p.name}, {gb:.0f} GB, compute {p.major}.{p.minor}")
    if gb < 11.5:
        raise SystemExit("this needs a GPU with 12 GB or more for bf16 (4-bit would not match the Colab results)")
    if p.major < 8:
        log("warning: no native bf16 on this GPU; results may differ slightly from Colab")
    batch = args.batch_size or (8 if gb >= 20 else 4)
    for spec in ("final", "adapters/v4_s1/final", "adapters/v4q_nocf_s0/final"):
        adapter_path(drive, spec)                       # fail now, not after an hour of downloads

    log("stage 1: downloads, all at once")
    with ThreadPoolExecutor(4) as pool:
        jobs = [pool.submit(extract_ext2, drive, work), pool.submit(get_siim, siim), pool.submit(get_qwen),
                pool.submit(get_lama, drive, work)]
        for j in jobs:
            j.result()
    lama = work / "models" / "big-lama.pt"

    log("stage 2: local copies of the fresh external test")
    ext2 = [localise(work / f, work / "local" / Path(f).name, work) for f in EXT2_FILES]
    siim256 = [localise(work / f, work / "local" / ("siim256_" + Path(f).name), work, prefix="siimext") for f in EXT2_FILES]

    log("stage 3: the same SIIM cases from the original DICOMs, and their views (LaMa on the GPU)")
    full = work / "v4" / "siim_full"
    if not (full / "cases_test.jsonl").exists():
        run([sys.executable, "scripts/siim_fullres.py", "--views", *ext2, "--siim", siim, "--out", full])
    if not (full / "views" / "views.jsonl").exists():
        run([sys.executable, "scripts/build_views.py", "--manifest", full / "cases_test.jsonl", "--out", full / "views",
             "--inpainter", "lama"], env={"MEDSCOPE_LAMA_PATH": str(lama)})
    if not (full / "views" / "views_clean.jsonl").exists():
        run([sys.executable, "scripts/check_views.py", "--views", full / "views" / "views.jsonl"])
    siimfull = [full / "views" / "views_clean.jsonl", full / "negatives" / "views_negatives_external.jsonl"]

    log("stage 4: tests (local models one at a time on the GPU; gemini-4-argon over the API at the same time)")
    runs = []
    with ThreadPoolExecutor(1) as api_pool:
        api_job = None
        if os.environ.get("GEMINI_API_KEY"):
            api_job = api_pool.submit(evaluate, "gemini-4-argon-siimfull", siimfull, results / "v2_gemini_siimfull",
                                      "siimfull", api=True)
            runs.append("v2_gemini_siimfull")
        plan = [(tag, spec, siimfull, "siimfull") for tag, spec in LOCAL_MODELS]
        if not args.skip_256:
            plan += [(tag, spec, siim256, "siim256local") for tag, spec in LOCAL_MODELS]
        for tag, spec, views, split in plan:
            run_name = f"{tag}_{split}"
            evaluate(f"{tag}-{split}", views, results / run_name, split, adapter_path(drive, spec), batch=batch)
            runs.append(run_name)
            publish(results, drive / "results", [run_name])           # each result reaches Drive as soon as it exists
        if api_job:
            api_job.result()
    publish(results, drive / "results", runs)

    log("stage 5: tables")
    from medscope.colab import by_dataset, build_report
    lines = ["| Model | Called present: 256 px (Colab) | 256 px (this GPU) | original resolution (this GPU) |",
             "| --- | --- | --- | --- |"]
    for tag in [t for t, _ in LOCAL_MODELS] + ["v2_gemini"]:
        cells = []
        for run_dir, prefix in ((drive / "results" / f"{tag}_ext2", "siimext"),
                                (results / f"{tag}_siim256local", "siimext"),
                                (results / f"{tag}_siimfull", "siimfull")):
            a, n = present_rate(run_dir, prefix) if run_dir.exists() else (0, 0)
            cells.append(f"{a}/{n} ({a / n:.0%})" if n else "not run")
        lines.append(f"| {tag} | " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    print(table)
    all_runs = [f"{t}_ext2" for t, _ in LOCAL_MODELS] + ["v2_gemini_ext2"]
    for r in all_runs:
        if (drive / "results" / r).exists() and not (results / r).exists():
            shutil.copytree(drive / "results" / r, results / r)
    report = build_report("MedScope report - 26 SIIM full resolution (local GPU, post hoc)", [
        ("GPU", f"{p.name}, {gb:.0f} GB, bf16, batch size {batch}"),
        ("Matched cases", (full / "report.txt").read_text()),
        ("Pneumothorax called present: 256 px vs original resolution", table),
        ("All metrics by source (siimext = 256 px, siimfull = original resolution)", by_dataset(results, all_runs + runs)),
    ])
    for d in (results, drive / "results"):
        (d / "siim_fullres.md").write_text(table + "\n")
        (d / "26_siim_full_resolution_report.md").write_text(report)
    log(f"done: {drive / 'results' / '26_siim_full_resolution_report.md'}")


if __name__ == "__main__":
    main()
