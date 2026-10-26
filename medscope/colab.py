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
            + f" | {np.mean([r['tool_calls'] for r in chunk]):.2f} | {np.mean([r['groups_with_signal'] for r in chunk]):.1f} | "
            f"{np.mean([r['secs'] for r in chunk]):.0f} |")
    return "\n".join(rows)


def build_report(title: str, sections: list[tuple[str, str]]) -> str:
    out = [f"# {title}", "", "## Environment", environment_info(), ""]
    for heading, body in sections:
        out += [f"## {heading}", "", body, ""]
    return "\n".join(out)
