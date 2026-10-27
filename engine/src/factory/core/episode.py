"""An episode on disk: episodes/<slug>/beats.json (the script) plus work/public, where every stage writes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import validate

from factory.core import formats
from factory.core.paths import EPISODES


@dataclass
class Episode:
    slug: str
    dir: Path
    beats: dict
    format_dir: Path

    @classmethod
    def load(cls, slug_or_path: str) -> Episode:
        d = Path(slug_or_path)
        if not d.is_dir():
            d = EPISODES / slug_or_path
        beats = json.loads((d / "beats.json").read_text(encoding="utf-8"))
        fmt = formats.load(beats.get("format"))  # scripts written before formats were named use the default one
        validate(beats, formats.schema(fmt))
        return cls(d.name, d, beats, fmt["dir"])

    @property
    def format(self) -> dict:
        return formats.load(self.format_dir.name)

    @property
    def language(self) -> str:
        return self.beats.get("language", "en")

    def work(self, *parts: str) -> Path:
        """work/public is served to Remotion as its public dir, so every render asset lives there."""
        p = self.dir / "work" / "public"
        for part in parts:
            p = p / part
        p.mkdir(parents=True, exist_ok=True)
        return p
