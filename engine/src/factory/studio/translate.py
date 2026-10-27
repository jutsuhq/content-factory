"""Another-language version of an episode. Frames do not depend on the language, so the new episode reuses the
original's frames, depth maps and transitions (hard links, no extra disk) and only voice, subtitles and render run.

The translated texts come from whoever writes the scripts (the owner, or an agent over MCP); without them the copy
starts with the original texts to be rewritten by hand. What the image model sees (every other field) is kept,
which keeps every frame's cache key."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from factory.core import EPISODES, LANGUAGES, formats
from factory.studio import store

REUSED = ("frames", "rife")  # work/public folders that only depend on the picture


def _link_tree(src: Path, dst: Path) -> None:
    for f in src.rglob("*"):
        if f.is_file() and ".raw." not in f.name:
            target = dst / f.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(f, target)
            except OSError:  # another volume, or a file system without hard links
                shutil.copyfile(f, target)


def translate(slug: str, language: str, texts: dict | None = None) -> str:
    """Create `<slug>-<language>` with the given texts (title, vo and the fields the format marks translate:
    {<script field>: ..., beats: [{<beat field>: ...}]}) or, without them, the original texts; returns the new slug."""
    if language not in LANGUAGES:
        raise ValueError(f"unsupported language {language}")
    beats = store.beats(slug)
    if not beats:
        raise ValueError(f"{slug} has no script")
    if beats.get("language", "en") == language:
        raise ValueError(f"{slug} is already in {LANGUAGES[language]}")
    fmt = formats.load(beats.get("format"))
    mode = formats.mode(fmt, beats)
    script_texts = ["title", *formats.keys(fmt, mode, "script", "translate")]  # title and vo exist in every format
    beat_texts = [*formats.keys(fmt, mode, "beat", "translate"), "vo"]
    texts = texts or {}
    lines = texts.get("beats") or []
    if lines and len(lines) != len(beats["beats"]):
        raise ValueError(f"texts has {len(lines)} beats, the episode has {len(beats['beats'])}")
    new = {
        **beats,
        "language": language,
        **{k: texts[k] for k in script_texts if texts.get(k)},
        "beats": [
            {**b, **{k: t[k] for k in beat_texts if t.get(k)}}
            for b, t in zip(beats["beats"], lines or [{}] * len(beats["beats"]), strict=False)
        ],
    }
    m = store.meta(slug)
    target = f"{slug}-{language}"
    if (EPISODES / target).exists():
        target = store.new_slug(f"{slug[11:]}-{language}")
    store.write_json(EPISODES / target / "beats.json", new)
    for folder in REUSED:
        src = EPISODES / slug / "work" / "public" / folder
        if src.exists():
            _link_tree(src, EPISODES / target / "work" / "public" / folder)
    store.save_meta(
        target,
        status="script",
        title=new.get("title") or m.get("title"),
        topic=m.get("topic"),
        series=m.get("series") or slug,
        episode_index=m.get("episode_index", 1),
        duration=m.get("duration"),
        created=m.get("created"),
        **{k: m[k] for k in ("project", "variant") if k in m},
        language=language,
        translation_of=slug,
    )
    return target
