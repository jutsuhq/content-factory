from __future__ import annotations

import re
from pathlib import Path

import yaml

from factory.core import DATA

DIR = DATA / "music"  # the audio files and the manifest of what is installed
MANIFEST = DIR / "library.yaml"
STARTER = Path(__file__).with_name("starter.yaml")  # what `factory music fetch --starter` installs


def tracks() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    return [t for t in (data or []) if (DIR / t["file"]).exists()]


def save(items: list[dict]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(yaml.safe_dump(items, sort_keys=False, allow_unicode=True), encoding="utf-8")


def pick(choice: str | None, mood_text: str = "") -> dict | None:
    """The episode's track: `music` naming a track id wins, "none" means silence, otherwise the track whose moods
    share the most words with the episode's mood text (ties go to the first track marked `default`)."""
    items = tracks()
    if not items or choice == "none":
        return None
    by_id = {t["id"]: t for t in items}
    if choice in by_id:
        return by_id[choice]
    words = set(re.findall(r"\w+", f"{choice or ''} {mood_text}".lower()))
    return max(
        items, key=lambda t: (len(words & set(" ".join(t.get("moods", [])).lower().split())), t.get("default", False))
    )
