"""The specialist agent: a lesion segmenter trained only on unedited training images.

It never sees an edited image in training, so how it reacts to erased lesions is a property it has to show on its
own (its evidence sensitivity gap is reported alongside the system's). One binary "lesion" model for all imaging
types; several questions on one image contribute the union of their masks.

Pure helpers (image lists, patient split, regions from a probability map, threshold choice) need only numpy and
OpenCV; training and prediction import torch and torchvision when called.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..data.schema import Box, View, ViewKind, pixels_to_box

SIZE = 512              # network input side
MIN_AREA = 0.001        # regions smaller than 0.1% of the image are ignored
PIXEL_THRESHOLD = 0.5
MAX_REGIONS = 3
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class TrainImage:
    image_path: str
    mask_paths: list[str] = field(default_factory=list)   # empty: a lesion-free image
    patient_id: str = ""


def training_images(views: list[View]) -> list[TrainImage]:
    """Unedited training images with the union of their lesion masks, plus natural negatives with empty masks.
    Edited views (erasures, control edits, degradations, insertions) are never used."""
    by_image: dict[str, TrainImage] = {}
    masks: dict[str, set[str]] = defaultdict(set)
    for v in views:
        if v.kind is ViewKind.ORIGINAL:
            path = v.meta.get("original_image") or v.image_path
            if v.meta.get("inserted") or v.meta.get("benchmark"):
                continue
            by_image.setdefault(path, TrainImage(path, [], v.patient_id))
            if v.meta.get("lesion_mask"):
                masks[path].add(v.meta["lesion_mask"])
        elif v.kind is ViewKind.NATURAL_NEGATIVE:
            by_image.setdefault(v.image_path, TrainImage(v.image_path, [], v.patient_id))
    out = []
    for path, ti in sorted(by_image.items()):
        ti.mask_paths = sorted(masks.get(path, set()))
        out.append(ti)
    return out


def patient_split(items: list[TrainImage], val_frac: float = 0.1, seed: int = 0) -> tuple[list[TrainImage], list[TrainImage]]:
    """Training and validation images with no patient in both."""
    patients = sorted({t.patient_id or t.image_path for t in items})
    rng = np.random.default_rng(seed)
    n_val = max(1, int(round(val_frac * len(patients))))
    val_patients = set(rng.permutation(patients)[:n_val].tolist())
    train = [t for t in items if (t.patient_id or t.image_path) not in val_patients]
    val = [t for t in items if (t.patient_id or t.image_path) in val_patients]
    return train, val


def load_union_mask(paths: list[str], shape: tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    for p in paths:
        x = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if x is None:
            continue
        if x.shape != shape:
            x = cv2.resize(x, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
        m |= x > 127
    return m


def preprocess(image: np.ndarray, size: int = SIZE) -> np.ndarray:
    """RGB uint8 HxWx3 -> float32 3xSxS, ImageNet-normalised."""
    rgb = image if image.ndim == 3 else np.stack([image] * 3, axis=-1)
    x = cv2.resize(rgb[..., :3], (size, size), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return ((x - MEAN) / STD).transpose(2, 0, 1)


@dataclass
class Region:
    box: Box
    score: float


def regions_from_prob(prob: np.ndarray, pixel_threshold: float = PIXEL_THRESHOLD, min_area: float = MIN_AREA,
                      max_regions: int = MAX_REGIONS) -> list[Region]:
    """Connected regions of a probability map (any size), each with its box (0-1000) and peak probability,
    highest first."""
    h, w = prob.shape
    binary = (prob >= pixel_threshold).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    regions = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < min_area * h * w:
            continue
        regions.append(Region(pixels_to_box(int(x), int(y), int(x + bw), int(y + bh), w, h),
                              round(float(prob[labels == i].max()), 3)))
    regions.sort(key=lambda r: -r.score)
    return regions[:max_regions]


def youden_threshold(scores: list[float], labels: list[bool]) -> float:
    """Image-level threshold on the peak probability that maximises sensitivity + specificity - 1."""
    s, y = np.asarray(scores, dtype=float), np.asarray(labels, dtype=bool)
    if y.all() or (~y).all():
        return PIXEL_THRESHOLD
    best, best_t = -1.0, PIXEL_THRESHOLD
    for t in np.unique(s):
        pred = s >= t
        j = pred[y].mean() + (~pred[~y]).mean() - 1
        if j > best:
            best, best_t = j, float(t)
    return round(best_t, 4)


# ---- torch parts ----------------------------------------------------------------------------------------------

def build_model(pretrained_backbone: bool = True):
    from torchvision.models import ResNet50_Weights
    from torchvision.models.segmentation import deeplabv3_resnet50
    return deeplabv3_resnet50(weights=None, weights_backbone=ResNet50_Weights.IMAGENET1K_V1 if pretrained_backbone else None,
                              num_classes=1, aux_loss=False)


class _Dataset:
    def __init__(self, items: list[TrainImage], size: int, augment: bool, seed: int):
        self.items, self.size, self.augment, self.seed = items, size, augment, seed

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        t = self.items[i]
        img = cv2.cvtColor(cv2.imread(t.image_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        mask = load_union_mask(t.mask_paths, img.shape[:2]).astype(np.uint8)
        if self.augment:
            rng = np.random.default_rng()
            if rng.random() < 0.5:
                img, mask = img[:, ::-1].copy(), mask[:, ::-1].copy()
            if rng.random() < 0.5:                       # mild contrast and brightness change
                img = np.clip(img.astype(np.float32) * rng.uniform(0.85, 1.15) + rng.uniform(-15, 15), 0, 255).astype(np.uint8)
        x = preprocess(img, self.size)
        y = cv2.resize(mask, (self.size, self.size), interpolation=cv2.INTER_NEAREST).astype(np.float32)[None]
        return x, y


def _loss(logits, target):
    import torch
    bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
    p = torch.sigmoid(logits)
    inter = (p * target).sum(dim=(1, 2, 3))
    denom = p.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    dice = 1 - (2 * inter + 1) / (denom + 1)
    return bce + dice.mean()


def train_specialist(views: list[View], out_dir: str | Path, epochs: int = 15, batch_size: int = 16, lr: float = 1e-4,
                     size: int = SIZE, workers: int = 8, seed: int = 0, log=print) -> dict:
    """Train, choose the image-level threshold on the patient-disjoint validation images, save model.pt and
    specialist.json. Resumes from the last finished epoch."""
    import torch
    from torch.utils.data import DataLoader

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "specialist.json"
    if meta_path.exists() and json.loads(meta_path.read_text()).get("finished"):
        log(f"specialist already trained: {meta_path}")
        return json.loads(meta_path.read_text())
    torch.manual_seed(seed)
    items = training_images(views)
    train, val = patient_split(items, seed=seed)
    n_pos = sum(bool(t.mask_paths) for t in items)
    log(f"specialist: {len(items)} unedited training images ({n_pos} with a lesion mask), "
        f"{len(train)} for training, {len(val)} patient-disjoint for the threshold")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    start = 0
    ckpt = out / "checkpoint.pt"
    if ckpt.exists():
        state = torch.load(ckpt, map_location=device)
        model.load_state_dict(state["model"]), opt.load_state_dict(state["opt"]), sched.load_state_dict(state["sched"])
        start = state["epoch"] + 1
        log(f"resuming the specialist at epoch {start}")
    loader = DataLoader(_Dataset(train, size, True, seed), batch_size=batch_size, shuffle=True, num_workers=workers,
                        pin_memory=True, drop_last=True, persistent_workers=workers > 0)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")
    for epoch in range(start, epochs):
        model.train()
        t0, losses = time.time(), []
        for x, y in loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                logits = model(x)["out"]
            loss = _loss(logits.float(), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            losses.append(loss.item())
        sched.step()
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": epoch}, ckpt)
        log(f"specialist epoch {epoch + 1}/{epochs}: loss {np.mean(losses):.4f} ({time.time() - t0:.0f}s)")
    torch.save(model.state_dict(), out / "model.pt")
    # image-level threshold on the validation patients: peak probability against "has a lesion mask"
    spec = Specialist(out / "model.pt", threshold=PIXEL_THRESHOLD, device=device)
    scores, labels, dices = [], [], []
    for t in val:
        img = cv2.cvtColor(cv2.imread(t.image_path, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        prob = spec.prob(img)
        scores.append(float(prob.max()))
        labels.append(bool(t.mask_paths))
        if t.mask_paths:
            gt = load_union_mask(t.mask_paths, img.shape[:2])
            pred = prob >= PIXEL_THRESHOLD
            dices.append(2 * (pred & gt).sum() / max(1, pred.sum() + gt.sum()))
    thr = youden_threshold(scores, labels)
    s, y = np.asarray(scores), np.asarray(labels)
    meta = {"finished": True, "threshold": thr, "pixel_threshold": PIXEL_THRESHOLD, "size": size, "epochs": epochs,
            "n_train": len(train), "n_val": len(val),
            "val_sensitivity": round(float((s[y] >= thr).mean()), 3) if y.any() else None,
            "val_specificity": round(float((s[~y] < thr).mean()), 3) if (~y).any() else None,
            "val_dice": round(float(np.mean(dices)), 3) if dices else None}
    meta_path.write_text(json.dumps(meta, indent=2))
    log(f"specialist saved: {meta}")
    return meta


class Specialist:
    """Loaded segmenter: probability map and regions for an image."""

    def __init__(self, path: str | Path, threshold: Optional[float] = None, device: Optional[str] = None):
        import torch
        self.torch = torch
        p = Path(path)
        model_file = p / "model.pt" if p.is_dir() else p
        meta_file = model_file.parent / "specialist.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        self.threshold = threshold if threshold is not None else meta.get("threshold", PIXEL_THRESHOLD)
        self.size = meta.get("size", SIZE)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = build_model(pretrained_backbone=False)
        self.model.load_state_dict(torch.load(model_file, map_location=self.device))
        self.model.to(self.device).eval()

    def prob(self, image: np.ndarray) -> np.ndarray:
        torch = self.torch
        x = torch.from_numpy(preprocess(image, self.size))[None].to(self.device)
        with torch.no_grad(), torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=self.device == "cuda"):
            logits = self.model(x)["out"][0, 0].float()
        p = torch.sigmoid(logits).cpu().numpy()
        h, w = image.shape[:2]
        return cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)

    def report(self, image: np.ndarray) -> dict:
        """What the specialist agent says: peak score, whether it passes the image-level threshold, its regions."""
        prob = self.prob(image)
        peak = float(prob.max())
        # regions are drawn at the image-level threshold when it is below the usual 0.5, so a passing image has one
        regions = regions_from_prob(prob, pixel_threshold=min(PIXEL_THRESHOLD, self.threshold)) if peak >= self.threshold else []
        return {"peak": round(peak, 3), "threshold": self.threshold, "found": bool(regions),
                "regions": [{"box": r.box, "score": r.score} for r in regions]}
