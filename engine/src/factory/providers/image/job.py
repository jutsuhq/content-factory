from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SHAPES = {
    "v": "a tall vertical 2:3 portrait image (1024x1536)",
    "l": "a 3:2 landscape image (1536x1024)",
    "sq": "a square image",
}
# The same shapes as API parameters: a pixel size (OpenAI) and an aspect ratio (Gemini, fal).
SIZES = {"v": "1024x1536", "l": "1536x1024", "sq": "1024x1024"}
RATIOS = {"v": "2:3", "l": "3:2", "sq": "1:1"}


@dataclass
class ImageJob:
    prompt: str
    out: Path
    shape: str = "v"
    refs: list[Path] = field(default_factory=list)
