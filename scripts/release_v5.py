"""Add the post hoc MedScope-v5 model and the natural-pair runs to the public release.

The first release (scripts/release_hf.py, notebook 53) holds MedScope-4B, MedScope-4B-v4.2 and MedScope-Bench. This
adds, without touching what is there:

  <user>/MedScope-4B-v5       the adapter trained with natural pairs (all videos), with a card that says it is post hoc
  <user>/MedScope-Bench       runs/<name>/ for every natural-pair and v5 run (summary, judged decisions, transcripts),
                              manifests/natural_colon_views.jsonl (video and frame numbers, no images), reports/

    python scripts/release_v5.py --adapter ADAPTERS/v5_s3/final --results RESULTS \
        --views NP/colon/views_natural_colon.jsonl NP/colon_train/views_context_colon.jsonl --out DIR [--upload --public]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_hf import build_model, set_public  # noqa: E402

RUN_PATTERNS = ("np_*", "v5_*", "blind_*", "r17_*", "r21_*")
REPORT_PATTERNS = ("r16_*.md", "r17_*.md", "r18_*.md", "r19_*.md", "r20_*.md", "r21_*.md", "natural_*.md")
BLURB = ("MedScope-v5 (post hoc): the stage 3 of MedScope-4B-v4.2 again, with real same-patient colonoscopy frames "
         "(REAL-Colon, polyp and polyp-free frames of the same video) added to training.")
POST_HOC = """
## Read this first: a post hoc model

MedScope-4B (v4) is the pre-registered model of the paper. On unedited same-patient colonoscopy pairs it rarely
claimed a polyp that was not shown, but it found no more real polyps than its untrained base (natural ESG 0.243 for
both), so its advantage did not carry over. MedScope-v5 was designed **after** that result.

- On the 103 natural pairs, cross-validated over patients (each pair answered by a fold model that never saw its
  video; this repository holds the model trained on all videos), natural ESG is 0.553 [0.430, 0.670]: above
  gpt-6-astra (+0.233 [0.096, 0.369]) and not significantly different from gemini-4-argon (+0.087 [-0.030, 0.207])
  or Claude Opus 5.5 (+0.107 [-0.019, 0.233]). By the rule fixed in advance the result is mixed.
- Main test: unchanged against MedScope-4B (ESG 0.744 against 0.758).
- It claims more erased lesions than MedScope-4B on the fresh external set (19.6% against 8.3%).
- One training run; the fold models were trained on other patients of the same four centres; an independent
  confirmation is still owed. Do not use it, or any model here, for clinical decisions.
"""


def collect(results: Path, views: list[str], out: Path) -> tuple[int, int]:
    """Stage runs/, manifests/ and reports/ exactly as they are laid out in MedScope-Bench."""
    n_runs = 0
    for run in sorted({r for pat in RUN_PATTERNS for r in results.glob(pat)}):
        if not run.is_dir() or not (run / "summary.json").exists() or "reader" in run.name:
            continue
        dst = out / "runs" / run.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("summary.json", "scored.jsonl", "transcripts.jsonl", "usage.json", "report.md"):
            if (run / f).exists():
                shutil.copy2(run / f, dst / f)
        n_runs += 1
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    rows = []
    for f in views:
        for line in Path(f).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["image_path"] = Path(r["image_path"]).name            # local paths mean nothing elsewhere
                r["meta"] = {k: v for k, v in (r.get("meta") or {}).items() if not str(v).startswith("/")}
                rows.append(r)
    (out / "manifests" / "natural_colon_views.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "reports").mkdir(exist_ok=True)
    n_reports = 0
    for f in sorted({f for pat in REPORT_PATTERNS for f in results.glob(pat)}):
        if "reader" not in f.name and "key" not in f.name:
            shutil.copy2(f, out / "reports" / f.name)
            n_reports += 1
    return n_runs, n_reports


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True, help="the MedScope-v5 adapter folder (v5_s3/final)")
    ap.add_argument("--results", required=True)
    ap.add_argument("--views", nargs="+", required=True, help="natural-pair view files for the manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--user", default=None, help="Hugging Face user or organisation (default: the token's owner)")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--public", action="store_true", help="make the model repository public (default: private)")
    args = ap.parse_args()
    out, results = Path(args.out), Path(args.results)
    user = args.user
    if user is None and args.upload:
        from huggingface_hub import HfApi
        user = HfApi().whoami()["name"]
    user = user or "USER"
    model_repo, bench_repo = f"{user}/MedScope-4B-v5", f"{user}/MedScope-Bench"
    build_model(out / "MedScope-4B-v5", Path(args.adapter), model_repo, "MedScope-4B-v5", BLURB, results, "v5_test", "v5_ext")
    card = out / "MedScope-4B-v5" / "README.md"
    text = card.read_text()
    head, sep, rest = text.partition("\n## ")                           # put the notice before the first section
    card.write_text(head + "\n" + POST_HOC.strip() + "\n" + sep + rest if sep else text + "\n" + POST_HOC)
    n_runs, n_reports = collect(results, args.views, out / "bench_add")
    print(f"prepared {out}: the v5 adapter, {n_runs} runs and {n_reports} reports to add to {bench_repo}")
    if args.upload:
        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(model_repo, repo_type="model", private=not args.public, exist_ok=True)
        if args.public:
            set_public(api, model_repo, "model")
        api.upload_folder(folder_path=str(out / "MedScope-4B-v5"), repo_id=model_repo, repo_type="model")
        api.upload_folder(folder_path=str(out / "bench_add"), repo_id=bench_repo, repo_type="dataset")
        urls = {"MedScope-4B-v5": f"https://huggingface.co/{model_repo}",
                "MedScope-Bench": f"https://huggingface.co/datasets/{bench_repo}"}
        (out / "release_v5_urls.json").write_text(json.dumps(urls, indent=1))
        print(json.dumps(urls, indent=1))


if __name__ == "__main__":
    main()
