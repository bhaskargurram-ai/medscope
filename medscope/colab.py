"""Colab helpers: report building and publishing reports as Google Docs.

Reports are published as Google Docs (not raw files) so they can be read back
through the Google Drive connector, which reads Docs but not .json or .md files.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

DRIVE_ROOT = "/content/drive/MyDrive/medscope"
WORK = "/content/work"


def publish_doc(title: str, text: str) -> str:
    """Create or overwrite a Google Doc called `title` in My Drive. Returns its id."""
    import io

    from google.colab import auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload

    auth.authenticate_user()
    service = build("drive", "v3")
    media = MediaIoBaseUpload(io.BytesIO(text.encode("utf-8")), mimetype="text/plain", resumable=False)
    safe = title.replace("'", "\\'")
    existing = service.files().list(
        q=f"name = '{safe}' and mimeType = 'application/vnd.google-apps.document' and trashed = false",
        fields="files(id)").execute().get("files", [])
    if existing:
        doc_id = existing[0]["id"]
        service.files().update(fileId=doc_id, media_body=media).execute()
    else:
        doc_id = service.files().create(
            body={"name": title, "mimeType": "application/vnd.google-apps.document"},
            media_body=media, fields="id").execute()["id"]
    print(f"published Google Doc '{title}' (id {doc_id})")
    return doc_id


def environment_info() -> str:
    """GPU and library versions, so results can be traced to the setup that produced them."""
    lines = []
    try:
        import torch
        lines.append(f"torch {torch.__version__}, CUDA {torch.version.cuda}")
        if torch.cuda.is_available():
            lines.append(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        lines.append("torch not installed")
    for mod in ("transformers", "peft", "bitsandbytes"):
        try:
            lines.append(f"{mod} {__import__(mod).__version__}")
        except ImportError:
            pass
    return "\n".join(f"- {x}" for x in lines)


def read_text(path: str | Path, limit: int = 20000) -> str:
    p = Path(path)
    return p.read_text()[:limit] if p.exists() else f"(missing: {p})"


def train_log_summary(path: str | Path, window: int = 10) -> str:
    """Markdown table of a train_log.jsonl averaged over windows of steps."""
    p = Path(path)
    if not p.exists():
        return f"(no training log at {p})"
    recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    recs = [r for r in recs if "loss" in r or "reward" in r]
    if not recs:
        return "(training log is empty)"
    if "loss" in recs[0]:
        rows = ["| steps | mean loss |", "| --- | --- |"]
        for i in range(0, len(recs), window):
            chunk = recs[i:i + window]
            rows.append(f"| {chunk[0]['step']}-{chunk[-1]['step']} | {np.mean([r['loss'] for r in chunk]):.4f} |")
        return "\n".join(rows)
    rows = ["| steps | mean reward | answer | refer | clarify | malformed | tool calls | groups with signal | secs/step |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i in range(0, len(recs), window):
        chunk = recs[i:i + window]
        acts = Counter()
        for r in chunk:
            acts.update(r["actions"])
        total = sum(acts.values()) or 1
        rows.append(
            f"| {chunk[0]['step']}-{chunk[-1]['step']} | {np.mean([r['reward'] for r in chunk]):+.3f} | "
            + " | ".join(f"{acts[a] / total:.0%}" for a in ("answer", "refer", "clarify", "malformed"))
            + f" | {np.mean([r['tool_calls'] for r in chunk]):.2f} | {np.mean([r['groups_with_signal'] for r in chunk]):.1f}"
            + (f" of {np.mean([r['groups_drawn'] for r in chunk]):.1f}" if all("groups_drawn" in r for r in chunk) else "")
            + " | "
            f"{np.mean([r['secs'] for r in chunk]):.0f} |")
    return "\n".join(rows)


NEG_DOMAINS = {"slakeneg_": "SLAKE CT/MRI (cross-domain)", "hkneg_": "HyperKvasir colonoscopy (in-domain)"}


def negatives_by_domain(results_dir: str | Path, views_file: str | Path | None = None) -> str:
    """Hallucination and safe rates on natural negatives, per model and per domain.

    With views_file, only views in the current test set count (results for views that a
    rebuild moved out of the test set stay on disk but are ignored)."""
    keep = None
    if views_file and Path(views_file).exists():
        keep = {json.loads(l)["view_id"] for l in Path(views_file).read_text().splitlines() if l.strip()}
    rows = ["| Model | Domain | Images | Claims absent finding | Safe (refers or correct No) | Refers |",
            "| --- | --- | --- | --- | --- | --- |"]
    for run in sorted(Path(results_dir).glob("neg_*")):
        p = run / "outcomes.jsonl"
        if not p.exists():
            continue
        recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        if keep is not None:
            recs = [r for r in recs if r["view_id"] in keep]
        for prefix, label in NEG_DOMAINS.items():
            rs = [r for r in recs if r["case_id"].startswith(prefix)]
            if not rs:
                continue
            n = len(rs)
            halluc = sum(r["action"] == "answer" and not r["correct"] for r in rs) / n
            safe = sum(r["action"] == "refer" or (r["action"] == "answer" and r["correct"]) for r in rs) / n
            refer = sum(r["action"] == "refer" for r in rs) / n
            rows.append(f"| {run.name[4:]} | {label} | {n} | {halluc:.0%} | {safe:.0%} | {refer:.0%} |")
    return "\n".join(rows) if len(rows) > 2 else "(no natural-negative results yet)"


def build_report(title: str, sections: list[tuple[str, str]]) -> str:
    out = [f"# {title}", "", "## Environment", environment_info(), ""]
    for heading, body in sections:
        out += [f"## {heading}", "", body, ""]
    return "\n".join(out)
