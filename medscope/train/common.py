"""Small training utilities shared by SFT and GRPO."""

from __future__ import annotations

import json
import math
from pathlib import Path


def lr_at(step: int, total: int, base_lr: float, warmup_frac: float = 0.03, min_frac: float = 0.1) -> float:
    """Linear warmup, then cosine decay to min_frac * base_lr."""
    warm = max(1, int(total * warmup_frac))
    if step < warm:
        return base_lr * (step + 1) / warm
    progress = min(1.0, (step - warm) / max(1, total - warm))
    return base_lr * (min_frac + (1 - min_frac) * 0.5 * (1 + math.cos(math.pi * progress)))


def read_state(out_dir: str | Path) -> dict:
    p = Path(out_dir) / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def write_state(out_dir: str | Path, state: dict) -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    tmp = p / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(p / "state.json")


def append_log(out_dir: str | Path, record: dict) -> None:
    with open(Path(out_dir) / "train_log.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")


def checkpoint_path(out_dir: str | Path) -> Path:
    return Path(out_dir) / "checkpoint"


def save_optimizer(opt, out_dir: str | Path) -> None:
    import torch
    tmp = Path(out_dir) / "optimizer.pt.tmp"
    torch.save(opt.state_dict(), tmp)
    tmp.replace(Path(out_dir) / "optimizer.pt")


def load_optimizer(opt, out_dir: str | Path) -> bool:
    p = Path(out_dir) / "optimizer.pt"
    if not p.exists():
        return False
    import torch
    opt.load_state_dict(torch.load(p, map_location="cpu"))
    return True


def load_adapter_weights(model, path: str | Path) -> None:
    """Load saved LoRA weights into an already-built PEFT model (for resuming)."""
    from peft import set_peft_model_state_dict

    path = Path(path)
    st = path / "adapter_model.safetensors"
    if st.exists():
        from safetensors.torch import load_file
        weights = load_file(str(st))
    else:
        import torch
        weights = torch.load(path / "adapter_model.bin", map_location="cpu")
    set_peft_model_state_dict(model, weights)
