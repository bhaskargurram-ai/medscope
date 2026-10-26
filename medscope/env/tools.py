"""Evidence tools the agent can call during an episode.

Each call returns a new image for the model to look at plus a short text
observation. The environment enforces the tool budget; calls beyond it are refused
and counted, and the reward penalises them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from ..data.schema import Box, box_to_pixels


@dataclass
class ToolResult:
    ok: bool
    observation: str
    image: np.ndarray | None = None


def zoom(image: np.ndarray, box: Box, out_size: int = 448) -> np.ndarray:
    """Crop a normalised box and upscale its longer side to `out_size`."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = box_to_pixels(box, w, h)
    if x2 - x1 < 2 or y2 - y1 < 2:
        raise ValueError("zoom box is too small")
    crop = image[y1:y2, x1:x2]
    ch, cw = crop.shape[:2]
    scale = out_size / max(ch, cw)
    return cv2.resize(crop, (max(1, round(cw * scale)), max(1, round(ch * scale))),
                      interpolation=cv2.INTER_CUBIC)


def window(image: np.ndarray, center: float, width: float) -> np.ndarray:
    """Intensity windowing on an 8-bit image (centre and width on the 0-255 scale)."""
    if width <= 0:
        raise ValueError("window width must be positive")
    lo, hi = center - width / 2, center + width / 2
    out = (image.astype(np.float32) - lo) / (hi - lo) * 255
    return np.clip(out, 0, 255).astype(np.uint8)


@dataclass
class ToolEnv:
    """Holds the current image and the call budget for one episode."""

    image: np.ndarray
    budget: int = 3
    calls: int = 0
    refused: int = 0
    log: list[dict] = field(default_factory=list)

    def call(self, name: str, args: dict) -> ToolResult:
        if self.calls >= self.budget:
            self.refused += 1
            self.log.append({"name": name, "args": args, "ok": False, "why": "budget"})
            return ToolResult(False, f"Tool budget of {self.budget} calls is used up. Give your final action.")
        self.calls += 1
        try:
            if name == "zoom":
                img = zoom(self.image, [int(v) for v in args["box"]])
                obs = "Zoomed view of the requested region."
            elif name == "window":
                img = window(self.image, float(args["center"]), float(args["width"]))
                obs = "Image re-windowed."
            else:
                raise ValueError(f"unknown tool {name!r}")
        except (KeyError, ValueError, TypeError) as exc:
            self.log.append({"name": name, "args": args, "ok": False, "why": str(exc)})
            return ToolResult(False, f"Tool error: {exc}")
        self.log.append({"name": name, "args": args, "ok": True})
        return ToolResult(True, obs, img)
